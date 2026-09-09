"""Deterministic lexical retrieval with explicit no-match behavior."""

import json
import re
from importlib.resources import files

from .models import Document, Source

STOPWORDS = set(
    "a an the how do i my is can to for of in on me what it please banking bank".split()
)


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def load_documents() -> list[Document]:
    data = files("ai_observability_lab").joinpath("data/knowledge-base.json").read_text("utf-8")
    return [Document.model_validate(row) for row in json.loads(data)]


class Retriever:
    def __init__(self) -> None:
        self.documents = load_documents()

    def search(self, question: str, top_k: int = 2) -> list[tuple[Document, Source]]:
        query = tokens(question)
        scored = []
        for doc in self.documents:
            terms = tokens(doc.title + " " + " ".join(doc.keywords))
            overlap = query & terms
            score = len(overlap) / max(len(query), 1)
            # One generic word is insufficient evidence for an answer.
            if len(overlap) >= 2 and score >= 0.25:
                scored.append((doc, Source(id=doc.id, title=doc.title, score=round(score, 4))))
        scored.sort(key=lambda pair: (-pair[1].score, pair[0].id))
        if not scored:
            return []
        # Exclude weak secondary matches that share only generic product words.
        return [pair for pair in scored if pair[1].score >= scored[0][1].score * 0.8][:top_k]
