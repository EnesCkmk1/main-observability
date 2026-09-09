import json

import pytest

from ai_observability_lab.models import ChatRequest
from ai_observability_lab.providers import MockProvider, ProviderFailure


async def test_span_tree_and_privacy(assistant, exporter):
    response = await assistant.chat(
        ChatRequest(question="reset business password", session_id="customer@example.com")
    )
    assistant.telemetry.flush()
    spans = exporter.get_finished_spans()
    names = {s.name for s in spans}
    assert {
        "session",
        "agent.execution",
        "document.retrieval",
        "retrieval.result",
        "prompt.construction",
        "llm.request",
        "guardrail.input",
        "guardrail.output",
        "response.generation",
    } <= names
    assert {f"{s.context.trace_id:032x}" for s in spans} == {response.trace_id}
    encoded = json.dumps([dict(s.attributes) for s in spans])
    assert "customer@example.com" not in encoded
    assert "reset business password" not in encoded
    assert "input.value" not in encoded
    llm = next(s for s in spans if s.name == "llm.request")
    assert llm.attributes["openinference.span.kind"] == "LLM"
    assert llm.attributes["llm.token_count.total"] > 0
    assert all(s.parent is not None for s in spans if s.name != "session")


async def test_failed_span_never_records_exception_content(assistant, exporter):
    assistant.provider = MockProvider("error")
    with pytest.raises(ProviderFailure):
        await assistant.chat(ChatRequest(question="reset business password"))
    assistant.telemetry.flush()
    spans = exporter.get_finished_spans()
    assert any(s.status.is_ok is False for s in spans)
    assert all(not s.events for s in spans)


async def test_sensitive_input_is_not_captured_even_opted_in(assistant, exporter):
    assistant.settings.capture_message_content = True
    response = await assistant.chat(ChatRequest(question="My email is customer@example.com"))
    assistant.telemetry.flush()
    assert response.guardrail_triggered
    assert "customer@example.com" not in str([s.attributes for s in exporter.get_finished_spans()])
