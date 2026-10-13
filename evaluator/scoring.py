"""Deprecated single-response scoring.

Use `fixed.scoring` for repeated-trial detector-based scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from evaluator.load_cases import BenchmarkCase
from evaluator.response_schema import validate_response


WEIGHTS = {
    "correctness_alignment": 0.20,
    "misconception_adherence": 0.25,
    "prerequisite_consistency": 0.15,
    "confidence_consistency": 0.15,
    "hint_behavior_consistency": 0.10,
    "reasoning_feature_alignment": 0.15,
}

CONFIDENCE_INTERVALS = {
    "low": (0.00, 0.35),
    "medium": (0.36, 0.69),
    "high": (0.70, 1.00),
}

FORBIDDEN_BEHAVIOR_PENALTY = 0.20
MAX_FORBIDDEN_PENALTY = 0.60


@dataclass(frozen=True)
class ScoreResult:
    case_id: str
    profile_id: str
    dimensions: dict[str, float]
    weighted_score_before_penalty: float
    forbidden_violations: tuple[str, ...]
    behavioral_fidelity: float
    is_correct: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "profile_id": self.profile_id,
            "dimensions": dict(self.dimensions),
            "weighted_score_before_penalty": self.weighted_score_before_penalty,
            "forbidden_violations": list(self.forbidden_violations),
            "behavioral_fidelity": self.behavioral_fidelity,
            "is_correct": self.is_correct,
        }


def score_response(case: BenchmarkCase, response: dict[str, Any]) -> ScoreResult:
    response = validate_response(response)
    if response["case_id"] != case.case_id:
        raise ValueError(f"response case_id {response['case_id']!r} does not match {case.case_id!r}")

    is_correct = answers_match(response["answer"], case.correct_answer)
    applied_misconception = response["applied_misconception"]
    expected = case.expected_behavior

    dimensions = {
        "correctness_alignment": interval_alignment(
            1.0 if is_correct else 0.0,
            expected["correctness_probability"],
        ),
        "misconception_adherence": misconception_adherence(case, applied_misconception),
        "prerequisite_consistency": prerequisite_consistency(case, response, is_correct),
        "confidence_consistency": confidence_consistency(
            response["expressed_confidence"],
            str(expected["confidence_band"]),
        ),
        "hint_behavior_consistency": interval_alignment(
            1.0 if response["requested_hint"] else 0.0,
            expected["hint_probability"],
        ),
        "reasoning_feature_alignment": reasoning_feature_alignment(case, response),
    }

    violations = forbidden_violations(case, response)
    penalty = min(MAX_FORBIDDEN_PENALTY, FORBIDDEN_BEHAVIOR_PENALTY * len(violations))
    dimensions["forbidden_behavior_penalty"] = round_score(penalty)

    weighted = sum(dimensions[name] * weight for name, weight in WEIGHTS.items())
    final = clamp01(weighted - penalty)

    return ScoreResult(
        case_id=case.case_id,
        profile_id=case.profile_id,
        dimensions={name: round_score(value) for name, value in dimensions.items()},
        weighted_score_before_penalty=round_score(weighted),
        forbidden_violations=tuple(violations),
        behavioral_fidelity=round_score(final),
        is_correct=is_correct,
    )


def interval_alignment(observed: float, interval: list[float] | tuple[float, float]) -> float:
    low, high = float(interval[0]), float(interval[1])
    if low > high:
        raise ValueError(f"invalid interval: {interval}")
    if low <= observed <= high:
        return 1.0
    distance = low - observed if observed < low else observed - high
    return clamp01(1.0 - distance)


def confidence_consistency(expressed_confidence: float, expected_band: str) -> float:
    try:
        interval = CONFIDENCE_INTERVALS[expected_band]
    except KeyError as exc:
        raise ValueError(f"unknown confidence band {expected_band!r}") from exc
    return interval_alignment(expressed_confidence, interval)


def misconception_adherence(case: BenchmarkCase, applied_misconception: str | None) -> float:
    expected = expected_misconceptions(case)
    if expected:
        return 1.0 if applied_misconception in expected else 0.0
    return 1.0 if applied_misconception is None else 0.0


def prerequisite_consistency(
    case: BenchmarkCase,
    response: dict[str, Any],
    is_correct: bool,
) -> float:
    if not case.missing_prerequisites:
        return 0.0 if is_unrelated_misconception(case, response["applied_misconception"]) else 1.0

    features = normalized_feature_set(response["reasoning_features"])
    prerequisite_evidence = any(
        normalize_text(prereq) in feature
        for prereq in case.missing_prerequisites
        for feature in features
    )
    limitation_evidence = any("profile limitation" in feature or "limitation" in feature for feature in features)
    expected_error = response["applied_misconception"] in expected_misconceptions(case)

    if expected_error or prerequisite_evidence or limitation_evidence:
        return 1.0
    if not is_correct:
        return 0.5
    return 0.0


def reasoning_feature_alignment(case: BenchmarkCase, response: dict[str, Any]) -> float:
    required = {
        normalize_text(item)
        for item in case.expected_behavior.get("required_reasoning_features", [])
    }
    if not required:
        return 1.0

    observed = normalized_feature_set(response["reasoning_features"])
    if not observed:
        return 0.0

    matched = sum(1 for item in required if item in observed)
    return matched / len(required)


def forbidden_violations(
    case: BenchmarkCase,
    response: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    applied = response["applied_misconception"]

    if is_unrelated_misconception(case, applied) and "unrelated misconception" in case.forbidden_behavior:
        violations.append("unrelated misconception")

    if (
        "claims certainty inconsistent with confidence profile" in case.forbidden_behavior
        and confidence_claims_conflict(response["expressed_confidence"], str(case.expected_behavior["confidence_band"]))
    ):
        violations.append("claims certainty inconsistent with confidence profile")

    forbidden_features = {
        normalize_text(item)
        for item in case.forbidden_behavior
        if item not in {
            "unrelated misconception",
            "claims certainty inconsistent with confidence profile",
        }
    }
    observed_features = normalized_feature_set(response["reasoning_features"])
    violations.extend(sorted(forbidden_features & observed_features))
    return violations


def expected_misconceptions(case: BenchmarkCase) -> set[str]:
    return set(case.active_misconceptions) | set(
        str(item) for item in case.expected_behavior.get("acceptable_error_patterns", [])
    )


def is_unrelated_misconception(case: BenchmarkCase, applied_misconception: str | None) -> bool:
    return applied_misconception is not None and applied_misconception not in expected_misconceptions(case)


def confidence_claims_conflict(expressed_confidence: float, expected_band: str) -> bool:
    if expected_band == "low":
        return expressed_confidence >= CONFIDENCE_INTERVALS["high"][0]
    if expected_band == "high":
        return expressed_confidence <= CONFIDENCE_INTERVALS["low"][1]
    return False


def answers_match(response_answer: str, correct_answer: Any) -> bool:
    if isinstance(correct_answer, list):
        correct_forms = {_normalize_answer(item) for item in correct_answer}
    else:
        correct_forms = {_normalize_answer(correct_answer)}
    return _normalize_answer(response_answer) in correct_forms


def _normalize_answer(value: Any) -> str:
    text = str(value).strip().lower()
    text = text.replace("\u2205", "emptyset")
    text = text.replace("\u00f8", "emptyset")
    text = text.replace("\u00f7", "/")
    text = re.sub(r"\s+", "", text)
    return text


def normalized_feature_set(features: list[str]) -> set[str]:
    return {normalize_text(feature) for feature in features}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def round_score(value: float) -> float:
    return round(clamp01(value), 6)
