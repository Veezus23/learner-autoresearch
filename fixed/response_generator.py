"""Fixed baseline response generator for evaluator verification."""

from __future__ import annotations

import random
from typing import Any

from prepare import LearnerProfile, PolicyCase


def generate_baseline_response(
    policy_case: PolicyCase,
    profile: LearnerProfile,
    trial_index: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Generate a deterministic baseline response from label-free policy inputs."""

    confidence = _confidence(profile)
    requested_hint = rng.random() < _hint_probability(profile)
    answer_correctly = rng.random() < _correctness_probability(profile)
    answer = _correct_answer(policy_case) if answer_correctly else _misconception_answer(policy_case)
    return {
        "case_id": policy_case.case_id,
        "answer": answer,
        "requested_hint": requested_hint,
        "expressed_confidence": confidence,
        "debug_profile_id": profile.profile_id,
        "debug_trial_index": trial_index,
    }


def _correctness_probability(profile: LearnerProfile) -> float:
    low, high = profile.mastery_range
    return (low + high) / 2.0


def _hint_probability(profile: LearnerProfile) -> float:
    if profile.hint_tendency == "high":
        return 0.80
    if profile.hint_tendency == "medium_high":
        return 0.60
    if profile.hint_tendency == "medium":
        return 0.45
    if profile.hint_tendency == "low_medium":
        return 0.30
    return 0.10


def _confidence(profile: LearnerProfile) -> float:
    low, high = profile.confidence_range
    return round((low + high) / 2.0, 3)


def _correct_answer(policy_case: PolicyCase) -> str:
    if policy_case.domain == "sets":
        return _sets_correct(policy_case)
    if policy_case.domain == "algebra":
        return _algebra_correct(policy_case)
    if policy_case.domain == "fractions":
        return _fractions_correct(policy_case)
    return "I am not sure."


def _misconception_answer(policy_case: PolicyCase) -> str:
    if policy_case.domain == "sets":
        return _sets_misconception(policy_case)
    if policy_case.domain == "algebra":
        return _algebra_misconception(policy_case)
    if policy_case.domain == "fractions":
        return _fractions_misconception(policy_case)
    return "I am not sure."


def _sets_correct(policy_case: PolicyCase) -> str:
    if policy_case.concept == "power_set":
        return "{empty set, {1}, {2}, {1,2}}"
    if policy_case.concept == "subset":
        return "Yes. Every element of {1} is in {1,2}."
    if policy_case.concept == "cardinality_power_set":
        return "8"
    if policy_case.concept == "set_difference":
        return "{1,3}"
    return "I am not sure."


def _sets_misconception(policy_case: PolicyCase) -> str:
    if policy_case.concept == "power_set":
        return "{1,2}"
    if policy_case.concept == "subset":
        return "No, 1 is an element, not a subset."
    if policy_case.concept == "cardinality_power_set":
        if policy_case.profile_id in {"weak_low_conf"}:
            return "7"
        return "3"
    if policy_case.concept == "set_difference":
        return "1,3"
    return "I am not sure."


def _algebra_correct(policy_case: PolicyCase) -> str:
    if policy_case.concept == "negative_distribution":
        return "-x + 4"
    if policy_case.concept == "linear_equation":
        return "x = 7"
    if policy_case.concept == "like_terms":
        return "7x + 2"
    if policy_case.concept == "two_step_equation":
        return "x = 6"
    return "I am not sure."


def _algebra_misconception(policy_case: PolicyCase) -> str:
    if policy_case.concept == "negative_distribution":
        return "-x - 4"
    if policy_case.concept == "linear_equation":
        return "x = 17"
    if policy_case.concept == "like_terms":
        return "9x"
    if policy_case.concept == "two_step_equation":
        return "x = 3"
    return "I am not sure."


def _fractions_correct(policy_case: PolicyCase) -> str:
    if policy_case.concept == "fraction_addition":
        return "5/6"
    if policy_case.concept == "fraction_division":
        return "5/6"
    if policy_case.concept == "ratio_order":
        return "3:5"
    if policy_case.concept == "fraction_comparison":
        return "3/4"
    return "I am not sure."


def _fractions_misconception(policy_case: PolicyCase) -> str:
    if policy_case.concept == "fraction_addition":
        return "2/5"
    if policy_case.concept == "fraction_division":
        return "8/15"
    if policy_case.concept == "ratio_order":
        return "5:3"
    if policy_case.concept == "fraction_comparison":
        return "2/5"
    return "I am not sure."
