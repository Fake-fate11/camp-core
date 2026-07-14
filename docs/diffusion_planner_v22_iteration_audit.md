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

The first AutoDL evidence attempt was sealed at
`/root/autodl-tmp/camp_dp_v22_route_family_split_design_7ee8a2cf_20260714T192722CST`
with root SHA256
`385774d8cc815405c8189f628afe0c44496a675208105f9f0dfb75519438be73`
and `run.exit=1`. AutoDL fast-forwarded correctly, but the harness compared
the live commit against another manually guessed full SHA. The failed artifact
is retained and its payload and root manifests reverify.

The corrected immutable design artifact is
`/root/autodl-tmp/camp_dp_v22_route_family_split_design_rerun_7ee8a2cf_20260714T192814CST`
with root SHA256
`071fe5939d34800bf517c16ff6c0c4a878e12714b15c522c31b46a49b0adec91`.
It records `run.exit=0`, matched full CAMP HEAD/origin, the fixed DP HEAD,
tracked-clean repositories, exact command, stdout/stderr, summary JSON/MD,
`SHA256SUMS`, and `ROOT_SHA256SUMS`. Local and AutoDL v21/v22 contract tests
passed `19 / 19`; py_compile and diff checks passed.

current_v22_status=v22_native_route_family_split_design_ready_for_static_review
current_v22_artifact_source_head=7ee8a2cfe8d49d42e222535b203b90bd559e1332
current_v22_prior_gate_final_synced_head=7ee8a2cfe8d49d42e222535b203b90bd559e1332
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_route_family_split_design_rerun_7ee8a2cf_20260714T192814CST
current_v22_artifact_root_sha256=071fe5939d34800bf517c16ff6c0c4a878e12714b15c522c31b46a49b0adec91
next_work_target=v22_native_route_family_split_design_static_review_and_tdd_plan_only

## Gate 3: Static Review and TDD Implementation Plan

Status: passed.

Static review confirmed that the minimum production change is confined to the
shared causal materializer, shared affine selector, and existing v21 native
hook with an explicit v22 policy whose default preserves v21 behavior. The
existing convex `robust_margin_master.py` already enforces nonnegative simplex
weights and reports iterations, master gap, cuts, convergence, solver status,
and solver name. No new solver and no parallel native runner are needed.

The executable eight-task RED/GREEN plan is
`docs/superpowers/plans/2026-07-14-v22-native-route-family-safety-tdd.md`.
It covers source-valid versus soft-risk materialization, affine selection and
all-K-high-risk receipts, speed metrics and retained failures, pre-outcome
route-family split freeze, 0.5 s native corpus sampling, 5k/10k/20k/50k convex
learning curves, calibration freeze, capability/pilot, one-shot main holdout,
cluster statistics, independent review, and honest claim/no-claim closeout.

The immutable static-review artifact is
`/root/autodl-tmp/camp_dp_v22_route_family_split_plan_static_review_30885f0f_20260714T193535CST`
with root SHA256
`3ad0b18f187c46508464df2e8151001b83af7d61f59f4f4bd7e6c0c77675ea3a`.
It records `run.exit=0`, matched CAMP HEAD/origin, fixed DP HEAD, tracked-clean
repositories, exact command, stdout/stderr, summary JSON/MD, `SHA256SUMS`, and
`ROOT_SHA256SUMS`. Local and AutoDL v21/v22 audit/design/plan contract tests
passed `25 / 25`; py_compile, placeholder scan, shared-runner guards, and diff
checks passed.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made. The next gate
is Task 1 TDD only: add a v22 source-valid materialization policy while keeping
the v21 physical-eligibility default byte-for-byte behaviorally compatible.

current_v22_status=v22_native_route_family_split_plan_static_review_passed
current_v22_artifact_source_head=30885f0f1a9b02215ee7fd5c7d9998f4ee49b922
current_v22_prior_gate_final_synced_head=30885f0f1a9b02215ee7fd5c7d9998f4ee49b922
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_route_family_split_plan_static_review_30885f0f_20260714T193535CST
current_v22_artifact_root_sha256=3ad0b18f187c46508464df2e8151001b83af7d61f59f4f4bd7e6c0c77675ea3a
next_work_target=v22_task1_source_valid_materialization_tdd_only

