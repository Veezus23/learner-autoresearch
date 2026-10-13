"""Concept-level transformation identifiers for fixed beliefs.

The registry intentionally stores identity and metadata only. Transformations
do not solve benchmark questions and do not generate answer text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


@dataclass(frozen=True)
class TransformationDefinition:
    transformation_id: str
    domain: str
    description: str
    version: str = "transformation_v0"

    def __post_init__(self) -> None:
        validate_snake_case_id("transformation_id", self.transformation_id)
        validate_snake_case_id("domain", self.domain)
        _validate_non_empty_string("description", self.description)
        _validate_non_empty_string("version", self.version)


@dataclass(frozen=True)
class TransformationRegistry:
    _transformations: Mapping[str, TransformationDefinition]

    def __init__(self, transformations: Iterable[TransformationDefinition]) -> None:
        by_id: dict[str, TransformationDefinition] = {}
        for transformation in transformations:
            if transformation.transformation_id in by_id:
                raise ValueError(
                    f"duplicate transformation_id: {transformation.transformation_id}"
                )
            by_id[transformation.transformation_id] = transformation
        object.__setattr__(self, "_transformations", MappingProxyType(by_id))

    def get(self, transformation_id: str) -> TransformationDefinition:
        return self._transformations[transformation_id]

    def contains(self, transformation_id: str | None) -> bool:
        return transformation_id is not None and transformation_id in self._transformations

    def ids(self) -> frozenset[str]:
        return frozenset(self._transformations)

    def definitions(self) -> tuple[TransformationDefinition, ...]:
        return tuple(self._transformations.values())


def validate_snake_case_id(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty snake_case string")
    if not SNAKE_CASE_RE.fullmatch(value):
        raise ValueError(f"{name} must be snake_case")


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


DEFAULT_TRANSFORMATION_REGISTRY = TransformationRegistry(
    (
        TransformationDefinition(
            "enumerate_all_subsets",
            "sets",
            "Represent a set by enumerating all of its subsets.",
        ),
        TransformationDefinition(
            "return_original_set",
            "sets",
            "Represent a power-set prompt by returning the original set.",
        ),
        TransformationDefinition(
            "enumerate_nonempty_subsets",
            "sets",
            "Represent subset enumeration while omitting the empty set.",
        ),
        TransformationDefinition(
            "treat_elements_as_subsets",
            "sets",
            "Treat individual elements as if they were subsets.",
        ),
        TransformationDefinition(
            "distribute_negative_correctly",
            "algebra",
            "Apply a leading negative to every term in a grouped expression.",
        ),
        TransformationDefinition(
            "distribute_negative_first_term_only",
            "algebra",
            "Apply a leading negative to only the first term.",
        ),
        TransformationDefinition(
            "apply_inverse_operation",
            "algebra",
            "Use inverse operations to preserve equality while isolating a term.",
        ),
        TransformationDefinition(
            "move_term_without_sign_change",
            "algebra",
            "Move a term across equality without changing its sign.",
        ),
        TransformationDefinition(
            "combine_like_terms",
            "algebra",
            "Combine terms that share the same variable part.",
        ),
        TransformationDefinition(
            "combine_unlike_terms",
            "algebra",
            "Combine terms without requiring the same variable part.",
        ),
        TransformationDefinition(
            "add_with_common_denominator",
            "fractions",
            "Add fractions after representing them with a common denominator.",
        ),
        TransformationDefinition(
            "add_numerators_and_denominators",
            "fractions",
            "Add numerators together and denominators together.",
        ),
        TransformationDefinition(
            "divide_by_multiplying_reciprocal",
            "fractions",
            "Divide fractions by multiplying by the reciprocal of the divisor.",
        ),
        TransformationDefinition(
            "invert_wrong_operand",
            "fractions",
            "Invert the wrong fraction while attempting fraction division.",
        ),
        TransformationDefinition(
            "preserve_ratio_order",
            "fractions",
            "Preserve the requested A-to-B order in a ratio.",
        ),
        TransformationDefinition(
            "reverse_ratio_order",
            "fractions",
            "Reverse the requested A-to-B order in a ratio.",
        ),
    )
)


__all__ = [
    "DEFAULT_TRANSFORMATION_REGISTRY",
    "SNAKE_CASE_RE",
    "TransformationDefinition",
    "TransformationRegistry",
    "validate_snake_case_id",
]
