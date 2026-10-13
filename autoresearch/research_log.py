"""Utilities for autoresearch result summaries and TSV history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


RESULTS_HEADER = (
    "commit",
    "behavioral_fidelity",
    "status",
    "description",
    "paper_or_source",
    "metrics",
)
VALID_STATUSES = frozenset({"keep", "discard", "crash", "invalid"})

SUMMARY_KEYS = (
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
)


def initialize_results_tsv(path: Path) -> None:
    """Create a results TSV with the fixed header if it does not exist."""

    if path.exists():
        return
    path.write_text("\t".join(RESULTS_HEADER) + "\n", encoding="utf-8")


def parse_summary_metrics(text: str) -> dict[str, float | int]:
    """Parse the fixed metric lines printed by evaluate_policy."""

    metrics: dict[str, float | int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key not in SUMMARY_KEYS:
            continue
        stripped = value.strip()
        if key in {"guardrail_violations", "trials_completed"}:
            metrics[key] = int(stripped)
        else:
            metrics[key] = float(stripped)

    missing = [key for key in SUMMARY_KEYS if key not in metrics]
    if missing:
        raise ValueError("summary is missing metric line(s): " + ", ".join(missing))
    return metrics


def format_result_row(
    *,
    commit: str,
    behavioral_fidelity: float,
    status: str,
    description: str,
    paper_or_source: str,
    metrics: Mapping[str, object],
) -> str:
    """Return one tab-separated result row."""

    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    fields = {
        "commit": commit,
        "status": status,
        "description": description,
        "paper_or_source": paper_or_source,
    }
    for name, value in fields.items():
        _reject_tsv_control(name, value)

    encoded_metrics = json.dumps(dict(metrics), sort_keys=True, separators=(",", ":"))
    _reject_tsv_control("metrics", encoded_metrics)
    return "\t".join(
        (
            commit,
            f"{behavioral_fidelity:.6f}",
            status,
            description,
            paper_or_source,
            encoded_metrics,
        )
    )


def append_result(
    path: Path,
    *,
    commit: str,
    behavioral_fidelity: float,
    status: str,
    description: str,
    paper_or_source: str = "",
    metrics: Mapping[str, object] | None = None,
) -> None:
    """Append one experiment outcome to results.tsv."""

    initialize_results_tsv(path)
    row = format_result_row(
        commit=commit,
        behavioral_fidelity=behavioral_fidelity,
        status=status,
        description=description,
        paper_or_source=paper_or_source,
        metrics=metrics or {},
    )
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(row + "\n")


def _reject_tsv_control(name: str, value: str) -> None:
    if "\t" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{name} cannot contain TSV control characters")
