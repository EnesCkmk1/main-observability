"""Bounded per-process metrics. Summaries describe the retained rolling window."""

from collections import Counter, deque
from math import ceil
from statistics import mean
from threading import Lock
from typing import Any

from .models import ChatResponse


def percentile(values: list[float], quantile: float) -> float:
    return sorted(values)[max(0, ceil(len(values) * quantile) - 1)] if values else 0


class Metrics:
    def __init__(self, window: int) -> None:
        self.rows: deque[dict[str, Any]] = deque(maxlen=window)
        self.evaluations: deque[dict[str, float]] = deque(maxlen=window)
        self.lock = Lock()

    def record(self, response: ChatResponse | None, latency: float, version: str) -> None:
        with self.lock:
            self.rows.append({"response": response, "latency": latency, "version": version})

    def evaluate(self, scores: dict[str, float]) -> None:
        with self.lock:
            self.evaluations.append(scores)

    def summary(self) -> dict[str, Any]:
        with self.lock:
            rows, evaluations = list(self.rows), list(self.evaluations)
        responses = [row["response"] for row in rows if row["response"] is not None]
        costs = [r.estimated_cost for r in responses]
        return {
            "scope": "per-process rolling window, chat attempts including evaluation runs",
            "request_count": len(rows),
            "error_rate": (len(rows) - len(responses)) / max(len(rows), 1),
            "p50_latency_ms": percentile([r["latency"] for r in rows], 0.5),
            "p95_latency_ms": percentile([r["latency"] for r in rows], 0.95),
            "mean_llm_latency_ms": mean([r.llm_latency_ms for r in responses] or [0]),
            "mean_retrieval_latency_ms": mean([r.retrieval_latency_ms for r in responses] or [0]),
            "total_tokens": sum(r.total_token_count for r in responses),
            "estimated_cost_usd": sum(costs) if all(c is not None for c in costs) else None,
            "guardrail_trigger_count": sum(r.guardrail_triggered for r in responses),
            "requests_by_prompt_version": dict(Counter(r["version"] for r in rows)),
            "evaluation_count": len(evaluations),
            "evaluation_pass_rate": mean([s["pass"] for s in evaluations]) if evaluations else None,
            "groundedness_proxy": mean([s["groundedness"] for s in evaluations])
            if evaluations
            else None,
            "citation_accuracy": mean([s["citation_accuracy"] for s in evaluations])
            if evaluations
            else None,
        }
