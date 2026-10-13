"""Deprecated single-response reporting.

Use `evaluate.py` with `fixed.scoring` for repeated-trial evaluation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from evaluator.load_cases import BenchmarkCase, cases_by_id
from evaluator.response_schema import validate_response
from evaluator.scoring import ScoreResult, WEIGHTS, score_response


def evaluate_responses(
    cases: list[BenchmarkCase],
    responses: Iterable[dict[str, Any]],
    split: str,
) -> dict[str, Any]:
    indexed_cases = cases_by_id(cases)
    seen: set[str] = set()
    results: list[ScoreResult] = []

    for raw_response in responses:
        response = validate_response(raw_response)
        case_id = response["case_id"]
        if case_id not in indexed_cases:
            raise ValueError(f"response references unknown case_id {case_id!r}")
        if case_id in seen:
            raise ValueError(f"duplicate response for case_id {case_id!r}")
        seen.add(case_id)
        results.append(score_response(indexed_cases[case_id], response))

    missing = sorted(set(indexed_cases) - seen)
    if missing:
        raise ValueError(f"missing response(s) for case_id(s): {', '.join(missing)}")

    case_metrics = [result.to_dict() for result in sorted(results, key=lambda item: item.case_id)]
    aggregate = aggregate_metrics(results)
    return {
        "split": split,
        "case_count": len(case_metrics),
        "weights": dict(WEIGHTS),
        "aggregate": aggregate,
        "cases": case_metrics,
    }


def aggregate_metrics(results: list[ScoreResult]) -> dict[str, Any]:
    if not results:
        return {
            "behavioral_fidelity": 0.0,
            "dimensions": {},
            "accuracy": 0.0,
            "by_profile": {},
        }

    dimension_names = sorted(results[0].dimensions)
    dimensions = {
        name: round(sum(result.dimensions[name] for result in results) / len(results), 6)
        for name in dimension_names
    }
    by_profile: dict[str, list[ScoreResult]] = defaultdict(list)
    for result in results:
        by_profile[result.profile_id].append(result)

    return {
        "behavioral_fidelity": round(
            sum(result.behavioral_fidelity for result in results) / len(results),
            6,
        ),
        "dimensions": dimensions,
        "accuracy": round(sum(1 for result in results if result.is_correct) / len(results), 6),
        "by_profile": {
            profile_id: {
                "case_count": len(profile_results),
                "behavioral_fidelity": round(
                    sum(result.behavioral_fidelity for result in profile_results) / len(profile_results),
                    6,
                ),
                "accuracy": round(
                    sum(1 for result in profile_results if result.is_correct) / len(profile_results),
                    6,
                ),
            }
            for profile_id, profile_results in sorted(by_profile.items())
        },
    }


def format_terminal_summary(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        f"Split: {report['split']}",
        f"Cases: {report['case_count']}",
        f"Behavioral fidelity: {aggregate['behavioral_fidelity']:.3f}",
        f"Raw answer accuracy: {aggregate['accuracy']:.3f}",
        "",
        "Dimensions:",
    ]
    for name, value in sorted(aggregate["dimensions"].items()):
        lines.append(f"  {name}: {value:.3f}")

    lines.append("")
    lines.append("By profile:")
    for profile_id, metrics in aggregate["by_profile"].items():
        lines.append(
            "  "
            f"{profile_id}: fidelity={metrics['behavioral_fidelity']:.3f}, "
            f"accuracy={metrics['accuracy']:.3f}, "
            f"n={metrics['case_count']}"
        )
    return "\n".join(lines)
