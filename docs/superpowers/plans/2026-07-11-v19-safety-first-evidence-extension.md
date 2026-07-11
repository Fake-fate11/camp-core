# V19 Safety-First Evidence Extension Implementation Plan

> **Execution mode:** Inline on current `main`, with user-authorized checkpoint commits and AutoDL ff-only synchronization.

**Goal:** Establish an auditable v19 controller and prove or fail closed on the
native-baseline and real closed-loop evidence prerequisites before any
existing-data smoke execution.

**Architecture:** Add a thin v19 status reader rather than copying the v18
orchestrator, preserve v18 history, and generate a single read-only evidence-gap
artifact that reuses existing SafetyCost v1 semantics. Only subsequent EOF
gates may introduce an isolated CAMP-side nuPlan adapter.

**Constraints:** Fixed DP and candidate tensors are immutable; no old holdout
reopening; no trajectory mutation; no Full36 or seeds 11/12/13; no large data
download; no promotion/deployment/activation/model replacement.

---

## Task 1: Bootstrap the v19 controller and claim taxonomy

**Files:**

- Create: `scripts/integrations/run_diffusion_planner_dp_camp_v19.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`
- Create: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`

1. Write failing tests that require the reader to use only the named
   `Current V19 Status` section, reject a status/audit EOF mismatch, and ignore
   historical tail pointers.
2. Run the focused tests and confirm the expected failure.
3. Implement the smallest reader/CLI that returns the current v19 tuple and
   verifies it against the v19 audit EOF.
4. Create the append-only v19 audit qualification entry and prepend the sole
   current v19 pointer section to current status. Preserve all v18 text.
5. Run `py_compile`, focused v18/v19 tests, audit/status tests, and
   `git diff --check`.
6. Commit, push `main`, ff-only update AutoDL, rerun the focused checks there,
   record hashes, and reread v19 EOF.

Expected EOF after this task:

```text
current_v19_status=v19_safety_first_claim_taxonomy_and_controller_bootstrap_passed
next_work_target=v19_native_baseline_provenance_and_safety_evidence_gap_read_only_audit_only
```

## Task 2: Implement the read-only evidence-gap auditor with TDD

**Files:**

- Create: `scripts/integrations/audit_diffusion_planner_v19_safety_evidence_gap.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_safety_evidence_gap.py`
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`

1. Write failing contract tests for the four claim values, exact baseline
   naming, required fixed-DP source hashes, nuPlan capability fields, and
   fail-closed execution/claim booleans.
2. Implement a deterministic, read-only auditor over explicit inputs. Do not
   inspect holdout labels and do not mutate DP or remote data.
3. Run it on AutoDL against live CAMP/DP/data/env state and create JSON/MD,
   `HEADS`, `COMMAND`, stdout/stderr, and `SHA256SUMS`.
4. Independently review the artifact and append its root SHA, provenance
   decision, capability gaps, and next smallest gate to v19 audit/status.
5. Verify locally and on AutoDL, then commit/push/ff-only sync and reread EOF.

## Task 3: Freeze the closed-loop capability plan and static review

**Files:**

- Create or modify only the minimal v19 plan/preflight review files selected by
  the Task 2 result.
- Modify the v19 audit/status pointers.

1. If native/default provenance is unresolved, stop execution and route EOF to
   the smallest provenance remediation only.
2. If provenance is resolved but official nuPlan simulation is unavailable,
   freeze the smallest isolated CAMP-side dependency/adapter plan using the
   existing licensed mini data; do not download new data.
3. Freeze matched arms, scenario/run keys, seeds, initial state, simulator,
   metrics, thresholds, SafetyCost v1, 10,000-replicate cluster bootstrap,
   CVaR90, buckets, hard gates, latency definitions, and failure behavior.
4. Statically review that the plan requires no DP edit and no trajectory
   mutation. Advance only when every check passes.

## Task 4: Execute a minimal existing-data matched closed-loop smoke

**Files:**

- Add only an isolated CAMP-side adapter/harness proven necessary by Task 3.
- Add focused tests and v19 artifact/audit/status updates.

1. Use TDD for input conversion, immutable K=8 tensors, native/default arm
   selection, CAMP selection, paired scenario keys, and metric extraction.
2. Preflight live HEADs, no job, disk, data/license scope, zero-overlap,
   candidate immutability, and frozen protocol.
3. Run one minimal non-formal smoke on existing mini data. Never use formal
   seeds 11/12/13.
4. Independently review SafetyCost v1, official metrics when present,
   secondary trajectory metrics, selector latency, and total path latency.
5. Fail closed on incomplete metrics, candidate mutation, mismatched arms, or
   unavailable simulator execution.

## Task 5: Conditional non-formal scale-up or exact stop

1. Advance only if smoke result review, native/default provenance,
   zero-overlap, immutable candidates, and metric integrity all pass.
2. Run a larger non-formal matched evaluation only within existing authorized
   data and resources.
3. Otherwise emit a scale-up requirements plan with data, disk, runtime,
   dependency, and licensing gaps and stop without downloading new data.
4. Preserve the claim taxonomy: bounded proxy support remains distinct from
   closed-loop support, and no native-Top-1 claim is allowed unless native
   ranking provenance was actually established.
