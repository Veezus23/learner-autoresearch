from dataclasses import fields
from types import MappingProxyType

import pytest

from learner.belief_state import LearnerBelief, LearnerBeliefState
from learner.feedback import LearnerFeedback
from learner.policy import BehaviorPlan, LearnerPolicy, PolicyInput


def belief(belief_id, strength=0.5, confidence=0.5, **overrides):
    values = {
        "belief_id": belief_id,
        "current_strength": strength,
        "belief_confidence": confidence,
    }
    values.update(overrides)
    return LearnerBelief(**values)


def state_with(*beliefs):
    return LearnerBeliefState(tuple(beliefs))


def base_state():
    return state_with(
        belief("fraction_addition_correct", strength=0.30, confidence=0.50),
        belief("adds_denominators", strength=0.80, confidence=0.90),
        belief("fraction_addition_unknown", strength=0.10, confidence=0.20),
    )


def policy_input(**overrides):
    values = {
        "question_text": "Add the fractions.",
        "primary_concept_id": "fraction_addition",
        "secondary_concept_ids": (),
        "topic_mastery": {"fraction_addition": 0.4},
        "prerequisite_mastery": {
            "equivalent_fractions": 0.8,
            "common_denominator": 0.8,
        },
        "concept_confidence": 0.6,
        "persistence": 0.6,
        "hint_tendency": 0.2,
        "guess_tendency": 0.2,
        "belief_state": base_state(),
        "attempt_number": 0,
        "hint_available": True,
        "learner_feedback": LearnerFeedback("none"),
        "recent_activated_belief_ids": (),
        "current_turn": 3,
    }
    values.update(overrides)
    return PolicyInput(**values)


def plan(**overrides):
    return LearnerPolicy().plan_response(policy_input(**overrides))


def test_identical_inputs_produce_identical_plans():
    input_value = policy_input()

    first = LearnerPolicy().plan_response(input_value)
    second = LearnerPolicy().plan_response(input_value)

    assert first == second


def test_correct_belief_can_be_selected():
    state = state_with(
        belief("fraction_addition_correct", strength=0.90, confidence=0.90),
        belief("adds_denominators", strength=0.10, confidence=0.10),
    )

    result = plan(belief_state=state)

    assert result.activated_belief_id == "fraction_addition_correct"
    assert result.action == "answer"
    assert result.reasoning_mode == "apply_belief"
    assert "apply_transformation:add_with_common_denominator" in result.response_constraints


def test_misconception_belief_can_be_selected():
    result = plan()

    assert result.activated_belief_id == "adds_denominators"
    assert result.action == "answer"
    assert result.reasoning_mode == "apply_belief"
    assert "apply_transformation:add_numerators_and_denominators" in result.response_constraints
    assert "do_not_self_correct" in result.response_constraints


def test_activation_ranking_is_respected():
    state = state_with(
        belief("fraction_addition_correct", strength=0.60, confidence=0.20),
        belief("adds_denominators", strength=0.60, confidence=0.90),
    )

    result = plan(belief_state=state)

    assert result.activated_belief_id == "adds_denominators"


def test_unknown_belief_requests_hint_when_tendency_is_high():
    state = state_with(
        belief("fraction_addition_unknown", strength=1.0, confidence=1.0),
    )

    result = plan(
        belief_state=state,
        hint_available=True,
        hint_tendency=0.50,
        guess_tendency=1.0,
    )

    assert result.activated_belief_id == "fraction_addition_unknown"
    assert result.action == "request_hint"
    assert result.reasoning_mode == "no_rule"
    assert result.response_constraints == ("request_hint_only", "do_not_answer")


def test_unknown_belief_guesses_when_hint_is_not_used():
    state = state_with(
        belief("fraction_addition_unknown", strength=1.0, confidence=1.0),
    )

    result = plan(
        belief_state=state,
        hint_available=False,
        hint_tendency=1.0,
        guess_tendency=0.50,
    )

    assert result.action == "guess"
    assert result.reasoning_mode == "guess"


def test_unknown_belief_abstains_when_no_tendency_is_high():
    state = state_with(
        belief("fraction_addition_unknown", strength=1.0, confidence=1.0),
    )

    result = plan(
        belief_state=state,
        hint_available=False,
        hint_tendency=0.49,
        guess_tendency=0.49,
    )

    assert result.action == "abstain"
    assert result.reasoning_mode == "no_rule"


def test_partial_belief_produces_partial_attempt():
    state = state_with(
        belief("forgets_empty_set", strength=1.0, confidence=0.8),
        belief("power_set_correct", strength=0.1, confidence=0.1),
    )

    result = plan(
        primary_concept_id="power_set",
        topic_mastery={"power_set": 0.3},
        prerequisite_mastery={"subset": 1.0, "empty_set": 1.0, "set_notation": 1.0},
        belief_state=state,
    )

    assert result.activated_belief_id == "forgets_empty_set"
    assert result.action == "answer"
    assert result.reasoning_mode == "partial_attempt"
    assert "produce_partial_reasoning" in result.response_constraints


def test_corrective_feedback_can_produce_revise():
    feedback = LearnerFeedback(
        "corrective_feedback",
        learner_message="Try using a common denominator.",
        target_concept_ids=("fraction_addition",),
        referenced_belief_ids=("adds_denominators", "fraction_addition_correct"),
    )

    result = plan(
        learner_feedback=feedback,
        recent_activated_belief_ids=("adds_denominators",),
        persistence=0.50,
    )

    assert result.action == "revise"
    assert result.persistence_decision == "reconsider"
    assert "use_learner_facing_corrective_feedback" in result.response_constraints


