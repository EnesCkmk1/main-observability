# ADR 0002: Content minimization in telemetry

## Status

Accepted

## Decision

`CAPTURE_MESSAGE_CONTENT=false` is the default. Session identifiers are hashed before they become span attributes, and secrets, authorization headers, and raw exception payloads are excluded from telemetry.

## Why

Observability should remain useful without turning traces into a copy of user conversations. Synthetic local content can be enabled deliberately for demonstrations, but it is never required for the core workflow.

## Trade-offs

Debugging a failed request may require reproducing it locally because the default trace intentionally omits message bodies.
