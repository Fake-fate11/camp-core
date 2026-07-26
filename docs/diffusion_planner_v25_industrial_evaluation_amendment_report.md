# V25 Industrial-Oriented Evaluation-System Amendment

## Decision

This is an outcome-independent, additive scientific-contract amendment. It
defines a 56-endpoint vector and an evidence-capability matrix without reading
Fresh/B4 outcome values, rerunning an evaluation, or invoking a model, pool, or
selector.

The amendment does **not** authorize a claim. `SafetyCost` and its six legacy
components remain immutable historical values under the sole role
`immutable_legacy_exploratory_diagnostic_only`. They are not a primary
endpoint, weighted total, PASS criterion, training-support criterion, adaptation
criterion, or industrial certification metric.

High authority:
`720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5`.

Implementation HEAD: `5316bb8cc37a0bdc539923991a07709dfd45b2ed`.

## Contract scope

The registry contains 56 endpoints:

- Safety: 26
- Operations: 17
- Vehicle-body planar kinematic comfort proxy: 7
- Controlled-benchmark realtime: 6

Capability classification is structural, not outcome-bearing:

- `reconstructable_with_frozen_transform`: 42
- `evidence_missing`: 13
- `scientifically_inapplicable`: 1
- `directly_reconstructable`: 0 in this version because every retained primary
  endpoint needs at least a run-level aggregation or geometry transform

Every endpoint row contains the complete machine contract: source and SHA,
units, sample rate, coordinate frame, filter, window, edge handling, event
definition, opportunity denominator, per-run aggregation, cluster unit,
confidence interval, multiplicity, NI/guardrail state, missing and
full-denominator policies, evidence class, direction, formula, input shape,
applicability, finite rules, status enum, legacy alias, and industrial
interpretation.

Unknown, omitted, or duplicate endpoints fail closed.

## Safety domain

### Collision

The primary geometric event is full ego/actor OBB polygon intersection. The
vector separately records `collision_any`, false-to-true episode count, and
duration. Impact relative velocity, delta-v, and contact severity remain
`evidence_missing`; an any-event indicator is never substituted for severity.

### Dynamic critical exposure

The frozen transform covers:

- full-polygon minimum clearance;
- radial closing speed;
- continuous-SAT geometry TTC for approaching OBBs within the frozen 5 s
  descriptive horizon;
- DRAC only for positive closing and positive clearance;
- per-grid duration and episode counts.

Clearance, TTC, closing-speed, and DRAC grids are project-descriptive
sensitivity grids, never industrial PASS thresholds. THW is missing without an
unambiguous same-lane leader. PET is missing without a frozen conflict zone and
both passage times.

### Certified red crossing

A crossing requires the same-tick certified red phase, the route-specific exact
stop line, and swept full front-edge/footprint geometry. It is unthresholded:
a 0.4 m/s crossing remains a crossing. Unique encounter opportunities and
red-phase intervals are separate denominators and cannot be mixed.

### Road containment and direction

Containment uses the complete ego footprint against the external boundary of
the drivable polygon union. It reports maximum outside fraction, duration,
episodes, minimum signed clearance, and maximum penetration. Five-point
coverage remains legacy-only and cannot substitute for the polygon definition.

Wrong-way duration and episodes require onroad, moving state plus one
unambiguous lane/ordered-route direction. Topology or direction ambiguity is
typed missing.

## Operations domain

Speed compliance preserves same-tick speed-limit provenance and reports maximum
excess, mean positive excess, duration, and magnitude-duration on the
0/0.05/0.1/0.2 m/s project sensitivity grid. It is not legal or type-approval
certification.

Route progress is stateful. Transitions are restricted to the same or adjacent
forward/backward segment under the frozen kinematic bound; stateless
nearest-segment jumps are forbidden. Outputs include final ordered arc, maximum
and net forward progress, completion, goal distance/reached/passed,
backtracking duration/distance, and traveled distance.

Travel efficiency is
`max_forward_progress_m / distance_traveled_m`; a zero denominator is typed
missing. Traveled distance and legal forward progress remain separate.

False-stop endpoints are defined but currently `evidence_missing` because a
valid motion opportunity plus red-light, obstacle, and goal-wait exclusions are
not fully authoritative in the sealed evidence. Future instrumentation and
preregistration must freeze the speed threshold and minimum duration.

## Vehicle-body planar kinematic comfort proxy

The only allowed source is sealed `position_xy`, `ego_heading_rad`, and
`dt=0.1 s`.

The exact pipeline is:

1. 64 positions form 63 interval velocities.
2. Adjacent interval velocities form 62 world-frame accelerations.
3. Each acceleration is rotated by the aligned interior heading into
   longitudinal-forward and lateral-left vehicle-body axes.
4. Each axis uses an 11-point equal-weight centered FIR
   (`[1/11] * 11`), zero-phase offline, valid-only, with no padding or
   extrapolation.
5. The result is 52 filtered acceleration samples.
6. Filtered jerk is adjacent filtered acceleration difference divided by
   0.1 s, yielding 51 samples.

