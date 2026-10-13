# Benchmark Design

## Size

Total cases: 36

- Development: 18
- Validation: 9
- Test: 9

## Coverage

Three domains:
- Sets
- Algebra sign rules
- Fractions and ratios

Six canonical profiles cross mastery and confidence:
- weak / low confidence
- weak / high confidence
- medium / low confidence
- medium / high confidence
- strong / low confidence
- strong / high confidence

## Why these splits exist

Development cases can be inspected while building the policy.
Validation cases determine whether an autoresearch change is retained.
Test cases should remain hidden until final evaluation.

## Known limitations

- Labels are synthetic.
- Probability ranges are not yet calibrated.
- There are too few questions for robust generalization claims.
- Hint behavior is represented as an expected frequency but no interaction protocol is included yet.
- Longitudinal state updates are not included in V0.
- Some behavioral dimensions will initially need a hybrid rule-based and human evaluator.

## Next benchmark upgrades

1. Add repeated-response protocols.
2. Add multi-turn hint and feedback sequences.
3. Obtain real student responses.
4. Measure inter-rater agreement.
5. Expand each domain to at least 30 questions.
6. Add adversarial paraphrases and unseen concepts.
