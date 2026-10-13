"""Immutable expression-layer data types."""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import Mapping

from cognition.belief_definition import BeliefDefinition
from cognition.transformations import validate_snake_case_id
from learner.belief_state import LearnerBelief
from learner.feedback import LearnerFeedback, ensure_learner_feedback
from learner.policy import BehaviorPlan


EXPRESSION_VERSION = "expression_v0"
GENERATION_STATUS_VALUES = frozenset({"success", "failed", "rejected"})

FORBIDDEN_EXPRESSION_TOKENS = frozenset(
    {
        "answer_key",
        "answer_keys",
        "behavioral_fidelity_score",
        "benchmark_expectation",
        "benchmark_expectations",
        "case_id",
        "case_ids",
        "correct_answer",
        "correct_answers",
        "detector_internal",
        "detector_internals",
        "detector_output",
        "detector_outputs",
        "evaluator_label",
        "evaluator_labels",
        "evaluator_output",
        "evaluator_outputs",
        "evaluator_score",
        "evaluator_scores",
        "expected_answer",
        "expected_answers",
        "expected_output",
        "expected_outputs",
        "hidden_test",
        "hidden_test_metadata",
        "optimization_hint",
        "optimization_hints",
        "scoring_weight",
        "scoring_weights",
        "validation_aggregate",
        "validation_aggregates",
        "validation_expectation",
        "validation_expectations",
        "validation_label",
        "validation_labels",
    }
)


@dataclass(frozen=True, init=False)
class ExpressionInput:
    """Immutable input to the language expression layer."""

    question_text: str
    behavior_plan: BehaviorPlan
    activated_belief_definition: BeliefDefinition | None
    activated_learner_belief: LearnerBelief | None
    transformation_metadata: Mapping[str, object] | None
    prior_response_text: str | None
    learner_feedback: LearnerFeedback | None
    expression_version: str

    def __init__(
        self,
        *,
        question_text: str,
        behavior_plan: BehaviorPlan,
        activated_belief_definition: BeliefDefinition | None = None,
        activated_learner_belief: LearnerBelief | None = None,
        transformation_metadata: Mapping[str, object] | None = None,
        prior_response_text: str | None = None,
        learner_feedback: LearnerFeedback | Mapping[str, object] | None = None,
        expression_version: str = EXPRESSION_VERSION,
        **extra_fields: object,
    ) -> None:
        _reject_extra_fields("expression input", extra_fields)
        _validate_non_empty_string("question_text", question_text)
        _reject_forbidden_text("question_text", question_text)
        if not isinstance(behavior_plan, BehaviorPlan):
            raise ValueError("behavior_plan must be a BehaviorPlan")
        _validate_belief_pair(
            behavior_plan,
            activated_belief_definition,
            activated_learner_belief,
        )
        metadata = _immutable_metadata(transformation_metadata)
        if prior_response_text is not None:
            _validate_optional_text("prior_response_text", prior_response_text)
        feedback = _coerce_feedback(learner_feedback)
        _validate_non_empty_string("expression_version", expression_version)
        _reject_forbidden_text("expression_version", expression_version)

        object.__setattr__(self, "question_text", question_text)
        object.__setattr__(self, "behavior_plan", behavior_plan)
        object.__setattr__(
            self,
            "activated_belief_definition",
            activated_belief_definition,
        )
        object.__setattr__(self, "activated_learner_belief", activated_learner_belief)
        object.__setattr__(self, "transformation_metadata", metadata)
        object.__setattr__(self, "prior_response_text", prior_response_text)
        object.__setattr__(self, "learner_feedback", feedback)
        object.__setattr__(self, "expression_version", expression_version)


@dataclass(frozen=True, init=False)
class StudentResponse:
    """Learner-visible response returned by the expression layer."""

    response_text: str
    action: str
    expressed_confidence: float
    activated_belief_id: str | None
    generation_status: str
    failure_reason: str | None
    raw_model_output: str | None
    expression_version: str

    def __init__(
        self,
        *,
        response_text: str,
        action: str,
        expressed_confidence: float,
        activated_belief_id: str | None,
        generation_status: str,
        failure_reason: str | None = None,
        raw_model_output: str | None = None,
        expression_version: str = EXPRESSION_VERSION,
        _behavior_plan: BehaviorPlan | None = None,
        **extra_fields: object,
    ) -> None:
        _reject_extra_fields("student response", extra_fields)
        if not isinstance(response_text, str):
            raise ValueError("response_text must be a string")
        if action not in {"answer", "guess", "request_hint", "abstain", "revise"}:
            raise ValueError(f"invalid action: {action}")
        _validate_probability("expressed_confidence", expressed_confidence)
        if activated_belief_id is not None:
            validate_snake_case_id("activated_belief_id", activated_belief_id)
        if generation_status not in GENERATION_STATUS_VALUES:
            raise ValueError(f"invalid generation_status: {generation_status}")
        if failure_reason is not None:
            _validate_optional_text("failure_reason", failure_reason)
        if raw_model_output is not None and not isinstance(raw_model_output, str):
            raise ValueError("raw_model_output must be a string or None")
        _validate_non_empty_string("expression_version", expression_version)
        _reject_forbidden_text("response_text", response_text)
        _reject_forbidden_text("expression_version", expression_version)
        _validate_against_plan(
            _behavior_plan,
            action,
            expressed_confidence,
            activated_belief_id,
        )

        object.__setattr__(self, "response_text", response_text)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "expressed_confidence", float(expressed_confidence))
        object.__setattr__(self, "activated_belief_id", activated_belief_id)
        object.__setattr__(self, "generation_status", generation_status)
        object.__setattr__(self, "failure_reason", failure_reason)
        object.__setattr__(self, "raw_model_output", raw_model_output)
        object.__setattr__(self, "expression_version", expression_version)


