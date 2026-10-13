from dataclasses import fields
from types import MappingProxyType

import pytest

from cognition.belief_library import DEFAULT_BELIEF_LIBRARY
from cognition.transformations import DEFAULT_TRANSFORMATION_REGISTRY
from expression.types import ExpressionInput, StudentResponse
from learner.belief_state import LearnerBelief
from learner.feedback import LearnerFeedback
from learner.policy import BehaviorPlan


def behavior_plan(**overrides):
    values = {
        "activated_belief_id": "adds_denominators",
        "action": "answer",
        "expressed_confidence": 0.62,
        "persistence_decision": "continue",
        "reasoning_mode": "apply_belief",
        "response_constraints": (
            "apply_transformation:add_numerators_and_denominators",
            "preserve_selected_belief",
            "do_not_self_correct",
        ),
    }
    values.update(overrides)
    return BehaviorPlan(**values)


def learner_belief(belief_id="adds_denominators"):
    return LearnerBelief(belief_id, 0.8, 0.7)


def belief_definition(belief_id="adds_denominators"):
    return DEFAULT_BELIEF_LIBRARY.get(belief_id)


def metadata(transformation_id="add_numerators_and_denominators"):
    definition = DEFAULT_TRANSFORMATION_REGISTRY.get(transformation_id)
    return {
        "transformation": definition.transformation_id,
        "domain": definition.domain,
        "description": definition.description,
    }


def expression_input(**overrides):
    values = {
        "question_text": "Add 1/2 and 1/3.",
        "behavior_plan": behavior_plan(),
        "activated_belief_definition": belief_definition(),
        "activated_learner_belief": learner_belief(),
        "transformation_metadata": metadata(),
        "prior_response_text": None,
        "learner_feedback": None,
    }
    values.update(overrides)
    return ExpressionInput(**values)


def test_expression_input_is_immutable_and_metadata_is_read_only():
    source = metadata()
    value = expression_input(transformation_metadata=source)
    source["domain"] = "changed"

    assert value.transformation_metadata["domain"] == "fractions"
    assert isinstance(value.transformation_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        value.transformation_metadata["domain"] = "changed"


def test_expression_input_requires_behavior_plan():
    with pytest.raises(ValueError, match="BehaviorPlan"):
        expression_input(behavior_plan=object())


def test_activated_belief_objects_must_match_plan():
    with pytest.raises(ValueError, match="match behavior_plan"):
        expression_input(activated_learner_belief=learner_belief("fraction_addition_correct"))

    no_belief_plan = behavior_plan(
        activated_belief_id=None,
        action="abstain",
        reasoning_mode="no_rule",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )
    with pytest.raises(ValueError, match="must be None"):
        expression_input(behavior_plan=no_belief_plan)


def test_no_belief_expression_input_is_allowed_with_no_belief_metadata():
    no_belief_plan = behavior_plan(
        activated_belief_id=None,
        action="abstain",
        expressed_confidence=0.3,
        reasoning_mode="no_rule",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )

    value = expression_input(
        behavior_plan=no_belief_plan,
        activated_belief_definition=None,
        activated_learner_belief=None,
        transformation_metadata=None,
    )

    assert value.activated_belief_definition is None
    assert value.activated_learner_belief is None


def test_forbidden_expression_input_extra_fields_are_rejected():
    for field_name in (
        "case_id",
        "correct_answer",
        "expected_output",
        "evaluator_label",
        "behavioral_fidelity_score",
        "scoring_weight",
        "hidden_test_metadata",
        "validation_aggregate",
        "optimization_hint",
    ):
        with pytest.raises(ValueError, match=field_name):
            expression_input(**{field_name: "forbidden"})


def test_student_response_matches_behavior_plan_fields():
    plan = behavior_plan()
    response = StudentResponse(
        response_text="I think I add across.",
        action=plan.action,
        expressed_confidence=plan.expressed_confidence,
        activated_belief_id=plan.activated_belief_id,
        generation_status="success",
        _behavior_plan=plan,
    )

    assert response.action == plan.action
    assert response.expressed_confidence == plan.expressed_confidence
    assert response.activated_belief_id == plan.activated_belief_id


def test_student_response_rejects_plan_mismatch():
    plan = behavior_plan()

    with pytest.raises(ValueError, match="action"):
        StudentResponse(
            response_text="Could I have a hint?",
            action="request_hint",
            expressed_confidence=plan.expressed_confidence,
            activated_belief_id=plan.activated_belief_id,
            generation_status="success",
            _behavior_plan=plan,
        )


def test_no_correctness_or_evaluator_fields_exist():
    input_names = {field.name for field in fields(ExpressionInput)}
    response_names = {field.name for field in fields(StudentResponse)}
    forbidden = {
        "correct_answer",
        "correctness",
        "evaluator_label",
        "behavioral_fidelity_score",
        "applied_misconception",
        "benchmark_expectation",
        "scoring_weight",
        "validation_aggregate",
    }

    assert input_names.isdisjoint(forbidden)
    assert response_names.isdisjoint(forbidden)


def test_learner_feedback_must_remain_learner_facing():
    with pytest.raises(ValueError, match="evaluator-only"):
        expression_input(
            learner_feedback={
                "feedback_type": "corrective_feedback",
                "learner_message": "Visible message.",
                "target_concept_ids": ("fraction_addition",),
                "referenced_belief_ids": ("adds_denominators",),
                "source": "tutor",
                "evaluator_score": 1.0,
            }
        )


def test_valid_learner_feedback_is_kept():
    feedback = LearnerFeedback(
        "corrective_feedback",
        learner_message="Use common denominators.",
        target_concept_ids=("fraction_addition",),
        referenced_belief_ids=("adds_denominators",),
    )

    value = expression_input(learner_feedback=feedback)

    assert value.learner_feedback is feedback
