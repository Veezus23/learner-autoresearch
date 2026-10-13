from expression.mock_adapter import MockExpressionAdapter
from expression.prompt_builder import FAILURE_TOKEN, build_expression_prompt
from tests.test_prompt_builder import make_input, make_plan


def test_identical_prompt_produces_identical_output():
    adapter = MockExpressionAdapter()
    prompt = build_expression_prompt(make_input())

    assert adapter.generate(prompt) == adapter.generate(prompt)


def test_answer_action_produces_answer_style_response():
    output = MockExpressionAdapter().generate(build_expression_prompt(make_input()))

    assert "add_numerators_and_denominators" in output
    assert "hint" not in output.lower()


def test_request_hint_produces_only_hint_request():
    plan = make_plan(
        activated_belief_id=None,
        action="request_hint",
        expressed_confidence=0.4,
        reasoning_mode="no_rule",
        response_constraints=("request_hint_only", "do_not_answer"),
    )
    output = MockExpressionAdapter().generate(
        build_expression_prompt(
            make_input(
                behavior_plan=plan,
                activated_belief_definition=None,
                activated_learner_belief=None,
                transformation_metadata=None,
            )
        )
    )

    assert output == "Could I have a hint?"


def test_abstain_produces_uncertainty_without_answer():
    plan = make_plan(
        activated_belief_id=None,
        action="abstain",
        expressed_confidence=0.2,
        reasoning_mode="no_rule",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )
    output = MockExpressionAdapter().generate(
        build_expression_prompt(
            make_input(
                behavior_plan=plan,
                activated_belief_definition=None,
                activated_learner_belief=None,
                transformation_metadata=None,
            )
        )
    )

    assert "not sure" in output.lower()
    assert "=" not in output


def test_guess_produces_concise_low_certainty_response():
    plan = make_plan(
        activated_belief_id=None,
        action="guess",
        expressed_confidence=0.3,
        reasoning_mode="guess",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )
    output = MockExpressionAdapter().generate(
        build_expression_prompt(
            make_input(
                behavior_plan=plan,
                activated_belief_definition=None,
                activated_learner_belief=None,
                transformation_metadata=None,
            )
        )
    )

    assert "guess" in output.lower()
    assert len(output.split()) <= 15


def test_mock_adapter_respects_failure_token_path():
    prompt = build_expression_prompt(make_input()) + "\n- force_failure: true"

    assert MockExpressionAdapter().generate(prompt) == FAILURE_TOKEN


def test_mock_adapter_contains_no_answer_keys_or_case_specific_mappings():
    import inspect

    source = inspect.getsource(MockExpressionAdapter)

    assert "case_id" not in source
    assert "answer_key" not in source
    assert "correct_answer" not in source
    assert "5/6" not in source
