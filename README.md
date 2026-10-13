# Learner Agent Benchmark V0

Phase 1 benchmark for evaluating simulated learner agents.

## Goal

Measure whether a learner agent behaves consistently with a specified profile rather than simply maximizing correctness.

## Domains

- Sets
- Algebra sign rules
- Fractions and ratios

## Splits

- Development: visible to Codex during iteration
- Validation: used by the fixed evaluator to accept or reject changes
- Test: hidden from the builder until final evaluation

## Files

- `profiles/learner_profiles.json`: canonical learner profiles
- `misconceptions/misconception_bank.json`: misconception definitions and signatures
- `schemas/case.schema.json`: benchmark case schema
- `data/*/cases.jsonl`: benchmark cases
- `docs/annotation_guide.md`: how expected behaviors should be labeled
- `docs/benchmark_design.md`: design choices and limitations

## Important limitation

This V0 uses expert-authored synthetic expectations. It is suitable for testing engineering consistency, but it is not yet evidence that the agents match real students. Later versions should be calibrated with real student responses and longitudinal interaction data.


## Autoresearch experiment

`program.md` defines a bounded search over `learner/policy.py` using a fixed evaluator. The development and validation cases are included so the benchmark can be inspected and rerun. The hidden test set and private index are excluded. The optimization target is **behavioral fidelity to a simulated learner profile**, not raw answer accuracy; the synthetic benchmark does not establish fidelity to real students.

The recorded validation score rose from **0.6022 to 0.7390** across 16 documented policy experiments. These are results on the fixed synthetic benchmark, not student-outcome measurements. `research_notes.md` records every hypothesis and keep/discard decision.

Install `requirements.txt`, then run `python -m pytest tests -q`. See `docs/architecture.md` and `research_notes.md` for the architecture and experiment reasoning.
