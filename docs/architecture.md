# Simulated Learner Agents for Personalized Learning

## Research Objective

The goal of this project is to build simulated learner agents that behave like
real students rather than simply answering questions correctly or incorrectly.

These learner agents are intended to support research on personalized learning
systems, tutoring strategies, curriculum sequencing, hint generation, and
student modeling.

The long-term objective is to produce learner simulations whose observable
behavior resembles real students under equivalent learning conditions.

## Core Philosophy

The system does not directly simulate answers. It simulates an internal learner
model that produces answers.

The language model is not the learner. The language model is only responsible
for expressing the learner's internal decisions in natural language.

Correctness is an observable consequence of applying an activated belief to a
question. Correctness is not a direct policy field.

## High-Level Pipeline

Objective Knowledge Library
-> Belief Library
-> Learner Belief State
-> Learner State
-> Learner Policy
-> Language Expression Layer
-> Observable Response
-> Behavioral Evaluation
-> Behavioral Fidelity

Evaluator scoring and learner updates are separate channels.

## One-Interaction Lifecycle

Prompt-facing case view
-> policy-visible learner state and belief state
-> deterministic belief activation
-> behavior plan
-> language expression
-> observable response
-> evaluator observation
-> optional learner-facing feedback
-> fixed learner/state-belief update

Validation evaluation should not automatically update learner state unless the
experiment explicitly models learner-facing feedback.

## Objective Knowledge Library

Objective knowledge represents the correct domain model.

It includes:

- concepts
- correct symbolic rules
- procedures
- prerequisite relationships

Objective knowledge is fixed and is not optimized by autoresearch.

Correct symbolic rules are concept-level and reusable across many questions.
They are not benchmark answer keys.

## Concept Identifiers

Concept identifiers are stable snake_case IDs.

Each concept has one canonical ID. Optional aliases may exist, but aliases are
stored outside policy logic.

Questions may map to one primary concept and zero or more secondary concepts.

Belief records and prerequisite records must reference canonical concept IDs.

## Belief Library

The belief library is a fixed catalog of possible beliefs. It is defined in
[belief_model.md](belief_model.md).

The canonical belief-library schema is `BeliefDefinition`, defined in
[belief_model.md](belief_model.md).

The belief library does not contain learner-specific strength, confidence, or
history.

The policy may access correct symbolic belief rules from the fixed belief
library. A correct symbolic rule is not the same as a case-specific correct
answer, expected output, evaluator label, or validation expectation.

## Learner Belief State

Learner belief state is a learner-specific record referencing fixed belief
library entries. It is defined in [belief_model.md](belief_model.md).

The canonical learner-belief schemas are `LearnerBelief` and
`LearnerBeliefState`, defined in [belief_model.md](belief_model.md).

Learner belief state may change over time only through fixed learner-update
rules.

Learner belief state is the single source of truth for belief strength,
misconception strength, belief confidence, and belief activation history.

## Learner State

Learner state represents learner characteristics and interaction history. It is
defined in [learner_model_spec.md](learner_model_spec.md).

It may include:

- topic mastery
- prerequisite mastery
- concept confidence
- persistence
- hint tendency
- guess tendency
- bounded interaction history
- references to learner belief state

Learner state changes gradually over time through fixed update rules.

Learner state does not own permanent misconception definitions. It may retain
the last activated belief ID in bounded interaction history.

## Learner Policy

The learner policy decides how the learner behaves during one interaction.

The policy does not directly choose "correct" or "incorrect."

The policy outputs a behavior plan containing:

- `activated_belief_id`, or no belief
- `action`: `answer`, `guess`, `request_hint`, `abstain`, or `revise`
- `expressed_confidence`
- persistence decision
- optional reasoning mode

Correctness is an observable consequence of applying the activated belief, not
a direct policy field.

The policy does not define objective knowledge, belief schema, belief library
entries, symbolic rules, misconception definitions, or update rules.

During autonomous optimization, the policy implementation is the only learner
component that may be changed.

## Policy-Visible Inputs

The policy may read only:

