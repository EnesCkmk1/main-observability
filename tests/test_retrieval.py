from collections import Counter

import pytest

from ai_observability_lab.evaluation import load_dataset
from ai_observability_lab.retrieval import Retriever, load_documents


@pytest.mark.parametrize(
    "item", [i for i in load_dataset() if i.category == "normal"], ids=lambda i: i.id
)
def test_retrieval_finds_expected_document(item):
    matches = Retriever().search(item.question)
    assert matches[0][0].id in item.expected_document_ids
    assert matches == Retriever().search(item.question)


def test_no_evidence_and_data_integrity():
    assert Retriever().search("telescope supernova nebula") == []
    docs, dataset = load_documents(), load_dataset()
    assert 15 <= len(docs) <= 20
    assert len({d.id for d in docs}) == len(docs)
    assert len({d.id for d in dataset}) == len(dataset)
    assert Counter(d.category for d in dataset) == {
        "normal": 20,
        "ambiguous": 5,
        "unanswerable": 5,
        "sensitive": 5,
        "injection": 5,
    }
