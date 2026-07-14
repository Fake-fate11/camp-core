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

## Task 1: Causal Input and K=8 Pure Contracts

Status: passed.

Gate C was committed, pushed, and fast-forwarded on AutoDL at
`14b1a2394ba3e75ff5744e408f77e71be8f15d1b`. Task 1 then followed the
frozen red/green order. The red test failed only because the planned v21
module did not exist. The minimum CAMP-side module and its tests were added at
source HEAD `abda0bcf5d5874d0994bda4f8187879eaff614f3`.

The pure boundary now:

- copies the native materialized input, deletes only
  `ego_agent_future`/`neighbor_agents_future`, rejects every other future,
  label, outcome, holdout, safety-cost, or metric-result key, and validates
  the existing causal schema after copying the first 32 neighbor slots;
- records source/used/padded/truncated frame counts under
  `native_zero_left_pad_to_31_v1`, per-array shape/dtype/SHA, and a sorted-key
  dtype/shape/raw-C-byte input SHA;
- derives deterministic route/tick candidate seeds and produces local
  float32 K=8 latent tensors with candidate 0 all-zero and candidates 1-7 at
  frozen scale 1.0 without touching global Python or NumPy RNG state;
- fails closed unless direct default and independent candidate 0 have equal
  shape/dtype, exact elements, zero maximum difference, and equal SHA;
- fails closed if the K=8 candidate tensor SHA changes after downstream work.

The local and AutoDL target suites each report `27 passed` across the new 16
contract tests and 11 adjacent v19 worker regressions. `py_compile` and
`git diff --check` passed. AutoDL CAMP and fixed DP were tracked-clean, and no
related v21 run was active.

Immutable Task 1 artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_task1_causal_k8_contracts_abda0bcf_20260714T160847CST`;
- root SHA256:
  `99cef3fed4ff2b570c67f5cea6de5f17ac43db0942bd449c722ba61065eb5447`;
- stdout SHA256:
  `8cdc00a4f27dfc57c269652b3b6c9017e4e4cf5ec4626325e64cac931bff8b3d`;
- `run.exit=0`, empty stderr, all nine payload hashes independently
  reverified, directory mode 555 and every file mode 444.

The artifact contains heads, exact command, stdout/stderr, source and test,
JSON/Markdown review, SHA256SUMS, and root SHA. No model load, inference,
simulator run, candidate trajectory generation, training, holdout access,
formal seed, claim, promotion, deployment, activation, new dependency, or DP
modification occurred. The next work is Task 2 native hook TDD only.

## Task 2: Native Replay Hook and Immutable Selection

Status: passed with fake-model contract tests only.

Task 1 evidence was committed, pushed, and fast-forwarded on AutoDL at
`1e2f750e38cdc957f25ab9bc1c35abd3860a0253`. Task 2 then followed the
frozen red/green order: the red test failed only because the planned runner
did not exist. The minimum thin hook and its tests were added at source HEAD
`4364c149f09203f2a6558155ebb8d6cbb652628b`.

The hook now:

- verifies the exact native `_predict_batch` signature and all five frozen
  replay/simulate/converter/tracker/traffic-light source hashes before patching;
- reproduces native ordered `to_model_tensors` concatenation, direct output-0
  interpretation, and turn-indicator KEEP bias;
- reuses direct ego and first-32 neighbor bytes for candidate 0, then performs
  exactly seven extra calls whose nonzero latent is confined to the ego batch
  row while every NPC batch row remains zero-latent;
- returns the selected exact ego candidate plus byte-identical direct native
  NPC outputs and unchanged direct turn-indicator classes;
- reuses the existing causal 14D materializer/affine selector dependency
  boundary, verifies candidate SHA before/after atom and selector work, and
  fails closed without candidate-0 fallback on missing sources, all-K
  infeasibility, mutation, or non-indexed selection;
- records input/default/candidate/neighbor/atom/selected SHA, source masks,
  scores, global RNG state hashes, and nonnegative segmented latency;
- restores both replay predictor and tracker symbols in `finally` on normal or
  exceptional exit.

The local and AutoDL target suites each report `33 passed`: six new hook
contracts, sixteen Task 1 contracts, and eleven adjacent v19 worker
regressions. `py_compile`, `git diff --check`, and all five live fixed-DP
source hashes passed. AutoDL CAMP and DP were tracked-clean, and no related
v21 run was active.

Immutable Task 2 artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_task2_replay_hook_4364c149_20260714T161856CST`;
- root SHA256:
  `d86d38433a99e13f6429c9498833b85739a4831ea8f340334f9f15be301dba41`;
