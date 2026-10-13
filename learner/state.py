"""Fixed learner-state representation.

This module intentionally stores learner traits and history only. It must not
store benchmark labels, evaluator weights, correct answers, or optimization case
IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping


MAX_HISTORY_LENGTH = 50
STATE_VERSION = "learner_state_v0"
FORBIDDEN_STATE_FIELDS = {
    "correct_answer",
    "correct_answers",
    "expected_behavior",
    "validation_labels",
    "scoring_weights",
    "optimization_case_ids",
    "case_id",
    "case_ids",
}


@dataclass(frozen=True)
class InteractionRecord:
    concept: str
    was_correct: bool
    requested_hint: bool
    received_feedback: bool
    confidence_before: float
    confidence_after: float
    misconception_used: str | None
    attempt_number: int

    def __post_init__(self) -> None:
        _validate_non_empty_string("concept", self.concept)
        _validate_bool("was_correct", self.was_correct)
        _validate_bool("requested_hint", self.requested_hint)
        _validate_bool("received_feedback", self.received_feedback)
        _validate_probability("confidence_before", self.confidence_before)
        _validate_probability("confidence_after", self.confidence_after)
        if self.misconception_used is not None:
            _validate_non_empty_string("misconception_used", self.misconception_used)
        if not isinstance(self.attempt_number, int) or self.attempt_number < 1:
            raise ValueError("attempt_number must be a positive integer")


@dataclass(frozen=True)
class LearnerState:
    learner_id: str
    topic_mastery: Mapping[str, float]
    prerequisite_mastery: Mapping[str, float]
    confidence: Mapping[str, float]
    active_misconceptions: frozenset[str] | set[str] | tuple[str, ...] | list[str]
    misconception_strength: Mapping[str, float]
    hint_tendency: float
    guess_tendency: float
    persistence: float
    interaction_history: tuple[InteractionRecord, ...] = field(default_factory=tuple)
    version: str = STATE_VERSION

    def __post_init__(self) -> None:
        _validate_non_empty_string("learner_id", self.learner_id)
        _validate_probability_mapping("topic_mastery", self.topic_mastery)
        _validate_probability_mapping("prerequisite_mastery", self.prerequisite_mastery)
        _validate_probability_mapping("confidence", self.confidence)
        _validate_probability_mapping("misconception_strength", self.misconception_strength)
        _validate_probability("hint_tendency", self.hint_tendency)
        _validate_probability("guess_tendency", self.guess_tendency)
        _validate_probability("persistence", self.persistence)
        _validate_non_empty_string("version", self.version)

        active = frozenset(self.active_misconceptions)
        for misconception in active:
            _validate_non_empty_string("active_misconceptions item", misconception)
        missing_strength = sorted(active - set(self.misconception_strength))
        if missing_strength:
            raise ValueError(
                "misconception_strength missing active misconception(s): "
                + ", ".join(missing_strength)
            )

        history = tuple(self.interaction_history)
        if len(history) > MAX_HISTORY_LENGTH:
            raise ValueError(f"interaction_history cannot exceed {MAX_HISTORY_LENGTH} records")
        for record in history:
            if not isinstance(record, InteractionRecord):
                raise ValueError("interaction_history must contain InteractionRecord values")

        object.__setattr__(self, "topic_mastery", MappingProxyType(dict(self.topic_mastery)))
        object.__setattr__(
            self,
            "prerequisite_mastery",
            MappingProxyType(dict(self.prerequisite_mastery)),
        )
        object.__setattr__(self, "confidence", MappingProxyType(dict(self.confidence)))
        object.__setattr__(self, "active_misconceptions", active)
        object.__setattr__(
            self,
            "misconception_strength",
            MappingProxyType(dict(self.misconception_strength)),
        )
        object.__setattr__(self, "interaction_history", history)

    def with_updates(self, **changes: object) -> "LearnerState":
        forbidden = sorted(FORBIDDEN_STATE_FIELDS & set(changes))
        if forbidden:
            raise ValueError(f"forbidden learner-state field(s): {', '.join(forbidden)}")
        return replace(self, **changes)

    def with_history_record(self, record: InteractionRecord) -> "LearnerState":
        history = (self.interaction_history + (record,))[-MAX_HISTORY_LENGTH:]
        return self.with_updates(interaction_history=history)


def clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, value))


def bounded_increment(value: float, delta: float) -> float:
    return clamp_probability(value + delta)


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


def _validate_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
