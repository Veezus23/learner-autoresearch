"""Observable behavior detectors for trial responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixed.answer_detectors import detect_misconceptions, is_correct_answer
from prepare import BenchmarkCase


@dataclass(frozen=True)
class TrialResponse:
    case_id: str
    answer: str
    requested_hint: bool
    expressed_confidence: float
    debug_metadata: dict[str, Any]


@dataclass(frozen=True)
class TrialObservation:
    case_id: str
    trial_index: int
    answer: str
    requested_hint: bool
    expressed_confidence: float
    is_correct: bool
    detected_misconceptions: tuple[str, ...]
    debug_metadata: dict[str, Any]


def validate_trial_response(response: dict[str, Any]) -> TrialResponse:
    required = {"case_id", "answer", "requested_hint", "expressed_confidence"}
    missing = sorted(required - response.keys())
    if missing:
        raise ValueError(f"response missing required field(s): {', '.join(missing)}")
    if not isinstance(response["case_id"], str) or not response["case_id"].strip():
        raise ValueError("case_id must be a non-empty string")
    if not isinstance(response["answer"], str):
        raise ValueError("answer must be a string")
    if not isinstance(response["requested_hint"], bool):
        raise ValueError("requested_hint must be a boolean")
    confidence = response["expressed_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("expressed_confidence must be a number from 0 to 1")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("expressed_confidence must be between 0 and 1")

    debug_metadata = {
        key: value
        for key, value in response.items()
        if key not in {"case_id", "answer", "requested_hint", "expressed_confidence"}
    }
    return TrialResponse(
        case_id=response["case_id"].strip(),
        answer=response["answer"],
        requested_hint=response["requested_hint"],
        expressed_confidence=float(confidence),
        debug_metadata=debug_metadata,
    )


def observe_trial(case: BenchmarkCase, trial_index: int, response: dict[str, Any]) -> TrialObservation:
    trial = validate_trial_response(response)
    if trial.case_id != case.case_id:
        raise ValueError(f"response case_id {trial.case_id!r} does not match case {case.case_id!r}")
    return TrialObservation(
        case_id=trial.case_id,
        trial_index=trial_index,
        answer=trial.answer,
        requested_hint=trial.requested_hint,
        expressed_confidence=trial.expressed_confidence,
        is_correct=is_correct_answer(case, trial.answer),
        detected_misconceptions=tuple(sorted(detect_misconceptions(case, trial.answer))),
        debug_metadata=trial.debug_metadata,
    )


def infer_reasoning_feature_alignment(case: BenchmarkCase, observations: list[TrialObservation]) -> float:
    required = [str(item) for item in case.expected_behavior.get("required_reasoning_features", [])]
    if not required:
        return 1.0
    if not observations:
        return 0.0

    correctness_frequency = sum(obs.is_correct for obs in observations) / len(observations)
    expected_misconceptions = set(case.active_misconceptions) | set(
        str(item) for item in case.expected_behavior.get("acceptable_error_patterns", [])
    )
    expected_misconception_frequency = (
        sum(bool(set(obs.detected_misconceptions) & expected_misconceptions) for obs in observations)
        / len(observations)
    )
    correctness_alignment_proxy = _interval_alignment(
        correctness_frequency,
        case.expected_behavior["correctness_probability"],
    )

    scores: list[float] = []
    for feature in required:
        normalized = feature.lower()
        if "uses relevant concept correctly" in normalized:
            scores.append(correctness_frequency)
        elif "partial but recognizable" in normalized:
            scores.append(max(correctness_alignment_proxy, expected_misconception_frequency))
        elif "profile limitations" in normalized:
            scores.append(max(correctness_alignment_proxy, expected_misconception_frequency))
        else:
            scores.append(correctness_alignment_proxy)
    return sum(scores) / len(scores)


def _interval_alignment(observed: float, interval: list[float] | tuple[float, float]) -> float:
    low, high = float(interval[0]), float(interval[1])
    if low <= observed <= high:
        return 1.0
    distance = low - observed if observed < low else observed - high
    return max(0.0, min(1.0, 1.0 - distance))