## Task 1: Source-valid Materialization

Status: passed.

TDD added an opt-in `v22_source_valid` eligibility policy to the existing
`materialize_canonical_14d` path. The default remains `v21_physical`, so v18,
v19, and v21 callers preserve the historical all-K physical fail-closed
behavior. Under the v22 policy, hard source validity is the conjunction of
real signal-source availability and exact route-speed source availability;
lane corridor and predicted OBB collision remain in the diagnostic physical
risk mask.

When all K=8 candidates are source-valid but the physical risk mask is all
false, the materializer now emits a finite canonical 8x14 atom matrix,
`source_valid_mask`, and `all_k_high_risk=true`. Progress shortfall is
referenced to the source-valid candidates rather than the old physical mask.
No selector behavior changed in this task, so v22 execution still waits for
Task 2 before using the new mask.

The first AutoDL attempt was sealed at
`/root/autodl-tmp/camp_dp_v22_task1_source_valid_materialization_1009b3da_20260714T194217CST`
with root SHA256
`c0df271623167428e2291a24a264460305ad36b52cdd097bb0a8cf5576ce69f3`
and `run.exit=2`. HEAD checks and fast-forward succeeded, but pytest collection
did not receive the repository `camp_core/` package on `PYTHONPATH`; no test
assertion ran. Its premature positive summary fields are not pass evidence;
the exit code, stdout, and audit attribution are authoritative. The failed
artifact remains preserved and its manifests verify.

The corrected immutable artifact is
`/root/autodl-tmp/camp_dp_v22_task1_source_valid_materialization_rerun_1009b3da_20260714T194325CST`
with root SHA256
`5d4feb0d91058ed71de20378f05040399e7874af73d5ff549baabf310a899215`.
It records `run.exit=0`, empty stderr, matched CAMP HEAD/origin, fixed DP HEAD,
tracked-clean repositories, no related running job, exact command,
stdout/stderr, summary JSON/MD, `SHA256SUMS`, and `ROOT_SHA256SUMS`. AutoDL ran
the complete relevant v18/v19/v21 plus v22-pointer set: `66 / 66` passed.

Locally, the non-torch shared suites passed `28 / 28` and materializer tests
passed `6 / 6`. A full local v18 run is unavailable because the existing
Anaconda runtime aborts on a standalone `import torch` with duplicate
`libiomp5md.dll`; the unsafe duplicate-runtime workaround was not used. AutoDL
provided the complete fixed-runtime verification instead.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made. Next is Task 2
TDD: make the shared affine selector and existing native hook opt into
`source_valid_mask`, retain both risk masks, and record all-K-high-risk without
fallback or forced candidate 0.

current_v22_status=v22_task1_source_valid_materialization_passed
current_v22_artifact_source_head=1009b3da15ee25a8325e25169d0374e54da4bb70
current_v22_prior_gate_final_synced_head=1009b3da15ee25a8325e25169d0374e54da4bb70
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_task1_source_valid_materialization_rerun_1009b3da_20260714T194325CST
current_v22_artifact_root_sha256=5d4feb0d91058ed71de20378f05040399e7874af73d5ff549baabf310a899215
next_work_target=v22_task2_affine_source_valid_selection_and_all_k_high_risk_receipts_tdd_only

## Task 2: Source-valid Affine Selection and All-K-high-risk Receipts

Status: passed.

The shared v19 selector now accepts an explicit eligibility mask name. Its
default remains `physical_feasible_mask`; v22 may opt into
`source_valid_mask`. Scores, positive scales, and nonnegative simplex weights
are unchanged. The selector computes the same affine scores for all K and masks
only hard source-invalid rows. It returns both masks, the eligibility policy,
and `all_k_high_risk`; it has no fallback and does not force candidate 0.

