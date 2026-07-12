# V19 nuPlan Adapter and Executable DP-default Provenance TDD Plan

> **For agentic workers:** Execute task-by-task on the current `main` branch. The user's v19 controller already authorizes inline TDD execution; do not request another plan or implementation approval.

**Goal:** Add the smallest CAMP-side, test-first adapter that lets official nuPlan v1.2 request either the fixed Diffusion Planner default deterministic/MAP trajectory or a CAMP selection from that same fixed model's K=8 tensor, while proving the default trajectory's executable provenance and preserving every fixed-candidate boundary.

**Architecture:** Keep official nuPlan v1.2 in `/root/autodl-tmp/camp_v19_nuplan_env` and fixed DP in the unchanged `/root/autodl-tmp/dp312_venv`. The nuPlan `AbstractPlanner` subclass converts current `PlannerInput` plus frozen `PlannerInitialization` into the existing causal DP schema, writes one atomic NPZ+JSON request, invokes one fixed-DP worker process with an argument list, validates one atomic NPZ+JSON response, and uses official `transform_predictions_to_states` plus `InterpolatedTrajectory`. No socket, pickle, service, new dependency, DP edit, or trajectory rewrite is needed.

**Tech Stack:** Python standard library, NumPy, existing CAMP causal materializer/14D atom code, fixed DP PyTorch runtime, official nuPlan v1.2 APIs.

## Frozen evidence and naming

- CAMP local/GitHub/AutoDL starting HEAD: `47497ef353b5c0df1a0c6cef08031444e88ae793`.
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Official nuPlan source HEAD: `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`.
- Minimal runtime artifact/root: `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_d85ea23b_20260712T133356CST` / `816367a0eec1b0e0563a1d09c0b8b988f9d407bef3f99678bd01ebc2d1f83f8c`.
- Independent runtime review artifact/root: `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_result_review_d85ea23b_20260712T160605CST` / `4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031`.
- Fixed selector root: `/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_static_14d_train_calibrate_79c9570b_0c22f85e`; root `afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7`; scales `a4122b0fa56912818af92eacf90449633addf9872966aed975317b4307076952`; weights `922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134`.
- Source-provenance evidence root: `8d860e61165f77cc0893ad17199970f833b41be2a4d2696dd168d789f929a791`. It freezes decoder, deterministic converter, replay consumer, and ROS source SHA256 values `8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd`, `af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7`, `de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e`, and `3341028ca11f45e73b7b43ab49dbf38980711f422dccfdb2f816f301443a5f53`.
- The only authorized baseline name is `DP-default deterministic/MAP baseline`. `candidate 0` is a fixed-DP deterministic/MAP reference; `native_ranked_top1=false`. Equality with the default output must not rename it native Top-1 or establish a native K-ranking path.

## Frozen bridge contract

Each tick uses a fresh, explicitly named directory under the future run artifact. The simulator writes `request.npz` and `request.json.tmp`, fsyncs, then replaces the JSON with `request.json`; the worker does the same for `response.npz` and `response.json`. Only the JSON file is the readiness marker. Readers reject missing, extra, stale, mismatched, non-finite, wrong-shape, or wrong-hash fields.

`request.npz` contains exactly `CAUSAL_DP_INPUT_SCHEMA`. `request.json` contains `schema_version`, `arm` (`dp_default` or `camp`), `run_key`, `log_name`, `scenario_token`, `iteration_index`, `simulation_time_us`, `causal_input_sha256`, the three frozen source HEADs, selector hashes for the CAMP arm, and deterministic per-tick seed provenance. It contains no expert future, closed-loop outcome, label, metric, or holdout payload.

