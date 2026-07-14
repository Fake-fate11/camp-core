# V21 Native Simulator Paired Closed-loop TDD Plan

> Execute in order on `main`. Use the current branch. After each verified
> slice, commit/push only its files, fast-forward AutoDL, and reread the v21
> EOF before continuing.

**Goal:** Add the smallest CAMP-side adapter that can audit and run a paired
fixed-DP operational-default versus immutable K=8 CAMP selection comparison in
native `scenario_generation.run_route_replay`.

**Architecture:** One pure CAMP integration module owns deterministic hashes,
padding receipts, K=8 latent schedule, immutable-selection checks, and safety
reducers. One thin runner owns temporary native replay hooks, model/runtime
imports, pair orchestration, and evidence writes. Native DP owns scene state,
NPC/TL policies, map refresh, inference semantics, and MPC. No
Diffusion-Planner file is edited.

**Frozen design:**
`docs/superpowers/specs/2026-07-14-v21-native-simulator-paired-closed-loop-design.md`.

**Base:** Gate B final sync will be the commit containing this plan. Fixed DP
is always `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## Global execution rules

For every implementation task:

1. write the failing test;
2. run it and confirm the expected failure, not an environment error;
3. implement the minimum code for that test;
4. rerun the target test and adjacent v19/v21 regression tests;
5. run `py_compile` and `git diff --check`;
6. commit/push only task files, AutoDL `pull --ff-only`, and reread v21 EOF.

No training in Gates C-E. No holdout access. Formal seeds 11/12/13 remain
forbidden. Smoke cannot support a claim. No new dependency, DP change,
candidate rewrite, fallback selection, or parallel simulator framework is
allowed.

## Task 1: Causal input and K=8 contracts

**Files:**

- Create:
  `camp_core/camp_core/integrations/diffusion_planner_v21_native.py`
- Create:
  `camp_core/tests/test_diffusion_planner_v21_native_contracts.py`

### Red

Write tests for:

- deterministic sorted-key dtype/shape/raw-byte input SHA;
- `observed_frames`, `padded_frames`, and
  `padding_policy=native_zero_left_pad_to_31_v1` for 31, short, and long
  histories;
- deletion/rejection of `ego_agent_future`, `neighbor_agents_future`, label,
  outcome, and holdout keys;
- native causal schema validation after selecting the first 32 neighbor slots;
- deterministic per-route/per-tick seed derivation;
- K=8 float32 latent tensor with candidate 0 all-zero and candidates 1-7
  normal at scale 1.0;
- no mutation of global Python/NumPy RNG state;
- candidate 0 exact identity checks and candidate tensor before/after SHA
  checks.

Run and require missing-module/function failures:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_contracts.py -q
```

### Green

Implement only pure functions and small frozen constants. Reuse
`CAUSAL_DP_INPUT_SCHEMA`, `validate_causal_dp_input`, and the v19 array hash
format where compatible. Do not import the remote DP repository from this
module.

Required public helpers:

- `causal_input_receipt(...)`;
- `deterministic_array_mapping_sha256(...)`;
- `candidate_seed(...)`;
- `candidate_latents(...)`;
- `verify_default_candidate0_identity(...)`;
- `verify_candidate_tensor_immutable(...)`.

Run:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_contracts.py tests/test_diffusion_planner_v19_dp_worker.py -q
py -3.12 -m py_compile camp_core/integrations/diffusion_planner_v21_native.py tests/test_diffusion_planner_v21_native_contracts.py
cd F:\camp_core-main
git diff --check
```

Commit message: `feat(v21): add native causal contracts`.

## Task 2: Native hook and immutable selection

**Files:**

- Create:
  `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py`
- Create:
  `camp_core/tests/test_diffusion_planner_v21_native_hook.py`
- Modify only if a pure reusable check belongs there:
  `camp_core/camp_core/integrations/diffusion_planner_v21_native.py`

### Red

Use fake tensor dictionaries, a fake fixed model, and a fake replay module.
Test:

- direct output matches the original native batch interpretation;
- candidate 0 reuses the direct output and neighbor bytes, while candidates
  1-7 use only the ego row's isolated latents;
- NPC returned trajectories and default turn-indicator output never change;
- K=8 candidate and candidate-neighbor shapes are exact;
- the existing `materialize_canonical_14d` and `select_camp_candidate` paths
  select an exact indexed copy without mutation;
- missing atom source and all-K infeasibility fail closed without candidate-0
  fallback;
- hook and tracker symbols restore in `finally` on success and exception;
- source/signature/hash mismatch fails before model call;
- per-segment latency is finite and nonnegative.

Run and require failures because the runner does not exist:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_hook.py -q
```

