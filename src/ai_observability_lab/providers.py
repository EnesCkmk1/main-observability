"""Swappable providers; the mock is an extractive simulator, not a language model."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

from openai import AsyncOpenAI

from .config import Settings
from .models import Document


class ProviderFailure(Exception):
    """Sanitized provider failure, safe to expose in telemetry."""


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    estimated: bool = False


class Provider(Protocol):
    async def complete(self, prompt: str, question: str, docs: list[Document]) -> Completion: ...
    async def close(self) -> None: ...


class MockProvider:
    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario

    async def complete(self, prompt: str, question: str, docs: list[Document]) -> Completion:
        if self.scenario == "slow":
            await asyncio.sleep(3.1)
        if self.scenario == "timeout":
            raise TimeoutError("provider_timeout")
        if self.scenario == "error":
            raise ProviderFailure("provider_error")
        answer = docs[0].content
        # Mimics instruction-following only. No dataset IDs or expected labels are available here.
        if "square brackets" in prompt:
            answer += f" [{docs[0].id}]"
        if self.scenario == "hallucination":
            answer = "Every account earns a guaranteed 40 percent annual return."
        if self.scenario == "invalid_citation":
            answer += " [nonexistent-policy]"
        return Completion(answer, len((prompt + question).split()), len(answer.split()), True)

    async def close(self) -> None:
        pass


class OpenAIProvider:
    def __init__(self, settings: Settings) -> None:
        self.model = settings.openai_model
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.provider_timeout_seconds,
            max_retries=0,
        )

    async def complete(self, prompt: str, question: str, docs: list[Document]) -> Completion:
        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=prompt,
                input=question,
                max_output_tokens=600,
                store=False,
            )
            usage = response.usage
            if usage is None:
                raise ProviderFailure("provider_usage_missing")
            return Completion(response.output_text, usage.input_tokens, usage.output_tokens)
        except Exception as exc:
            # Do not attach SDK exceptions: they can contain request bodies and credentials.
            name = (
                "provider_timeout" if "timeout" in type(exc).__name__.lower() else "provider_error"
            )
            raise ProviderFailure(name) from None

    async def close(self) -> None:
        await self.client.close()
