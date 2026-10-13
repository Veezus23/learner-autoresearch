from dataclasses import FrozenInstanceError

import pytest

from learner.feedback import LearnerFeedback


def test_feedback_is_immutable_and_canonicalizes_sequences():
    feedback = LearnerFeedback(
        feedback_type="correctness_only",
        learner_message="That answer is correct.",
        target_concept_ids=["fraction_addition"],
        referenced_belief_ids=["fraction_addition_correct"],
        source="tutor",
    )

    assert feedback.target_concept_ids == ("fraction_addition",)
    assert feedback.referenced_belief_ids == ("fraction_addition_correct",)
    with pytest.raises(FrozenInstanceError):
        feedback.feedback_type = "hint"


def test_invalid_feedback_type_and_source_are_rejected():
    with pytest.raises(ValueError, match="invalid feedback_type"):
        LearnerFeedback("score", source="tutor")

    with pytest.raises(ValueError, match="invalid feedback source"):
        LearnerFeedback("hint", source="evaluator")


def test_feedback_requires_canonical_snake_case_ids():
    with pytest.raises(ValueError, match="snake_case"):
        LearnerFeedback(
            "hint",
            target_concept_ids=("FractionAddition",),
            referenced_belief_ids=("fraction_addition_correct",),
        )

    with pytest.raises(ValueError, match="snake_case"):
        LearnerFeedback(
            "hint",
            target_concept_ids=("fraction_addition",),
            referenced_belief_ids=("fraction-addition-correct",),
        )


def test_evaluator_outputs_cannot_enter_feedback_object():
    with pytest.raises(ValueError, match="evaluator-only"):
        LearnerFeedback(
            "correctness_only",
            target_concept_ids=("fraction_addition",),
            referenced_belief_ids=("fraction_addition_correct",),
            evaluator_score=0.92,
        )

    with pytest.raises(ValueError, match="hidden-label"):
        LearnerFeedback(
            "correctness_only",
            learner_message="hidden_label=correct",
            target_concept_ids=("fraction_addition",),
            referenced_belief_ids=("fraction_addition_correct",),
        )


def test_feedback_from_mapping_rejects_benchmark_expectations():
    with pytest.raises(ValueError, match="benchmark-only"):
        LearnerFeedback.from_mapping(
            {
                "feedback_type": "correctness_only",
                "learner_message": "Visible feedback.",
                "target_concept_ids": ("fraction_addition",),
                "referenced_belief_ids": ("fraction_addition_correct",),
                "source": "tutor",
                "expected_output": "not allowed",
            }
        )
