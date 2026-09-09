"""API and dataset contracts."""

from typing import Literal

from pydantic import BaseModel, Field

PromptVersion = Literal["v1", "v2"]
Behavior = Literal["answer", "clarify", "refuse"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    session_id: str = Field(default="demo-session", min_length=1, max_length=128)
    prompt_version: PromptVersion = "v2"


class Document(BaseModel):
    id: str
    title: str
    content: str
    keywords: list[str]


class Source(BaseModel):
    id: str
    title: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    trace_id: str
    span_id: str
    latency_ms: float
    llm_latency_ms: float = 0
    retrieval_latency_ms: float = 0
    prompt_version: PromptVersion
    behavior: Behavior
    guardrail_triggered: bool
    input_token_count: int = 0
    output_token_count: int = 0
    total_token_count: int = 0
    estimated_cost: float | None = None
    token_count_is_estimate: bool = False


class DatasetItem(BaseModel):
    id: str
    category: Literal["normal", "ambiguous", "unanswerable", "sensitive", "injection"]
    question: str
    expected_document_ids: list[str]
    expected_behavior: Behavior
    important_keywords: list[str]
    refusal_expected: bool


class EvaluationRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=100)
    prompt_version: PromptVersion = "v2"


class EvaluationResult(BaseModel):
    dataset_id: str
    response: ChatResponse
    scores: dict[str, float]
    passed: bool
    annotation_status: Literal["disabled", "uploaded", "failed"] = "disabled"
