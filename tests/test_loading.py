from pathlib import Path

import evaluate
from prepare import PolicyCase, load_cases, prepare_experiment


ROOT = Path(__file__).resolve().parents[1]


def test_load_public_splits_through_prepare():
    development = load_cases("development", root=ROOT)
    validation = load_cases("validation", root=ROOT)

    assert len(development) == 18
    assert len(validation) == 9
    assert len({case.case_id for case in development}) == 18
    assert len({case.case_id for case in validation}) == 9


def test_validation_labels_are_not_exposed_to_policy_cases():
    experiment = prepare_experiment("validation", trial_count=3, seed=123, root=ROOT)

    assert len(experiment.cases) == 9
    assert len(experiment.policy_cases) == 9
    assert all(isinstance(policy_case, PolicyCase) for policy_case in experiment.policy_cases)

    for policy_case in experiment.policy_cases:
        assert not hasattr(policy_case, "correct_answer")
        assert not hasattr(policy_case, "active_misconceptions")
        assert not hasattr(policy_case, "expected_behavior")
        assert not hasattr(policy_case, "forbidden_behavior")

    validation_labels = {case.case_id: case.expected_behavior for case in experiment.cases}
    assert set(validation_labels) == {policy_case.case_id for policy_case in experiment.policy_cases}


def test_validation_labels_are_not_passed_to_baseline_adapter(monkeypatch):
    experiment = prepare_experiment("validation", trial_count=1, seed=123, root=ROOT)
    seen_policy_cases = []

    def spy_generator(policy_case, profile, trial_index, rng):
        assert isinstance(policy_case, PolicyCase)
        assert not hasattr(policy_case, "correct_answer")
        assert not hasattr(policy_case, "active_misconceptions")
        assert not hasattr(policy_case, "expected_behavior")
        assert not hasattr(policy_case, "forbidden_behavior")
        seen_policy_cases.append(policy_case.case_id)
        return {
            "case_id": policy_case.case_id,
            "answer": "I am not sure.",
            "requested_hint": False,
            "expressed_confidence": 0.5,
        }

    monkeypatch.setattr(evaluate, "generate_baseline_response", spy_generator)
    evaluate.run_baseline_trials(experiment)

    assert seen_policy_cases == [policy_case.case_id for policy_case in experiment.policy_cases]
