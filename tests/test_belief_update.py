import pytest

from learner.belief_state import LearnerBelief, LearnerBeliefState
from learner.belief_update import (
    belief_context_after_hint,
    update_after_correct_answer,
    update_after_corrective_feedback,
    update_after_hint,
    update_after_incorrect_answer,
    update_after_repeated_failure,
    update_after_repeated_success,
)
from learner.feedback import LearnerFeedback


def belief(belief_id, strength=0.5, confidence=0.5, **overrides):
    values = {
        "belief_id": belief_id,
        "current_strength": strength,
        "belief_confidence": confidence,
    }
    values.update(overrides)
    return LearnerBelief(**values)


def make_state(**overrides):
    beliefs = (
        belief("fraction_addition_correct", strength=0.50, confidence=0.60),
        belief("adds_denominators", strength=0.70, confidence=0.80),
        belief("fraction_addition_unknown", strength=0.20, confidence=0.30),
        belief("power_set_correct", strength=0.40, confidence=0.50),
    )
    values = {"beliefs": beliefs}
    values.update(overrides)
    return LearnerBeliefState(**values)


def feedback(feedback_type, concept="fraction_addition", belief_ids=None):
    return LearnerFeedback(
        feedback_type=feedback_type,
        learner_message="Learner-visible feedback.",
        target_concept_ids=(concept,),
        referenced_belief_ids=tuple(belief_ids or ("fraction_addition_correct",)),
        source="tutor",
    )


def by_id(state, belief_id):
    return next(belief for belief in state.beliefs if belief.belief_id == belief_id)


def test_correct_feedback_strengthens_the_correct_belief():
    state = make_state()
    updated = update_after_correct_answer(
        state,
        "fraction_addition_correct",
        feedback("correctness_only"),
    )

    assert by_id(updated, "fraction_addition_correct").current_strength == pytest.approx(0.54)
    assert by_id(updated, "fraction_addition_correct").evidence_count == 1
    assert by_id(updated, "fraction_addition_correct").activation_count == 0
    assert updated.library is state.library


def test_incorrect_answer_minimally_reinforces_a_misconception():
    state = make_state()
    updated = update_after_incorrect_answer(
        state,
        "adds_denominators",
        feedback("correctness_only", belief_ids=("adds_denominators",)),
    )

    assert by_id(updated, "adds_denominators").current_strength == pytest.approx(0.71)
    assert by_id(updated, "adds_denominators").evidence_count == 1


def test_partial_or_unknown_incorrect_answer_strength_is_unchanged():
    state = make_state()
    updated = update_after_incorrect_answer(
        state,
        "fraction_addition_unknown",
        feedback("correctness_only", belief_ids=("fraction_addition_unknown",)),
    )

    assert by_id(updated, "fraction_addition_unknown").current_strength == pytest.approx(0.20)
    assert by_id(updated, "fraction_addition_unknown").evidence_count == 1


def test_hint_boost_is_temporary_and_does_not_change_permanent_strength():
    state = make_state()
    hint_feedback = feedback("hint")

    updated = update_after_hint(state, "fraction_addition_correct", hint_feedback)
    context = belief_context_after_hint(state, "fraction_addition_correct", hint_feedback)

    original = by_id(state, "fraction_addition_correct")
    permanent = by_id(updated, "fraction_addition_correct")
    assert permanent.current_strength == original.current_strength
    assert context.effective_strength(permanent) == pytest.approx(0.70)
    assert context.consume_interaction().effective_strength(permanent) == permanent.current_strength


def test_corrective_feedback_weakens_misconception_and_strengthens_correct_belief():
    state = make_state()
    updated = update_after_corrective_feedback(
        state,
        "adds_denominators",
        "fraction_addition_correct",
        feedback(
            "corrective_feedback",
            belief_ids=("adds_denominators", "fraction_addition_correct"),
        ),
    )

    assert by_id(updated, "adds_denominators").current_strength == pytest.approx(0.62)
    assert by_id(updated, "fraction_addition_correct").current_strength == pytest.approx(0.55)
    assert by_id(updated, "adds_denominators").evidence_count == 1
    assert by_id(updated, "fraction_addition_correct").evidence_count == 1