- stdout SHA256:
  `31cd39c06c07bab1c3cc762d5396cb2fbc7f69e00d5b01b03e5230cba1402a7e`;
- `run.exit=0`, empty stderr, all ten payload hashes independently
  reverified, directory mode 555 and every file mode 444.

The artifact contains heads, exact command, stdout/stderr, runner/core/test,
JSON/Markdown review, SHA256SUMS, and root SHA. Tests use an injected fake
model only. No fixed model load or inference, native simulator run, candidate
trajectory evidence, training, holdout access, formal seed, claim, promotion,
deployment, activation, new dependency, or DP modification occurred. The next
work is Task 3 SafetyCost Native v1 pure reducers TDD only.

## Task 3: SafetyCost Native v1 Pure Reducers

Status: passed.

Task 2 evidence was committed, pushed, and fast-forwarded on AutoDL at
`467004f685fe7f3da8d5fea62ad63360993ebb08`. Task 3 followed the frozen
red/green order: the red test exposed only the missing reducer helpers. The
minimum pure NumPy implementation and tests were added at source HEAD
`ba527d439188617f729a3951038524108d1b2024`.

The reducers now freeze:

- collision at realized OBB clearance `<=1e-6 m` and noncollision near miss
  only in `(1e-6 m, 2.0 m]`, with collision ticks excluded from the near-miss
  numerator;
- the explicitly named center-plus-four-corners five-point drivable proxy via
  an injected native point-inside callback, with no polygon-union claim and no
  Shapely dependency;
- moving/on-road wrong-way using the same five-point coverage result, speed
  `>0.5 m/s`, and a wrapped heading comparison;
- inclusive 2D segment intersection for front-center red stop-line crossing,
  requiring red state at interval start and speed `>0.5 m/s`;
- exact on-road nearest-route-lane speed source and the strict
  `speed > speed_limit_mps + 1e-6` threshold;
- all raw counts, denominators, event ticks, minimum clearance, maximum speed
  excess, the exact frozen SafetyCost formula, and fail-closed missing-source
  or zero-denominator behavior;
- route/comfort summaries at 0.1 s, an explicitly diagnostic constant-velocity
  circle TTC that makes no observed-future claim, and paired CAMP-minus-DP
  better/tie/worse plus mean/median deltas.

There is no second independent `on_road` source: wrong-way and speed-limit
denominators use the exact five-point coverage result. Local target plus
adjacent v19 evidence tests report `49 passed`; AutoDL pure-runtime target and
Task 1/2/v19-worker regressions report `46 passed`. `py_compile` and
`git diff --check` passed. AutoDL CAMP and DP were tracked-clean, and no
related run was active.

