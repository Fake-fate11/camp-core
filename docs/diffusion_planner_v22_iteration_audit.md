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

## First Native Train Corpus Execution and Candidate-0 Receipt Remediation

Status: execution complete; evidence review no-pass; receipt remediation TDD
passed; one corrected train-corpus rerun authorized.

The first train-only native corpus execution at source HEAD
`8ecd346c110b0f7ebd66c290be2d06d8f466708a` completed all `32 / 32 route-seed
runs`, retained `416 / 416 snapshots`, and had zero execution failures. All 32
frozen denominator rows remain present. The immutable execution artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_8ecd346c_20260714T214316CST`
with root SHA256
`d270e094902401c791bebb21e6f88bf6e7a2bafae4f7daeaf874340156d5abb0`.
Its total wall-clock was `1037.325977530796 s`; per-run wall-clock mean, median,
minimum, and maximum were `32.4159 / 32.0706 / 30.9441 / 34.9905 s`. All 416
snapshots carried the branch-intersection, short-progress-opportunity, and
tight-corridor source strata; none was marked all-K-high-risk. Calibration and
holdout were not executed.

Independent review verified the source root and execution counts but found
that all `416 / 416 snapshots omit` both `default_output_sha256` and
`default_candidate0_identity`. Candidate-row and candidate-tensor immutability
SHAs were present, and the live hook had checked the identity internally, but
the artifact could not independently prove at every sampled tick that candidate
0 was the byte-identical DP operational default. Therefore the execution is
preserved as complete but is not a gate pass and is not renamed as success.
The immutable no-pass review is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_independent_review_no_pass_8ecd346c_20260714T220605CST`
with root SHA256
`c32c9110015b069f3300b5d3878ade0286d829f22aa0a42cff83504d14986983`
and `run.exit=1`.

Minimal TDD at source HEAD `b5880e25816bfde2058746eca8b37c3d36461aa9`
now persists the existing operational-default SHA, candidate-0 SHA, and full
default/candidate-0 identity receipt in each snapshot sidecar. The corpus writer
rejects a missing SHA, a row-0 mismatch, a candidate-0 mismatch, or a false
identity receipt. It does not modify DP, the candidate tensor, any trajectory,
the selector score, or the split. The immutable AutoDL TDD artifact is
`/root/autodl-tmp/camp_dp_v22_candidate0_identity_receipt_tdd_b5880e25_20260714T221217CST`
with root SHA256
`15c2444d73ef05742b88935e68d24fda946d9a40ee4974bf8417a17861996a6e`;
`69 / 69` relevant tests, py_compile, and git diff checks passed.

No calibration or holdout outcome was read, and no claim was authorized. Since
the missing per-tick evidence cannot be reconstructed from the first artifact,
the next gate is one corrected train-corpus rerun at the fixed split and seeds.
It must not run in parallel with any existing related task and must be followed
by an independent full-snapshot evidence review before label construction.

## Corrected Native Train Corpus and Independent Full-snapshot Review

Status: passed; all available train snapshots are frozen for label construction.

