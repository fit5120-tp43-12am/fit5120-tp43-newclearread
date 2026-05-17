import asyncio
from typing import Any

import httpx

from app.config import Settings
from app.response_guard import GuardedSummary, ResponseGuardError, parse_summary


SYSTEM_PROMPT = """You are ClearRead, an accessibility-first reading support model.
Return only a strict JSON object with:
{"summary":"concise faithful summary","keyPoints":["useful point","useful point"]}
Rules:
- Use only information supported by the source text.
- Use plain English.
- Do not add citations, markdown, bullet markers, or explanations outside JSON.
- keyPoints should be an array of short, concrete points. The count can be dynamic.
"""


def build_user_prompt(text: str) -> str:
    return f"Summarize this source text for a reader.\n\nSOURCE TEXT:\n{text.strip()}"


class VllmClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.vllm_max_concurrency)
        self._client = httpx.AsyncClient(
            base_url=settings.vllm_base_url.rstrip("/"),
            timeout=settings.vllm_timeout_seconds,
            headers=self._headers(settings),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def ready(self) -> bool:
        try:
            response = await self._client.get("/v1/models")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def summarize_one(self, text: str) -> GuardedSummary:
        async with self._semaphore:
            raw = await self._chat(build_user_prompt(text))
            try:
                return parse_summary(raw)
            except ResponseGuardError:
                repair_raw = await self._chat(
                    "Repair the following content into the required strict JSON schema. "
                    "Return only JSON with summary and a keyPoints array. Do not force a fixed key point count.\n\n"
                    f"CONTENT:\n{raw}"
                )
                return parse_summary(repair_raw, action="retry_json_repair")

    async def _chat(self, user_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.vllm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.vllm_temperature,
            "max_tokens": self.settings.vllm_max_tokens,
        }
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

    @staticmethod
    def _headers(settings: Settings) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.vllm_api_key:
            headers["Authorization"] = f"Bearer {settings.vllm_api_key}"
        return headers
