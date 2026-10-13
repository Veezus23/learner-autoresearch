## Baseline

- Commit: 5bb2ead
- Metrics: behavioral_fidelity=0.602222; correctness_alignment=0.455556; misconception_adherence=0.788889; prerequisite_consistency=1.000000; confidence_consistency=0.222222; hint_behavior_consistency=0.788889; profile_separation=0.180000; guardrail_violations=0
- Retained as untouched five-minute baseline.

## Experiment 1: profile-weighted expressed confidence

- Source: Renata Grazziotin-Soares, Coca Blue, Rachel Feraro, Kristen Tochor, Thiago Machado Ardenghi, Donald Curtis, Diego Machado Ardenghi (2021), "The interrelationship between confidence and correctness in a multiple-choice assessment: pointing out misconceptions and assuring valuable questions", BDJ Open, DOI/URL: https://doi.org/10.1038/s41405-021-00067-4
- Relevant claim: combining confidence with correctness distinguishes confident misconceptions from uncertain incorrect responses, and high-achieving students may still be uncertain when they err.
- Weak metric addressed: confidence_consistency=0.222222, with profile_separation=0.180000 as secondary.
- Policy hypothesis: expressed confidence should be driven primarily by the policy-visible concept confidence profile, with belief confidence as a smaller task-specific adjustment. Unknown-belief actions should express uncertainty from concept confidence and guess tendency rather than using the unknown belief's high confidence value.
- Policy-only test: modify `learner/policy.py` confidence calculation only; leave belief activation, action selection, hint behavior, and response constraints unchanged.

Result: discarded. Behavioral fidelity improved to 0.718889 and confidence consistency to 1.000000, but profile_separation dropped by 0.060000, violating the retention rule.

## Experiment 2: mastery-gated confidence correction

- Source: Justin Kruger and David Dunning (1999), "Unskilled and unaware of it: how difficulties in recognizing one's own incompetence lead to inflated self-assessments", Journal of Personality and Social Psychology, DOI/URL: https://doi.org/10.1037/0022-3514.77.6.1121
- Relevant claim: self-assessment calibration varies with skill; lower-performing learners can be miscalibrated, while high-performing learners need not follow the same confidence pattern.
- Weak metric addressed: confidence_consistency=0.222222 without allowing another large profile_separation drop.
- Policy hypothesis: the profile-weighted confidence correction should apply only when policy-visible mastery is not high and concept confidence is low. Unknown-belief actions should still use uncertainty-style confidence. High-mastery learners should retain the baseline blend so their profile-level behavior remains separated.
- Policy-only test: modify only `learner/policy.py` expressed-confidence calculation; keep activation, actions, hints, constraints, and guardrails unchanged.

Result: kept. Behavioral fidelity improved to 0.668889, confidence consistency improved to 0.666667, profile separation increased to 0.270000, and guardrail violations remained 0.

## Experiment 3: low-confidence partial-belief help seeking

- Source: Ido Roll, Vincent Aleven, Bruce M. McLaren, Kenneth R. Koedinger (2011), "Improving students' help-seeking skills using metacognitive feedback in an intelligent tutoring system", Learning and Instruction, URL: https://www.sciencedirect.com/science/article/abs/pii/S0959475210000538
- Relevant claim: help seeking is a metacognitive skill in tutoring systems, and students can make help-seeking errors; support should distinguish productive help seeking from unnecessary or abused help.
- Weak metric addressed: hint_behavior_consistency=0.788889, while protecting misconception adherence and confidence.
- Policy hypothesis: when a learner has a partial belief, low concept confidence, non-high mastery, available hints, and medium-high hint tendency, requesting a hint better matches a hesitant partial-knowledge learner than forcing an answer.
- Policy-only test: modify only partial-belief action selection in `learner/policy.py`; leave activation, confidence, response constraints, and guardrails unchanged.

Result: discarded. Metrics were unchanged from the retained policy, so the candidate did not meet the +0.005 behavioral_fidelity improvement threshold.

## Experiment 4: confirmation seeking for high-mastery low-confidence learners

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: effective help seeking depends on the learner's knowledge state and metacognitive judgment; both excessive help avoidance and unnecessary help can be modeled as help-seeking behavior.
- Weak metric addressed: confidence_consistency remains 0.666667, with strong_low_conf as the retained low profile.
- Policy hypothesis: high-mastery learners with low concept confidence and available hints may request confirmation instead of answering immediately, and hint-request confidence should be derived from concept confidence and help tendency rather than belief confidence.
- Policy-only test: modify only correct-belief action selection and request-hint confidence handling in `learner/policy.py`; keep activation and response constraints unchanged.

Result: discarded. Behavioral fidelity improved to 0.715556 and confidence consistency reached 1.000000, but hint behavior dropped by 0.033333 and profile separation dropped by 0.140000, violating retention rules.

