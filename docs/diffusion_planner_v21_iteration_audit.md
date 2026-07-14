# Diffusion Planner V21 Iteration Audit

Last verified: 2026-07-14, Asia/Shanghai.

This file is the sole v21 gate authority. V20 and earlier audits are historical
and read-only. V21 uses the fixed TiER IV Diffusion Planner native
`scenario_generation` simulator; CARLA and official nuPlan simulation are out
of scope.

## Frozen Objective Boundary

- CAMP repository: `F:\camp_core-main`, branch `main`.
- CAMP source HEAD for Gate A:
  `b419acf31eea7323232f117e8009f5eb9e19e318`.
- Fixed DP repository: `/root/autodl-tmp/Diffusion-Planner`.
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Baseline: the actual native operational default output. The label
  "operational Top-1" is allowed only after an independent exact-identity
  check.
- CAMP action: select one immutable member of the current causal K=8 tensor;
  it may not generate, repair, blend, smooth, or rewrite a trajectory.
- No Full36, formal seeds 11/12/13, holdout reopening, claim, promotion,
  deployment, online activation, model replacement, or real-road statement.

V20 remains an honest no-claim closeout. Its scientific artifact source HEAD
is `3b69cde1849d258b9e328abedd3819e232f81b98`; its final docs-sync HEAD is
`b419acf31eea7323232f117e8009f5eb9e19e318`. The different hashes describe
source execution and later documentation synchronization. They are not a
three-endpoint drift signal and neither may be rewritten by v21.

## Gate A: Native Simulator Capability and Provenance Audit

Status: passed read-only.

Startup synchronization proved:

- local CAMP `main`, `origin/main`, GitHub `main`, and AutoDL CAMP were all
  `b419acf31eea7323232f117e8009f5eb9e19e318` and tracked-clean;
- AutoDL DP was tracked-clean on `tier4-main` at the fixed HEAD;
- no related v21, `scenario_generation`, training, or evaluation task was
  running;
- no model, simulator, training data, holdout, or formal seed was opened.

### Native entrypoint, state, and data

The selected simulator entrypoint is
`scenario_generation.replay.run_route_replay`. It consumes an authored
`scenario_generation.route.Route`, constructs a live `SceneContext`, batches
every active agent as ego through the same fixed DP, advances all agents, and
updates map and signal state at 0.1 s. `scenario_generation.simulate` also
contains generic `closed_loop` and `semi_closed_loop` modes, but v21 does not
need a second simulator framework.

The AutoDL runtime is Python 3.12.3 with Torch 2.8.0+cu128, NumPy 1.26.4,
SciPy 1.14.1, and Lanelet2. The native builder imports an unavailable
Autoware `MGRSProjector`; the existing CAMP
`install_lanelet2_projection_fallback` process-local shim supplies a standard
Lanelet2 UTM projector for the existing no-ROS maps. Live construction of the
sample map passed, the authored start pose was inside its drivable lanelet,
all four route segments had exact positive speed limits, and 36 road-border
polylines were available. This shim changes only map projection dependency
resolution; it does not alter DP, candidates, simulator dynamics, or metrics.

Existing authored route assets include a normal sample route and two
traffic-light routes on the same sample map. Regulatory traffic-light objects
expose their exact stop lines, and the native seeded controller exposes the
current group color. No new data download or license action is required for a
tiny 2-route smoke.

### History and future-leakage contract

The fixed DP converter has `_INPUT_T=30`, hence 31 history frames. Native
`_pad_or_truncate` prepends deterministic all-zero rows when a history is
short and retains the most recent 31 frames when it is long. A live 3-to-31
probe confirmed 28 zero prefix rows followed by byte-equal observed rows.
Route replay synthesizes a full 31-frame causal ego history, so the initial
smoke should normally report `observed_frames=31` and `padded_frames=0`.

For any shorter source, v21 must use that native left-padding behavior and
record `observed_frames`, `padded_frames`, `padding_policy`, and a deterministic
input SHA. The direct-default and K=8 calls at one arm/tick must consume the
same materialized bytes. After paired arms diverge, each arm correctly uses
its own current causal state; cross-arm histories are not forced equal.

