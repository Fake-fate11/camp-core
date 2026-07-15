# V23 Source and License Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize and seal only the authorized exact-commit Lanelet2 source files with byte, Git-object, license, NOTICE, URL, time, and redistribution receipts.

**Architecture:** Add one standard-library Python manifest builder that reads exact Git objects from two supplied repositories and writes byte-identical source payloads plus `manifest.json`. A thin AutoDL shell harness performs filtered exact-commit fetches, runs the builder, adds execution receipts, and seals recursive hashes. No map loader, simulator, model, label, or outcome path is invoked.

**Tech Stack:** Python 3.12 standard library, Git object plumbing, pytest, Bash, SHA256.

## Global Constraints

- CAMP branch: `main`; use current branch and fast-forward only.
- Fixed DP commit: `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify DP.
- Autoware repository/commit/path: `https://github.com/autowarefoundation/autoware_universe.git`, `b8d441c59293e34289cd7bca1ba5e5a33e9189d9`, `planning/behavior_path_planner/autoware_behavior_path_bidirectional_traffic_module/test_map/lanelet2_map.osm`.
- Scenario repository/commit: `https://github.com/tier4/scenario_simulator_v2.git`, `e22f01093fa6516c0552549ada302270329c59a4`; select every exact-tree `*.osm` path and no non-OSM data file.
- Materialize root `LICENSE`; materialize root `NOTICE` when present, otherwise record `absent_at_commit`.
- Source files remain byte-identical. No `sanitize_lanelet2_map`, XML rewrite, adapter, route generation, model, simulator, label, calibration, or holdout action is allowed.
- Exclude INTERACTION, inD, rounD, exiD, CARLA, nuPlan, and nuScenes.
- AutoDL network commands source `/etc/network_turbo >/dev/null 2>&1 || true`.
- Maintain at least `10,737,418,240` free bytes.
- Evidence includes HEADS, COMMAND, stdout, stderr, JSON, MD, SHA256SUMS, and ROOT_SHA256SUMS.

---

### Task 1: Exact Git-object source freezer

**Files:**
- Create: `scripts/integrations/freeze_diffusion_planner_v23_sources.py`
- Create: `camp_core/tests/test_diffusion_planner_v23_source_freeze.py`

**Interfaces:**
- Consumes: two local Git repositories containing the frozen commits, an absent output directory, and one explicit ISO-8601 retrieval timestamp.
- Produces: `freeze_sources(specs: Sequence[SourceSpec], output_dir: Path, retrieved_at: str) -> dict[str, Any]`, byte-identical files under `sources/<source_id>/`, and `manifest.json`.
- CLI: `--autoware-repo PATH --scenario-repo PATH --output-dir PATH --retrieved-at ISO8601`.

- [ ] **Step 1: Write failing tests for exact bytes and fail-closed validation**

Create two tiny temporary Git repositories using real `git init`, `git add`,
and `git commit`. Repository A contains `LICENSE`, `NOTICE`, and one OSM.
Repository B contains `LICENSE`, two byte-identical OSM paths, and one distinct
OSM; it has no root NOTICE. Use the real commit SHA from each fixture:

