"""Demonstration rules, not a comprehensive security boundary."""

import re

DISCLAIMER = "Fictional support information only; not personalized financial advice."
REFUSAL = "I cannot help with that request. Contact fictional support through a verified channel."
UNKNOWN = "I cannot answer that from the fictional knowledge base. Contact fictional support."
CLARIFY = "Please clarify the product and action you need help with, without sharing personal data."
RULES = {
    "prompt_injection": r"ignore.{0,50}(instruction|rule|previous)|system prompt|developer message|"
    r"override|jailbreak|you are now|act as|disregard|<\s*/?system|base64|execute.{0,20}code",
    "secrets": r"api.?key|secret|access token|admin password|reveal.{0,30}password",
    "personal_data": r"customer (data|balance|record)|someone.{0,20}(balance|account)|"
    r"social security|\bssn\b|\bcpr\b|\b\d{10,}\b|[\w.+-]+@[\w.-]+\.[a-z]{2,}",
    "financial_advice": r"(which|what).{0,30}(stock|invest)|buy.{0,20}(bitcoin|stock)|"
    r"personalized.{0,20}(advice|investment)|guarantee.{0,30}(return|profit)",
}


def check_input(question: str) -> str | None:
    normalized = " ".join(question.lower().split())
    return next((name for name, pattern in RULES.items() if re.search(pattern, normalized)), None)


def citations(answer: str) -> set[str]:
    return set(re.findall(r"\[([a-zA-Z0-9_-]+)\]", answer))


def check_output(answer: str, allowed_ids: set[str]) -> bool:
    """Reject unknown references, obvious sensitive content, and empty output."""
    return (
        bool(answer.strip())
        and citations(answer) <= allowed_ids
        and not bool(re.search(RULES["personal_data"] + r"|sk-[A-Za-z0-9]{10,}", answer))
    )
