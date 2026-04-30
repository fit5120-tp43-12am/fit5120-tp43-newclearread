from __future__ import annotations

from fastapi.testclient import TestClient

from ai_summary_service import ServiceSettings, create_app


API_KEY = "test-clearread-key"


def make_client(max_chars: int = 6000, max_body_bytes: int = 512 * 1024) -> TestClient:
    settings = ServiceSettings(
        api_key=API_KEY,
        runtime="mock",
        max_characters_per_text=max_chars,
        max_request_body_bytes=max_body_bytes,
        max_texts_per_request=32,
        request_timeout_seconds=5,
        enable_debug_responses=False,
    )
    return TestClient(create_app(settings=settings))


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def test_health_returns_liveness() -> None:
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "clearread-ai-summary"}


def test_ready_reports_ready_in_mock_mode() -> None:
    client = make_client()

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_missing_auth_returns_401() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        json={"texts": [{"id": "block-1", "text": "A valid block."}]},
    )

    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "unauthorized"


def test_invalid_auth_returns_401() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers={"Authorization": "Bearer wrong-key"},
        json={"texts": [{"id": "block-1", "text": "A valid block."}]},
    )

    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "unauthorized"


def test_one_valid_text_returns_one_successful_result() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={
            "requestId": "single-block",
            "texts": [{"id": "block-1", "text": "Photosynthesis helps plants make food."}],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["requestId"] == "single-block"
    assert body["status"] == "ok"
    assert len(body["results"]) == 1
    assert body["results"][0]["id"] == "block-1"
    assert body["results"][0]["status"] == "ok"
    assert isinstance(body["results"][0]["summary"], str)
    assert len(body["results"][0]["keyPoints"]) == 4
    assert "raw_output" not in body["results"][0]


def test_multiple_valid_texts_preserve_order() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={
            "texts": [
                {"id": "block-a", "text": "First valid block."},
                {"id": "block-b", "text": "Second valid block."},
                {"id": "block-c", "text": "Third valid block."},
            ]
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert [result["id"] for result in body["results"]] == [
        "block-a",
        "block-b",
        "block-c",
    ]


def test_duplicate_ids_return_whole_request_422() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={
            "texts": [
                {"id": "block-1", "text": "First valid block."},
                {"id": "block-1", "text": "Second valid block."},
            ]
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["results"] == []
    assert body["errors"][0]["code"] == "invalid_request"


def test_more_than_32_texts_return_whole_request_422() -> None:
    client = make_client()
    texts = [{"id": f"block-{index}", "text": "Valid block."} for index in range(33)]

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={"texts": texts},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "invalid_request"


def test_empty_text_returns_item_level_error() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={"texts": [{"id": "block-1", "text": "   "}]},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "error"
    assert body["results"][0]["status"] == "error"
    assert body["results"][0]["error"]["code"] == "empty_text"
    assert body["errors"] == []


def test_oversized_text_returns_item_level_error() -> None:
    client = make_client(max_chars=10)

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={"texts": [{"id": "block-1", "text": "This text is too long."}]},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "error"
    assert body["results"][0]["error"]["code"] == "text_too_large"


def test_oversized_request_body_returns_413() -> None:
    client = make_client(max_body_bytes=32)

    response = client.post(
        "/v1/clearread/summarize",
        headers={**auth_headers(), "Content-Type": "application/json"},
        content='{"texts":[{"id":"block-1","text":"This body is intentionally too large."}]}',
    )

    assert response.status_code == 413
    assert response.json()["errors"][0]["code"] == "request_body_too_large"


def test_partial_success_with_mock_schema_error() -> None:
    client = make_client()

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={
            "texts": [
                {"id": "block-1", "text": "A valid block."},
                {"id": "block-2", "text": "MOCK_SCHEMA_ERROR"},
            ]
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "partial_error"
    assert body["results"][0]["status"] == "ok"
    assert body["results"][1]["status"] == "error"
    assert body["results"][1]["error"]["code"] == "model_schema_error"


def test_normal_response_does_not_include_raw_source_text() -> None:
    client = make_client()
    source_text = "Unique private phrase 8f03c0 should not be echoed."

    response = client.post(
        "/v1/clearread/summarize",
        headers=auth_headers(),
        json={"texts": [{"id": "block-1", "text": source_text}]},
    )

    assert response.status_code == 200
    assert source_text not in response.text
    assert "8f03c0" not in response.text