The corrected train-only corpus execution ran exactly once at CAMP HEAD
`ac13fa415e4a59e7557504a506f6618468b7dc77` and fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It completed all `32 / 32
route-seed runs`, retained all `416 / 416 snapshots`, had zero failures and
route coverage `1.0`, and used the same frozen four routes, eight non-formal
train seeds, 64 ticks, and 0.5 s snapshot cadence. The immutable artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_corrected_ac13fa41_20260714T222051CST`
with root SHA256
`a5ab6572eab37ecec6031e14a56755c71ef26b8ffd393d710ee32d40af8dfcb7`
and `run.exit=0`.

Execution wall-clock was `1026.6618002699688 s`. Per route-seed wall-clock
mean, median, minimum, and maximum were
`32.08267445088131 / 31.856336938915774 / 30.42812016699463 /
34.52966402238235 s`. All 416 snapshots carry the branch-intersection,
short-progress-opportunity, and tight-corridor source strata; zero are
all-K-high-risk in this train corpus. This does not change the all-K-high-risk
runtime contract or remove that stratum from pilot/main evaluation.

The read-only independent review performed `9,514 independent checks` with
zero failures. It rehashed the source root and every source artifact file,
verified all 32 retained route-seed receipts and exact ticks `0, 5, ..., 60`,
proved exact reference coverage for all content-addressed snapshots, and
validated `416 / 416 DP operational default/candidate-0 identity receipts` plus
416 / 416 candidate-tensor immutability receipts. Every feature payload is
exactly finite 8 x 14 atoms, an eight-value source-valid mask, and eight
candidate-row SHAs; map, route, group, split, and seed remain sidecar-only.
The review artifact is
`/root/autodl-tmp/camp_dp_v22_native_train_corpus_corrected_independent_review_ac13fa41_20260714T224107CST`
with root SHA256
`cf3622d49f8933e16868618b9dd7eaa6736b07a3978af22a1d4463df5402ecd1`
and `run.exit=0`.

No 5k/10k/20k/50k learning-curve tier is reachable under the frozen split, so
training must use all 416 available snapshots and report the sub-5k ceiling.
All 416 snapshots still mark offline supervision as pending: no label has been
invented or inferred from missing data. No calibration or holdout route/outcome
was executed or read, the independent review loaded no model and ran no
simulator, and no claim is authorized. The next gate is exactly
`v22_train_only_offline_label_contract_and_tdd_only`: define and test a
train-only, causal/source-backed label sidecar before convex training.

## Train-only Causal Soft-risk Label Materialization and Independent Review

Status: passed; one train-only causal label corpus is sealed for convex
selector training.

The frozen label schema is `v22_causal_soft_risk_surrogate_v1`. Each label is
a causal soft-risk surrogate, not an actual closed-loop outcome. For candidate
`k`, it adds normalized, clipped canonical-14D soft-risk severities and a
finite additive penalty of 100 for predicted physical risk. The source-valid
mask is the only eligibility boundary: predicted collision, clearance, lane,
red-light, speed, progress, and comfort risks remain finite costs and never
invalidate a source-complete candidate. No route, map, group, split, or seed
identity is a feature or label input.

At source HEAD `fb7d1032955c03b1c56bcb9311a3adc1570bd482`, AutoDL
materialized `416 / 416 label sidecars` from the corrected train corpus, with
no missing or nonfinite row. Train-only 95th-percentile atom scales have SHA256
`1da8ff585eca04c11fae9cd1a5629c4f077d26f050d075f97a6f5c1c9810a740`.
There are 11 supported atoms with positive cross-candidate range. The three
unsupported atoms are lane_deviation, planned_red_light_cost, and
red_stopping_margin_cost; they remain in the canonical 14D schema and must
receive zero learned weight. The surrogate oracle selected candidate 0 versus
non-candidate 0 in `12 / 404` snapshots. This is training supervision only,
not paired closed-loop evidence.

The immutable materialization artifact is
`/root/autodl-tmp/camp_dp_v22_train_causal_labels_fb7d1032_20260714T225959CST`
with root SHA256
`86be3a18fb7f1fe3efdee1ee4a1c7b1399baac9c7421ea784d21b349bde89a4f`.
It used the already sealed 416-snapshot source root and did not load a model or
run the simulator.

The independent review recomputed every scale, support mask, candidate cost,
oracle, source linkage, and content hash. It performed `3,759 independent
checks` with zero failures. Its immutable artifact is
`/root/autodl-tmp/camp_dp_v22_train_causal_labels_independent_review_fb7d1032_20260714T230052CST`
with root SHA256
`f8e646e6b030efb2b613ec3a30b2a712e4a5fb55b79aa4daa386ee390560971c`
and `run.exit=0`.

No calibration or holdout data or outcome was read. No model was loaded and no
simulator executed. No safety or CAMP-over-DP claim is authorized. Since no
5k/10k/20k/50k tier is reachable, the next target
`v22_convex_selector_training_tdd_only` trains exactly the frozen
all-available-416 level using the existing convex master and reports the true
sub-5k ceiling.

## Convex Selector Training TDD

Status: passed; implementation is ready for a read-only execution preflight.

At CAMP HEAD `fdbbf1c5e7a98d77847ce78895052fd0c710b565`, focused
TDD reuses the unchanged robust-margin master through CVXPY/CLARABEL. It sorts
snapshots by content SHA, converts lower-is-better surrogate costs with
`outcome_oracle_and_margins(-cost, source_valid, ...)`, and trains only the
honest `all_available_416` level because every preregistered 5k/10k/20k/50k
level is unreachable. Solver acceptance requires exact `optimal`, convergence,
zero final new cuts, a projected final gap at most `1e-6`, and a finite
nonnegative simplex.

Only the 11 supported atoms enter the convex master. The three unsupported
canonical atoms expand back into the 14D runtime model with strict zero learned
weight. The frozen transform is `clip(raw_atom/scale,0,10.0)` using the already
sealed train-only scales; no scale is recomputed. The output records solver
name/status, iterations, gap, cuts, convergence, history, offline wall-clock,
and train surrogate-ranking diagnostics without calling iterations epochs.

Loader tests prove train-only split and non-formal seeds, exact candidate-0
identity and candidate-tensor immutability, label-to-source root linkage, and
the feature identity denylist before solver invocation. The v18 frozen
corrected14d selector is ablation-only and cannot become the v22 primary model.
Calibration, holdout, simulator execution, and claims remain disabled.

Local regression passed `81` tests with one expected skip because the local
environment lacks CVXPY. AutoDL ran the focused trainer and actual
CVXPY/CLARABEL Benders contract with `13 / 13` tests passing, plus py_compile
and diff checks. Its immutable artifact is
`/root/autodl-tmp/camp_dp_v22_convex_selector_training_tdd_fdbbf1c5_20260714T232226CST`
with root SHA256
`e63260e1ed636672a42fa8f2f19ac2b3ba34093fb18af082c7f5f2f44a5d18fd`
and `run.exit=0`.

One earlier controller invocation used an incorrect guessed full CAMP SHA and
exited immediately after the successful ff-only update, before artifact
creation, tests, solver use, or training. The corrected invocation above used
the live full SHA. No production model was trained, no simulator ran, and no
calibration/holdout data or outcome was read. Next gate is a read-only
preflight of every frozen root, input count, solver availability, output
absence, and process guard. Its exact target is
`v22_convex_selector_training_preflight_only`.

## Convex Selector Training Execution Preflight

Status: passed; the one train-only solve is authorized.

The read-only AutoDL preflight ran at CAMP HEAD
`b4389693c78d6c293c7238d389a9c3d54215ee31` with fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It independently rehashed all
six frozen upstream roots: corrected source corpus, source review, causal label
corpus, label review, v18 ablation freeze, and v18 review. All matched their
preregistered SHA256 values.

The loader retained all `416 snapshots`. Train inventory counts for logical
maps / routes / route-family groups / seeds / route-seeds were
`1 / 4 / 1 / 8 / 32`. Eleven atoms were supported and three unsupported. No
5k/10k/20k/50k level was reachable, so the only planned solve remains
`all_available_416`. Snapshot filenames were exact content SHAs and their
order was lexicographically frozen before any solver use.

AutoDL had CVXPY 1.6.7 with CLARABEL installed and `50,336,387,072 free
bytes`. No related Python process existed. The planned output was absent:
`/root/autodl-tmp/camp_dp_v22_convex_selector_training_execution_fdbbf1c5`.
The v18 ablation-only dry evaluation agreed with the surrogate
oracle for `186 / 416` snapshots and selected candidate 0 / non-candidate 0 in
`10 / 406`; its selected versus candidate-0 mean surrogate costs were
`5.770243907042391 / 5.66610969706022`. These are train-only ablation
diagnostics, not closed-loop outcomes or a performance claim.

No solver was invoked, no model was trained, no simulator ran, and no
calibration/holdout data or outcome was read. A first local orchestration
attempt had a quoting SyntaxError before SSH connection or artifact creation;
the corrected read-only attempt below is the only remote preflight execution.
Its immutable artifact is
`/root/autodl-tmp/camp_dp_v22_convex_selector_training_preflight_b4389693_20260714T232907CST`
with root SHA256
`b89a653114b82405cdcc2eb73f63f3537c979a9bb55baab239118448ae74949c`
and `run.exit=0`.

The exact authorized execution target was
`v22_convex_selector_training_execution_only`.

## Convex Selector Training Execution and Independent Review

Status: passed; one v22 train-derived candidate model is sealed for
calibration. It is not yet the frozen primary selector.

The only reachable level, `all_available_416`, completed once on AutoDL. Its
immutable execution artifact is
`/root/autodl-tmp/camp_dp_v22_convex_selector_training_execution_fdbbf1c5`
with root SHA256
`aab747c7ab835d11421bbb6f77e8aeb53aeba97b666adeb0fb6f7e98918ca23a`
and `run.exit=0`. Total artifact wall-clock was `1.1904628276824951 s`.
Model SHA256 is
`33d4d9b23e7cc505e546a8bf33ca7477f072118ea1fda6dad9744969fc00956a`.

CLARABEL returned exact `optimal` and converged. Solver iterations / final
projected master gap / total cuts were `2 / 4.39870362356487e-13 / 434`;
solver wall-clock was `0.7657483862712979 s`. The canonical 14D simplex has
only two nonzero weights: speed_limit_margin_0_0 / clearance are
`0.47543440765511247 / 0.5245655923448875`. All other weights, including the
three unsupported atoms, are exactly zero. The frozen atom transform remains
`clip(raw_atom/scale,0,10.0)`.

Train surrogate diagnostics selected candidate 0 / non-candidate 0 in
`305 / 111` snapshots and agreed with the surrogate oracle in `96 / 416`.
Selected / candidate-0 / delta mean surrogate costs were
`2.7545079763521803 / 5.66610969706022 / -2.9116017207080387`. These are
train-only surrogate diagnostics, not actual closed-loop outcomes or safety
evidence. The previously reported v18 selector remains ablation-only.

The independent reviewer rehashed the execution artifact and model, then
recomputed all 416 source/label links, candidate identity and immutability
receipts, clipped scores, source-valid selections, surrogate oracles, margins,
violations, CVaR, train metrics, and v18 ablation. It performed `2,546
independent checks` with zero failures and did not invoke the solver or retrain
the model. Its artifact is
`/root/autodl-tmp/camp_dp_v22_convex_selector_training_independent_review_017aa8d9_20260714T233449CST`
with root SHA256
`8cf7c4b2b85d27a027d05589d50d5adb901c90774752f5cf506c6cecea7904e5`
and `run.exit=0`.

The execution manifest explicitly records `primary_model_frozen=false`. No
calibration or holdout route/outcome was read, no simulator ran, and no claim
is authorized. Next gate is a read-only preflight for generating native causal
decision snapshots on the already frozen 30-route, 3-seed calibration split;
it may not alter train weights, scales, atom schema, or holdout state.
Its exact target was `v22_native_calibration_corpus_preflight_only`.

## Native Calibration Corpus TDD

Status: passed; the shared native corpus runner is ready for a read-only
calibration preflight.

At CAMP HEAD `16d580a5ce7f43401e7bcc840a3ebbd23a31e0f0`, TDD
parameterized the existing train corpus path for exactly one `train` or
`calibration` split. It did not create a parallel runner. The existing train
entry point remains backward compatible, while the new calibration entry
point generates run configs with training disabled, calibration enabled, and
holdout/formal-seed/claim access disabled. The shared v21 native validator
enforces those mutually exclusive roles.

The tracked calibration config binds the already frozen source-only split
manifest: `30 routes x 3 non-formal seeds = 90 route-seed attempts`, with a
maximum of `1,170` causal snapshots at 0.5-second cadence. All preregistered
routes remain in the attempt set and denominator. A native failure writes a
retained failure receipt and cannot trigger route deletion, replacement,
redraw, candidate-0 fallback, or holdout access. Identity fields remain
receipt-only and the feature payload remains exactly atom matrix,
source-valid mask, and candidate-row hashes.

Local and AutoDL regression both passed `102 tests`; py_compile, diff check,
and tracked-clean checks also passed. The immutable AutoDL artifact is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_tdd_16d580a5_20260714T235050CST`
with root SHA256
`afee77845876ec7f6d20793ec169cfa5969e9391cae88a343bd9191201bac124`
and exit 0. CAMP/origin HEADs matched, and fixed DP remained
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

