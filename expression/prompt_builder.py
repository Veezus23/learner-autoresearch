"""Deterministic prompt construction for the expression layer."""

from __future__ import annotations

from expression.types import ExpressionInput


FAILURE_TOKEN = "<EXPRESSION_FAILURE>"


def build_expression_prompt(expression_input: ExpressionInput) -> str:
    if not isinstance(expression_input, ExpressionInput):
        raise ValueError("expression_input must be an ExpressionInput")

    plan = expression_input.behavior_plan
    sections = [
        "You are an expression engine, not the learner.",
        "Your job is to produce only the student-facing response.",
        f"Reserved failure token: {FAILURE_TOKEN}",
        "",
        "Student-facing question:",
        expression_input.question_text,
        "",
        "Selected behavior:",
        f"- action: {plan.action}",
        f"- expressed_confidence: {plan.expressed_confidence:.2f}",
        f"- confidence_band: {_confidence_band(plan.expressed_confidence)}",
        f"- reasoning_mode: {plan.reasoning_mode}",
        "- symbolic_response_constraints: "
        + ", ".join(plan.response_constraints),
        "",
        "Selected belief:",
        _belief_section(expression_input),
        "",
        "Transformation:",
        _transformation_section(expression_input),
        "",
        "Hard requirements:",
        "- Do not independently solve the problem.",
        "- Do not replace or repair the selected belief.",
        "- Do not use external correctness knowledge.",
        "- Do not self-correct unless the selected action is revise.",
        "- Faithfully apply the selected transformation when one is provided.",
        "- Follow the requested action exactly.",
        "- Produce only the student-facing response.",
        "- Preserve the uncertainty and confidence level.",
        f"- Return exactly {FAILURE_TOKEN} if faithful expression is impossible.",
        "",
        "Action instructions:",
        _action_instructions(plan.action),
        "",
        "Reasoning-mode instructions:",
        _reasoning_mode_instructions(plan.reasoning_mode),
    ]
    if plan.action == "revise":
        sections.extend(
            [
                "",
                "Revision context:",
                f"- prior_response: {expression_input.prior_response_text or ''}",
                "- learner_facing_feedback: "
                + _feedback_message(expression_input),
            ]
        )
    return "\n".join(sections)


def _belief_section(expression_input: ExpressionInput) -> str:
    definition = expression_input.activated_belief_definition
    learner_belief = expression_input.activated_learner_belief
    if definition is None or learner_belief is None:
        return "- no selected belief; no usable rule is available"
    return "\n".join(
        [
            f"- belief_description: {definition.description}",
            f"- belief_type: {definition.belief_type}",
            f"- learner_belief_confidence: {learner_belief.belief_confidence:.2f}",
        ]
    )


def _transformation_section(expression_input: ExpressionInput) -> str:
    definition = expression_input.activated_belief_definition
    if definition is None or definition.transformation_id is None:
        return "- no executable transformation identifier"
    lines = [f"- transformation: {definition.transformation_id}"]
    metadata = expression_input.transformation_metadata
    if metadata:
        for key in sorted(metadata):
            lines.append(f"- {key}: {metadata[key]}")
    return "\n".join(lines)


def _action_instructions(action: str) -> str:
    instructions = {
        "answer": (
            "- Express an answer based on the selected belief and transformation.\n"
            "- Do not ask for a hint.\n"
            "- Do not mention the architecture or policy.\n"
            "- Preserve the selected belief."
        ),
        "guess": (
            "- Give a concise plausible guess.\n"
            "- Reflect low or moderate confidence.\n"
            "- Do not derive a polished expert solution.\n"
            "- Do not claim knowledge the learner does not have."
        ),
        "request_hint": (
            "- Ask for a hint only.\n"
            "- Do not answer the question.\n"
            "- Do not solve."
        ),
        "abstain": (
            "- State uncertainty or inability to answer.\n"
            "- Do not guess.\n"
            "- Do not solve."
        ),
        "revise": (
            "- Revise the prior response using learner-facing corrective feedback.\n"
            "- Remain consistent with the selected behavior and selected belief.\n"
            "- Do not use evaluator-only information.\n"
            "- Do not silently produce an expert answer unless the activated "
            "belief and feedback justify it."
        ),
    }
    return instructions[action]


def _reasoning_mode_instructions(reasoning_mode: str) -> str:
    instructions = {
        "apply_belief": "- Apply the selected transformation faithfully.",
        "partial_attempt": (
            "- Show incomplete but directionally coherent reasoning.\n"
            "- Do not fill in missing knowledge from external reasoning."
        ),
        "guess": "- Produce a short guess with limited reasoning.",
        "no_rule": (
            "- Do not invent a procedure.\n"
            "- Request help, abstain, or express uncertainty according to action."
        ),
    }
    return instructions[reasoning_mode]


def _feedback_message(expression_input: ExpressionInput) -> str:
    feedback = expression_input.learner_feedback
    if feedback is None:
        return ""
    return feedback.learner_message


def _confidence_band(value: float) -> str:
    if value <= 0.35:
        return "low"
    if value <= 0.69:
        return "medium"
    return "high"


__all__ = ["FAILURE_TOKEN", "build_expression_prompt"]
