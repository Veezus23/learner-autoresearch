# Evaluator Design

Phase 2 adds a fixed deterministic evaluator for structured simulated-learner
responses. The evaluator scores behavioral fidelity to the case expectations
rather than raw answer accuracy alone.

## Input response format

Each JSONL row must be a JSON object with this schema:

```json
{
  "case_id": "case_001",
  "answer": "...",
  "requested_hint": false,
  "expressed_confidence": 0.25,
  "applied_misconception": "power_set_means_original_set",
  "reasoning_features": ["..."]
}
```

`applied_misconception` may be `null` when no misconception is being applied.
`expressed_confidence` must be a numeric value from 0 to 1.

## Scoring dimensions

The evaluator emits per-case scores from 0 to 1 for:

- `correctness_alignment`
- `misconception_adherence`
- `prerequisite_consistency`
- `confidence_consistency`
- `hint_behavior_consistency`
- `reasoning_feature_alignment`
- `forbidden_behavior_penalty`

Correctness and hint behavior are scored against the expected probability
intervals. A single structured response is treated as one observed sample:
correct or incorrect for correctness, requested or not requested for hint
behavior. If the observed value is inside the interval it receives full credit.
If it is outside, credit declines linearly by distance from the nearest interval
edge. This means a weak learner can be penalized for always giving correct
answers.

Confidence is scored with fixed bands:

- low: 0.00 to 0.35
- medium: 0.36 to 0.69
- high: 0.70 to 1.00

Misconception adherence compares `applied_misconception` to the case's active
misconceptions and acceptable error patterns. Cases without an expected
misconception receive full misconception credit only when the response leaves
`applied_misconception` empty.

Prerequisite consistency gives credit when missing prerequisites plausibly show
up through an expected misconception, an explicit prerequisite reference, or a
reasoning feature describing profile limitations. Cases without missing
prerequisites receive full credit unless the response applies an unrelated
misconception.

Reasoning feature alignment is exact normalized string overlap with the case's
`required_reasoning_features`.

Forbidden behavior is applied after the weighted score. The current deterministic
checks detect unrelated misconceptions, high confidence on low-confidence cases,
low confidence on high-confidence cases, and exact forbidden reasoning features.
Each violation subtracts `0.20`, capped at `0.60`.

## Composite score

The unpenalized weighted score is:

```text
0.20 * correctness_alignment
+ 0.25 * misconception_adherence
+ 0.15 * prerequisite_consistency
+ 0.15 * confidence_consistency
+ 0.10 * hint_behavior_consistency
+ 0.15 * reasoning_feature_alignment
```

The final `behavioral_fidelity` is:

```text
max(0, weighted_score - forbidden_behavior_penalty)
```

## CLI

Evaluate a JSONL response file:

```bash
python evaluate.py --split development --responses responses.jsonl --output report.json
```

Run the built-in deterministic baseline used for evaluator tests:

```bash
python evaluate.py --split development --baseline
```

The baseline is intentionally simple evaluator-test support. It is not a learner
policy and should not be optimized as one.

## Known limitations

- Single-response scoring approximates probability intervals with one observed
  sample. Repeated-response protocols would be more faithful.
- Answer matching uses lightweight normalization, not symbolic math.
- Reasoning feature alignment is exact string overlap.
- Forbidden behavior detection is limited to structured fields and simple
  confidence conflicts.
- The evaluator depends on synthetic expert-authored expectations that should be
  calibrated against real student data in later benchmark versions.
