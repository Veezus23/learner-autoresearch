"""Git-diff guardrails for learner-policy autoresearch experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


EDITABLE_EXPERIMENT_TARGET = "learner/policy.py"


@dataclass(frozen=True)
class GitStatusEntry:
    index_status: str
    worktree_status: str
    path: str

    @property
    def is_untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"


@dataclass(frozen=True)
class ProtectedFileReport:
    entries: tuple[GitStatusEntry, ...]
    violations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


class ProtectedFileError(RuntimeError):
    """Raised when an experiment changes files outside the editable target."""


def inspect_git_diff(root: Path) -> ProtectedFileReport:
    """Inspect git status and report non-permitted experiment changes."""

    completed = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return report_from_status(completed.stdout)


def ensure_only_policy_changed(root: Path) -> ProtectedFileReport:
    """Raise if git status contains changes outside learner/policy.py."""

    report = inspect_git_diff(root)
    if not report.ok:
        raise ProtectedFileError(
            "experiment changed protected file(s): " + ", ".join(report.violations)
        )
    return report


def report_from_status(status_text: str) -> ProtectedFileReport:
    entries = tuple(_parse_status_line(line) for line in status_text.splitlines() if line)
    violations = tuple(
        entry.path
        for entry in entries
        if not _is_allowed_experiment_status(entry)
    )
    return ProtectedFileReport(entries=entries, violations=violations)


def _parse_status_line(line: str) -> GitStatusEntry:
    if len(line) < 4:
        raise ValueError(f"invalid git status line: {line!r}")
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return GitStatusEntry(
        index_status=line[0],
        worktree_status=line[1],
        path=_normalize_path(path),
    )


def _is_allowed_experiment_status(entry: GitStatusEntry) -> bool:
    if entry.path == EDITABLE_EXPERIMENT_TARGET:
        return True
    if entry.is_untracked and _is_untracked_run_artifact(entry.path):
        return True
    return False


def _is_untracked_run_artifact(path: str) -> bool:
    if path == "results.tsv":
        return True
    if path == "run.log":
        return True
    if path.startswith("runs/"):
        return True
    return False


def _normalize_path(path: str) -> str:
    return path.strip().strip('"').replace("\\", "/")
