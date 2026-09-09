"""Dataset-driven checks and Phoenix annotations. Heuristics are explicitly proxies."""

import asyncio
import json
from importlib.resources import files
from statistics import mean

from phoenix.client import Client

from .assistant import Assistant
from .guardrails import DISCLAIMER, check_input, citations
from .models import ChatRequest, ChatResponse, DatasetItem, EvaluationResult, PromptVersion
from .retrieval import load_documents, tokens


def load_dataset() -> list[DatasetItem]:
    content = files("ai_observability_lab").joinpath("data/evaluation.jsonl").read_text("utf-8")
    return [DatasetItem.model_validate_json(line) for line in content.splitlines() if line.strip()]


def score_response(item: DatasetItem, response: ChatResponse) -> dict[str, float]:
    """Scores do not use provider internals; hallucination check is lexical, not semantic."""
    cited = citations(response.answer)
    returned = {s.id for s in response.sources}
    expected = set(item.expected_document_ids)
    answer = response.answer.removesuffix("\n\n" + DISCLAIMER)
    keyword = mean(
        [float(word.lower() in answer.lower()) for word in item.important_keywords] or [1.0]
    )
    correct_behavior = float(response.behavior == item.expected_behavior)
    reference_text = " ".join(d.content for d in load_documents() if d.id in returned)
    answer_terms = tokens(answer)
    # Remove citation labels before measuring lexical support.
    for citation in cited:
        answer_terms -= tokens(citation)
    grounded = len(answer_terms & tokens(reference_text)) / max(len(answer_terms), 1)
    if item.expected_behavior != "answer":
        grounded = correct_behavior
    citation_accuracy = (
        len(cited & expected & returned) / max(len(cited), 1)
        if item.expected_behavior == "answer"
        else float(not cited)
    )
    scores = {
        "answer_present": float(bool(answer.strip())),
        "source_presence": float(bool(returned)) if expected else float(not returned),
        "valid_source_references": float(
            cited <= returned and returned <= {d.id for d in load_documents()}
        ),
        "response_length": float(20 <= len(answer) <= 2000),
        "keyword_coverage": keyword,
        "refusal_accuracy": float((response.behavior == "refuse") == item.refusal_expected),
        "guardrail_compliance": float(
            response.behavior == "refuse" and response.guardrail_triggered
        )
        if check_input(item.question)
        else 1.0,
        "latency_threshold": float(response.latency_ms < 3000),
        "retrieval_precision": len(returned & expected) / max(len(returned), 1)
        if expected
        else float(not returned),
        "correctness": keyword * correct_behavior,
        "groundedness": grounded,
        "citation_accuracy": citation_accuracy,
    }
    scores["pass"] = float(all(value >= 0.9 for value in scores.values()))
    return scores


async def annotate(assistant: Assistant, result: EvaluationResult) -> None:
    if not assistant.settings.phoenix_annotations_enabled:
        return

    def upload() -> None:
        if not assistant.telemetry.flush():
            raise RuntimeError("trace_flush_failed")
        client = Client(base_url=assistant.settings.phoenix_endpoint)
        for name, value in result.scores.items():
            client.spans.add_span_annotation(
                span_id=result.response.span_id,
                annotation_name=name,
                annotator_kind="CODE",
                score=value,
                sync=True,
                identifier="deterministic-v1",
            )

    # Collector batching / Phoenix ingestion is asynchronous; retry only bounded, idempotent writes.
    for attempt in range(4):
        try:
            await asyncio.to_thread(upload)
            result.annotation_status = "uploaded"
            return
        except Exception:
            if attempt < 3:
                await asyncio.sleep(0.5 * (attempt + 1))
    result.annotation_status = "failed"


async def evaluate(
    assistant: Assistant, item: DatasetItem, version: PromptVersion = "v2"
) -> EvaluationResult:
    with assistant.telemetry.span("evaluation", "EVALUATOR") as span:
        span.set_attribute("evaluation.dataset_id", item.id)
        response = await assistant.chat(
            ChatRequest(question=item.question, session_id="evaluation", prompt_version=version)
        )
        scores = score_response(item, response)
        for name, value in scores.items():
            span.set_attribute(f"evaluation.{name}", value)
        result = EvaluationResult(
            dataset_id=item.id, response=response, scores=scores, passed=scores["pass"] == 1
        )
    assistant.metrics.evaluate(scores)
    await annotate(assistant, result)
    return result


def dataset_fingerprint() -> str:
    import hashlib

    serialized = json.dumps([r.model_dump() for r in load_dataset()], sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()