No model was loaded and no simulator, solver, calibration outcome, holdout
outcome, training, or claim ran. Next gate is static calibration-corpus
preflight only: verify frozen roots/assets/counts, process guard, output
absence, storage, and all 90 planned run configs without starting the native
runner.

## Native Calibration Corpus Static Preflight

Status: passed; one frozen 90-attempt calibration corpus execution is
authorized.

At CAMP HEAD `606aa838084337bd0e9546458ab59e3b771d3824`, the
read-only AutoDL preflight rehashed both the frozen route-family split artifact
and the preceding calibration TDD artifact, including their nested
SHA256SUMS. Their roots matched
`b231ba9fe425e40a129e30ce0b37044f1059354f84744d91911608f09f87baa5`
and
`afee77845876ec7f6d20793ec169cfa5969e9391cae88a343bd9191201bac124`.

Static validation retained the frozen inventory of 4 train, 30 calibration,
and 100 holdout routes with disjoint 8, 3, and 5 seed namespaces. It selected
only calibration and validated exactly `30 x 3 = 90` native run configs. The
maximum snapshot count is `1,170` at 0.5-second cadence. Every run config keeps
K=8 fixed-candidate selection, source-valid-only eligibility, affine/simplex
scoring, training disabled, calibration enabled, and holdout/formal-seed/claim
access disabled.

