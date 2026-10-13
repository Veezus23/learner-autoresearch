"""Deprecated compatibility loader.

Use `prepare.py` for benchmark loading in the autoresearch architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


VALID_SPLITS = {"development", "validation"}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    domain: str
    concept: str
    question: str
    correct_answer: Any
    profile_id: str
    active_misconceptions: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    expected_behavior: dict[str, Any]
    forbidden_behavior: tuple[str, ...]
    metadata: dict[str, Any]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "BenchmarkCase":
        required = {
            "case_id",
            "domain",
            "concept",
            "question",
            "correct_answer",
            "profile_id",
            "active_misconceptions",
            "missing_prerequisites",
            "expected_behavior",
            "forbidden_behavior",
        }
        missing = sorted(required - data.keys())
        if missing:
            raise ValueError(f"case is missing required field(s): {', '.join(missing)}")

        return cls(
            case_id=str(data["case_id"]),
            domain=str(data["domain"]),
            concept=str(data["concept"]),
            question=str(data["question"]),
            correct_answer=data["correct_answer"],
            profile_id=str(data["profile_id"]),
            active_misconceptions=tuple(str(item) for item in data["active_misconceptions"]),
            missing_prerequisites=tuple(str(item) for item in data["missing_prerequisites"]),
            expected_behavior=dict(data["expected_behavior"]),
            forbidden_behavior=tuple(str(item) for item in data["forbidden_behavior"]),
            metadata=dict(data.get("metadata", {})),
        )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def load_cases(split: str, root: Path | None = None) -> list[BenchmarkCase]:
    if split not in VALID_SPLITS:
        raise ValueError(f"unsupported split {split!r}; expected one of {sorted(VALID_SPLITS)}")

    base = root or repo_root()
    path = base / "data" / split / "cases.jsonl"
    cases = [BenchmarkCase.from_mapping(row) for row in load_jsonl(path)]
    _reject_duplicate_case_ids(cases)
    return cases


def load_public_cases(root: Path | None = None) -> dict[str, list[BenchmarkCase]]:
    return {split: load_cases(split, root=root) for split in sorted(VALID_SPLITS)}


def load_profiles(root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = root or repo_root()
    rows = load_json(base / "profiles" / "learner_profiles.json")
    return {str(row["profile_id"]): dict(row) for row in rows}


def load_misconceptions(root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = root or repo_root()
    rows = load_json(base / "misconceptions" / "misconception_bank.json")
    return {str(row["misconception_id"]): dict(row) for row in rows}


def cases_by_id(cases: Iterable[BenchmarkCase]) -> dict[str, BenchmarkCase]:
    case_list = list(cases)
    indexed = {case.case_id: case for case in case_list}
    if len(indexed) != len(case_list):
        raise ValueError("duplicate case_id found")
    return indexed


def _reject_duplicate_case_ids(cases: list[BenchmarkCase]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for case in cases:
        if case.case_id in seen:
            duplicates.append(case.case_id)
        seen.add(case.case_id)
    if duplicates:
        raise ValueError(f"duplicate case_id(s): {', '.join(sorted(set(duplicates)))}")
