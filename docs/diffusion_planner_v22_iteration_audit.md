# Diffusion Planner V22 Iteration Audit

Last verified: 2026-07-14, Asia/Shanghai.

This file is the sole v22 gate authority. V21 is historical and read-only: its
failed frozen Gate E remains an honest no-claim diagnosis and must not be
rerun, rewritten, or renamed as success.

## Frozen Objective Boundary

- CAMP repository: `F:\camp_core-main`, branch `main`.
- Startup CAMP HEAD: `0a9b19b4f3993460a1a28d28e25211ac7087997b`.
- Fixed DP repository: `/root/autodl-tmp/Diffusion-Planner`.
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Native simulator: fixed TiER IV Diffusion Planner
  `scenario_generation` route replay.
- CAMP action: select exactly one member of the fixed K=8 candidate tensor.
  CAMP may not generate, repair, rewrite, blend, smooth, or postprocess a
  candidate trajectory.
- Candidate 0 must remain byte-identical to the independently computed DP
  operational default at every evidence gate. The native K=8 tensor has no
  native ranking provenance, so no broader native Top-1 claim is invented.
- Selector score remains `score_k(w)=a_k^T w` using approved affine atoms and
  nonnegative simplex weights; the master remains convex.
- No Full36 or formal seeds 11/12/13. No promotion, deployment, online
  activation, model replacement, real-road safety statement, or broad
  CAMP-over-DP claim is authorized.

## Frozen Route-Retention Contract

Route inventory, route selection, and route-family/corridor group split are
outcome-blind. Logical maps may be reused across splits. Train, calibration,
and holdout route identity, route family, and seed namespace must be frozen
before any CAMP or DP outcome is observed, with zero overlap. Routes with a
shared lanelet, overlapping corridor, or the same highly correlated topology
family stay in one split. The two already observed v21 routes may enter
train/calibration/diagnostic work only; they may not enter the v22 holdout.

Map ID, route ID, and split identity are forbidden from CAMP atoms, features,
online input, and DP input. The claim scope is limited to unseen
route-family/corridor and seed within the two fixed logical maps. No unseen-map
generalization claim is permitted. A third map is a future external-validation
extension and does not block the current protocol.

Every route selected by the preregistered outcome-blind rule must remain in the
evaluation denominator, per-route receipt set, and complete failure
accounting, regardless of difficulty or observed DP/CAMP behavior. A selected
route must not be deleted, replaced, redrawn, or skipped because of low
progress, high SafetyCost, lane overrun, overspeed, collision risk, all-K high
risk, or any other observed result.

When all K=8 candidates are source-valid and the simulator/tracker can run,
CAMP must use the same frozen affine/simplex score to select the relatively
lowest-risk candidate and continue closed loop. The tick and route are marked
`all-K-high-risk/stress`; selection must not fail closed or force candidate 0,
and it must not use fallback to fabricate feasibility.

Hard invalidity is limited to NaN/Inf, shape or time-grid error, missing real
causal source, incomplete candidate bytes/hash, or objective inability of the
simulator/tracker to execute. A hard-invalid route is still retained as an
`execution/source failure`, including failure stage and reason, and is never
replaced. Reports must separate route coverage, hard-invalid rate, and
paired-complete rate.

## Frozen Scientific Protocol

- Capability precedes scale. Pilot target: at least 30 routes by 3 non-formal
  seeds, 90 paired runs. Main target: at least 100 routes by 5 non-formal
  seeds, 500 paired runs. If native inventory is smaller, its true reachable
  ceiling is frozen before execution; routes are not repeated to fabricate
  sample size.
- Native causal train-route decision snapshots are sampled at a suggested
  0.5 s cadence. The preregistered learning curve is 5k/10k/20k/50k
  snapshots, limited honestly by available data.
- V22 train/calibration closed-loop outcomes may supply offline supervision or
  calibration labels only. Outcomes are never selector features, online
  inputs, or DP inputs. Holdout outcomes are opened once after model, atoms,
  scales, tolerance, and claim contract freeze.
- V18 frozen weights are an ablation baseline only. The v22 primary selector
  must be trained on the v22 train split with the existing convex solver;
  report solver iterations, gap, cuts, optimal status, and wall-clock rather
  than fictional epochs.
- Prefer the existing canonical 14D atoms. An atom enters only when the native
  simulator supplies a real causal source and affine/convex structure remains
  valid. Missing source fails closed; no synthetic source is allowed.
- Speed reporting includes raw strict overspeed, a frozen operational event
  at 0.1 m/s tolerance, and continuous magnitude-duration severity.
  Calibration sensitivity is 0/0.05/0.1/0.2 m/s; holdout may not choose the
  tolerance.