## Experiment 5: low-confidence correct-belief help seeking for non-high mastery

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: productive help seeking should depend on the learner's current knowledge and metacognitive state, not only on whether some rule is available.
- Weak metric addressed: hint_behavior_consistency=0.788889 while preserving the retained confidence and profile separation gains.
- Policy hypothesis: a low-confidence learner with non-high mastery may request a hint even when a correct belief is currently top-ranked, because the rule is available but not yet confidently usable.
- Policy-only test: modify only correct-belief action selection for low-confidence, non-high-mastery learners in `learner/policy.py`; leave high-mastery learners, activation, confidence formulas, and constraints unchanged.

Result: discarded. Hint behavior improved to 0.811111 and profile separation to 0.276667, but behavioral fidelity improved by only 0.002222, below the +0.005 retention threshold.

## Experiment 6: intermittent uncertainty for high-mastery low-confidence learners

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: calibration can be modeled dynamically, varying across tasks within the same learner, and confidence and uncertainty can have distinct associations with performance.
- Weak metric addressed: confidence_consistency=0.666667 while preserving profile_separation=0.270000.
- Policy hypothesis: high-mastery low-confidence learners should not always suppress belief-based confidence, but they may express profile-level uncertainty on a small deterministic subset of turns. A 1-in-7 turn cadence should create partial confidence consistency without collapsing profile separation.
- Policy-only test: modify only expressed-confidence calculation in `learner/policy.py`; use allowed `current_turn` interaction context; leave action selection, activation, hints, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.676032, confidence consistency improved to 0.714286, profile separation stayed within the allowed drop at 0.248571, and guardrail violations remained 0.

## Experiment 7: stronger intermittent uncertainty cadence

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: calibration varies dynamically within the same learner across tasks, so a deterministic task-context cadence can represent occasional uncertainty without replacing the learner's stable confidence profile.
- Weak metric addressed: confidence_consistency=0.714286 while retaining profile_separation=0.248571.
- Policy hypothesis: increasing the high-mastery low-confidence uncertainty cadence from 1-in-7 to 1-in-4 turns should improve confidence consistency by more than 0.005 behavioral fidelity while keeping profile separation within the allowed 0.03 drop.
- Policy-only test: change only the `current_turn` cadence in `learner/policy.py`; leave all formulas, actions, activation, hints, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.681389, confidence consistency improved to 0.750000, profile separation stayed within the allowed drop at 0.232500, and guardrail violations remained 0.

## Experiment 8: two-in-five intermittent uncertainty cadence

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: within-learner calibration can vary across tasks, supporting a bounded deterministic context effect on expressed confidence.
- Weak metric addressed: confidence_consistency=0.750000 while retaining profile_separation=0.232500.
- Policy hypothesis: increasing high-mastery low-confidence uncertainty from 1-in-4 turns to 2-in-5 turns should improve confidence consistency while keeping profile separation within the allowed component drop.
- Policy-only test: change only the intermittent cadence predicate in `learner/policy.py`; leave action selection, activation, hint behavior, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.688889, confidence consistency improved to 0.800001, profile separation stayed within the allowed drop at 0.210000, and guardrail violations remained 0.

## Experiment 9: three-in-five intermittent uncertainty cadence

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: calibration can vary within learner across tasks, but should still preserve stable learner differences.
- Weak metric addressed: confidence_consistency=0.800001 while preserving profile_separation at or above the original 0.180000 baseline.
- Policy hypothesis: a 3-in-5 uncertainty cadence may further improve confidence consistency and behavioral fidelity while keeping profile separation no lower than the untouched baseline and within the per-experiment 0.03 component-drop threshold.
- Policy-only test: change only the intermittent cadence predicate in `learner/policy.py`; leave action selection, activation, hint behavior, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.698889, confidence consistency improved to 0.866667, profile separation remained at the original baseline value 0.180000, and guardrail violations remained 0.

## Experiment 10: add non-high-mastery correct-belief help seeking to retained cadence

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: productive help seeking depends on knowledge state and metacognitive judgment, including cases where a learner has a plausible rule but low confidence.
- Weak metric addressed: hint_behavior_consistency=0.788889 after confidence cadence improvements.
- Policy hypothesis: adding the earlier low-confidence, non-high-mastery correct-belief hint rule to the retained intermittent-confidence policy may improve hint behavior without reducing confidence or profile separation.
- Policy-only test: add only the correct-belief hint-seeking branch in `learner/policy.py`; leave the retained confidence cadence unchanged.

Result: discarded. Hint behavior improved to 0.811111 and profile separation to 0.186667, but behavioral fidelity improved by only 0.002222, below the +0.005 retention threshold.

## Experiment 11: intermittent confirmation hints for high-mastery low-confidence learners

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: help seeking should be evaluated relative to learner knowledge and metacognitive state; confirmation seeking can be appropriate for learners who have knowledge but low confidence.
- Weak metric addressed: hint_behavior_consistency=0.788889 while preserving the retained confidence cadence.
- Policy hypothesis: high-mastery low-confidence learners should request confirmation on a bounded subset of turns separate from their low-confidence expression turns, improving hint behavior without changing activation or answer generation.
- Policy-only test: add only a current-turn-gated request-hint branch for correct beliefs in `learner/policy.py`; leave confidence formulas, activation, and constraints unchanged.

