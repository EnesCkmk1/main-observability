# ADR 0001: Local-first observability stack

## Status

Accepted

## Decision

The lab uses a local mock provider by default and exports telemetry through an OpenTelemetry Collector to Phoenix. Dynatrace is an explicit optional fan-out.

## Why

This keeps the default path reproducible, fast, and safe to run without credentials while preserving a production-shaped telemetry boundary. Provider and exporter changes remain configuration concerns rather than changes to assistant orchestration.

## Trade-offs

The mock provider does not measure real model quality or cost. The local lexical retriever is intentionally small. Production deployments would replace those components and use a durable metrics and evaluation backend.
