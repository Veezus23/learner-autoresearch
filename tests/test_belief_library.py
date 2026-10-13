import json
from pathlib import Path
from types import MappingProxyType

import pytest

from cognition.belief_definition import BeliefDefinition
from cognition.belief_library import BeliefLibrary, DEFAULT_BELIEF_LIBRARY
from cognition.transformations import DEFAULT_TRANSFORMATION_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


def test_default_library_exposes_catalog_views():
    library = DEFAULT_BELIEF_LIBRARY

    assert library.contains("adds_denominators")
    assert library.get("adds_denominators").concept_id == "fraction_addition"
    assert library.correct_definitions("fraction_addition")
    assert library.misconception_definitions("fraction_addition")
    assert library.unknown_definition("fraction_addition") is not None
    assert library.partial_definitions("power_set")


def test_add_definition_returns_new_library():
    library = DEFAULT_BELIEF_LIBRARY
    definition = BeliefDefinition(
        belief_id="ratio_order_partial",
        concept_id="ratio_order",
        belief_type="partial",
        transformation_id="preserve_ratio_order",
        prerequisite_concept_ids=(),
        description="Preserves order but does not complete all ratio reasoning.",
    )

    updated = library.add_definition(definition)

    assert updated is not library
    assert not library.contains("ratio_order_partial")
    assert updated.contains("ratio_order_partial")


def test_duplicate_belief_ids_are_rejected():
    definition = DEFAULT_BELIEF_LIBRARY.get("adds_denominators")

    with pytest.raises(ValueError, match="duplicate belief_id"):
        BeliefLibrary((definition, definition))


def test_duplicate_unknown_definitions_are_rejected():
    first = DEFAULT_BELIEF_LIBRARY.get("fraction_addition_unknown")
    second = BeliefDefinition(
        belief_id="fraction_addition_unknown_again",
        concept_id="fraction_addition",
        belief_type="unknown",
        transformation_id=None,
        prerequisite_concept_ids=(),
        description="No usable alternate rule is available.",
    )

    with pytest.raises(ValueError, match="multiple unknown"):
        BeliefLibrary((first, second))


def test_definitions_reference_valid_concepts_and_transformations():
    DEFAULT_BELIEF_LIBRARY.validate()
    for definition in DEFAULT_BELIEF_LIBRARY.definitions():
        if definition.belief_type != "unknown":
            assert DEFAULT_TRANSFORMATION_REGISTRY.contains(definition.transformation_id)


def test_library_rejects_unregistered_transformations():
    definition = BeliefDefinition(
        belief_id="fraction_addition_invalid_transform",
        concept_id="fraction_addition",
        belief_type="correct",
        transformation_id="not_registered",
        prerequisite_concept_ids=(),
        description="Locally valid but not registered.",
    )

    with pytest.raises(ValueError, match="unregistered transformation"):
        BeliefLibrary((definition,))


def test_library_rejects_missing_non_unknown_transformation():
    definition = BeliefDefinition(
        belief_id="fraction_addition_missing_transform",
        concept_id="fraction_addition",
        belief_type="correct",
        transformation_id=None,
        prerequisite_concept_ids=(),
        description="Locally valid but missing a transformation.",
    )

    with pytest.raises(ValueError, match="unregistered transformation"):
        BeliefLibrary((definition,))


def test_library_rejects_invalid_concept_references():
    unknown_concept = BeliefDefinition(
        belief_id="not_a_graph_concept_correct",
        concept_id="not_a_graph_concept",
        belief_type="correct",
        transformation_id="add_with_common_denominator",
        prerequisite_concept_ids=(),
        description="Uses a concept outside the prerequisite graph.",
    )
    unknown_prerequisite = BeliefDefinition(
        belief_id="fraction_addition_unknown_prerequisite",
        concept_id="fraction_addition",
        belief_type="correct",
        transformation_id="add_with_common_denominator",
        prerequisite_concept_ids=("not_a_graph_concept",),
        description="Uses a prerequisite outside the prerequisite graph.",
    )

    with pytest.raises(ValueError, match="unknown concept_id"):
        BeliefLibrary((unknown_concept,))
    with pytest.raises(ValueError, match="unknown concept_id"):
        BeliefLibrary((unknown_prerequisite,))


def test_library_internal_collections_are_read_only_or_tuples():
    library = DEFAULT_BELIEF_LIBRARY

    assert isinstance(library.definitions(), tuple)
    assert isinstance(library._by_id, MappingProxyType)
    assert isinstance(library._by_concept, MappingProxyType)


def test_documentation_requires_new_belief_id_for_semantic_changes():
    documentation = (ROOT / "docs" / "belief_implementation.md").read_text()
    normalized = " ".join(documentation.split())

    assert "Semantic changes to an existing belief require a new `belief_id`" in normalized
    assert "Updating `version` alone must not silently alter" in normalized


def test_every_current_benchmark_misconception_has_definition_and_transformation():
    bank = json.loads((ROOT / "misconceptions" / "misconception_bank.json").read_text())

    for row in bank:
        misconception_id = row["misconception_id"]
        assert DEFAULT_BELIEF_LIBRARY.contains(misconception_id)
        definition = DEFAULT_BELIEF_LIBRARY.get(misconception_id)
        assert definition.transformation_id is not None
        assert DEFAULT_TRANSFORMATION_REGISTRY.contains(definition.transformation_id)