The existing v21 native hook now accepts an explicit selection policy whose
default preserves v21. Under `v22_source_valid`, it passes the matching policy
to the shared materializer and selector, then records the policy, both masks,
source-complete mask, all-K-high-risk flag, scores, selected index/SHA, and
candidate tensor before/after SHA. Exact indexed selection and candidate
immutability remain mandatory. No parallel native runner was added.

The immutable artifact is
`/root/autodl-tmp/camp_dp_v22_task2_source_valid_selector_receipts_f83f76c6_20260714T195440CST`
with root SHA256
`9eaf7ca17c5946e144c8bc59e017e971dbda37f7f9eb379663d7656b3eabc88e`.
It records `run.exit=0`, empty stderr, matched CAMP HEAD/origin, fixed DP HEAD,
tracked-clean repositories, no related running job, exact command,
stdout/stderr, summary JSON/MD, `SHA256SUMS`, and `ROOT_SHA256SUMS`. The
complete relevant AutoDL v18/v19/v21 plus v22-pointer set passed `68 / 68`.
Local selector/hook/runner tests passed `30 / 30`, materializer regression
passed `6 / 6`, and py_compile/diff checks passed.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made. Next is Task 3
TDD: implement raw strict speed events, frozen 0.1 m/s operational events,
continuous excess severity, 0/0.05/0.1/0.2 sensitivity, and denominator-retained
source/execution failure rows.

current_v22_status=v22_task2_source_valid_selector_receipts_passed
current_v22_artifact_source_head=f83f76c62e6e9670396d1e822de92f3f458758f1
current_v22_prior_gate_final_synced_head=f83f76c62e6e9670396d1e822de92f3f458758f1
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_task2_source_valid_selector_receipts_f83f76c6_20260714T195440CST
current_v22_artifact_root_sha256=9eaf7ca17c5946e144c8bc59e017e971dbda37f7f9eb379663d7656b3eabc88e
next_work_target=v22_task3_speed_protocol_and_retained_failure_rows_tdd_only

## Task 3: Speed Protocol and Retained Failure Rows

Status: passed.

The new focused v22 native metric module preserves all v21 collision,
near-miss, drivable-area, wrong-way, and red-light definitions. It reports raw
strict speed events using the existing `1e-6 m/s` comparison epsilon, freezes
the primary operational tolerance at `0.1 m/s`, reports calibration
sensitivity at `0/0.05/0.1/0.2 m/s`, and records maximum/mean excess,
positive-excess duration, and excess magnitude-duration.

`SafetyCost Native v22` retains the v21 formula and replaces only its speed
component with the 0.1 m/s operational event rate. The strict count/ticks and
full sensitivity remain present and are never hidden. The existing native arm
receipt builder now dispatches explicitly between `safety_cost_native_v1` and
`safety_cost_native_v22`; the v21 config remains on v1.

The retained-pair row helper accepts complete, source-invalid, and execution-
failed arms. Every row sets `included_in_denominator=true`, keeps both arm
statuses, failure stage/reason, hard-invalid/execution flags, and
all-K-high-risk stratum. It has no deletion, replacement, redraw, or retry
path.

The immutable artifact is
`/root/autodl-tmp/camp_dp_v22_task3_speed_retained_failures_d9eab84e_20260714T200250CST`
with root SHA256
`c568c2b589621b4de05fb10c5b3f75daf939dcdcd3bf2081dfd948b427e57478`.
It records `run.exit=0`, empty stderr, matched CAMP HEAD/origin, fixed DP HEAD,
tracked-clean repositories, no related running job, exact command,
stdout/stderr, summary JSON/MD, `SHA256SUMS`, and `ROOT_SHA256SUMS`. The
complete relevant AutoDL suite passed `88 / 88`; local v22/v21 metric,
runner, and hook tests passed `38 / 38`, with py_compile and diff checks passed.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made. The next gate
is a static native capability preflight for the single-tick and tiny
multi-route regression. It must verify exact v22 policy wiring, hashes,
candidate immutability receipts, source-only route use, fixed seeds, and the
absence of a related running task before model load.

