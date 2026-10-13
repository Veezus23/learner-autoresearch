# Belief Update Implementation

Version: 0.1

This document describes the V0 learner-belief update layer implemented in
`learner/feedback.py` and `learner/belief_update.py`.

## Feedback Boundary

`LearnerFeedback` is the only feedback object accepted by belief updates. It is
immutable and contains only learner-facing fields:

- `feedback_type`
- `learner_message`
- `target_concept_ids`
- `referenced_belief_ids`
- `source`

The object rejects evaluator scores, detector internals, benchmark
expectations, hidden labels, validation labels, expected outputs, and extra
fields. Concept and belief identifiers must be canonical snake_case IDs.

Evaluator outputs are not learner-facing feedback. They must be converted by an
experiment into an explicit `LearnerFeedback` object before the update layer can
consume anything.

## Update API

The V0 belief update functions are:

- `update_after_correct_answer(state, activated_belief_id, feedback)`
- `update_after_incorrect_answer(state, activated_belief_id, feedback)`
- `update_after_hint(state, correct_belief_id, feedback)`
- `belief_context_after_hint(state, correct_belief_id, feedback)`
- `update_after_corrective_feedback(state, misconception_belief_id, correct_belief_id, feedback)`
- `update_after_repeated_success(state, activated_belief_id, *, unknown_belief_id=None)`
- `update_after_repeated_failure(state, activated_belief_id, *, unknown_belief_id=None, weaken_active_correct_belief=True)`

All update functions return a new `LearnerBeliefState`, preserve the existing
belief-library object, and reject belief IDs not present in the learner state.
Feedback-driven updates require the targeted belief IDs to be listed in
`referenced_belief_ids` and their concept IDs to be listed in
`target_concept_ids`.

## Fixed V0 Effects

Correct answer feedback strengthens the activated correct belief by `+0.04` and
increments its evidence count.

Incorrect answer feedback strengthens an activated misconception by `+0.01` and
increments evidence count. Partial and unknown beliefs keep the same permanent
strength under ordinary correctness feedback.

Hints do not permanently increase belief strength. `update_after_hint` returns
a new belief state with unchanged permanent strengths. The one-interaction
`+0.20` correct-belief boost is represented in the separate immutable
`BeliefContext` returned by `belief_context_after_hint`.

Corrective feedback requires explicit learner-facing `corrective_feedback`. It
weakens the targeted misconception by `-0.08`, strengthens the corresponding
correct belief by `+0.05`, and increments both evidence counts.

Repeated success strengthens the activated correct belief by `+0.03` and
weakens the concept's unknown belief by `-0.02` when present.

Repeated failure is intentionally conservative in V0: it modifies only learner
belief state, not mastery, persistence, hint tendency, or guess tendency. It
increases the concept's unknown belief by `+0.03` when present and weakens a
repeatedly failing active correct belief by `-0.01` at most.

All strength and confidence values are clamped to `[0, 1]`. Activation history
is preserved unless a future explicit activation-recording API updates it.
