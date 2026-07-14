# V22 Native Route-family Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train and evaluate a v22 CAMP affine/simplex selector over the fixed native DP K=8 tensor using leakage-safe route-family splits, retained failures, and paired closed-loop SafetyCost.

**Architecture:** Extend the existing shared causal materializer, v19 selector, and `run_diffusion_planner_dp_camp_v21_native.py` hook behind an explicit v22 policy whose defaults preserve v21 behavior. Add focused v22 metric, split, corpus, training, and statistics helpers; all native execution continues through the existing scenario-generation hook, with no parallel native runner.

**Tech Stack:** Python 3.12, NumPy, pytest, Lanelet2 native map sources, CVXPY/CLARABEL through `robust_margin_master.py`, Git, SHA256 evidence manifests, AutoDL fixed DP runtime.

## Global Constraints

- Fixed DP HEAD is `7a1d33da277a1992ec474b5383a0c963c72e04e4`; no Diffusion-Planner file is edited.
- CAMP selects one exact row of the fixed K=8 candidate tensor. Candidate generation, repair, rewrite, blend, smoothing, and postprocessing are forbidden.
- Candidate 0 exact identity and `candidate_tensor_sha256_before == candidate_tensor_sha256_after` are required at every execution gate.
- Scores remain `score_k(w)=a_k^T w`; weights are a nonnegative simplex and the master remains convex.
- Preserve the v21 default behavior. V21 tests and historical artifacts remain unchanged.
- Logical maps may cross splits; route identity, route-family/corridor group, and seed namespace may not.
- Split manifests are frozen before any CAMP or DP outcome. Shared lanelet, overlapping corridor, and topology-family conflicts stay in one connected group.
- Map ID, route ID, or split identity may appear in manifests and receipts only, never in CAMP atoms, features, online input, labels, or DP input.
- Every preregistered route remains present. A hard-invalid route remains in the denominator and failure accounting; no replacement, redraw, retry-selection, or silent skip is allowed.
- Formal seeds 11/12/13 remain forbidden. Full36 remains forbidden.
- Pilot cannot support the final claim. Holdout is opened once only after all freezes.
- Any final statement is limited to unseen route-family/corridor and seed within the two fixed logical maps. There is no unseen-map generalization claim.
- A failed claim gate closes as an honest no-claim; thresholds do not change after outcomes.
- Each code step follows RED then GREEN: write the failing test, run it and confirm the expected failure, implement the minimum, rerun the narrow test, then run the relevant regression set.

---

### Task 1: Source-valid materialization

**Files:**
- Modify: `camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py:543-748`
- Modify: `camp_core/tests/test_diffusion_planner_v18_orchestrator.py:366-585`

**Interfaces:**
- Consumes: existing `materialize_canonical_14d(...)` inputs and canonical 14D schema.
- Produces: `eligibility_policy: str = "v21_physical"`, `source_valid_mask: np.ndarray[bool]`, and `all_k_high_risk: bool` while retaining `physical_feasible_mask` as a risk diagnostic.

- [ ] **Step 1: Write the failing test**

Add this test beside the existing all-K physical-infeasible test:

```python
def test_materialize_v22_keeps_source_valid_all_k_high_risk() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    neighbors[:, 0, :, :2] = candidates[:, None, :, :2][:, 0]
    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
        eligibility_policy="v22_source_valid",
    )
    assert result["canonical_eligible"] is True
    assert result["source_valid_mask"].tolist() == [True] * 8
    assert result["physical_feasible_mask"].tolist() == [False] * 8
    assert result["all_k_high_risk"] is True
    assert result["atom_matrix"].shape == (8, 14)
    assert np.isfinite(result["atom_matrix"]).all()
    assert result["progress_reference"] == pytest.approx(
        result["route_progress"][result["source_valid_mask"]].max()
    )
```

Also assert in the existing v21 test that omitting `eligibility_policy` still
returns `canonical_eligible is False` and
`exclusion_reason == "all_candidates_physically_infeasible"`.

- [ ] **Step 2: Run it and confirm the expected failure**

