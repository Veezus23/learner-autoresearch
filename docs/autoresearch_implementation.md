# Autoresearch Implementation

This document describes the local autoresearch harness for learner-policy
experiments.

## Architectural Constraints

The harness preserves the boundaries in `docs/architecture.md`,
`docs/belief_model.md`, `docs/learner_model_spec.md`, and
`docs/evaluator_design.md`:

- the research objective is behavioral fidelity, not raw answer accuracy;
- the single editable experiment target is `learner/policy.py`;
- policy input contains no case ID, correct answer, evaluator label, expected
  interval, scoring weight, forbidden-behavior annotation, or validation
  aggregate;
- expression uses the deterministic V0 mock adapter;
- scoring uses the fixed behavior detectors and fixed scoring infrastructure;
- validation labels remain inside evaluator-side case objects and are used only
  after observable responses are produced.

## Files

- `program.md` gives autonomous research instructions.
- `autoresearch/evaluate_policy.py` runs the current policy under a wall-clock
  budget and prints fixed metric lines.
- `autoresearch/protected_files.py` checks git status before and after
  experiments.
- `autoresearch/research_log.py` initializes and formats `results.tsv` rows.
- `results.tsv` stores uncommitted experiment history.

## Evaluation Flow

`python -m autoresearch.evaluate_policy --split validation --budget-seconds 300`
loads the public validation split, derives policy-visible learner state from the
public learner profile, constructs a label-free `PolicyInput`, plans behavior
with `LearnerPolicy`, renders with `MockExpressionAdapter`, observes the
student response with fixed detectors, and scores with `fixed.scoring`.

The evaluator repeats full passes through the prepared case order until the
wall-clock budget expires. It always completes the current case and keeps case
ordering identical across experiments.

The fixed summary includes:

- `behavioral_fidelity`
- `correctness_alignment`
- `misconception_adherence`
- `prerequisite_consistency`
- `confidence_consistency`
- `hint_behavior_consistency`
- `profile_separation`
- `guardrail_violations`
- `evaluation_seconds`
- `trials_completed`

## Scope and Limitations

The score is valid only for the V0 structured/mock environment. The mock
expression adapter does not solve cases or generate calibrated student language;
it provides deterministic infrastructure behavior for policy-harness
experiments.

During autonomous optimization, architecture documents, evaluator code, fixed
detectors, benchmark data, profiles, schemas, cognition, expression,
learner-state, and update modules remain fixed. `results.tsv` and run logs may
be written but must not be committed.