def _validate_belief_pair(
    behavior_plan: BehaviorPlan,
    definition: BeliefDefinition | None,
    learner_belief: LearnerBelief | None,
) -> None:
    plan_id = behavior_plan.activated_belief_id
    if plan_id is None:
        if definition is not None or learner_belief is not None:
            raise ValueError("activated belief objects must be None when plan has no belief")
        return

    if not isinstance(definition, BeliefDefinition):
        raise ValueError("activated_belief_definition must be a BeliefDefinition")
    if not isinstance(learner_belief, LearnerBelief):
        raise ValueError("activated_learner_belief must be a LearnerBelief")
    if definition.belief_id != plan_id or learner_belief.belief_id != plan_id:
        raise ValueError("activated belief objects must match behavior_plan")


def _validate_against_plan(
    behavior_plan: BehaviorPlan | None,
    action: str,
    expressed_confidence: float,
    activated_belief_id: str | None,
) -> None:
    if behavior_plan is None:
        return
    if action != behavior_plan.action:
        raise ValueError("action must match behavior_plan")
    if float(expressed_confidence) != behavior_plan.expressed_confidence:
        raise ValueError("expressed_confidence must match behavior_plan")
    if activated_belief_id != behavior_plan.activated_belief_id:
        raise ValueError("activated_belief_id must match behavior_plan")


def _immutable_metadata(
    metadata: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    if metadata is None:
        return None
    if not isinstance(metadata, Mapping):
        raise ValueError("transformation_metadata must be a mapping or None")
    copied: dict[str, object] = {}
    for key, value in metadata.items():
        validate_snake_case_id("transformation_metadata key", key)
        _validate_metadata_value(f"transformation_metadata[{key!r}]", value)
        _reject_forbidden_text("transformation_metadata key", key)
        if isinstance(value, str):
            _reject_forbidden_text(f"transformation_metadata[{key!r}]", value)
        copied[key] = _freeze_metadata_value(value)
    return MappingProxyType(copied)


def _validate_metadata_value(name: str, value: object) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _validate_metadata_value(name, item)
        return
    raise ValueError(f"{name} must contain only scalar or tuple/list values")


def _freeze_metadata_value(value: object) -> object:
    if isinstance(value, list):
        return tuple(_freeze_metadata_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_metadata_value(item) for item in value)
    return value


def _coerce_feedback(
    feedback: LearnerFeedback | Mapping[str, object] | None,
) -> LearnerFeedback | None:
    if feedback is None:
        return None
    return ensure_learner_feedback(feedback)


def _reject_extra_fields(name: str, extra_fields: Mapping[str, object]) -> None:
    if not extra_fields:
        return
    normalized = {_normalize(str(key)) for key in extra_fields}
    forbidden = sorted(normalized & FORBIDDEN_EXPRESSION_TOKENS)
    if forbidden:
        raise ValueError(
            f"{name} cannot contain evaluator-only or benchmark-only field(s): "
            + ", ".join(forbidden)
        )
    raise ValueError(
        f"{name} cannot contain extra field(s): "
        + ", ".join(sorted(str(key) for key in extra_fields))
    )


def _reject_forbidden_text(name: str, value: str) -> None:
    normalized = _normalize(value)
    matched = sorted(
        token for token in FORBIDDEN_EXPRESSION_TOKENS if token in normalized
    )
    if matched:
        raise ValueError(
            f"{name} cannot contain evaluator-only, benchmark-only, or hidden-test "
            f"metadata: {', '.join(matched)}"
        )


def _validate_probability(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def _validate_optional_text(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    _reject_forbidden_text(name, value)


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _normalize(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "EXPRESSION_VERSION",
    "FORBIDDEN_EXPRESSION_TOKENS",
    "GENERATION_STATUS_VALUES",
    "ExpressionInput",
    "StudentResponse",
]
