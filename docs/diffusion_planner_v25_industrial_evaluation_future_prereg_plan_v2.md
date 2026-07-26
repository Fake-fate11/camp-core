# V25 Industrial Evaluation v2 Future Preregistration Plan

This is a contract plan only. It authorizes no model, pool, selector, training,
calibration, validation, closed-loop, Fresh, or holdout run.

Before future outcome access:

1. Freeze the exact 161-leaf registry and its source-capability receipt.
2. Freeze scenario/corridor-intersection clusters as independent units and
   equal-cluster weighting; never use ticks, rows, arms, or seeds as `n`.
3. Freeze a numeric margin for every hard-safety or guardrail leaf intended for
   a claim. Until then its state remains
   `numeric_margin_not_authorized_until_future_preregistration`.
4. Use one-sided equal-cluster Student-t CI95 for directed leaves and two-sided
   CI95 for descriptive-unclassified leaves.
5. Apply Holm-Bonferroni step-down within the exact registered family at
   familywise alpha 0.05.
6. Require the hard-safety IUT to pass before the guardrail IUT; require every
   testable registered leaf in each layer to pass.
7. Treat missing/failure on a required leaf as claim-blocking; retain the full
   planned denominator and never substitute zero or complete cases.
8. Use exact-zero paired delta as B/T/W tie only where direction and full
   pairing are defined.
9. Never create a weighted total or allow descriptive performance to
   compensate safety.
10. Preserve SafetyCost only as immutable legacy exploratory evidence.

New nonholdout instrumentation is required for target same-ego batch8
pool/atoms/context/selector/end-to-end timing under controlled warm-up,
concurrency/load, and scheduler conditions. Unique-leader semantics, conflict
zones, justified-stop context, contact dynamics, and occupant/seat/vertical
measurements require separate prospective acquisition if those endpoints are
to become testable.

A future PASS can only address the preregistered bounded benchmark. It cannot
establish industrial certification, occupant comfort conformity, real-road
safety, broad unseen-map generalization, promotion, deployment, online
activation, or production readiness.
