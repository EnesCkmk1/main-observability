import pytest
from pydantic import ValidationError

from ai_observability_lab.config import Settings


@pytest.mark.parametrize(
    "changes",
    [
        {"llm_provider": "openai", "openai_api_key": ""},
        {"judge_enabled": True, "openai_api_key": ""},
        {"dynatrace_enabled": True, "dynatrace_api_token": ""},
        {"retrieval_top_k": 0},
        {"provider_timeout_seconds": -1},
        {"input_cost_per_million": -1},
        {"phoenix_annotations_enabled": True, "telemetry_enabled": False},
        {"phoenix_endpoint": "file:///tmp/x"},
    ],
)
def test_invalid_configuration(changes):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **changes)


def test_secret_repr_redacts_and_defaults_are_private():
    settings = Settings(_env_file=None, openai_api_key="synthetic-not-a-real-key")
    assert "synthetic-not-a-real-key" not in repr(settings)
    assert settings.llm_provider == "mock"
    assert not settings.capture_message_content
