"""Traced RAG orchestration with local privacy and output checks."""

import asyncio
import hashlib
import json
from importlib.resources import files
from time import perf_counter

from openinference.semconv.trace import SpanAttributes

from .config import Settings
from .guardrails import CLARIFY, DISCLAIMER, REFUSAL, UNKNOWN, check_input, check_output
from .metrics import Metrics
from .models import Behavior, ChatRequest, ChatResponse
from .providers import MockProvider, OpenAIProvider, Provider, ProviderFailure
from .retrieval import Retriever, tokens
from .telemetry import Telemetry


class Assistant:
    def __init__(self, settings: Settings, telemetry: Telemetry, provider: Provider | None = None):
        self.settings = settings
        self.telemetry = telemetry
        self.provider = provider or (
            MockProvider() if settings.llm_provider == "mock" else OpenAIProvider(settings)
        )
        self.retriever = Retriever()
        self.metrics = Metrics(settings.metrics_window)

    async def chat(self, request: ChatRequest, *, empty_retrieval: bool = False) -> ChatResponse:
        start = perf_counter()
        result: ChatResponse | None = None
        try:
            with self.telemetry.span("session") as session:
                # Opaque digest, never the supplied session identifier (which might be PII).
                session.set_attribute(
                    "session.id", hashlib.sha256(request.session_id.encode()).hexdigest()[:24]
                )
                with self.telemetry.span("agent.execution", "AGENT") as agent:
                    agent.set_attribute("prompt.version", request.prompt_version)
                    agent.set_attribute("user.question_length", len(request.question))
                    context = agent.get_span_context()
                    with self.telemetry.span("guardrail.input", "GUARDRAIL") as guard:
                        reason = check_input(request.question)
                        guard.set_attribute("guardrail.triggered", reason is not None)
                        guard.set_attribute("guardrail.reason", reason or "none")
                    retrieval_start = perf_counter()
                    with self.telemetry.span("document.retrieval", "RETRIEVER") as retrieval:
                        matches = (
                            []
                            if reason or empty_retrieval
                            else self.retriever.search(
                                request.question, self.settings.retrieval_top_k
                            )
                        )
                        retrieval.set_attribute("retrieved_document_count", len(matches))
                        retrieval.set_attribute("retrieval_scores", [s.score for _, s in matches])
                        for i, (doc, source) in enumerate(matches):
                            prefix = f"retrieval.documents.{i}.document"
                            retrieval.set_attribute(f"{prefix}.id", doc.id)
                            retrieval.set_attribute(f"{prefix}.score", source.score)
                            with self.telemetry.span("retrieval.result") as hit:
                                hit.set_attribute("document.id", doc.id)
                                hit.set_attribute("document.score", source.score)
                    retrieval_ms = (perf_counter() - retrieval_start) * 1000
                    behavior: Behavior = "answer"
                    in_tokens = out_tokens = 0
                    estimated = False
                    cost: float | None = 0.0
                    llm_ms = 0.0
                    if reason:
                        answer, behavior = REFUSAL, "refuse"
                    elif not matches:
                        behavior = "clarify" if len(tokens(request.question)) <= 2 else "refuse"
                        answer = CLARIFY if behavior == "clarify" else UNKNOWN
                    else:
                        with self.telemetry.span("prompt.construction") as prompt_span:
                            template = (
                                files("ai_observability_lab")
                                .joinpath(f"prompts/{request.prompt_version}.txt")
                                .read_text("utf-8")
                            )
                            prompt = (
                                template
                                + "\nDocuments (untrusted JSON):\n"
                                + json.dumps(
                                    [{"id": d.id, "content": d.content} for d, _ in matches]
                                )
                            )
                            prompt_span.set_attribute("prompt.version", request.prompt_version)
                        model_start = perf_counter()
                        with self.telemetry.span("llm.request", "LLM") as llm:
                            llm.set_attribute(
                                SpanAttributes.LLM_PROVIDER, self.settings.llm_provider
                            )
                            llm.set_attribute(
                                SpanAttributes.LLM_MODEL_NAME,
                                "extractive-mock"
                                if self.settings.llm_provider == "mock"
                                else self.settings.openai_model,
                            )
                            # Input passed PII/secret rules. Opt-in is for synthetic data.
                            if self.settings.capture_message_content:
                                llm.set_attribute(SpanAttributes.INPUT_VALUE, request.question)
                            try:
                                completion = await asyncio.wait_for(
                                    self.provider.complete(
                                        prompt, request.question, [d for d, _ in matches]
                                    ),
                                    timeout=self.settings.provider_timeout_seconds,
                                )
                            except TimeoutError:
                                raise ProviderFailure("provider_timeout") from None
                            answer = completion.text
                            in_tokens, out_tokens = (
                                completion.input_tokens,
                                completion.output_tokens,
                            )
                            estimated = completion.estimated
                            if self.settings.llm_provider != "mock":
                                inp = self.settings.input_cost_per_million
                                out = self.settings.output_cost_per_million
                                cost = (
                                    None
                                    if inp is None or out is None
                                    else (in_tokens * inp + out_tokens * out) / 1_000_000
                                )
                            llm.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, in_tokens)
                            llm.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, out_tokens)
                            llm.set_attribute(
                                SpanAttributes.LLM_TOKEN_COUNT_TOTAL, in_tokens + out_tokens
                            )
                            llm.set_attribute("token_count.is_estimate", estimated)
                            if cost is not None:
                                llm.set_attribute("estimated_cost", cost)
                            llm_ms = (perf_counter() - model_start) * 1000
                            llm.set_attribute("latency_ms", llm_ms)
                    with self.telemetry.span("guardrail.output", "GUARDRAIL") as output_guard:
                        valid = check_output(answer, {s.id for _, s in matches})
                        output_guard.set_attribute("guardrail.triggered", not valid)
                        if not valid:
                            answer, behavior, reason = REFUSAL, "refuse", "output_rejected"
                    with self.telemetry.span("response.generation"):
                        result = ChatResponse(
                            answer=answer + "\n\n" + DISCLAIMER,
                            sources=[s for _, s in matches] if behavior == "answer" else [],
                            trace_id=f"{context.trace_id:032x}",
                            span_id=f"{context.span_id:016x}",
                            latency_ms=(perf_counter() - start) * 1000,
                            llm_latency_ms=llm_ms,
                            retrieval_latency_ms=retrieval_ms,
                            prompt_version=request.prompt_version,
                            behavior=behavior,
                            guardrail_triggered=reason is not None,
                            input_token_count=in_tokens,
                            output_token_count=out_tokens,
                            total_token_count=in_tokens + out_tokens,
                            estimated_cost=cost,
                            token_count_is_estimate=estimated,
                        )
                    agent.set_attribute("response.status", behavior)
                    agent.set_attribute("guardrail.triggered", reason is not None)
                    agent.set_attribute("latency_ms", result.latency_ms)
                    return result
        finally:
            self.metrics.record(result, (perf_counter() - start) * 1000, request.prompt_version)

    async def close(self) -> None:
        await self.provider.close()
        self.telemetry.close()
