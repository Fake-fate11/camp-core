# V21 Native Simulator Paired Closed-loop Design

## Status, interpretation, and assumptions

This design implements the approved v21 direction: compare the CAMP selector
against the fixed DP operational default in TiER IV Diffusion Planner's own
`scenario_generation` route replay. CARLA and official nuPlan simulation are
stopped. V20 is historical and read-only.

The source baseline is CAMP Gate A final synced HEAD
`0937174beead161854b6e273020e53fcca589409`. The Gate A evidence source HEAD
remains `b419acf31eea7323232f117e8009f5eb9e19e318`; these are different roles,
not drift. Fixed DP stays
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Assumptions that Gate C/D must verify before execution:

- the existing Python 3.12 DP runtime has the native Lanelet2 point-in-lanelet
  geometry needed by the frozen drivable-area proxy; no install is authorized
  and there is no Shapely dependency;
- the existing fixed checkpoint, reconstructed fixed args, and v18 corrected
  14D selector hashes remain unchanged;
- a thin CAMP hook can exactly reproduce native `_predict_batch` output bytes
  before it adds K=8 selection;
- the selected existing routes load through the already-audited no-ROS
  projection compatibility shim.

If an assumption fails and the correction would change DP, checkpoint/request
semantics, candidate bytes, simulator dynamics, or the scientific metric
contract, stop for one spec review. Import-path or harness-only defects inside
this frozen design may be fixed without changing the contract.

## Alternatives considered

1. **CAMP-side thin hook around native route replay. Selected.** Keep
   `scenario_generation.replay.run_route_replay`, `SceneContext`, authored
   routes, native NPC manager, traffic-light controller, map refresh, and
   native MPC. Replace only the module-level ego planning callback and wrap
   tracker timing. This is the smallest testable change and leaves DP tracked
   clean.
2. **Copy the native replay loop into CAMP. Rejected.** It would duplicate a
   large evolving loop, create a parallel simulator, and make paired parity
   harder to audit.
3. **Add a selector callback inside Diffusion-Planner. Rejected.** DP
   modification is a hard stop under the fixed-commit contract.

## Architecture

One CAMP runner imports the fixed DP repository with the frozen Python paths,
installs the existing process-local Lanelet2 projection shim, loads the fixed
model through the already-tested v19 loader, creates a fresh builder per arm,
and calls native `run_route_replay`.

The runner temporarily replaces `scenario_generation.replay._predict_batch`
with a signature-compatible CAMP-side thin hook. The hook reuses native
`to_model_tensors`, native map cache, native normalization, the fixed model,
and native output interpretation. A `try/finally` restores the original symbol
after each arm. A second pass-through wrapper times native
`advance_scene_mpc`; it does not change arguments or output.

No DP file is edited. Source SHA guards cover `replay.py`, `simulate.py`,
`tensor_converter.py`, `mpc_tracker.py`, `traffic_light.py`, and the CAMP hook.
A signature or source hash mismatch fails before model load.

## Native operational default and K=8 construction

At every tick, the hook builds the same ordered per-agent tensor dictionaries
as native `_predict_batch`, concatenates them identically, keeps every latent
zero, calls the fixed model once, and obtains the direct operational output
and default turn-indicator logits.

For the CAMP arm only:

1. candidate 0 reuses the direct operational output bytes and its
   candidate-specific neighbor outputs from that same model result;
2. candidates 1-7 use the frozen v18 latent shape, float32 normal noise at
   scale 1.0, and a local `numpy.random.Generator` seeded from the frozen
   per-route/per-tick schedule;
3. only the ego batch row receives the nonzero latent; every NPC row remains
   on its zero-latent native operational policy;
4. seven additional fixed-model calls produce candidate-specific ego and
   neighbor predictions; the original NPC operational predictions remain the
   only trajectories returned for non-ego agents;
5. CAMP selects one complete ego candidate. Default turn-indicator output is
   retained, so CAMP changes only the chosen ego trajectory.