Run:

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -k 'v22_keeps_source_valid or excludes_all_k_infeasible' -q
```

Expected: the v22 test fails because `eligibility_policy` is not accepted; the
unchanged v21 test passes.

- [ ] **Step 3: Implement the minimum**

Add constants and the keyword parameter:

```python
V21_PHYSICAL_ELIGIBILITY = "v21_physical"
V22_SOURCE_VALID_ELIGIBILITY = "v22_source_valid"

def materialize_canonical_14d(
    *,
    candidates: np.ndarray,
    causal_input: Mapping[str, np.ndarray],
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    signal_mask: np.ndarray,
    planned_red_light_cost: np.ndarray,
    dt: float,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
    eligibility_policy: str = V21_PHYSICAL_ELIGIBILITY,
) -> dict[str, object]:
```

Validate the two policies. After projection and feasibility, compute:

```python
source_valid = signal & source_complete
physical = np.asarray(feasibility["physical_feasible_mask"], dtype=bool).copy()
physical &= source_valid
all_k_high_risk = bool(source_valid.all() and not physical.any())
```

Store both masks. For `v21_physical`, keep all existing early-return rules and
use `physical` for the progress reference. For `v22_source_valid`, return only
when `source_valid.any()` is false, materialize the finite 14D matrix for all
rows, use `source_valid` for `progress_reference`, and set
`canonical_eligible=True`. Route-speed atoms for source-invalid rows remain
finite zero values and those rows are excluded later by `source_valid_mask`.

- [ ] **Step 4: Run GREEN and regressions**

Run:

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -k 'materialize_canonical_14d or materialize_candidate_local_speed' -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py
git diff --check
```

Expected: all selected tests pass; no v21 expectation changes.

- [ ] **Step 5: Commit and push checkpoint**

```powershell
git add -- camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat(v22): separate source validity from risk"
git push origin main
```

### Task 2: V22 affine selection and all-K-high-risk receipts

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py:324-386`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py:144-424`
- Modify: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py:130-205`
- Modify: `camp_core/tests/test_diffusion_planner_v21_native_hook.py:110-225`

**Interfaces:**
- Consumes: Task 1 `source_valid_mask`, `physical_feasible_mask`, and `all_k_high_risk`.
- Produces: `eligibility_mask_name: str = "physical_feasible_mask"` in the shared selector and `selection_policy: str = "v21_physical"` in `NativeCampPredictBatch`.

- [ ] **Step 1: Write the failing selector test**

```python
def test_v22_selector_scores_all_source_valid_candidates_when_all_high_risk() -> None:
    module = _worker()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    atoms = np.ones((8, 14), dtype=np.float64)
    atoms[:, 0] = np.arange(8, dtype=np.float64)
    atoms[6, 0] = -1.0
    materialized = {
        "canonical_eligible": True,
        "atom_matrix": atoms,
        "source_valid_mask": np.ones(8, dtype=bool),
        "physical_feasible_mask": np.zeros(8, dtype=bool),
        "all_k_high_risk": True,
        "candidate_reasons": [("lane_corridor",)] * 8,
    }
    result = module.select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=np.ones(14),
        weights=np.eye(1, 14).reshape(14),
        eligibility_mask_name="source_valid_mask",
    )
    assert result["status"] == "ok"
    assert result["selected_index"] == 6
    assert result["all_k_high_risk"] is True
    assert result["candidate_sha256_before"] == result["candidate_sha256_after"]
```

Add a hook test that supplies all-true `source_valid_mask`, all-false physical
mask, `selection_policy="v22_source_valid"`, and asserts the hook returns the
affine argmin, records `all_k_high_risk=True`, and does not force candidate 0.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v21_native_hook.py -k 'v22_selector or all_k_high_risk' -q
```

Expected: FAIL on the missing policy keywords.

- [ ] **Step 3: Implement the minimum shared selector change**

Add the selector keyword and a two-value allowlist:

```python
def select_camp_candidate(
    *,
    candidates: np.ndarray,
    materialized: Mapping[str, Any],
    atom_scales: np.ndarray,
    weights: np.ndarray,
    eligibility_mask_name: str = "physical_feasible_mask",
) -> dict[str, object]:
    if eligibility_mask_name not in {"physical_feasible_mask", "source_valid_mask"}:
        raise ValueError("unknown eligibility mask")
```

