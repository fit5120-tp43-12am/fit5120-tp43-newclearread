from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AbstractSet, Any, Dict, Optional, Sequence, Set

from .checkpoint import CheckpointStore
from .config import (
    ensure_output_dirs,
    load_pipeline_config,
    read_json,
    read_text,
    sha256_file,
    stable_json_hash,
)
from .judge_gate import judge_result_is_clean_pass, parse_and_validate_judge_result
from .models import ApiCallResult, PipelineConfig, SourceRecord
from .openai_client import OpenAIResponsesClient
from .reports import write_run_reports
from .run_logger import RunLogger
from .source_loader import iter_source_records, validate_sources
from .structural_gate import canonicalize_assistant_label, validate_assistant_label_text
from .writers import (
    accepted_path_for_slug,
    build_quarantine_record,
    build_training_record,
    flush_outputs_from_checkpoint,
    quarantine_path_for_slug,
)


TERMINAL_STATUSES = {"accepted", "quarantined", "source_error"}


def make_run_id(prefix: str = "stage4") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}"


def judge_incomplete_reason(result: ApiCallResult) -> Optional[str]:
    status = result.raw_metadata.get("status")
    details = result.raw_metadata.get("incomplete_details")
    if isinstance(details, dict):
        reason = details.get("reason")
    else:
        reason = None
    if status == "incomplete" or reason:
        return str(reason or status or "unknown")
    return None