The worker response contains the unchanged selected local trajectory `[80,4]` and its SHA. The CAMP response additionally contains candidates `[8,80,4]`, neighbor predictions `[8,32,80,4]`, neighbor-valid `[32]`, signal/physical-feasibility masks `[8]`, candidate reasons, atom matrix `[8,14]`, selected index, pre-score and post-score candidate SHA, and affine/simplex selection evidence. The DP-default response contains the direct zero-latent default output and, only in provenance mode, the independent deterministic/MAP reference plus both SHAs and maximum elementwise difference.

All-K-infeasible or incomplete-source responses are failures: preserve candidates, masks, reasons, and hashes; return no usable selected trajectory; terminate the matched scenario pair; never force candidate 0 and never recompute `progress_shortfall` from all K. Bridge, causal-conversion, DP-inference, atom/selector, and total planning-path durations are recorded separately for later reporting but are not evaluated by this TDD gate.

## Task 1: Lock the pure bridge and run-key contract

**Files:**
- Create: `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py`

- [ ] **Step 1: Write failing tests** for exact request/response keys, NPZ array shapes/dtypes, canonical causal-input SHA, stable paired run keys, `dp_default`/`camp` arm separation, atomic JSON readiness, stale tick rejection, forbidden future/outcome/label fields, formal seed rejection, and response hash validation.
- [ ] **Step 2: Run** `python -m pytest -q camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py` and retain the expected red result.
- [ ] **Step 3: Implement** frozen dataclasses/constants and direct stdlib/NumPy read-write-validation helpers. Use `Path.replace`; do not add a serializer, queue, daemon, socket, or cleanup abstraction.
- [ ] **Step 4: Re-run** the target test and `python -m py_compile camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`.
- [ ] **Step 5: Commit and push** only this verified slice.

## Task 2: Convert official live PlannerInput without future leakage

**Files:**
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py`
- Create: `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`

- [ ] **Step 1: Write failing tests in the official Python 3.9 runtime** using nuPlan `EgoState`, `DetectionsTracks`, `PlannerInput`, and `PlannerInitialization`. Cover exactly 31 causal history states at `dt=0.1`, current-tick 32 dynamic plus 5 static observable objects, mission-route connectedness, real lane boundaries/speed limits, same-tick traffic-light timestamps, goal pose, SE(2) invariance, and deterministic ordering/truncation.
- [ ] **Step 2: Add negative tests** proving any future/label/outcome field, irregular or insufficient history, missing true speed limit/boundary/route source, stale traffic light, disconnected route, unsupported observation, or unavailable required atom source fails closed. A future sentinel perturbation must not change a valid causal request SHA because no future field is accepted.
- [ ] **Step 3: Implement one narrow conversion entry point** that adapts live official objects to the existing `materialize_causal_dp_input` contract. Reuse existing route encoding and source validation; do not read logged future or use nearby-lane/current-speed/zero-value substitutes.
- [ ] **Step 4: Implement `NuPlanCAMPPlanner(AbstractPlanner)`** with `requires_scenario=False`, `observation_type() -> DetectionsTracks`, frozen initialization, one subprocess argument-list call per tick, response validation, and official `transform_predictions_to_states(arctan2(sin, cos), history.ego_states, 8.0, 0.1)` followed by `InterpolatedTrajectory`. It may transform coordinate frames only; it may not smooth, blend, guide, repair, postprocess, or postselect a trajectory.
- [ ] **Step 5: Run** the target test and py_compile in `/root/autodl-tmp/camp_v19_nuplan_env`. Do not construct `Simulation`, call `SimulationRunner.run`, access a holdout, or calculate a metric.
- [ ] **Step 6: Commit and push** only this verified slice.

## Task 3: Implement the fixed-DP worker and executable default provenance

**Files:**
- Create: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py`