Use the named mask only for score masking. Always return both masks and
`all_k_high_risk`; do not add fallback logic. Existing callers omit the new
keyword and retain v21 behavior.

Add `selection_policy` to `NativeCampPredictBatch`. Map it to Task 1's
`eligibility_policy` and to the selector mask. The v22 hook receipt must include
`source_valid_mask`, `physical_feasible_mask`, `all_k_high_risk`, selected row
SHA, and unchanged tensor SHA. The default remains `v21_physical`.

- [ ] **Step 4: Run GREEN and full hook regression**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v21_native_hook.py camp_core/tests/test_diffusion_planner_v21_native_runner.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py
git diff --check
```

Expected: all tests pass, including the old v21 fail-closed tests.

- [ ] **Step 5: Commit and push checkpoint**

```powershell
git add -- scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v21_native_hook.py
git commit -m "feat(v22): select all source-valid candidates"
git push origin main
```

### Task 3: Speed protocol and retained failure rows

**Files:**
- Create: `camp_core/camp_core/integrations/diffusion_planner_v22_native.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_native_metrics.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py:1705-1810`

**Interfaces:**
- Produces: `summarize_speed_protocol(records, dt=0.1)`, `summarize_safety_cost_native_v22(records)`, and `retained_pair_row(...)`.
- The runner selects v22 summaries only when config contains `protocol_version="v22_route_family_v1"`; v21 remains on `summarize_safety_cost_native_v1`.

- [ ] **Step 1: Write the failing metric tests**

Use four on-road ticks with excesses `0.0`, `0.04`, `0.0927605`, and `0.21`
m/s. Assert:

```python
summary = module.summarize_speed_protocol(records, dt=0.1)
assert summary["strict"]["event_count"] == 3
assert summary["sensitivity"]["0.0"]["event_count"] == 3
assert summary["sensitivity"]["0.05"]["event_count"] == 2
assert summary["sensitivity"]["0.1"]["event_count"] == 1
assert summary["sensitivity"]["0.2"]["event_count"] == 1
assert summary["operational_tolerance_mps"] == 0.1
assert summary["continuous"]["magnitude_duration_m"] == pytest.approx(
    0.1 * (0.04 + 0.0927605 + 0.21)
)
```

Add failure-row assertions:

```python
row = module.retained_pair_row(
    pair_key="group-a/route-a/seed-21",
    split="holdout",
    dp_arm={"status": "ok"},
    camp_arm={"status": "failed", "failure_stage": "tracker", "reason": "x"},
)
assert row["included_in_denominator"] is True
assert row["paired_complete"] is False
assert row["failure_class"] == "execution_failure"
```

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_native_metrics.py -q
```

Expected: collection fails because the v22 metrics module does not exist.

- [ ] **Step 3: Implement the minimum metric module**

Use frozen tolerances `(0.0, 0.05, 0.1, 0.2)`. Validate finite nonnegative
speed, positive speed limit, on-road coverage, unique tick IDs, and `dt==0.1`.
Strict uses the existing `speed > limit + 1e-6` rule. Sensitivity uses
`speed > limit + tolerance + 1e-6`. Continuous severity reports maximum
excess, mean excess, excess-duration seconds, and
`sum(excess_mps * dt)` magnitude-duration.

Build `SafetyCost Native v22` by calling the v21 summary for unchanged
collision/near/offroad/wrong-way/red definitions, replacing only the speed
component with the 0.1 m/s operational event rate, and recomputing the same
weights. `retained_pair_row` accepts `ok`, `source_invalid`, and `failed` arm
states; it never drops the row and distinguishes source from execution
failure.