Immutable Task 3 artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_task3_safety_reducers_ba527d43_20260714T162656CST`;
- root SHA256:
  `b1cf4a8c7ff6ae21805a520a29d172b60be2e73c135967353ac775cf998d9814`;
- stdout SHA256:
  `bfc80f91be0c90c0f2a426fe601667c39689e2fdf46b6934805f3b2ce8a1124a`;
- `run.exit=0`, empty stderr, all nine payload hashes independently
  reverified, directory mode 555 and every file mode 444.

The artifact contains heads, exact command, stdout/stderr, source/test,
JSON/Markdown review, SHA256SUMS, and root SHA. No Shapely, fixed model load or
inference, native simulator run, candidate trajectory evidence, training,
holdout access, formal seed, claim, promotion, deployment, activation, new
dependency, or DP modification occurred. The next work is Task 4 paired runner
and frozen smoke config TDD only.

## Task 4: Paired Runner and Frozen Native Smoke Configuration

Status: passed without model load, inference, or simulator execution.

Task 3 evidence was committed, pushed, and fast-forwarded on AutoDL at
`12e98803f3f0fa2b0b3eccc1279d8b41756c2496`. Task 4 followed the frozen
red/green order: the first red run exposed the missing config/runner, and the
provenance red run exposed missing sealed `HEADS`, `COMMAND`, and config
receipts. The runner/config implementation was committed at
`b8184a08e59d3fd670fc134836aa84898c2e21e2`; the provenance-only harness fix
produced the artifact source HEAD
`ac9cf98cafa0f27bc30acc7ca51d90f3d96766b8`.

The runner now freezes:

- exact fixed-DP/checkpoint/args/native-source/map/route/selector hashes and
  every native `SpawnConfig` field, including MPC 20/5, disabled SG smoothing,
  no NPZ dump/reward config, traffic lights on, and 64 paired ticks;
- non-formal seeds 3417/3418/3419, exactly two existing frozen routes, and
  fresh arm order DP then CAMP with equal initial state/input receipts;
- native default-only observation for the DP arm and the Task 2 immutable K=8
  causal selector hook only for CAMP, without copying the native replay loop;
- exact `native_zero_left_pad_to_31_v1` receipts, post-divergence causal input
  hashes, candidate/atom/selection/tracker/safety/latency receipts, and
  fail-closed partial, duplicate, asymmetric, missing-source, or failed arms;
- SafetyCost Native v1, secondary metrics, paired CAMP-minus-DP deltas,
  padding strata, and atomic single-use per-tick/per-arm/per-pair evidence;
- `--preflight`, `--capability-smoke`, and `--paired-smoke`, with
  `claim_authorized=false` in every result.

Local and AutoDL target suites each report `43 passed`; `py_compile` and
`git diff --check` passed. AutoDL CAMP and DP were tracked-clean, and no
related v21 run was active. The CLI preflight independently verified all
frozen assets and native source hashes without loading the model. Its artifact
is
`/root/autodl-tmp/camp_dp_v21_native_task4_runner_preflight_ac9cf98c_20260714T165206CST`
with root SHA256
`44a861b85f4335dfbd0dc02e92d7da3ea889c4093539ea4ac616b3b1290a9fc0`.

Immutable Task 4 artifact:

- path:
  `/root/autodl-tmp/camp_dp_v21_native_task4_paired_runner_ac9cf98c_20260714T165318CST`;
- root SHA256:
  `443a2a663347e4b5a825336da96653bc3803dd8fed787f8e721275f402e705a6`;
- `run.exit=0`, empty stderr, all ten payload hashes and the root independently
  reverified, directory mode 555 and every file mode 444.

The artifact contains heads, exact commands, stdout/stderr, runner/test/config,
JSON/Markdown review, SHA256SUMS, and root SHA. No simulator execution occurred;
there is still no real candidate, atom, padding, tracker, safety, or
latency evidence. No model load, inference, training, holdout access, formal
seed, claim, promotion, deployment, activation, dependency change, or DP
modification occurred. The next work is the one-tick Gate D capability smoke;
its scientific checks remain fail-closed and it cannot make a claim.

## Gate D: One-Tick Native Capability Smoke and Independent Review

Status: passed as chain/capability evidence only.

Gate D ran from source HEAD
`11f1421646780b1ffe2a4c0fe7957b17158456d0`; the prior Task 4 docs-sync
HEAD was `4e79dc3999045fb8cd293c0794f2226b64084000`. The fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The successful capability smoke used one frozen sample-route CAMP arm for
exactly one decision tick and one native MPC tracker advance. It recorded
observed / padded frames `31 / 0` under
`native_zero_left_pad_to_31_v1`. Native DP produced exactly K=8 candidates.
The candidate tensor SHA256 before and after atom/selector work was identical:
`86f91da26f61f00a2e73cddab9a900b2526b7781a940dd983cf4649c6290fd1b`.
The independent default and candidate 0 were elementwise equal with maximum
absolute difference zero and shared SHA256
`823b2e604297bf2229e8079999e5d57c0a74949bfdeb0ec91fd41a841de72913`.
This proves default/candidate-0 identity only for the frozen native path; the
native output is not a ranked K=8 tensor, so it is recorded as the operational
default rather than relabelled as a native Top-1 ranking.

All eight candidates had complete native sources and passed the frozen
physical-feasibility mask. The exact 14D atom tensor SHA256 was
`c19bf3b55f2eb2a530a875af967fd8e9e7fc6df6679fb86fd3d09b428d5579ec`.
The affine simplex selector chose selected index 7 with exact selected-trajectory
SHA256 `8a40bcc45bc1dfd106f0e7cd0844b659370888dcf6e51e1b7c3152fa1eaf6239`;
no candidate generation, repair, rewrite, or blending occurred. The legacy
scale artifact omitted a declared schema version, but it was accepted only
because all 14 atom names matched the frozen current schema exactly and its
asset SHA was frozen. This effective contract is explicit in the receipt.

Recorded latency in milliseconds was input 106.553151, independent default
inference 422.988578, K=8 candidate inference 368.754908, atoms 24.487224,
selector 0.120177, tracker 11.344897, native hook total 940.949404, and total
planning 953.220759. These are single-tick smoke measurements, not performance
claims.

The immutable preflight artifact is
`/root/autodl-tmp/camp_dp_v21_native_gate_d_preflight_11f14216_20260714T171247CST`
with root SHA256
`317b3e2410135b72c7a90ceeb7d7b8b55f41571470e5b443636f40f95b6ddab0`.
The immutable capability artifact is
`/root/autodl-tmp/camp_dp_v21_native_gate_d_capability_11f14216_20260714T171247CST`
with root SHA256
`125d14dc3de12bd4bf515f0f00ed5bc31b457e88248f604450142caadb3a83fa`.
Its `run.exit=0`, sealed stderr was empty, and all payload and root hashes were
independently reverified.

Three distinct fail-closed attempts are preserved rather than hidden:

- root `c4aa2f392ec1831bcc00bece1e4f6773e6fe160f95174228129476e383120937`
  stopped before model load because direct script execution could not import
  the repository package;
- root `f812e14178e8920204f9282eb7f97ad016b0078c67abdb91cb7f3ac32407d650`
  stopped in preflight because the exact-name legacy selector scale JSON had
  no schema-version field;
- root `25d729350cb3f57747f988ae17348cb72547ad4289d1f3f0af3984d14e03d868`
  stopped after K=8 inference because the CAMP route projector treated native
  channel 13 as a validity sentinel and rejected valid geometry.

The fixes were surgical: direct-script repository bootstrap, strict legacy
scale compatibility only for the exact current 14-atom name list, and native
route-row validity derived only from the first eight geometry channels. The
last fix was proven red/green and committed at the Gate D source HEAD.

Independent review artifact
`/root/autodl-tmp/camp_dp_v21_native_gate_d_independent_review_11f14216_20260714T171411CST`
has root SHA256
`852c5c2190d828cc6f8825ab0f0edbb211859e941743d8e16600eccdd59a3a1c`.
It reports `26 / 0` checks passed, rehashed the successful preflight and
capability artifacts plus all three failures, verified K=8 shape, candidate
immutability, exact indexed selection, RNG isolation, and default/candidate-0
identity, and reran 77 AutoDL regression tests successfully. Its `run.exit=0`,
sealed stderr was empty, and every payload/root hash was independently
reverified.

No training, holdout access, formal seed, promotion, deployment, online
activation, or DP modification occurred.
Gate D cannot support a safety or CAMP-over-DP claim. The next authorized gate
is the frozen two-route paired
closed-loop smoke, which remains chain evidence only.

## Gate E: Frozen Two-Route Paired Smoke Failed Closed

Status: failed its frozen two-pair acceptance; user decision required before
any contract change or retry.

Gate E ran from final source HEAD
`f04dbeb867b783d211621c52ea2bf2385a6f5733`; the prior Gate D docs-sync
HEAD was `74be718236dfb8b6e50be2b24b7504f2cd990865`. Fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`, no related task was
active, and the frozen Python 3.12 target suite passed `78` tests.