- topic mastery
- prerequisite mastery
- concept confidence
- persistence
- hint tendency
- guess tendency
- bounded interaction history
- learner belief state
- prompt-facing question content
- concept IDs needed for reasoning
- fixed belief library entries for those concepts
- bounded interaction context

Profile schemas should mirror policy-visible initialization fields only.

Allowed profile initialization fields are:

- `topic_mastery`
- `prerequisite_mastery`
- `concept_confidence`
- `persistence`
- `hint_tendency`
- `guess_tendency`
- learner belief-state references and initial values

Forbidden profile fields are:

- expected correctness intervals
- expected hint intervals
- scoring weights
- forbidden-behavior labels
- acceptable evaluator patterns
- validation-specific metadata

Evaluator-only expectations must remain in separate benchmark records and must
never be included in prompt-facing or policy-facing profile objects.

The policy-visible interaction context may include only:

- attempt number
- whether a hint is available
- whether learner-facing feedback was received
- prior learner answer text
- prior action
- recent activated belief IDs
- bounded interaction history

The policy must not access:

- expected behavior labels
- correctness intervals
- hint probability intervals
- scoring weights
- forbidden-behavior annotations
- aggregate validation results
- hidden test metadata
- benchmark-specific optimization hints
- evaluator correctness judgment unless presented as learner-facing feedback
- detector outputs
- behavioral-fidelity scores
- validation aggregates
- case-specific correct answers
- expected outputs
- evaluator labels
- validation expectations

## Learner-Facing Feedback

Learner-facing feedback is a strict object separate from evaluator output.

It contains:

- `feedback_type`: `none`, `correctness_only`, `hint`, `explanation`, or
  `corrective_feedback`
- `learner_message`
- `target_concept_ids`
- `referenced_belief_ids`
- `source`: `tutor`, `environment`, or `instructor`

The update layer may consume learner-facing feedback.

The update layer may not consume evaluator scores, detector internals, hidden
labels, behavioral-fidelity scores, or validation aggregates.

## Learner Update Layer

The learner update layer controls how learner state and learner belief state
change after:

- learner-facing correctness feedback
- learner-facing hints
- learner-facing explanations
- learner-facing corrective feedback
- repeated failure
- repeated successful practice

Update behavior is fixed during policy autoresearch.

The fixed V0 update constants are defined in
[learner_model_spec.md](learner_model_spec.md).

The update layer may use learner-facing feedback and observable interaction
records. It may not use evaluator-only signals.

## Language Expression Layer

The language expression layer converts the selected behavior plan and activated
belief into natural language.

The expression layer must verbalize the selected behavior plan and activated
belief.

It must not independently solve the question.

It must not repair, override, enrich, or replace the activated belief using
external correctness.

If it cannot express the plan faithfully, it should return a generation failure
rather than correct the learner.

The language expression layer does not independently choose:

- correctness
- misconception
- hint behavior
- confidence
- learner-state updates

These decisions are made before language generation.

## Behavioral Evaluation

The evaluator observes produced behavior rather than trusting internal
declarations.

It evaluates:

- correctness distribution
- misconception adherence
- prerequisite consistency
- confidence consistency
- hint behavior
- reasoning behavior
- profile separation
- longitudinal consistency

The primary objective is behavioral fidelity, not answer accuracy.

Evaluator observations and evaluator scores are not learner-facing feedback
unless an experiment explicitly converts them into a learner-facing feedback
object.

## Data Boundary Matrix

