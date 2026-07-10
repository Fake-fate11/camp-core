# Diffusion Planner V17 Iteration Audit

Date: 2026-07-10, Asia/Shanghai.

This is the concise append-only ledger for v17. V14-v16 scripts, tests, and
audits are historical evidence. V16 may receive only an explicit correction or
qualification.

## Fixed Boundary

- Diffusion Planner is fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4` and remains tracked-clean.
- CAMP receives exactly the fixed DP `K=8` candidate tensors, computes atoms,
  evaluates `score_k(w)=a_k^T w`, and selects an existing candidate index.
- CAMP does not generate, repair, rewrite, blend, guide, postprocess, or mutate
  a trajectory.
- Approved atom weights stay on the nonnegative simplex and the master stays
  convex.
- Runtime inputs are limited to the fixed candidate tensor and information
  available at the current decision tick. GT future, holdout labels, and
  closed-loop outcomes are offline label/evaluation data only.
- Full36, formal seeds 11/12/13, DP changes, production promotion, deployment,
  and online activation remain forbidden.

## Phase 0 User Decision and Design

The v16 closeout requested a user decision among 32k expansion, a formal claim
pathway, and integration/runtime packaging. The user selected a fourth,
corrective v17 path: causal rematerialization, canonical `dp_camp_v10_14d`, an
independent paired evaluation, and only then default-off/shadow-only runtime
packaging.

Three implementation shapes were considered:

1. Extend the v16 gate-script chain. Rejected because it preserves circular
   labels/evaluation and adds more frozen historical machinery.
2. Create a new plan/static-review/execution/result-review runner for every v17
   gate. Rejected because it repeats orchestration rather than new computation.
3. Use one thin v17 orchestrator, existing CAMP atom/selector/master helpers,
   a small causal materializer seam, and a few targeted tests. Selected because
   it is the smallest design that provides a shared train/runtime computation
   path and independent evidence.

## Initial Authority Snapshot

- Local branch / HEAD / tracked status:
  `main / 4da4a15d20e448835f46f67a33b280532083a33e / clean`
- GitHub `origin/main` / remote ref:
  `4da4a15d20e448835f46f67a33b280532083a33e`
- AutoDL CAMP branch / HEAD / origin / tracked status:
  `main / 4da4a15d20e448835f46f67a33b280532083a33e / same / clean`
- AutoDL DP branch / HEAD / tracked status:
  `tier4-main / 7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`
- Filesystems: `/` has `12 GiB` available; `/root/autodl-tmp` has `7.6 GiB`
  available (`85%` used).
- Active processes: only platform Jupyter/TensorBoard services; no CAMP/DP
  candidate-generation, training, or evaluation job.
- Retained v16 corpus archive SHA256:
  `bed758757b881c47dce6559a8cbdc1988a6cbd425a1af96842b05a57cea89d39`
- Retained verification archive SHA256:
  `8a36218fb3bb2baaae47f7b87a2b423ca15416d25e2ee17510b9800a91beb0b9`

The deleted v16 corpus working tree is not a bootstrap dependency. V17 will not
restore or reuse it and must generate a new causal corpus.

## V16 Evidence Qualification

V16 paired evaluation computes the atom score, applies `argmin`, then reports
the selected score against candidate 0 under that same score. V16 proxy labels
are likewise the `argmin` of normalized atoms under proxy weights. The 3737-row
result therefore proves only selector self-score consistency. It is not an
independent CAMP-over-DP Top-1 result. The v16 EOF and current status record the
correction; historical artifacts and hashes are unchanged.

## Confirmed Causal Risks to Remediate

- `resolve_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.py:291`
  sets `goal_pose` from `ego_agent_future[-1]`.
- The same materializer exports neighbor future and uses `lanes[:25]` as the
  route at lines 293 and 296.
- Those 25 lanes are only distance-sorted nearby lanes/connectors, not a
  connected route. `_route_centerline()` then concatenates their polylines and
  may create artificial connecting segments.
- V16 atom derivation consumes `neighbor_agents_future` for dynamic clearance.
  The existing runtime path already has a causal alternative: candidate-specific
  DP-predicted neighbor trajectories are injected before atom scoring.
- The adapter writes unit tangent vectors into fields later interpreted as lane
  boundary offsets, so the derived half-width is effectively `1.0 m` rather
  than a measured lane width.
- Route speed-limit arrays are not populated, so the 9D bank falls back to a
  `100 m/s` limit and effectively disables the speed atoms. If limits were
  present, the v16 helper would still take the first valid limit instead of the
  candidate's projected route segment. Reuse the existing route-segment speed
  projection in `diffusion_planner_external_context_payload.py`.
- V16 derives desired speed from current speed. These are different semantics
  and the value must not be relabeled; it is currently dormant in the strict
  9D bank.
- Materialization drops the source `batch.dt`, atom derivation hardcodes
  `dt=0.1`, and validation checks shape/dtype/finiteness but not the declared
  80-step/8-second/frame/heading contract.
- `nuscenes_trajdata_bridge.py` also prefers GT future neighbor trajectories
  and GT future ego speed when those fields exist.
- V16 paired evaluation uses the same affine score for selection and outcome;
  proxy training labels use the same atom family.

No v17 materializer implementation is accepted until tests show that changing
GT ego future, GT neighbor future, or holdout-only fields leaves DP generation
inputs and runtime atoms unchanged.

The Phase 1 leakage suite must also cover: sentinel future fields that raise on
access; neighbor-history perturbation changing clearance; disconnected-lane
enumeration invariance; explicit-boundary rather than tangent-derived lane
width; candidate-to-route-segment speed limits; global SE(2) invariance;
heading wraparound at +/-pi; and `batch.dt` resampling without origin padding.

## Canonical 14D Target

The fixed order is:

1. `jerk_early`
2. `jerk_late`
3. `jerk_full`
4. `rms_acceleration`
5. `speed_limit_margin_0_0`
6. `speed_limit_margin_0_5`
7. `speed_limit_margin_1_0`
8. `lane_deviation`
9. `clearance`
10. `progress_shortfall`
11. `planned_red_light_cost`
12. `planned_lateral_acceleration_cost`
13. `red_stopping_margin_cost`
14. `dp_prior_jerk_excess_cost`

The repository already registers this exact order as `dp_camp_v10_14d` and
already has the affine selector and convex/simplex master. V17 will reuse those
paths. Each atom still requires a v17 provenance/units/formula/availability
record and targeted evidence before approval. NuScenes currently has no proven
decision-time traffic-light state in this bridge, so the two red-light atoms
are unavailable unless a real current-tick source is verified. They must not be
replaced by constant zero, and no full-14D nuScenes validation claim is allowed
while they are unavailable.

The current 14D assembly also has fail-open behavior that v17 must not inherit:
missing/nonfinite planned-red values and some final normalized atoms can become
zero, empty red-route points conflate "no red" with "signal unavailable", and
the general all-infeasible fallback can be uniform instead of DP Top-1. The
shared v17 assembler must require explicit availability, finite nonnegative
atoms, exact schema, and `fallback_mode=top1`. Default-off shadow routing stays
the runtime default.

## Scoped Read-Only Ponytail Audit

- `shrink:` freeze the existing 248 v14-v16 integration scripts and 249 tests;
  use one v17 orchestrator plus targeted computation tests. [`scripts/integrations`,
  `camp_core/tests`]
- `shrink:` do not copy the v16-local `_read_json` (59 copies), `_stable` (64),
  `_expect` (63), SHA writer (43), or `_sha256` (63); use existing module helpers
  or Python `json`, `hashlib`, and `pathlib`. [`scripts/integrations`]
- `yagni:` do not create plan/static-review/result-review runners when no new
  computation or independent validation occurs. [`scripts/integrations`]
- `shrink:` replace the duplicated pilot/scale-up NPZ-to-context-to-atoms
  materializers with one shared causal implementation; reuse the existing
  candidate-neighbor and route-speed projection paths. [`scripts/integrations`,
  `camp_core/camp_core/integrations`]
- `native:` store new numeric corpus arrays with `numpy.savez_compressed` after
  loader validation; keep shared context once and split with lightweight
  manifests. [future v17 orchestrator]
- `delete:` no historical cleanup is part of v17; unrelated files and retained
  evidence stay untouched.

net: about `-100` duplicate lines and `-0` dependencies are possible in the
v17 path; no historical deletion is applied in Phase 0.

## Independent Evaluation Boundary

- Primary: selected-trajectory ADE, lower is better.
- Secondary: FDE, miss rate, off-road/lane violation, offline
  collision/near-collision proxy, progress, jerk, acceleration, and lateral
  acceleration.
- Methods: fixed DP Top-1; frozen v16 legacy 9D historical baseline; corrected
  9D/10D/12D/13D/14D; external-metric best-of-K oracle for headroom only.
- Split: scene-level 60/20/20, zero overlap. Train only on train. Freeze
  configuration and criteria before opening holdout once.
- Statistics: paired bootstrap by scene cluster with a recorded non-formal seed
  that is not 11, 12, or 13. Predeclared v17 seeds are: split `3407`, training
  `3408`, deterministic tie handling `3409`, and scene-cluster bootstrap
  `3410`.
- Passing requires CAMP14-vs-Top1 ADE mean delta below zero with CI95 high below
  zero, preregistered FDE/collision/off-road non-regression, CAMP14 primary
  non-inferiority to corrected CAMP9 plus one 14D-sensitive improvement,
  selector latency p99 at most 1 ms, and complete paired SHA evidence.

Reuse the NaN-aware ADE/FDE and acceleration/jerk definitions in
`scripts/eval/unified_eval.py`, existing candidate geometry and outcome helpers
in `camp_core/camp_core/integrations/diffusion_planner.py`, the v16 scene
assignment/zero-overlap and SHA-manifest structure, and the existing selector
latency summary. Do not copy the pilot evaluator into a scale-up evaluator.
No scene-cluster bootstrap, production miss-rate, or drivable-area off-road
helper currently exists; those require one small v17 implementation each.
Lane-centerline violation must not be relabeled as off-road.

## Phase Ledger

### Phase 0A: Bootstrap, Erratum, and Read-Only Audit

Status: local documentation ready; checkpoint commit/push and AutoDL ff-only
sync still required.

Completed:

- local/GitHub/AutoDL/DP synchronization and tracked-clean checks;
- disk/process preflight and both archive SHA verifications;
- v16 self-score erratum and withdrawn performance wording;
- v17 scope, canonical order, independent metrics, stop conditions, and
  minimal implementation shape;
- scoped read-only Ponytail audit.

Not executed: corpus generation, training, holdout access, evaluation, runtime
packaging, DP modification, promotion, deployment, or online activation.

current_v17_status=v17_phase0_bootstrap_erratum_ponytail_audit_local_ready
current_v17_artifact_scope=docs_only_v17_bootstrap_and_v16_qualification
current_v17_artifact=docs/diffusion_planner_v17_iteration_audit.md
next_work_target=v17_phase0_commit_push_autodl_ff_only_sync_and_sha_verification_only

### Phase 0B: Checkpoint and Cross-Surface Verification

Status: passed.

- Checkpoint commit:
  `7d9d9df137247e3f9d3d1accef3c98a99b8a416b`
- Local HEAD / origin / GitHub ref / AutoDL HEAD / AutoDL origin:
  all equal to the checkpoint commit.
- Local and AutoDL CAMP tracked status: clean.
- AutoDL DP HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- AutoDL document SHA256:
  - current status:
    `8886403dd540d0bdf1d97849aa7950f1d733a1272034fc0bfeb85c4f3206640a`
  - v16 audit with erratum:
    `73c31a101387c5c77bc5599eeafe8ed8d9118d992f35a1ad4ade0b48f7843257`
  - v17 ledger:
    `04de5257ac6d54c903f67c98693dd61779f1210b99b8ea711f6ac7da6103e9de`
- AutoDL data-disk available space: `7.6 GiB`.
- Active v17 candidate-generation/training/evaluation jobs: none.
- Local verification: document contract checks `10/10`; `py_compile` exit `0`;
  targeted Benders atom-contract tests `4 passed`; staged diff check exit `0`.

No corpus, holdout, training, paired evaluation, runtime package, DP change,
promotion, deployment, or online activation occurred in Phase 0.

current_v17_status=v17_phase0_bootstrap_erratum_ponytail_audit_passed
current_v17_artifact_scope=phase0_docs_and_cross_surface_sync_evidence
current_v17_artifact=docs/diffusion_planner_v17_iteration_audit.md
next_work_target=v17_phase1_causal_materializer_contract_leakage_tests_and_minimal_implementation

### Phase 1A: Observable-Only Causal Materializer Boundary

Status: passed; candidate-to-route speed projection and the shared runtime atom
handoff remain the next gate.

- Implementation checkpoint:
  `754826cb2011d5c94688d6dd04ca56b4416db977`.
- Fixed-DP contract-test follow-up:
  `07bf33784ae168e72f0b0a7bab5376e5012610bc`.
- The materializer accepts only current-tick trajdata history plus an explicit
  world-frame map context whose route provenance is
  `current_map_topology_successors`. Its output schema contains only fields
  consumed by fixed-DP inference; ego future, neighbor future, and label fields
  are absent and sentinel properties raise if accessed.
- `goal_pose` comes from the final point and direction of the validated ordered
  route, not GT ego future. General-lane enumeration cannot replace or reorder
  the route.
- Source `batch.dt` is retained and histories are resampled by physical time to
  31 samples at `0.1 s`; heading interpolation unwraps across `+/-pi`; short
  neighbor histories use the fixed-DP all-zero missing-history mask rather than
  an apparent object trajectory at the ego origin.
- World-to-ego position and heading consistency, global SE(2) invariance,
  explicit left/right boundary sides, route endpoint/heading continuity,
  speed-limit slot alignment, categorical dtypes, traffic-channel binary
  validity, and explicit traffic/turn availability are fail-closed.
- nuScenes traffic-light state remains unavailable. The materializer preserves
  that fact in metadata; no red-light atom is synthesized or approved.
- AutoDL ran the target suite with `FIXED_DP_REPO` set, so the upstream
  `DiffusionPlannerData` loader and official `ObservationNormalizer` check did
  not skip: `18 passed`. Local target tests were `17 passed, 1 skipped`; eight
  directly related atom/route regressions passed; `py_compile` and diff checks
  passed.
- AutoDL file SHA256:
  - materializer:
    `dca0fc8ed5d2e1d60ed250228d5453e211823c0b8637d800d52c696a5b5be124`
  - target tests:
    `9cb1412ff0bff181235ddaeddf88ee7b0c4f93526226075905519c4782318ff8`
- Local HEAD, `origin/main`, GitHub ref, AutoDL HEAD, and AutoDL origin all
  equal `07bf33784ae168e72f0b0a7bab5376e5012610bc`; both CAMP tracked states are
  clean. AutoDL DP remains tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- `/root/autodl-tmp` has `10 GiB` available. No v17 candidate-generation,
  training, or paired-evaluation process is active.

Not yet executed or claimed: a nuScenes current-map topology route builder,
candidate-to-route-segment speed projection, shared canonical atom assembly,
fixed-model candidate generation from this boundary, corpus generation,
training, holdout access, paired evaluation, runtime packaging, DP change,
promotion, deployment, or online activation.

current_v17_status=v17_phase1a_observable_only_causal_materializer_boundary_passed
current_v17_artifact_scope=causal_materializer_and_fixed_dp_loader_normalizer_contract
current_v17_artifact=camp_core/camp_core/integrations/diffusion_planner_causal_materializer.py
next_work_target=v17_phase1b_phase2_candidate_route_speed_and_shared_canonical_atom_handoff

### Phase 2: Canonical Atom Provenance and Missing-Input Stop Review

Status: fail-closed no-claim stop. This is a true stop condition, not a failed
pilot and not an invitation to substitute constants.

The shared availability gate and canonical contract table were committed at
`7d90abdc3957d3855bea026e80c16ca6b7178c81`. It requires exact K=8,
explicit boolean source evidence, complete route-speed coverage, current
feasibility/static-obstacle/signal inputs, exact schema keys, and a finite
nonnegative `[8,D]` atom matrix. An unavailable atom raises instead of becoming
zero or inheriting the legacy `100 m/s` fallback.

#### Live nuScenes Source Audit

The full trainval source was inspected read-only before any corpus generation.
Across all four nuScenes expansion-map JSON files and every
`v1.0-trainval/*.json` metadata table, the number of files containing a JSON
key with `speed` or `limit` was `0`. The trajdata live batch exposed no vector
map or alternate speed-limit field. The four expansion-map SHA256 values are:

- Boston Seaport:
  `fc33712481efd763be39ce7edca0ec924d2d1fe20e1c89d52e21bf43d86e6b59`
- Singapore Holland Village:
  `0c9209c277686e367b06ab5bbe2547ba357f7f790365cb4927f44ae0f78266b2`
- Singapore One North:
  `17939122b940d7faff50fa7ff623ded7f739549a781c32dff1ecd1ac7bebca02`
- Singapore Queenstown:
  `c7e75f5a5643c4831aae1c99a0fdcc61e9ba3c01f98d922f0fafa34ea1062927`

The combined four-file SHA listing hashes to
`9906ad0698054e2fa7bcd55552a25ca16cd820410627faa6bbed1d4511c866c8`.

Traffic-light tables exist only as static map geometry. Their union of fields
is `from_road_block_token`, `items`, `line_token`, `pose`, `token`, and
`traffic_light_type`; there is no current phase/state or sample timestamp.
Record counts are 307, 119, 127, and 81 for the four maps respectively.
NuScenes also supplies no mission route; a topology-successor corridor would
be causal but is not an actual mission route and cannot repair the absent
segment speed rule.

The synthetic `[8, 12] m/s` values in the materializer unit fixture are contract
tests only. They are not nuScenes observations and are not eligible inputs.
Likewise, statutory defaults, a current-speed proxy, `100 m/s`, and zero-filled
availability are forbidden.

#### Canonical 14D Atom Ledger

| # | Atom | Inputs and formula | Unit | Decision-time / nuScenes status | Test evidence |
|---:|---|---|---|---|---|
| 1 | `jerk_early` | fixed-DP candidate xy; `dt*sum(||jerk||^2)` over first third | `m^2/s^5` | causal after candidate generation; no GT future | component benchmark + v17 contract |
| 2 | `jerk_late` | fixed-DP candidate xy; same cost after first third | `m^2/s^5` | causal after candidate generation; no GT future | component benchmark + v17 contract |
| 3 | `jerk_full` | fixed-DP candidate xy; same cost over full horizon | `m^2/s^5` | causal after candidate generation; no GT future | component benchmark + v17 contract |
| 4 | `rms_acceleration` | fixed-DP candidate xy; `sqrt(mean(||acc||^2))` | `m/s^2` | causal after candidate generation; no GT future | component benchmark + v17 contract |
| 5 | `speed_limit_margin_0_0` | candidate speed and projected actual route-segment limit; squared hinge | `m^2/s` | **unavailable:** no nuScenes speed-limit source | component benchmark + fail-closed gate |
| 6 | `speed_limit_margin_0_5` | same with `0.5 m/s` margin | `m^2/s` | **unavailable:** no nuScenes speed-limit source | component benchmark + fail-closed gate |
| 7 | `speed_limit_margin_1_0` | same with `1.0 m/s` margin | `m^2/s` | **unavailable:** no nuScenes speed-limit source | component benchmark + fail-closed gate |
| 8 | `lane_deviation` | candidate/ordered route/explicit boundaries; lateral hinge integral | `m^2*s` | conditional geometry exists; no mission route; not materialized | component benchmark + materializer geometry tests |
| 9 | `clearance` | candidate plus same-call fixed-DP neighbor predictions and current static obstacles | `m^2*s` | causal path exists but new neighbor export was not run | clearance hinge + materializer leakage tests |
| 10 | `progress_shortfall` | route progress vs feasible K-set reference | `m` | conditional on actual route and frozen feasibility; not materialized | selector progress test + v17 gate |
| 11 | `planned_red_light_cost` | `max(-planned_DP_red_reward,0)` with current route phase | dimensionless DP cost | **unavailable:** no current nuScenes signal phase | v8 selector assembly + fail-closed gate |
| 12 | `planned_lateral_acceleration_cost` | mean absolute candidate lateral acceleration | `m/s^2` | causal after candidate generation | lateral comfort tests + v17 contract |
| 13 | `red_stopping_margin_cost` | proximity-weighted comfortable-stopping speed excess | `m^2/s` | **unavailable:** no current nuScenes signal phase | red stopping formula tests + fail-closed gate |
| 14 | `dp_prior_jerk_excess_cost` | `max(mean_jerk_k-mean_jerk_candidate0,0)` | `m/s^3` | causal after candidate-0 Top-1 semantic verification | DP-prior comfort tests + v17 contract |

All atoms require finite nonnegative values and are independent of `w`, rank,
and the selected index. Atom 14 alone depends on candidate index 0 as the fixed
DP-prior reference. Progress depends on the candidate set and feasibility mask,
not on ranking. No atom permits GT future, holdout labels, or closed-loop
outcomes as runtime inputs.

#### Schema Decision

| Schema | Status | First blocking input |
|---|---|---|
| legacy 9D | unavailable | actual route-segment speed limits for atoms 5-7 |
| corrected 10D | unavailable | inherits 9D; actual route also unresolved |
| corrected 12D | unavailable | inherits prefix; current signal phase also absent |
| corrected 13D | unavailable | same; red stopping input absent |
| canonical `dp_camp_v10_14d` | unavailable | inherits all preceding missing inputs |

The user-authorized red-light exception would permit a 9D/10D causal subset if
real route speed limits existed. They do not, so no approved schema remains.
The unregistered candidate-only diagnostics (atoms 1-4, 12, and conditionally
14) may be described as diagnostics but must not carry a canonical schema name,
train weights/scales, or drive selection. No new partial schema is introduced.

#### Verification and Stop Boundary

- AutoDL target suite, including the real fixed-DP loader/normalizer contract:
  `24 passed`.
- Local target suite: `23 passed, 1 environment-gated skip`.
- Directly related formula/assembly regressions: `6 passed`.
- `py_compile` and diff checks: passed.
- AutoDL SHA256:
  - canonical contract/gate:
    `b26024162999f0824d9eae5e5be25d826ff592229e8c9ac432a8a69d3cbe0d30`
  - availability tests:
    `cfb442e0aa2d88de5ef6a9abd97572b6485bc85ab679701f79f5048e261d1783`
- Local/GitHub/AutoDL implementation HEAD:
  `7d90abdc3957d3855bea026e80c16ca6b7178c81`; CAMP and fixed DP tracked
  states were clean. Fixed DP remains
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- `/root/autodl-tmp` available space: `10 GiB`; no v17 job is active.

Because the minimum approved 9D prefix cannot be materialized, no projected
corpus-size calculation, candidate generation, 1024-record pilot, split,
training, calibration, holdout opening, independent paired evaluation, 10k
scale-up, evidence package, runtime selector integration, claim, promotion,
deployment, or activation was executed. There are therefore no method metrics,
paired confidence intervals, training times, selector latencies, or DP
generation timings to report. This preserves the one-shot holdout unopened.

The only accurate claim is: the v17 causal materializer boundary and fixed-DP
loader/normalizer compatibility passed, and the canonical atom availability
gate correctly blocks all approved nuScenes CAMP schemas because real
route-segment speed limits are absent (with current signal phase and mission
route also absent). No CAMP-over-DP performance or safety claim is allowed.

current_v17_status=v17_no_claim_stop_missing_causal_nuscenes_atom_inputs
current_v17_artifact_scope=canonical_14d_provenance_availability_and_fail_closed_stop_evidence
current_v17_artifact=camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py
next_work_target=stop_until_real_decision_time_route_speed_limit_signal_and_route_sources_are_provided

### User-Directed V17 Closeout

v17_nuscenes_path_superseded_by_user_decision_and_artifacts_deleted
