from dataclasses import FrozenInstanceError, fields

import pytest

from learner.state import (
    MAX_HISTORY_LENGTH,
    InteractionRecord,
    LearnerState,
)


def make_state(**overrides):
    values = {
        "learner_id": "learner_a",
        "topic_mastery": {"sets.power_set": 0.4},
        "prerequisite_mastery": {"subset": 0.5},
        "confidence": {"sets.power_set": 0.3},
        "active_misconceptions": frozenset({"forgets_empty_set"}),
        "misconception_strength": {"forgets_empty_set": 0.7},
        "hint_tendency": 0.6,
        "guess_tendency": 0.2,
        "persistence": 0.8,
        "interaction_history": (),
    }
    values.update(overrides)
    return LearnerState(**values)


def make_record(index=1):
    return InteractionRecord(
        concept="sets.power_set",
        was_correct=False,
        requested_hint=True,
        received_feedback=False,
        confidence_before=0.2,
        confidence_after=0.25,
        misconception_used="forgets_empty_set",
        attempt_number=index,
    )


def test_invalid_probability_values_are_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        make_state(topic_mastery={"sets.power_set": 1.2})

    with pytest.raises(ValueError, match="between 0 and 1"):
        make_state(hint_tendency=-0.1)

    with pytest.raises(ValueError, match="between 0 and 1"):
        InteractionRecord(
            concept="sets.power_set",
            was_correct=True,
            requested_hint=False,
            received_feedback=False,
            confidence_before=0.0,
            confidence_after=2.0,
            misconception_used=None,
            attempt_number=1,
        )


def test_history_remains_bounded():
    state = make_state()

    for index in range(MAX_HISTORY_LENGTH + 10):
        state = state.with_history_record(make_record(index + 1))

    assert len(state.interaction_history) == MAX_HISTORY_LENGTH
    assert state.interaction_history[0].attempt_number == 11
    assert state.interaction_history[-1].attempt_number == MAX_HISTORY_LENGTH + 10


def test_state_is_frozen_and_updates_return_new_state():
    state = make_state()
    updated = state.with_history_record(make_record())

    assert updated is not state
    assert len(state.interaction_history) == 0
    assert len(updated.interaction_history) == 1
    with pytest.raises(FrozenInstanceError):
        state.hint_tendency = 0.1


def test_no_evaluator_only_or_benchmark_label_fields_present():
    state_field_names = {field.name for field in fields(LearnerState)}

    forbidden = {
        "correct_answer",
        "correct_answers",
        "expected_behavior",
        "validation_labels",
        "scoring_weights",
        "optimization_case_ids",
        "case_id",
        "case_ids",
    }
    assert state_field_names.isdisjoint(forbidden)


def test_forbidden_state_update_fields_rejected():
    state = make_state()

    with pytest.raises(ValueError, match="forbidden learner-state field"):
        state.with_updates(correct_answer="8")
