"""Deterministic fixed learner-state update rules.

The constants below define conservative V0 transition magnitudes. These rules
are fixed infrastructure; future autoresearch should optimize learner policy
behavior, not these state-transition semantics.
"""

from __future__ import annotations

from learner.state import (
    InteractionRecord,
    LearnerState,
    bounded_increment,
    clamp_probability,
)


CORRECT_MASTERY_GAIN = 0.03
CORRECT_CONFIDENCE_GAIN = 0.04
INCORRECT_CONFIDENCE_LOSS = 0.05
HINT_CONFIDENCE_GAIN = 0.03
HINT_TENDENCY_GAIN = 0.02
CORRECTIVE_FEEDBACK_MISCONCEPTION_REDUCTION = 0.10
CORRECTIVE_FEEDBACK_CONFIDENCE_GAIN = 0.02
REPEATED_FAILURE_HINT_GAIN = 0.08
REPEATED_FAILURE_GUESS_GAIN = 0.04
REPEATED_FAILURE_PERSISTENCE_LOSS = 0.06
DEFAULT_CONCEPT_VALUE = 0.5


def update_after_correct_answer(
    state: LearnerState,
    concept: str,
    confidence_before: float,
    requested_hint: bool = False,
    misconception_used: str | None = None,
    attempt_number: int = 1,
) -> LearnerState:
    mastery = dict(state.topic_mastery)
    confidence = dict(state.confidence)
    mastery[concept] = bounded_increment(
        mastery.get(concept, DEFAULT_CONCEPT_VALUE),
        CORRECT_MASTERY_GAIN,
    )
    confidence_after = bounded_increment(
        confidence.get(concept, confidence_before),
        CORRECT_CONFIDENCE_GAIN,
    )
    confidence[concept] = confidence_after
    updated = state.with_updates(topic_mastery=mastery, confidence=confidence)
    return updated.with_history_record(
        InteractionRecord(
            concept=concept,
            was_correct=True,
            requested_hint=requested_hint,
            received_feedback=False,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            misconception_used=misconception_used,
            attempt_number=attempt_number,
        )
    )


def update_after_incorrect_answer(
    state: LearnerState,
    concept: str,
    confidence_before: float,
    requested_hint: bool = False,
    misconception_used: str | None = None,
    attempt_number: int = 1,
) -> LearnerState:
    confidence = dict(state.confidence)
    confidence_after = bounded_increment(
        confidence.get(concept, confidence_before),
        -INCORRECT_CONFIDENCE_LOSS,
    )
    confidence[concept] = confidence_after
    updated = state.with_updates(confidence=confidence)
    return updated.with_history_record(
        InteractionRecord(
            concept=concept,
            was_correct=False,
            requested_hint=requested_hint,
            received_feedback=False,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            misconception_used=misconception_used,
            attempt_number=attempt_number,
        )
    )


def update_after_hint(
    state: LearnerState,
    concept: str,
    confidence_before: float,
    attempt_number: int = 1,
) -> LearnerState:
    confidence = dict(state.confidence)
    confidence_after = bounded_increment(
        confidence.get(concept, confidence_before),
        HINT_CONFIDENCE_GAIN,
    )
    confidence[concept] = confidence_after
    updated = state.with_updates(
        confidence=confidence,
        hint_tendency=bounded_increment(state.hint_tendency, HINT_TENDENCY_GAIN),
    )
    return updated.with_history_record(
        InteractionRecord(
            concept=concept,
            was_correct=False,
            requested_hint=True,
            received_feedback=False,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            misconception_used=None,
            attempt_number=attempt_number,
        )
    )


def update_after_corrective_feedback(
    state: LearnerState,
    concept: str,
    misconception: str,
    confidence_before: float,
    attempt_number: int = 1,
) -> LearnerState:
    strength = dict(state.misconception_strength)
    strength[misconception] = bounded_increment(
        strength.get(misconception, DEFAULT_CONCEPT_VALUE),
        -CORRECTIVE_FEEDBACK_MISCONCEPTION_REDUCTION,
    )
    active = set(state.active_misconceptions)
    if strength[misconception] <= 0.0:
        active.discard(misconception)
    else:
        active.add(misconception)

    confidence = dict(state.confidence)
    confidence_after = bounded_increment(
        confidence.get(concept, confidence_before),
        CORRECTIVE_FEEDBACK_CONFIDENCE_GAIN,
    )
    confidence[concept] = confidence_after
    updated = state.with_updates(
        confidence=confidence,
        active_misconceptions=frozenset(active),
        misconception_strength=strength,
    )
    return updated.with_history_record(
        InteractionRecord(
            concept=concept,
            was_correct=False,
            requested_hint=False,
            received_feedback=True,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            misconception_used=misconception,
            attempt_number=attempt_number,
        )
    )


def update_after_repeated_failure(
    state: LearnerState,
    concept: str,
    failure_count: int,
    confidence_before: float,
    misconception_used: str | None = None,
) -> LearnerState:
    if not isinstance(failure_count, int) or failure_count < 2:
        raise ValueError("failure_count must be an integer of at least 2")

    scaled_hint_gain = REPEATED_FAILURE_HINT_GAIN * min(failure_count, 5) / 5.0
    scaled_guess_gain = REPEATED_FAILURE_GUESS_GAIN * min(failure_count, 5) / 5.0
    scaled_persistence_loss = REPEATED_FAILURE_PERSISTENCE_LOSS * min(failure_count, 5) / 5.0
    confidence = dict(state.confidence)
    confidence_after = clamp_probability(confidence.get(concept, confidence_before))

    updated = state.with_updates(
        hint_tendency=bounded_increment(state.hint_tendency, scaled_hint_gain),
        guess_tendency=bounded_increment(state.guess_tendency, scaled_guess_gain),
        persistence=bounded_increment(state.persistence, -scaled_persistence_loss),
    )
    return updated.with_history_record(
        InteractionRecord(
            concept=concept,
            was_correct=False,
            requested_hint=False,
            received_feedback=False,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            misconception_used=misconception_used,
            attempt_number=failure_count,
        )
    )
