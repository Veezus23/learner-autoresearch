# Belief Implementation

Version: 0.1

This implementation adds a fixed cognition layer and learner-specific belief
state without changing the deterministic evaluator baseline.

## Fixed Cognition Layer

`cognition/` contains objective concept-level definitions:

- `BeliefDefinition` is an immutable fixed-library record.
- `TransformationDefinition` is an immutable metadata record.
- `BeliefLibrary` is an immutable catalog of fixed belief definitions.
- `PrerequisiteGraph` stores canonical benchmark concept prerequisites.

The transformation registry stores identity and metadata only. It does not
execute symbolic rules, solve benchmark cases, generate answers, or expose
case-specific expected outputs.

## Learner Belief State

`learner/belief_state.py` contains learner-specific records:

- `LearnerBelief`
- `LearnerBeliefState`

These records own learner-specific belief strength, belief confidence, status,
evidence count, activation count, and activation recency. Operations return new
objects instead of mutating existing state.

Learner belief status has fixed V0 semantics:

- `active`: eligible for activation;
- `inactive`: retained but excluded from activation;
- `retired`: no longer usable.

Activation ranking considers active beliefs only. `strongest_belief` is a
simple current-strength view and is distinct from activation ranking.

Semantic changes to an existing belief require a new `belief_id`. Updating
`version` alone must not silently alter the meaning of an existing learner
belief reference.

## Error Description vs Transformation vs Outcome

The belief layer keeps three concerns separate.

An error description is the abstract misconception or buggy commitment. For
example, `adds_denominators` means the learner treats fraction addition as if
both numerators and denominators should be added directly.

An error simulation transformation is the reusable operation identity that can
instantiate the error across prompts. For example,
`add_numerators_and_denominators` identifies the reusable operation associated
with that misconception. The transformation record is metadata only.

Outcome generation is deferred to a future policy and expression pipeline. The
belief layer does not produce benchmark answers, compare against answer keys, or
read evaluator labels. Correctness remains an observable consequence of applying
an activated belief later in the pipeline.

## Activation Support

Activation support is deterministic:

`A(b) = 0.40*S + 0.25*C + 0.25*P + 0.10*R`

Where:

- `S` is learner-specific current strength.
- `C` is learner-specific belief confidence.
- `P` is prerequisite support.
- `R` is normalized recency.

Correct and partial beliefs use the mean mastery of their declared
prerequisites. Misconception beliefs use only the prerequisites declared by that
misconception. Unknown beliefs use prerequisite support `1.0`.

Recency is `0.0` for a belief that has never activated, `1.0` when it activated
at the current turn, decays linearly over 10 turns, and is `0.0` after 10 or
more turns.

Ranking is deterministic by activation score, prerequisite support, current
strength, and lexicographic belief ID. No stochastic sampling, correctness
choice, learner action choice, or answer generation happens in this layer.

## Data Boundaries

Belief definitions do not include:

- learner-specific strengths;
- belief confidence;
- case IDs;
- answer keys;
- expected outputs;
- evaluator labels;
- validation metadata.

The default catalog uses public misconception IDs as fixed belief IDs so the
current benchmark misconceptions can be represented without exposing benchmark
answers to the belief layer.
