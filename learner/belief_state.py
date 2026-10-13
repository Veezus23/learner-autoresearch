"""Immutable learner-specific belief records and activation utilities."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

from cognition.belief_definition import BeliefDefinition
from cognition.belief_library import DEFAULT_BELIEF_LIBRARY, BeliefLibrary


BELIEF_STATUS_VALUES = frozenset({"active", "inactive", "retired"})
BELIEF_STATUS_SEMANTICS = MappingProxyType(
    {
        "active": "eligible for activation",
        "inactive": "retained but excluded from activation",
        "retired": "no longer usable",
    }
)
MAX_BELIEFS_PER_CONCEPT = 4


@dataclass(frozen=True)
class LearnerBelief:
    belief_id: str
    current_strength: float
    belief_confidence: float
    status: str = "active"
    evidence_count: int = 0
    last_activated_turn: int | None = None
    activation_count: int = 0

    def __post_init__(self) -> None:
        _validate_non_empty_string("belief_id", self.belief_id)
        _validate_probability("current_strength", self.current_strength)
        _validate_probability("belief_confidence", self.belief_confidence)
        if self.status not in BELIEF_STATUS_VALUES:
            raise ValueError(f"invalid belief status: {self.status}")
        _validate_nonnegative_int("evidence_count", self.evidence_count)
        _validate_nonnegative_int("activation_count", self.activation_count)
        if self.last_activated_turn is not None:
            _validate_nonnegative_int("last_activated_turn", self.last_activated_turn)

        object.__setattr__(self, "current_strength", float(self.current_strength))
        object.__setattr__(self, "belief_confidence", float(self.belief_confidence))

    def with_updates(self, **changes: object) -> "LearnerBelief":
        return replace(self, **changes)

    def record_activation(self, turn: int) -> "LearnerBelief":
        _validate_nonnegative_int("turn", turn)
        return self.with_updates(
            last_activated_turn=turn,
            activation_count=self.activation_count + 1,
        )


@dataclass(frozen=True)
class LearnerBeliefState:
    beliefs: tuple[LearnerBelief, ...] = ()
    library: BeliefLibrary = DEFAULT_BELIEF_LIBRARY

    def __post_init__(self) -> None:
        belief_tuple = tuple(self.beliefs)
        seen_ids: set[str] = set()
        by_concept: dict[str, list[LearnerBelief]] = {}
        unknown_by_concept: set[str] = set()

        for belief in belief_tuple:
            if not isinstance(belief, LearnerBelief):
                raise ValueError("beliefs must contain LearnerBelief values")
            if belief.belief_id in seen_ids:
                raise ValueError(f"duplicate learner belief_id: {belief.belief_id}")
            if not self.library.contains(belief.belief_id):
                raise ValueError(f"unknown belief_id: {belief.belief_id}")

            seen_ids.add(belief.belief_id)
            definition = self.library.get(belief.belief_id)
            concept_beliefs = by_concept.setdefault(definition.concept_id, [])
            concept_beliefs.append(belief)
            if len(concept_beliefs) > MAX_BELIEFS_PER_CONCEPT:
                raise ValueError(
                    f"at most {MAX_BELIEFS_PER_CONCEPT} beliefs are allowed "
                    f"for concept: {definition.concept_id}"
                )
            if definition.belief_type == "unknown":
                if definition.concept_id in unknown_by_concept:
                    raise ValueError(
                        f"multiple unknown learner beliefs for concept: {definition.concept_id}"
                    )
                unknown_by_concept.add(definition.concept_id)

        object.__setattr__(self, "beliefs", belief_tuple)

    def add_belief(self, belief: LearnerBelief) -> "LearnerBeliefState":
        return LearnerBeliefState(self.beliefs + (belief,), self.library)

    def replace_belief(self, belief: LearnerBelief) -> "LearnerBeliefState":
        if not self.library.contains(belief.belief_id):
            raise ValueError(f"unknown belief_id: {belief.belief_id}")
        replaced = False
        updated: list[LearnerBelief] = []
        for existing in self.beliefs:
            if existing.belief_id == belief.belief_id:
                updated.append(belief)
                replaced = True
            else:
                updated.append(existing)
        if not replaced:
            raise KeyError(belief.belief_id)
        return LearnerBeliefState(tuple(updated), self.library)

    def remove_belief(self, belief_id: str) -> "LearnerBeliefState":
        if not any(belief.belief_id == belief_id for belief in self.beliefs):
            raise KeyError(belief_id)
        return LearnerBeliefState(
            tuple(belief for belief in self.beliefs if belief.belief_id != belief_id),
            self.library,
        )

    def record_activation(self, belief_id: str, turn: int) -> "LearnerBeliefState":
        for belief in self.beliefs:
            if belief.belief_id == belief_id:
                return self.replace_belief(belief.record_activation(turn))
        raise KeyError(belief_id)

    def beliefs_for_concept(self, concept_id: str) -> tuple[LearnerBelief, ...]:
        self.library.definitions_for_concept(concept_id)
        return tuple(
            belief
            for belief in self.beliefs
            if self.library.get(belief.belief_id).concept_id == concept_id
        )

    def strongest_belief(self, concept_id: str) -> LearnerBelief | None:
        concept_beliefs = self.beliefs_for_concept(concept_id)
        if not concept_beliefs:
            return None
        return sorted(
            concept_beliefs,
            key=lambda belief: (-belief.current_strength, belief.belief_id),
        )[0]

    def correct_beliefs(self, concept_id: str | None = None) -> tuple[LearnerBelief, ...]:
        return self._beliefs_by_type("correct", concept_id)

    def misconception_beliefs(
        self, concept_id: str | None = None
    ) -> tuple[LearnerBelief, ...]:
        return self._beliefs_by_type("misconception", concept_id)

    def partial_beliefs(self, concept_id: str | None = None) -> tuple[LearnerBelief, ...]:
        return self._beliefs_by_type("partial", concept_id)

    def unknown_belief(self, concept_id: str) -> LearnerBelief | None:
        unknowns = self._beliefs_by_type("unknown", concept_id)
        return unknowns[0] if unknowns else None

    def activation_score(
        self,
        belief: LearnerBelief,
        prerequisite_mastery: Mapping[str, float],
        current_turn: int,
        *,
        recency_horizon: int = 10,
    ) -> float:
        support = prerequisite_support(belief, self.library, prerequisite_mastery)
        recency = normalized_recency(
            belief.last_activated_turn,
            current_turn,
            horizon=recency_horizon,
        )
        return activation_score(belief, support, recency)

    def ranked_beliefs_for_concept(
        self,
        concept_id: str,
        prerequisite_mastery: Mapping[str, float],
        current_turn: int,
        *,
        recency_horizon: int = 10,
    ) -> tuple[LearnerBelief, ...]:
        candidates = tuple(
            belief
            for belief in self.beliefs_for_concept(concept_id)
            if belief.status == "active"
        )
        scored = []
        for belief in candidates:
            support = prerequisite_support(belief, self.library, prerequisite_mastery)
            recency = normalized_recency(
                belief.last_activated_turn,
                current_turn,
                horizon=recency_horizon,
            )
            score = activation_score(belief, support, recency)
            scored.append((score, support, belief.current_strength, belief))

        return tuple(
            item[3]
            for item in sorted(
                scored,
                key=lambda item: (-item[0], -item[1], -item[2], item[3].belief_id),
            )
        )

    def _beliefs_by_type(
        self, belief_type: str, concept_id: str | None
    ) -> tuple[LearnerBelief, ...]:
        source = (
            self.beliefs_for_concept(concept_id)
            if concept_id is not None
            else self.beliefs
        )
        return tuple(
            belief
            for belief in source
            if self.library.get(belief.belief_id).belief_type == belief_type
        )


def prerequisite_support(
    belief: LearnerBelief,
    library: BeliefLibrary,
    prerequisite_mastery: Mapping[str, float],
) -> float:
    _validate_probability_mapping("prerequisite_mastery", prerequisite_mastery)
    definition = library.get(belief.belief_id)
    return prerequisite_support_for_definition(definition, prerequisite_mastery)


def prerequisite_support_for_definition(
    definition: BeliefDefinition,
    prerequisite_mastery: Mapping[str, float],
) -> float:
    _validate_probability_mapping("prerequisite_mastery", prerequisite_mastery)
    if definition.belief_type == "unknown":
        return 1.0
    if not definition.prerequisite_concept_ids:
        return 1.0
    return sum(
        float(prerequisite_mastery.get(concept_id, 0.0))
        for concept_id in definition.prerequisite_concept_ids
    ) / len(definition.prerequisite_concept_ids)


def normalized_recency(
    last_activated_turn: int | None,
    current_turn: int,
    *,
    horizon: int = 10,
) -> float:
    """Return recency in [0, 1] with linear decay over the horizon.

    Never activated beliefs have recency 0.0. A belief activated at the current
    turn has recency 1.0. With the default horizon, recency decays linearly over
    10 turns and is zero after 10 or more turns.
    """
    _validate_nonnegative_int("current_turn", current_turn)
    if not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if last_activated_turn is None:
        return 0.0
    _validate_nonnegative_int("last_activated_turn", last_activated_turn)
    delta = max(current_turn - last_activated_turn, 0)
    return max(0.0, min(1.0, 1.0 - (delta / horizon)))


def activation_score(
    belief: LearnerBelief,
    prerequisite_support_value: float,
    recency: float,
) -> float:
    _validate_probability("prerequisite_support", prerequisite_support_value)
    _validate_probability("recency", recency)
    return (
        0.40 * belief.current_strength
        + 0.25 * belief.belief_confidence
        + 0.25 * prerequisite_support_value
        + 0.10 * recency
    )


def _validate_probability_mapping(name: str, values: Mapping[str, float]) -> None:
    if not isinstance(values, Mapping):
        raise ValueError(f"{name} must be a mapping")
    for key, value in values.items():
        _validate_non_empty_string(f"{name} key", key)
        _validate_probability(f"{name}[{key!r}]", value)


def _validate_probability(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def _validate_nonnegative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "BELIEF_STATUS_SEMANTICS",
    "BELIEF_STATUS_VALUES",
    "MAX_BELIEFS_PER_CONCEPT",
    "LearnerBelief",
    "LearnerBeliefState",
    "activation_score",
    "normalized_recency",
    "prerequisite_support",
    "prerequisite_support_for_definition",
]
