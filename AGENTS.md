# Codex instructions

This repository contains the public development and validation benchmark for simulated learner agents.

You may inspect and modify files inside this repository only.

Do not search for, access, or infer the hidden test set.
Do not modify validation labels, schemas, or fixed evaluator files once Phase 2 begins.
Do not hard-code question IDs, exact answers, or validation cases into learner policies.

The research objective is to improve behavioral fidelity to learner profiles, not raw answer accuracy.

## Architecture-driven workflow

This repository is architecture-driven. `docs/architecture.md` is the
authoritative specification.

Before every implementation task, read:

- `docs/architecture.md`
- any architecture documents directly relevant to the task, such as
  `docs/belief_model.md`, `docs/learner_model_spec.md`, or
  `docs/evaluator_design.md`

If the requested implementation conflicts with `docs/architecture.md`, stop and
report the conflict before writing code.

Before implementing, summarize the architectural constraints relevant to the
task.

After implementing, explain how every relevant architectural constraint was
satisfied.

Prefer updating architecture documents before implementing large structural
changes.

During autonomous optimization, only `learner/policy.py` may be modified.

Never modify the following unless explicitly instructed by a human:

- benchmark datasets
- hidden test data
- evaluator labels
- `prepare.py`
- `evaluate.py`
- `fixed/`
- `learner/state.py`
- `learner/update.py`
