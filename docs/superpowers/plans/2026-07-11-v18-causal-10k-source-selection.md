# V18 Causal nuPlan 10k Source Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a frozen, label-free causal nuPlan 10k manifest with collision-safe multi-decision paths before candidate generation.

**Architecture:** Extend the existing thin v18 orchestrator with one mutually exclusive source-selection mode and one shared record-path helper. Reuse the existing causal adapter, v18 status reader, SHA helpers, manifest loader, candidate exporter, and canonical materializer; add no runner or dependency.

**Tech Stack:** Python 3.12 standard library, NumPy, existing CAMP nuPlan causal adapter, pytest.

## Global Constraints

- Parent manifest SHA256 is `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`.
- Preserve the parent seed-3407 whole-log split and exclude all parent decisions.
- Targets are train/calibration/holdout `6000/2000/2000`; caps are 500/log and 64/scene.
- Selection reads zero expert-future values and makes zero model/candidate/atom/training/evaluation calls.
- K=8, fixed DP, deterministic/MAP baseline, affine/simplex/convex, 32+5 scope, all-K fail-closed, and no-safety-claim contracts do not change.
- Frozen bounded-offline protocol SHA256 remains `54022f480b53d1a036af82f81b4d9124b333bda1971a07122523e9e692a6f94b`.

---

### Task 1: Make record paths decision-unique

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v18_orchestrator.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v18.py`

**Interfaces:**
- Produces: `_record_npz_relative(row: Mapping[str, Any]) -> Path`
- Consumers: candidate export and canonical materialization.

- [ ] **Step 1: Write the failing tests**

Add a test asserting two rows with the same split/log/scene and different
decision tokens map to distinct paths ending in
`scene__decision_a.npz` and `scene__decision_b.npz`. Update the existing real
candidate-export assertion to expect `scene__decision.npz`.

- [ ] **Step 2: Run RED**

Run:
`python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -k "record_npz_relative or run_manifest_writes_single" -q`

Expected: failure because `_record_npz_relative` does not exist and the current
export path is scene-only.

- [ ] **Step 3: Implement the minimum helper**

```python
def _record_npz_relative(row: Mapping[str, Any]) -> Path:
    return (
        Path(str(row["split"]))
        / str(row["log_token"])
        / f'{row["scene_token"]}__{row["decision_token"]}.npz'
    )
```

Use it at the two existing candidate/canonical output-path sites only.

- [ ] **Step 4: Run GREEN**

Run the RED command again, then the complete v18 orchestrator test file.
Expected: all selected tests and the complete file pass.

### Task 2: Add deterministic causal-10k manifest selection

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v18_orchestrator.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v18.py`

**Interfaces:**
- Produces: `run_causal_10k_selection(args: argparse.Namespace) -> dict[str, Any]`
- CLI: `--causal_10k_manifest_output`, plus existing manifest/SHA/DP/status/audit inputs.

- [ ] **Step 1: Write a failing selection test**

Create a minimal read-only SQLite fixture containing `scene`, `lidar_pc`, and
`scenario_tag`; use two decisions in one scene and patch the existing adapter
to return finite causal v2 inputs. Lower selection targets/caps through module
constants in the test. Assert parent decisions are excluded, identities and
paths are new, split is inherited, causal hashes are stored, and label/model
functions are never called.

- [ ] **Step 2: Run RED**

Run:
`python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -k causal_10k_selection -q`

Expected: failure because the selection entrypoint is absent.

- [ ] **Step 3: Implement the minimum selection mode**

Add constants for the parent SHA, exact split targets, 500/log, and 64/scene.
Read and verify the parent manifest; enumerate buffered distinct official tags;
exclude parent decisions; sort by the frozen identity hash; causally
materialize/validate each attempted tick; accept until each split target is
met subject to caps. Atomically write the manifest, rejection sidecar, and
summary only after all invariants pass. Store the controller pointer and zero
label/model/candidate counters.

- [ ] **Step 4: Make CLI modes mutually exclusive**

Selection mode requires manifest, expected manifest SHA, output manifest,
current status, v18 audit, and fixed DP repo. It rejects checkpoint/args,
candidate-root/materialization, refresh, execution, and candidate output
inputs. Route `main()` to selection before the existing two modes.

- [ ] **Step 5: Run GREEN and regression suites**

Run:

```text
python -m py_compile scripts/integrations/run_diffusion_planner_dp_camp_v18.py
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
python -m pytest camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py -q
git diff --check
```

Expected: all tests pass and diff check is clean.

### Task 3: Execute and review the source-selection gate

**Files:**
- Modify: `docs/diffusion_planner_v18_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md` only inside `Current V18 Status`

**Interfaces:**
- Consumes: committed orchestrator, parent manifest/SHA, fixed protocol/SHA.
- Produces: immutable AutoDL source-selection artifact and reviewed 10k manifest.

- [ ] **Step 1: Commit, push, and ff-only sync implementation**

Commit only the spec, plan, orchestrator, tests, audit, and V18 status changes.
Push `main`, then fast-forward AutoDL after rechecking tracked-clean CAMP/DP
HEADs and no active v18 job.

- [ ] **Step 2: Run AutoDL preflight**

Recheck `df -B1 /root/autodl-tmp`, require at least 10 GiB free, no partial or
existing 10k output, fixed DP HEAD, parent/protocol SHA, current pointer, and
zero active relevant jobs. Run py_compile and the focused/v18 causal suites.

- [ ] **Step 3: Execute selection once**

Invoke the committed orchestrator selection mode with explicit parent manifest,
expected SHA, status/audit paths, and a new artifact-local manifest output.
Capture HEADS, COMMAND, stdout, stderr, exit, wall time, JSON/MD, SHA256SUMS,
and root SHA. Do not start candidate generation.

- [ ] **Step 4: Independently review**

Without calling the adapter or labels, re-open the source databases and verify
all 10,000 identities/timestamps/tags, parent-scene membership, parent-decision
exclusion, exact split counts, caps, overlap, causal hashes, failure records,
protocol SHA, and zero forbidden calls. Fail closed on any mismatch.

- [ ] **Step 5: Record and checkpoint**

Append the passed/rejected evidence to the v18 audit, update only the named V18
status section, run the status-pointer regression plus v18 suites and
`git diff --check`, then commit/push/AutoDL ff-only sync. Re-read audit EOF;
only a passed review may authorize fixed-DP K=8 generation preflight.
