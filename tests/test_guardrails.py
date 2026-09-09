import pytest

from ai_observability_lab.evaluation import load_dataset
from ai_observability_lab.guardrails import check_input, check_output


@pytest.mark.parametrize(
    "item", [i for i in load_dataset() if i.category in {"injection", "sensitive"}]
)
def test_adversarial_input(item):
    assert check_input(item.question)


@pytest.mark.parametrize(
    "question", ["How do I reset my password?", "How do I block a stolen card?"]
)
def test_legitimate_support_is_allowed(question):
    assert check_input(question) is None


def test_output_rejects_invalid_reference_and_pii():
    assert not check_output("An answer [missing]", {"password-reset"})
    assert not check_output("Customer: test@example.com", set())
    assert not check_output("", set())
    assert check_output("Select Forgot password [password-reset]", {"password-reset"})
