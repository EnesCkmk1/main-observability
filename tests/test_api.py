from fastapi.testclient import TestClient

from ai_observability_lab.api import create_app
from ai_observability_lab.assistant import Assistant
from ai_observability_lab.providers import MockProvider
from ai_observability_lab.telemetry import Telemetry


def test_api_round_trip(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json()["status"] == "ok"
        response = client.post("/chat", json={"question": "How do I reset my business password?"})
        assert response.status_code == 200
        body = response.json()
        assert len(body["trace_id"]) == 32 and int(body["trace_id"], 16) > 0
        assert body["sources"][0]["id"] == "password-reset"
        assert client.post("/evaluate", json={"dataset_id": "normal-01"}).json()["passed"]
        assert client.get("/metrics-summary").json()["request_count"] == 2
        assert client.post("/evaluate", json={"dataset_id": "missing"}).status_code == 404
        for payload in (
            {"question": ""},
            {"question": "   "},
            {"question": "hi", "prompt_version": "v3"},
        ):
            assert client.post("/chat", json=payload).status_code == 422


def test_provider_error_is_sanitized_and_counted(settings):
    for scenario, status in [("timeout", 504), ("error", 502)]:
        service = Assistant(settings, Telemetry(settings), MockProvider(scenario))
        with TestClient(create_app(settings, service)) as client:
            response = client.post("/chat", json={"question": "reset business password"})
            assert response.status_code == status
            assert response.json()["detail"].startswith("provider_")
            summary = client.get("/metrics-summary").json()
            assert summary["error_rate"] == 1
            assert summary["request_count"] == 1