- [ ] **Step 4: Run GREEN and v21 metric regression**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_native_metrics.py camp_core/tests/test_diffusion_planner_v21_native_metrics.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile camp_core/camp_core/integrations/diffusion_planner_v22_native.py scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py
git diff --check
```

- [ ] **Step 5: Commit and push checkpoint**

```powershell
git add -- camp_core/camp_core/integrations/diffusion_planner_v22_native.py camp_core/tests/test_diffusion_planner_v22_native_metrics.py scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py
git commit -m "feat(v22): add operational speed metrics"
git push origin main
```

### Task 4: Route-family/corridor census and split freeze

**Files:**
- Create: `camp_core/camp_core/integrations/diffusion_planner_v22_split.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_split.py`
- Create: `scripts/integrations/build_diffusion_planner_v22_split.py`
- Create: `configs/integrations/diffusion_planner_v22_split_preregistration.json`

**Interfaces:**
- Consumes route records with `identity_sha256`, `logical_map_sha256`,
  `lanelet_ids`, `boundary_ids`, 1 m centerline samples/headings, topology
  complex, entry arm, exit arm, and source-only stratum.
- Produces `build_leakage_groups(routes) -> dict`,
  `freeze_split_manifest(groups, seed_namespaces, targets) -> dict`, and a
  SHA-sealed JSON manifest.

- [ ] **Step 1: Write the failing split tests**

Construct routes A/B sharing a lanelet, B/C sharing a boundary, D/E with 20
one-metre samples within 3 m and parallel heading, and F/G with the same
topology complex plus entry/exit arm. Assert each pair is in one connected
group, transitive A/B/C share a group, and unrelated routes may differ.

Add a manifest test with explicit train/calibration/holdout group and seed
sets. Assert duplicate route identity, group, or seed across splits raises
`ValueError`; map reuse does not. Assert feature-field validation rejects
`map_id`, `route_id`, and `split`.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_split.py -q
```

Expected: collection fails because the split module does not exist.

- [ ] **Step 3: Implement leakage grouping**

Use a small union-find. Add an edge for equal identity, lanelet intersection,
boundary intersection, frozen geometric overlap (1 m samples, at least 20
matched metres, distance at most 3 m, parallel/antiparallel angle at most 15
degrees), or equal `(map_sha, topology_complex, entry_arm, exit_arm)`. Emit
every edge and reason. Group SHA is SHA256 of sorted route identity SHAs.

`freeze_split_manifest` sorts groups by SHA, assigns whole groups with the
frozen source-only target table, and validates disjoint identities, groups,
and seed namespaces. It reports achieved counts and an honest leakage-safe
ceiling before outcomes. Every preregistered pair receives a receipt key; no
post-preregistration replacement API exists.

- [ ] **Step 4: Run GREEN, CLI fixture, and static validation**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_split.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile camp_core/camp_core/integrations/diffusion_planner_v22_split.py scripts/integrations/build_diffusion_planner_v22_split.py
git diff --check
```

Then run the CLI on a checked-in synthetic fixture in the test temporary
directory and verify byte-identical output across two executions.

- [ ] **Step 5: AutoDL source-only census and evidence**

Fast-forward AutoDL, confirm fixed heads and no related process, then run:

```bash
/root/autodl-tmp/dp312_venv/bin/python scripts/integrations/build_diffusion_planner_v22_split.py \
  --config configs/integrations/diffusion_planner_v22_split_preregistration.json \
  --output-dir /root/autodl-tmp/camp_dp_v22_route_family_split_freeze
```

The artifact must contain the full 915-source-route accounting, excluded
pre-preregistration source routes and source-only reasons, leakage edges,
groups, split identities, seed namespaces, target/achieved counts, HEADS,
COMMAND, stdout, stderr, JSON/MD, SHA256SUMS, and ROOT_SHA256SUMS. Stop before
model load if 30 calibration pilot routes or 100 holdout main routes are not
reachable; report the true ceiling without duplicating routes.

- [ ] **Step 6: Commit and push checkpoint**

```powershell
git add -- camp_core/camp_core/integrations/diffusion_planner_v22_split.py camp_core/tests/test_diffusion_planner_v22_split.py scripts/integrations/build_diffusion_planner_v22_split.py configs/integrations/diffusion_planner_v22_split_preregistration.json
git commit -m "feat(v22): freeze route-family splits"
git push origin main
```

### Task 5: Native decision corpus

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py:144-424`
- Create: `scripts/integrations/materialize_diffusion_planner_v22_native_corpus.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_native_corpus.py`

