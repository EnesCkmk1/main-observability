"""FastAPI routes. No user content or credentials are included in HTTP spans."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from opentelemetry.trace import Status, StatusCode
from starlette.middleware.base import RequestResponseEndpoint

from .assistant import Assistant
from .config import Settings
from .evaluation import evaluate, load_dataset
from .models import ChatRequest, ChatResponse, EvaluationRequest, EvaluationResult
from .providers import ProviderFailure
from .telemetry import Telemetry


def create_app(settings: Settings | None = None, assistant: Assistant | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings or Settings()
        app.state.assistant = assistant or Assistant(config, Telemetry(config))
        try:
            yield
        finally:
            await app.state.assistant.close()

    app = FastAPI(title="AI Observability Lab", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def trace_http(request: Request, call_next: RequestResponseEndpoint) -> Response:
        service: Assistant = request.app.state.assistant
        # Only fixed known paths; arbitrary user-controlled URL paths are excluded.
        path = (
            request.url.path
            if request.url.path in {"/health", "/chat", "/evaluate", "/metrics-summary"}
            else "other"
        )
        with service.telemetry.span(f"HTTP {request.method} {path}", server=True) as span:
            span.set_attribute("http.request.method", request.method)
            response = await call_next(request)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR, "request_failed"))
            return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "ai-observability-lab"}

    @app.post("/chat")
    async def chat(body: ChatRequest, request: Request) -> ChatResponse:
        service: Assistant = request.app.state.assistant
        try:
            return await service.chat(body)
        except ProviderFailure as exc:
            raise HTTPException(
                status_code=504 if str(exc) == "provider_timeout" else 502, detail=str(exc)
            ) from None

    @app.post("/evaluate")
    async def evaluate_route(body: EvaluationRequest, request: Request) -> EvaluationResult:
        service: Assistant = request.app.state.assistant
        item = next((i for i in load_dataset() if i.id == body.dataset_id), None)
        if item is None:
            raise HTTPException(404, "Unknown dataset item")
        try:
            return await evaluate(service, item, body.prompt_version)
        except ProviderFailure as exc:
            raise HTTPException(502, str(exc)) from None

    @app.get("/metrics-summary")
    async def metrics(request: Request) -> dict[str, Any]:
        service: Assistant = request.app.state.assistant
        return service.metrics.summary()

    return app


app = create_app()
