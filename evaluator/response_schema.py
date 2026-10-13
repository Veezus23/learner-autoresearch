"""Deprecated structured-response validation.

New fixed scoring treats extra structured response fields as debug metadata
rather than behavioral evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_RESPONSE_FIELDS = {
    "case_id",
    "answer",
    "requested_hint",
    "expressed_confidence",
    "applied_misconception",
    "reasoning_features",
}


class ResponseValidationError(ValueError):
    """Raised when a learner response does not match the evaluator contract."""


def validate_response(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ResponseValidationError("response must be a JSON object")

    missing = sorted(REQUIRED_RESPONSE_FIELDS - response.keys())
    if missing:
        raise ResponseValidationError(f"response missing required field(s): {', '.join(missing)}")

    case_id = response["case_id"]
    if not isinstance(case_id, str) or not case_id.strip():
        raise ResponseValidationError("case_id must be a non-empty string")

    answer = response["answer"]
    if not isinstance(answer, str):
        raise ResponseValidationError("answer must be a string")

    requested_hint = response["requested_hint"]
    if not isinstance(requested_hint, bool):
        raise ResponseValidationError("requested_hint must be a boolean")

    expressed_confidence = response["expressed_confidence"]
    if isinstance(expressed_confidence, bool) or not isinstance(expressed_confidence, (int, float)):
        raise ResponseValidationError("expressed_confidence must be a number from 0 to 1")
    if not 0.0 <= float(expressed_confidence) <= 1.0:
        raise ResponseValidationError("expressed_confidence must be between 0 and 1")

    applied_misconception = response["applied_misconception"]
    if applied_misconception is not None and not isinstance(applied_misconception, str):
        raise ResponseValidationError("applied_misconception must be a string or null")
    if isinstance(applied_misconception, str) and not applied_misconception.strip():
        applied_misconception = None

    reasoning_features = response["reasoning_features"]
    if not isinstance(reasoning_features, list) or not all(
        isinstance(item, str) for item in reasoning_features
    ):
        raise ResponseValidationError("reasoning_features must be a list of strings")

    normalized = dict(response)
    normalized["case_id"] = case_id.strip()
    normalized["expressed_confidence"] = float(expressed_confidence)
    normalized["applied_misconception"] = applied_misconception
    normalized["reasoning_features"] = list(reasoning_features)
    return normalized


def load_response_jsonl(path: Path) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ResponseValidationError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            try:
                responses.append(validate_response(value))
            except ResponseValidationError as exc:
                raise ResponseValidationError(f"{path}:{line_number}: {exc}") from exc
    return responses
