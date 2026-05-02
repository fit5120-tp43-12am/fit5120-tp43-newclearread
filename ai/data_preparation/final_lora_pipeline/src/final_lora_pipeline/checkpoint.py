from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import SourceRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CheckpointStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def close(self) -> None:
        self.conn.close()

    def init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                config_hash TEXT NOT NULL,
                generation_model TEXT NOT NULL,
                judge_model TEXT NOT NULL,
                max_attempts INTEGER NOT NULL,
                prompt_hashes_json TEXT,
                source_manifest_hash TEXT,
                source_manifest_json TEXT,
                status TEXT NOT NULL,
                report_json_path TEXT,
                report_md_path TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS records (
                record_id TEXT PRIMARY KEY,
                dataset_slug TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                source_path TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                accepted_json TEXT,
                quarantine_json TEXT,
                output_path TEXT,
                quarantine_path TEXT,
                last_error TEXT,
                first_seen_run_id TEXT NOT NULL,
                updated_run_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                record_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                generation_response_id TEXT,
                judge_response_id TEXT,
                generation_model TEXT,
                judge_model TEXT,
                structural_ok INTEGER,
                judge_verdict TEXT,
                error TEXT,
                usage_json TEXT,
                raw_generation_text TEXT,
                cleaned_generation_text TEXT,
                candidate_json TEXT,
                judge_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id),
                FOREIGN KEY(record_id) REFERENCES records(record_id)
            );

            CREATE INDEX IF NOT EXISTS idx_records_dataset_status
                ON records(dataset_slug, status, line_number);
            CREATE INDEX IF NOT EXISTS idx_attempts_record
                ON attempts(record_id, attempt_number);
            """
        )
        self._ensure_column("runs", "prompt_hashes_json", "TEXT")
        self._ensure_column("runs", "source_manifest_hash", "TEXT")
        self._ensure_column("runs", "source_manifest_json", "TEXT")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self.conn.execute(f"PRAGMA table_info({table})")
        }
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def start_run(
        self,
        run_id: str,
        config_hash: str,
        generation_model: str,
        judge_model: str,
        max_attempts: int,
        prompt_hashes: Optional[Dict[str, str]] = None,
        source_manifest_hash: Optional[str] = None,
        source_manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, started_at, ended_at, config_hash, generation_model,
                judge_model, max_attempts, prompt_hashes_json, source_manifest_hash,
                source_manifest_json, status
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                utc_now(),
                config_hash,
                generation_model,
                judge_model,
                max_attempts,
                json.dumps(prompt_hashes or {}, ensure_ascii=False, sort_keys=True),
                source_manifest_hash,
                json.dumps(source_manifest or {}, ensure_ascii=False, sort_keys=True),
                "running",
            ),
        )
        self.conn.commit()

    def has_resume_state(self) -> bool:
        record_count = self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        attempt_count = self.conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        return bool(record_count or attempt_count)

    def find_startup_drift(
        self,
        config_hash: str,
        generation_model: str,
        judge_model: str,
        max_attempts: int,
        prompt_hashes: Dict[str, str],
        source_manifest_hash: str,
    ) -> List[str]:
        if not self.has_resume_state():
            return []

        relevant_run_ids = [
            row["run_id"]
            for row in self.conn.execute(
                """
                SELECT first_seen_run_id AS run_id FROM records
                UNION
                SELECT updated_run_id AS run_id FROM records
                UNION
                SELECT run_id AS run_id FROM attempts
                ORDER BY run_id
                """
            )
        ]
        if not relevant_run_ids:
            return ["checkpoint contains resumable record state but no linked run ids"]

        placeholders = ",".join("?" for _ in relevant_run_ids)
        rows = list(
            self.conn.execute(
                f"""
                SELECT run_id, config_hash, generation_model, judge_model, max_attempts,
                       prompt_hashes_json, source_manifest_hash
                FROM runs
                WHERE run_id IN ({placeholders})
                ORDER BY started_at, run_id
                """,
                relevant_run_ids,
            )
        )
        found_run_ids = {row["run_id"] for row in rows}
        missing_run_ids = sorted(set(relevant_run_ids) - found_run_ids)

        drift: List[str] = []
        for run_id in missing_run_ids:
            drift.append(f"run {run_id}: linked run metadata is missing")
        for row in rows:
            run_label = f"run {row['run_id']}"
            if row["config_hash"] != config_hash:
                drift.append(f"{run_label}: config_hash differs")
            if row["generation_model"] != generation_model:
                drift.append(f"{run_label}: generation_model differs")
            if row["judge_model"] != judge_model:
                drift.append(f"{run_label}: judge_model differs")
            if int(row["max_attempts"]) != int(max_attempts):
                drift.append(f"{run_label}: max_attempts differs")

            stored_prompt_hashes = row["prompt_hashes_json"]
            if stored_prompt_hashes is None:
                drift.append(f"{run_label}: prompt hash metadata is missing")
            else:
                try:
                    parsed_prompt_hashes = json.loads(stored_prompt_hashes)
                except json.JSONDecodeError:
                    drift.append(f"{run_label}: prompt hash metadata is invalid JSON")
                else:
                    if parsed_prompt_hashes != prompt_hashes:
                        drift.append(f"{run_label}: prompt hashes differ")

            stored_source_manifest_hash = row["source_manifest_hash"]
            if stored_source_manifest_hash is None:
                drift.append(f"{run_label}: source manifest metadata is missing")
            elif stored_source_manifest_hash != source_manifest_hash:
                drift.append(f"{run_label}: source manifest hash differs")

        return drift

    def finish_run(
        self,
        run_id: str,
        status: str,
        report_json_path: Optional[Path] = None,
        report_md_path: Optional[Path] = None,
        notes: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET ended_at = ?, status = ?, report_json_path = ?, report_md_path = ?, notes = ?
            WHERE run_id = ?
            """,
            (
                utc_now(),
                status,
                str(report_json_path) if report_json_path else None,
                str(report_md_path) if report_md_path else None,
                notes,
                run_id,
            ),
        )
        self.conn.commit()

    def upsert_record_seen(self, record: SourceRecord, run_id: str) -> sqlite3.Row:
        now = utc_now()
        existing = self.get_record(record.record_id)
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO records (
                    record_id, dataset_slug, line_number, source_path, source_sha256,
                    status, attempts, first_seen_run_id, updated_run_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.dataset_slug,
                    record.line_number,
                    str(record.source_path),
                    record.source_sha256,
                    "pending",
                    run_id,
                    run_id,
                    now,
                    now,
                ),
            )
        else:
            self.conn.execute(
                """
                UPDATE records
                SET dataset_slug = ?, line_number = ?, source_path = ?, source_sha256 = ?,
                    updated_run_id = ?, updated_at = ?
                WHERE record_id = ?
                """,
                (
                    record.dataset_slug,
                    record.line_number,
                    str(record.source_path),
                    record.source_sha256,
                    run_id,
                    now,
                    record.record_id,
                ),
            )
        self.conn.commit()
        return self.get_record(record.record_id)

    def get_record(self, record_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM records WHERE record_id = ?",
            (record_id,),
        ).fetchone()

    def attempt_count(self, record_id: str) -> int:
        row = self.get_record(record_id)
        if row is None:
            return 0
        return int(row["attempts"])

    def mark_in_progress(self, record_id: str, run_id: str) -> None:
        self.conn.execute(
            """
            UPDATE records
            SET status = ?, updated_run_id = ?, updated_at = ?
            WHERE record_id = ? AND status NOT IN ('accepted', 'quarantined', 'source_error')
            """,
            ("in_progress", run_id, utc_now(), record_id),
        )
        self.conn.commit()

    def add_attempt(
        self,
        run_id: str,
        record_id: str,
        attempt_number: int,
        stage: str,
        status: str,
        generation_response_id: Optional[str] = None,
        judge_response_id: Optional[str] = None,
        generation_model: Optional[str] = None,
        judge_model: Optional[str] = None,
        structural_ok: Optional[bool] = None,
        judge_verdict: Optional[str] = None,
        error: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
        raw_generation_text: Optional[str] = None,
        cleaned_generation_text: Optional[str] = None,
        candidate: Optional[Dict[str, Any]] = None,
        judge: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO attempts (
                run_id, record_id, attempt_number, stage, status,
                generation_response_id, judge_response_id, generation_model, judge_model,
                structural_ok, judge_verdict, error, usage_json, raw_generation_text,
                cleaned_generation_text, candidate_json, judge_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                record_id,
                attempt_number,
                stage,
                status,
                generation_response_id,
                judge_response_id,
                generation_model,
                judge_model,
                None if structural_ok is None else int(structural_ok),
                judge_verdict,
                error,
                json.dumps(usage or {}, ensure_ascii=False),
                raw_generation_text,
                cleaned_generation_text,
                json.dumps(candidate, ensure_ascii=False) if candidate is not None else None,
                json.dumps(judge, ensure_ascii=False) if judge is not None else None,
                utc_now(),
            ),
        )
        self.conn.execute(
            """
            UPDATE records
            SET attempts = MAX(attempts, ?), last_error = ?, updated_run_id = ?, updated_at = ?
            WHERE record_id = ?
            """,
            (attempt_number, error, run_id, utc_now(), record_id),
        )
        self.conn.commit()

    def mark_accepted(self, record_id: str, run_id: str, accepted_json: Dict[str, Any], output_path: Path) -> None:
        self.conn.execute(
            """
            UPDATE records
            SET status = ?, accepted_json = ?, output_path = ?, last_error = NULL,
                updated_run_id = ?, updated_at = ?
            WHERE record_id = ?
            """,
            (
                "accepted",
                json.dumps(accepted_json, ensure_ascii=False),
                str(output_path),
                run_id,
                utc_now(),
                record_id,
            ),
        )
        self.conn.commit()

    def mark_quarantined(
        self,
        record_id: str,
        run_id: str,
        quarantine_json: Dict[str, Any],
        quarantine_path: Path,
        reason: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE records
            SET status = ?, quarantine_json = ?, quarantine_path = ?, last_error = ?,
                updated_run_id = ?, updated_at = ?
            WHERE record_id = ?
            """,
            (
                "quarantined",
                json.dumps(quarantine_json, ensure_ascii=False),
                str(quarantine_path),
                reason,
                run_id,
                utc_now(),
                record_id,
            ),
        )
        self.conn.commit()

    def mark_source_error(self, record_id: str, run_id: str, reason: str) -> None:
        self.conn.execute(
            """
            UPDATE records
            SET status = ?, last_error = ?, updated_run_id = ?, updated_at = ?
            WHERE record_id = ?
            """,
            ("source_error", reason, run_id, utc_now(), record_id),
        )
        self.conn.commit()

    def fetch_accepted_records(self) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM records
                WHERE status = 'accepted' AND accepted_json IS NOT NULL
                ORDER BY dataset_slug, line_number
                """
            )
        )

    def fetch_quarantine_records(self) -> List[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM records
                WHERE status = 'quarantined' AND quarantine_json IS NOT NULL
                ORDER BY dataset_slug, line_number
                """
            )
        )

    def status_summary(self) -> Dict[str, Any]:
        by_status = {
            row["status"]: row["count"]
            for row in self.conn.execute(
                "SELECT status, COUNT(*) AS count FROM records GROUP BY status ORDER BY status"
            )
        }
        by_dataset = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT dataset_slug, status, COUNT(*) AS count
                FROM records
                GROUP BY dataset_slug, status
                ORDER BY dataset_slug, status
                """
            )
        ]
        attempts = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT attempt_number, status, COUNT(*) AS count
                FROM attempts
                GROUP BY attempt_number, status
                ORDER BY attempt_number, status
                """
            )
        ]
        return {
            "by_status": by_status,
            "by_dataset": by_dataset,
            "attempts": attempts,
        }
