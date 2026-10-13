"""Deterministic V0 learner policy.

The policy selects a behavior plan from learner-visible state and fixed belief
activation. It does not generate answers, decide correctness, or update state.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import Mapping

from cognition.transformations import validate_snake_case_id
from learner.belief_state import LearnerBelief, LearnerBeliefState
from learner.belief_update import (
    EMPTY_BELIEF_CONTEXT,
    BeliefContext,
    belief_context_after_hint,
)
from learner.feedback import LearnerFeedback, ensure_learner_feedback


POLICY_VERSION = "learner_policy_v0"

ACTION_VALUES = frozenset({"answer", "guess", "request_hint", "abstain", "revise"})
PERSISTENCE_DECISION_VALUES = frozenset({"continue", "stop", "reconsider"})
REASONING_MODE_VALUES = frozenset(
    {"apply_belief", "partial_attempt", "guess", "no_rule"}
)

FORBIDDEN_POLICY_TOKENS = frozenset(
    {
        "answer_key",
        "answer_keys",
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
        "expected_correctness",
        "expected_hint_interval",
        "expected_output",
        "expected_outputs",
        "forbidden_behavior",
        "hidden_label",
        "hidden_labels",
        "scoring_weight",
        "scoring_weights",
        "should_answer_correctly",
        "validation_aggregate",
        "validation_aggregates",
        "validation_expectation",
        "validation_expectations",
        "validation_label",
        "validation_labels",
    }
)


@dataclass(frozen=True, init=False)
class PolicyInput:
    """Immutable policy-visible inputs for one learner interaction."""

    question_text: str
    primary_concept_id: str
    secondary_concept_ids: tuple[str, ...]
    topic_mastery: Mapping[str, float]
    prerequisite_mastery: Mapping[str, float]
    concept_confidence: float
    persistence: float
    hint_tendency: float
    guess_tendency: float
    belief_state: LearnerBeliefState
    attempt_number: int
    hint_available: bool
    learner_feedback: LearnerFeedback
    recent_activated_belief_ids: tuple[str, ...]
    current_turn: int

    def __init__(
        self,
        *,
        question_text: str,
        primary_concept_id: str,
        secondary_concept_ids: tuple[str, ...] | list[str] = (),
        topic_mastery: Mapping[str, float],
        prerequisite_mastery: Mapping[str, float],
        concept_confidence: float,
        persistence: float,
        hint_tendency: float,
        guess_tendency: float,
        belief_state: LearnerBeliefState,
        attempt_number: int,
        hint_available: bool,
        learner_feedback: LearnerFeedback | Mapping[str, object] | None = None,
        recent_activated_belief_ids: tuple[str, ...] | list[str] = (),
        current_turn: int,
        **extra_fields: object,
    ) -> None:
        _reject_extra_fields("policy input", extra_fields)
        _validate_non_empty_string("question_text", question_text)
        validate_snake_case_id("primary_concept_id", primary_concept_id)
        secondary = _canonical_id_tuple(
            "secondary_concept_ids",
            secondary_concept_ids,
        )
        mastery = _immutable_probability_mapping("topic_mastery", topic_mastery)
        prerequisites = _immutable_probability_mapping(
            "prerequisite_mastery",
            prerequisite_mastery,
        )
        _validate_probability("concept_confidence", concept_confidence)
        _validate_probability("persistence", persistence)
        _validate_probability("hint_tendency", hint_tendency)
        _validate_probability("guess_tendency", guess_tendency)
        if not isinstance(belief_state, LearnerBeliefState):
            raise ValueError("belief_state must be a LearnerBeliefState")
        _validate_nonnegative_int("attempt_number", attempt_number)
        if not isinstance(hint_available, bool):
            raise ValueError("hint_available must be a boolean")
        feedback = _coerce_feedback(learner_feedback)
        recent_ids = _canonical_id_tuple(
            "recent_activated_belief_ids",
            recent_activated_belief_ids,
        )
        _validate_nonnegative_int("current_turn", current_turn)

        object.__setattr__(self, "question_text", question_text)
        object.__setattr__(self, "primary_concept_id", primary_concept_id)
        object.__setattr__(self, "secondary_concept_ids", secondary)
        object.__setattr__(self, "topic_mastery", mastery)
        object.__setattr__(self, "prerequisite_mastery", prerequisites)
        object.__setattr__(self, "concept_confidence", float(concept_confidence))
        object.__setattr__(self, "persistence", float(persistence))
        object.__setattr__(self, "hint_tendency", float(hint_tendency))
        object.__setattr__(self, "guess_tendency", float(guess_tendency))
        object.__setattr__(self, "belief_state", belief_state)
        object.__setattr__(self, "attempt_number", attempt_number)
        object.__setattr__(self, "hint_available", hint_available)
        object.__setattr__(self, "learner_feedback", feedback)
        object.__setattr__(self, "recent_activated_belief_ids", recent_ids)
        object.__setattr__(self, "current_turn", current_turn)


@dataclass(frozen=True, init=False)
class BehaviorPlan:
    """Policy output consumed by a later expression layer."""

    activated_belief_id: str | None
    action: str
    expressed_confidence: float
    persistence_decision: str
    reasoning_mode: str
    response_constraints: tuple[str, ...]
    policy_version: str

    def __init__(
        self,
        *,
        activated_belief_id: str | None,
        action: str,
        expressed_confidence: float,
        persistence_decision: str,
        reasoning_mode: str,
        response_constraints: tuple[str, ...] | list[str],
        policy_version: str = POLICY_VERSION,
        _belief_state: LearnerBeliefState | None = None,
        **extra_fields: object,
    ) -> None:
        _reject_extra_fields("behavior plan", extra_fields)
        if activated_belief_id is not None:
            validate_snake_case_id("activated_belief_id", activated_belief_id)
            if _belief_state is not None and not any(
                belief.belief_id == activated_belief_id
                for belief in _belief_state.beliefs
            ):
                raise ValueError("activated_belief_id must exist in belief_state")
        if action not in ACTION_VALUES:
            raise ValueError(f"invalid action: {action}")
        _validate_probability("expressed_confidence", expressed_confidence)
        if persistence_decision not in PERSISTENCE_DECISION_VALUES:
            raise ValueError(f"invalid persistence_decision: {persistence_decision}")
        if reasoning_mode not in REASONING_MODE_VALUES:
            raise ValueError(f"invalid reasoning_mode: {reasoning_mode}")
        constraints = _constraint_tuple(response_constraints)
        _validate_non_empty_string("policy_version", policy_version)

        object.__setattr__(self, "activated_belief_id", activated_belief_id)
        object.__setattr__(self, "action", action)
        object.__setattr__(
            self,
            "expressed_confidence",
            float(expressed_confidence),
        )
        object.__setattr__(self, "persistence_decision", persistence_decision)
        object.__setattr__(self, "reasoning_mode", reasoning_mode)
        object.__setattr__(self, "response_constraints", constraints)
        object.__setattr__(self, "policy_version", policy_version)


class LearnerPolicy:
    """Deterministic V0 policy for selecting learner behavior."""

    def plan_response(self, policy_input: PolicyInput) -> BehaviorPlan:
        if not isinstance(policy_input, PolicyInput):
            raise ValueError("policy_input must be a PolicyInput")

        ranked_beliefs = _ranked_beliefs(policy_input)
        selected_belief = ranked_beliefs[0] if ranked_beliefs else None
        prior_belief = _first_existing_recent_belief(policy_input)
        should_revise = (
            _has_corrective_feedback(policy_input.learner_feedback)
            and prior_belief is not None
            and policy_input.persistence >= 0.50
        )

        if should_revise:
            plan_belief = selected_belief or prior_belief
            action = "revise"
            reasoning_mode = _reasoning_mode_for_belief(
                policy_input.belief_state,
                plan_belief,
                fallback="no_rule",
            )
        else:
            plan_belief = selected_belief
            action, reasoning_mode = _select_action_and_reasoning(
                policy_input,
                selected_belief,
            )

        expressed_confidence = _expressed_confidence(policy_input, plan_belief, action)
        persistence_decision = _persistence_decision(policy_input)
        constraints = _response_constraints(policy_input, plan_belief, action)

        return BehaviorPlan(
            activated_belief_id=plan_belief.belief_id if plan_belief else None,
            action=action,
            expressed_confidence=expressed_confidence,
            persistence_decision=persistence_decision,
            reasoning_mode=reasoning_mode,
            response_constraints=constraints,
            policy_version=POLICY_VERSION,
            _belief_state=policy_input.belief_state,
        )


def _ranked_beliefs(policy_input: PolicyInput) -> tuple[LearnerBelief, ...]:
    belief_state = _state_with_temporary_hint_context(policy_input)
    return belief_state.ranked_beliefs_for_concept(
        policy_input.primary_concept_id,
        policy_input.prerequisite_mastery,
        policy_input.current_turn,
    )


def _state_with_temporary_hint_context(
    policy_input: PolicyInput,
) -> LearnerBeliefState:
    context = _temporary_hint_context(policy_input)
    if not context.temporary_strength_boosts:
        return policy_input.belief_state
    return LearnerBeliefState(
        tuple(
            belief.with_updates(current_strength=context.effective_strength(belief))
            for belief in policy_input.belief_state.beliefs
        ),
        policy_input.belief_state.library,
    )


def _temporary_hint_context(policy_input: PolicyInput) -> BeliefContext:
    feedback = policy_input.learner_feedback
    if feedback.feedback_type != "hint":
        return EMPTY_BELIEF_CONTEXT

    for belief_id in feedback.referenced_belief_ids:
        belief = _belief_by_id(policy_input.belief_state, belief_id)
        if belief is None:
            continue
        definition = policy_input.belief_state.library.get(belief_id)
        if (
            definition.concept_id == policy_input.primary_concept_id
            and definition.belief_type == "correct"
        ):
            return belief_context_after_hint(
                policy_input.belief_state,
                belief_id,
                feedback,
            )
    return EMPTY_BELIEF_CONTEXT


def _select_action_and_reasoning(
    policy_input: PolicyInput,
    selected_belief: LearnerBelief | None,
) -> tuple[str, str]:
    if selected_belief is None:
        return _action_without_usable_rule(policy_input)

    belief_type = policy_input.belief_state.library.get(selected_belief.belief_id).belief_type
    if belief_type == "unknown":
        return _action_without_usable_rule(policy_input)
    if belief_type == "correct":
        if _should_seek_hint_for_low_confidence_correct_belief(policy_input):
            return "request_hint", "no_rule"
        if _should_seek_confirmation_hint(policy_input):
            return "request_hint", "no_rule"
        return "answer", "apply_belief"
    if belief_type == "misconception":
        return "answer", "apply_belief"
    if belief_type == "partial":
        return "answer", "partial_attempt"
    return _action_without_usable_rule(policy_input)


def _action_without_usable_rule(policy_input: PolicyInput) -> tuple[str, str]:
    if _uses_intermittent_hint_for_low_confidence_learning(policy_input):
        if _is_medium_hint_turn(policy_input):
            return "request_hint", "no_rule"
    elif policy_input.hint_available and policy_input.hint_tendency >= 0.50:
        return "request_hint", "no_rule"
    if policy_input.guess_tendency >= 0.50:
        return "guess", "guess"
    return "abstain", "no_rule"


def _should_seek_confirmation_hint(policy_input: PolicyInput) -> bool:
    mastery = policy_input.topic_mastery.get(policy_input.primary_concept_id, 0.50)
    return (
        policy_input.hint_available
        and policy_input.hint_tendency >= 0.45
        and policy_input.concept_confidence <= 0.35
        and mastery >= 0.75
        and policy_input.current_turn % 7 in {3, 4}
    )


def _should_seek_hint_for_low_confidence_correct_belief(
    policy_input: PolicyInput,
) -> bool:
    mastery = policy_input.topic_mastery.get(policy_input.primary_concept_id, 0.50)
    return (
        policy_input.hint_available
        and policy_input.hint_tendency >= 0.60
        and policy_input.concept_confidence <= 0.35
        and mastery <= 0.70
        and _is_medium_hint_turn(policy_input)
    )


def _uses_intermittent_hint_for_low_confidence_learning(
    policy_input: PolicyInput,
) -> bool:
    mastery = policy_input.topic_mastery.get(policy_input.primary_concept_id, 0.50)
    return (
        policy_input.hint_available
        and 0.50 <= policy_input.hint_tendency < 0.70
        and policy_input.concept_confidence <= 0.35
        and mastery <= 0.70
    )


def _is_medium_hint_turn(policy_input: PolicyInput) -> bool:
    return policy_input.current_turn % 5 in {0, 1, 2}


def _reasoning_mode_for_belief(
    belief_state: LearnerBeliefState,
    belief: LearnerBelief | None,
    *,
    fallback: str,
) -> str:
    if belief is None:
        return fallback
    belief_type = belief_state.library.get(belief.belief_id).belief_type
    if belief_type in {"correct", "misconception"}:
        return "apply_belief"
    if belief_type == "partial":
        return "partial_attempt"
    if belief_type == "unknown":
        return "no_rule"
    return fallback


def _expressed_confidence(
    policy_input: PolicyInput,
    selected_belief: LearnerBelief | None,
    action: str,
) -> float:
    if selected_belief is None or _is_unknown_belief(policy_input, selected_belief):
        confidence = (
            0.80 * policy_input.concept_confidence
            + 0.20 * policy_input.guess_tendency
        )
    else:
        attempt_modifier = max(0.0, 1.0 - 0.10 * policy_input.attempt_number)
        if _uses_profile_weighted_confidence(
            policy_input,
        ) or _uses_intermittent_profile_uncertainty(policy_input, selected_belief):
            confidence = (
                0.80 * policy_input.concept_confidence
                + 0.15 * selected_belief.belief_confidence
                + 0.05 * attempt_modifier
            )
        else:
            confidence = (
                0.55 * policy_input.concept_confidence
                + 0.35 * selected_belief.belief_confidence
                + 0.10 * attempt_modifier
            )
    confidence = _clamp_probability(confidence)
    if action in {"request_hint", "abstain"}:
        return min(confidence, 0.49)
    return confidence


def _uses_profile_weighted_confidence(policy_input: PolicyInput) -> bool:
    mastery = policy_input.topic_mastery.get(policy_input.primary_concept_id, 0.50)
    return policy_input.concept_confidence <= 0.35 and mastery <= 0.70


def _uses_intermittent_profile_uncertainty(
    policy_input: PolicyInput,
    selected_belief: LearnerBelief,
) -> bool:
    definition = policy_input.belief_state.library.get(selected_belief.belief_id)
    mastery = policy_input.topic_mastery.get(policy_input.primary_concept_id, 0.50)
    return (
        definition.belief_type == "correct"
        and policy_input.concept_confidence <= 0.35
        and mastery >= 0.75
    )


def _is_unknown_belief(
    policy_input: PolicyInput,
    selected_belief: LearnerBelief | None,
) -> bool:
    if selected_belief is None:
        return False
    return (
        policy_input.belief_state.library.get(selected_belief.belief_id).belief_type
        == "unknown"
    )


def _persistence_decision(policy_input: PolicyInput) -> str:
    if _has_corrective_feedback(policy_input.learner_feedback) and policy_input.persistence >= 0.50:
        return "reconsider"
    if policy_input.persistence < 0.30 and policy_input.attempt_number >= 2:
        return "stop"
    return "continue"


def _response_constraints(
    policy_input: PolicyInput,
    selected_belief: LearnerBelief | None,
    action: str,
) -> tuple[str, ...]:
    if action == "request_hint":
        return ("request_hint_only", "do_not_answer")

    if selected_belief is None:
        return ("do_not_solve_from_external_knowledge", "express_uncertainty")

    definition = policy_input.belief_state.library.get(selected_belief.belief_id)
    if definition.belief_type == "unknown":
        return ("do_not_solve_from_external_knowledge", "express_uncertainty")

    constraints: list[str] = []
    if definition.transformation_id is not None:
        constraints.append(f"apply_transformation:{definition.transformation_id}")
    if definition.belief_type == "partial":
        constraints.append("produce_partial_reasoning")
    constraints.append("preserve_selected_belief")
    if definition.belief_type == "misconception":
        constraints.append("do_not_self_correct")
    if action == "revise":
        constraints.append("use_learner_facing_corrective_feedback")
    return tuple(constraints)


def _first_existing_recent_belief(policy_input: PolicyInput) -> LearnerBelief | None:
    for belief_id in policy_input.recent_activated_belief_ids:
        belief = _belief_by_id(policy_input.belief_state, belief_id)
        if belief is not None:
            return belief
    return None


def _belief_by_id(
    belief_state: LearnerBeliefState,
    belief_id: str,
) -> LearnerBelief | None:
    for belief in belief_state.beliefs:
        if belief.belief_id == belief_id:
            return belief
    return None


def _has_corrective_feedback(feedback: LearnerFeedback) -> bool:
    return feedback.feedback_type == "corrective_feedback"


def _coerce_feedback(
    feedback: LearnerFeedback | Mapping[str, object] | None,
) -> LearnerFeedback:
    if feedback is None:
        return LearnerFeedback("none")
    return ensure_learner_feedback(feedback)


def _immutable_probability_mapping(
    name: str,
    values: Mapping[str, float],
) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{name} must be a mapping")
    copied: dict[str, float] = {}
    for key, value in values.items():
        validate_snake_case_id(f"{name} key", key)
        _validate_probability(f"{name}[{key!r}]", value)
        copied[key] = float(value)
    return MappingProxyType(copied)


def _canonical_id_tuple(
    name: str,
    values: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    result = tuple(values)
    for value in result:
        validate_snake_case_id(f"{name} item", value)
    return result


def _constraint_tuple(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError("response_constraints must be a tuple or list")
    constraints = tuple(values)
    for constraint in constraints:
        _validate_constraint(constraint)
    return constraints


def _validate_constraint(value: str) -> None:
    _validate_non_empty_string("response_constraints item", value)
    if len(value) > 80:
        raise ValueError("response_constraints items must be short")
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    forbidden = sorted(token for token in FORBIDDEN_POLICY_TOKENS if token in normalized)
    if forbidden:
        raise ValueError(
            "response_constraints cannot contain evaluator-only or benchmark-only "
            f"metadata: {', '.join(forbidden)}"
        )
    parts = value.split(":")
    if len(parts) > 2:
        raise ValueError("response_constraints items must be symbolic")
    for part in parts:
        validate_snake_case_id("response_constraints item", part)


def _reject_extra_fields(name: str, extra_fields: Mapping[str, object]) -> None:
    if not extra_fields:
        return
    normalized = {
        str(key).lower().replace("-", "_").replace(" ", "_")
        for key in extra_fields
    }
    forbidden = sorted(normalized & FORBIDDEN_POLICY_TOKENS)
    if forbidden:
        raise ValueError(
            f"{name} cannot contain evaluator-only or benchmark-only field(s): "
            + ", ".join(forbidden)
        )
    raise ValueError(
        f"{name} cannot contain extra field(s): "
        + ", ".join(sorted(str(key) for key in extra_fields))
    )


def _validate_probability(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def _validate_nonnegative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


__all__ = [
    "ACTION_VALUES",
    "BehaviorPlan",
    "LearnerPolicy",
    "PERSISTENCE_DECISION_VALUES",
    "POLICY_VERSION",
    "PolicyInput",
    "REASONING_MODE_VALUES",
]
