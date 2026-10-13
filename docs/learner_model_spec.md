# Learner Model Specification

Phase 3 introduces a fixed learner-state layer before adding an optimizable
learner policy. The goal is to make learner behavior stateful while preserving a
hard boundary between benchmark labels, fixed evaluation, and future
autoresearch changes.

System-wide boundaries are defined in [architecture.md](architecture.md).
Belief schema, belief-library semantics, learner belief state, and belief
activation semantics are defined in [belief_model.md](belief_model.md).

Policy-visible profile boundaries are defined in
[architecture.md](architecture.md).

## 1. Research Objective

The learner model should support simulated students whose answers, confidence,
hint use, persistence, and misconception patterns remain behaviorally faithful
to a target learner profile over repeated interactions. The objective is
behavioral fidelity, not maximum answer accuracy.

## 2. State Variables

`LearnerState` is the fixed representation of a simulated learner's non-belief
state.

- `learner_id`: stable identifier for the simulated learner.
- `topic_mastery`: concept-to-probability map for current topic knowledge.
- `prerequisite_mastery`: prerequisite concept-to-probability map for
  supporting skills.
- `concept_confidence`: concept-to-probability map for general self-assessed
  certainty about a concept.
- `hint_tendency`: probability-like tendency to request help.
- `guess_tendency`: probability-like tendency to answer despite uncertainty.
- `persistence`: probability-like tendency to keep trying after difficulty.
- `interaction_history`: bounded tuple of structured interaction records.
- `learner_belief_state_ref`: reference to learner belief state records defined
  by [belief_model.md](belief_model.md).
- `version`: state schema version.

All continuous values are bounded from `0` to `1`.

Learner belief state is the single source of truth for belief strength,
misconception strength, belief confidence, belief status, and activation
history.

`active_misconceptions` and `misconception_strength` are not permanent
learner-state fields. If compatibility requires those concepts, they are derived
views over learner belief state:

- `active_misconceptions`: active learner belief records whose fixed
  belief-library type is `misconception`.
- `misconception_strength`: `current_strength` values for those misconception
  belief records.

`LearnerState` does not own permanent misconception definitions.

## 3. Mastery and Confidence

Mastery represents underlying ability to solve a concept or prerequisite.

Concept confidence is stored in `LearnerState`. It represents the learner's
general confidence for a concept.

Belief confidence is stored in learner belief state. It represents trust in one
specific belief.

Expressed confidence is produced by the policy for one interaction. For V0,
expressed confidence should be derived from concept confidence,
activated-belief confidence, and interaction context. The exact formula is not
defined yet.

Mastery and concept confidence can move independently. A strong but
low-confidence learner may have high mastery and low concept confidence. A weak
high-confidence learner may have low mastery and high concept confidence,
especially when a misconception feels compelling.

## 4. Misconceptions vs Prerequisite Gaps

Misconceptions are fixed belief-library entries representing incorrect rules or
interpretations, such as adding fraction denominators directly.

Prerequisite gaps are missing supporting skills, such as weak common-denominator
knowledge.

A prerequisite gap may make a misconception more likely to activate, but
misconception strength is stored in learner belief state rather than in
`LearnerState`.

## 5. Interaction History

Each history record contains:

- `concept`
- `was_correct`
- `requested_hint`
- `received_feedback`
- `concept_confidence_before`
- `concept_confidence_after`
- `activated_belief_id`
- `action`
- `attempt_number`

History is bounded to avoid unbounded state growth. V0 keeps the most recent 50
records.

`was_correct` may be stored only when correctness is observable to the learner
or provided through learner-facing feedback. Evaluator-only correctness
judgments must not be written into learner history.

## 6. State-Transition Rules

V0 update rules are deterministic and conservative:

- Learner-facing correctness feedback after correct answers increases topic
  mastery, concept confidence, and activated correct belief strength.
- Learner-facing correctness feedback after incorrect answers decreases concept
  confidence, leaves topic mastery unchanged, and slightly increases activated
  misconception strength.
- Hints increase immediate concept confidence, leave topic mastery unchanged,
  and create a temporary relevant correct-belief effective `current_strength`
  boost for one interaction.
- Corrective feedback reduces the `current_strength` of targeted misconception
  beliefs, increases the corresponding correct belief strength, and can
  slightly increase concept confidence.
- Repeated failure increases hint tendency and guess tendency while reducing
  persistence.

Named V0 update constants:

| Event | Fixed V0 update |
| --- | --- |
| Correct answer | `topic_mastery +0.03`; `concept_confidence +0.03`; activated correct belief `current_strength +0.04` |
| Incorrect answer | `topic_mastery` unchanged; `concept_confidence -0.04`; activated misconception `current_strength +0.01` |
| Hint | `topic_mastery` unchanged; `concept_confidence +0.03`; temporary relevant correct-belief effective `current_strength` boost `+0.20` for one interaction |
| Corrective feedback | targeted misconception `current_strength -0.08`; corresponding correct belief `current_strength +0.05`; `concept_confidence +0.01` |
| Repeated failure | `hint_tendency +0.05`; `guess_tendency +0.02`; `persistence -0.04` |

All updates clamp continuous values to `[0, 1]` and return new learner state and
learner belief state records.

These constants are conservative V0 engineering assumptions, not empirically
calibrated psychometric parameters.

The update layer may consume learner-facing feedback objects defined in
[architecture.md](architecture.md). It may not consume evaluator scores,
detector internals, hidden labels, behavioral-fidelity scores, or validation
aggregates.

## 7. What `learner/policy.py` Will Eventually Control

The future policy will decide observable learner behavior by producing a
behavior plan.

The behavior plan contains:

- `activated_belief_id`, or no belief
- `action`: `answer`, `guess`, `request_hint`, `abstain`, or `revise`
- `expressed_confidence`
- persistence decision
- optional reasoning mode

The policy must not directly choose "correct" or "incorrect."

Correctness is an observable consequence of applying the activated belief, not
a direct policy field.

The policy may read `LearnerState`, learner belief state, the prompt-facing case
view, and policy-visible profile information defined in
[architecture.md](architecture.md).

Profile schemas mirror policy-visible initialization fields only. Allowed and
forbidden profile fields are defined in [architecture.md](architecture.md).

## 8. What Policy Must Never Access

The policy must never access:

- case-specific correct answers;
- expected benchmark behavior;
- expected outputs;
- validation labels;
- scoring weights;
- hidden test data;
- case IDs used as optimization shortcuts;
- evaluator-only detector outputs for the current response;
- aggregate validation results;
- benchmark-specific optimization hints.

The policy may access correct symbolic belief rules from the fixed belief
library. Correct symbolic rules are concept-level and reusable across many
questions; they are not case-specific answer keys.

`LearnerState` and learner belief state also must not store prohibited fields.

## 9. V0 Assumptions

- State variables are probability-like scalars rather than calibrated
  psychometric estimates.
- Updates are deliberately small to avoid overfitting a single interaction.
- Incorrect answers do not prove mastery decreased.
- Hints may support confidence before durable learning occurs.
- Corrective feedback weakens misconceptions but does not guarantee removal.
- Interaction history is a summary of recent behavior, not a full transcript.
- Misconception availability and strength are derived from learner belief state.

## 10. Open Research Questions

- How should the state represent forgetting over time?
- Should concept confidence also have a global learner-level component?
- How should hints be typed by specificity or pedagogical strategy?
- What is the best history window length for behavioral fidelity?

## 11. Example State Transitions

Example A: a learner answers a fraction-addition item using the
`adds_denominators` misconception belief.

1. Before: `topic_mastery["fraction_addition"] = 0.25`,
   `concept_confidence["fraction_addition"] = 0.75`, and learner belief state
   has `current_strength = 0.80` for belief `adds_denominators`.
2. Learner-facing incorrectness feedback lowers concept confidence to `0.71`
   and records the activated belief ID in history. Mastery remains `0.25`.
3. Learner-facing corrective feedback lowers the targeted belief strength to
   `0.73` and can raise immediate concept confidence to `0.72`.

Example B: a low-confidence strong learner requests a hint before answering.

1. Before: `topic_mastery["power_set"] = 0.90`,
   `concept_confidence["power_set"] = 0.25`.
2. Learner-facing hint feedback raises concept confidence to `0.28` and hint
   creates a temporary relevant correct-belief effective `current_strength`
   boost of `+0.20` for one interaction. Mastery remains `0.90`.
3. Learner-facing correctness feedback after a correct answer raises mastery to
   `0.93` and concept confidence to `0.31`.

Example C: repeated failure on linear equations.

1. The learner misses several attempts with learner-facing feedback.
2. `update_after_repeated_failure` increases hint tendency and guess tendency,
   reduces persistence, and records the repeated-failure event.
3. The policy may later use this state to request a hint earlier or give a less
   persistent answer.

## Authoritative Scope

This document owns learner-state semantics and fixed state transitions.

[architecture.md](architecture.md) owns system boundaries and component
responsibilities.

[belief_model.md](belief_model.md) owns belief schema, belief-library semantics,
learner belief state, and belief activation semantics.
