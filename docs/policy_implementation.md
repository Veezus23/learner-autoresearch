# Policy Implementation

Version: 0.1

`learner/policy.py` implements the minimal deterministic V0 learner policy.

## Scope

The policy produces a `BehaviorPlan` for one interaction. It does not generate
answers, choose correctness, mutate learner state, mutate learner belief state,
or consume evaluator-only data.

The public API is:

- `PolicyInput`
- `BehaviorPlan`
- `LearnerPolicy.plan_response(policy_input: PolicyInput) -> BehaviorPlan`

## Policy-Visible Input

`PolicyInput` is immutable and contains only learner-facing fields:

- prompt-facing question text;
- canonical primary and secondary concept IDs;
- topic mastery and prerequisite mastery;
- concept confidence, persistence, hint tendency, and guess tendency;
- `LearnerBeliefState`;
- attempt number, hint availability, learner-facing feedback, recent activated
  belief IDs, and current turn.

It rejects extra fields, non-canonical concept IDs, out-of-range
probability-like values, negative turn or attempt values, non-learner feedback,
and non-`LearnerBeliefState` belief state.

`PolicyInput` has no case ID, correct answer, expected correctness, expected
hint interval, evaluator label, scoring weight, validation aggregate, or
forbidden-behavior metadata field.

## Belief Activation

The policy uses `LearnerBeliefState.ranked_beliefs_for_concept` for activation.
That keeps the fixed V0 activation formula in the belief-state layer:

`A(b) = 0.40*S + 0.25*C + 0.25*P + 0.10*R`

Only active beliefs are ranked. Prerequisite mastery and current turn are passed
through to the existing ranking API.

When learner-facing hint feedback references a correct belief for the current
concept, the policy builds the existing temporary `BeliefContext` and applies it
to a transient copied belief state for ranking only. Permanent
`LearnerBelief.current_strength` values are not changed.

## Behavior Plan

`BehaviorPlan` is immutable and contains:

- `activated_belief_id: str | None`
- `action`
- `expressed_confidence`
- `persistence_decision`
- `reasoning_mode`
- `response_constraints`
- `policy_version`

Allowed actions are `answer`, `guess`, `request_hint`, `abstain`, and `revise`.
Allowed persistence decisions are `continue`, `stop`, and `reconsider`.
Allowed reasoning modes are `apply_belief`, `partial_attempt`, `guess`, and
`no_rule`.

The plan contains no correctness field, answer key, expected outcome,
benchmark-specific output, or evaluator-only metadata. When built by
`LearnerPolicy`, a non-null `activated_belief_id` is validated against the
provided `LearnerBeliefState`.

## V0 Action Rules

No active belief and unknown beliefs use the same rule:

- request a hint when a hint is available and `hint_tendency >= 0.50`;
- otherwise guess when `guess_tendency >= 0.50`;
- otherwise abstain.

Correct and misconception beliefs produce `action = "answer"` with
`reasoning_mode = "apply_belief"`.

Partial beliefs produce `action = "answer"` with
`reasoning_mode = "partial_attempt"`.

Revision is used only when learner-facing corrective feedback exists, a prior
activated belief is available, and `persistence >= 0.50`.

## V0 Confidence Assumption

The expressed-confidence formulas are V0 engineering assumptions, not
calibrated learner parameters.

With a selected belief:

`0.55 * concept_confidence + 0.35 * selected_belief.belief_confidence + 0.10 * attempt_modifier`

where:

`attempt_modifier = max(0, 1 - 0.10 * attempt_number)`

Without a selected belief:

`0.70 * concept_confidence + 0.30 * guess_tendency`

All values are clamped to `[0, 1]`. `request_hint` and `abstain` cap expressed
confidence at `0.49`.

## Persistence Decision

The persistence decision uses only persistence, attempt number, and
learner-facing corrective feedback:

- corrective feedback with `persistence >= 0.50` produces `reconsider`;
- `persistence < 0.30` after at least two attempts produces `stop`;
- otherwise the learner continues.

Evaluator judgments are not used unless an experiment has converted them into
explicit learner-facing feedback.

## Response Constraints

Response constraints are symbolic only.

Selected correct and misconception beliefs include the selected transformation
identifier and preserve the selected belief. Misconceptions also add
`do_not_self_correct`. Partial beliefs add `produce_partial_reasoning`.
Unknown or missing beliefs add uncertainty and no-external-solving constraints.
Hint requests add `request_hint_only` and `do_not_answer`.

Constraints do not contain question IDs, benchmark answers, evaluator
expectations, or case-specific outputs.

## Expression-Layer Boundary

The policy preserves the distinction between selecting a belief, naming the
transformation associated with that belief, and generating the final response.
The expression layer later verbalizes the plan and activated belief without
repairing or replacing the selected belief using external correctness.
