from dataclasses import FrozenInstanceError

import pytest

from cognition.belief_definition import BeliefDefinition
from cognition.belief_library import BeliefLibrary, DEFAULT_BELIEF_LIBRARY
from learner.belief_state import (
    BELIEF_STATUS_SEMANTICS,
    LearnerBelief,
    LearnerBeliefState,
    activation_score,
    normalized_recency,
    prerequisite_support,
)


def belief(belief_id, strength=0.5, confidence=0.5, **overrides):
    values = {
        "belief_id": belief_id,
        "current_strength": strength,
        "belief_confidence": confidence,
    }
    values.update(overrides)
    return LearnerBelief(**values)


def test_multiple_competing_beliefs_coexist_for_one_concept():
    state = LearnerBeliefState(
        (
            belief("power_set_correct"),
            belief("power_set_means_original_set"),
            belief("forgets_empty_set"),
            belief("power_set_unknown"),
        )
    )

    assert len(state.beliefs_for_concept("power_set")) == 4
    assert state.correct_beliefs("power_set")
    assert state.misconception_beliefs("power_set")
    assert state.partial_beliefs("power_set")
    assert state.unknown_belief("power_set") is not None


def test_more_than_four_learner_beliefs_per_concept_are_rejected():
    definitions = tuple(
        BeliefDefinition(
            belief_id=f"fraction_addition_extra_{index}",
            concept_id="fraction_addition",
            belief_type="partial",
            transformation_id="add_with_common_denominator",
            prerequisite_concept_ids=(),
            description=f"Extra partial rule {index}.",
        )
        for index in range(5)
    )
    library = BeliefLibrary(definitions)

    with pytest.raises(ValueError, match="at most 4"):
        LearnerBeliefState(
            tuple(belief(definition.belief_id) for definition in definitions),
            library,
        )


def test_unknown_belief_ids_are_rejected():
    with pytest.raises(ValueError, match="unknown belief_id"):
        LearnerBeliefState((belief("not_in_library"),))


def test_operations_are_immutable():
    state = LearnerBeliefState((belief("fraction_addition_correct"),))

    added = state.add_belief(belief("adds_denominators"))
    replaced = added.replace_belief(
        belief("adds_denominators", strength=0.9, confidence=0.7)
    )
    activated = replaced.record_activation("adds_denominators", 3)
    removed = activated.remove_belief("adds_denominators")

    assert len(state.beliefs) == 1
    assert len(added.beliefs) == 2
    assert replaced.misconception_beliefs("fraction_addition")[0].current_strength == 0.9
    assert activated.misconception_beliefs("fraction_addition")[0].activation_count == 1
    assert len(removed.beliefs) == 1
    with pytest.raises(FrozenInstanceError):
        state.beliefs = ()


def test_invalid_strengths_and_confidence_values_are_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        belief("adds_denominators", strength=1.1)

    with pytest.raises(ValueError, match="between 0 and 1"):
        belief("adds_denominators", confidence=-0.1)


def test_prerequisite_support_uses_only_declared_prerequisites():
    state_belief = belief("adds_denominators")

    support = prerequisite_support(
        state_belief,
        DEFAULT_BELIEF_LIBRARY,
        {
            "equivalent_fractions": 0.2,
            "common_denominator": 0.6,
            "reciprocal": 1.0,
        },
    )

    assert support == pytest.approx(0.4)


def test_unknown_support_is_one():
    state_belief = belief("fraction_addition_unknown")

    support = prerequisite_support(
        state_belief,
        DEFAULT_BELIEF_LIBRARY,
        {},
    )

    assert support == 1.0


def test_activation_formula_is_correct():
    state_belief = belief("adds_denominators", strength=0.5, confidence=0.8)

    score = activation_score(
        state_belief,
        prerequisite_support_value=0.4,
        recency=0.5,
    )

    assert score == pytest.approx(0.40 * 0.5 + 0.25 * 0.8 + 0.25 * 0.4 + 0.10 * 0.5)


def test_normalized_recency_is_bounded():
    assert normalized_recency(None, 10) == 0.0
    assert normalized_recency(10, 10) == 1.0
    assert normalized_recency(5, 10, horizon=10) == 0.5
    assert normalized_recency(0, 20, horizon=10) == 0.0


def test_normalized_recency_documents_default_ten_turn_decay():
    assert normalized_recency(None, 20) == 0.0
    assert normalized_recency(20, 20) == 1.0
    assert normalized_recency(19, 20) == pytest.approx(0.9)
    assert normalized_recency(15, 20) == pytest.approx(0.5)
    assert normalized_recency(10, 20) == 0.0
    assert normalized_recency(9, 20) == 0.0


def test_status_semantics_are_fixed_and_read_only():
    assert BELIEF_STATUS_SEMANTICS["active"] == "eligible for activation"
    assert BELIEF_STATUS_SEMANTICS["inactive"] == "retained but excluded from activation"
    assert BELIEF_STATUS_SEMANTICS["retired"] == "no longer usable"

    with pytest.raises(TypeError):
        BELIEF_STATUS_SEMANTICS["active"] = "changed"


def test_ranking_excludes_inactive_and_retired_beliefs():
    state = LearnerBeliefState(
        (
            belief("fraction_addition_correct", strength=0.1, confidence=0.1),
            belief("adds_denominators", strength=1.0, confidence=1.0, status="inactive"),
            belief(
                "fraction_addition_unknown",
                strength=1.0,
                confidence=1.0,
                status="retired",
            ),
        )
    )

    ranked = state.ranked_beliefs_for_concept(
        "fraction_addition",
        {"equivalent_fractions": 1.0, "common_denominator": 1.0},
        current_turn=1,
    )

    assert [item.belief_id for item in ranked] == ["fraction_addition_correct"]


def test_strongest_belief_is_strength_view_not_activation_ranking():
    state = LearnerBeliefState(
        (
            belief("fraction_addition_correct", strength=0.4, confidence=1.0),
            belief("adds_denominators", strength=0.9, confidence=0.1, status="inactive"),
        )
    )

    assert state.strongest_belief("fraction_addition").belief_id == "adds_denominators"
    assert [
        item.belief_id
        for item in state.ranked_beliefs_for_concept(
            "fraction_addition",
            {"equivalent_fractions": 1.0, "common_denominator": 1.0},
            current_turn=1,
        )
    ] == ["fraction_addition_correct"]


def test_learner_belief_state_internal_collections_are_tuples():
    state = LearnerBeliefState([belief("fraction_addition_correct")])

    assert isinstance(state.beliefs, tuple)


def test_tie_breaking_is_deterministic():
    definitions = (
        BeliefDefinition(
            "a_tie_belief",
            "ratio_order",
            "partial",
            "preserve_ratio_order",
            (),
            "A tied belief.",
        ),
        BeliefDefinition(
            "z_tie_belief",
            "ratio_order",
            "partial",
            "preserve_ratio_order",
            (),
            "A second tied belief.",
        ),
    )
    library = BeliefLibrary(definitions)
    state = LearnerBeliefState(
        (
            belief("z_tie_belief", strength=0.5, confidence=0.5),
            belief("a_tie_belief", strength=0.5, confidence=0.5),
        ),
        library,
    )

    ranked = state.ranked_beliefs_for_concept("ratio_order", {}, current_turn=1)

    assert [item.belief_id for item in ranked] == ["a_tie_belief", "z_tie_belief"]
