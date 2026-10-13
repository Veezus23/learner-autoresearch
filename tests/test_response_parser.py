from dataclasses import fields

from expression.prompt_builder import FAILURE_TOKEN
from expression.response_parser import parse_student_response
from tests.test_prompt_builder import make_input, make_plan


def test_failure_token_becomes_failed_status():
    value = parse_student_response(FAILURE_TOKEN, make_input())

    assert value.generation_status == "failed"
    assert value.failure_reason == "expression_failure_token"
    assert value.raw_model_output == FAILURE_TOKEN


def test_empty_output_is_rejected():
    value = parse_student_response("   ", make_input())

    assert value.generation_status == "rejected"
    assert value.failure_reason == "empty_output"


def test_internal_architecture_leakage_is_rejected():
    for term in (
        "BehaviorPlan",
        "PolicyInput",
        "belief_id",
        "transformation_id",
        "evaluator",
        "benchmark",
    ):
        value = parse_student_response(f"I used {term}.", make_input())

        assert value.generation_status == "rejected"
        assert value.failure_reason.startswith("internal_leakage")


def test_request_hint_rejects_substantive_answer():
    plan = make_plan(
        activated_belief_id=None,
        action="request_hint",
        expressed_confidence=0.4,
        reasoning_mode="no_rule",
        response_constraints=("request_hint_only", "do_not_answer"),
    )
    value = parse_student_response(
        "Could I have a hint? The answer is 5/6.",
        make_input(
            behavior_plan=plan,
            activated_belief_definition=None,
            activated_learner_belief=None,
            transformation_metadata=None,
        ),
    )

    assert value.generation_status == "rejected"
    assert value.failure_reason == "hint_response_contains_answer"


def test_request_hint_allows_hint_only():
    plan = make_plan(
        activated_belief_id=None,
        action="request_hint",
        expressed_confidence=0.4,
        reasoning_mode="no_rule",
        response_constraints=("request_hint_only", "do_not_answer"),
    )
    value = parse_student_response(
        "Could I have a hint?",
        make_input(
            behavior_plan=plan,
            activated_belief_definition=None,
            activated_learner_belief=None,
            transformation_metadata=None,
        ),
    )

    assert value.generation_status == "success"


def test_abstain_rejects_solution_like_output():
    plan = make_plan(
        activated_belief_id=None,
        action="abstain",
        expressed_confidence=0.2,
        reasoning_mode="no_rule",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )
    value = parse_student_response(
        "First combine the denominators, then the answer equals 5/6.",
        make_input(
            behavior_plan=plan,
            activated_belief_definition=None,
            activated_learner_belief=None,
            transformation_metadata=None,
        ),
    )

    assert value.generation_status == "rejected"
    assert value.failure_reason == "abstain_response_contains_solution"


def test_parser_preserves_plan_action_confidence_and_belief_id():
    expression_input = make_input()

    value = parse_student_response("I think I add across.", expression_input)

    assert value.action == expression_input.behavior_plan.action
    assert value.expressed_confidence == expression_input.behavior_plan.expressed_confidence
    assert value.activated_belief_id == expression_input.behavior_plan.activated_belief_id


def test_student_response_has_no_correctness_or_scoring_field():
    names = {field.name for field in fields(parse_student_response("I think this.", make_input()))}

    assert "correctness" not in names
    assert "correct_answer" not in names
    assert "applied_misconception" not in names
    assert "evaluator_label" not in names
    assert "benchmark_expectation" not in names