```python
from pathlib import Path

import pytest

from scripts.integrations.freeze_diffusion_planner_v23_sources import (
    SourceSpec,
    freeze_sources,
)


def test_freeze_sources_preserves_git_objects_and_notice_state(tmp_path: Path) -> None:
    autoware = make_git_repo(
        tmp_path / "autoware",
        {
            "LICENSE": APACHE_LICENSE,
            "NOTICE": "Autoware notice\n",
            "map/lanelet2_map.osm": "<osm version='0.6'/>\n",
        },
        "https://github.com/example/autoware.git",
    )
    scenario = make_git_repo(
        tmp_path / "scenario",
        {
            "LICENSE": APACHE_LICENSE,
            "maps/a.osm": "<osm version='0.6'/>\n",
            "maps/copy.osm": "<osm version='0.6'/>\n",
            "maps/b.osm": "<osm version='0.6'><node id='1'/></osm>\n",
        },
        "https://github.com/example/scenario.git",
    )
    output = tmp_path / "out"
    manifest = freeze_sources(
        (
            SourceSpec.exact("autoware", autoware.path, autoware.remote, autoware.commit, ("map/lanelet2_map.osm",)),
            SourceSpec.all_osm("scenario", scenario.path, scenario.remote, scenario.commit),
        ),
        output,
        "2026-07-15T09:00:00Z",
    )
    assert manifest["map_path_count"] == 4
    assert manifest["unique_map_file_sha256_count"] == 3
    assert manifest["sources"][0]["notice_status"] == "present"
    assert manifest["sources"][1]["notice_status"] == "absent_at_commit"
    assert (output / "sources/autoware/map/lanelet2_map.osm").read_bytes() == b"<osm version='0.6'/>\n"
    assert all(row["git_blob_oid"] and row["file_sha256"] for row in manifest["files"])


def test_freeze_sources_rejects_wrong_remote_commit_or_license(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "repo", {"LICENSE": "not Apache", "map.osm": "<osm/>"}, "https://github.com/example/repo.git")
    with pytest.raises(ValueError, match="Apache-2.0"):
        freeze_sources(
            (SourceSpec.exact("bad", repo.path, repo.remote, repo.commit, ("map.osm",)),),
            tmp_path / "out",
            "2026-07-15T09:00:00Z",
        )
```

- [ ] **Step 2: Run RED and confirm missing module**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v23_source_freeze.py -q
```

Expected: collection fails with `ModuleNotFoundError` for
`freeze_diffusion_planner_v23_sources`.

- [ ] **Step 3: Implement the minimum source freezer**

Use a frozen `SourceSpec` dataclass with `exact` and `all_osm` constructors.
The implementation uses only `subprocess`, `hashlib`, `json`, `datetime`,
`dataclasses`, and `pathlib`:

```python
def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def _tree(repo: Path, commit: str) -> dict[str, str]:
    raw = _git(repo, "ls-tree", "-r", "--full-tree", "-z", commit, binary=True)
    rows = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        _mode, kind, oid = metadata.decode("ascii").split()
        if kind == "blob":
            rows[path.decode("utf-8")] = oid
    return rows


def _blob(repo: Path, commit: str, path: str) -> bytes:
    return _git(repo, "show", f"{commit}:{path}", binary=True)
```

`freeze_sources` must:

1. Reject an existing output path.
2. Parse and require the explicit timezone-bearing retrieval time.
3. Require `rev-parse <commit>^{commit}` to equal the requested full commit.
4. Normalize and compare the configured and actual origin URLs.
5. Require root `LICENSE` and the text `Apache License` plus `Version 2.0`.
6. Select exactly configured Autoware paths or every sorted `.osm` tree path.
7. Materialize OSM, LICENSE, and root NOTICE bytes using `git show`.
8. Record source ID, relative path, raw URL, commit, Git blob OID, Git blob
   object SHA256, file SHA256, size, retrieval time, license path/SHA, and
   NOTICE present/absent status.
9. Report total path count and unique file-SHA count without treating either
   as independent map-family count.
10. Write sorted, indented `manifest.json` and return the same mapping.

The manifest's fixed obligations are:

```python
APACHE_2_0_OBLIGATIONS = (
    "provide recipients a copy of Apache License 2.0",
    "mark modified files with prominent change notices",
    "retain applicable copyright, patent, trademark, and attribution notices",
    "include readable upstream NOTICE attributions when NOTICE is present",
    "do not imply trademark permission beyond origin description and NOTICE reproduction",
)
```

- [ ] **Step 4: Run GREEN and static checks**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v23_source_freeze.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile scripts/integrations/freeze_diffusion_planner_v23_sources.py camp_core/tests/test_diffusion_planner_v23_source_freeze.py
git diff --check
```

Expected: all focused tests pass; no new dependency appears.

- [ ] **Step 5: Commit and push the verified builder**

```powershell
git add -- scripts/integrations/freeze_diffusion_planner_v23_sources.py camp_core/tests/test_diffusion_planner_v23_source_freeze.py docs/superpowers/plans/2026-07-15-v23-source-license-freeze.md
git commit -m "feat(v23): freeze map source receipts"
git push origin main
```

### Task 2: AutoDL acquisition, independent source review, and audit pointer