The final asset/source preflight artifact is
`/root/autodl-tmp/camp_dp_v21_native_gate_e_preflight_f04dbeb8_20260714T174548CST`
with root SHA256
`af39edb010c945d73d0e4cb16cc07b5932ea0e46e40dedfba7baa8cdd16b2c80`.
Every fixed checkpoint, args, selector, map, route, native source, and DP HEAD
hash reverified before execution.

The provenance-complete failed paired artifact is
`/root/autodl-tmp/camp_dp_v21_native_gate_e_paired_f04dbeb8_20260714T174548CST`
with root SHA256
`f359cd81786399b377dc5eeb5d423398b4ab678acef8181bc8977c3d30de9eaa`.
Its `run.exit=1`; all payload and root hashes independently reverified. It
contains `HEADS`, exact `COMMAND`, frozen config, native logs, the complete
first pair, the complete second-route DP arm, per-tick receipts, and the exact
failure. In total, `3 / 4 arms` and `1 / 2 pairs` completed, each completed
arm having 64 tracker ticks. All 192 completed ticks recorded `31 / 0`
observed / padded frames, complete safety sources, and no future-derived input.
Every completed CAMP tick retained identical candidate SHA before/after and
exact default/candidate-0 identity.

For the complete `sample_map_smoke_route` pair, the descriptive SafetyCost
DP / CAMP / CAMP-minus-DP values were `0.0 / 7.1875 / +7.1875`, classified
`worse`. DP had zero events in every SafetyCost component. CAMP also had zero
collision, near-miss, offroad, wrong-way, and red-light events, but had 46 / 64
speed-limit-violation ticks, rate 0.71875 and maximum excess 0.0927605 m/s.
Minimum realized OBB clearance was 45.4505 m for DP and 45.4927 m for CAMP.
This single completed pair is not an aggregate result or claim.