**Interfaces:**
- Adds optional `decision_sink: Callable[[Mapping[str, Any]], None] | None` to
  `NativeCampPredictBatch`.
- Produces one snapshot every five native 0.1 s ticks, with K tensor SHA,
  candidate row SHAs, finite atoms, source-valid/risk masks, causal input SHA,
  offline label provenance, and receipt-only group/split keys.

- [ ] **Step 1: Write the failing corpus tests**

Use the existing fake native hook. Assert ticks 0, 5, and 10 emit exactly
three snapshots; ticks between do not. Assert feature payload keys are exactly
`atom_matrix`, `source_valid_mask`, and `candidate_row_sha256`; map, route,
split, outcome, and receipt IDs occur only in the sidecar. Reject holdout
records and a snapshot whose before/after tensor SHA differs.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_native_corpus.py -q
```

Expected: FAIL because `decision_sink` and corpus helpers are missing.

- [ ] **Step 3: Implement the minimum sink and corpus writer**

Call `decision_sink` only after finite atom materialization and tensor
immutability checks, before the selected trajectory is returned. The corpus
CLI imports `build_native_arm_runner` from the existing v21 native script; it
does not copy `run_route_replay` or create a new native loop. It accepts only
train/calibration manifest rows, samples `tick_index % 5 == 0`, writes each
snapshot once under its content SHA, and retains failed route/seed receipts.

- [ ] **Step 4: Run GREEN and no-parallel-runner guard**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_native_corpus.py camp_core/tests/test_diffusion_planner_v21_native_hook.py -q
rg -n "run_route_replay|while .*tick|advance_scene_mpc" scripts/integrations/materialize_diffusion_planner_v22_native_corpus.py
```

Expected: tests pass and the grep shows only the documented imported runner
boundary, not a copied replay loop.

- [ ] **Step 5: Generate the sealed train/calibration corpus**

Run once on the frozen split manifest. Record route/seed counts, snapshots by
split/stratum/failure, 0.5 s cadence, full SHA receipts, timing, and reachable
learning-curve levels. Holdout rows must be rejected before model load.

- [ ] **Step 6: Commit and push checkpoint**

```powershell
git add -- scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py scripts/integrations/materialize_diffusion_planner_v22_native_corpus.py camp_core/tests/test_diffusion_planner_v22_native_corpus.py
git commit -m "feat(v22): capture native decision corpus"
git push origin main
```

### Task 6: Convex learning curve and calibration freeze

**Files:**
- Create: `scripts/integrations/train_diffusion_planner_v22_selector.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_selector_training.py`
- Reuse unchanged: `camp_core/camp_core/outer_master/robust_margin_master.py`

**Interfaces:**
- Consumes train corpus atoms, source-valid masks, and lower-is-better offline
  `v22_causal_soft_risk_surrogate_v1` candidate costs; physical risk is a
  finite additive penalty, while source-valid remains the only oracle mask.
  It uses `outcome_oracle_and_margins(-cost, source_valid, ...)` and
  `solve_robust_margin_cutting_plane(...)`.
- Produces sealed models for reachable 5k/10k/20k/50k levels and one
  calibration-selected frozen primary model.

- [ ] **Step 1: Write the failing training tests**

Create a synthetic two-record corpus where candidate 2 has lowest cost. Assert
the oracle is candidate 2 after the cost sign conversion. Assert every model
weight is finite, nonnegative, sums to one, and contains solver status/name,
iterations, final gap, cuts, convergence, and wall-clock. Assert holdout or
forbidden ID feature fields raise before solver invocation.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_selector_training.py -q
```

Expected: collection fails because the training script is missing.

- [ ] **Step 3: Implement the minimum trainer**

Sort train snapshots by content SHA and use exact prefixes at
5k/10k/20k/50k. Compute positive atom scales from train only; fail if a scale
is nonfinite or nonpositive. Run the existing static CLARABEL robust-margin
master at each reachable level. Calibration compares only preregistered
levels and freezes model SHA, scales SHA, atom schema, 0.1 m/s primary
tolerance, and claim thresholds. V18 weights are evaluated only as a named
ablation.

- [ ] **Step 4: Run GREEN and solver regression**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_selector_training.py camp_core/tests/test_diffusion_planner_benders_atom_contract.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile scripts/integrations/train_diffusion_planner_v22_selector.py
git diff --check
```

