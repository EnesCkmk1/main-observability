"""Validated configuration; secrets never appear in configuration repr."""

from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-5.5"
    provider_timeout_seconds: float = Field(default=15, gt=0, le=120)
    capture_message_content: bool = False
    telemetry_enabled: bool = False
    otel_exporter_otlp_traces_endpoint: str = "http://localhost:4318/v1/traces"
    phoenix_endpoint: str = "http://localhost:6006"
    phoenix_project_name: str = "banking-assistant-observability"
    phoenix_annotations_enabled: bool = False
    dynatrace_enabled: bool = False
    dynatrace_otlp_endpoint: str = ""
    dynatrace_api_token: SecretStr = SecretStr("")
    judge_enabled: bool = False
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    retrieval_top_k: int = Field(default=2, ge=1, le=5)
    retrieval_backend: Literal["lexical", "vector"] = "lexical"
    metrics_window: int = Field(default=10000, ge=10, le=100000)

    @model_validator(mode="after")
    def validate_integrations(self) -> Self:
        if (self.llm_provider == "openai" or self.judge_enabled) and not (
            self.openai_api_key.get_secret_value()
        ):
            raise ValueError("OpenAI provider/judge requires OPENAI_API_KEY")
        if self.dynatrace_enabled and (
            not self.dynatrace_api_token.get_secret_value()
            or not self.dynatrace_otlp_endpoint.startswith("https://")
        ):
            raise ValueError("Dynatrace requires an HTTPS endpoint and API token")
        if self.phoenix_annotations_enabled and not self.telemetry_enabled:
            raise ValueError("Phoenix annotations require telemetry_enabled")
        for endpoint in (self.otel_exporter_otlp_traces_endpoint, self.phoenix_endpoint):
            parsed = urlparse(endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
                raise ValueError(
                    "Telemetry endpoints must be HTTP(S), without embedded credentials"
                )
        return self
