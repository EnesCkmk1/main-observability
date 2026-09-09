import pytest

from ai_observability_lab.evaluation import evaluate, load_dataset, score_response
from ai_observability_lab.experiments import regression_failures


@pytest.mark.parametrize("item", load_dataset(), ids=lambda i: i.id)
async def test_v2_regression(assistant, item):
    result = await evaluate(assistant, item)
    assert result.passed, result.scores


async def test_hallucination_and_missing_citation_are_detected(assistant):
    item = load_dataset()[0]
    result = await evaluate(assistant, item)
    corrupt = result.response.model_copy(update={"answer": "The moon is made of cheese."})
    scores = score_response(item, corrupt)
    assert scores["groundedness"] < 0.5
    assert scores["correctness"] == 0
    assert scores["citation_accuracy"] == 0
    assert scores["pass"] == 0
    result.scores = scores
    result.passed = False
    assert regression_failures([result])


async def test_v1_versus_v2_is_a_real_prompt_contract_difference(assistant):
    item = load_dataset()[0]
    v1, v2 = await evaluate(assistant, item, "v1"), await evaluate(assistant, item, "v2")
    assert v1.scores["citation_accuracy"] == 0
    assert v2.scores["citation_accuracy"] == 1
    assert v1.response.input_token_count < v2.response.input_token_count