The following future-derived paths are forbidden:

- `simulate.py --use_gt_goals`, which derives routes/goals from GT future;
- `npz_loader.py` heading correction when it falls back to
  `future_trajectory` for a stationary history;
- replay NPZ post-hoc neighbor-future backfill as an online selector or
  training input;
- any future interpolation, outcome field, evaluation label, or future-derived
  route/goal at decision time.

V21 therefore uses authored routes and live native state, keeps
`dump_npz_dir=null`, and removes all future placeholder/outcome keys at the
CAMP boundary.

### Operational default, K=8, and trajectory immutability

Native `simulate._predict_batch` converts current `SceneContext`, leaves
`sampled_trajectories` at zero, and consumes `outputs["prediction"][:, 0]`.
That is the actual route-replay operational default path; candidate 0 identity is not claimed in Gate A.
Gate D must run the direct native path and an
independent zero-latent candidate path on identical input and require:

- `np.array_equal=true`;
- zero maximum absolute difference;
- identical dtype, shape, and SHA256;
- candidate tensor SHA unchanged before/after atoms and selection.

If any equality check fails, the baseline keeps its truthful native
operational-default definition and candidate 0 may not be renamed Top-1.

The native replay has two trajectory transformations outside DP inference:

- Savitzky-Golay smoothing is enabled by default and rewrites predictions;
- stuck recovery rewrites the ego prediction after 400 consecutive low-speed
  ticks.

V21 must set `sg_smooth_enabled=false` and freeze tiny-smoke
`max_steps < 400`, making both rewrites impossible. It also uses the same
native MPC tracker in both arms with horizon 20 and 5 knots. The tracker may
postprocess its reference internally as common downstream actuation, but the
selected candidate bytes are recorded before the tracker and may not change.

### Atom source audit

The existing canonical `dp_camp_v10_14d` schema remains the first reuse
candidate. Native route replay can potentially provide all required sources:

- immutable K=8 candidate trajectories for jerk, acceleration, lateral
  comfort, progress, and the candidate-0 jerk anchor;
- authored route topology, boundaries, and exact segment speed limits;
- candidate-specific fixed-DP neighbor predictions and current static
  objects;
- live native traffic-light phase and red stop geometry.

Static capability is not runtime eligibility. Every tick must fail closed if
any signal, route speed, boundary, obstacle, neighbor-prediction, or candidate
identity source is missing. The selector remains affine
`score_k(w)=a_k^T w` on nonnegative simplex weights, and closed-loop outcomes
remain forbidden as training or online inputs. The frozen v18 14D checkpoint
may be used for smoke only if Gate D proves exact schema/source compatibility;
its cross-simulator distribution does not support a claim.

### Closed-loop metric source audit

The following actual or explicitly named diagnostic sources exist:

- collision: native realized ego-to-agent OBB clearance equal to zero;
- near miss: realized noncollision OBB clearance in `(0, 2 m]`;
- road border: native realized ego-OBB-corner distance to a road-border line;
- drivable area: ego footprint corners inside the union of native drivable
  Lanelet2 lanelets;
- wrong way: ego heading versus the nearest current authored-route lane
  direction;
- red light: actual state transition crossing the regulatory stop line while
  the native controller reports red;
- speed limit: current ego speed versus the exact nearest-route-lane
  `speed_limit_mps`;
- TTC: a secondary, explicitly labeled constant-velocity causal diagnostic,
  never a measured future outcome;
- route progress/completion/stuck and comfort: current trajectory and tracker
  telemetry;
- latency: DP inference, atom materialization, selector, tracker, and total
  planning path measured separately.

Authored-route replay has no legal expert GT future. ADE/FDE/miss are therefore
unavailable and must be omitted, not zero-filled. Gate B must preregister one
SafetyCost formula using only the realized, runtime-materialized components;
missing required components invalidate a pair instead of receiving zero.

### Gate A evidence

