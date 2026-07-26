# V25 Industrial-Oriented Evaluation-System Amendment v3

## Decision

This outcome-independent amendment closes the final mathematical and
independent-review gaps identified in v2. It authorizes no model, pool,
selector, training, calibration, validation, closed-loop, Fresh, holdout,
legacy-evaluation, outcome-read, claim, promotion or deployment action.

The live evaluation contract remains a four-domain, unweighted endpoint
vector. The 56 domain/family parents expand to an exact 161-scalar-leaf
registry:

No weighted total is defined or authorized.

- 110 future noninferiority leaves;
- 9 descriptive-only leaves;
- 42 evidence-missing or scientifically-inapplicable leaves that are not
  testable.

SafetyCost and its weighted six-component construction retain the exact role
`immutable_legacy_exploratory_diagnostic_only`. They are not primary
endpoints, compensation terms, training-support gates, adaptation evidence,
industrial scores or claim evidence.

## Collision-onset kinematic proxy

`safety.collision_onset_relative_closing_speed_kinematic_proxy_mps` is now
strictly nonnegative. For the first full-OBB false-to-true intersection
interval `[t-1,t]`, interval velocities are reconstructed from consecutive
centroid positions and the frozen `dt`. The earliest continuous-SAT
translation entry fraction `tau` is computed with the previous-tick OBB
orientations. At that fraction:

`closing=max(0,-dot(r_tau,v_rel_tau)/max(norm(r_tau),1e-9))`.

Initial overlap, absence of a preceding interval, nonfinite inputs, lack of a
finite unique SAT entry, and coincident centroids are typed missing. A
separating relative motion returns zero rather than a negative signed value.
This is only a severity-related planar kinematic proxy. It is not delta-v,
impact severity or contact dynamics; the latter fields remain
`evidence_missing`.

## Executable statistical contract

Each scalar leaf now carries an exact `test_type`, direction-oriented cluster
delta, symbolic margin authority, hypotheses, p-value rule and familywise
decision rule.

For lower-is-better leaves,
`z_j=baseline_cluster_mean_j-method_cluster_mean_j`; for higher-is-better
leaves, `z_j=method_cluster_mean_j-baseline_cluster_mean_j`. Future
noninferiority uses:

- `H0: mu_z <= -M_leaf`;
- `H1: mu_z > -M_leaf`;
- `t=(mean(z)+M_leaf)/(sample_sd(z)/sqrt(n))`, `df=n-1`;
- one-sided `p=student_t.sf(t,df)`;
- for zero sample variance, `p=0` only when the null-bound numerator is
  strictly positive, otherwise `p=1`.

`n>=2`, finiteness and the full equal-cluster denominator are mandatory.
Numeric margins remain
`numeric_margin_not_authorized_until_future_preregistration`; therefore the
current claim gate remains false.

Within each exact test family, Holm-Bonferroni uses stable ascending
`(p_value,leaf_id)` order. At one-based rank `i`, rejection requires
`p<=0.05/(m-i+1)`. The first non-rejection stops the procedure. Any required
missing, nonfinite, failed or absent leaf blocks the complete family.
The machine method identifier is
`holm_bonferroni_step_down_within_exact_family`.

Hard-safety and guardrail layers are separate intersection-union all-pass
layers. No descriptive leaf can compensate. Ordinary one-sided or two-sided
95% Student-t intervals are explicitly descriptive: an ordinary 95% CI is
descriptive only and is never presented as familywise claim evidence. B/T/W,
where applicable, uses the oriented paired-unit delta and exact-zero ties.

## Independent review

The separate-role reviewer imports no v3 producer or decision oracle. It
reconstructs all 161 leaves from reviewer-local parent, threshold-grid,
summary-statistic and latency-budget literals, then compares exact formula,
units, direction, opportunity denominator, missing policy, role, family,
test type, hypotheses and source binding. The registry digest is only an
additional byte lock.

Adversarial tests alter a leaf formula, units, denominator or test type and
then synchronously repin both the producer payload digest and reviewer
registry digest. The local semantic oracle still rejects each mutation.
Additional tests cover approach/separation/initial overlap/zero norm,
Student-t zero-variance boundaries, Holm equality, equal-p ordering, stopping,
missing family members and capability-inventory drift.

## Sealed evidence and result boundary

The sealed-evidence matrix method accepted in v2 is unchanged and
deterministically resealed against the v3 leaf contract:

- 119 leaves are reconstructable with a frozen transform;
- 41 are evidence missing;
- 1 is scientifically inapplicable.

No outcome value was read. The old B4/Evaluation, continuation ledger,
superseded v1 roots, superseded v2 roots and all old artifacts/CAS remain
unchanged. The
historical scientific result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.

The planar vehicle-body kinematic proxy remains distinct from occupant/seat
comfort and cannot establish ISO 2631 or SAE J2834 conformity. No Fresh
benefit, real-road safety, broad unseen-map, native-ranked Top1, production
readiness, promotion, deployment or online-activation statement is
authorized.
