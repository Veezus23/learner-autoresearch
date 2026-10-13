from learner.state import MAX_HISTORY_LENGTH, LearnerState
from learner.update import (
    update_after_correct_answer,
    update_after_corrective_feedback,
    update_after_hint,
    update_after_incorrect_answer,
    update_after_repeated_failure,
)


def make_state(**overrides):
    values = {
        "learner_id": "learner_b",
        "topic_mastery": {"fractions.addition": 0.3},
        "prerequisite_mastery": {"common_denominator": 0.2},
        "confidence": {"fractions.addition": 0.4},
        "active_misconceptions": frozenset({"adds_denominators"}),
        "misconception_strength": {"adds_denominators": 0.8},
        "hint_tendency": 0.4,
        "guess_tendency": 0.3,
        "persistence": 0.7,
        "interaction_history": (),
    }
    values.update(overrides)
    return LearnerState(**values)


def test_state_updates_remain_bounded_between_zero_and_one():
    state = make_state(
        topic_mastery={"fractions.addition": 0.99},
        confidence={"fractions.addition": 0.99},
        hint_tendency=0.99,
        guess_tendency=0.99,
        persistence=0.01,
    )

    state = update_after_correct_answer(state, "fractions.addition", confidence_before=0.99)
    state = update_after_hint(state, "fractions.addition", confidence_before=0.99)
    state = update_after_repeated_failure(
        state,
        "fractions.addition",
        failure_count=5,
        confidence_before=1.0,
    )

    assert all(0.0 <= value <= 1.0 for value in state.topic_mastery.values())
    assert all(0.0 <= value <= 1.0 for value in state.confidence.values())
    assert 0.0 <= state.hint_tendency <= 1.0
    assert 0.0 <= state.guess_tendency <= 1.0
    assert 0.0 <= state.persistence <= 1.0


def test_hint_can_increase_confidence_without_increasing_mastery():
    state = make_state()
    updated = update_after_hint(state, "fractions.addition", confidence_before=0.4)

    assert updated.confidence["fractions.addition"] > state.confidence["fractions.addition"]
    assert updated.topic_mastery["fractions.addition"] == state.topic_mastery["fractions.addition"]
    assert updated.interaction_history[-1].requested_hint


def test_corrective_feedback_can_weaken_misconception():
    state = make_state()
    updated = update_after_corrective_feedback(
        state,
        "fractions.addition",
        misconception="adds_denominators",
        confidence_before=0.4,
    )

    assert updated.misconception_strength["adds_denominators"] < state.misconception_strength["adds_denominators"]
    assert "adds_denominators" in updated.active_misconceptions
    assert updated.interaction_history[-1].received_feedback


def test_one_incorrect_answer_does_not_automatically_lower_mastery():
    state = make_state()
    updated = update_after_incorrect_answer(
        state,
        "fractions.addition",
        confidence_before=0.4,
        misconception_used="adds_denominators",
    )

    assert updated.topic_mastery["fractions.addition"] == state.topic_mastery["fractions.addition"]
    assert updated.confidence["fractions.addition"] < state.confidence["fractions.addition"]


def test_repeated_failure_changes_behavior_related_state():
    state = make_state()
    updated = update_after_repeated_failure(
        state,
        "fractions.addition",
        failure_count=4,
        confidence_before=0.4,
        misconception_used="adds_denominators",
    )

    assert updated.hint_tendency > state.hint_tendency
    assert updated.guess_tendency > state.guess_tendency
    assert updated.persistence < state.persistence
    assert updated.topic_mastery == state.topic_mastery


def test_update_functions_return_new_state_without_mutating_original():
    state = make_state()
    updated = update_after_correct_answer(state, "fractions.addition", confidence_before=0.4)

    assert updated is not state
    assert state.topic_mastery["fractions.addition"] == 0.3
    assert updated.topic_mastery["fractions.addition"] > state.topic_mastery["fractions.addition"]
    assert len(state.interaction_history) == 0
    assert len(updated.interaction_history) == 1


def test_update_history_remains_bounded():
    state = make_state()
    for index in range(MAX_HISTORY_LENGTH + 5):
        state = update_after_incorrect_answer(
            state,
            "fractions.addition",
            confidence_before=state.confidence["fractions.addition"],
            misconception_used="adds_denominators",
            attempt_number=index + 1,
        )

    assert len(state.interaction_history) == MAX_HISTORY_LENGTH
    assert state.interaction_history[0].attempt_number == 6