class Stage4Pipeline:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = load_pipeline_config(config_path)
        self.generation_prompt = read_text(self.config.paths.generation_prompt)
        self.judge_prompt = read_text(self.config.paths.judge_prompt)
        self.assistant_schema = read_json(self.config.paths.assistant_schema)
        self.judge_schema = read_json(self.config.paths.judge_schema)
        self.config_hash = stable_json_hash(
            {
                "config": self.config.raw,
                "generation_model": self.config.generation_model,
                "judge_model": self.config.judge_model,
                "generation_prompt": self.generation_prompt,
                "judge_prompt": self.judge_prompt,
                "assistant_schema": self.assistant_schema,
                "judge_schema": self.judge_schema,
            }
        )
        self.prompt_hashes = {
            "generation_system": stable_json_hash(self.generation_prompt),
            "judge_system": stable_json_hash(self.judge_prompt),
        }
        self.store: Optional[CheckpointStore] = None

    def close(self) -> None:
        if self.store is not None:
            self.store.close()

    def _ensure_store(self) -> CheckpointStore:
        if self.store is None:
            ensure_output_dirs(self.config)
            self.store = CheckpointStore(self.config.paths.checkpoint_db)
        return self.store

    def expected_source_counts(self) -> Dict[str, int]:
        return {dataset.slug: dataset.expected_records for dataset in self.config.datasets}

    def build_source_manifest(self, source_counts: Dict[str, int]) -> Dict[str, Any]:
        return {
            "datasets": [
                {
                    "slug": dataset.slug,
                    "source_path": str(dataset.source_path),
                    "expected_records": dataset.expected_records,
                    "observed_records": source_counts.get(dataset.slug),
                    "source_file_sha256": sha256_file(dataset.source_path),
                }
                for dataset in self.config.datasets
            ]
        }

    def count_sources(
        self,
        dataset_slugs: Optional[Sequence[str]] = None,
        limit_per_dataset: Optional[int] = None,
        record_ids: Optional[AbstractSet[str]] = None,
    ) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in iter_source_records(self.config, dataset_slugs, limit_per_dataset, record_ids):
            counts[record.dataset_slug] = counts.get(record.dataset_slug, 0) + 1
        return counts

    def matched_record_ids(
        self,
        dataset_slugs: Optional[Sequence[str]] = None,
        limit_per_dataset: Optional[int] = None,
        record_ids: Optional[AbstractSet[str]] = None,
    ) -> Set[str]:
        return {
            record.record_id
            for record in iter_source_records(self.config, dataset_slugs, limit_per_dataset, record_ids)
        }

    def run(
        self,
        run_id: Optional[str] = None,
        dataset_slugs: Optional[Sequence[str]] = None,
        limit_per_dataset: Optional[int] = None,
        record_ids: Optional[AbstractSet[str]] = None,
        validate_only: bool = False,
        rebuild_outputs: bool = False,
        allow_drift: bool = False,
    ) -> Dict[str, Any]:
        run_id = run_id or make_run_id()
        source_validation_counts = validate_sources(self.config)
        source_manifest = self.build_source_manifest(source_validation_counts)
        source_manifest_hash = stable_json_hash(source_manifest)
        source_counts = self.count_sources(dataset_slugs, limit_per_dataset, record_ids)
        if record_ids is not None:
            matched = self.matched_record_ids(dataset_slugs, limit_per_dataset, record_ids)
            missing = sorted(set(record_ids) - matched)
            if missing:
                raise RuntimeError(
                    "Record allowlist contains ids that were not found in the selected sources: "
                    + ", ".join(missing)
                )

        if validate_only:
            return {
                "run_id": run_id,
                "validate_only": True,
                "non_mutating": True,
                "config_hash": self.config_hash,
                "prompt_hashes": self.prompt_hashes,
                "source_manifest_hash": source_manifest_hash,
                "expected_source_counts": self.expected_source_counts(),
                "source_validation_counts": source_validation_counts,
                "source_counts": source_counts,
                "record_allowlist_count": len(record_ids) if record_ids is not None else None,
                "notes": "validate_only_non_mutating",
            }

        if not rebuild_outputs and not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to the environment before running API generation.")

        store = self._ensure_store()
        drift = store.find_startup_drift(
            config_hash=self.config_hash,
            generation_model=self.config.generation_model,
            judge_model=self.config.judge_model,
            max_attempts=self.config.max_attempts,
            prompt_hashes=self.prompt_hashes,
            source_manifest_hash=source_manifest_hash,
        )
        if drift and not allow_drift:
            drift_text = "; ".join(drift)
            raise RuntimeError(
                "Checkpoint drift detected. Refusing to continue because prompt/config/model/source "
                f"expectations changed: {drift_text}. Re-run with --allow-drift to override explicitly."
            )

        logger = RunLogger(self.config.paths.logs_dir / f"{run_id}.jsonl")
        logger.log(
            "run_started",
            run_id=run_id,
            generation_model=self.config.generation_model,
            judge_model=self.config.judge_model,
            config_hash=self.config_hash,
            prompt_hashes=self.prompt_hashes,
            source_manifest_hash=source_manifest_hash,
            source_validation_counts=source_validation_counts,
            dataset_slugs=list(dataset_slugs) if dataset_slugs else None,
            limit_per_dataset=limit_per_dataset,
            record_allowlist_count=len(record_ids) if record_ids is not None else None,
            allow_drift=allow_drift,
        )
        store.start_run(
            run_id=run_id,
            config_hash=self.config_hash,
            generation_model=self.config.generation_model,
            judge_model=self.config.judge_model,
            max_attempts=self.config.max_attempts,
            prompt_hashes=self.prompt_hashes,
            source_manifest_hash=source_manifest_hash,
            source_manifest=source_manifest,
        )

        if rebuild_outputs:
            output_summary = flush_outputs_from_checkpoint(store, self.config)
            notes = "rebuild_outputs"
            logger.log(notes, run_id=run_id, source_counts=source_counts, outputs=output_summary)
            report_json, report_md = write_run_reports(
                store,
                self.config,
                run_id,
                self.config_hash,
                self.prompt_hashes,
                source_counts,
                output_summary,
                notes=notes,
                source_validation_counts=source_validation_counts,
                expected_source_counts=self.expected_source_counts(),
                source_manifest_hash=source_manifest_hash,
            )
            store.finish_run(run_id, "completed", report_json, report_md, notes=notes)
            logger.log("run_completed", run_id=run_id, status="completed", reports=[str(report_json), str(report_md)])
            return {"run_id": run_id, "source_counts": source_counts, "reports": [str(report_json), str(report_md)]}

        client = OpenAIResponsesClient(self.config.api)
        processed = 0
        accepted = 0
        quarantined = 0
        skipped = 0

        try:
            for record in iter_source_records(self.config, dataset_slugs, limit_per_dataset, record_ids):
                row = store.upsert_record_seen(record, run_id)
                if row["status"] in TERMINAL_STATUSES:
                    skipped += 1
                    logger.log(
                        "record_skipped",
                        run_id=run_id,
                        record_id=record.record_id,
                        dataset_slug=record.dataset_slug,
                        line_number=record.line_number,
                        status=row["status"],
                    )
                    continue
                result = self._process_record(client, record, run_id, logger)
                processed += 1
                if result == "accepted":
                    accepted += 1
                elif result == "quarantined":
                    quarantined += 1

                if self.config.flush_every_records > 0 and processed % self.config.flush_every_records == 0:
                    flush_outputs_from_checkpoint(store, self.config)

            output_summary = flush_outputs_from_checkpoint(store, self.config)
            report_json, report_md = write_run_reports(
                store,
                self.config,
                run_id,
                self.config_hash,
                self.prompt_hashes,
                source_counts,
                output_summary,
                notes="completed",
                source_validation_counts=source_validation_counts,
                expected_source_counts=self.expected_source_counts(),
                source_manifest_hash=source_manifest_hash,
            )
            store.finish_run(run_id, "completed", report_json, report_md, notes="completed")
            logger.log(
                "run_completed",
                run_id=run_id,
                status="completed",
                processed=processed,
                accepted=accepted,
                quarantined=quarantined,
                skipped=skipped,
                reports=[str(report_json), str(report_md)],
            )
            return {
                "run_id": run_id,
                "processed": processed,
                "accepted": accepted,
                "quarantined": quarantined,
                "skipped": skipped,
                "source_counts": source_counts,
                "reports": [str(report_json), str(report_md)],
                "outputs": output_summary,
            }
        except Exception as exc:
            output_summary = flush_outputs_from_checkpoint(store, self.config)
            report_json, report_md = write_run_reports(
                store,
                self.config,
                run_id,
                self.config_hash,
                self.prompt_hashes,
                source_counts,
                output_summary,
                notes=f"aborted:{exc}",
                source_validation_counts=source_validation_counts,
                expected_source_counts=self.expected_source_counts(),
                source_manifest_hash=source_manifest_hash,
            )
            store.finish_run(run_id, "aborted", report_json, report_md, notes=str(exc))
            logger.log("run_aborted", run_id=run_id, error=str(exc), reports=[str(report_json), str(report_md)])
            raise

    def _process_record(
        self,
        client: OpenAIResponsesClient,
        record: SourceRecord,
        run_id: str,
        logger: RunLogger,
    ) -> str:
        self.store.mark_in_progress(record.record_id, run_id)
        logger.log(
            "record_started",
            run_id=run_id,
            record_id=record.record_id,
            dataset_slug=record.dataset_slug,
            line_number=record.line_number,
        )
        starting_attempt = self.store.attempt_count(record.record_id) + 1
        last_state: Dict[str, Any] = {}

        for attempt_number in range(starting_attempt, self.config.max_attempts + 1):
            generation = client.generate_label(
                model=self.config.generation_model,
                system_prompt=self.generation_prompt,
                source_text=record.source_text,
                assistant_schema=self.assistant_schema,
            )
            gate = validate_assistant_label_text(generation.text)
            if not gate.ok:
                reason = ";".join(gate.issues)
                logger.log(
                    "attempt_retry",
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_2_structural_gate",
                    generation_response_id=generation.response_id,
                    structural_ok=False,
                    usage={"generation": generation.usage},
                    reason=reason,
                )
                self.store.add_attempt(
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_2_structural_gate",
                    status="retry",
                    generation_response_id=generation.response_id,
                    generation_model=self.config.generation_model,
                    structural_ok=False,
                    error=reason,
                    usage={"generation": generation.usage},
                    raw_generation_text=generation.text,
                    cleaned_generation_text=gate.cleaned_text,
                )
                last_state = {
                    "reason": reason,
                    "last_stage": "stage_2_structural_gate",
                    "last_raw_generation": generation.text,
                    "last_cleaned_generation": gate.cleaned_text,
                    "structural_issues": gate.issues,
                }
                continue

            candidate = gate.parsed
            assert candidate is not None
            judge = client.judge_label(
                model=self.config.judge_model,
                system_prompt=self.judge_prompt,
                source_text=record.source_text,
                candidate_label=candidate,
                judge_schema=self.judge_schema,
                domain_hint=record.domain_hint,
            )
            incomplete_reason = judge_incomplete_reason(judge)
            if incomplete_reason is not None:
                reason = "judge_output_incomplete:" + incomplete_reason
                judge_payload = {
                    "raw_text": judge.text,
                    "raw_metadata": judge.raw_metadata,
                    "issues": [reason],
                }
                logger.log(
                    "attempt_retry",
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_3_judge",
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    structural_ok=True,
                    usage={"generation": generation.usage, "judge": judge.usage},
                    reason=reason,
                )
                self.store.add_attempt(
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_3_judge",
                    status="retry",
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    generation_model=self.config.generation_model,
                    judge_model=self.config.judge_model,
                    structural_ok=True,
                    error=reason,
                    usage={"generation": generation.usage, "judge": judge.usage},
                    raw_generation_text=generation.text,
                    cleaned_generation_text=gate.cleaned_text,
                    candidate=candidate,
                    judge=judge_payload,
                )
                last_state = {
                    "reason": reason,
                    "last_stage": "stage_3_judge",
                    "last_raw_generation": generation.text,
                    "last_cleaned_generation": gate.cleaned_text,
                    "last_candidate": candidate,
                    "last_judge": judge_payload,
                    "structural_issues": [],
                }
                continue
            judge_result, cleaned_judge_text, judge_issues = parse_and_validate_judge_result(judge.text)
            if judge_result is None:
                reason = "judge_output_invalid:" + ";".join(judge_issues)
                logger.log(
                    "attempt_retry",
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_3_judge",
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    structural_ok=True,
                    usage={"generation": generation.usage, "judge": judge.usage},
                    reason=reason,
                )
                self.store.add_attempt(
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_3_judge",
                    status="retry",
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    generation_model=self.config.generation_model,
                    judge_model=self.config.judge_model,
                    structural_ok=True,
                    error=reason,
                    usage={"generation": generation.usage, "judge": judge.usage},
                    raw_generation_text=generation.text,
                    cleaned_generation_text=gate.cleaned_text,
                    candidate=candidate,
                    judge={"raw_text": judge.text, "cleaned_text": cleaned_judge_text, "issues": judge_issues},
                )
                last_state = {
                    "reason": reason,
                    "last_stage": "stage_3_judge",
                    "last_raw_generation": generation.text,
                    "last_cleaned_generation": gate.cleaned_text,
                    "last_candidate": candidate,
                    "last_judge": {"raw_text": judge.text, "cleaned_text": cleaned_judge_text, "issues": judge_issues},
                    "structural_issues": [],
                }
                continue

            clean_pass = judge_result_is_clean_pass(judge_result)
            verdict = "pass" if clean_pass else judge_result.get("verdict", "retry")
            if verdict == "pass":
                accepted_record = build_training_record(record, candidate, self.generation_prompt)
                logger.log(
                    "record_accepted",
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    usage={"generation": generation.usage, "judge": judge.usage},
                )
                self.store.add_attempt(
                    run_id=run_id,
                    record_id=record.record_id,
                    attempt_number=attempt_number,
                    stage="stage_3_judge",
                    status="accepted",
                    generation_response_id=generation.response_id,
                    judge_response_id=judge.response_id,
                    generation_model=self.config.generation_model,
                    judge_model=self.config.judge_model,
                    structural_ok=True,
                    judge_verdict="pass",
                    usage={"generation": generation.usage, "judge": judge.usage},
                    raw_generation_text=generation.text,
                    cleaned_generation_text=gate.cleaned_text,
                    candidate=candidate,
                    judge=judge_result,
                )
                self.store.mark_accepted(
                    record.record_id,
                    run_id,
                    accepted_record,
                    accepted_path_for_slug(self.config, record.dataset_slug),
                )
                return "accepted"

            reason = judge_result.get("reason", "judge requested retry")
            status = "fail" if verdict == "fail" else "retry"
            logger.log(
                "attempt_" + status,
                run_id=run_id,
                record_id=record.record_id,
                attempt_number=attempt_number,
                stage="stage_3_judge",
                generation_response_id=generation.response_id,
                judge_response_id=judge.response_id,
                judge_verdict=verdict,
                usage={"generation": generation.usage, "judge": judge.usage},
                reason=reason,
            )
            self.store.add_attempt(
                run_id=run_id,
                record_id=record.record_id,
                attempt_number=attempt_number,
                stage="stage_3_judge",
                status=status,
                generation_response_id=generation.response_id,
                judge_response_id=judge.response_id,
                generation_model=self.config.generation_model,
                judge_model=self.config.judge_model,
                structural_ok=True,
                judge_verdict=verdict,
                error=reason,
                usage={"generation": generation.usage, "judge": judge.usage},
                raw_generation_text=generation.text,
                cleaned_generation_text=gate.cleaned_text,
                candidate=candidate,
                judge=judge_result,
            )
            last_state = {
                "reason": reason,
                "last_stage": "stage_3_judge",
                "last_raw_generation": generation.text,
                "last_cleaned_generation": gate.cleaned_text,
                "last_candidate": candidate,
                "last_judge": judge_result,
                "structural_issues": [],
            }
            if verdict == "fail":
                self._quarantine(record, run_id, attempt_number, "judge_fail:" + reason, last_state, logger)
                return "quarantined"

        attempts_used = self.config.max_attempts
        reason = "retry_budget_exhausted:" + str(last_state.get("reason", "unknown"))
        self._quarantine(record, run_id, attempts_used, reason, last_state, logger)
        return "quarantined"

    def _quarantine(
        self,
        record: SourceRecord,
        run_id: str,
        attempts_used: int,
        reason: str,
        last_state: Dict[str, Any],
        logger: RunLogger,
    ) -> None:
        quarantine_record = build_quarantine_record(
            record=record,
            run_id=run_id,
            reason=reason,
            attempts_used=attempts_used,
            last_stage=last_state.get("last_stage", "unknown"),
            last_raw_generation=last_state.get("last_raw_generation", ""),
            last_cleaned_generation=last_state.get("last_cleaned_generation", ""),
            last_candidate=last_state.get("last_candidate"),
            last_judge=last_state.get("last_judge"),
            structural_issues=last_state.get("structural_issues", []),
        )
        self.store.mark_quarantined(
            record.record_id,
            run_id,
            quarantine_record,
            quarantine_path_for_slug(self.config, record.dataset_slug),
            reason,
        )
        logger.log(
            "record_quarantined",
            run_id=run_id,
            record_id=record.record_id,
            dataset_slug=record.dataset_slug,
            line_number=record.line_number,
            attempts_used=attempts_used,
            reason=reason,
        )
