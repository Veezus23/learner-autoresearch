"""Provider-neutral expression adapter interfaces."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class ExpressionAdapter(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a raw model response from an expression prompt."""


class ExternalExpressionAdapter:
    """Lightweight wrapper for a provider callable.

    This class intentionally performs no network calls and imports no provider
    SDK. A future integration can pass a callable that owns provider-specific
    behavior.
    """

    def __init__(self, generate_fn: Callable[[str], str]) -> None:
        if not callable(generate_fn):
            raise ValueError("generate_fn must be callable")
        self._generate_fn = generate_fn

    def generate(self, prompt: str) -> str:
        return self._generate_fn(prompt)


__all__ = ["ExpressionAdapter", "ExternalExpressionAdapter"]
