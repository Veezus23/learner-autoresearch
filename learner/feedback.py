"""Learner-facing feedback boundary for fixed update rules."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from cognition.transformations import validate_snake_case_id


FEEDBACK_TYPES = frozenset(
    {
        "none",
        "correctness_only",
        "hint",
        "explanation",
        "corrective_feedback",
    }
)
FEEDBACK_SOURCES = frozenset({"tutor", "environment", "instructor"})
FORBIDDEN_FEEDBACK_TOKENS = frozenset(
    {
        "answer_key",
        "answer_keys",
        "benchmark_expectation",
        "benchmark_expectations",
        "behavioral_fidelity_score",
        "case_id",
        "case_ids",
        "correct_answer",
        "correct_answers",
        "detector_internal",
        "detector_internals",
        "detector_output",
        "detector_outputs",
        "evaluator_label",
        "evaluator_labels",
        "evaluator_output",
        "evaluator_outputs",
        "evaluator_score",
        "evaluator_scores",
        "expected_behavior",
        "expected_behaviors",
        "expected_output",
        "expected_outputs",
        "hidden_label",
        "hidden_labels",
        "scoring_weight",
        "scoring_weights",
        "validation_aggregate",
        "validation_aggregates",
        "validation_label",
        "validation_labels",
    }
)


@dataclass(frozen=True, init=False)
class LearnerFeedback:
    """Immutable feedback object visible to the simulated learner."""

    feedback_type: str
    learner_message: str
    target_concept_ids: tuple[str, ...]
    referenced_belief_ids: tuple[str, ...]
    source: str

    def __init__(
        self,
        feedback_type: str,
        learner_message: str = "",
        target_concept_ids: tuple[str, ...] | list[str] = (),
        referenced_belief_ids: tuple[str, ...] | list[str] = (),
        source: str = "tutor",
        **extra_fields: object,
    ) -> None:
        if extra_fields:
            _reject_forbidden_keys(extra_fields.keys())
            raise ValueError(
                "learner feedback cannot contain extra field(s): "
                + ", ".join(sorted(extra_fields))
            )

        _validate_feedback_type(feedback_type)
        _validate_message(learner_message)
        _validate_source(source)
        concepts = _canonical_id_tuple("target_concept_ids", target_concept_ids)
        beliefs = _canonical_id_tuple("referenced_belief_ids", referenced_belief_ids)

        object.__setattr__(self, "feedback_type", feedback_type)
        object.__setattr__(self, "learner_message", learner_message)
        object.__setattr__(self, "target_concept_ids", concepts)
        object.__setattr__(self, "referenced_belief_ids", beliefs)
        object.__setattr__(self, "source", source)
        self._validate_no_forbidden_metadata()

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "LearnerFeedback":
        if not isinstance(values, Mapping):
            raise ValueError("learner feedback must be a mapping")
        return cls(**dict(values))

    def _validate_no_forbidden_metadata(self) -> None:
        allowed = {field.name for field in fields(self)}
        _reject_forbidden_keys(allowed)

        normalized_values = " ".join(
            (
                self.feedback_type,
                self.learner_message,
                " ".join(self.target_concept_ids),
                " ".join(self.referenced_belief_ids),
                self.source,
            )
        )
        _reject_forbidden_text("learner feedback", normalized_values)


def ensure_learner_feedback(
    feedback: LearnerFeedback | Mapping[str, object],
) -> LearnerFeedback:
    if isinstance(feedback, LearnerFeedback):
        return feedback
    return LearnerFeedback.from_mapping(feedback)


def _validate_feedback_type(value: str) -> None:
    if value not in FEEDBACK_TYPES:
        raise ValueError(f"invalid feedback_type: {value}")


def _validate_source(value: str) -> None:
    if value not in FEEDBACK_SOURCES:
        raise ValueError(f"invalid feedback source: {value}")


def _validate_message(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("learner_message must be a string")
    _reject_forbidden_text("learner_message", value)


def _canonical_id_tuple(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    result = tuple(values)
    for value in result:
        validate_snake_case_id(f"{name} item", value)
    return result


def _reject_forbidden_keys(keys: object) -> None:
    normalized = {_normalize_token(str(key)) for key in keys}
    forbidden = sorted(normalized & FORBIDDEN_FEEDBACK_TOKENS)
    if forbidden:
        raise ValueError(
            "learner feedback cannot contain evaluator-only or benchmark-only "
            f"field(s): {', '.join(forbidden)}"
        )


def _reject_forbidden_text(name: str, value: str) -> None:
    normalized = _normalize_token(value)
    matched = sorted(
        token for token in FORBIDDEN_FEEDBACK_TOKENS if token in normalized
    )
    if matched:
        raise ValueError(
            f"{name} cannot contain evaluator-only, benchmark-only, or hidden-label "
            f"metadata: {', '.join(matched)}"
        )


def _normalize_token(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "FEEDBACK_SOURCES",
    "FEEDBACK_TYPES",
    "FORBIDDEN_FEEDBACK_TOKENS",
    "LearnerFeedback",
    "ensure_learner_feedback",
]