Selected secondary values for DP / CAMP were: route completion
0.305987 / 0.308718, route progress 52.6668 / 53.1368 m, distance traveled
51.9168 / 52.3869 m, and mean speed 8.24185 / 8.31685 m/s. Mean absolute
acceleration was 0.125528 / 0.167703 m/s2; mean absolute jerk was
0.432252 / 1.067511 m/s3; mean absolute lateral acceleration was
0.0318142 / 0.0516168 m/s2. Both arms terminated at the frozen 64-tick maximum.

Mean / median latency in milliseconds for that pair was:

- DP total planning 80.8311 / 69.4771, default inference
  69.1071 / 61.6106, and tracker 8.74821 / 7.63985;
- CAMP total planning 538.785 / 528.869, default inference
  60.5999 / 60.3292, K=8 candidate inference 418.039 / 413.471, atom
  materialization 25.2197 / 24.1206, selector 0.118289 / 0.116157, and tracker
  9.40422 / 7.62920.

The second-route DP-only arm completed 64 ticks with SafetyCost 0.0, no hard
event, route completion 0.0486669, progress 24.4276 m, distance 24.0634 m, and
mean speed 3.83854 m/s. Its mean / median total planning latency was
78.3138 / 74.7923 ms, default inference 63.0977 / 61.4645 ms, and tracker
11.3280 / 9.77315 ms. These DP-only values have no paired interpretation.

The frozen `sample_map_tl_route_59_to_86` CAMP arm failed at tick 0. All
`8 / 8 candidates` had complete sources, but every candidate was rejected by
the same `lane_corridor` physical-feasibility condition; the physical mask was
0 / 8. The frozen design explicitly requires an all-K infeasible arm and pair
to fail without candidate-0 fallback. Replacing the route after observing this
outcome, widening or removing the corridor, changing the physical mask, or
adding fallback would change the frozen scientific contract and is not
authorized.

The first failure at source `74be7182...` was sealed at root
`0d36b589ad1b7adfd20bb8d91a35e4d6439bf0de75ff9d5b370e099071507c15`.
A diagnostic-only change preserved per-candidate masks/reasons without changing
selection; the exact failure then repeated at source `6f02ee79...`, root
`f8a7aec4bc39d5ed72986893696ba6c7c5f6243d3fb4f864a079f561e1c5bb91`.
A second harness-only change added failure HEADS/COMMAND/config and partial
receipts; the provenance-complete source and root are the final ones above.
No failed evidence was deleted or overwritten.

Independent failure review artifact
`/root/autodl-tmp/camp_dp_v21_native_gate_e_failure_independent_review_f04dbeb8_20260714T174815CST`
has root SHA256
`032f50f51588abc6a95522cfc07bff5b90ebfb7b7e5aa6239310dced6da1789b`.
It reports `38 / 0` checks passed and independently rehashed all three failure
artifacts plus the final preflight, recomputed SafetyCost, secondary metrics,
latency, pair identity/delta, padding, source completeness, candidate
immutability, and no-claim guards. Its `run.exit=0`, stderr was empty, and the
artifact is immutable.

Gate E failed its frozen acceptance. There is no two-route aggregate,
better/tie/worse table, CI, safety claim, or CAMP-over-DP claim, and Gate F is
not authorized. No training, holdout access, formal seed, promotion,
deployment, activation, DP edit, candidate repair, trajectory rewrite, or
fallback occurred. The next action is a user decision on whether to revise the
frozen Gate E route/feasibility contract; absent that decision, do not rerun.

## Authoritative EOF Pointer

current_v21_status=v21_native_simulator_gate_e_frozen_two_pair_smoke_failed_all_k_lane_corridor
current_v21_artifact_source_head=f04dbeb867b783d211621c52ea2bf2385a6f5733
current_v21_prior_gate_final_synced_head=74be718236dfb8b6e50be2b24b7504f2cd990865
current_v21_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_gate_e_failure_independent_review_f04dbeb8_20260714T174815CST
current_v21_artifact_root_sha256=032f50f51588abc6a95522cfc07bff5b90ebfb7b7e5aa6239310dced6da1789b
next_work_target=user_decision_required_before_v21_gate_e_contract_change_or_retry