The hook does not call global NumPy/Python RNG for candidate generation. It
records global Python, NumPy, CPU Torch, and CUDA RNG state digests before and
after the extra candidate calls and requires them to match. Thus candidate
work cannot perturb the native NPC, traffic-light, or spawn seed schedule.

Gate D independently calls the unhooked native default and a separate
zero-latent path on the same materialized tick. Exact identity requires equal
shape/dtype, `np.array_equal`, zero maximum absolute difference, and identical
SHA256. Until that passes, the honest name is `DP native operational output-0`,
not native-ranked Top-1. If it passes, receipts may use
`DP operational Top-1 (output-0, exact identity verified)`; they must still
record `native_ranked_k8=false` because the repository has no native K-ranking
stage.

Every tick records `candidate_tensor_sha256_before` before atom work and
`candidate_tensor_sha256_after` after selection. They must match. Selected
trajectory bytes and SHA must equal the indexed candidate exactly.

## Causal history and padding

The native checkpoint input remains 31 frames at 0.1 s. Route replay normally
provides a full native 31-frame synthesized causal history. A source with fewer
frames uses only the native converter behavior:

`padding_policy=native_zero_left_pad_to_31_v1`.

Observed rows remain in original order at the right edge; missing older rows
are all-zero float32 rows. Longer history retains the most recent 31 rows. No
future row, interpolation, future-derived goal, or future-derived route is
allowed.

For each arm/tick, the direct default and every K candidate reuse one
materialized input object. The receipt contains `observed_frames`,
`padded_frames`, `padding_policy`, per-array shape/dtype/SHA, and one
deterministic `input_sha256` over sorted key, dtype, shape, and raw C-order
bytes. At a shared initial state, both arms must have identical input SHA.
After the first divergent action, each arm uses its own causal state and is not
forced to match the other arm.

Padding strata are `0`, `1-5`, `6-15`, and `16-30` padded frames. Padding
records may support chain smoke and directional evidence only. A later claim
requires a preregistered sensitivity result with the full-history stratum
reported separately.

## Atom and selector contract

The first allowed selector is the frozen v18 corrected
`dp_camp_v10_14d` checkpoint:

- selector root SHA256
  `afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7`;
- atom scales SHA256
  `a4122b0fa56912818af92eacf90449633addf9872966aed975317b4307076952`;
- static weights SHA256
  `922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134`.

Its scoring rule remains exactly `score_k(w)=a_k^T w` after frozen positive
atom scaling, with `w` on the nonnegative simplex. The master remains convex.
No rank feature, selected-index feature, candidate mutation, nonlinear model,
or simulator outcome enters the score.

The native causal boundary calls `dump_step_npz(...,
predicted_neighbor_num=32)` in memory, immediately deletes the future
placeholder keys, validates the existing causal schema, and pairs the first 32
candidate-specific fixed-DP neighbor predictions with the same K output.
Authored route lanes, exact speed-limit flags/values, lane boundaries, live
traffic-light state, red stop geometry, current static objects, and the
candidate-0 identity receipt complete the 14D sources.

Each missing or nonfinite source fails closed for that tick. An all-K
infeasible result fails the arm and pair; there is no candidate-0 fallback.
Closed-loop outcomes are forbidden as training, calibration, atom, score, or
online selector inputs.

The v18 weights are accepted for capability/tiny smoke only after schema and
source compatibility passes. Distribution shift means smoke cannot validate
the learned selector. Any later retraining must use a pre-frozen
scene/route/seed zero-overlap train split with open-loop/expert labels only;
calibration and holdout cannot train. Training reports solver iterations,
gap/cuts, and wall-clock, never invented epochs.

## Paired closed-loop protocol

Each pair is keyed by route SHA and non-formal scenario seed. Baseline and
CAMP arms are separate fresh native runs with identical:

- route/map bytes and authored route lanelet sequence;
- initial `SceneContext` receipt and input SHA;
- full explicit `SpawnConfig` JSON;
- scenario seed, NPC policy, spawn schedule, traffic-light seed, tracker,
  map-refresh period, and signal state;
- fixed DP/checkpoint/args and operational-default policy.

