# V24 Startup Reconciliation Record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the sealed v24 startup reconciliation as the first authoritative v24 audit/current-status gate.

**Architecture:** Reuse the existing audit-pointer contract. Add no runtime controller or simulator code. One focused test locks the new v24 EOF tuple and its matching named current-status section.

**Tech Stack:** Markdown, Python 3.12, pathlib, pytest, Git, existing AutoDL `camp` environment.

## Global Constraints

- Local, GitHub, and AutoDL CAMP must remain on `main` at the same commit.
- DP must remain tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- V23 and earlier audits are read-only.
- Branch A and Branch B remain independently pending after startup.
- No map load, simulator, corpus, training, calibration, holdout, or paired evaluation occurs.
- AutoDL secrets stay in local secure storage and never enter artifacts or logs.

---

### Task 1: Record the sealed startup gate

**Files:**
- Create: `docs/diffusion_planner_v24_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v24_iteration_audit.py`
- Plan: `docs/superpowers/plans/2026-07-15-v24-startup-reconciliation-record.md`

**Interfaces:**
- Consumes: sealed artifact `/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST` and root `a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67`.
- Produces: a v24 audit EOF tuple and an identical `Current V24 Status` tuple.

- [ ] **Step 1: Extend the audit test before creating the audit**

Keep the existing design test and add these constants and tests:

```python
AUDIT = ROOT / "docs" / "diffusion_planner_v24_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v24_status=v24_startup_reconciliation_passed",
    "current_v24_artifact_source_head=245ce029b91f73e6a7fca7c4ecf6a40679770ad7",
    "current_v24_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v24_artifact=/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST",
    "current_v24_artifact_root_sha256=a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67",
    "source_a_status=pending_v23_boundary_review",
    "source_a_terminal=false",
    "source_b_status=pending_v23_boundary_review",
    "source_b_terminal=false",
    "authorized_source_count=2",
    "source_terminal_count=0",
    "global_stop_authorized=false",
    "global_stop_reason=none",
    "next_work_target=v24_v23_boundary_review_only",
)


def test_v24_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_v24_pointer_matches_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    section = text.split("## Current V24 Status", 1)[1].split(
        "## Current V23 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v24_startup_records_frozen_history_and_independent_sources() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "V23 and earlier audits are historical and read-only",
        "dependency-capability diagnosis, not a CAMP/DP performance failure",
        "49,752,203,264",
        "zero related tasks",
        "Branch A and Branch B remain independently eligible",
        "No map loader, simulator, corpus, training, calibration, holdout, or paired evaluation ran",
    ):
        assert phrase in text
```

- [ ] **Step 2: Run RED and confirm the missing audit is the cause**

Run:

```powershell
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v24_iteration_audit.py -q
```

Expected: the design test passes and the new audit tests fail because
`docs/diffusion_planner_v24_iteration_audit.md` or `Current V24 Status` does
not exist.

- [ ] **Step 3: Create the audit and update the current-status entry point**

Create the audit with this content:

```markdown
# Diffusion Planner V24 Iteration Audit

This file is the sole mutable audit for v24. V23 and earlier audits are historical and read-only.
V24 corrects the v23 single-source global-stop control error and advances the
Autoware and TIER IV Lanelet2 sources independently on the unchanged fixed DP.

## Frozen Scope

- CAMP repositories are `F:\camp_core-main` and
  `/root/autodl-tmp/camp_core`, branch `main`.
- Fixed DP is `/root/autodl-tmp/Diffusion-Planner` at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Branch A is the frozen Autoware map plus only the official Apache-2.0
  `autoware_lanelet2_extension` dependency source.
- Branch B is the 14-path/12-blob TIER IV `scenario_simulator_v2` inventory at
  `e22f01093fa6516c0552549ada302270329c59a4`.
- Branch-local and single-map failures cannot stop the other source.
- CAMP may only rerank/select the fixed DP K=8 tensor. DP, source-map semantics,
  candidate tensors, and the convex master remain unchanged.

Persistent goal thread `019f656a-1a4a-7550-8d42-8a385fd2712e` was created
without a token budget. The goal tool limits objective text to 4,000
characters, so its stored compression binds source task
`019f26f1-36ec-7f91-932d-3f365940e8f8` and this full authorized contract.

## Gate 0: Startup Reconciliation

Status: passed. V23 boundary review is next.

Local `main`, local `origin/main`, live GitHub `main`, AutoDL CAMP HEAD, and
AutoDL `origin/main` were identical and tracked-clean at
`245ce029b91f73e6a7fca7c4ecf6a40679770ad7`. AutoDL DP was tracked-clean at
the fixed commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The startup check found zero related tasks. Free space was `49,752,203,264`
bytes, above the 10 GiB floor. V23 closeout root
`08276aec1333f26ec02e7f4a05a2c07aeea810ec4b214a37fba062bd0f138752`
and v22 closeout root
`d82dacf580a1d135c902a27b1cc5ade9af64604b7c7a72ce3c76b437744269ff`
were rehashed successfully.

Two pre-artifact AutoDL public-GitHub probes received transient HTTP 503
errors; bounded retries passed. The sealed startup artifact/root is
`/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST`
/
`a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67`,
with `run.exit=0`.

V23 remains a dependency-capability diagnosis, not a CAMP/DP performance failure.
Branch A and Branch B remain independently eligible. No map loader, simulator,
corpus, training, calibration, holdout, or paired evaluation ran.
`claim_authorized=false` and `holdout_opened=false`.

current_v24_status=v24_startup_reconciliation_passed
current_v24_artifact_source_head=245ce029b91f73e6a7fca7c4ecf6a40679770ad7
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST
current_v24_artifact_root_sha256=a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67
source_a_status=pending_v23_boundary_review
source_a_terminal=false
source_b_status=pending_v23_boundary_review
source_b_terminal=false
authorized_source_count=2
source_terminal_count=0
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_v23_boundary_review_only
```

Update the top of `diffusion_planner_current_status.md` to name v24 as the
authoritative audit, insert `## Current V24 Status` before v23, summarize the
same startup facts, and end that section with the exact `POINTER` tuple.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v24_iteration_audit.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Run the full narrow gate verification**

Run:

```powershell
py -3.12 -m py_compile camp_core\tests\test_diffusion_planner_v24_iteration_audit.py
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v24_iteration_audit.py -q
git diff --check
```

Expected: all commands exit 0 and pytest reports `4 passed`.

- [ ] **Step 6: Commit, push, sync, and reread EOF**

Stage only the four v24 task files and commit:

```powershell
git add -- camp_core/tests/test_diffusion_planner_v24_iteration_audit.py docs/diffusion_planner_v24_iteration_audit.md docs/diffusion_planner_current_status.md docs/superpowers/plans/2026-07-15-v24-startup-reconciliation-record.md
git commit -m "docs(v24): record startup reconciliation"
git push origin main
```

On AutoDL, source `/etc/network_turbo`, fetch, and `git pull --ff-only`. Run
the same py_compile, pytest with
`/root/miniconda3/envs/camp/bin/python`, and `git diff --check`. Confirm AutoDL
CAMP HEAD/origin match GitHub and DP remains fixed, then reread the v24 audit
EOF and current-status v24 section. Expected next target:
`v24_v23_boundary_review_only`.
