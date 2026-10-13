import pytest

from autoresearch.protected_files import (
    ProtectedFileError,
    ensure_only_policy_changed,
    report_from_status,
)


def test_allows_only_policy_changes_and_untracked_run_artifacts():
    report = report_from_status(
        " M learner/policy.py\n"
        "?? results.tsv\n"
        "?? run.log\n"
        "?? runs/experiment_001.log\n"
    )

    assert report.ok
    assert report.violations == ()


def test_rejects_protected_tracked_files():
    report = report_from_status(
        " M learner/policy.py\n"
        " M evaluator/scoring.py\n"
        " M fixed/scoring.py\n"
    )

    assert not report.ok
    assert report.violations == ("evaluator/scoring.py", "fixed/scoring.py")


def test_rejects_tracked_results_file_changes():
    report = report_from_status(" M results.tsv\n")

    assert not report.ok
    assert report.violations == ("results.tsv",)


def test_rejects_untracked_non_artifacts():
    report = report_from_status("?? notes.txt\n")

    assert not report.ok
    assert report.violations == ("notes.txt",)


def test_ensure_only_policy_changed_raises_for_violations(monkeypatch, tmp_path):
    class Completed:
        stdout = " M docs/architecture.md\n"

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr("autoresearch.protected_files.subprocess.run", fake_run)

    with pytest.raises(ProtectedFileError, match="docs/architecture.md"):
        ensure_only_policy_changed(tmp_path)
