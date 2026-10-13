"""Deterministic learner-belief update rules."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from learner.belief_state import LearnerBelief, LearnerBeliefState
from learner.feedback import LearnerFeedback, ensure_learner_feedback


CORRECT_ANSWER_STRENGTH_GAIN = 0.04
INCORRECT_MISCONCEPTION_STRENGTH_GAIN = 0.01
HINT_TEMPORARY_STRENGTH_BOOST = 0.20
CORRECTIVE_MISCONCEPTION_STRENGTH_LOSS = 0.08
CORRECTIVE_CORRECT_STRENGTH_GAIN = 0.05
REPEATED_SUCCESS_CORRECT_STRENGTH_GAIN = 0.03
REPEATED_SUCCESS_UNKNOWN_STRENGTH_LOSS = 0.02
REPEATED_FAILURE_UNKNOWN_STRENGTH_GAIN = 0.03
REPEATED_FAILURE_CORRECT_STRENGTH_LOSS = 0.01


@dataclass(frozen=True)
class BeliefContext:
    """One-interaction belief activation context."""

    temporary_strength_boosts: Mapping[str, float]
    interactions_remaining: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.interactions_remaining, int) or self.interactions_remaining < 0:
            raise ValueError("interactions_remaining must be a non-negative integer")
        boosts = dict(self.temporary_strength_boosts)
        for belief_id, boost in boosts.items():
            if not isinstance(belief_id, str) or not belief_id:
                raise ValueError("temporary boost belief IDs must be non-empty strings")
            if isinstance(boost, bool) or not isinstance(boost, (int, float)):
                raise ValueError("temporary boost values must be numeric")
        object.__setattr__(self, "temporary_strength_boosts", MappingProxyType(boosts))

    def effective_strength(self, belief: LearnerBelief) -> float:
        boost = self.temporary_strength_boosts.get(belief.belief_id, 0.0)
        return _clamp_probability(belief.current_strength + boost)

    def consume_interaction(self) -> "BeliefContext":
        if self.interactions_remaining <= 1:
            return BeliefContext({})
        return BeliefContext(
            self.temporary_strength_boosts,
            interactions_remaining=self.interactions_remaining - 1,
        )


EMPTY_BELIEF_CONTEXT = BeliefContext({})


def update_after_correct_answer(
    state: LearnerBeliefState,
    activated_belief_id: str,
    feedback: LearnerFeedback | Mapping[str, object],
) -> LearnerBeliefState:
    learner_feedback = _require_feedback_type(
        feedback,
        {"correctness_only", "explanation"},
    )
    belief = _require_referenced_belief(state, activated_belief_id, learner_feedback)
    _require_belief_type(state, belief, {"correct"})

    return _replace_beliefs(
        state,
        (
            belief.with_updates(
                current_strength=_clamp_probability(
                    belief.current_strength + CORRECT_ANSWER_STRENGTH_GAIN
                ),
                evidence_count=belief.evidence_count + 1,
            ),
        ),
    )


def update_after_incorrect_answer(
    state: LearnerBeliefState,
    activated_belief_id: str,
    feedback: LearnerFeedback | Mapping[str, object],
) -> LearnerBeliefState:
    learner_feedback = _require_feedback_type(
        feedback,
        {"correctness_only", "explanation"},
    )
    belief = _require_referenced_belief(state, activated_belief_id, learner_feedback)
    belief_type = state.library.get(belief.belief_id).belief_type
    if belief_type == "correct":
        raise ValueError("incorrect answer update cannot target a correct belief")
    if belief_type == "misconception":
        strength = _clamp_probability(
            belief.current_strength + INCORRECT_MISCONCEPTION_STRENGTH_GAIN
        )
    else:
        strength = belief.current_strength

    return _replace_beliefs(
        state,
        (
            belief.with_updates(
                current_strength=strength,
                evidence_count=belief.evidence_count + 1,
            ),
        ),
    )


def update_after_hint(
    state: LearnerBeliefState,
    correct_belief_id: str,
    feedback: LearnerFeedback | Mapping[str, object],
) -> LearnerBeliefState:
    learner_feedback = _require_feedback_type(feedback, {"hint"})
    belief = _require_referenced_belief(state, correct_belief_id, learner_feedback)
    _require_belief_type(state, belief, {"correct"})
    return LearnerBeliefState(tuple(state.beliefs), state.library)


def belief_context_after_hint(
    state: LearnerBeliefState,
    correct_belief_id: str,
    feedback: LearnerFeedback | Mapping[str, object],
) -> BeliefContext:
    learner_feedback = _require_feedback_type(feedback, {"hint"})
    belief = _require_referenced_belief(state, correct_belief_id, learner_feedback)
    _require_belief_type(state, belief, {"correct"})
    return BeliefContext(
        {correct_belief_id: HINT_TEMPORARY_STRENGTH_BOOST},
        interactions_remaining=1,
    )


def update_after_corrective_feedback(
    state: LearnerBeliefState,
    misconception_belief_id: str,
    correct_belief_id: str,
    feedback: LearnerFeedback | Mapping[str, object],
) -> LearnerBeliefState:
    learner_feedback = _require_feedback_type(feedback, {"corrective_feedback"})
    misconception = _require_referenced_belief(
        state,
        misconception_belief_id,
        learner_feedback,
    )
    correct = _require_referenced_belief(state, correct_belief_id, learner_feedback)
    _require_belief_type(state, misconception, {"misconception"})
    _require_belief_type(state, correct, {"correct"})
    _require_same_concept(state, misconception, correct)

    return _replace_beliefs(
        state,
        (
            misconception.with_updates(
                current_strength=_clamp_probability(
                    misconception.current_strength
                    - CORRECTIVE_MISCONCEPTION_STRENGTH_LOSS
                ),
                evidence_count=misconception.evidence_count + 1,
            ),
            correct.with_updates(
                current_strength=_clamp_probability(
                    correct.current_strength + CORRECTIVE_CORRECT_STRENGTH_GAIN
                ),
                evidence_count=correct.evidence_count + 1,
            ),
        ),
    )


def update_after_repeated_success(
    state: LearnerBeliefState,
    activated_belief_id: str,
    *,
    unknown_belief_id: str | None = None,
) -> LearnerBeliefState:
    belief = _require_state_belief(state, activated_belief_id)
    _require_belief_type(state, belief, {"correct"})
    concept_id = state.library.get(belief.belief_id).concept_id
    unknown = _unknown_for_concept(state, concept_id, unknown_belief_id)

    updated: list[LearnerBelief] = [
        belief.with_updates(
            current_strength=_clamp_probability(
                belief.current_strength + REPEATED_SUCCESS_CORRECT_STRENGTH_GAIN
            ),
            evidence_count=belief.evidence_count + 1,
        )
    ]
    if unknown is not None:
        updated.append(
            unknown.with_updates(
                current_strength=_clamp_probability(
                    unknown.current_strength - REPEATED_SUCCESS_UNKNOWN_STRENGTH_LOSS
                ),
                evidence_count=unknown.evidence_count + 1,
            )
        )
    return _replace_beliefs(state, tuple(updated))


def update_after_repeated_failure(
    state: LearnerBeliefState,
    activated_belief_id: str,
    *,
    unknown_belief_id: str | None = None,
    weaken_active_correct_belief: bool = True,
) -> LearnerBeliefState:
    belief = _require_state_belief(state, activated_belief_id)
    concept_id = state.library.get(belief.belief_id).concept_id
    belief_type = state.library.get(belief.belief_id).belief_type
    unknown = _unknown_for_concept(state, concept_id, unknown_belief_id)

    updated: list[LearnerBelief] = []
    if unknown is not None:
        updated.append(
            unknown.with_updates(
                current_strength=_clamp_probability(
                    unknown.current_strength + REPEATED_FAILURE_UNKNOWN_STRENGTH_GAIN
                ),
                evidence_count=unknown.evidence_count + 1,
            )
        )
    if belief_type == "correct" and weaken_active_correct_belief:
        updated.append(
            belief.with_updates(
                current_strength=_clamp_probability(
                    belief.current_strength - REPEATED_FAILURE_CORRECT_STRENGTH_LOSS
                ),
                evidence_count=belief.evidence_count + 1,
            )
        )
    if not updated:
        return LearnerBeliefState(tuple(state.beliefs), state.library)
    return _replace_beliefs(state, tuple(updated))


def _require_feedback_type(
    feedback: LearnerFeedback | Mapping[str, object],
    allowed_types: set[str],
) -> LearnerFeedback:
    learner_feedback = ensure_learner_feedback(feedback)
    if learner_feedback.feedback_type not in allowed_types:
        raise ValueError(
            "feedback_type must be one of: " + ", ".join(sorted(allowed_types))
        )
    return learner_feedback


def _require_referenced_belief(
    state: LearnerBeliefState,
    belief_id: str,
    feedback: LearnerFeedback,
) -> LearnerBelief:
    belief = _require_state_belief(state, belief_id)
    if belief_id not in feedback.referenced_belief_ids:
        raise ValueError(f"feedback does not reference belief_id: {belief_id}")
    concept_id = state.library.get(belief_id).concept_id
    if concept_id not in feedback.target_concept_ids:
        raise ValueError(
            f"feedback target_concept_ids do not include concept_id: {concept_id}"
        )
    return belief


def _require_state_belief(state: LearnerBeliefState, belief_id: str) -> LearnerBelief:
    for belief in state.beliefs:
        if belief.belief_id == belief_id:
            return belief
    raise ValueError(f"belief_id not present in learner state: {belief_id}")


def _require_belief_type(
    state: LearnerBeliefState,
    belief: LearnerBelief,
    allowed_types: set[str],
) -> None:
    belief_type = state.library.get(belief.belief_id).belief_type
    if belief_type not in allowed_types:
        raise ValueError(
            f"belief_id {belief.belief_id} has type {belief_type}; expected one of: "
            + ", ".join(sorted(allowed_types))
        )


def _require_same_concept(
    state: LearnerBeliefState,
    first: LearnerBelief,
    second: LearnerBelief,
) -> None:
    first_concept = state.library.get(first.belief_id).concept_id
    second_concept = state.library.get(second.belief_id).concept_id
    if first_concept != second_concept:
        raise ValueError("belief IDs must belong to the same concept")


def _unknown_for_concept(
    state: LearnerBeliefState,
    concept_id: str,
    unknown_belief_id: str | None,
) -> LearnerBelief | None:
    if unknown_belief_id is None:
        return state.unknown_belief(concept_id)
    unknown = _require_state_belief(state, unknown_belief_id)
    _require_belief_type(state, unknown, {"unknown"})
    unknown_concept = state.library.get(unknown.belief_id).concept_id
    if unknown_concept != concept_id:
        raise ValueError("unknown belief must belong to the activated concept")
    return unknown


def _replace_beliefs(
    state: LearnerBeliefState,
    replacements: Iterable[LearnerBelief],
) -> LearnerBeliefState:
    replacement_tuple = tuple(replacements)
    by_id = {belief.belief_id: belief for belief in replacement_tuple}
    if len(by_id) != len(replacement_tuple):
        raise ValueError("duplicate replacement belief IDs")
    updated = tuple(by_id.get(belief.belief_id, belief) for belief in state.beliefs)
    return LearnerBeliefState(updated, state.library)


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


__all__ = [
    "BeliefContext",
    "CORRECT_ANSWER_STRENGTH_GAIN",
    "CORRECTIVE_CORRECT_STRENGTH_GAIN",
    "CORRECTIVE_MISCONCEPTION_STRENGTH_LOSS",
    "EMPTY_BELIEF_CONTEXT",
    "HINT_TEMPORARY_STRENGTH_BOOST",
    "INCORRECT_MISCONCEPTION_STRENGTH_GAIN",
    "REPEATED_FAILURE_CORRECT_STRENGTH_LOSS",
    "REPEATED_FAILURE_UNKNOWN_STRENGTH_GAIN",
    "REPEATED_SUCCESS_CORRECT_STRENGTH_GAIN",
    "REPEATED_SUCCESS_UNKNOWN_STRENGTH_LOSS",
    "belief_context_after_hint",
    "update_after_correct_answer",
    "update_after_corrective_feedback",
    "update_after_hint",
    "update_after_incorrect_answer",
    "update_after_repeated_failure",
    "update_after_repeated_success",
]