The planned execution output
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_execution_606aa838`
was absent. No matching execution process existed and AutoDL had
`50,334,998,528` free bytes. The static command did not build the runner,
load a model, execute a simulator, read outcomes, or open holdout.

The immutable preflight artifact is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_preflight_606aa838_20260714T235357CST`
with root SHA256
`122d4e12fc44f7a4a9b90386c8acc2d370870480f960f34c6e4923b5f702ea42`
and exit 0. CAMP/origin matched; fixed DP remained
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The next gate may start exactly one calibration-corpus execution for all 90
frozen route-seed attempts. It must retain success and failure receipts, may
not replace or redraw any route, and may not read holdout.

Its exact target was `v22_native_calibration_corpus_execution_only`.

## First Native Calibration Corpus Execution and Independent Review

Status: execution complete; evidence review no-pass due to one metadata
provenance defect; remediation TDD is next.

The one authorized execution ran at CAMP HEAD
`83c090761c6c928e71de7fd99f58a21c15abd1f6` and fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It attempted every frozen
calibration route-seed exactly once: planned / retained / complete / failed
were `90 / 90 / 89 / 1`. Route coverage is `1.0`. The sole retained failure
was route identity
`1f621dfd5ef7d16c036520249f7521772f8377257e4ac57f63d060990221c957`
at seed 22102, stage `native_arm_execution`, reason
`native safety metric source is incomplete`. It remains in the denominator;
hard-source-failure rate is `1 / 90 = 0.011111111111111112`. No route was
deleted, replaced, redrawn, or forced to candidate 0.

