"""Send HTTP traffic and verify its actual agent span and annotations in Phoenix."""

import argparse
import json
import time
from pathlib import Path

import httpx
from phoenix.client import Client

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--api", default="http://localhost:8000")
parser.add_argument("--phoenix", default="http://localhost:6006")
args = parser.parse_args()
api = httpx.Client(base_url=args.api, timeout=90)
health = api.get("/health")
health.raise_for_status()
result = api.post("/evaluate", json={"dataset_id": "normal-01", "prompt_version": "v2"})
result.raise_for_status()
body = result.json()
assert body["annotation_status"] == "uploaded", body["annotation_status"]
client = Client(base_url=args.phoenix)
span_id = body["response"]["span_id"]
for _attempt in range(30):
    spans = client.spans.get_spans(project_identifier="banking-assistant-observability", limit=100)
    if any(s["context"]["span_id"] == span_id for s in spans):
        break
    time.sleep(1)
else:
    raise RuntimeError("Expected application span was not received by Phoenix")
annotations = client.spans.get_span_annotations(
    project_identifier="banking-assistant-observability", span_ids=[span_id]
)
assert annotations, "Phoenix has no annotations for agent span"
evidence = {
    "health": health.json(),
    "trace_id": body["response"]["trace_id"],
    "span_id": span_id,
    "annotation_count": len(annotations),
    "verified_at_unix": time.time(),
}
Path("reports").mkdir(exist_ok=True)
Path("reports/stack-verification.json").write_text(json.dumps(evidence, indent=2) + "\n", "utf-8")
print(json.dumps(evidence, indent=2))
