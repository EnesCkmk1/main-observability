# Production-readiness notes

This repository is a portfolio lab, but its operational decisions are explicit.

## Reliability

- Provider calls use a bounded timeout from `PROVIDER_TIMEOUT_SECONDS`.
- The Collector uses bounded retry, batching, a memory limiter, and a bounded queue.
- Provider failures are sanitized before they reach the API response or trace.
- The demo has no implicit network dependency because the mock provider is the default.

## Traffic and cost controls

The sample app is intentionally single-process. A production deployment should put rate limiting and authentication at the edge, cap request size and retrieval `top_k`, and enforce per-tenant budgets. Input and output token counts are recorded when available; cost is reported as unknown when pricing is not configured.

## Privacy and model risk

Message content capture is opt-in and intended only for synthetic data. Session identifiers are hashed. The retrieval corpus and evaluation set are fictional. Deterministic groundedness and correctness scores are useful regression signals, not proof of factual accuracy; high-risk use cases require human review and a domain-approved evaluation set.

## Scaling and SLOs

The in-process metrics window is suitable for a demo and one process. Production deployments should export metrics to a shared backend, define availability and latency SLOs, and alert on guardrail violations, provider errors, trace export failures, and evaluation regressions. A practical starting point is availability >=99%, p95 latency <3 seconds, groundedness >=90%, and citation accuracy >=95%.

## Incident flow

1. Confirm impact with API health, request error rate, latency, and provider telemetry.
2. Check the trace for guardrail, retrieval, provider, and exporter failures.
3. Disable the affected provider or prompt version through configuration if needed.
4. Reproduce with the version-controlled evaluation cases, fix, and verify the regression gate before rollout.