Sequential arm order is frozen DP then CAMP. Each native run reseeds all
native RNGs at entry; CAMP's local candidate RNG is isolated. Natural arm
divergence after a different ego action is expected. At every later tick, all
agents in an arm are replanned on that arm's current causal state by the same
fixed DP; only CAMP ego has K=8 reranking.

The native replay config must explicitly include every `SpawnConfig` field.
Critical values are:

- `advance_mode=mpc`, `mpc_horizon_steps=20`, `mpc_n_knots=5`;
- `sequential_inference=false`;
- `sg_smooth_enabled=false`;
- `dump_npz_dir=null`, `reward_config_path=null`;
- `enable_traffic_lights=true`, `map_refresh_steps=5`;
- `max_steps=64`, which makes the post-400-tick nudge unreachable.

The same native MPC tracker consumes each selected reference. Any common
tracker reference postprocessing is downstream actuation. Candidate bytes are
hashed before tracker entry and never replaced with tracker output.

## SafetyCost Native v1

The primary run-level metric is lower-is-better `SafetyCost Native v1`:

```text
100 * collision_any
+ 10 * near_miss_noncollision_rate
+ 20 * offroad_rate
+ 20 * wrong_way_rate
+ 30 * red_light_violation_any
+ 10 * speed_limit_violation_rate
```

Every component lies in `[0,1]`. Missing source, zero denominator, invalid
geometry, or nonfinite value fails the arm and matched pair; it is never
filled with zero.

- `collision_any`: 1 if any native realized ego-to-agent OBB clearance is
  `<=1e-6 m`, else 0.
- `near_miss_noncollision_rate`: evaluated ticks with minimum OBB clearance
  in `(1e-6 m, 2.0 m]` divided by evaluated clearance ticks. Collision ticks
  are excluded to avoid double counting.
- `offroad_rate`: evaluated ticks that fail five-point drivable coverage,
  divided by evaluated drivable-area ticks. The five points are the ego center
  and four exact OBB corners; every point must be inside at least one native
  vehicle-drivable Lanelet2 lanelet. This is an explicitly named footprint
  sampling proxy, not full polygon-union coverage. It uses native Lanelet2
  only, with no Shapely dependency or new install.
- `wrong_way_rate`: moving on-road ticks (`speed>0.5 m/s`) whose ego forward
  vector has negative dot product with the nearest segment of the current
  authored route, divided by evaluated moving on-road ticks.
- `red_light_violation_any`: 1 if the ego front-center state transition
  intersects a regulatory `stopLine` while its native traffic-light group was
  red at interval start and ego speed was `>0.5 m/s`, else 0.
- `speed_limit_violation_rate`: on-road ticks with an exact nearest-route-lane
  speed source and `ego_speed > speed_limit_mps + 1e-6`, divided by evaluated
  speed-limit ticks.

Raw counts, denominators, minimum clearances, maximum speed excess, and event
ticks are mandatory. Native road-border clearance and a constant-velocity
circle TTC diagnostic are secondary and explicitly named as diagnostics; TTC
does not claim observed future collision time.

## Secondary metrics and latency

Report route progress/length/completion, termination reason, stopped fraction,
distance traveled, mean/max speed, acceleration, jerk, yaw rate, lateral
acceleration, road-border clearance, minimum diagnostic TTC, NPC counts, and
traffic-light exposure. ADE/FDE/miss are absent because authored-route replay
has no legal expert GT future.

Use `time.perf_counter_ns()` and retain finite nonnegative milliseconds for:

- native direct-default inference;
- additional candidate inference for candidates 1-7;
- causal conversion;
- atom materialization;
- affine selector;
- native MPC tracker;
- total planning path from hook entry through tracker completion.

Report count, mean, median, p95, and max. Total path is not forced to equal the
sum because Python scheduling and receipt work are included, but it must be at
least each measured child segment.

## Tiny smoke preregistration

Gate E uses only these existing authored routes on the existing sample map:

- `sample_map_smoke_route.pkl`, SHA256
  `b8b5417c3269bbdbe72efe49388d32af04751b25cffcec297a04b25a50140c13`;
