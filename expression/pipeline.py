"""Expression-layer pipeline."""

from __future__ import annotations

from expression.adapter import ExpressionAdapter
from expression.prompt_builder import build_expression_prompt
from expression.response_parser import parse_student_response
from expression.types import ExpressionInput, StudentResponse


def express_response(
    expression_input: ExpressionInput,
    adapter: ExpressionAdapter,
) -> StudentResponse:
    if not isinstance(expression_input, ExpressionInput):
        raise ValueError("expression_input must be an ExpressionInput")
    if not hasattr(adapter, "generate"):
        raise ValueError("adapter must provide generate(prompt)")

    prompt = build_expression_prompt(expression_input)
    raw_output = adapter.generate(prompt)
    return parse_student_response(raw_output, expression_input)


__all__ = ["express_response"]
