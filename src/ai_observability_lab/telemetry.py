"""Explicit allowlisted spans; no automatic HTTP/header or exception-content capture."""

from collections.abc import Iterator
from contextlib import contextmanager

from openinference.semconv.trace import SpanAttributes
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

from .config import Settings


class Telemetry:
    def __init__(self, settings: Settings, exporter: SpanExporter | None = None) -> None:
        self.provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": "ai-observability-lab",
                    "openinference.project.name": settings.phoenix_project_name,
                }
            )
        )
        if exporter is not None:
            self.provider.add_span_processor(BatchSpanProcessor(exporter))
        elif settings.telemetry_enabled:
            self.provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=settings.otel_exporter_otlp_traces_endpoint,
                        timeout=5,
                    )
                )
            )
        self.tracer = self.provider.get_tracer("ai_observability_lab", "0.1.0")

    @contextmanager
    def span(self, name: str, kind: str = "CHAIN", server: bool = False) -> Iterator[Span]:
        with self.tracer.start_as_current_span(
            name,
            kind=SpanKind.SERVER if server else SpanKind.INTERNAL,
            attributes={SpanAttributes.OPENINFERENCE_SPAN_KIND: kind},
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except Exception:
                span.set_status(Status(StatusCode.ERROR, "operation_failed"))
                span.set_attribute("response.status", "error")
                raise

    def flush(self) -> bool:
        return self.provider.force_flush(timeout_millis=10000)

    def close(self) -> None:
        self.provider.shutdown()
