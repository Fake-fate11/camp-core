# V19 Closed-loop Smoke Speed-complete Reselection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze and independently review two label-free, zero-overlap nuPlan mini smoke scenarios whose official live route windows contain complete real speed limits.

**Architecture:** Reuse the existing v19 smoke constructors and v18 exclusion manifest from one retained AutoDL gate script. The script applies the existing bucket and SHA ordering, adds only the official route-speed eligibility check, and emits a replacement config; a separate read-only review reconstructs the result.

**Tech Stack:** Python 3.9 standard library, existing CAMP nuPlan adapters, official nuPlan v1.2 runtime, pytest pointer contracts, Git.

## Global Constraints

- Keep exactly two smoke scenarios: one normal and one interaction.
- Use only existing Las Vegas/Pittsburgh mini data and official finite positive `speed_limit_mps`.
- Read no expert future, label, safety result, ADE/FDE/miss result, or latency result.
- Keep selection seed `3411`, all metric/threshold/bootstrap seeds, baseline provenance, SafetyCost v1, fixed DP, selector, K=8, and claim taxonomy unchanged.
- Do not run planner compute, worker, simulator runner, or metric engine in this plan.
- Preserve every failed artifact and unrelated untracked file.

---

### Task 1: Deterministic selection and freeze artifact

**Files:**
- Create remotely in the immutable artifact: `select_speed_complete_scenarios.py`
- Consume: frozen v18 manifest and prior v19 `smoke_config.json`
- Produce: `candidate_audit.jsonl`, `selection.json`, `excluded_identity_receipt.json`, `smoke_config.json`, `SHA256SUMS`, `ROOT_SHA256`

**Interfaces:**
- Consumes `construct_nuplan_scenario`, `construct_simulation`, `_map_roadblock`, `_connected_live_lane_path`, and `_polyline` from existing CAMP code.
- Produces two records in the existing `selected_scenarios` schema.

- [ ] **Step 1: Verify immutable inputs and absence of peer work**

Verify CAMP/GitHub/AutoDL agreement, fixed DP/source commits, tracked-clean
state, the v18 manifest SHA, prior selection/config roots, no related process,
and at least 10 GiB free space.

- [ ] **Step 2: Enumerate label-free candidates**

Read only SQLite scene/log/lidar/scenario-tag metadata. Exclude the frozen v18
log and scene identities, retain Las Vegas/Pittsburgh candidates satisfying the
existing bucket, mission-route, and timestamp-coverage rules, and compute:

```python
priority = hashlib.sha256(
    f"3411|{bucket}|{log_token}|{scene_token}|{scenario_token}".encode()
).hexdigest()
```

- [ ] **Step 3: Apply the official route-speed gate in priority order**

For each candidate, use official initialization and the existing route-window
helpers. Reject unless this assertion holds:

```python
assert selected_route and all(
    lane.speed_limit_mps is not None
    and np.isfinite(lane.speed_limit_mps)
    and lane.speed_limit_mps > 0.0
    for lane in selected_route
)
```

Select the first eligible normal record, then the first eligible interaction
record from a distinct log and scene. Fail closed if either is unavailable.

- [ ] **Step 4: Freeze the replacement config**

Copy the prior parsed config, replace only `selected_scenarios`, validate it
with `validate_smoke_config`, and assert every other parsed field is unchanged.
Record zero label/outcome reads and zero compute/runner/metric calls.

- [ ] **Step 5: Finalize immutable evidence**

Write exit codes, manifests, root SHA, and atomically rename the staging
directory. Preserve any failure with its ordered rejection audit.

### Task 2: Independent selection review

**Files:**
- Create remotely in a separate immutable artifact: `review_selection.py`
- Consume: Task 1 artifact plus original v18 manifest/prior config
- Produce: `review.json`, `route_speed_review.json`, `SHA256SUMS`, `ROOT_SHA256`

**Interfaces:**
- Consumes no Task 1 Python imports; it reads Task 1 JSON evidence and rebuilds
  selected official scenario/route objects independently.
- Produces `passed=true` only if every frozen selection invariant holds.

- [ ] **Step 1: Recompute identities, hashes, and ordering**

Recompute both SHA256 values, verify distinct selected logs/scenes, and prove
from `candidate_audit.jsonl` that no lower-priority eligible candidate was
skipped outside the distinct-log rule.

- [ ] **Step 2: Recheck zero overlap and config immutability**

Rebuild the frozen v18 log/scene sets, require empty intersections, and compare
old/new parsed configs after removing only `selected_scenarios`.

- [ ] **Step 3: Reconstruct real route sources**

Independently reconstruct both official current-roadblock route windows and
require finite positive speed limits for every selected slot. Confirm the
recorded lane IDs and speeds match exactly.

- [ ] **Step 4: Finalize the independent review**

Record no label/outcome access and no planner/worker/runner/metric execution,
then finalize the review artifact and root SHA.

### Task 3: Controller and three-end synchronization

**Files:**
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`

**Interfaces:**
- Consumes the passed selection and independent-review roots.
- Produces a current v19 pointer whose next target is the bounded real-source
  execution-preflight retry only.

- [ ] **Step 1: Append audit and update only Current V19 Status**

Record authorization, deterministic selection provenance, two replacement
records, both roots, unchanged protocol/claims, and zero forbidden accesses.

- [ ] **Step 2: Update and run pointer regression tests**

Run the v19 pointer tests plus v18 pointer nodes, py_compile, and
`git diff --check`. The checked-in Current V19 tuple must equal v19 audit EOF.

- [ ] **Step 3: Commit, push, and AutoDL ff-only sync**

Commit only the plan-scoped files, push `main`, source network turbo before the
single AutoDL fetch, pull ff-only, rerun the pointer checks, verify roots and
heads, and reread the live v19 EOF.