current_v22_status=v22_task3_speed_retained_failures_passed
current_v22_artifact_source_head=d9eab84eb301935fa99a4f7b26e3259fa4cd8ccd
current_v22_prior_gate_final_synced_head=d9eab84eb301935fa99a4f7b26e3259fa4cd8ccd
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_task3_speed_retained_failures_d9eab84e_20260714T200250CST
current_v22_artifact_root_sha256=c568c2b589621b4de05fb10c5b3f75daf939dcdcd3bf2081dfd948b427e57478
next_work_target=v22_native_single_tick_and_tiny_multi_route_capability_preflight_only

## Native Capability Static Preflight

Status: passed.

The existing v21 native runner now validates a narrowly scoped v22 capability
configuration by normalizing only its v22 policy metadata back to the frozen
v21 base contract. The v21 config and default physical-eligibility policy are
unchanged. The v22 config opts into `v22_source_valid`, identifies the frozen
v18 weights as `v18_ablation_capability_only`, fixes the tiny regression at
four ticks, and labels both already-observed v21 routes as
`diagnostic_v21_observed_not_holdout`. Claim, training, holdout access, and
formal seeds remain unauthorized.

The immutable AutoDL artifact is
`/root/autodl-tmp/camp_dp_v22_native_capability_preflight_f964c0f5_20260714T201537CST`
with root SHA256
`4dc22b6c193867a15c672a5710af7516d05111ca55a901518b2a1983b5dedd98`.
It records `run.exit=0`, empty stderr, matched CAMP HEAD/origin, fixed DP HEAD,
tracked-clean CAMP and DP repositories, exact command, verified config/assets,
stdout/stderr, summary JSON/MD, `SHA256SUMS`, and `ROOT_SHA256SUMS`. AutoDL
py_compile and capability/v21-runner/v21-hook/v22-pointer tests passed `28 / 28`.
The preflight result contains zero routes, zero arms, and no receipts.

No model was loaded, no simulator was executed, no candidate was generated,
no training ran, no holdout was opened, and no claim was made. The next gate
is the one-tick CAMP capability execution on the diagnostic normal route. It
must prove the live v22 source-valid policy, exact K=8 candidate and candidate-0
identity evidence, selected-candidate immutability, and native causal-history
receipt before any tiny multi-route execution.

current_v22_status=v22_native_capability_preflight_passed
current_v22_artifact_source_head=f964c0f5fef3937cad46e4be09564f2bc0d7da04
current_v22_prior_gate_final_synced_head=f964c0f5fef3937cad46e4be09564f2bc0d7da04
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_native_capability_preflight_f964c0f5_20260714T201537CST
current_v22_artifact_root_sha256=4dc22b6c193867a15c672a5710af7516d05111ca55a901518b2a1983b5dedd98
next_work_target=v22_native_single_tick_capability_execution_only

## Native Single-tick Capability Execution

Status: passed.

Two pre-execution harness failures occurred before the successful run. The
first used an incorrectly hand-expanded full CAMP SHA in the HEAD guard. It is
sealed at
`/root/autodl-tmp/camp_dp_v22_native_single_tick_capability_harness_head_guard_480b6fda_20260714T202203CST`
with root SHA256
`81e57eebae00443dc83a2f891aad8e600339979359c071c6d711c585f4ad0cb1`.
The second used a broad `pgrep` expression that matched its own bash wrapper,
not a Python runner. It is sealed at
`/root/autodl-tmp/camp_dp_v22_native_single_tick_capability_harness_process_guard_480b6fda_20260714T202255CST`
with root SHA256
`00a3c9cf6e702482c56e3934c47bf25f25a1af20b7a98c05b1395aeb0039a2a3`.
Both record `run.exit=1`, the failure stage and cause, and
`model_loaded=false` / `simulator_executed=false`. The corrected process guard
inspected independent `/proc/*/cmdline` argv entries and found no active native
runner.

