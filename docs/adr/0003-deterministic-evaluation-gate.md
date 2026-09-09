# ADR 0003: Deterministic evaluation gate

## Status

Accepted

## Decision

CI uses version-controlled JSONL cases and deterministic evaluators as the merge gate. An optional LLM judge is available for richer analysis but is not required for a green build.

## Why

Deterministic checks make regressions reproducible, cheap, and reviewable. The dataset covers normal, ambiguous, unanswerable, sensitive, and prompt-injection behavior.

## Trade-offs

Lexical correctness and groundedness are proxies. They complement human review and model-based judging; they do not establish semantic truth.
