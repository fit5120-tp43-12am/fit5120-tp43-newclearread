from __future__ import annotations

import io
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from fastapi.testclient import TestClient

from ai_summary_service import ServiceSettings, create_app


API_KEY = "test-clearread-key"
VLLM_API_KEY = "test-vllm-key"
DEFAULT_MAX_CHARS = 11000


class FakeVLLMServer:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.auth_headers: list[str | None] = []
        handler = self._handler()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeVLLMServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/v1/models":
                    if not self._authorized():
                        self._send_json(401, {"error": "unauthorized"})
                        return
                    self._send_json(200, {"data": [{"id": "clearread-test"}]})
                    return
                self._send_json(404, {"error": "not found"})

            def do_POST(self) -> None:
                if self.path != "/v1/chat/completions":
                    self._send_json(404, {"error": "not found"})
                    return
                if not self._authorized():
                    self._send_json(401, {"error": "unauthorized"})
                    return

                length = int(self.headers.get("content-length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                outer.requests.append(payload)

                user_text = self._user_text(payload)
                if "HTTP_FAIL" in user_text:
                    self._send_json(503, {"error": "backend unavailable"})
                    return
                if "SCHEMA_FAIL" in user_text:
                    content = json.dumps(
                        {
                            "main_idea": "This output is incomplete. It should fail.",
                            "key_points": ["Only one point."],
                        }
                    )
                else:
                    marker = user_text.split()[0] if user_text.split() else "block"
                    content = json.dumps(
                        {
                            "main_idea": f"{marker} was summarized by the fake vLLM backend. The response is valid ClearRead wrapper JSON.",
                            "key_points": [
                                f"{marker} has a first key point.",
                                f"{marker} has a second key point.",
                                f"{marker} has a third key point.",
                                f"{marker} has a fourth key point.",
                            ],
                        }
                    )

                self._send_json(
                    200,
                    {"choices": [{"message": {"role": "assistant", "content": content}}]},
                )

            def log_message(self, format: str, *args: object) -> None:
                return

            def _authorized(self) -> bool:
                authorization = self.headers.get("authorization")
                outer.auth_headers.append(authorization)
                return authorization == f"Bearer {VLLM_API_KEY}"

            def _user_text(self, payload: dict[str, Any]) -> str:
                messages = payload.get("messages", [])
                for message in messages:
                    if isinstance(message, dict) and message.get("role") == "user":
                        content = message.get("content")
                        return content if isinstance(content, str) else ""
                return ""

            def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler


def make_client(fake_vllm: FakeVLLMServer, logger: logging.Logger | None = None) -> TestClient:
    settings = ServiceSettings(
        api_key=API_KEY,
        runtime="vllm_http",
        max_texts_per_request=32,
        max_characters_per_text=DEFAULT_MAX_CHARS,
        request_timeout_seconds=5,
        enable_debug_responses=False,
        vllm_base_url=fake_vllm.url,
        vllm_api_key=VLLM_API_KEY,
        vllm_model="clearread-test",
        vllm_internal_concurrency=4,
        vllm_request_timeout_seconds=2,
        vllm_schema_retry_attempts=0,
    )
    app = create_app(settings=settings)
    if logger is not None:
        app.state.logger = logger
    return TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def test_vllm_runtime_one_block_success() -> None:
    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm)

        response = client.post(
            "/v1/clearread/summarize",
            headers=auth_headers(),
            json={"texts": [{"id": "block-1", "text": "Alpha source text."}]},
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "ok"
        assert body["results"][0]["id"] == "block-1"
        assert body["results"][0]["status"] == "ok"
        assert len(body["results"][0]["keyPoints"]) == 4
        assert "main_idea" not in response.text
        assert fake_vllm.requests[0]["model"] == "clearread-test"
        assert f"Bearer {VLLM_API_KEY}" in fake_vllm.auth_headers


def test_vllm_runtime_multi_block_success_preserves_order() -> None:
    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm)

        response = client.post(
            "/v1/clearread/summarize",
            headers=auth_headers(),
            json={
                "texts": [
                    {"id": "block-a", "text": "Alpha source text."},
                    {"id": "block-b", "text": "Beta source text."},
                    {"id": "block-c", "text": "Gamma source text."},
                ]
            },
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "ok"
        assert [result["id"] for result in body["results"]] == [
            "block-a",
            "block-b",
            "block-c",
        ]
        assert len(fake_vllm.requests) == 3


def test_vllm_runtime_partial_schema_failure_returns_item_error() -> None:
    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm)

        response = client.post(
            "/v1/clearread/summarize",
            headers=auth_headers(),
            json={
                "texts": [
                    {"id": "block-1", "text": "Alpha source text."},
                    {"id": "block-2", "text": "SCHEMA_FAIL source text."},
                ]
            },
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "partial_error"
        assert body["results"][0]["status"] == "ok"
        assert body["results"][1]["status"] == "error"
        assert body["results"][1]["summary"] == ""
        assert body["results"][1]["keyPoints"] == []
        assert body["results"][1]["schemaGuardAction"] == "return_error_object"
        assert body["results"][1]["error"]["code"] == "model_schema_error"
        assert "Only one point" not in response.text
        assert len(fake_vllm.requests) == 2


def test_vllm_http_failure_returns_safe_retryable_item_error() -> None:
    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm)

        response = client.post(
            "/v1/clearread/summarize",
            headers=auth_headers(),
            json={"texts": [{"id": "block-1", "text": "HTTP_FAIL source text."}]},
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "error"
        assert body["results"][0]["status"] == "error"
        assert body["results"][0]["error"] == {
            "code": "model_runtime_error",
            "message": "The model runtime failed while processing this item.",
            "retryable": True,
        }
        assert "backend unavailable" not in response.text
        assert len(fake_vllm.requests) == 1


def test_docs_and_openapi_remain_disabled_in_vllm_mode() -> None:
    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm)

        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_whole_request_error_logging_uses_safe_metadata_only() -> None:
    stream = io.StringIO()
    logger = logging.getLogger("clearread.test.safe-whole-error")
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stream))
    private_text = "Private phrase 379f30 must not appear in logs."

    with FakeVLLMServer() as fake_vllm:
        client = make_client(fake_vllm, logger)

        response = client.post(
            "/v1/clearread/summarize",
            headers=auth_headers(),
            json={
                "texts": [
                    {"id": "block-1", "text": private_text},
                    {"id": "block-1", "text": private_text},
                ]
            },
        )

    log_output = stream.getvalue()
    assert response.status_code == 422
    assert "invalid_request" in log_output
    assert "block-1" in log_output
    assert str(len(private_text)) in log_output
    assert private_text not in log_output
    assert "379f30" not in log_output
    assert API_KEY not in log_output
