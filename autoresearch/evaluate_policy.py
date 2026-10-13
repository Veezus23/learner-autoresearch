"""Evaluate the current learner policy under fixed autoresearch conditions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import time
import traceback
from typing import Callable, Mapping

from cognition.belief_library import DEFAULT_BELIEF_LIBRARY
from cognition.prerequisite_graph import DEFAULT_PREREQUISITE_GRAPH
from cognition.transformations import DEFAULT_TRANSFORMATION_REGISTRY
from expression.mock_adapter import MockExpressionAdapter
from expression.pipeline import express_response
from expression.types import ExpressionInput
from fixed.behavior_detectors import TrialObservation, observe_trial
from fixed.scoring import score_experiment
from learner.belief_state import LearnerBelief, LearnerBeliefState
from learner.feedback import LearnerFeedback
from learner.policy import BehaviorPlan, LearnerPolicy, PolicyInput
from prepare import (
    DEFAULT_SEED,
    BenchmarkCase,
    LearnerProfile,
    PreparedExperiment,
    prepare_experiment,
)


DEFAULT_BUDGET_SECONDS = 300.0
VALIDATION_SPLIT = "validation"

HINT_TENDENCY_VALUES = {
    "high": 0.80,
    "medium_high": 0.60,
    "medium": 0.45,
    "low_medium": 0.30,
    "low": 0.10,
}


@dataclass(frozen=True)
class EvaluationResult:
    status: str
    metrics: dict[str, float | int]
    report: dict[str, object]
    evaluation_seconds: float
    trials_completed: int
    crash_traceback: str | None = None


def evaluate_current_policy(
    *,
    split: str = VALIDATION_SPLIT,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    seed: int = DEFAULT_SEED,
    policy_factory: Callable[[], LearnerPolicy] = LearnerPolicy,
    clock: Callable[[], float] = time.monotonic,
) -> EvaluationResult:
    """Run repeated policy trials until the wall-clock budget expires."""

    if budget_seconds <= 0:
        raise ValueError("budget_seconds must be positive")

    start = clock()
    deadline = start + budget_seconds
    experiment = prepare_experiment(split=split, trial_count=1, seed=seed)
    observations_by_case: dict[str, list[TrialObservation]] = {
        case.case_id: [] for case in experiment.cases
    }
    policy = policy_factory()
    adapter = MockExpressionAdapter()
    trials_completed = 0

    try:
        while True:
            completed_full_pass = _run_one_pass(
                experiment,
                observations_by_case,
                policy,
                adapter,
                trials_completed,
            )
            trials_completed += completed_full_pass
            if clock() >= deadline:
                break
    except Exception:
        elapsed = max(0.0, clock() - start)
        return _crash_result(elapsed, trials_completed, traceback.format_exc())

    elapsed = max(0.0, clock() - start)
    report = score_experiment(experiment.cases, observations_by_case)
    report["split"] = split
    report["seed"] = seed
    report["budget_seconds"] = budget_seconds
    report["case_ordering_policy"] = "prepared_order_repeated_full_passes"
    report["expression_adapter"] = "MockExpressionAdapter"
    report["trials_completed"] = trials_completed
    report["evaluation_seconds"] = round(elapsed, 6)
    metrics = metrics_from_report(report, elapsed, trials_completed)
    return EvaluationResult(
        status="ok",
        metrics=metrics,
        report=report,
        evaluation_seconds=elapsed,
        trials_completed=trials_completed,
    )


def metrics_from_report(
    report: Mapping[str, object],
    evaluation_seconds: float,
    trials_completed: int,
) -> dict[str, float | int]:
    aggregate = report["aggregate"]  # type: ignore[index]
    dimensions = aggregate["dimensions"]  # type: ignore[index]
    by_profile = aggregate["by_profile"]  # type: ignore[index]
    profile_scores = [
        float(metrics["behavioral_fidelity"])
        for metrics in by_profile.values()
    ]
    if len(profile_scores) >= 2:
        profile_separation = max(profile_scores) - min(profile_scores)
    else:
        profile_separation = 0.0
    cases = report["cases"]  # type: ignore[index]
    guardrail_violations = sum(
        len(case_report.get("forbidden_violations", []))
        for case_report in cases
    )
    return {
        "behavioral_fidelity": float(aggregate["behavioral_fidelity"]),  # type: ignore[index]
        "correctness_alignment": float(dimensions["correctness_alignment"]),
        "misconception_adherence": float(dimensions["misconception_adherence"]),
        "prerequisite_consistency": float(dimensions["prerequisite_consistency"]),
        "confidence_consistency": float(dimensions["confidence_consistency"]),
        "hint_behavior_consistency": float(dimensions["hint_behavior_consistency"]),
        "profile_separation": round(profile_separation, 6),
        "guardrail_violations": int(guardrail_violations),
        "evaluation_seconds": round(evaluation_seconds, 6),
        "trials_completed": int(trials_completed),
    }


def format_summary(result: EvaluationResult) -> str:
    metrics = result.metrics
    lines = [
        f"behavioral_fidelity: {float(metrics['behavioral_fidelity']):.6f}",
        f"correctness_alignment: {float(metrics['correctness_alignment']):.6f}",
        f"misconception_adherence: {float(metrics['misconception_adherence']):.6f}",
        f"prerequisite_consistency: {float(metrics['prerequisite_consistency']):.6f}",
        f"confidence_consistency: {float(metrics['confidence_consistency']):.6f}",
        f"hint_behavior_consistency: {float(metrics['hint_behavior_consistency']):.6f}",
        f"profile_separation: {float(metrics['profile_separation']):.6f}",
        f"guardrail_violations: {int(metrics['guardrail_violations'])}",
        f"evaluation_seconds: {float(metrics['evaluation_seconds']):.6f}",
        f"trials_completed: {int(metrics['trials_completed'])}",
    ]
    if result.status != "ok":
        lines.append(f"status: {result.status}")
    return "\n".join(lines)


def build_policy_input(
    case: BenchmarkCase,
    profile: LearnerProfile,
    *,
    current_turn: int,
) -> PolicyInput:
    """Create a PolicyInput without evaluator-only case fields."""

    mastery = _midpoint(profile.mastery_range)
    confidence = _midpoint(profile.confidence_range)
    direct_prerequisites = DEFAULT_PREREQUISITE_GRAPH.direct_prerequisites(case.concept)
    prerequisite_mastery = {
        prerequisite: mastery for prerequisite in direct_prerequisites
    }
    belief_state = build_belief_state(case.concept, mastery, confidence)
    return PolicyInput(
        question_text=case.question,
        primary_concept_id=case.concept,
        secondary_concept_ids=(),
        topic_mastery={case.concept: mastery},
        prerequisite_mastery=prerequisite_mastery,
        concept_confidence=confidence,
        persistence=_persistence_from_profile(profile, mastery, confidence),
        hint_tendency=_hint_tendency(profile),
        guess_tendency=_guess_tendency(mastery, confidence),
        belief_state=belief_state,
        attempt_number=0,
        hint_available=True,
        learner_feedback=LearnerFeedback("none"),
        recent_activated_belief_ids=(),
        current_turn=current_turn,
    )


def build_belief_state(
    concept_id: str,
    mastery: float,
    confidence: float,
) -> LearnerBeliefState:
    beliefs: list[LearnerBelief] = []
    for definition in DEFAULT_BELIEF_LIBRARY.definitions_for_concept(concept_id):
        if definition.belief_type == "correct":
            strength = mastery
            belief_confidence = max(mastery, confidence)
        elif definition.belief_type == "misconception":
            strength = (1.0 - mastery) * (0.60 + 0.40 * confidence)
            belief_confidence = confidence
        elif definition.belief_type == "partial":
            strength = max(0.0, 1.0 - abs(mastery - 0.50) * 2.0)
            belief_confidence = min(0.60, max(0.30, confidence))
        else:
            strength = (1.0 - mastery) * (1.0 - confidence)
            belief_confidence = 1.0 - confidence
        beliefs.append(
            LearnerBelief(
                definition.belief_id,
                current_strength=round(max(0.0, min(1.0, strength)), 6),
                belief_confidence=round(max(0.0, min(1.0, belief_confidence)), 6),
            )
        )
    return LearnerBeliefState(tuple(beliefs), DEFAULT_BELIEF_LIBRARY)


def response_from_plan(
    case: BenchmarkCase,
    plan: BehaviorPlan,
    policy_input: PolicyInput,
    adapter: MockExpressionAdapter,
) -> dict[str, object]:
    belief = _belief_by_id(policy_input.belief_state, plan.activated_belief_id)
    definition = (
        policy_input.belief_state.library.get(plan.activated_belief_id)
        if plan.activated_belief_id is not None
        else None
    )
    transformation_metadata = None
    if definition is not None and definition.transformation_id is not None:
        transformation = DEFAULT_TRANSFORMATION_REGISTRY.get(definition.transformation_id)
        transformation_metadata = {
            "domain": transformation.domain,
            "description": transformation.description,
            "version": transformation.version,
        }
    expression_input = ExpressionInput(
        question_text=policy_input.question_text,
        behavior_plan=plan,
        activated_belief_definition=definition,
        activated_learner_belief=belief,
        transformation_metadata=transformation_metadata,
        learner_feedback=policy_input.learner_feedback,
    )
    student_response = express_response(expression_input, adapter)
    return {
        "case_id": case.case_id,
        "answer": student_response.response_text,
        "requested_hint": plan.action == "request_hint",
        "expressed_confidence": plan.expressed_confidence,
        "debug_action": plan.action,
        "debug_generation_status": student_response.generation_status,
        "debug_activated_belief_id": plan.activated_belief_id,
    }


def _run_one_pass(
    experiment: PreparedExperiment,
    observations_by_case: dict[str, list[TrialObservation]],
    policy: LearnerPolicy,
    adapter: MockExpressionAdapter,
    starting_turn: int,
) -> int:
    trials = 0
    profiles = experiment.profiles
    for case in experiment.cases:
        profile = profiles[case.profile_id]
        current_turn = starting_turn + trials
        policy_input = build_policy_input(case, profile, current_turn=current_turn)
        plan = policy.plan_response(policy_input)
        response = response_from_plan(case, plan, policy_input, adapter)
        trial_index = len(observations_by_case[case.case_id])
        observations_by_case[case.case_id].append(
            observe_trial(case, trial_index, response)
        )
        trials += 1
    return trials


def _crash_result(
    evaluation_seconds: float,
    trials_completed: int,
    trace: str,
) -> EvaluationResult:
    metrics: dict[str, float | int] = {
        "behavioral_fidelity": 0.0,
        "correctness_alignment": 0.0,
        "misconception_adherence": 0.0,
        "prerequisite_consistency": 0.0,
        "confidence_consistency": 0.0,
        "hint_behavior_consistency": 0.0,
        "profile_separation": 0.0,
        "guardrail_violations": 1,
        "evaluation_seconds": round(evaluation_seconds, 6),
        "trials_completed": trials_completed,
    }
    return EvaluationResult(
        status="crash",
        metrics=metrics,
        report={"status": "crash"},
        evaluation_seconds=evaluation_seconds,
        trials_completed=trials_completed,
        crash_traceback=trace,
    )


def _belief_by_id(
    belief_state: LearnerBeliefState,
    belief_id: str | None,
) -> LearnerBelief | None:
    if belief_id is None:
        return None
    for belief in belief_state.beliefs:
        if belief.belief_id == belief_id:
            return belief
    return None


def _midpoint(interval: tuple[float, float]) -> float:
    return round((float(interval[0]) + float(interval[1])) / 2.0, 6)


def _hint_tendency(profile: LearnerProfile) -> float:
    return HINT_TENDENCY_VALUES.get(profile.hint_tendency, 0.45)


def _guess_tendency(mastery: float, confidence: float) -> float:
    return round(max(0.10, min(0.90, 0.35 + (0.50 * confidence) - (0.30 * mastery))), 6)


def _persistence_from_profile(
    profile: LearnerProfile,
    mastery: float,
    confidence: float,
) -> float:
    base = 0.35 + (0.35 * mastery) + (0.20 * confidence)
    if profile.hint_tendency in {"high", "medium_high"}:
        base -= 0.05
    return round(max(0.10, min(0.95, base)), 6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["development", "validation"], default=VALIDATION_SPLIT)
    parser.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)

    result = evaluate_current_policy(
        split=args.split,
        budget_seconds=args.budget_seconds,
        seed=args.seed,
    )
    print(format_summary(result))
    if result.crash_traceback:
        print("crash_traceback:")
        print(result.crash_traceback.rstrip())
    if args.output:
        import json

        args.output.write_text(
            json.dumps(result.report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
