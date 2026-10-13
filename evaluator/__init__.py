"""Deprecated Phase 2 evaluator package.

Use `prepare.py` and the `fixed/` package for the autoresearch architecture.
This package is retained temporarily for compatibility and should not receive
new feature work.
"""

from evaluator.load_cases import BenchmarkCase, load_cases, load_public_cases
from evaluator.response_schema import ResponseValidationError, validate_response
from evaluator.scoring import score_response

__all__ = [
    "BenchmarkCase",
    "ResponseValidationError",
    "load_cases",
    "load_public_cases",
    "score_response",
    "validate_response",
]
