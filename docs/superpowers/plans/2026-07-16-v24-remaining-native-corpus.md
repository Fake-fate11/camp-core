# v24 Remaining Native Corpus Implementation Plan

> **Execution boundary:** this plan's current gate stops after sealed static
> preflight. It does not start the 1,500-run remaining-seed execution.

## Task 1: Freeze row selection with TDD

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v24_native_corpus.py`
- Modify: `scripts/integrations/execute_diffusion_planner_v24_native_corpus.py`

1. Add a failing test proving remaining rows are the exact sorted 375-route
   denominator crossed with seeds `24002-24005` in route-major/seed-minor order.
2. Add failing cases for review authorization, route order, seed namespace,
   denominator preservation, and forbidden tuning/outcome/holdout flags.
3. Implement the smallest shared manifest validator plus pilot and remaining
   row wrappers.
4. Run the targeted row-selection tests.

## Task 2: Parameterize execution without changing pilot behavior

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v24_native_corpus.py`
- Modify: `scripts/integrations/execute_diffusion_planner_v24_native_corpus.py`

1. Add a failing two-route test that schedules eight remaining rows, retains a
   failure, continues, and writes terminal progress.
2. Parameterize writer phase/schema and the shared execution loop.
3. Keep `execute_pilot_manifest` and all pilot schemas/filenames compatible.
4. Add `execute_remaining_manifest` with remaining-specific schemas and
   `remaining_summary.json`.
5. Run pilot and remaining executor tests together.

## Task 3: Add remaining static-preflight CLI

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v24_native_corpus.py`
- Modify: `scripts/integrations/execute_diffusion_planner_v24_native_corpus.py`

1. Add `remaining-execution-preflight` and `execute-remaining` modes.
2. Require and rehash the sealed pilot and pilot-review roots in both modes.
3. Parse the sealed review decision and validate all 1,500 run configs without
   constructing the native runner in preflight mode.
4. Record exact counts, seeds, row-order SHA, 96,000 ceiling, closed boundaries,
   and all four source roots in the evidence files.
5. Test that preflight reports model/simulator/candidate execution as false and
   refuses missing or drifted review evidence.

## Task 4: Verify and seal the AutoDL preflight

**Files:**
- Modify: `docs/diffusion_planner_v24_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`

1. Run local py_compile, targeted pytest, all v24 tests, and `git diff --check`.
2. Commit and push the implementation checkpoint; fast-forward AutoDL CAMP.
3. Reconfirm fixed DP HEAD/status, no related worker, and more than 10 GiB free.
4. Run only `remaining-execution-preflight` against the four sealed source
   roots. Do not invoke `execute-remaining`.
5. Verify and seal HEADS/COMMAND/stdout/stderr/JSON/MD/SHA manifests.
6. Independently review the preflight in the next gate, update live EOF/status,
   commit/push, AutoDL fast-forward, then reread live EOF.