### Green

Implement a signature-compatible callable and context manager. Reuse native
`to_model_tensors`, native tensor concatenation semantics, existing v19 fixed
model loader, canonical 14D materializer, and affine selector. Do not copy
`run_route_replay`.

The hook must expose a one-tick receipt with input/default/candidate/atom/
selected SHA values, source masks, scores, RNG digests, and latency. It returns
only native operational NPC outputs plus the selected ego trajectory.

Run:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_hook.py tests/test_diffusion_planner_v21_native_contracts.py tests/test_diffusion_planner_v19_dp_worker.py -q
py -3.12 -m py_compile ..\scripts\integrations\run_diffusion_planner_dp_camp_v21_native.py camp_core\integrations\diffusion_planner_v21_native.py
cd F:\camp_core-main
git diff --check
```

Commit message: `feat(v21): add native replay selector hook`.

## Task 3: SafetyCost Native v1 materialization

**Files:**

- Modify:
  `camp_core/camp_core/integrations/diffusion_planner_v21_native.py`
- Create:
  `camp_core/tests/test_diffusion_planner_v21_native_metrics.py`

### Red

Write table-driven pure tests for:

- collision-any from realized OBB clearance `<=1e-6 m`;
- noncollision near-miss rate only on `(1e-6, 2.0]`;
- native Lanelet2 five-point drivable coverage through an injected
  point-inside callback, including an outside center/corner;
- wrong-way moving/on-road denominator and wrapped route direction;
- exact 2D segment intersection for red regulatory stop lines;
- exact speed-limit rate and missing-limit failure;
- constant-velocity diagnostic TTC naming and finite behavior;
- route/comfort summaries at 0.1 s;
- the frozen SafetyCost formula and missing/zero-denominator failures;
- paired delta and better/tie/worse with tolerance `1e-12`.

Run and require missing-helper failures:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_metrics.py -q
```

### Green

Implement only NumPy/math reducers. Native geometry extraction remains in the
runner; the pure module accepts current-state records and exact source results.
Do not add Shapely or rename the five-point proxy as full polygon coverage.

Run:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_metrics.py tests/test_diffusion_planner_v19_closed_loop_evidence.py -q
py -3.12 -m py_compile camp_core/integrations/diffusion_planner_v21_native.py tests/test_diffusion_planner_v21_native_metrics.py
cd F:\camp_core-main
git diff --check
```

Commit message: `feat(v21): add native safety reducers`.

## Task 4: Paired runner and frozen smoke config

**Files:**

- Modify:
  `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py`
- Create:
  `configs/diffusion_planner_v21_native_smoke.json`
- Create:
  `camp_core/tests/test_diffusion_planner_v21_native_runner.py`

### Red

Write a fake-native-replay integration test that proves:

- all required checkpoint/args/selector/route/map/source hashes are exact;
- config explicitly contains every native `SpawnConfig` field and freezes
  `advance_mode=mpc`, `mpc_horizon_steps=20`, `mpc_n_knots=5`,
  `sequential_inference=false`, `sg_smooth_enabled=false`,
  `dump_npz_dir=null`, `reward_config_path=null`, and `max_steps=64`;
- route hashes are exactly sample smoke and TL 59-to-86;
- seeds are 3417/3418/3419 and exclude formal seeds;
- fresh DP then CAMP arms share exact initial state/config/seed receipts;
- post-divergence arm inputs may differ but remain causal;
- partial/duplicate tick receipts, missing metrics, source failures, or arm
  failure invalidate the pair;
- stdout, stderr, JSON, Markdown, per-tick/per-arm/per-pair receipts,
  SHA256SUMS, and root SHA are written atomically without overwriting evidence;
- smoke result always serializes `claim_authorized=false`.

Run and require missing-config/runner failures:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_runner.py -q
```

### Green

Implement the smallest CLI with `--preflight`, `--capability-smoke`, and
`--paired-smoke`. Reuse the native replay result and existing SHA helpers.
Keep output creation single-use and fail if the target exists.

