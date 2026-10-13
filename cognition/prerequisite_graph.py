"""Canonical prerequisite graph for current benchmark concepts."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from cognition.transformations import validate_snake_case_id


DEFAULT_PREREQUISITES: dict[str, tuple[str, ...]] = {
    "set_notation": (),
    "empty_set": ("set_notation",),
    "subset": ("set_notation",),
    "power_set": ("set_notation", "subset", "empty_set"),
    "cardinality_power_set": ("power_set", "exponents"),
    "set_difference": ("set_notation",),
    "exponents": (),
    "integer_signs": (),
    "distributive_property": (),
    "negative_distribution": ("integer_signs", "distributive_property"),
    "inverse_operations": (),
    "equation_balance": (),
    "linear_equation": ("inverse_operations", "equation_balance"),
    "two_step_equation": ("linear_equation", "inverse_operations", "equation_balance"),
    "like_terms": (),
    "equivalent_fractions": (),
    "common_denominator": ("equivalent_fractions",),
    "fraction_addition": ("equivalent_fractions", "common_denominator"),
    "fraction_comparison": ("equivalent_fractions", "common_denominator"),
    "reciprocal": (),
    "fraction_multiplication": (),
    "fraction_division": ("reciprocal", "fraction_multiplication"),
    "ratio_order": (),
}


@dataclass(frozen=True)
class PrerequisiteGraph:
    _prerequisites: Mapping[str, tuple[str, ...]]

    def __init__(self, prerequisites: Mapping[str, Iterable[str]]) -> None:
        normalized: dict[str, tuple[str, ...]] = {}
        for concept_id, direct in prerequisites.items():
            validate_snake_case_id("concept_id", concept_id)
            normalized_direct = tuple(direct)
            for prerequisite_id in normalized_direct:
                validate_snake_case_id("prerequisite_concept_id", prerequisite_id)
            if len(set(normalized_direct)) != len(normalized_direct):
                raise ValueError(f"duplicate prerequisite for concept: {concept_id}")
            normalized[concept_id] = normalized_direct

        missing = sorted(
            prerequisite_id
            for direct in normalized.values()
            for prerequisite_id in direct
            if prerequisite_id not in normalized
        )
        if missing:
            raise ValueError(
                "referenced prerequisite concept(s) are not defined: "
                + ", ".join(missing)
            )

        self._raise_if_cyclic(normalized)
        object.__setattr__(self, "_prerequisites", MappingProxyType(normalized))

    def concepts(self) -> frozenset[str]:
        return frozenset(self._prerequisites)

    def contains(self, concept_id: str) -> bool:
        return concept_id in self._prerequisites

    def direct_prerequisites(self, concept_id: str) -> tuple[str, ...]:
        self.validate_concept(concept_id)
        return self._prerequisites[concept_id]

    def transitive_prerequisites(self, concept_id: str) -> tuple[str, ...]:
        self.validate_concept(concept_id)
        visited: set[str] = set()
        ordered: list[str] = []

        def visit(current: str) -> None:
            for prerequisite_id in self._prerequisites[current]:
                if prerequisite_id in visited:
                    continue
                visited.add(prerequisite_id)
                ordered.append(prerequisite_id)
                visit(prerequisite_id)

        visit(concept_id)
        return tuple(ordered)

    def validate_concept(self, concept_id: str) -> None:
        validate_snake_case_id("concept_id", concept_id)
        if concept_id not in self._prerequisites:
            raise ValueError(f"unknown concept_id: {concept_id}")

    def validate_references(self, concept_ids: Iterable[str]) -> None:
        for concept_id in concept_ids:
            self.validate_concept(concept_id)

    @staticmethod
    def _raise_if_cyclic(prerequisites: Mapping[str, tuple[str, ...]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(concept_id: str) -> None:
            if concept_id in visiting:
                raise ValueError(f"cycle detected at concept_id: {concept_id}")
            if concept_id in visited:
                return
            visiting.add(concept_id)
            for prerequisite_id in prerequisites[concept_id]:
                visit(prerequisite_id)
            visiting.remove(concept_id)
            visited.add(concept_id)

        for concept_id in prerequisites:
            visit(concept_id)


DEFAULT_PREREQUISITE_GRAPH = PrerequisiteGraph(DEFAULT_PREREQUISITES)


__all__ = [
    "DEFAULT_PREREQUISITE_GRAPH",
    "DEFAULT_PREREQUISITES",
    "PrerequisiteGraph",
]
