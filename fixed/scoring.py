"""Repeated-trial behavioral-fidelity scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixed.behavior_detectors import TrialObservation, infer_reasoning_feature_alignment
from prepare import BenchmarkCase


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
class CaseScore:
    case_id: str
    profile_id: str
    trial_count: int
    frequencies: dict[str, float]
    dimensions: dict[str, float]
    weighted_score_before_penalty: float
    forbidden_violations: tuple[str, ...]
    behavioral_fidelity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "profile_id": self.profile_id,
            "trial_count": self.trial_count,
            "frequencies": dict(self.frequencies),
            "dimensions": dict(self.dimensions),
            "weighted_score_before_penalty": self.weighted_score_before_penalty,
            "forbidden_violations": list(self.forbidden_violations),
            "behavioral_fidelity": self.behavioral_fidelity,
        }


def score_case_trials(case: BenchmarkCase, observations: list[TrialObservation]) -> CaseScore:
    if not observations:
        raise ValueError("at least one trial observation is required")
    if any(observation.case_id != case.case_id for observation in observations):
        raise ValueError("all trial observations must match the case_id")

    trial_count = len(observations)
    correctness_frequency = sum(obs.is_correct for obs in observations) / trial_count
    hint_frequency = sum(obs.requested_hint for obs in observations) / trial_count
    confidence_band_frequency = confidence_consistency_frequency(
        observations,
        str(case.expected_behavior["confidence_band"]),
    )
    any_misconception_frequency = (
        sum(bool(obs.detected_misconceptions) for obs in observations) / trial_count
    )
    expected_misconceptions = case_expected_misconceptions(case)
    expected_misconception_frequency = (
        sum(bool(set(obs.detected_misconceptions) & expected_misconceptions) for obs in observations)
        / trial_count
    )
    unrelated_misconception_frequency = (
        sum(bool(set(obs.detected_misconceptions) - expected_misconceptions) for obs in observations)
        / trial_count
    )

    dimensions = {
        "correctness_alignment": interval_alignment(
            correctness_frequency,
            case.expected_behavior["correctness_probability"],
        ),
        "misconception_adherence": misconception_adherence(
            case,
            expected_misconception_frequency,
            any_misconception_frequency,
        ),
        "prerequisite_consistency": prerequisite_consistency(
            case,
            expected_misconception_frequency,
            unrelated_misconception_frequency,
            correctness_frequency,
        ),
        "confidence_consistency": confidence_band_frequency,
        "hint_behavior_consistency": interval_alignment(
            hint_frequency,
            case.expected_behavior["hint_probability"],
        ),
        "reasoning_feature_alignment": infer_reasoning_feature_alignment(case, observations),
    }

    violations = forbidden_violations(
        case,
        observations,
        unrelated_misconception_frequency,
        confidence_band_frequency,
    )
    penalty = min(MAX_FORBIDDEN_PENALTY, FORBIDDEN_BEHAVIOR_PENALTY * len(violations))
    dimensions["forbidden_behavior_penalty"] = round_score(penalty)

    weighted = sum(dimensions[name] * weight for name, weight in WEIGHTS.items())
    final = clamp01(weighted - penalty)

    return CaseScore(
        case_id=case.case_id,
        profile_id=case.profile_id,
        trial_count=trial_count,
        frequencies={
            "correctness": round_score(correctness_frequency),
            "hint_request": round_score(hint_frequency),
            "confidence_in_expected_band": round_score(confidence_band_frequency),
            "expected_misconception": round_score(expected_misconception_frequency),
            "any_misconception": round_score(any_misconception_frequency),
            "unrelated_misconception": round_score(unrelated_misconception_frequency),
        },
        dimensions={name: round_score(value) for name, value in dimensions.items()},
        weighted_score_before_penalty=round_score(weighted),
        forbidden_violations=tuple(violations),
        behavioral_fidelity=round_score(final),
    )


def score_experiment(cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...], observations_by_case: dict[str, list[TrialObservation]]) -> dict[str, Any]:
    scores = [score_case_trials(case, observations_by_case[case.case_id]) for case in cases]
    case_reports = [score.to_dict() for score in sorted(scores, key=lambda item: item.case_id)]
    return {
        "case_count": len(case_reports),
        "weights": dict(WEIGHTS),
        "aggregate": aggregate_scores(scores),
        "cases": case_reports,
    }


def aggregate_scores(scores: list[CaseScore]) -> dict[str, Any]:
    if not scores:
        return {"behavioral_fidelity": 0.0, "dimensions": {}, "frequencies": {}, "by_profile": {}}

    dimensions = {
        name: round(sum(score.dimensions[name] for score in scores) / len(scores), 6)
        for name in sorted(scores[0].dimensions)
    }
    frequencies = {
        name: round(sum(score.frequencies[name] for score in scores) / len(scores), 6)
        for name in sorted(scores[0].frequencies)
    }
    by_profile: dict[str, list[CaseScore]] = {}
    for score in scores:
        by_profile.setdefault(score.profile_id, []).append(score)

    return {
        "behavioral_fidelity": round(
            sum(score.behavioral_fidelity for score in scores) / len(scores),
            6,
        ),
        "dimensions": dimensions,
        "frequencies": frequencies,
        "by_profile": {
            profile_id: {
                "case_count": len(profile_scores),
                "behavioral_fidelity": round(
                    sum(score.behavioral_fidelity for score in profile_scores) / len(profile_scores),
                    6,
                ),
                "correctness_frequency": round(
                    sum(score.frequencies["correctness"] for score in profile_scores) / len(profile_scores),
                    6,
                ),
            }
            for profile_id, profile_scores in sorted(by_profile.items())
        },
    }


def interval_alignment(observed: float, interval: list[float] | tuple[float, float]) -> float:
    low, high = float(interval[0]), float(interval[1])
    if low > high:
        raise ValueError(f"invalid interval: {interval}")
    if low <= observed <= high:
        return 1.0
    distance = low - observed if observed < low else observed - high
    return clamp01(1.0 - distance)


def confidence_consistency_frequency(observations: list[TrialObservation], expected_band: str) -> float:
    interval = CONFIDENCE_INTERVALS[expected_band]
    return sum(interval[0] <= obs.expressed_confidence <= interval[1] for obs in observations) / len(observations)


def misconception_adherence(
    case: BenchmarkCase,
    expected_misconception_frequency: float,
    any_misconception_frequency: float,
) -> float:
    if case_expected_misconceptions(case):
        expected_incorrect_interval = (
            1.0 - float(case.expected_behavior["correctness_probability"][1]),
            1.0 - float(case.expected_behavior["correctness_probability"][0]),
        )
        return interval_alignment(expected_misconception_frequency, expected_incorrect_interval)
    return interval_alignment(any_misconception_frequency, (0.0, 0.0))


def prerequisite_consistency(
    case: BenchmarkCase,
    expected_misconception_frequency: float,
    unrelated_misconception_frequency: float,
    correctness_frequency: float,
) -> float:
    if not case.missing_prerequisites:
        return 1.0 - unrelated_misconception_frequency
    if case_expected_misconceptions(case):
        return max(
            interval_alignment(
                expected_misconception_frequency,
                (
                    1.0 - float(case.expected_behavior["correctness_probability"][1]),
                    1.0 - float(case.expected_behavior["correctness_probability"][0]),
                ),
            ),
            1.0 - correctness_frequency,
        )
    return 1.0 - correctness_frequency


def forbidden_violations(
    case: BenchmarkCase,
    observations: list[TrialObservation],
    unrelated_misconception_frequency: float,
    confidence_band_frequency: float,
) -> list[str]:
    violations: list[str] = []
    if unrelated_misconception_frequency > 0 and "unrelated misconception" in case.forbidden_behavior:
        violations.append("unrelated misconception")
    if (
        confidence_band_frequency < 1.0
        and "claims certainty inconsistent with confidence profile" in case.forbidden_behavior
    ):
        hard_conflict_count = sum(
            confidence_claims_conflict(obs.expressed_confidence, str(case.expected_behavior["confidence_band"]))
            for obs in observations
        )
        if hard_conflict_count:
            violations.append("claims certainty inconsistent with confidence profile")
    return violations


def case_expected_misconceptions(case: BenchmarkCase) -> set[str]:
    return set(case.active_misconceptions) | set(
        str(item) for item in case.expected_behavior.get("acceptable_error_patterns", [])
    )


def confidence_claims_conflict(expressed_confidence: float, expected_band: str) -> bool:
    if expected_band == "low":
        return expressed_confidence >= CONFIDENCE_INTERVALS["high"][0]
    if expected_band == "high":
        return expressed_confidence <= CONFIDENCE_INTERVALS["low"][1]
    return False


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def round_score(value: float) -> float:
    return round(clamp01(value), 6)