- [ ] **Step 5: Execute and seal the learning curve**

Run every reachable level. Report snapshot/group/map counts, solver
iterations, gap, cuts, status, name, wall-clock, train objective, calibration
metrics, sensitivity at 0/0.05/0.1/0.2 m/s, frozen model/scales/atom hashes,
and V18 ablation. Do not call solver iterations epochs.

- [ ] **Step 6: Commit and push checkpoint**

```powershell
git add -- scripts/integrations/train_diffusion_planner_v22_selector.py camp_core/tests/test_diffusion_planner_v22_selector_training.py
git commit -m "feat(v22): train native convex selector"
git push origin main
```

### Task 7: Capability and pilot preregistration

**Files:**
- Create: `scripts/integrations/evaluate_diffusion_planner_v22_pairs.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_paired_protocol.py`
- Create: `configs/integrations/diffusion_planner_v22_evaluation.json`

**Interfaces:**
- Imports the existing v21 `build_native_arm_runner`; no parallel native
  runner or replay loop is permitted.
- Consumes frozen split/model/scales/config hashes. Produces retained DP/CAMP
  pair rows, per-tick/arm/route receipts, failure accounting, and pilot
  summaries.

- [ ] **Step 1: Write the failing protocol tests**

Use fake arms to assert identical route/map bytes, initial input/state,
scenario seeds, SpawnConfig, fixed DP hashes, and tracker contract. Assert an
arm failure still produces one denominator row. Assert source-valid all-K-risk
selects a nonzero affine argmin without fallback. Assert candidate-0/default
identity, tensor immutability, exact selected-row SHA, and forbidden seed
guards.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_paired_protocol.py -q
```

Expected: collection fails because the evaluator is missing.

- [ ] **Step 3: Implement the thin evaluator**

The evaluator validates all frozen hashes before model load, calls the shared
arm runner once per preregistered arm, writes a row even on exception, and
never substitutes another route, seed, candidate, or arm. Modes are
`capability`, `pilot`, and `main`; `main` requires a freeze receipt and rejects
any prior holdout-open marker. Pilot accepts calibration rows only and sets
`final_claim_authorized=False`.

- [ ] **Step 4: Run GREEN, static review, and preflight**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_paired_protocol.py camp_core/tests/test_diffusion_planner_v21_native_runner.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile scripts/integrations/evaluate_diffusion_planner_v22_pairs.py
git diff --check
```

Run an independent read-only static review over hashes, split overlap,
feature-field denylist, route retention, exact seed sets, expected 90 pilot and
500 main pair keys, and absence of a second native loop.

- [ ] **Step 5: Run capability then the 90-pair pilot**

Run single-tick and tiny multi-route capability first. If hashes, source
validity, tracker, or symmetry fail, preserve the artifact and stop before
pilot. Otherwise execute exactly 30 frozen calibration routes x 3 frozen
non-formal seeds. Report complete failure rows, strata, variance, latency,
route/seed coverage, hard-invalid rate, paired-complete rate, and artifact
roots. Independent review may confirm chain and scale only; pilot cannot
support the final claim and may not open main holdout.

- [ ] **Step 6: Commit and push checkpoint**

```powershell
git add -- scripts/integrations/evaluate_diffusion_planner_v22_pairs.py camp_core/tests/test_diffusion_planner_v22_paired_protocol.py configs/integrations/diffusion_planner_v22_evaluation.json
git commit -m "feat(v22): preregister native paired evaluation"
git push origin main
```

### Task 8: Main holdout, statistics, and closeout

**Files:**
- Create: `camp_core/camp_core/evaluation/diffusion_planner_v22_statistics.py`
- Create: `camp_core/tests/test_diffusion_planner_v22_statistics.py`
- Create: `scripts/integrations/review_diffusion_planner_v22_results.py`
- Modify: `docs/diffusion_planner_v22_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`

