"""Experiment preparation for the learner-agent autoresearch benchmark."""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
from pathlib import Path
from typing import Any


VALID_SPLITS = {"development", "validation"}
DEFAULT_SEED = 1729
DEFAULT_TRIAL_COUNT = 20


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


@dataclass(frozen=True)
class LearnerProfile:
    profile_id: str
    mastery_level: str
    mastery_range: tuple[float, float]
    confidence_level: str
    confidence_range: tuple[float, float]
    hint_tendency: str
    description: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "LearnerProfile":
        return cls(
            profile_id=str(data["profile_id"]),
            mastery_level=str(data["mastery_level"]),
            mastery_range=(float(data["mastery_range"][0]), float(data["mastery_range"][1])),
            confidence_level=str(data["confidence_level"]),
            confidence_range=(float(data["confidence_range"][0]), float(data["confidence_range"][1])),
            hint_tendency=str(data["hint_tendency"]),
            description=str(data["description"]),
        )


@dataclass(frozen=True)
class PolicyCase:
    """Label-free case view passed to response generators or learner policies."""

    case_id: str
    domain: str
    concept: str
    question: str
    profile_id: str


@dataclass(frozen=True)
class ExperimentConfig:
    split: str
    trial_count: int
    seed: int
    root: Path


@dataclass(frozen=True)
class PreparedExperiment:
    config: ExperimentConfig
    cases: tuple[BenchmarkCase, ...]
    profiles: dict[str, LearnerProfile]
    misconceptions: dict[str, dict[str, Any]]
    policy_cases: tuple[PolicyCase, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def make_config(
    split: str = "development",
    trial_count: int = DEFAULT_TRIAL_COUNT,
    seed: int = DEFAULT_SEED,
    root: Path | None = None,
) -> ExperimentConfig:
    if split not in VALID_SPLITS:
        raise ValueError(f"unsupported split {split!r}; expected one of {sorted(VALID_SPLITS)}")
    if trial_count <= 0:
        raise ValueError("trial_count must be positive")
    return ExperimentConfig(split=split, trial_count=trial_count, seed=seed, root=root or repo_root())


def prepare_experiment(
    split: str = "development",
    trial_count: int = DEFAULT_TRIAL_COUNT,
    seed: int = DEFAULT_SEED,
    root: Path | None = None,
) -> PreparedExperiment:
    config = make_config(split=split, trial_count=trial_count, seed=seed, root=root)
    cases = tuple(load_cases(config.split, root=config.root))
    profiles = load_profiles(root=config.root)
    misconceptions = load_misconceptions(root=config.root)
    policy_cases = tuple(policy_case_from_case(case) for case in cases)
    return PreparedExperiment(
        config=config,
        cases=cases,
        profiles=profiles,
        misconceptions=misconceptions,
        policy_cases=policy_cases,
    )


def make_rng(config: ExperimentConfig, case_id: str, trial_index: int) -> random.Random:
    seed_material = f"{config.seed}:{config.split}:{case_id}:{trial_index}"
    return random.Random(seed_material)


def load_cases(split: str, root: Path | None = None) -> list[BenchmarkCase]:
    config = make_config(split=split, root=root or repo_root())
    path = config.root / "data" / split / "cases.jsonl"
    cases = [BenchmarkCase.from_mapping(row) for row in load_jsonl(path)]
    reject_duplicate_case_ids(cases)
    return cases


def load_profiles(root: Path | None = None) -> dict[str, LearnerProfile]:
    base = root or repo_root()
    rows = load_json(base / "profiles" / "learner_profiles.json")
    return {str(row["profile_id"]): LearnerProfile.from_mapping(row) for row in rows}


def load_misconceptions(root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = root or repo_root()
    rows = load_json(base / "misconceptions" / "misconception_bank.json")
    return {str(row["misconception_id"]): dict(row) for row in rows}


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


def policy_case_from_case(case: BenchmarkCase) -> PolicyCase:
    return PolicyCase(
        case_id=case.case_id,
        domain=case.domain,
        concept=case.concept,
        question=case.question,
        profile_id=case.profile_id,
    )


def cases_by_id(cases: tuple[BenchmarkCase, ...] | list[BenchmarkCase]) -> dict[str, BenchmarkCase]:
    indexed = {case.case_id: case for case in cases}
    if len(indexed) != len(cases):
        raise ValueError("duplicate case_id found")
    return indexed


def reject_duplicate_case_ids(cases: list[BenchmarkCase]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for case in cases:
        if case.case_id in seen:
            duplicates.append(case.case_id)
        seen.add(case.case_id)
    if duplicates:
        raise ValueError(f"duplicate case_id(s): {', '.join(sorted(set(duplicates)))}")