- Primary reporting includes paired SafetyCost and all critical components,
  overall/normal/stress/all-K-high-risk strata, paired better/tie/worse,
  mean/median delta, map/route/seed cluster-bootstrap CI95, complete receipts,
  latency, and failure accounting. Failed arms do not delete pairs.

The preregistered claim requires mean CAMP-minus-DP SafetyCost below zero,
cluster CI95 upper below zero, better greater than worse, no material
preregistered critical-component regression, complete holdout coverage and
failure accounting, plus passed independent review, SHA, candidate
immutability, and split zero-overlap checks. Otherwise the closeout is an
honest no-claim; thresholds may not change after results.

## Gate 0: Startup Reconciliation and Persistent Goal

Status: passed.

Read-only local and remote checks established:

- local repository and current branch: `F:\camp_core-main`, `main`;
- local HEAD, local `origin/main`, live GitHub `main`, AutoDL CAMP HEAD, and
  AutoDL `origin/main`:
  `0a9b19b4f3993460a1a28d28e25211ac7087997b`;
- local unrelated untracked files were left untouched;
- AutoDL CAMP and fixed DP tracked-file counts: `0 / 0`;
- fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- related v21/v22/scenario-generation active tasks: `0`.

AutoDL access used the current machine's Windows Credential Manager, Paramiko,
the existing known-host ed25519 key, and `RejectPolicy`; no password entered a
prompt, command, log, artifact, commit, audit, or response. Remote git/network
work sourced `/etc/network_turbo` first and used ff-only synchronization.

The v21 EOF was reread at its frozen user-decision stop. This v22 objective is
the explicit user-authorized independent continuation, not a retry or rewrite
of v21. Persistent goal thread
`019f6038-c1f7-7da2-91ee-2b55d8ffa95f` was created without a token budget.

The first evidence attempt was sealed at
`/root/autodl-tmp/camp_dp_v22_startup_reconciliation_cba43279_20260714T184935CST`
with root SHA256
`216335397acd25f09498a90ee1009acdf0aaf57f2fe8e0706a1b807a2c10cc4f`
and `run.exit=1`. The substantive live checks were healthy; the harness had
manually expanded the abbreviated commit to the wrong full SHA. No failed
evidence was overwritten or deleted.

The corrected immutable artifact is
`/root/autodl-tmp/camp_dp_v22_startup_reconciliation_rerun_cba43279_20260714T185046CST`
with root SHA256
`7dfda9dbae23156f31c55a404bf162fa1c951454a8be67f1b7faf579b0b976e6`.
It records `run.exit=0`, empty stderr, CAMP/DP heads, exact check command,
stdout, summary JSON/Markdown, `SHA256SUMS`, and `ROOT_SHA256SUMS`; all payload
and root checks passed before read-only sealing. It loaded no model, ran no
simulator, generated no candidate, opened no holdout, and made no claim.

The next gate is read-only contract/capability audit: trace and reuse the v21
native runner, atom materializer, convex solver, and route inventory; reject a
parallel framework; and identify the smallest shared hard-valid/soft-risk
boundary change. It may not load the model, execute the simulator, train,
open holdout, or make a claim.

## Gate 1: Contract, Capability, and Native Inventory Audit

Status: read-only audit passed; frozen split contract reached a hard stop.

The immutable artifact is
`/root/autodl-tmp/camp_dp_v22_contract_capability_audit_9ebed6e2_20260714T190011CST`
with root SHA256
`56b214e25ba4b275d3eb4aa7575302be9e627b3e7457d1118e96fa2779e13787`.
It has `run.exit=0`, empty stderr, matched CAMP/DP heads, exact command,
summary JSON/Markdown, `SHA256SUMS`, and `ROOT_SHA256SUMS`; both manifests
reverified independently before this record.

### Shared implementation path

The v21 native runner remains the single correct simulator path. No parallel
runner or DP-side change is needed. The minimum later implementation would:

- split true source validity from risk inside
  `diffusion_planner_causal_atoms.py`; today `lane_corridor` and predicted OBB
  collision are folded into `physical_feasible_mask`, and all-K false returns
  before the finite 14D atom matrix is produced;
- make the shared `select_camp_candidate` consume a v22 `source_valid_mask`
  while leaving v21's historical physical-mask behavior unchanged;
- retain lane overrun, collision/clearance, red exposure, speed excess,
  progress/stuck, and comfort as finite audited atoms/severities, including an
  `all-K-high-risk/stress` receipt instead of fallback;
- reuse `run_diffusion_planner_dp_camp_v21_native.py`, exact indexed candidate
  selection, candidate-0/default SHA proof, native MPC, and evidence sealing;