- [ ] **Step 1: Write failing fake-model tests** for a direct single zero-latent default call, an independently constructed deterministic/MAP call on byte-identical input, K=8 generation with candidate 0 zero latent and candidates 1-7 at `noise_scale=1.0`, output shapes, immutable tensor hashes, selector artifact hashes, nonnegative simplex weights, affine `score_k(w)=a_k^T w`, feasible-only argmin, and all-K-infeasible failure.
- [ ] **Step 2: Implement one-shot CLI operations** `default_provenance` and `plan_tick`. Reuse `prepare_causal_arrays`, `causal_input_sha256`, `sample_fixed_dp_sources`, fixed-DP planned-red calculation, `materialize_canonical_14d`, and frozen selector loading. Do not change DP files, checkpoint, config, guidance, candidates, or `dp312_venv`.
- [ ] **Step 3: Make `default_provenance` require** byte-identical causal inputs, elementwise equality, maximum absolute difference `0.0`, and identical SHA between the fixed commit's executable zero-latent default output `[batch=0, ego=0]` and the independent deterministic/MAP reference. Record source-file, config, checkpoint, input, and output hashes. Failure is terminal and cannot be relabeled.
- [ ] **Step 4: Make CAMP selection hash** the candidate tensor before and after atom/score evaluation and require equality. Use only physical-feasible candidates and the frozen 14D scales/weights. Return no trajectory when canonical eligibility or feasibility fails.
- [ ] **Step 5: Run** fake-model target tests and py_compile locally and in the DP runtime. Loading the real checkpoint or executing the real provenance call belongs to the later executable-provenance preflight/execution gate, not this TDD implementation gate.
- [ ] **Step 6: Commit and push** only this verified slice.

## Task 4: Integrate contracts without running a simulator

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: only the `## Current V19 Status` section of `docs/diffusion_planner_current_status.md`

- [ ] **Step 1: Add contract tests** proving paired arms share the same label-free scenario/seed/initial-state identity while using separate run directories, then may diverge after the first selected trajectory; no cross-arm response is accepted.
- [ ] **Step 2: Add static source tests** for fixed HEADs/source hashes, no candidate-0 native-Top-1 naming, no forbidden seeds, no simulator construction/run, no holdout path, and no metric/SafetyCost/ADE/FDE/latency result generation in the TDD gate.
- [ ] **Step 3: Run** py_compile, the three target files, all v18/v19 pointer/audit tests, the causal adapter/materializer/atom suites, and `git diff --check`.
- [ ] **Step 4: On AutoDL, verify** CAMP/GitHub/AutoDL HEAD agreement, fixed DP/source HEADs and tracked cleanliness, selector/runtime/review hashes, zero related jobs, free bytes at least 10 GiB, official nuPlan imports, and the same tests in their isolated runtimes. Do not execute the adapter, DP checkpoint, simulator, holdout, or any metric.
- [ ] **Step 5: Produce** an immutable TDD result-review artifact with `HEADS`, `COMMAND`, stdout/stderr, exit codes, JSON/MD review, and `SHA256SUMS`; append the audit and set the matching current-status tuple.
- [ ] **Step 6: Commit/push, AutoDL ff-only, rerun verification, and reread the live v19 audit EOF.** Continue only to its next smallest gate; do not infer execution permission from this plan itself.

## Acceptance and stop conditions

The TDD implementation is acceptable only when all unit/contract tests pass in the appropriate isolated runtimes, DP/source/selector/candidate hashes remain fixed, no future/label/outcome field crosses the online bridge, candidate tensors are unchanged, all-K-infeasible fails closed, and the executable baseline remains named `DP-default deterministic/MAP baseline` with `native_ranked_top1=false`.

Stop before mutation if a related job is running; any HEAD, source, selector, checkpoint, config, or candidate hash drifts; implementation requires modifying DP or its environment; causal/affine/simplex/convex/zero-overlap boundaries fail; a repair changes the frozen protocol; or the next action requires a large download, old-holdout reopening, Full36/formal seeds, promotion, deployment, activation, model replacement, or a broad native-Top-1/real-world safety claim.

This plan authorizes no simulator execution, holdout access, adapter execution, real checkpoint inference, safety/ADE/FDE/latency metric generation, or scientific claim by itself.
