"""Portable commands used by Make and Docker; failure controls are never API inputs."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx

from .assistant import Assistant
from .config import Settings
from .evaluation import annotate, evaluate, load_dataset, score_response
from .experiments import experiment, phoenix_experiment, regression_failures, run_suite
from .models import ChatRequest, EvaluationResult
from .providers import MockProvider, ProviderFailure
from .retrieval import load_documents
from .telemetry import Telemetry


async def failures(settings: Settings, output: Path) -> None:
    if settings.llm_provider != "mock":
        raise ValueError("Failure simulation requires LLM_PROVIDER=mock")
    rows = []
    for scenario in (
        "slow",
        "empty_retrieval",
        "hallucination",
        "invalid_citation",
        "injection",
        "timeout",
        "error",
        "guardrail",
    ):
        assistant = Assistant(settings, Telemetry(settings), MockProvider(scenario))
        item = load_dataset()[0].model_copy(deep=True)
        if scenario == "injection":
            item = next(i for i in load_dataset() if i.category == "injection")
        elif scenario == "guardrail":
            item = next(i for i in load_dataset() if i.category == "sensitive")
        with assistant.telemetry.span("failure.simulation") as span:
            span.set_attribute("demo.scenario", scenario)
            trace_id = f"{span.get_span_context().trace_id:032x}"
            try:
                response = await assistant.chat(
                    ChatRequest(question=item.question),
                    empty_retrieval=scenario == "empty_retrieval",
                )
                scores = score_response(item, response)
                result = EvaluationResult(
                    dataset_id=item.id, response=response, scores=scores, passed=scores["pass"] == 1
                )
                for name, value in scores.items():
                    span.set_attribute(f"evaluation.{name}", value)
                await annotate(assistant, result)
                rows.append({"scenario": scenario, "result": result.model_dump()})
            except ProviderFailure as exc:
                rows.append({"scenario": scenario, "error": str(exc), "trace_id": trace_id})
        await assistant.close()
    output.mkdir(parents=True, exist_ok=True)
    output.joinpath("failure-results.json").write_text(json.dumps(rows, indent=2) + "\n", "utf-8")
    print(json.dumps([{"scenario": r["scenario"], "error": r.get("error")} for r in rows]))


async def run(args: argparse.Namespace) -> None:
    settings = Settings()
    if args.command == "experiment":
        report = await experiment(settings, args.output)
        print(json.dumps(report["summaries"], indent=2))
    elif args.command == "eval":
        rows = await run_suite(settings, "v2")
        failed = regression_failures(rows)
        print(f"{len(rows)} cases; failed gates: {failed}")
        if failed or any(r.annotation_status == "failed" for r in rows):
            raise SystemExit(1)
    elif args.command == "failures":
        await failures(settings, args.output)
    elif args.command == "seed":
        docs, data = load_documents(), load_dataset()
        assert len({d.id for d in docs}) == len(docs)
        assert len({d.id for d in data}) == len(data)
        assert all(set(d.expected_document_ids) <= {x.id for x in docs} for d in data)
        print(f"Validated packaged seed data: {len(docs)} documents, {len(data)} cases")
    elif args.command == "judge":
        from .judge import judge

        assistant = Assistant(settings, Telemetry(settings))
        try:
            item = load_dataset()[0]
            result = await evaluate(assistant, item)
            print((await judge(assistant, item.question, result)).model_dump_json(indent=2))
        finally:
            await assistant.close()
    else:
        async with httpx.AsyncClient(base_url=args.url, timeout=30) as client:
            for item in load_dataset()[:3]:
                response = await client.post("/chat", json={"question": item.question})
                response.raise_for_status()
                print(response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["demo", "seed", "eval", "experiment", "failures", "phoenix-experiment", "judge"],
    )
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    if args.command == "phoenix-experiment":
        phoenix_experiment(Settings())
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