Run:

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_native_runner.py tests/test_diffusion_planner_v21_native_hook.py tests/test_diffusion_planner_v21_native_metrics.py tests/test_diffusion_planner_v21_native_contracts.py -q
py -3.12 -m py_compile ..\scripts\integrations\run_diffusion_planner_dp_camp_v21_native.py
cd F:\camp_core-main
git diff --check
```

Commit message: `feat(v21): add paired native smoke runner`.

## Task 5: Gate D capability smoke

**Files:**

- Modify only the v21 audit/current pointer tests and docs after evidence:
  `camp_core/tests/test_diffusion_planner_v21_iteration_audit.py`
  `docs/diffusion_planner_v21_iteration_audit.md`
  `docs/diffusion_planner_current_status.md`

### Preflight

At live synchronized HEAD, verify no related task, fixed DP/source hashes,
frozen assets, CUDA, disk, runtime imports, sample route/map, config, and target
absence. On AutoDL run the complete target suite without model load first:

```bash
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/Diffusion-Planner:/root/autodl-tmp/Diffusion-Planner/diffusion_planner \
  /root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_v21_native_contracts.py \
  camp_core/tests/test_diffusion_planner_v21_native_hook.py \
  camp_core/tests/test_diffusion_planner_v21_native_metrics.py \
  camp_core/tests/test_diffusion_planner_v21_native_runner.py -q
```

### One-tick execution

Run one CAMP-arm tick on `sample_map_smoke_route.pkl`, seed schedule 3417/3418,
without training or holdout. Acceptance requires:

- model load at fixed checkpoint/config hashes;
- one full 31-frame receipt or honest native padding metadata;
- direct native default and independent candidate 0 exact identity;
- K=8 finite candidate tensor and candidate-specific neighbor predictions;
- complete causal 14D atoms and at least one feasible candidate;
- candidate bytes unchanged before/after atom/selection;
- selected bytes exactly indexed;
- global RNG state unchanged by K=8 work;
- `run.exit=0`, empty unexpected stderr, all payload hashes, and root SHA.

If any scientific acceptance check fails, preserve the artifact and stop. Do
not rename, repair, or retry with changed semantics.

After one independent result review, append only the verified receipt and next
target to v21 docs, run pointer tests, commit/push, AutoDL fast-forward, and
reread EOF.

Commit message: `docs(v21): record native capability smoke`.

## Task 6: Gate E tiny paired smoke

**Files:**

- No implementation change unless a test-first harness defect is found inside
  the frozen contract.
- Modify v21 audit/current pointer tests and docs only after evidence.

### Preflight

Reverify all live heads/hashes, no related task, Gate D root, config/route/map
hashes, target absence, disk, CUDA, and target tests. Do not repeat Gate D if
its exact exit/SHA/root is already complete.

### Execution

Run DP then CAMP for exactly two existing routes, two arms per route,
`scenario_seed=3417`, candidate root 3418, native MPC, and `max_steps=64`.
No training in Gates C-E, no holdout access, and no formal seed.

Acceptance requires:

- identical paired initial receipts and explicit native config;
- every executed tick has complete input, candidate, atom, selector, tracker,
  safety, and latency receipts;
- both arms use native operational NPC/TL/map/tracker behavior;
- SafetyCost Native v1 raw counts, denominators, components, and totals;
- route/comfort/clearance/TTC diagnostic and latency summaries;
- two per-pair deltas plus better/tie/worse, mean, and median;
- padding strata;
- complete immutable artifact and root SHA.

Perform an independent result review that recomputes SHA chains, component
formula, pair deltas, and no-claim fields. Smoke cannot support a claim even if
CAMP is numerically better. Only a passing review may preregister Gate F mini
split/size; it may not start mini evaluation in the same gate.

Commit message: `docs(v21): record paired native smoke`.

## Completion checks for every slice

```powershell
cd F:\camp_core-main\camp_core
py -3.12 -m pytest tests/test_diffusion_planner_v21_iteration_audit.py tests/test_diffusion_planner_v21_native_design.py tests/test_diffusion_planner_v21_native_tdd_plan.py -q
cd F:\camp_core-main
git diff --check
git status --short --branch --untracked-files=no
```

Before each push, summarize the exact files and checks. Never stage unrelated
untracked files. After push, local HEAD, `origin/main`, GitHub `main`, and
AutoDL CAMP must match; DP must remain fixed and tracked-clean.
