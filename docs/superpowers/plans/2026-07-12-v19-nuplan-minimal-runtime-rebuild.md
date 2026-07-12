# V19 nuPlan Minimal Runtime Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the exact nuPlan Python 3.9 simulator prefix from a reviewed, torch-free, hash-locked runtime union while preserving the 10 GiB disk floor.

**Architecture:** Resolve the frozen direct requirements for CPython 3.9 into a wheel-only pip report, convert that report to a deterministic hash lock, statically review it, and perform one fail-closed installation. Official lower-level nuPlan simulator components run in Python 3.9; fixed DP remains unchanged in Python 3.12 across the existing file bridge.

**Tech Stack:** Python standard library, pip dry-run report, conda explicit prefix, pytest, official nuPlan devkit v1.2.

## Global Constraints

- Only `/root/autodl-tmp/camp_v19_nuplan_env` may be recreated.
- Free bytes must remain at least `10737418240` at every materialization checkpoint.
- Fixed DP commit/environment/code/config/weights/checkpoint must not change.
- No torch, Lightning, training stack, old holdout access, simulator execution, claim, promotion, deployment, or activation is authorized by materialization.
- One materialization attempt only; any conflict or non-reproducible state fails closed and is retained.

---

### Task 1: Deterministic pip-report lock converter

**Files:**
- Create: `scripts/integrations/build_nuplan_v12_minimal_runtime_lock.py`
- Create: `camp_core/tests/test_nuplan_v12_minimal_runtime_lock.py`
- Consume: `scripts/integrations/nuplan_v12_minimal_runtime_requirements.txt`

**Interfaces:**
- Consumes: pip `--dry-run --report` JSON.
- Produces: sorted `name==version --hash=sha256:<digest>` lines and a JSON summary.

- [ ] **Step 1: Write failing tests** covering sorted canonical names, exact versions, wheel-only URLs, missing hashes, forbidden packages, and direct-requirement coverage.
- [ ] **Step 2: Run** `python -m pytest -q camp_core/tests/test_nuplan_v12_minimal_runtime_lock.py` and require failure because the converter is absent.
- [ ] **Step 3: Implement** a stdlib-only converter with CLI arguments `--report`, `--direct-requirements`, `--lock-output`, and `--summary-output`.
- [ ] **Step 4: Run** the target test and `python -m py_compile scripts/integrations/build_nuplan_v12_minimal_runtime_lock.py`; both must exit 0.
- [ ] **Step 5: Commit** only the converter, test, requirements input, design, and plan.

### Task 2: Wheel-lock static preflight and review

**Files:**
- Execute: `scripts/integrations/build_nuplan_v12_minimal_runtime_lock.py`
- Read: `docs/superpowers/specs/2026-07-12-v19-nuplan-minimal-runtime-rebuild-design.md`

**Interfaces:**
- Consumes: CPython 3.9 manylinux2014 pip report.
- Produces: immutable report, hash lock, summary, disk projection, command/stdout/stderr, and SHA manifest.

- [ ] **Step 1: Recheck** exact absent target, no related process, preserved paths, three tracked-clean heads, pointer equality, and free bytes.
- [ ] **Step 2: Run** `/root/miniconda3/envs/camp/bin/python -m pip --isolated install --index-url https://pypi.org/simple --dry-run --ignore-installed --only-binary=:all: --report <artifact>/pip-report.json -r scripts/integrations/nuplan_v12_minimal_runtime_requirements.txt`.
- [ ] **Step 3: Convert** the report with the Task 1 CLI and require all review booleans true, no forbidden package, and wheel-only SHA256 coverage.
- [ ] **Step 4: Record** estimated download bytes from the report and require current free minus the frozen 5,000,000,000-byte reserve to remain at least `10737418240`.
- [ ] **Step 5: Seal** the successful static-review artifact and independently recompute its root SHA256. Do not create the environment if review fails.

### Task 3: Single fail-closed materialization

**Files:**
- Create only: `/root/autodl-tmp/camp_v19_nuplan_env`
- Read only: `/root/autodl-tmp/camp_v19_nuplan_devkit`

**Interfaces:**
- Consumes: the reviewed Task 2 hash lock/root.
- Produces: reproducible Python 3.9 simulator runtime or a retained failed prefix/artifact.

- [ ] **Step 1: Create** the exact prefix with `/root/miniconda3/bin/conda create --yes --override-channels -c conda-forge -p /root/autodl-tmp/camp_v19_nuplan_env python=3.9 pip=21.2.4 setuptools=59.5.0`.
- [ ] **Step 2: Check** free bytes and stop before wheel installation if below the hard floor.
- [ ] **Step 3: Install** the reviewed lock with `/root/autodl-tmp/camp_v19_nuplan_env/bin/python -m pip install --no-deps --require-hashes -r <review-artifact>/runtime.lock`.
- [ ] **Step 4: Check** free bytes again, then install the fixed source with `python -m pip install --no-deps --no-build-isolation /root/autodl-tmp/camp_v19_nuplan_devkit`.
- [ ] **Step 5: Run** `pip check`, forbidden-package inspection, source HEAD verification, and imports for the frozen scenario-builder/simulator/controller/observation/metric modules.
- [ ] **Step 6: Seal** conda explicit lock, pip freeze, import output, disk checkpoints, stdout/stderr, and SHA256SUMS. Never retry a failed materialization.

### Task 4: Result review and controller advance

**Files:**
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`

**Interfaces:**
- Consumes: cleanup and materialization artifact roots.
- Produces: append-only review and the next minimal v19 EOF gate.

- [ ] **Step 1: Write** the expected new pointer in the orchestrator regression test and run it red.
- [ ] **Step 2: Append** cleanup/materialization evidence to the v19 audit and update only `Current V19 Status` to the identical tuple.
- [ ] **Step 3: Run** py_compile, the target lock/pointer tests, all v18/v19 suites, and `git diff --check`.
- [ ] **Step 4: Commit/push** only scoped files, ff-only sync AutoDL, rerun the same checks there, and reread the v19 audit EOF.