The execution retained the full theoretical `1,170 / 1,170` causal snapshots,
including the failed row's already emitted 13 snapshots. Five snapshots are
all-K-high-risk. Successful-run source-stratum snapshot counts are 1,157
branch-intersection, 1,157 tight-corridor, and 494 traffic-light. The
collection policy remained the v18 selector as an ablation-only behavior
policy; the v22 trained candidate was not frozen or loaded as primary. Total
wall-clock was `2,863 s`.

The immutable execution artifact is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_execution_606aa838`
with root SHA256
`a2304f73892b13f952850a41e300f00710b2f11b2017948776f06f80d2b338e4`
and `run.exit=0`. Its status is execution complete pending review, not a claim
or gate pass. Holdout was not executed or read.

The first independent reviewer preserved root
`f356391a3c0d01fee4ec5f0d66d07e619018975d949a1c41cb7443c26e70128b`
and exited 1. It correctly found the provenance defect, but also compared
canonical JSON's sorted feature-key load order against insertion order and
therefore produced 1,170 false-positive feature-schema failures. No source
artifact was altered. A corrected review-only harness instead compares the
exact feature key set.

The corrected independent review performed `24,224` checks. Candidate-0 / DP
operational-default identity and candidate-tensor immutability passed
`1,170 / 1,170`. All 90 receipt identities, route retention, exact tick
coverage, source-valid/physical masks, all-K-high-risk receipts, feature
identity denylist, source strata, content hashes, and holdout absence passed.
Its only `1,170` failed checks are
`offline_label_provenance`: every calibration snapshot retained the hook's
train-only string `pending_train_only_offline_supervision_sidecar`, instead of
the frozen calibration provenance
`calibration_causal_candidate_cost_sidecar_only_not_selector_feature`.

The corrected no-pass review artifact is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_independent_review_corrected_83c09076_20260715T005600CST`
with root SHA256
`f2e97e3c85886275d29c06775d0632ae9bc7efc05d0c8c2e67a5517fb9723866`
and `run.exit=1`. It loaded no model and ran no solver or simulator. The first
execution cannot be renamed as success and its snapshots cannot be rewritten
in place. The next target is minimal TDD that makes the shared writer stamp
split-specific offline-label provenance before content hashing. It may not
change feature payloads, DP, candidates, trajectories, score, split, or
failure-retention behavior.

