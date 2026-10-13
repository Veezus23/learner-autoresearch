from cognition.belief_library import DEFAULT_BELIEF_LIBRARY
from cognition.transformations import DEFAULT_TRANSFORMATION_REGISTRY
from expression.prompt_builder import FAILURE_TOKEN, build_expression_prompt
from expression.types import ExpressionInput
from learner.belief_state import LearnerBelief
from learner.feedback import LearnerFeedback
from learner.policy import BehaviorPlan


def make_plan(action="answer", reasoning_mode="apply_belief", **overrides):
    values = {
        "activated_belief_id": "adds_denominators",
        "action": action,
        "expressed_confidence": 0.64,
        "persistence_decision": "continue",
        "reasoning_mode": reasoning_mode,
        "response_constraints": (
            "apply_transformation:add_numerators_and_denominators",
            "preserve_selected_belief",
            "do_not_self_correct",
        ),
    }
    values.update(overrides)
    return BehaviorPlan(**values)


def make_input(**overrides):
    transformation = DEFAULT_TRANSFORMATION_REGISTRY.get(
        "add_numerators_and_denominators"
    )
    values = {
        "question_text": "Add 1/2 and 1/3.",
        "behavior_plan": make_plan(),
        "activated_belief_definition": DEFAULT_BELIEF_LIBRARY.get("adds_denominators"),
        "activated_learner_belief": LearnerBelief("adds_denominators", 0.8, 0.7),
        "transformation_metadata": {
            "domain": transformation.domain,
            "description": transformation.description,
        },
    }
    values.update(overrides)
    return ExpressionInput(**values)


def test_prompt_says_model_is_expression_engine():
    prompt = build_expression_prompt(make_input())

    assert "You are an expression engine, not the learner." in prompt


def test_prompt_forbids_independent_solving_and_self_correction():
    prompt = build_expression_prompt(make_input())

    assert "Do not independently solve the problem." in prompt
    assert "Do not replace or repair the selected belief." in prompt
    assert "Do not use external correctness knowledge." in prompt
    assert "Do not self-correct unless the selected action is revise." in prompt
    assert FAILURE_TOKEN in prompt


def test_prompt_includes_core_plan_and_belief_metadata():
    prompt = build_expression_prompt(make_input())

    assert "Student-facing question:" in prompt
    assert "- action: answer" in prompt
    assert "- expressed_confidence: 0.64" in prompt
    assert "- reasoning_mode: apply_belief" in prompt
    assert "Adds numerators together and denominators together." in prompt
    assert "- transformation: add_numerators_and_denominators" in prompt


def test_answer_action_prompt_has_answer_specific_instructions():
    prompt = build_expression_prompt(make_input())

    assert "Express an answer based on the selected belief and transformation." in prompt
    assert "Do not ask for a hint." in prompt
    assert "Preserve the selected belief." in prompt


def test_request_hint_prompt_requires_hint_only():
    plan = make_plan(
        activated_belief_id=None,
        action="request_hint",
        expressed_confidence=0.4,
        reasoning_mode="no_rule",
        response_constraints=("request_hint_only", "do_not_answer"),
    )
    prompt = build_expression_prompt(
        make_input(
            behavior_plan=plan,
            activated_belief_definition=None,
            activated_learner_belief=None,
            transformation_metadata=None,
        )
    )

    assert "Ask for a hint only." in prompt
    assert "Do not answer the question." in prompt


def test_revise_prompt_includes_prior_response_and_feedback():
    plan = make_plan(action="revise")
    feedback = LearnerFeedback(
        "corrective_feedback",
        learner_message="Use a common denominator.",
        target_concept_ids=("fraction_addition",),
        referenced_belief_ids=("adds_denominators",),
    )
    prompt = build_expression_prompt(
        make_input(
            behavior_plan=plan,
            prior_response_text="I added straight across.",
            learner_feedback=feedback,
        )
    )

    assert "Revision context:" in prompt
    assert "I added straight across." in prompt
    assert "Use a common denominator." in prompt


def test_non_revise_prompt_omits_revision_context():
    prompt = build_expression_prompt(
        make_input(prior_response_text="Old response should not be included.")
    )

    assert "Revision context:" not in prompt
    assert "Old response should not be included." not in prompt


def test_partial_attempt_prompt_preserves_incompleteness():
    plan = make_plan(
        activated_belief_id="forgets_empty_set",
        reasoning_mode="partial_attempt",
        response_constraints=(
            "apply_transformation:enumerate_nonempty_subsets",
            "produce_partial_reasoning",
            "preserve_selected_belief",
        ),
    )
    transformation = DEFAULT_TRANSFORMATION_REGISTRY.get("enumerate_nonempty_subsets")
    prompt = build_expression_prompt(
        make_input(
            behavior_plan=plan,
            activated_belief_definition=DEFAULT_BELIEF_LIBRARY.get("forgets_empty_set"),
            activated_learner_belief=LearnerBelief("forgets_empty_set", 0.7, 0.5),
            transformation_metadata={
                "domain": transformation.domain,
                "description": transformation.description,
            },
        )
    )

    assert "Show incomplete but directionally coherent reasoning." in prompt
    assert "Do not fill in missing knowledge from external reasoning." in prompt


def test_no_rule_prompt_forbids_inventing_procedure():
    plan = make_plan(
        activated_belief_id=None,
        action="abstain",
        expressed_confidence=0.2,
        reasoning_mode="no_rule",
        response_constraints=("do_not_solve_from_external_knowledge",),
    )
    prompt = build_expression_prompt(
        make_input(
            behavior_plan=plan,
            activated_belief_definition=None,
            activated_learner_belief=None,
            transformation_metadata=None,
        )
    )

    assert "Do not invent a procedure." in prompt
    assert "no selected belief; no usable rule is available" in prompt