- `sample_map_tl_route_59_to_86.pkl`, SHA256
  `dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4`;
- shared no-ROS map SHA256
  `a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036`.

Gate A mentioned route `58_to_55` only as a capability candidate. Before any
simulator result, Gate B rejects it because its start and goal are spatially
adjacent on a looping route and the native goal-pass termination can end the
smoke prematurely. This source-only geometry decision freezes `59_to_86` for
Gate E and is not outcome-driven.

Frozen non-formal seeds are `scenario_seed=3417`,
`candidate_tick_seed_root=3418`, and later descriptive bootstrap seed `3419`.
Formal seeds 11/12/13 are forbidden. There are exactly two paired routes, two
arms per route, and `max_steps=64`. The smoke runs no training and opens no
holdout.

Smoke acceptance proves only:

- both arms start from matching initial receipts and run the native loop;
- direct default/candidate-0 identity and candidate immutability hold;
- every selected tick has complete causal 14D atoms or fails honestly;
- SafetyCost components, secondary metrics, latency, and receipts materialize;
- both pair summaries and evidence roots verify.

The smoke cannot support a safety or CAMP>DP claim. Values are descriptive
even if CAMP is better on both routes.

## Paired statistics and later claim boundary

For every valid pair, define `delta = CAMP - DP` for SafetyCost and every
secondary scalar. Report better/tie/worse with tie tolerance `1e-12`, paired
mean and median delta, and all raw pair receipts. Tiny smoke reports no CI.

After independent smoke review, Gate F may preregister a mini split and exact
sample size before generation. Mini evaluation must use scene/route/seed
cluster bootstrap CI95 and multiple non-formal seeds. At most a bounded native
mini-split directional statement is eligible, and only if:

- every planned pair is present and independently reviewed;
- the SafetyCost delta CI95 upper bound is strictly `<0`;
- collision and red-light hard-event worse-pair counts are both zero;
- median route-completion delta is at least `-0.02`;
- padding strata and full-history sensitivity are reported;
- latency and every preregistered secondary metric are reported without
  selective omission.

These thresholds do not authorize a broad safety, CAMP>DP, deployment,
activation, model-replacement, or real-road claim. Gate G can only plan larger
evidence if the mini gate passes.

## Receipts, failures, and evidence

Per-tick receipts include pair/arm/route/seed/tick, all HEADs and source hashes,
input padding metadata/SHA, direct output SHA, K=8 latent schedule and tensor
SHA, candidate-specific neighbor SHA, atom names/matrix/source mask/SHA,
weights/scales hashes, physical mask/reasons, scores, selected index/SHA,
pre-tracker selected SHA, RNG-state digests, safety state, and latency.

Per-arm and per-pair receipts include explicit config, initial-state SHA,
termination, padding strata, SafetyCost raw counts/denominators/components,
secondary metrics, latency distributions, pair deltas, and missing-source
reasons. Every artifact contains HEADS, COMMAND, stdout, stderr, JSON/Markdown,
SHA256SUMS, and a root SHA.

Fail closed on HEAD/hash drift, running related jobs, hook/native mismatch,
candidate mutation, initial-state asymmetry, future leakage, missing atom or
metric source, all-K infeasibility, RNG perturbation, partial receipt, or
failed command. Preserve failure tails and completed evidence. Do not rerun a
sealed successful gate, delete evidence, force-push, rewrite history, or alter
DP.

## Self-review result

The selected hook is the only option that preserves native simulator
ownership and fixed DP while adding the authorized selector. Self-review found
that Shapely is absent from the frozen DP environment. Before sealing the spec
or observing simulator outcomes, the offroad component was narrowed to the
honestly named native Lanelet2 five-point proxy; no dependency was installed
and no missing source is renamed as full polygon coverage. The design makes
the two known native prediction rewrites unreachable, separates candidate
bytes from common tracker processing, defines short-history behavior without
future leakage, and refuses to rename other missing metrics. The only
pre-outcome route change from Gate A is justified by authored route geometry
and native termination semantics. No ambiguity remains that would change the
scientific conclusion; implementation may proceed to a minimal TDD plan.
