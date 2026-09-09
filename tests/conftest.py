import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ai_observability_lab.assistant import Assistant
from ai_observability_lab.config import Settings
from ai_observability_lab.telemetry import Telemetry


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        llm_provider="mock",
        telemetry_enabled=False,
        phoenix_annotations_enabled=False,
        judge_enabled=False,
        dynatrace_enabled=False,
    )


@pytest.fixture
def exporter():
    return InMemorySpanExporter()


@pytest.fixture
async def assistant(settings, exporter):
    service = Assistant(settings, Telemetry(settings, exporter))
    yield service
    await service.close()
