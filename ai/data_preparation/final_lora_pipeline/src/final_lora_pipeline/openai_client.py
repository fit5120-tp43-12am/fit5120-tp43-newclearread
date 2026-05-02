from __future__ import annotations

import json
import random
import time
from typing import Any, Dict, List, Optional

from .models import ApiCallResult, ApiConfig


_NON_RETRYABLE_OPENAI_ERRORS = {
    "AuthenticationError",
    "BadRequestError",
    "NotFoundError",
    "PermissionDeniedError",
}


def _to_plain(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


class OpenAIResponsesClient:
    def __init__(self, api_config: ApiConfig) -> None:
        if api_config.provider != "openai":
            raise ValueError(f"Unsupported provider for v1 pipeline: {api_config.provider}")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is required for API runs. Install with: python -m pip install -r requirements.txt"
            ) from exc

        self.api_config = api_config
        self.client = OpenAI(timeout=api_config.request_timeout_seconds)

    def generate_label(
        self,
        model: str,
        system_prompt: str,
        source_text: str,
        assistant_schema: Dict[str, Any],
    ) -> ApiCallResult:
        return self._create_response(
            model=model,
            input_messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": source_text},
            ],
            schema=assistant_schema,
            schema_name="assistant_label",
            max_output_tokens=self.api_config.generation_max_output_tokens,
            reasoning_effort=self.api_config.generation_reasoning_effort,
        )

    def judge_label(
        self,
        model: str,
        system_prompt: str,
        source_text: str,
        candidate_label: Dict[str, Any],
        judge_schema: Dict[str, Any],
        domain_hint: str,
    ) -> ApiCallResult:
        judge_payload = {
            "source_domain_hint": domain_hint,
            "structural_gate": {
                "accepted": True,
                "stage": "stage_2",
            },
            "source_text": source_text,
            "candidate_label": candidate_label,
        }
        return self._create_response(
            model=model,
            input_messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(judge_payload, ensure_ascii=False)},
            ],
            schema=judge_schema,
            schema_name="judge_result",
            max_output_tokens=self.api_config.judge_max_output_tokens,
            reasoning_effort=self.api_config.judge_reasoning_effort,
        )

    def _create_response(
        self,
        model: str,
        input_messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        schema_name: str,
        max_output_tokens: int,
        reasoning_effort: Optional[str],
    ) -> ApiCallResult:
        request: Dict[str, Any] = {
            "model": model,
            "input": input_messages,
            "max_output_tokens": max_output_tokens,
        }

        text_config: Dict[str, Any] = {}
        if self.api_config.use_structured_outputs:
            text_config["format"] = {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        if self.api_config.text_verbosity:
            text_config["verbosity"] = self.api_config.text_verbosity
        if text_config:
            request["text"] = text_config
        if reasoning_effort:
            request["reasoning"] = {"effort": reasoning_effort}

        response = self._call_with_retries(request)
        incomplete_details = getattr(response, "incomplete_details", None)
        raw_metadata = {
            "id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
            "model": getattr(response, "model", model),
        }
        if incomplete_details is not None:
            raw_metadata["incomplete_details"] = _to_plain(incomplete_details)
        return ApiCallResult(
            text=self._extract_output_text(response),
            response_id=getattr(response, "id", None),
            model=model,
            usage=_to_plain(getattr(response, "usage", None)),
            raw_metadata=raw_metadata,
        )

    def _call_with_retries(self, request: Dict[str, Any]) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.api_config.max_api_retries + 1):
            try:
                return self.client.responses.create(**request)
            except Exception as exc:  # OpenAI SDK exception classes vary by installed version.
                if exc.__class__.__name__ in _NON_RETRYABLE_OPENAI_ERRORS:
                    raise
                last_exc = exc
                if attempt >= self.api_config.max_api_retries:
                    break
                delay = min(
                    self.api_config.backoff_max_seconds,
                    self.api_config.backoff_base_seconds * (2 ** (attempt - 1)),
                )
                time.sleep(delay + random.random())
        assert last_exc is not None
        raise last_exc

    def _extract_output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        chunks: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
        if chunks:
            return "".join(chunks)

        if getattr(response, "status", None) == "incomplete" or getattr(response, "incomplete_details", None):
            return ""

        plain = _to_plain(response)
        return json.dumps(plain, ensure_ascii=False)
