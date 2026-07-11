# V18 Bounded Offline Safety Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Inline execution on current `main`
> is already approved; do not request another execution-choice approval.

**Goal:** Compute and audit an independent bounded offline safety score for the
frozen nuPlan-mini CAMP and fixed-DP baseline selections, then freeze the same
protocol before any causal-10k holdout evaluation.

**Architecture:** Add one read-only runner with evaluate and review modes. It
reuses the v18 materialized split loader, artifact hash verifier, and clustered
bootstrap; it reads immutable selected indices and never reads expert labels or
learned selector weights.

**Tech Stack:** Python 3, NumPy, existing v18 integration helpers, pytest.

## Global Constraints

- Fixed DP remains `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- No model call, candidate mutation, training, label query, claim, promotion,
  deployment, or online activation.
- Score name is `camp_dp_bounded_offline_safety_score_v1`; never call it the
  official nuPlan or closed-loop safety score.
- Formula and thresholds are exactly those in
  `docs/superpowers/specs/2026-07-11-v18-bounded-offline-safety-score-design.md`.
- Mini output is post-hoc descriptive evidence only.

---

### Task 1: Pure Safety Components and Score

**Files:**
- Create: `scripts/integrations/run_diffusion_planner_dp_camp_v18_bounded_safety.py`
- Test: `camp_core/tests/test_diffusion_planner_v18_bounded_safety.py`

**Interfaces:**
- Produces: `trajectory_comfort_pass(candidates, dt) -> np.ndarray`
- Produces: `candidate_safety_components(...) -> dict[str, np.ndarray]`

- [ ] **Step 1: Write failing formula and threshold tests**

Cover a fully compliant candidate, each hard multiplier failure, exact comfort
thresholds, speed/progress/clearance normalization, finite/shape validation,
and the absence of learned weights from the API.

```python
components = candidate_safety_components(
    atom_matrix=atoms,
    candidates=candidates,
    lane_feasible_mask=np.array([True]),
    obb_collision_free_mask=np.array([True]),
    physical_feasible_mask=np.array([True]),
    route_progress=np.array([10.0]),
    progress_reference=10.0,
    minimum_obb_clearance=np.full((1, 80), 3.0),
    planned_red_light_cost=np.array([0.0]),
)
assert components["bounded_offline_safety_score"][0] == 100.0
```

- [ ] **Step 2: Verify RED**

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
python -m pytest camp_core/tests/test_diffusion_planner_v18_bounded_safety.py -q
```

Expected: import failure because the runner does not exist.

- [ ] **Step 3: Implement the minimum pure functions**

Use candidate finite differences for official comfort bounds and implement:

```python
soft = (5*clearance + 4*speed + 5*progress + 2*comfort) / 16
score = 100 * collision * lane * red * making_progress * soft
```

Reject non-finite values, wrong shapes, and missing 14D atom names.

- [ ] **Step 4: Verify GREEN**

Run the focused pytest and `py_compile` for the new runner.

### Task 2: Immutable Mini Evaluation Artifact

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v18_bounded_safety.py`
- Modify: `camp_core/tests/test_diffusion_planner_v18_bounded_safety.py`

**Interfaces:**
- Consumes: frozen canonical/candidate/paired-evaluation roots.
- Produces: `run_evaluate(args) -> dict[str, object]` and an atomic artifact.

- [ ] **Step 1: Write failing read-only artifact tests**

Assert exact hash verification, identity joins, selected/baseline component
rows, no expert fields or label loader, existing-output refusal, and summary
contents including paired better/tie/worse and log/scene CI95.

- [ ] **Step 2: Implement evaluate mode**

Load holdout with `labels_required=False`, verify the paired-evaluation root,
join all 71 identities, compute CAMP and baseline components, and atomically
write:

```text
protocol.json
records.jsonl
summary.json
SHA256SUMS
ROOT_SHA256SUMS
```

Freeze bootstrap seed `3410`, 10,000 replicates, score tie tolerance `1e-9`,
the complete metric constants, and causal-10k pass criteria in `protocol.json`.

- [ ] **Step 3: Verify GREEN and commit**

Run focused pytest, `py_compile`, and `git diff --check`; commit only the runner
and test.

### Task 3: Read-Only Result Review

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v18_bounded_safety.py`
- Modify: `camp_core/tests/test_diffusion_planner_v18_bounded_safety.py`

**Interfaces:**
- Produces: `run_review(args) -> dict[str, object]` and a separate review root.

- [ ] **Step 1: Write failing review tests**

Require source artifact/root match, exact protocol constants, 71 unique rows,
recomputed component values/aggregates/CIs, zero labels, fixed baseline
semantics, and explicit no-claim bounds.

- [ ] **Step 2: Implement review mode**

Recompute from frozen upstream roots in memory, compare every persisted row and
summary field, then write only the review summary and SHA manifests.

- [ ] **Step 3: Verify GREEN and commit**

Run focused pytest, adjacent v18 training/evaluation tests, `py_compile`, and
`git diff --check`.

### Task 4: AutoDL Mini Run, Audit, and 10k Preregistration

**Files:**
- Modify: `docs/diffusion_planner_v18_iteration_audit.md`
- Modify only `## Current V18 Status` in
  `docs/diffusion_planner_current_status.md`
- Test: existing v18 audit/status contract tests plus the new focused tests.

- [ ] **Step 1: Sync and preflight AutoDL**

Verify CAMP/GitHub/AutoDL equality, tracked-clean CAMP/DP, fixed DP HEAD, no
active job, and these immutable source roots:

```text
candidate: 92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028
canonical: 7c89f73e2b26308a42fbd453fff7e0ece4c7d0b49e219a9c56f99bdb2a65d1cc
paired evaluation: 6ca6bdd70497173356277ce4cb6ed5ba23420a99c381c68f44c5e446c3ffd366
```

- [ ] **Step 2: Execute evaluate once and review once**

Use new absent output roots. Do not access nuPlan databases or holdout labels.
Capture `HEADS`, `COMMAND`, stdout/stderr, `run.exit`, and recursive SHA files
in the normal v18 evidence harness.

- [ ] **Step 3: Record result and preregister 10k**

Append exact component/aggregate values, roots, limitations, and the protocol
SHA to the v18 audit. The next target may enter causal-10k source/preflight
work, but no 10k generation or holdout opening occurs in this plan.

- [ ] **Step 4: Final verification and synchronization**

Run local and AutoDL `py_compile`, focused pytest, adjacent v18 tests,
audit/status tests, artifact SHA verification, and `git diff --check`; then
small commit/push and AutoDL ff-only sync.