Immutable artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_simulator_capability_audit_b419acf3_20260714T154035CST`;
- root SHA256:
  `47016fa5e4e397eec27b705cb122cab0c7d3f23c50cf03f84b41cf175ea15ac2`;
- stdout SHA256:
  `0b037e63c3f0512749121d3dd43b6d859f59d90c7254696c0cc5be3f2922953b`;
- `run.exit=0`, empty stderr, all seven payload hashes reverified, directory
  mode 555 and payload mode 444.

Source hashes, fixed checkpoint/config/selector hashes, route/map hashes,
live runtime capability output, heads, command, stdout, stderr, JSON, Markdown,
`SHA256SUMS`, and `ROOT_SHA256SUMS` are included.

No inference, simulation, training, holdout access, claim, promotion,
deployment, activation, DP modification, candidate generation, or metric
comparison occurred.

## Gate B: Paired Native Closed-loop Design and Self-review

Status: passed after one preserved pre-seal dependency correction.

Gate A was committed, pushed, and fast-forwarded on AutoDL at
`0937174beead161854b6e273020e53fcca589409`. This is Gate A's final synced
HEAD. Its evidence source HEAD remains `b419acf3...`; the two roles are now
explicit.

Three minimum approaches were reviewed:

1. a CAMP-side signature-compatible hook around native `run_route_replay` was
   selected;
2. copying the native replay loop was rejected as a parallel framework;
3. changing fixed DP was rejected as a hard boundary.

The design is frozen in
`docs/superpowers/specs/2026-07-14-v21-native-simulator-paired-closed-loop-design.md`.
It retains native `SceneContext`, route builder, NPC manager, traffic-light
controller, map refresh, operational non-ego policy, and MPC. Only the ego
planning callback can select one immutable current-tick candidate; a
pass-through wrapper measures tracker latency.

The spec freezes:

- native 31-frame causal input and
  `padding_policy=native_zero_left_pad_to_31_v1`, with observed/padded counts
  and deterministic input SHA;
- direct operational output first, candidate 0 reusing those exact bytes, and
  seven isolated extra fixed-DP latents;
- an independent Gate D default/candidate-0 exact identity proof before
  operational Top-1 naming;
- K=8 tensor SHA before/after equality and exact selected-index bytes;
- the existing corrected `dp_camp_v10_14d` scales/weights, nonnegative simplex,
  and `score_k(w)=a_k^T w`;
- two fresh native arms per pair with identical authored route, initial state,
  native seed/policy/TL/tracker/map config, and natural causal divergence after
  the first action;
- explicit `sg_smooth_enabled=false`, `dump_npz_dir=null`, native MPC, and
  `max_steps=64`, which makes the post-400-tick nudge unreachable;
- SafetyCost Native v1 using realized collision, noncollision near miss,
  offroad proxy, wrong-way, red stop-line crossing, and speed-limit rates;
- paired deltas, better/tie/worse, later scene/route/seed cluster CI95, and
  no smoke claim.

The first pre-seal runtime review failed because Shapely is not installed in
the frozen DP environment. No artifact had been created, and no download or
install occurred. Systematic review proved native Lanelet2 provides exact
point-in-lanelet tests but no polygon-union coverage overload. Before any
simulator outcome, the spec was narrowed to an honestly named five-point
drivable-coverage proxy using the ego center plus four OBB corners. It is not
called full polygon coverage. The failure reason is preserved in the sealed
artifact.

Gate A's provisional TL route `58_to_55` was also rejected before outcomes:
its authored start and goal are only 2.98 m apart on a looping route, which can
interact with native goal-pass termination. Gate E instead freezes existing
routes `sample_map_smoke_route.pkl` and `sample_map_tl_route_59_to_86.pkl`,
non-formal seeds 3417/3418, and 64 ticks.

The SafetyCost formula is frozen as:

```text
100 * collision_any
+ 10 * near_miss_noncollision_rate
+ 20 * offroad_rate
+ 20 * wrong_way_rate
+ 30 * red_light_violation_any
+ 10 * speed_limit_violation_rate
```

Missing sources or denominators fail the pair rather than becoming zero.
Road-border clearance, constant-velocity diagnostic TTC, route progress,
comfort, and latency remain secondary. ADE/FDE/miss are absent because authored
route replay has no legal expert GT future.

Immutable Gate B artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_simulator_design_self_review_0937174b_20260714T155319CST`;
- root SHA256:
  `5fa62b35bdc1b3f65b26077d98b2d150d3e274186d36e747ddaa3159c01221d1`;
