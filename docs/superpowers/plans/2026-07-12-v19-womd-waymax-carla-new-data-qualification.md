# V19 New-Data Qualification Implementation Plan

> **Execution:** Run inline on the approved current `main` with TDD and small
> verified commits. No data/simulator download or execution is part of this
> plan.

**Goal:** Produce an independently reviewable fail-closed qualification of
WOMD/Waymax and the CARLA fallback without changing DP, candidates, atoms,
weights, protocols, or claims.

**Architecture:** Add one pure, standard-library qualification script. It
loads a frozen official-source evidence JSON, applies six conjunctive gates,
and renders JSON/Markdown. The execution artifact records live heads, disk,
commands, source hashes, and SHA manifests.

## Task 1: TDD the qualification decision

**Files:**
- Create `camp_core/tests/test_diffusion_planner_v19_new_data_qualification.py`
- Create `scripts/integrations/audit_diffusion_planner_dp_camp_v19_new_data_qualification.py`

1. Write tests requiring WOMD to fail on the 1+8 versus 3+8 contract, CARLA to
   fail when its compressed archive exceeds floor-preserving headroom, unknown
   gates to fail closed, and taxonomy/baseline naming to remain frozen.
2. Run `py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_new_data_qualification.py -q`
   and confirm RED because the module is absent.
3. Implement only `qualify_source`, `build_report`, rendering, and a CLI that
   reads evidence JSON and writes result JSON/Markdown.
4. Re-run the focused test GREEN and run `py -3.12 -m py_compile` on the script.

## Task 2: Freeze and execute the read-only preflight

**Files:**
- Create `docs/superpowers/evidence/2026-07-12-v19-new-data-qualification-input.json`

1. Record official URLs, proto SHA256 receipts, WOMD window/schema facts,
   Waymax capability/access facts, CARLA release URL/content length, live free
   bytes, and the 10 GiB floor.
2. Run the audit locally into a temporary directory and independently recompute
   the history and disk decisions from the JSON.
3. Verify no WOMD/CARLA data/runtime was created and no simulator/metric job ran.

## Task 3: Seal AutoDL evidence and advance the pointer

**Files:**
- Modify `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`
- Modify `docs/diffusion_planner_current_status.md`
- Append `docs/diffusion_planner_v19_iteration_audit.md`

1. Push the tested code/spec/plan checkpoint and ff-only sync AutoDL.
2. Run exactly one audit artifact on AutoDL with `HEADS`, `COMMAND`, stdout,
   stderr, exit, JSON/MD, input receipt, `SHA256SUMS`, and root digest.
3. Independently verify all hashes and the two hard failures without executing
   a simulator or accessing a holdout.
4. Change the checked-in pointer expectation to the new exact tuple, observe
   RED, then update the named Current V19 section and append-only audit to make
   it GREEN.
5. Run pycompile, focused qualification tests, v18/v19 pointer tests, and
   `git diff --check` locally and on AutoDL; commit/push/ff-only sync.
6. Re-read the live EOF and stop at the explicit CARLA large-download,
   additional-disk, and license/source decision boundary.