def test_corrective_feedback_without_persistence_does_not_revise():
    feedback = LearnerFeedback(
        "corrective_feedback",
        learner_message="Try using a common denominator.",
        target_concept_ids=("fraction_addition",),
        referenced_belief_ids=("adds_denominators", "fraction_addition_correct"),
    )

    result = plan(
        learner_feedback=feedback,
        recent_activated_belief_ids=("adds_denominators",),
        persistence=0.49,
    )

    assert result.action != "revise"


def test_low_persistence_after_repeated_attempts_can_stop():
    result = plan(persistence=0.29, attempt_number=2)

    assert result.persistence_decision == "stop"


@pytest.mark.parametrize("attempt_number", [0, 5, 100])
def test_expressed_confidence_remains_bounded(attempt_number):
    result = plan(
        concept_confidence=1.0,
        guess_tendency=1.0,
        attempt_number=attempt_number,
    )

    assert 0.0 <= result.expressed_confidence <= 1.0


def test_request_hint_confidence_is_capped():
    state = state_with(
        belief("fraction_addition_unknown", strength=1.0, confidence=1.0),
    )

    result = plan(
        belief_state=state,
        concept_confidence=1.0,
        hint_available=True,
        hint_tendency=1.0,
        guess_tendency=1.0,
    )

    assert result.action == "request_hint"
    assert result.expressed_confidence == 0.49


def test_abstain_confidence_is_capped():
    state = state_with()

    result = plan(
        belief_state=state,
        concept_confidence=1.0,
        hint_available=False,
        hint_tendency=0.0,
        guess_tendency=0.0,
    )

    assert result.action == "abstain"
    assert result.expressed_confidence == 0.49


def test_no_correctness_field_exists_in_behavior_plan():
    result = plan()

    names = {field.name for field in fields(result)}

    assert "correct_answer" not in names
    assert "should_answer_correctly" not in names
    assert not hasattr(result, "correct_answer")
    assert not hasattr(result, "should_answer_correctly")


def test_forbidden_policy_input_fields_do_not_exist():
    names = {field.name for field in fields(PolicyInput)}

    forbidden = {
        "case_id",
        "correct_answer",
        "answer_key",
        "evaluator_label",
        "expected_correctness",
        "expected_hint_interval",
        "scoring_weight",
        "validation_aggregate",
    }
    assert names.isdisjoint(forbidden)


def test_forbidden_policy_input_extra_fields_are_rejected():
    with pytest.raises(ValueError, match="case_id"):
        policy_input(case_id="dev_1")

    with pytest.raises(ValueError, match="correct_answer"):
        policy_input(correct_answer="1/2")

    with pytest.raises(ValueError, match="evaluator_label"):
        policy_input(evaluator_label="misconception")

    with pytest.raises(ValueError, match="scoring_weight"):
        policy_input(scoring_weight=1.0)


def test_response_constraints_contain_no_benchmark_answers():
    result = plan(question_text="What is 1/2 + 1/3?")

    joined = " ".join(result.response_constraints)

    assert "5/6" not in joined
    assert "case_id" not in joined
    assert "expected" not in joined


def test_policy_does_not_mutate_learner_belief_state():
    state = base_state()
    before = state

    LearnerPolicy().plan_response(policy_input(belief_state=state))

    assert state == before
    assert state.beliefs[0].current_strength == 0.30


def test_inactive_and_retired_beliefs_are_never_selected():
    state = state_with(
        belief(
            "adds_denominators",
            strength=1.0,
            confidence=1.0,
            status="inactive",
        ),
        belief(
            "fraction_addition_unknown",
            strength=1.0,
            confidence=1.0,
            status="retired",
        ),
        belief("fraction_addition_correct", strength=0.1, confidence=0.1),
    )

    result = plan(belief_state=state)

    assert result.activated_belief_id == "fraction_addition_correct"


def test_temporary_hint_context_can_affect_activation_without_permanent_change():
    state = state_with(
        belief("fraction_addition_correct", strength=0.49, confidence=0.70),
        belief("adds_denominators", strength=0.60, confidence=0.70),
    )
    feedback = LearnerFeedback(
        "hint",
        learner_message="Think about the common denominator.",
        target_concept_ids=("fraction_addition",),
        referenced_belief_ids=("fraction_addition_correct",),
    )

    result = plan(belief_state=state, learner_feedback=feedback)

    assert result.activated_belief_id == "fraction_addition_correct"
    assert state.beliefs[0].current_strength == 0.49
    assert state.beliefs[1].current_strength == 0.60


def test_missing_active_beliefs_are_handled_safely():
    result = plan(
        belief_state=state_with(),
        hint_available=True,
        hint_tendency=0.50,
        guess_tendency=0.0,
    )

    assert result.activated_belief_id is None
    assert result.action == "request_hint"
    assert result.reasoning_mode == "no_rule"


def test_policy_input_is_immutable_and_copies_mutable_collections():
    topic_mastery = {"fraction_addition": 0.4}
    input_value = policy_input(topic_mastery=topic_mastery)
    topic_mastery["fraction_addition"] = 1.0

    assert isinstance(input_value.topic_mastery, MappingProxyType)
    assert input_value.topic_mastery["fraction_addition"] == 0.4
    with pytest.raises(TypeError):
        input_value.topic_mastery["fraction_addition"] = 0.9


def test_behavior_plan_validates_activated_belief_against_state():
    with pytest.raises(ValueError, match="must exist"):
        BehaviorPlan(
            activated_belief_id="not_in_state",
            action="answer",
            expressed_confidence=0.5,
            persistence_decision="continue",
            reasoning_mode="apply_belief",
            response_constraints=("preserve_selected_belief",),
            _belief_state=base_state(),
        )
