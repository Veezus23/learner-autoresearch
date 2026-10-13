"""Run repeated-trial evaluation for simulated learner agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fixed.behavior_detectors import TrialObservation, observe_trial
from fixed.response_generator import generate_baseline_response
from fixed.scoring import score_experiment
from prepare import PreparedExperiment, cases_by_id, make_rng, prepare_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["development", "validation"], default="development")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--output", type=Path, help="Optional path for machine-readable JSON report")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Use the fixed label-free baseline adapter to verify the evaluator",
    )
    args = parser.parse_args()

    if not args.baseline:
        parser.error("only --baseline is supported until a learner policy adapter is added")

    experiment = prepare_experiment(split=args.split, trial_count=args.trials, seed=args.seed)
    observations_by_case = run_baseline_trials(experiment)
    report = score_experiment(experiment.cases, observations_by_case)
    report["split"] = args.split
    report["trial_count"] = args.trials
    report["seed"] = args.seed

    print(format_terminal_summary(report))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def run_baseline_trials(experiment: PreparedExperiment) -> dict[str, list[TrialObservation]]:
    cases = cases_by_id(experiment.cases)
    observations_by_case: dict[str, list[TrialObservation]] = {
        case.case_id: [] for case in experiment.cases
    }
    for policy_case in experiment.policy_cases:
        case = cases[policy_case.case_id]
        profile = experiment.profiles[policy_case.profile_id]
        for trial_index in range(experiment.config.trial_count):
            rng = make_rng(experiment.config, policy_case.case_id, trial_index)
            response = generate_baseline_response(policy_case, profile, trial_index, rng)
            observations_by_case[case.case_id].append(observe_trial(case, trial_index, response))
    return observations_by_case


def format_terminal_summary(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        f"Split: {report['split']}",
        f"Cases: {report['case_count']}",
        f"Trials per case: {report['trial_count']}",
        f"Seed: {report['seed']}",
        f"Behavioral fidelity: {aggregate['behavioral_fidelity']:.3f}",
        "",
        "Frequencies:",
    ]
    for name, value in sorted(aggregate["frequencies"].items()):
        lines.append(f"  {name}: {value:.3f}")
    lines.append("")
    lines.append("Dimensions:")
    for name, value in sorted(aggregate["dimensions"].items()):
        lines.append(f"  {name}: {value:.3f}")
    lines.append("")
    lines.append("By profile:")
    for profile_id, metrics in aggregate["by_profile"].items():
        lines.append(
            "  "
            f"{profile_id}: fidelity={metrics['behavioral_fidelity']:.3f}, "
            f"correctness={metrics['correctness_frequency']:.3f}, "
            f"n={metrics['case_count']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
