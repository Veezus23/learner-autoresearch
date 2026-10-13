"""Deterministic answer and misconception detectors."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from prepare import BenchmarkCase


MISCONCEPTIONS = {
    "power_set_means_original_set",
    "forgets_empty_set",
    "elements_are_subsets",
    "distributes_negative_incorrectly",
    "moves_term_without_sign_change",
    "combines_unlike_terms",
    "adds_denominators",
    "inverts_wrong_fraction",
    "ratio_order_reversed",
}


def is_correct_answer(case: BenchmarkCase, answer: str) -> bool:
    if normalized_answer(answer) == normalized_answer(case.correct_answer):
        return True

    if case.domain == "sets":
        return _sets_correct(case, answer)
    if case.domain == "algebra":
        return _algebra_correct(case, answer)
    if case.domain == "fractions":
        return _fractions_correct(case, answer)
    return False


def detect_misconceptions(case: BenchmarkCase, answer: str) -> set[str]:
    detected: set[str] = set()
    normalized = normalized_answer(answer)
    text = normalize_text(answer)

    if case.domain == "sets":
        detected.update(_detect_set_misconceptions(case, normalized, text))
    elif case.domain == "algebra":
        detected.update(_detect_algebra_misconceptions(case, normalized, text))
    elif case.domain == "fractions":
        detected.update(_detect_fraction_misconceptions(case, normalized, text))

    return detected


def normalized_answer(value: Any) -> str:
    text = str(value).strip().lower()
    text = text.replace("\u2205", "emptyset")
    text = text.replace("\u00f8", "emptyset")
    text = text.replace("\u00f7", "/")
    text = text.replace("\u2212", "-")
    text = re.sub(r"\s+", "", text)
    return text


def normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("\u2205", "empty set")
    text = text.replace("\u00f8", "empty set")
    text = text.replace("\u00f7", " divided by ")
    text = text.replace("\u2212", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def _sets_correct(case: BenchmarkCase, answer: str) -> bool:
    normalized = normalized_answer(answer)
    if case.concept == "subset":
        return normalized.startswith("yes") and "everyelement" in normalized
    if case.concept == "cardinality_power_set":
        return normalized in {"8", "eight"}
    return False


def _algebra_correct(case: BenchmarkCase, answer: str) -> bool:
    normalized = normalized_answer(answer)
    if case.concept == "negative_distribution":
        return normalized in {"-x+4", "4-x"}
    if case.concept == "linear_equation":
        return normalized in {"x=7", "7"}
    if case.concept == "two_step_equation":
        return normalized in {"x=6", "6"}
    if case.concept == "like_terms":
        return normalized in {"7x+2", "2+7x"}
    return False


def _fractions_correct(case: BenchmarkCase, answer: str) -> bool:
    normalized = normalized_answer(answer)
    if case.concept in {"fraction_addition", "fraction_division"}:
        return _fraction_value(normalized) == _fraction_value(normalized_answer(case.correct_answer))
    if case.concept == "ratio_order":
        return normalized in {"3:5", "3to5"}
    if case.concept == "fraction_comparison":
        return normalized in {"3/4", "threefourths", "3quarters"}
    return False


def _detect_set_misconceptions(case: BenchmarkCase, normalized: str, text: str) -> set[str]:
    detected: set[str] = set()
    if case.concept in {"power_set", "cardinality_power_set"}:
        if normalized in {"{1,2}", "1,2", "{1,2,3}", "3"} or "original set" in text:
            detected.add("power_set_means_original_set")
        if normalized in {"{{1},{2},{1,2}}", "{1},{2},{1,2}", "7", "seven"}:
            detected.add("forgets_empty_set")
        if "element" in text and "subset" not in text:
            detected.add("elements_are_subsets")
    if case.concept == "subset":
        if "not a subset" in text or normalized.startswith("no"):
            detected.add("elements_are_subsets")
    if case.concept == "set_difference":
        if normalized in {"1,3", "1and3"} or "without braces" in text:
            detected.add("elements_are_subsets")
    return detected


def _detect_algebra_misconceptions(case: BenchmarkCase, normalized: str, text: str) -> set[str]:
    detected: set[str] = set()
    if case.concept == "negative_distribution" and normalized in {"-x-4", "-(x)-4"}:
        detected.add("distributes_negative_incorrectly")
    if case.concept == "linear_equation" and normalized in {"x=17", "17"}:
        detected.add("moves_term_without_sign_change")
    if case.concept == "two_step_equation" and normalized in {"x=3", "3", "2x=6"}:
        detected.add("moves_term_without_sign_change")
    if case.concept == "like_terms" and normalized in {"9x", "9", "7x+2x", "9x+0"}:
        detected.add("combines_unlike_terms")
    if "same sign" in text and "equals" in text:
        detected.add("moves_term_without_sign_change")
    return detected


def _detect_fraction_misconceptions(case: BenchmarkCase, normalized: str, text: str) -> set[str]:
    detected: set[str] = set()
    if case.concept in {"fraction_addition", "fraction_comparison"} and normalized in {"2/5", "5/7"}:
        detected.add("adds_denominators")
    if case.concept == "fraction_division" and normalized in {"8/15", "10/12", "5/6?wrongflip"}:
        detected.add("inverts_wrong_fraction")
    if case.concept == "ratio_order" and normalized in {"5:3", "5to3"}:
        detected.add("ratio_order_reversed")
    if "add denominators" in text or "added denominators" in text:
        detected.add("adds_denominators")
    return detected


def _fraction_value(normalized: str) -> Fraction | None:
    match = re.fullmatch(r"(-?\d+)/(-?\d+)", normalized)
    if not match:
        return None
    denominator = int(match.group(2))
    if denominator == 0:
        return None
    return Fraction(int(match.group(1)), denominator)