- stdout SHA256:
  `586330234eea48e3bf295bf4c7855cf22e98bfd71ac6b5831ac6281eba3deb21`;
- `run.exit=0`, empty current stderr, all eleven payload hashes reverified,
  directory mode 555 and payload mode 444.

The artifact includes the spec, contract test, pre-seal failure reason, heads,
fixed asset/route/map hashes, route-geometry diagnosis, command, stdout,
stderr, JSON/Markdown, SHA256SUMS, and root SHA. Local design plus pointer tests
report `6 passed`.

No model load, inference, simulator run, training, holdout access, formal seed,
claim, promotion, deployment, activation, or DP modification occurred. No
scientific ambiguity remains before a minimal TDD plan.

## Gate C: Minimal Native Simulator TDD Plan

Status: passed.

Gate B was committed, pushed, and fast-forwarded on AutoDL at
`90937b0eda431e1365d41f1f5ef55864568d0a2d`. This is Gate B's final synced
HEAD and Gate C's evidence source HEAD; the source/final roles remain
explicit.

The executable plan is frozen in
`docs/superpowers/plans/2026-07-14-v21-native-simulator-paired-closed-loop-tdd.md`.
It keeps implementation CAMP-side and orders six test-first slices:

1. pure causal-input, padding, deterministic hash/seed, K=8 latent, default
   identity, and candidate immutability contracts;
2. a signature-compatible native replay hook that reuses native batching and
   the existing causal 14D selector without copying `run_route_replay`;
3. pure SafetyCost Native v1 reducers, including the honestly named Lanelet2
   five-point drivable proxy;
4. a paired runner plus fully frozen native smoke configuration;
5. one-tick Gate D capability execution and independent review;
6. two-route Gate E paired smoke and independent recomputation review.

Every implementation slice must show the intended red failure, the minimum
green code, target plus adjacent regression tests, `py_compile`, and
`git diff --check` before its exact-file commit/push and AutoDL fast-forward.
No DP edit, new dependency, parallel simulator, training in Gates C-E,
holdout access, formal seed, fallback selection, candidate repair, or smoke
claim is permitted.

Immutable Gate C artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_simulator_minimal_tdd_plan_90937b0e_20260714T155950CST`;
- root SHA256:
  `2625188c0d9346e5d1f53ec4d8cb8bc1390a9c0bec428cfb0dddff47b186f40e`;
- stdout SHA256:
  `918b7b6297d5dad25346161323349412e7adf59dc1b0e5472d870d2f5ffde4fc`;
- `run.exit=0`, empty stderr, all ten payload hashes independently
  reverified, directory mode 555 and payload mode 444.

The artifact includes heads, commands, the frozen plan, its contract test,
local target-test output, JSON/Markdown review, stdout/stderr,
`SHA256SUMS`, and `ROOT_SHA256SUMS`. Plan, design, and pointer tests report
`9 passed`.

No model load, inference, simulator run, candidate generation, training,
holdout access, formal seed, claim, promotion, deployment, activation, or DP
modification occurred. The next work is Task 1 test-first causal input and
K=8 pure contracts only.

## Authoritative EOF Pointer

current_v21_status=v21_native_simulator_minimal_tdd_plan_review_passed
current_v21_artifact_source_head=90937b0eda431e1365d41f1f5ef55864568d0a2d
current_v21_prior_gate_final_synced_head=90937b0eda431e1365d41f1f5ef55864568d0a2d
current_v21_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_simulator_minimal_tdd_plan_90937b0e_20260714T155950CST
current_v21_artifact_root_sha256=2625188c0d9346e5d1f53ec4d8cb8bc1390a9c0bec428cfb0dddff47b186f40e
next_work_target=v21_native_simulator_task1_causal_input_and_k8_contracts_tdd_only