The one-tick diagnostic capability execution then passed on the already
observed normal v21 route. The immutable artifact is
`/root/autodl-tmp/camp_dp_v22_native_single_tick_capability_480b6fda_20260714T202326CST`
with root SHA256
`0c65c4a2af758dba7d9658f1fda95cac152271b43afeb6e7024d2818658efe80`.
Independent `SHA256SUMS` and `ROOT_SHA256SUMS` checks passed. It records
`run.exit=0`, CAMP/fixed-DP HEADS, exact command, stdout/stderr, summary JSON/MD,
one route, one CAMP arm, and one complete tick receipt. AutoDL py_compile and
capability/v21-runner/v21-hook/v22-pointer tests passed `30 / 30` immediately
before execution.

The native tick used 31 observed causal frames and zero padding. All eight
candidates were source-valid and physically feasible; `all_k_high_risk=false`.
The frozen affine selector chose candidate 7 under `v22_source_valid`. The K=8
candidate tensor SHA was identical before and after selection. The independent
DP operational default and candidate 0 were elementwise and byte-hash equal
with max absolute difference `0.0`; both SHA256 values are
`823b2e604297bf2229e8079999e5d57c0a74949bfdeb0ec91fd41a841de72913`.
The receipt explicitly keeps `native_ranked_k8=false` and makes no native
K-ranking provenance claim.

This was diagnostic capability only: the v18 weights remain ablation-only,
no training ran, no holdout was opened, and no safety or CAMP-over-DP claim was
made. Next is TDD for the four-tick, two-route diagnostic capability mode on
the same shared runner; it must not run 64-step v21 paired smoke or access any
v22 evaluation split.

current_v22_status=v22_native_single_tick_capability_passed
current_v22_artifact_source_head=480b6fda746db9e8b75d598fc9bbd56991b59721
current_v22_prior_gate_final_synced_head=480b6fda746db9e8b75d598fc9bbd56991b59721
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_native_single_tick_capability_480b6fda_20260714T202326CST
current_v22_artifact_root_sha256=0c65c4a2af758dba7d9658f1fda95cac152271b43afeb6e7024d2818658efe80
next_work_target=v22_native_tiny_multi_route_capability_tdd_only

## Native Tiny Multi-route Capability

Status: passed.

TDD added a `tiny-capability-smoke` mode to the same native runner. It is
restricted to the v22 diagnostic config and runs exactly the two already
observed v21 routes, CAMP-only, for four ticks each. The v21 one-tick and
64-step paired modes remain unchanged. The v22 validator requires the frozen
0.1 m/s operational speed protocol, K=8 source-valid masks, candidate
immutability/default identity, and the explicit affine score receipt.

The first tiny execution completed successfully at source HEAD `bf26d566` and
is preserved at
`/root/autodl-tmp/camp_dp_v22_native_tiny_multi_route_capability_bf26d566_20260714T203658CST`
with root SHA256
`25be90dc1983c37d98380393f32f332b8e5a7c3eee6c4536bdab8a6054fc4c31`.
Review found that its public tick receipts omitted the already-computed affine
score vector, so the artifact could not independently prove that a selected
candidate 0 in an all-K-high-risk tick was a real score argmin rather than a
fallback. The execution was not renamed as gate success. TDD then made the
public receipt retain `score_k(w)=a_k^T w`, the eligibility mask name, and all
eight finite scores; the validator independently recomputes the masked argmin.

The corrected immutable artifact is
`/root/autodl-tmp/camp_dp_v22_native_tiny_multi_route_capability_score_receipts_ea741985_20260714T204030CST`
with root SHA256
`56f9e35bbf12140d365acfc74f2de6f13a4cf71fda582d9d976175ceff1be42c`.
Independent `SHA256SUMS` and `ROOT_SHA256SUMS` checks passed. It records
`run.exit=0`, matched CAMP/fixed-DP HEADS, exact command, stdout/stderr,
summary JSON/MD, two routes, two CAMP arms, eight complete tick receipts, and
zero failures. AutoDL py_compile and capability/v21-runner/v21-hook/v22-metric/
v22-pointer tests passed `38 / 38` immediately before execution.

