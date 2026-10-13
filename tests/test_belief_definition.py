from dataclasses import fields

import pytest

from cognition.belief_definition import BeliefDefinition


def make_definition(**overrides):
    values = {
        "belief_id": "fraction_addition_correct",
        "concept_id": "fraction_addition",
        "belief_type": "correct",
        "transformation_id": "add_with_common_denominator",
        "prerequisite_concept_ids": ("common_denominator",),
        "description": "Adds fractions with a common denominator.",
    }
    values.update(overrides)
    return BeliefDefinition(**values)


def test_invalid_identifiers_are_rejected():
    with pytest.raises(ValueError, match="snake_case"):
        make_definition(belief_id="FractionAdditionCorrect")

    with pytest.raises(ValueError, match="snake_case"):
        make_definition(concept_id="fractions.addition")

    with pytest.raises(ValueError, match="non-empty"):
        make_definition(belief_id="")


def test_invalid_belief_types_are_rejected():
    with pytest.raises(ValueError, match="invalid belief_type"):
        make_definition(belief_type="buggy")


def test_unknown_beliefs_cannot_have_executable_transformations():
    with pytest.raises(ValueError, match="unknown beliefs"):
        make_definition(
            belief_type="unknown",
            transformation_id="add_with_common_denominator",
        )

    definition = make_definition(
        belief_id="fraction_addition_unknown",
        belief_type="unknown",
        transformation_id=None,
        prerequisite_concept_ids=(),
        description="No usable rule is available.",
    )
    assert definition.transformation_id is None


def test_belief_definition_does_not_cross_validate_transformations():
    definition = make_definition(transformation_id="not_registered")

    assert definition.transformation_id == "not_registered"


def test_non_unknown_belief_definition_allows_missing_transformation_locally():
    definition = make_definition(transformation_id=None)

    assert definition.transformation_id is None


def test_belief_objects_contain_no_forbidden_fields_or_metadata():
    field_names = {field.name for field in fields(BeliefDefinition)}
    forbidden = {
        "case_id",
        "correct_answer",
        "answer_key",
        "expected_output",
        "evaluator_label",
        "validation_label",
        "current_strength",
        "belief_confidence",
    }
    assert field_names.isdisjoint(forbidden)

    with pytest.raises(ValueError, match="cannot contain"):
        make_definition(description="Uses validation_label metadata.")