- reuse `robust_margin_master.py`, whose CLARABEL cutting-plane master already
  enforces finite nonnegative cost atoms and simplex weights while reporting
  iterations, gap, cuts, solver status, and solver name.

No implementation began because inventory exposed a prior frozen-contract
failure.

### Outcome-blind native inventory

AutoDL contains 7 existing route assets but only 2 logical maps. The six OSM
files are ROS/no-ROS or packaging variants of the same sample-map and
nishishinjuku families, not six independent maps. No third existing Lanelet2
map was found under `/root/autodl-tmp`, `/autodl-pub/data`, or other `/root`
paths.

Read-only Lanelet2 topology construction succeeded without model load or
simulation:

- nishishinjuku: 979 cached lanelets, 887 drivable lanelets, 282
  traffic-light lanelets, and 759 deterministic topology routes at least
  80 m;
- sample map: 190 cached lanelets, 184 drivable lanelets, 24 traffic-light
  lanelets, and 156 deterministic topology routes at least 80 m;
- deterministic route capacity: `759 / 156`, totaling 915 deterministic
  topology routes.

Thus route count is not the blocker: an outcome-blind route census can exceed
the 30-route pilot and 100-route main targets without repeating a route.
However, the frozen contract requires train, calibration, and holdout to have
map/route/seed group-level zero-overlap. Under the leakage-safe interpretation
that logical map identity itself cannot cross those three splits, strict
three-way map-identity zero-overlap is impossible with two maps.

Using ROS/no-ROS copies as separate maps would fabricate independence.
Partitioning one map into route regions would relax map-identity zero-overlap.
Downloading or licensing another map is outside current authorization. The
only honest next actions therefore require a user decision: provide/authorize
a third independent native Lanelet2 map, or explicitly change the scientific
contract to permit shared logical maps while keeping route identities and seed
namespaces split-disjoint. No design spec, implementation, corpus, training,
pilot, or holdout may proceed under the current contradiction.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made.

current_v22_status=v22_native_contract_capability_audit_hard_stop_two_logical_maps
current_v22_artifact_source_head=9ebed6e2c7da57088503eed717061b36a3b70b8e
current_v22_prior_gate_final_synced_head=9ebed6e2c7da57088503eed717061b36a3b70b8e
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_contract_capability_audit_9ebed6e2_20260714T190011CST
current_v22_artifact_root_sha256=56b214e25ba4b275d3eb4aa7575302be9e627b3e7457d1118e96fa2779e13787
next_work_target=user_decision_required_before_v22_map_zero_overlap_contract_change_or_new_map_assets

## Gate 1 Contract Resolution and Gate 2 Design

Status: the Gate 1 evidence remains passed and unchanged; its scientific hard
stop was explicitly resolved by the user, and the v22 design is ready for
static review.

The user authorized that logical maps may be reused across splits. The split
unit is now the outcome-blind route-family/corridor group. Route identity, route
family, and seed namespace remain strictly zero-overlap. A shared lanelet,
overlapping corridor, or highly correlated topology family is indivisible and
must remain in one split. The split is frozen before any CAMP or DP outcome.
All preregistered routes and hard-invalid failures remain in the denominator,
receipts, and failure accounting without replacement.

The restriction is explicit: map ID, route ID, and split identity are forbidden
from selector atoms, features, or online input. The eligible claim is only within the two fixed
logical maps on unseen route-family/corridor and seed. No unseen-map generalization claim
is authorized; a third map is a future
external-validation extension and is not a blocker for v22 training, pilot,
or main evaluation.

The design is frozen at
`docs/superpowers/specs/2026-07-14-v22-native-route-family-safety-design.md`.
It defines a source-only leakage graph, connected route-family/corridor groups,
whole-group allocation, pre-outcome validation, route retention, the
source-valid versus soft-risk boundary, all-K-high-risk selection, native
training, speed diagnostics, paired metrics, and fixed claim/no-go thresholds.
It reuses the v21 native runner and existing convex master; no DP change,
model load, simulation, corpus generation, training, or holdout opening
occurred in this documentation gate.

The next gate is read-only static review plus a minimal TDD implementation
plan. It may inspect code and write tests/plans but may not load the model,
execute the simulator, train, or open holdout.

current_v22_status=v22_native_route_family_split_design_ready_for_static_review
current_v22_artifact_source_head=pending_v22_design_source_commit
current_v22_prior_gate_final_synced_head=a94ad0a50640a86583e9dcc74b33bd68a00c1382
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=pending_v22_route_family_split_design_evidence
current_v22_artifact_root_sha256=pending_v22_route_family_split_design_evidence
next_work_target=v22_native_route_family_split_design_static_review_and_tdd_plan_only
