from dataclasses import fields

import pytest

from autoresearch.evaluate_policy import (
    evaluate_current_policy,
    format_summary,
    metrics_from_report,
)
from autoresearch.research_log import (
    RESULTS_HEADER,
    append_result,
    format_result_row,
    initialize_results_tsv,
    parse_summary_metrics,
)
from learner.policy import LearnerPolicy, PolicyInput
from prepare import load_cases


class OnePassClock:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls == 1:
            return 0.0
        return 1.0


def one_pass_result(**kwargs):
    return evaluate_current_policy(
        split="validation",
        budget_seconds=0.5,
        clock=OnePassClock(),
        **kwargs,
    )


def test_deterministic_evaluation():
    first = one_pass_result()
    second = one_pass_result()

    assert first.status == "ok"
    assert first.metrics == second.metrics
    assert first.report["aggregate"] == second.report["aggregate"]
    assert first.trials_completed == len(load_cases("validation"))


def test_metric_parsing_round_trips_summary():
    result = one_pass_result()
    summary = format_summary(result)

    parsed = parse_summary_metrics(summary)

    assert parsed["behavioral_fidelity"] == result.metrics["behavioral_fidelity"]
    assert parsed["trials_completed"] == result.metrics["trials_completed"]


def test_metrics_from_report_includes_required_summary_keys():
    result = one_pass_result()
    metrics = metrics_from_report(
        result.report,
        result.evaluation_seconds,
        result.trials_completed,
    )

    assert set(metrics) == {
        "behavioral_fidelity",
        "correctness_alignment",
        "misconception_adherence",
        "prerequisite_consistency",
        "confidence_consistency",
        "hint_behavior_consistency",
        "profile_separation",
        "guardrail_violations",
        "evaluation_seconds",
        "trials_completed",
    }


def test_validation_labels_never_enter_policy_input():
    captured = []

    class CapturingPolicy(LearnerPolicy):
        def plan_response(self, policy_input):
            captured.append(policy_input)
            return super().plan_response(policy_input)

    result = one_pass_result(policy_factory=CapturingPolicy)

    assert result.status == "ok"
    assert captured
    input_fields = {field.name for field in fields(PolicyInput)}
    forbidden = {
        "case_id",
        "correct_answer",
        "expected_behavior",
        "expected_correctness",
        "expected_hint_interval",
        "evaluator_label",
        "forbidden_behavior",
        "scoring_weight",
        "validation_aggregate",
    }
    assert input_fields.isdisjoint(forbidden)
    for policy_input in captured:
        for name in forbidden:
            assert not hasattr(policy_input, name)


def test_timeout_completes_current_full_case_pass():
    result = one_pass_result()

    assert result.trials_completed == len(load_cases("validation"))
    assert all(case_report["trial_count"] == 1 for case_report in result.report["cases"])


def test_crash_reporting_returns_crash_status_and_summary():
    class CrashPolicy:
        def plan_response(self, policy_input):
            raise RuntimeError("policy exploded")

    result = one_pass_result(policy_factory=CrashPolicy)
    summary = format_summary(result)

    assert result.status == "crash"
    assert "policy exploded" in result.crash_traceback
    assert "status: crash" in summary
    assert parse_summary_metrics(summary)["guardrail_violations"] == 1


def test_results_tsv_formatting(tmp_path):
    path = tmp_path / "results.tsv"

    initialize_results_tsv(path)
    append_result(
        path,
        commit="abcdef1",
        behavioral_fidelity=0.123456,
        status="keep",
        description="baseline",
        paper_or_source="",
        metrics={"trials_completed": 9},
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "\t".join(RESULTS_HEADER)
    assert len(lines[1].split("\t")) == len(RESULTS_HEADER)
    assert lines[1].split("\t")[:4] == ["abcdef1", "0.123456", "keep", "baseline"]


def test_results_tsv_rejects_invalid_rows():
    with pytest.raises(ValueError, match="invalid status"):
        format_result_row(
            commit="abcdef1",
            behavioral_fidelity=0.0,
            status="maybe",
            description="bad",
            paper_or_source="",
            metrics={},
        )

    with pytest.raises(ValueError, match="TSV control"):
        format_result_row(
            commit="abcdef1",
            behavioral_fidelity=0.0,
            status="invalid",
            description="bad\trow",
            paper_or_source="",
            metrics={},
        )