| Component | Owns | May read | May write | Prohibited access |
| --- | --- | --- | --- | --- |
| Objective Knowledge Library | Concept-level correct domain rules, procedures, prerequisite relationships | Public domain definitions and approved benchmark-facing concept metadata | Objective knowledge files only when explicitly approved | Hidden test data, validation labels, evaluator scoring weights |
| Belief Library | Fixed belief schema entries, symbolic rule identifiers, belief types, prerequisite concept IDs | Objective Knowledge Library and approved misconception definitions | Belief library only when explicitly approved | Learner-specific strength, confidence, activation history, evaluator labels, hidden test data |
| Learner Belief State | Per-learner belief strength, belief confidence, status, evidence count, activation history | Belief Library, learner-facing feedback, observable interaction history | Learner belief records through fixed update rules | Permanent belief definitions, evaluator scores, detector internals, hidden labels |
| Learner State | Topic mastery, prerequisite mastery, concept confidence, persistence, hint tendency, guess tendency, bounded interaction history | Learner-facing feedback, observable interaction records, learner belief state references | Learner state through fixed update rules | Benchmark expectations, scoring weights, hidden test metadata, evaluator-only detector outputs |
| Learner Policy | Behavior plan for one interaction | Policy-visible inputs, bounded interaction context, fixed belief library entries for relevant concepts | Behavior plan only | Case-specific correct answers, expected outputs, evaluator labels, validation expectations, aggregate scores, hidden test data |
| Language Expression Layer | Natural-language rendering of a behavior plan | Prompt-facing question content, behavior plan, activated belief | Observable response or generation failure | External correctness used to repair or replace the activated belief, evaluator labels, hidden data |
| Learner Update Layer | Fixed state-transition application | Learner-facing feedback, observable interaction records, prior learner state, prior learner belief state | Learner state and learner belief state | Evaluator scores, detector internals, hidden labels, validation aggregates |
| Evaluator | Behavioral observations, detector outputs, benchmark scores | Observable responses, public validation cases, evaluator configuration | Evaluation outputs and result summaries | Hidden test data outside its authorized evaluation environment; learner policy internals as a shortcut |
| Benchmark Data | Public development and validation cases, prompt-facing case views, allowed concept mappings | Objective Knowledge Library and approved case metadata | Benchmark data only with human approval | Hidden test data, evaluator-only labels exposed to policy |
| Hidden Test Data | Hidden held-out cases and labels | Nothing in the Codex workspace | Nothing in the Codex workspace | Any access by learner policy, language expression, autoresearch, or documentation-driven optimization |

## Validation and Autoresearch Boundaries

Development data may be inspected during normal engineering.

Validation data may be evaluated, but its labels, expected behavior fields, and
evaluator-only annotations must not be passed to policy code.

Hidden test data remains outside the Codex workspace.

Autonomous optimization may modify only:

- `learner/policy.py`
- `results.tsv`
- temporary run logs

Architecture, beliefs, update rules, evaluator behavior, benchmark data,
profiles, schemas, and tests require human approval to change.

During autonomous experimentation, the following remain fixed:

- `prepare.py`
- `evaluate.py`
- `fixed/`
- `data/`
- `profiles/`
- `schemas/`
- `knowledge/`
- `learner/state.py`
- `learner/update.py`
- belief schema
- belief library
- update rules
- tests
- hidden test data

Each experiment must:

1. form one focused hypothesis;
2. modify `learner/policy.py`;
3. run tests;
4. run the validation evaluator;
5. record results;
6. keep the change only if behavioral fidelity improves without violating
   guardrails;
7. otherwise revert the change.

## Current Design Decision

The system uses multiple competing beliefs per concept.

Each library belief may be:

- correct
- misconception
- partial
- unknown

The learner policy selects among active learner belief records using deterministic
belief activation. The fixed V0 baseline activation formula is defined in
[belief_model.md](belief_model.md).

## Architecture Version

Version: 0.2

Date: 2026-07-13

Initial decisions:

- separated the learner from the language model;
- introduced structured competing beliefs;
- separated learner state, learner belief state, policy, and updates;
- restricted autoresearch to `learner/policy.py`;
- established behavioral fidelity as the optimization objective;
- separated evaluator scoring from learner-facing feedback.

## Authoritative Scope

This document owns system boundaries, component responsibilities, allowed data
flows, validation boundaries, and autoresearch boundaries.

[learner_model_spec.md](learner_model_spec.md) owns learner-state semantics and
fixed state transitions.

[belief_model.md](belief_model.md) owns belief schema, belief-library semantics,
learner belief state, and belief activation semantics.
