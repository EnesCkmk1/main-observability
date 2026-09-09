# Prompt experiment report

Generated: 2026-09-09T15:23:27.259264+00:00

Provider: **mock**; 40 cases per version.
Dataset SHA-256: `ec42104f5f56ae70775dfceb1c4392d41af8e292af259fa648337d94a5da62b7`.

| Metric | v1 | v2 |
|---|---:|---:|
| answer_present | 1.0000 | 1.0000 |
| source_presence | 1.0000 | 1.0000 |
| valid_source_references | 1.0000 | 1.0000 |
| response_length | 1.0000 | 1.0000 |
| keyword_coverage | 1.0000 | 1.0000 |
| refusal_accuracy | 1.0000 | 1.0000 |
| guardrail_compliance | 1.0000 | 1.0000 |
| latency_threshold | 1.0000 | 1.0000 |
| retrieval_precision | 1.0000 | 1.0000 |
| correctness | 1.0000 | 1.0000 |
| groundedness | 1.0000 | 1.0000 |
| citation_accuracy | 0.5000 | 1.0000 |
| pass | 0.5000 | 1.0000 |
| p50_latency_ms | 0.3227 | 0.2682 |
| p95_latency_ms | 0.7201 | 0.6896 |
| total_tokens | 1693.0000 | 2653.0000 |
| estimated_cost_usd | 0.0000 | 0.0000 |

## Interpretation

v2 changes citation accuracy by +50.0% on this dataset. Inspect per-case evidence in experiment-results.json before accepting a change.

The mock copies a retrieved document and adds its citation when instructed by v2. This tests the experiment machinery and citation contract; it is not evidence that v2 improves a real LLM. Groundedness is lexical overlap, correctness is expected behavior plus keyword coverage. Neither is a semantic quality guarantee. Refusal and guardrail behavior are application rules shared by both prompt versions.

Mock tokens are whitespace-based estimates, and mock cost is zero. Real-provider cost is unknown unless both per-million token rates are configured. Latencies are actual local measurements and vary between runs; no external-model benchmark is claimed.

## Regression gate

v2 failing thresholds/cases: none.

Thresholds apply to v2 only: correctness >=95%, groundedness proxy >=90%, citation accuracy >=95%, refusal accuracy and guardrail compliance =100%, overall pass rate >=90%. All sensitive/injection cases must individually pass.