Its exact target was
`v22_native_calibration_corpus_label_provenance_receipt_remediation_tdd_only`.

## Calibration Provenance Receipt Remediation TDD

Status: passed; a corrected execution preflight is next.

At CAMP HEAD `810f050bded6b6e4a77008fde98887b15482e870`, the
minimal remediation leaves the shared native runner and all feature/candidate
paths untouched. `CorpusSnapshotWriter` stamps exactly one split-specific
offline-label provenance value before canonical JSON hashing. Calibration must
use
`calibration_causal_candidate_cost_sidecar_only_not_selector_feature`; a
different tracked config value fails preflight. Train snapshots retain the
historical `pending_train_only_offline_supervision_sidecar` value.

TDD first reproduced the defect: a calibration snapshot lacked the tracked
provenance. After the fix, its content-addressed sidecar matches the frozen
calibration config. The test also proves calibration remains training-disabled
and holdout-disabled. Feature payloads remain exactly atom matrix,
source-valid mask, and candidate-row hashes. No map/route/group/split/seed
identity enters features. DP, K=8 candidates, candidate-0 identity, trajectories,
affine/simplex scoring, source-valid eligibility, all-K-high-risk selection,
and failure retention are unchanged.

Local and AutoDL regression each passed `102 tests`; AutoDL py_compile, diff,
and tracked-clean checks also passed. Immutable TDD artifact/root:
`/root/autodl-tmp/camp_dp_v22_calibration_provenance_remediation_tdd_810f050b_20260715T010014CST`
/ `9d4cb7820956bfc0ef828612a7ae6e920ec69d6617f8b1ec1c8db08bcb94219b`,
with exit 0. No model, solver, simulator, calibration outcome, or holdout was
opened by this gate.

The first execution and both no-pass review artifacts remain immutable and are
not renamed. Next is read-only preflight for one corrected rerun over the same
frozen 30 routes and 3 seeds. It must verify all upstream roots, exact output
absence, process guard, 90 configs, and the provenance contract before any
simulator starts.

Its exact target was
`v22_corrected_native_calibration_corpus_execution_preflight_only`.

## Corrected Native Calibration Corpus Execution Preflight

Status: passed; exactly one corrected rerun is authorized.

At CAMP HEAD `7d36c199496949f205b0f1f5e572297f9c54bacc`, the
read-only AutoDL preflight rehashed the first execution root
`a2304f73892b13f952850a41e300f00710b2f11b2017948776f06f80d2b338e4`,
the corrected no-pass review root
`f2e97e3c85886275d29c06775d0632ae9bc7efc05d0c8c2e67a5517fb9723866`,
and remediation TDD root
`9d4cb7820956bfc0ef828612a7ae6e920ec69d6617f8b1ec1c8db08bcb94219b`.
All nested SHA manifests passed.

