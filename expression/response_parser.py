"""Conservative parser for raw expression-layer output."""

from __future__ import annotations

import re

from expression.prompt_builder import FAILURE_TOKEN
from expression.types import ExpressionInput, StudentResponse


INTERNAL_LEAKAGE_TERMS = (
    "BehaviorPlan",
    "PolicyInput",
    "belief_id",
    "transformation_id",
    "evaluator",
    "benchmark",
)


def parse_student_response(
    raw_output: str,
    expression_input: ExpressionInput,
) -> StudentResponse:
    if not isinstance(expression_input, ExpressionInput):
        raise ValueError("expression_input must be an ExpressionInput")
    if not isinstance(raw_output, str):
        raise ValueError("raw_output must be a string")

    stripped = raw_output.strip()
    plan = expression_input.behavior_plan
    if stripped == FAILURE_TOKEN:
        return _response(
            expression_input,
            response_text="",
            generation_status="failed",
            failure_reason="expression_failure_token",
            raw_model_output=raw_output,
        )
    if not stripped:
        return _response(
            expression_input,
            response_text="",
            generation_status="rejected",
            failure_reason="empty_output",
            raw_model_output=raw_output,
        )
    leaked = _internal_leakage(stripped)
    if leaked is not None:
        return _response(
            expression_input,
            response_text="",
            generation_status="rejected",
            failure_reason=f"internal_leakage:{leaked}",
            raw_model_output=raw_output,
        )
    if plan.action == "request_hint" and _contains_substantive_answer(stripped):
        return _response(
            expression_input,
            response_text="",
            generation_status="rejected",
            failure_reason="hint_response_contains_answer",
            raw_model_output=raw_output,
        )
    if plan.action == "abstain" and _looks_solution_like(stripped):
        return _response(
            expression_input,
            response_text="",
            generation_status="rejected",
            failure_reason="abstain_response_contains_solution",
            raw_model_output=raw_output,
        )
    return _response(
        expression_input,
        response_text=stripped,
        generation_status="success",
        failure_reason=None,
        raw_model_output=raw_output,
    )


def _response(
    expression_input: ExpressionInput,
    *,
    response_text: str,
    generation_status: str,
    failure_reason: str | None,
    raw_model_output: str,
) -> StudentResponse:
    plan = expression_input.behavior_plan
    return StudentResponse(
        response_text=response_text,
        action=plan.action,
        expressed_confidence=plan.expressed_confidence,
        activated_belief_id=plan.activated_belief_id,
        generation_status=generation_status,
        failure_reason=failure_reason,
        raw_model_output=raw_model_output,
        expression_version=expression_input.expression_version,
        _behavior_plan=plan,
    )


def _internal_leakage(text: str) -> str | None:
    lowered = text.lower()
    for term in INTERNAL_LEAKAGE_TERMS:
        if term.lower() in lowered:
            return term
    return None


def _contains_substantive_answer(text: str) -> bool:
    lowered = text.lower()
    if "?" in text and not any(marker in lowered for marker in ("answer is", "=", " so ")):
        return False
    if re.search(r"\b(answer|equals|therefore|because|solution)\b", lowered):
        return True
    if re.search(r"\d+\s*/\s*\d+|\d+\s*=\s*\d+|=\s*[-\w{(]", text):
        return True
    return False


def _looks_solution_like(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"\b(first|then|therefore|because|so the answer|equals)\b", lowered):
        return True
    if re.search(r"\d+\s*/\s*\d+|=\s*[-\w{(]", text):
        return True
    return False


__all__ = ["INTERNAL_LEAKAGE_TERMS", "parse_student_response"]