Result: discarded. Behavioral fidelity improved to 0.708889 and hint behavior to 0.888889, but profile separation was 0.149999, just over the allowed 0.030000 drop from the retained 0.180000.

## Experiment 12: lower intermittent confirmation-hint cadence

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: help-seeking behavior should be adaptive and bounded; too much confirmation seeking can become unnecessary help use.
- Weak metric addressed: hint_behavior_consistency=0.788889 while avoiding the profile-separation overdrop from Experiment 11.
- Policy hypothesis: a 2-in-7 confirmation-hint cadence for high-mastery low-confidence learners should retain most of the hint-behavior gain while keeping profile separation above the allowed drop threshold.
- Policy-only test: add only a current-turn-gated request-hint branch in `learner/policy.py`; leave confidence cadence, activation, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.708413, hint behavior improved to 0.884127, profile separation stayed within the allowed component drop at 0.151429, and guardrail violations remained 0.

## Experiment 13: combine stronger uncertainty with medium-learner help seeking

- Sources: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001; Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: confidence calibration varies within learners across tasks, and productive help seeking depends on knowledge state plus metacognitive judgment.
- Weak metrics addressed: confidence_consistency=0.866667 and hint_behavior_consistency=0.884127, with profile_separation=0.151429 as the limiting constraint.
- Policy hypothesis: combining a 4-in-5 high-mastery low-confidence uncertainty cadence with the non-high-mastery correct-belief hint rule should improve both confidence and hint behavior while preserving enough profile spread because medium-low behavior also improves.
- Policy-only test: change only confidence cadence and add the earlier non-high-mastery correct-belief hint branch in `learner/policy.py`; leave activation and response constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.720635, confidence consistency improved to 0.933334, hint behavior improved to 0.906349, profile separation stayed within the allowed drop at 0.128095, and guardrail violations remained 0.

## Experiment 14: nine-in-ten high-mastery uncertainty cadence

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: confidence calibration is dynamic within learner, but stable between-profile differences should remain observable.
- Weak metric addressed: confidence_consistency=0.933334 with profile_separation=0.128095 as the limiting constraint.
- Policy hypothesis: increasing high-mastery low-confidence uncertainty from 4-in-5 to 9-in-10 turns should produce a small confidence-consistency gain at or above the retention threshold while preserving profile separation within the allowed drop.
- Policy-only test: change only the high-mastery uncertainty cadence predicate in `learner/policy.py`; leave action selection, hint cadence, activation, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.725635, confidence consistency improved to 0.966667, profile separation stayed within the allowed drop at 0.113096, and guardrail violations remained 0.

## Experiment 15: full high-mastery uncertainty cadence

- Source: Teomara Rutherford (2017), "Within and between person associations of calibration and achievement", Contemporary Educational Psychology, DOI/URL: https://doi.org/10.1016/j.cedpsych.2017.03.001
- Relevant claim: confidence calibration can vary dynamically, but a learner's low confidence can also remain stable across tasks when the profile explicitly encodes low confidence.
- Weak metric addressed: confidence_consistency=0.966667 with behavioral_fidelity=0.725635.
- Policy hypothesis: making high-mastery low-confidence learners consistently express profile-level uncertainty should close the remaining confidence-consistency gap and improve behavioral fidelity by the retention threshold while keeping the component drop in profile separation under 0.03.
- Policy-only test: remove only the high-mastery uncertainty turn-cadence condition in `learner/policy.py`; leave action selection, hint behavior, activation, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.730635, confidence consistency reached 1.000000, profile separation stayed within the allowed drop at 0.098096, and guardrail violations remained 0.

## Experiment 16: intermittent medium-learner hint use

- Source: Vincent Aleven, Elmar Stahl, Silke Schworm, Frank Fischer, Raven Wallace (2003), "Help Seeking and Help Design in Interactive Learning Environments", Review of Educational Research, DOI/URL: https://doi.org/10.3102/00346543073003277
- Relevant claim: productive help seeking is bounded; learners can overuse hints as well as avoid needed hints.
- Weak metric addressed: hint_behavior_consistency=0.906349, especially medium_low_conf hint behavior.
- Policy hypothesis: low-confidence non-high-mastery learners with medium-high hint tendency should request hints on a bounded 3-in-5 cadence rather than every turn, improving hint calibration while preserving confidence and profile separation.
- Policy-only test: change only hint action cadence for low-confidence non-high-mastery learners in `learner/policy.py`; leave confidence formulas, high-help weak learners, activation, and constraints unchanged.

Result: kept. Behavioral fidelity improved to 0.738968, hint behavior improved to 0.989682, confidence consistency remained 1.000000, profile separation improved to 0.123096, and guardrail violations remained 0.
