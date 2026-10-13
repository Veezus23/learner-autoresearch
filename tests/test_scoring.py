from pathlib import Path

from fixed.behavior_detectors import observe_trial
from fixed.scoring import score_case_trials
from prepare import load_cases


ROOT = Path(__file__).resolve().parents[1]


def case_by_id(case_id):
    return {case.case_id: case for case in load_cases("development", root=ROOT)}[case_id]


def repeated_observations(case, responses):
    return [observe_trial(case, index, response) for index, response in enumerate(responses)]


def response(case, answer, hint=False, confidence=0.9, **debug):
    payload = {
        "case_id": case.case_id,
        "answer": answer,
        "requested_hint": hint,
        "expressed_confidence": confidence,
    }
    payload.update(debug)
    return payload


def test_falsely_declaring_misconception_does_not_earn_credit():
    case = case_by_id("case_015")
    observations = repeated_observations(
        case,
        [
            response(
                case,
                "-x + 4",
                confidence=0.9,
                applied_misconception="distributes_negative_incorrectly",
                reasoning_features=["response remains consistent with profile limitations"],
            )
            for _ in range(10)
        ],
    )
    score = score_case_trials(case, observations)

    assert score.frequencies["expected_misconception"] == 0.0
    assert score.dimensions["misconception_adherence"] < 0.2


def test_misconception_must_appear_in_actual_answer():
    case = case_by_id("case_015")
    observations = repeated_observations(
        case,
        [response(case, "-x - 4", confidence=0.9) for _ in range(10)],
    )
    score = score_case_trials(case, observations)

    assert observations[0].detected_misconceptions == ("distributes_negative_incorrectly",)
    assert score.frequencies["expected_misconception"] == 1.0
    assert score.dimensions["misconception_adherence"] == 1.0


def test_repeated_trial_frequencies_are_scored_against_expected_intervals():
    case = case_by_id("case_008")
    aligned = repeated_observations(
        case,
        [response(case, "8", hint=True, confidence=0.2) for _ in range(2)]
        + [response(case, "7", hint=True, confidence=0.2) for _ in range(16)]
        + [response(case, "7", hint=False, confidence=0.2) for _ in range(2)],
    )
    misaligned = repeated_observations(
        case,
        [response(case, "8", hint=False, confidence=0.2) for _ in range(10)]
        + [response(case, "7", hint=False, confidence=0.2) for _ in range(10)],
    )

    aligned_score = score_case_trials(case, aligned)
    misaligned_score = score_case_trials(case, misaligned)

    assert aligned_score.frequencies["correctness"] == 0.1
    assert aligned_score.dimensions["correctness_alignment"] == 1.0
    assert aligned_score.dimensions["hint_behavior_consistency"] == 1.0
    assert misaligned_score.frequencies["correctness"] == 0.5
    assert misaligned_score.dimensions["correctness_alignment"] < 1.0
    assert misaligned_score.dimensions["hint_behavior_consistency"] < 1.0


def test_weak_and_strong_profiles_score_differently_for_same_answer_behavior():
    weak_case = case_by_id("case_008")
    strong_case = case_by_id("case_003")

    weak_observations = repeated_observations(
        weak_case,
        [response(weak_case, "8", hint=False, confidence=0.9) for _ in range(10)],
    )
    strong_observations = repeated_observations(
        strong_case,
        [
            response(strong_case, "{empty set, {1}, {2}, {1,2}}", hint=False, confidence=0.9)
            for _ in range(10)
        ],
    )

    weak_score = score_case_trials(weak_case, weak_observations)
    strong_score = score_case_trials(strong_case, strong_observations)

    assert weak_score.frequencies["correctness"] == strong_score.frequencies["correctness"] == 1.0
    assert strong_score.behavioral_fidelity > weak_score.behavioral_fidelity
    assert weak_score.dimensions["correctness_alignment"] < strong_score.dimensions["correctness_alignment"]
