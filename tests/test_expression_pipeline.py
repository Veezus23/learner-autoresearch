import copy
import sys

from expression import MockExpressionAdapter, express_response
from expression.adapter import ExternalExpressionAdapter
from tests.test_prompt_builder import make_input


def test_identical_expression_input_and_mock_adapter_produce_identical_response():
    expression_input = make_input()
    adapter = MockExpressionAdapter()

    first = express_response(expression_input, adapter)
    second = express_response(expression_input, adapter)

    assert first == second


def test_pipeline_returns_successful_student_response():
    response = express_response(make_input(), MockExpressionAdapter())

    assert response.generation_status == "success"
    assert response.action == "answer"
    assert response.activated_belief_id == "adds_denominators"


def test_pipeline_does_not_mutate_inputs_or_behavior_plan():
    expression_input = make_input()
    plan_before = copy.deepcopy(expression_input.behavior_plan)
    learner_belief_before = copy.deepcopy(expression_input.activated_learner_belief)

    express_response(expression_input, MockExpressionAdapter())

    assert expression_input.behavior_plan == plan_before
    assert expression_input.activated_learner_belief == learner_belief_before


def test_external_adapter_is_lightweight_callable_wrapper():
    adapter = ExternalExpressionAdapter(lambda prompt: "student response")

    assert adapter.generate("prompt") == "student response"


def test_pipeline_does_not_import_or_call_protected_runtime_packages():
    before = set(sys.modules)

    express_response(make_input(), MockExpressionAdapter())

    after = set(sys.modules)
    newly_loaded = after - before
    assert "evaluate" not in newly_loaded
    assert "prepare" not in newly_loaded
    assert "evaluator.scoring" not in newly_loaded
    assert "fixed.scoring" not in newly_loaded
