"""Fixed catalog of concept-level belief definitions."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from cognition.belief_definition import BeliefDefinition
from cognition.prerequisite_graph import DEFAULT_PREREQUISITE_GRAPH, PrerequisiteGraph
from cognition.transformations import (
    DEFAULT_TRANSFORMATION_REGISTRY,
    TransformationRegistry,
)


@dataclass(frozen=True)
class BeliefLibrary:
    _definitions: tuple[BeliefDefinition, ...]
    _by_id: Mapping[str, BeliefDefinition]
    _by_concept: Mapping[str, tuple[BeliefDefinition, ...]]
    _graph: PrerequisiteGraph
    _transformations: TransformationRegistry

    def __init__(
        self,
        definitions: Iterable[BeliefDefinition] = (),
        *,
        prerequisite_graph: PrerequisiteGraph = DEFAULT_PREREQUISITE_GRAPH,
        transformations: TransformationRegistry = DEFAULT_TRANSFORMATION_REGISTRY,
    ) -> None:
        definition_tuple = tuple(definitions)
        by_id: dict[str, BeliefDefinition] = {}
        by_concept: dict[str, list[BeliefDefinition]] = {}

        for definition in definition_tuple:
            if definition.belief_id in by_id:
                raise ValueError(f"duplicate belief_id: {definition.belief_id}")
            by_id[definition.belief_id] = definition
            by_concept.setdefault(definition.concept_id, []).append(definition)

        frozen_by_concept = {
            concept_id: tuple(concept_definitions)
            for concept_id, concept_definitions in by_concept.items()
        }

        object.__setattr__(self, "_definitions", definition_tuple)
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))
        object.__setattr__(self, "_by_concept", MappingProxyType(frozen_by_concept))
        object.__setattr__(self, "_graph", prerequisite_graph)
        object.__setattr__(self, "_transformations", transformations)
        self.validate()

    def add_definition(self, definition: BeliefDefinition) -> "BeliefLibrary":
        return BeliefLibrary(
            self._definitions + (definition,),
            prerequisite_graph=self._graph,
            transformations=self._transformations,
        )

    def get(self, belief_id: str) -> BeliefDefinition:
        return self._by_id[belief_id]

    def contains(self, belief_id: str) -> bool:
        return belief_id in self._by_id

    def definitions(self) -> tuple[BeliefDefinition, ...]:
        return self._definitions

    def definitions_for_concept(self, concept_id: str) -> tuple[BeliefDefinition, ...]:
        self._graph.validate_concept(concept_id)
        return self._by_concept.get(concept_id, ())

    def correct_definitions(
        self, concept_id: str | None = None
    ) -> tuple[BeliefDefinition, ...]:
        return self._definitions_by_type("correct", concept_id)

    def misconception_definitions(
        self, concept_id: str | None = None
    ) -> tuple[BeliefDefinition, ...]:
        return self._definitions_by_type("misconception", concept_id)

    def partial_definitions(
        self, concept_id: str | None = None
    ) -> tuple[BeliefDefinition, ...]:
        return self._definitions_by_type("partial", concept_id)

    def unknown_definition(self, concept_id: str) -> BeliefDefinition | None:
        unknowns = self._definitions_by_type("unknown", concept_id)
        return unknowns[0] if unknowns else None

    def validate(self) -> None:
        unknown_concepts: set[str] = set()
        seen_unknowns: set[str] = set()

        for definition in self._definitions:
            self._graph.validate_concept(definition.concept_id)
            self._graph.validate_references(definition.prerequisite_concept_ids)

            if definition.belief_type == "unknown":
                if definition.concept_id in seen_unknowns:
                    raise ValueError(
                        f"multiple unknown definitions for concept: {definition.concept_id}"
                    )
                seen_unknowns.add(definition.concept_id)
                continue

            if not self._transformations.contains(definition.transformation_id):
                raise ValueError(
                    "definition references an unregistered transformation: "
                    f"{definition.belief_id}"
                )

        if unknown_concepts:
            raise ValueError(
                "unknown concept(s) in belief library: " + ", ".join(unknown_concepts)
            )

    def _definitions_by_type(
        self, belief_type: str, concept_id: str | None
    ) -> tuple[BeliefDefinition, ...]:
        definitions = (
            self.definitions_for_concept(concept_id)
            if concept_id is not None
            else self._definitions
        )
        return tuple(
            definition
            for definition in definitions
            if definition.belief_type == belief_type
        )


def _correct(
    concept_id: str,
    transformation_id: str,
    prerequisites: tuple[str, ...],
    description: str,
) -> BeliefDefinition:
    return BeliefDefinition(
        belief_id=f"{concept_id}_correct",
        concept_id=concept_id,
        belief_type="correct",
        transformation_id=transformation_id,
        prerequisite_concept_ids=prerequisites,
        description=description,
    )


def _unknown(concept_id: str) -> BeliefDefinition:
    return BeliefDefinition(
        belief_id=f"{concept_id}_unknown",
        concept_id=concept_id,
        belief_type="unknown",
        transformation_id=None,
        prerequisite_concept_ids=(),
        description=f"No usable rule is available for {concept_id}.",
    )


DEFAULT_BELIEF_DEFINITIONS: tuple[BeliefDefinition, ...] = (
    _correct(
        "power_set",
        "enumerate_all_subsets",
        ("set_notation", "subset", "empty_set"),
        "A power set contains every subset of the original set.",
    ),
    BeliefDefinition(
        "power_set_means_original_set",
        "power_set",
        "misconception",
        "return_original_set",
        ("subset",),
        "Treats a power set as the original set rather than a set of subsets.",
    ),
    BeliefDefinition(
        "forgets_empty_set",
        "power_set",
        "partial",
        "enumerate_nonempty_subsets",
        ("subset", "empty_set"),
        "Lists subsets while omitting the empty set.",
    ),
    _unknown("power_set"),
    _correct(
        "subset",
        "enumerate_all_subsets",
        ("set_notation",),
        "Recognizes a subset relation by checking membership against a set.",
    ),
    BeliefDefinition(
        "elements_are_subsets",
        "subset",
        "misconception",
        "treat_elements_as_subsets",
        ("set_notation", "subset"),
        "Treats individual elements as if they were subsets.",
    ),
    _unknown("subset"),
    _correct(
        "negative_distribution",
        "distribute_negative_correctly",
        ("integer_signs", "distributive_property"),
        "Applies a leading negative to every term in a grouped expression.",
    ),
    BeliefDefinition(
        "distributes_negative_incorrectly",
        "negative_distribution",
        "misconception",
        "distribute_negative_first_term_only",
        ("integer_signs", "distributive_property"),
        "Applies the leading negative to only part of a grouped expression.",
    ),
    _unknown("negative_distribution"),
    _correct(
        "linear_equation",
        "apply_inverse_operation",
        ("inverse_operations", "equation_balance"),
        "Uses inverse operations while preserving equality.",
    ),
    BeliefDefinition(
        "moves_term_without_sign_change",
        "linear_equation",
        "misconception",
        "move_term_without_sign_change",
        ("inverse_operations", "equation_balance"),
        "Moves a term across equality without changing the operation.",
    ),
    _unknown("linear_equation"),
    _correct(
        "like_terms",
        "combine_like_terms",
        (),
        "Combines only terms with matching variable parts.",
    ),
    BeliefDefinition(
        "combines_unlike_terms",
        "like_terms",
        "misconception",
        "combine_unlike_terms",
        ("like_terms",),
        "Combines terms without matching their variable parts.",
    ),
    _unknown("like_terms"),
    _correct(
        "fraction_addition",
        "add_with_common_denominator",
        ("equivalent_fractions", "common_denominator"),
        "Adds fractions by using a common denominator.",
    ),
    BeliefDefinition(
        "adds_denominators",
        "fraction_addition",
        "misconception",
        "add_numerators_and_denominators",
        ("equivalent_fractions", "common_denominator"),
        "Adds numerators together and denominators together.",
    ),
    _unknown("fraction_addition"),
    _correct(
        "fraction_division",
        "divide_by_multiplying_reciprocal",
        ("reciprocal", "fraction_multiplication"),
        "Divides fractions by multiplying by the reciprocal of the divisor.",
    ),
    BeliefDefinition(
        "inverts_wrong_fraction",
        "fraction_division",
        "misconception",
        "invert_wrong_operand",
        ("reciprocal", "fraction_multiplication"),
        "Inverts the wrong operand during fraction division.",
    ),
    _unknown("fraction_division"),
    _correct(
        "ratio_order",
        "preserve_ratio_order",
        (),
        "Preserves the requested order when writing a ratio.",
    ),
    BeliefDefinition(
        "ratio_order_reversed",
        "ratio_order",
        "misconception",
        "reverse_ratio_order",
        ("ratio_order",),
        "Reverses the requested order when writing a ratio.",
    ),
    _unknown("ratio_order"),
)

DEFAULT_BELIEF_LIBRARY = BeliefLibrary(DEFAULT_BELIEF_DEFINITIONS)


__all__ = [
    "BeliefLibrary",
    "DEFAULT_BELIEF_DEFINITIONS",
    "DEFAULT_BELIEF_LIBRARY",
]
