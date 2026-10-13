"""Deterministic mock expression adapter for tests and dry runs."""

from __future__ import annotations

import re

from expression.prompt_builder import FAILURE_TOKEN


class MockExpressionAdapter:
    """Predictable adapter that validates infrastructure, not behavior fidelity."""

    def generate(self, prompt: str) -> str:
        parsed = self._parse_prompt(prompt)
        if FAILURE_TOKEN in prompt and parsed["force_failure"] == "true":
            return FAILURE_TOKEN
        action = parsed["action"]
        confidence = parsed["confidence_band"]
        transformation = parsed["transformation"]
        if action == "answer":
            return _answer_text(confidence, transformation)
        if action == "guess":
            return _guess_text(confidence)
        if action == "request_hint":
            return "Could I have a hint?"
        if action == "abstain":
            return "I'm not sure how to do this yet."
        if action == "revise":
            return _revise_text(confidence, transformation)
        return FAILURE_TOKEN

    def _parse_prompt(self, prompt: str) -> dict[str, str]:
        return {
            "action": _extract(prompt, r"- action: ([a-z_]+)", "abstain"),
            "confidence_band": _extract(
                prompt,
                r"- confidence_band: ([a-z_]+)",
                "low",
            ),
            "transformation": _extract(
                prompt,
                r"- transformation: ([a-z_]+)",
                "no_transformation",
            ),
            "force_failure": _extract(prompt, r"- force_failure: ([a-z_]+)", "false"),
        }


def _answer_text(confidence: str, transformation: str) -> str:
    prefix = _confidence_prefix(confidence)
    if transformation == "no_transformation":
        return f"{prefix}I would try to answer, but I don't really have a rule to use."
    return (
        f"{prefix}I used the {transformation} idea, so my answer follows from "
        "that rule."
    )


def _guess_text(confidence: str) -> str:
    prefix = _confidence_prefix(confidence)
    return f"{prefix}my guess is a simple form."


def _revise_text(confidence: str, transformation: str) -> str:
    prefix = _confidence_prefix(confidence)
    if transformation == "no_transformation":
        return f"{prefix}Let me revise that: I still need help choosing the rule."
    return (
        f"{prefix}Let me revise that using the feedback and the "
        f"{transformation} idea."
    )


def _confidence_prefix(confidence: str) -> str:
    if confidence == "high":
        return "I'm pretty confident. "
    if confidence == "medium":
        return "I think "
    return "I'm not very sure, but "


def _extract(prompt: str, pattern: str, default: str) -> str:
    match = re.search(pattern, prompt)
    if match is None:
        return default
    return match.group(1)


__all__ = ["MockExpressionAdapter"]
