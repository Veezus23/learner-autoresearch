"""Fixed belief definitions for concept-level cognition."""

from __future__ import annotations

from dataclasses import dataclass, fields

from cognition.transformations import validate_snake_case_id


ALLOWED_BELIEF_TYPES = frozenset({"correct", "misconception", "partial", "unknown"})
FORBIDDEN_DEFINITION_TOKENS = frozenset(
    {
        "case_id",
        "case_ids",
        "correct_answer",
        "answer_key",
        "answer_keys",
        "expected_output",
        "expected_outputs",
        "expected_behavior",
        "evaluator_label",
        "evaluator_labels",
        "validation_label",
        "validation_labels",
        "validation_metadata",
        "scoring_weight",
        "scoring_weights",
        "current_strength",
        "belief_confidence",
        "confidence",
    }
)


@dataclass(frozen=True)
class BeliefDefinition:
    belief_id: str
    concept_id: str
    belief_type: str
    transformation_id: str | None
    prerequisite_concept_ids: tuple[str, ...]
    description: str
    version: str = "belief_definition_v0"

    def __post_init__(self) -> None:
        validate_snake_case_id("belief_id", self.belief_id)
        validate_snake_case_id("concept_id", self.concept_id)
        validate_snake_case_id("belief_type", self.belief_type)
        if self.belief_type not in ALLOWED_BELIEF_TYPES:
            raise ValueError(f"invalid belief_type: {self.belief_type}")

        prerequisites = tuple(self.prerequisite_concept_ids)
        for concept_id in prerequisites:
            validate_snake_case_id("prerequisite_concept_ids item", concept_id)

        if self.transformation_id is not None:
            validate_snake_case_id("transformation_id", self.transformation_id)

        if self.belief_type == "unknown":
            if self.transformation_id is not None:
                raise ValueError("unknown beliefs must not have a transformation_id")

        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be a non-empty string")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("version must be a non-empty string")

        object.__setattr__(self, "prerequisite_concept_ids", prerequisites)
        self._validate_no_forbidden_metadata()

    def _validate_no_forbidden_metadata(self) -> None:
        field_names = {field.name for field in fields(self)}
        forbidden_fields = field_names & FORBIDDEN_DEFINITION_TOKENS
        if forbidden_fields:
            raise ValueError(
                "belief definitions cannot contain forbidden field(s): "
                + ", ".join(sorted(forbidden_fields))
            )

        values = (
            self.belief_id,
            self.concept_id,
            self.belief_type,
            self.transformation_id or "",
            " ".join(self.prerequisite_concept_ids),
            self.description,
            self.version,
        )
        normalized = " ".join(values).lower()
        matched = sorted(
            token for token in FORBIDDEN_DEFINITION_TOKENS if token in normalized
        )
        if matched:
            raise ValueError(
                "belief definitions cannot contain benchmark, evaluator, or "
                f"learner-state metadata: {', '.join(matched)}"
            )


__all__ = [
    "ALLOWED_BELIEF_TYPES",
    "BeliefDefinition",
    "FORBIDDEN_DEFINITION_TOKENS",
]