Static validation again produced exactly 90 run configs from the unchanged 30
calibration routes and 3 non-formal seeds, with a 1,170 snapshot ceiling. The
tracked provenance is exactly
`calibration_causal_candidate_cost_sidecar_only_not_selector_feature`.
Pointer/corpus tests passed; no related execution process was active. Planned
corrected output
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_corrected_7d36c199`
was absent and `50,324,267,008` bytes were free.

The immutable preflight artifact/root is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_corrected_preflight_7d36c199_20260715T010211CST`
/ `390d5627abbf8974873b1bc761739d97294f55320b9c256114a8b4a129cc7a5a`,
with exit 0. It built no runner, loaded no model, executed no simulator, and
read no holdout outcome. The next gate may run the same frozen 90 attempts
exactly once and must retain any source/execution failure without replacement.

Its exact target was `v22_corrected_native_calibration_corpus_execution_only`.

## Corrected Native Calibration Corpus and Independent Review

Status: passed; calibration evidence is ready for selector freeze and pilot
preflight work.

One controller invocation performed the ff-only update and exited before
artifact creation because its full CAMP SHA was guessed incorrectly. A live
read then confirmed the actual full SHA, corrected output absence, and no
related process. No model or simulator ran in that failed launch attempt. The
corrected invocation started exactly one task.

The corrected execution ran at CAMP HEAD
`b8bab7a0460496d896d4efdb527281731f5aafa8` and fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Planned / retained /
complete / failed were again `90 / 90 / 89 / 1`. Route coverage is `1.0`.
The same route identity
`1f621dfd5ef7d16c036520249f7521772f8377257e4ac57f63d060990221c957`
at seed 22102 was retained with `native safety metric source is incomplete`,
so hard-source-failure rate remains `1 / 90 = 0.011111111111111112`. It was
not deleted, replaced, or redrawn.

All `1,170 / 1,170` content-addressed snapshots were retained, and all now
carry the frozen calibration provenance. Five are all-K-high-risk. Successful
source-stratum counts are 1,157 branch-intersection, 1,157 tight-corridor, and
494 traffic-light snapshots. Wall-clock was `2,854 s`. The v18 selector
remained collection behavior only; the v22 candidate was not yet frozen as
primary.

The immutable corrected execution artifact/root is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_corrected_7d36c199`
/ `07255ae24e1038860c22227822787c63f39e21cdde7e8f91d6829a716b8a8335`,
with `run.exit=0`.

The independent reviewer rehashed the execution and remediation TDD roots,
then repeated `24,224 independent checks` with zero failures. It verified all
90 route-seed receipts and the exact source-only cross-product; all content
hashes and tick coverage; feature identity denylist; finite 8 x 14 atoms;
source-valid and physical masks; 5 all-K-high-risk receipts; source strata;
and holdout absence. DP operational-default/candidate-0 identity and candidate
tensor immutability passed `1,170 / 1,170`. Calibration provenance passed
`1,170 / 1,170`.

The immutable review artifact/root is
`/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_corrected_independent_review_b8bab7a0_20260715T015350CST`
/ `c73c1b35a29294a7a14d02326bedb2f213e25cd8771bcdf165d747e0677d047a`,
with `run.exit=0`. The review loaded no model and ran no solver or simulator.
No holdout outcome was read and no claim is authorized.

The next target is TDD for calibration-only selector freeze and pilot
preflight. It may use calibration snapshots to compare the already trained
v22 candidate and v18 ablation under the frozen causal surrogate and speed
tolerance sensitivity, but may not retrain weights, alter train-only scales,
read holdout, or start pilot execution before the freeze artifact and static
preflight pass.

current_v22_status=v22_corrected_native_calibration_corpus_and_independent_review_passed
current_v22_artifact_source_head=b8bab7a0460496d896d4efdb527281731f5aafa8
current_v22_prior_gate_final_synced_head=b8bab7a0460496d896d4efdb527281731f5aafa8
current_v22_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v22_artifact=/root/autodl-tmp/camp_dp_v22_native_calibration_corpus_corrected_independent_review_b8bab7a0_20260715T015350CST
current_v22_artifact_root_sha256=c73c1b35a29294a7a14d02326bedb2f213e25cd8771bcdf165d747e0677d047a
next_work_target=v22_calibration_selector_freeze_and_pilot_preflight_tdd_only