For each acceleration axis the per-run output includes signed mean, RMS,
peak absolute value, absolute p50/p90/p95/p99, and duration on the
0.5/1/2/3 m/s2 descriptive grid. The descriptive planar proxy
`(sum(|a_filtered|^4)*dt)^(1/4)` is named
`planar_kinematic_vdv_like`; it is not ISO VDV.

Filtered jerk reports RMS, peak, p95, and duration on the 0.5/1/2/5 m/s3
descriptive grid. It is a control-smoothness auxiliary, not occupant comfort.
Raw 0.1 s scalar-speed second differences, raw `speed*yaw_rate`, and a
single-tick speed-drop deceleration remain legacy diagnostics only.

Seat/suspension/human transfer, vertical acceleration, roll/pitch, and
frequency-weighted whole-body vibration are not modeled. Occupant/seat comfort
and ISO 2631 / SAE J2834 conformity are therefore `not_assessed`.

## Controlled-benchmark realtime

Future same-ego batch8 experiments must instrument pool generation, atoms,
context/weights, selector increment, and end-to-end latency separately. Each
stage reports per-run mean, median, p95, p99, and maximum.

Deadline sensitivity reports rate and maximum overrun for explicitly
hypothetical 50/100/200/500/1000 ms budgets. The 100 ms value is only a
`hypothetical_10Hz_budget`. Warm-up, concurrent load, deadline scheduler, and
production runtime evidence are missing; no production deadline or readiness
claim is authorized.

## Statistics and future decision topology

All endpoint values are summarized per run first. A future paired experiment
must preregister the scenario/corridor-intersection cluster as the independent
unit. Ticks, rows, arms, and seeds are never independent `n`.

Within-cluster aggregation precedes equal-cluster weighting. The default
prospective interval is a two-sided Student-t CI95 across cluster values.
Directional endpoints use paired better/tie/worse with exact zero delta as a
tie. Descriptive-unclassified endpoints do not receive an invented direction.

The result stays a vector. No weighted total is allowed. A future hard-safety,
guardrail/NI, and multiplicity topology must be preregistered. Where there is
no prospective external basis, the machine state is
`numeric_margin_not_authorized_until_future_preregistration`.

Every planned run, failure, missing opportunity, and retained denominator
member remains visible. Missing is never converted to zero, and complete-case
subsets cannot replace full paired inference.

## Evidence capability boundary

The capability matrix binds only sealed roots, schema fields, and transform
feasibility. It does not open or report B4 per-run values.

The following need new nonholdout instrumentation or semantic authority before
future use:

- collision contact dynamics/severity;
- unique leader semantics for THW;
- conflict zones and passage timing for PET;
- false-stop opportunity and exclusion context;
- target same-ego batch8 stage timings;
- occupant/seat/vertical/transfer evidence.

Old five-point, nearest-route, raw jerk, and latency aliases cannot be silently
promoted to satisfy these gaps.

## Independent review and adversarial closure

The separate-role reviewer does not import the producer registry, formula,
filter, classification, or decision oracle. It reconstructs 56 endpoint
identities, units, directions, formula literals, source roots, filter/sample
accounting, statistics, missing policy, legacy boundary, and official-reference
scope.

The local focused suite passed 30/30 before the implementation commit. It
rejects, even after payload rehashing:

- SafetyCost reweighting or promotion to primary;
- unit, dt, filter coefficient, window, or edge changes;
- raw controller chatter renamed as occupant jerk;
- missing-to-zero and complete-case substitutions;
- tick/row inflation of independent `n`;
- red encounter/phase denominator mixing;
- five-point coverage substituted for polygon containment;
- stateless nearest-route jumps;
- fabricated PET/THW source authority;
- ISO/SAE conformity claims;
- unknown, duplicate, or deleted endpoints;
- selector-training and final-evaluation recoupling.

## Standards and public rationale

The following official or primary pages are cited only for public scope and
terminology. No non-public normative text or conformity conclusion is copied:

- [ISO 2631-1:1997](https://www.iso.org/standard/7612.html), accessed
  2026-07-26.
- [SAE J2834_202504](https://saemobilus.sae.org/standards/j2834_202504-ride-index-structure-development-methodology),
  accessed 2026-07-26.
- [ISO 34502:2022](https://www.iso.org/standard/78951.html), accessed
  2026-07-26.
- [FHWA SSAM report FHWA-HRT-08-051](https://www.fhwa.dot.gov/publications/research/safety/08051/),
  accessed 2026-07-26.

## Final boundary

Current state:
`industrial_oriented_evaluation_system_amendment_independently_reviewed_scientific_contract_review_required`.

This package makes no Fresh benefit, industrial safety, regulatory, occupant
comfort, broad unseen-map, native-ranked Top1, production-readiness,
promotion, deployment, or online-activation claim. The preserved legacy result
remains `honest_no_claim_under_frozen_preregistered_all_gate`.

The next action belongs to control: decide whether the superseded
training-support work is still useful, whether adaptation/retraining evidence
is needed, or whether a future same-ego batch8 calibration should be
prospectively designed against this endpoint system.
