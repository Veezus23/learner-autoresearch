# Expression Implementation

Version: 0.1

The V0 expression layer converts a `BehaviorPlan` and activated belief metadata
into a learner-visible natural-language response. It does not select beliefs,
choose actions, change confidence, judge correctness, call evaluators, or update
learner state.

## Public API

- `ExpressionInput`
- `StudentResponse`
- `build_expression_prompt(expression_input)`
- `ExpressionAdapter.generate(prompt)`
- `ExternalExpressionAdapter`
- `MockExpressionAdapter`
- `parse_student_response(raw_output, expression_input)`
- `express_response(expression_input, adapter)`

## Input Boundary

`ExpressionInput` contains only:

- question text;
- `BehaviorPlan`;
- selected `BeliefDefinition` and `LearnerBelief`, or no selected belief;
- read-only transformation metadata;
- optional prior response text;
- optional learner-facing feedback;
- expression version.

It rejects extra evaluator-only, benchmark-only, hidden-test, scoring,
validation, expected-answer, and optimization fields. Activated belief objects
must match `BehaviorPlan.activated_belief_id`.

## Prompt Structure

The deterministic prompt states that the model is an expression engine, not the
learner. It includes:

- student-facing question;
- selected action, expressed confidence, confidence band, reasoning mode, and
  symbolic constraints;
- selected belief description and type when available;
- transformation identifier and human-readable metadata when available;
- action-specific instructions;
- reasoning-mode-specific instructions;
- prior response and learner-facing feedback only for revise behavior.

The prompt explicitly forbids independent solving, selected-belief repair,
external correctness use, unauthorized self-correction, architecture or policy
mentions in the student answer, and output beyond the learner-facing response.
It reserves `<EXPRESSION_FAILURE>` for faithful-expression failure.

## Adapter Boundary

`ExpressionAdapter` is provider-neutral. `ExternalExpressionAdapter` is a
lightweight callable wrapper and performs no network calls.

`MockExpressionAdapter` is deterministic and intended only for infrastructure
tests and dry runs. It uses action, confidence band, and transformation identity
from the prompt to produce predictable student-style responses. It contains no
benchmark answer keys or case-specific mappings and makes no behavioral
fidelity claims.

## Parser Boundary

`parse_student_response` returns `StudentResponse` while preserving plan action,
numeric confidence, and activated belief ID. It does not judge mathematical
correctness and does not infer misconception labels for scoring.

The parser deterministically:

- maps exactly `<EXPRESSION_FAILURE>` to `generation_status = "failed"`;
- rejects empty output;
- rejects internal architecture leakage such as `BehaviorPlan`, `PolicyInput`,
  `belief_id`, `transformation_id`, `evaluator`, or `benchmark`;
- rejects hint responses that include substantive answers;
- rejects abstain responses that look like polished solutions.

Rejected or failed outputs preserve raw output as diagnostic metadata.

## Pipeline Boundary

`express_response` validates the immutable input, builds the prompt, calls the
adapter, parses the raw output, and returns `StudentResponse`.

The pipeline does not update learner state, update belief state, call the
evaluator, choose a belief, modify the behavior plan, or retry by changing
learner behavior.

## V0 Limitation

The transformation registry stores identity and metadata only. It does not
execute transformations, solve benchmark cases, or generate case-specific
answers. The V0 mock adapter therefore uses deterministic placeholders based on
transformation IDs. Production behavior must delegate natural-language
expression to an external model through the adapter interface without exposing
case-specific answer keys to this layer.