Every tick used 31 observed causal frames and zero padding. Candidate tensors
were immutable and the independent DP operational default was byte-identical
to candidate 0 on all eight ticks. On the normal diagnostic route, all eight
candidates were source-valid and physically feasible at every tick; selected
indices were `7, 7, 6, 7`. On the traffic-light/corridor diagnostic route, all
eight candidates remained source-valid; physical-feasible counts were
`7, 0, 0, 0`. The last three ticks were therefore the preregistered
all-K-high-risk/stress condition. CAMP continued the closed loop and selected
`2, 2, 0`; each selection exactly equaled the persisted source-valid masked
affine argmin. The final candidate-0 selection had the minimum score
`0.8657153899128988`; it was not forced and no fallback ran.

Both four-tick diagnostic arms had SafetyCost `0.0`; every collision,
near-miss, offroad, wrong-way, red-light, strict-speed, and 0.1 m/s operational
speed event count was zero, with maximum speed excess `0.0 m/s`. Route
completion was `0.017858330066413797` and `0.005420877832714185`. Mean latency
in milliseconds for normal/stress respectively was: DP default inference
`147.9857 / 54.0229`, K8 candidate inference `374.5511 / 375.2012`, atom
materialization `24.3869 / 32.7212`, selector `0.1266 / 0.1223`, tracker
`8.1096 / 8.5967`, and total planning `605.8580 / 497.1656`.

These are capability diagnostics, not paired DP/CAMP outcomes. The v18 weights
remain ablation-only; no native training corpus was generated, no evaluation
split or holdout was opened, and no safety or CAMP-over-DP claim was made. The
next gate is the outcome-blind route-family/corridor census and pre-outcome
train/calibration/holdout split freeze. It must retain every preregistered
route and failure and must not use any capability outcome as a split input.

## Outcome-blind Route-family Census and Split Freeze

Status: passed with a frozen four-route training ceiling.

Task 4 TDD added only a source-side route census, leakage graph, group
allocator, split validator, and frozen asset writer. It reused the fixed DP
Lanelet scene builder without loading the model or executing the simulator.
The source inventory contains 915 source routes: 759 on the nish map and 156
on the sample map. Route identity, shared lanelet/boundary, overlapping
corridor, and topology-family edges produced 7,917 leakage edges and three
indivisible connected groups sized `759 / 152 / 4`. All 915 source identities
remain explicitly accounted; the 781 routes above the preregistered targets
are frozen as source-only `frozen_capacity_above_target` exclusions before any
outcome, not silently deleted, replaced, or redrawn.

The first execution at source HEAD `27f73889` used a greedy split allocator.
It wrote a complete `run.exit=0` artifact at
`/root/autodl-tmp/camp_dp_v22_route_family_split_freeze_27f73889_20260714T205535CST`
with root SHA256
`9391d2f58335faac5874f2467f057af5ff4a1e45982b6e72f967a9cb6a9ae1d1`,
but allocated `152 / 4 / 100` routes to train/calibration/holdout and therefore
reported a no-go. Review identified this as allocator policy, not a native
inventory ceiling: its train-first greedy choice had consumed the only group
large enough for the frozen 30-route pilot. This artifact remains immutable
and is not renamed as the gate pass.

TDD at source HEAD `b36f98ae0c0efb2b55fcbe442172a0e6b52389fe`
replaced the three-group greedy decision with an exhaustive deterministic
global assignment that first satisfies the hard pilot/main targets, then
maximizes reachable training support. The corrected immutable artifact is
`/root/autodl-tmp/camp_dp_v22_route_family_split_freeze_global_eval_first_b36f98ae_20260714T210012CST`
with root SHA256
`b231ba9fe425e40a129e30ce0b37044f1059354f84744d91911608f09f87baa5`.
Its split freeze SHA256 is
`00394a1ad67f6d760f8c12f28532c6f661663fe7709a233adb79dc3b05904bc8`.
The train/calibration/holdout route counts are 4 / 30 / 100 and their disjoint
seed namespaces produce 32 / 90 / 500 expected paired runs. The 134 selected
route assets, every source identity, source hash, grouping edge, assignment,
and outcome-blind exclusion are persisted. Formal seeds `11/12/13` and Full36
are absent.

