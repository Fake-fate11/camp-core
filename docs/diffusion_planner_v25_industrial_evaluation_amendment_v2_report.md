# V25 Industrial-Oriented Evaluation-System Amendment v2

Status: `industrial_oriented_evaluation_system_amendment_v2_independently_reviewed_scientific_contract_review_required`

This is an outcome-independent correction to the v1 amendment. It ran no
model, pool, selector, training, calibration, validation, closed-loop, Fresh,
holdout, or legacy evaluation, and read no B4/Fresh outcome value. The v1
artifacts remain immutable superseded pre-correction diagnostics.

## Outcome

The evaluation contract is a four-domain endpoint vector with no weighted
total:

1. safety;
2. operations;
3. vehicle-body planar kinematic comfort proxy;
4. controlled-benchmark realtime.

The 56 domain/family rows are retained for navigation, but they are no longer
the machine decision surface. They expand to an exact **161-scalar-leaf
registry**. Every scalar statistic, threshold, tolerance, percentile, latency
stage, and hypothetical budget has its own canonical leaf ID, units,
direction, formula, applicability, opportunity denominator, missing policy,
decision role, multiplicity family, CI rule, and B/T/W applicability. Unknown,
omitted, duplicated, or renamed leaves fail closed.

Leaf evidence classes are:

- 119 `reconstructable_with_frozen_transform`;
- 41 `evidence_missing`;
- 1 `scientifically_inapplicable`;
- 0 `directly_reconstructable`.

Decision roles are 14 hard-safety, 96 guardrail, 9 descriptive-only, and 42
evidence-missing/not-testable leaves.

## Sealed-evidence capability audit

The capability matrix is no longer a projection of producer declarations.
For every scalar leaf it verifies the complete seals of the accepted B4
execution/execution review, Evaluation v2 contract/review and
materialization/review, and metric-semantics contract/review. It then binds
exact artifact/review roots, exact `SHA256SUMS` entries and file SHA256 values,
canonical JSON pointers, source shapes and units, applicability prerequisites,
and transform inputs.

The audit opens only outcome-independent contract reports and the execution
artifact metadata binding. It does not open per-run rows or outcome values.
Where structural existence cannot be proven from those sealed inventories, the
leaf is `evidence_missing`; a broad glob or producer status string is never
accepted as evidence.

## Collision semantics

`collision_onset_relative_closing_speed_kinematic_proxy_mps` is available from
the same sealed full-OBB and relative-motion inputs used by clearance, closing,
geometry TTC, and DRAC. At the first false-to-true full-OBB intersection it
uses the last finite noncollision interval and linearly interpolates signed
centroid closing speed to the first-contact fraction. If no authoritative
preceding interval exists, it remains typed missing.

This is only a severity-related kinematic proxy. It is not delta-v, contact
impulse, or contact severity. True collision delta-v and contact severity
remain `evidence_missing`.

## Statistical and decision topology

Future paired work must summarize per run first and use only a prospectively
registered scenario/corridor-intersection cluster as independent `n`. Clusters
receive equal mass. Directed leaves use a one-sided equal-cluster Student-t
CI95 in their registered direction; descriptive-unclassified leaves use a
two-sided equal-cluster Student-t CI95.

Multiplicity is frozen as
`holm_bonferroni_step_down_within_exact_family` at familywise alpha 0.05.
Hard-safety leaves combine by intersection-union: every preregistered,
testable hard-safety leaf must pass. Guardrails use the same all-pass IUT after
the hard-safety layer. Missing required evidence blocks the relevant future
claim, and descriptive leaves cannot compensate. No weighted compensation is
allowed.

The exact families are collision hard safety, red hard safety,
containment/direction hard safety, dynamic-exposure guardrails, operations
guardrails, planar-proxy guardrails, controlled-benchmark realtime
guardrails, and not-testable evidence gaps. B/T/W uses 500 paired units only
when applicable, with exact-zero paired delta as tie.

Numeric margins remain
`numeric_margin_not_authorized_until_future_preregistration`. Consequently no
hard-safety or guardrail leaf is currently a claim gate. This amendment
freezes the topology but authorizes no claim.

## Scientific boundaries

SafetyCost and its six components remain
`immutable_legacy_exploratory_diagnostic_only` evidence. They are never primary endpoints,
PASS/claim criteria, training-support evidence, or adaptation evidence.

The planar proxy remains 64 positions -> 63 interval velocities -> 62
body-frame accelerations -> 52 valid-only filtered acceleration samples -> 51
filtered jerk samples. It is not occupant/seat comfort, ISO 2631 conformity,
or SAE J2834 conformity.

The preserved legacy decision remains
`honest_no_claim_under_frozen_preregistered_all_gate`. This amendment does not
authorize Fresh benefit, industrial or real-road safety, broad unseen-map
generalization, native-ranked Top1, promotion, deployment, online activation,
production readiness, or training/retraining.

## Accepted v2 evidence

- implementation HEAD:
  `e226c1add02ff45a18008e808957adc316353bf3`
- contract root:
  `663977da1d1fe5d594764478881729f10483d13453c22024329375954b9ba3bb`
- independent contract-review root:
  `8ed937f521beb0f2163366b6999c8238eef173cdab67df7e5922e0f301a5b5f7`
- capability-matrix root:
  `86ab14e231129da7ec72dd7d632dd05336e03772c4af83e3d8e2dbdaec3e3afe`
- independent capability-review root:
  `0c6f25de790a48fb71001e94be31f0f56c92eb2c5f86c31fedc727f0a0b921cd`
- authoritative zero-model focused root:
  `0bccb1326860e3c1f74c5012fc6e40160722817a308212c8ec10f75b5209e4ec`
  (`123/123`)

The superseded v1 roots and its `140/140` final-docs evidence remain preserved
and are not rewritten.