def test_unrelated_beliefs_remain_unchanged():
    state = make_state()
    updated = update_after_correct_answer(
        state,
        "fraction_addition_correct",
        feedback("correctness_only"),
    )

    assert by_id(updated, "adds_denominators") == by_id(state, "adds_denominators")
    assert by_id(updated, "power_set_correct") == by_id(state, "power_set_correct")


def test_all_values_remain_bounded():
    state = make_state(
        beliefs=(
            belief("fraction_addition_correct", strength=0.99, confidence=1.0),
            belief("adds_denominators", strength=0.01, confidence=0.0),
            belief("fraction_addition_unknown", strength=0.99, confidence=0.2),
        )
    )

    state = update_after_correct_answer(
        state,
        "fraction_addition_correct",
        feedback("correctness_only"),
    )
    state = update_after_corrective_feedback(
        state,
        "adds_denominators",
        "fraction_addition_correct",
        feedback(
            "corrective_feedback",
            belief_ids=("adds_denominators", "fraction_addition_correct"),
        ),
    )
    state = update_after_repeated_failure(state, "fraction_addition_correct")

    for item in state.beliefs:
        assert 0.0 <= item.current_strength <= 1.0
        assert 0.0 <= item.belief_confidence <= 1.0


def test_original_state_is_unchanged():
    state = make_state()
    updated = update_after_incorrect_answer(
        state,
        "adds_denominators",
        feedback("correctness_only", belief_ids=("adds_denominators",)),
    )

    assert updated is not state
    assert by_id(state, "adds_denominators").current_strength == 0.70
    assert by_id(state, "adds_denominators").evidence_count == 0


def test_evaluator_outputs_cannot_enter_update_feedback():
    state = make_state()

    with pytest.raises(ValueError, match="evaluator-only"):
        update_after_correct_answer(
            state,
            "fraction_addition_correct",
            {
                "feedback_type": "correctness_only",
                "learner_message": "Visible feedback.",
                "target_concept_ids": ("fraction_addition",),
                "referenced_belief_ids": ("fraction_addition_correct",),
                "source": "tutor",
                "evaluator_score": 1.0,
            },
        )


def test_unknown_or_mismatched_belief_ids_are_rejected():
    state = make_state()

    with pytest.raises(ValueError, match="not present"):
        update_after_correct_answer(
            state,
            "not_in_state",
            feedback("correctness_only", belief_ids=("not_in_state",)),
        )

    with pytest.raises(ValueError, match="feedback target_concept_ids"):
        update_after_correct_answer(
            state,
            "fraction_addition_correct",
            feedback(
                "correctness_only",
                concept="power_set",
                belief_ids=("fraction_addition_correct",),
            ),
        )

    with pytest.raises(ValueError, match="expected one of"):
        update_after_correct_answer(
            state,
            "adds_denominators",
            feedback("correctness_only", belief_ids=("adds_denominators",)),
        )


def test_corrective_feedback_requires_explicit_corrective_feedback():
    state = make_state()

    with pytest.raises(ValueError, match="feedback_type"):
        update_after_corrective_feedback(
            state,
            "adds_denominators",
            "fraction_addition_correct",
            feedback(
                "correctness_only",
                belief_ids=("adds_denominators", "fraction_addition_correct"),
            ),
        )


def test_repeated_success_strengthens_correct_and_weakens_unknown():
    state = make_state()
    updated = update_after_repeated_success(state, "fraction_addition_correct")

    assert by_id(updated, "fraction_addition_correct").current_strength == pytest.approx(0.53)
    assert by_id(updated, "fraction_addition_unknown").current_strength == pytest.approx(0.18)


def test_repeated_failure_uses_conservative_belief_only_update():
    state = make_state()
    updated = update_after_repeated_failure(state, "fraction_addition_correct")

    assert by_id(updated, "fraction_addition_unknown").current_strength == pytest.approx(0.23)
    assert by_id(updated, "fraction_addition_correct").current_strength == pytest.approx(0.49)
    assert by_id(updated, "adds_denominators") == by_id(state, "adds_denominators")