The independent exhaustive review artifact is
`/root/autodl-tmp/camp_dp_v22_route_family_split_freeze_independent_review_b36f98ae_20260714T210148CST`
with root SHA256
`2ba80e30c40f92dac61bfe0996fd66f94e544c9a454429cb379bfe59afd7e7b6`
and `run.exit=0`. It independently rehashed the source artifact and all 134
selected route assets, enumerated every assignment of the three groups, found
four assignments that satisfy the 30-route pilot and 100-route main minimums,
and proved that the maximum reachable train count is exactly 4. This true
training ceiling is frozen for corpus generation; 5k/10k/20k/50k learning
curve tiers may therefore be unreachable and must be reported honestly rather
than filled with correlated or repeated routes.

No model was loaded and no simulator executed. No CAMP or DP outcome was read.
The holdout remains sealed. The holdout map is absent from train as a
consequence of the source-only connected groups. Therefore unseen-map
generalization remains unauthorized even though the contract permits logical
map reuse; any eventual claim wording is restricted to the fixed two-map
inventory and unseen route-family/corridor plus seed. `claim_authorized=false`.
Next is a static train-corpus preflight using only the four frozen train routes
and eight train seeds; it must not execute calibration or holdout routes.

## Native Train Corpus Static Preflight

Status: passed with a preregistered sub-5k ceiling.

The train-only static preflight at source HEAD
`74005ca49849d4601c11c1eed23038582f1062a7` added a frozen corpus contract and
a preflight mode to the planned corpus CLI. The CLI imports
`build_native_arm_runner` from the existing v21 native script and contains no
copied replay loop. The feature payload is limited to `atom_matrix`,
`source_valid_mask`, and `candidate_row_sha256`; logical-map, route, group,
split, and seed identities remain receipt-only. The collection behavior policy
is explicitly `v18_ablation_corpus_collection_only`; it is not the v22 primary
model and no identity or outcome enters selector features.

The validated freeze has 4 / 30 / 100 route counts and 8 / 3 / 5 seed counts
for train/calibration/holdout. This gate authorizes only the 32 train route-seed
runs. A complete run has 64 native 0.1 s ticks and samples ticks divisible by
five, giving 13 snapshots per complete 64-tick run. The theoretical ceiling is
416 snapshots. Therefore no 5k/10k/20k/50k level is reachable under the frozen
split. Corpus generation must retain all actual failures and train on all
available valid snapshots without repeating routes or pretending that any
preregistered tier was reached.

