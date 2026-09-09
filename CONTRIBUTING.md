# Contributing

## Local workflow

```bash
make setup
make lint
make test
make eval
```

Use the mock provider for reproducible changes. Keep examples synthetic, preserve the privacy defaults, and add or update deterministic evaluation cases when behavior changes.

## Pull requests

Describe the user-visible behavior, telemetry impact, evaluation evidence, and any configuration changes. Keep commits focused. Changes that affect prompts, retrieval, guardrails, or providers should include the relevant regression coverage.