**Interfaces:**
- Consumes the immutable 500 planned holdout pair keys and retained result
  rows.
- Produces overall/normal/stress/all-K-high-risk components, secondary
  metrics, cluster bootstrap CI95, coverage/failure tables, independent review,
  and a deterministic claim/no-claim decision.

- [ ] **Step 1: Write the failing statistics tests**

Build synthetic retained rows with map, group, route, and seed cluster keys.
Assert better/tie/worse, mean/median delta, deterministic bootstrap output,
component tables, and separate coverage/hard-invalid/paired-complete rates.
Assert a missing planned key or deleted failure row fails review. Assert claim
passes only when mean delta `<0`, CI95 upper `<0`, better>worse, zero added
collision/red-light pairs, offroad/wrong-way mean deltas `<=0`, their CI95
upper bounds `<=0.005`, and every evidence guard passes.

- [ ] **Step 2: Run it and confirm the expected failure**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_statistics.py -q
```

Expected: collection fails because the statistics module is missing.

- [ ] **Step 3: Implement the minimum statistics and review code**

Cluster resampling draws logical maps, then route-family groups, routes, and
seeds with replacement using the frozen bootstrap seed. The review compares
planned and observed pair-key sets exactly, verifies every nested/root SHA,
HEAD, candidate identity/immutability receipt, split proof, feature denylist,
and arm symmetry. It computes claim gates without changing thresholds and
emits `claim` only for the narrow two-fixed-map scope; otherwise it emits
`honest_no_claim` with every failed gate.

- [ ] **Step 4: Run GREEN and freeze-review preflight**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v22_statistics.py camp_core/tests/test_diffusion_planner_v22_native_metrics.py camp_core/tests/test_diffusion_planner_v22_split.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile camp_core/camp_core/evaluation/diffusion_planner_v22_statistics.py scripts/integrations/review_diffusion_planner_v22_results.py
git diff --check
```

Independent preflight must verify the main evaluator has not run and the
holdout-open marker is absent.

- [ ] **Step 5: Open main holdout once and review**

Execute exactly 100 frozen holdout routes x 5 frozen non-formal seeds unless
the pre-outcome census froze a lower true ceiling. Do not retry failed arms or
replace routes. Seal the execution artifact, then run independent result
review on that artifact only. Report SafetyCost components, secondary
metrics, latency, all strata, better/tie/worse, mean/median delta, cluster
CI95, route/seed receipts, route coverage, hard-invalid rate,
paired-complete rate, execution failures, and all-K-high-risk rate.

- [ ] **Step 6: Record claim/no-claim closeout and push**

Update v22 audit/status with exact HEADS, artifact paths/root SHAs, split and
snapshot counts, solver convergence/timing, pilot/main metrics, review gates,
and the narrow claim or honest no-claim. Preserve all failures and v21 history.

```powershell
git add -- camp_core/camp_core/evaluation/diffusion_planner_v22_statistics.py camp_core/tests/test_diffusion_planner_v22_statistics.py scripts/integrations/review_diffusion_planner_v22_results.py docs/diffusion_planner_v22_iteration_audit.md docs/diffusion_planner_current_status.md
git commit -m "docs(v22): close native safety study"
git push origin main
```

## Plan self-review

- Spec coverage: Tasks 1-3 implement hard-valid/soft-risk, all-K selection,
  speed diagnostics, and retained failures. Task 4 freezes leakage-safe groups.
  Tasks 5-6 generate native training data and train/calibrate the convex
  selector. Tasks 7-8 cover capability, pilot, one-shot main, statistics,
  independent review, evidence, and closeout.
- File boundaries: the existing native hook remains the only simulator path;
  new modules are limited to v22 metrics, split logic, corpus orchestration,
  training, and statistics.
- Type consistency: `source_valid_mask`, `physical_feasible_mask`,
  `all_k_high_risk`, `eligibility_policy`, `selection_policy`, and
  `eligibility_mask_name` have one spelling throughout.
- Scientific boundary: IDs remain receipt-only, v21 defaults stay frozen,
  pilot is non-claim, holdout is one-shot, and unseen-map generalization is
  excluded.