The first remote controller attempt performed the ff-only sync, then its
process guard matched the controller's own future command text and exited 45.
It created no artifact, ran no test, loaded no model, and executed no simulator.
The process-guard self-match was isolated by a separate read-only process check,
which found no related task. The corrected immutable artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_static_preflight_74005ca4_20260714T211622CST`
with root SHA256
`b1090808c9c3176eaf63cd92db8fbf6249d65e0549efdcc240492654f47f5370`
and `run.exit=0`. It contains HEADS, COMMAND, stdout/stderr, summary JSON/MD,
SHA256SUMS, and ROOT_SHA256SUMS; `44 / 44` relevant AutoDL tests passed.

No model was loaded and no simulator executed. Calibration and holdout were not
executed, holdout outcomes were not read, and no claim was authorized. Next is
TDD for the optional decision sink and content-addressed train corpus writer;
holdout remains sealed.

## Native Decision Sink and Corpus Writer

Status: TDD passed; execution not started.

At source HEAD `203a3368663018e8855ba46176ff4f9a30675537`, the shared
`NativeCampPredictBatch` gained an optional v22-only decision sink. With the
sink disabled, v21 behavior and interfaces remain unchanged. With it enabled,
the hook samples ticks 0, 5, and 10 and every fifth tick thereafter. Emission
occurs only after the finite `8 x 14` atom matrix, source-valid mask, selected
exact row, and candidate tensor before/after SHA256 equality have passed. A
materializer-induced candidate mutation raises before the sink is called.

Each snapshot feature payload contains exactly the atom matrix,
source-valid mask, and eight candidate-row SHA256 values. Causal-input SHA,
physical-risk mask, all-K-high-risk flag, collection behavior provenance, and
all logical-map/route/group/split/seed identity fields only in the sidecar.
The corpus writer validates these boundaries, writes each content-addressed snapshot
once, rejects a candidate-tensor SHA mismatch, and records that holdout snapshots
are rejected before execution.
A failed route-seed receipt persists failure stage/reason, the snapshots already
written, and `retained_in_denominator=true`; it is not deleted or replaced.

The immutable implementation evidence is
`/root/autodl-tmp/camp_dp_v22_native_decision_sink_writer_203a3368_20260714T212738CST`
with root SHA256
`94db868dcbd2a7d2711dda8158ed90f6901c45442f2f173c2d0f343fbd3ff5de`
and `run.exit=0`. AutoDL py_compile/contract/hook/runner/capability/split/pointer
regressions passed `58 / 58`. No model was loaded and no simulator executed;
no train, calibration, or holdout route ran, holdout outcomes were not read,
and no claim was authorized. Next is a train-only execution harness and its
static preflight before any native corpus run.

## Native Train Corpus Execution Harness and Preflight

Status: passed; execution authorized but not started.

Source HEAD `70dd163727fddf3ebd965c44e54d8491d2fd7305` added the
train-only execution harness. It derives and validates all 32 / 32 frozen run
configs before runtime. Every run is the CAMP collection arm only; it injects
the route-seed namespace value into the scenario, candidate, and spawn seed,
uses exactly 64 native ticks, and reuses one lazy-loaded model through the
existing `build_native_arm_runner`. No parallel replay loop exists.

The harness attempts every frozen train route-seed even after a run-level
source/simulator/tracker failure. It records a retained failure receipt rather
than deleting or replacing the route, plus per route-seed wall-clock, total
wall-clock, snapshot counts by source stratum and all-K-high-risk snapshot
counts. Calibration and holdout are absent from the call inventory. Formal
seeds and Full36 remain forbidden.

The first preflight artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_execution_preflight_70dd1637_20260714T213842CST`
with root SHA256
`3682434e21939e148f63a52640c7846e8130157926192b376ef32f91f160ea5f`.
Its checks passed, but review found a stale next-work pointer left from the
decision-sink gate. It is preserved and is not the execution authorization.
TDD at source HEAD `0d4046c08a7f922d402a1d6f518dbb963862c8b7` locked the
correct pointer. The corrected immutable preflight artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_execution_preflight_pointer_fixed_0d4046c0_20260714T214002CST`
with root SHA256
`c635be46ae3d511c496af2d0175812ea3611acc71da8beed1d72651bae108387`
and `run.exit=0`; `62 / 62` AutoDL tests passed.

No model was loaded and no simulator executed in either preflight. The
corrected summary reports 4 / 30 / 100 routes, 8 / 3 / 5 seeds, 32 train runs,
416 theoretical snapshots, no reachable 5k/10k/20k/50k level, and
`next_work_target=v22_native_train_corpus_execution_only`. Holdout outcomes
were not read and no claim was authorized. Next is exactly one train-corpus
execution; an existing related process must be monitored rather than restarted.

current_v22_status=v22_native_train_corpus_execution_preflight_passed
current_v22_artifact_source_head=0d4046c08a7f922d402a1d6f518dbb963862c8b7
current_v22_prior_gate_final_synced_head=0d4046c08a7f922d402a1d6f518dbb963862c8b7
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_native_train_corpus_execution_preflight_pointer_fixed_0d4046c0_20260714T214002CST
current_v22_artifact_root_sha256=c635be46ae3d511c496af2d0175812ea3611acc71da8beed1d72651bae108387
next_work_target=v22_native_train_corpus_execution_only