**Files:**
- Modify: `docs/diffusion_planner_v23_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v23_iteration_audit.py`

**Interfaces:**
- Consumes: Task 1 script at synced CAMP HEAD and the two public exact commits.
- Produces: one immutable AutoDL source artifact and an EOF pointer to `v23_adapter_design_tdd_static_review_only`.

- [ ] **Step 1: Fast-forward AutoDL and write the acquisition COMMAND**

The sealed command must source network turbo, verify live CAMP/origin/GitHub
HEADs and fixed DP, verify no related task, and verify the 10 GiB floor. For
each source, create a uniquely named filtered checkout and run:

```bash
git init <checkout>
git -C <checkout> remote add origin <frozen-url>
git -C <checkout> -c protocol.version=2 fetch --depth 1 --filter=blob:none origin <frozen-commit>
```

Use three bounded fetch attempts only for transport failure. Do not change the
commit after a failure. Then run:

```bash
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/freeze_diffusion_planner_v23_sources.py \
  --autoware-repo <autoware-checkout> \
  --scenario-repo <scenario-checkout> \
  --output-dir <artifact>/payload \
  --retrieved-at <frozen-UTC-time>
```

- [ ] **Step 2: Seal and independently review source receipts**

Require command exit 0, exact commits, root licenses, Autoware NOTICE present,
scenario root NOTICE status from the exact tree, source byte SHA agreement,
and URL/blob/file receipts for every OSM. Record observed path and unique-byte
counts; if they differ from the earlier 14/12 scan, preserve the result and
attribute it before any adapter work. Recursively hash every artifact file into
`SHA256SUMS`, then hash that file into `ROOT_SHA256SUMS`.

- [ ] **Step 3: RED/GREEN the audit pointer update**

First change the v23 audit test's exact pointer to source-freeze status and
artifact root; run it and confirm failure. Then append the passed/failed
receipt details to the v23 audit, replace only the Current V23 section in
current status, and end both with:

```text
current_v23_status=v23_license_source_freeze_passed
current_v23_artifact_source_head=<live-full-builder-head>
current_v23_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v23_artifact=<immutable-source-artifact>
current_v23_artifact_root_sha256=<root-sha256>
next_work_target=v23_adapter_design_tdd_static_review_only
```

- [ ] **Step 4: Run local and AutoDL regression**

```powershell
& 'C:\Users\lenovo\anaconda3\python.exe' -m pytest camp_core/tests/test_diffusion_planner_v23_source_freeze.py camp_core/tests/test_diffusion_planner_v23_design.py camp_core/tests/test_diffusion_planner_v23_iteration_audit.py camp_core/tests/test_diffusion_planner_v22_iteration_audit.py -q
& 'C:\Users\lenovo\anaconda3\python.exe' -m py_compile scripts/integrations/freeze_diffusion_planner_v23_sources.py camp_core/tests/test_diffusion_planner_v23_source_freeze.py camp_core/tests/test_diffusion_planner_v23_iteration_audit.py
git diff --check
```

Repeat on AutoDL after ff-only sync. Expected: all tests pass; fixed DP and
tracked-clean state remain exact.

- [ ] **Step 5: Commit, push, sync, and reread EOF**

```powershell
git add -- docs/diffusion_planner_v23_iteration_audit.md docs/diffusion_planner_current_status.md camp_core/tests/test_diffusion_planner_v23_iteration_audit.py
git commit -m "docs(v23): record source license freeze"
git push origin main
```

Fast-forward AutoDL, rerun checks, then reread both live v23 pointers. Continue
only to `v23_adapter_design_tdd_static_review_only`.

## Plan self-review

- Spec coverage: exact URLs/commits, allowed path selection, LICENSE/NOTICE,
  acquisition time, blob/file hashes, Apache obligations, byte preservation,
  forbidden sources, evidence shape, and no-execution boundary are covered.
- Placeholder scan: complete; no deferred marker or unnamed step remains.
- Type consistency: `SourceSpec`, `freeze_sources`, `git_blob_oid`,
  `git_blob_sha256`, `file_sha256`, `notice_status`, and CLI names are
  consistent throughout.
- Scope: adapter and map semantics are deliberately excluded until the next
  independently reviewed subproject.
