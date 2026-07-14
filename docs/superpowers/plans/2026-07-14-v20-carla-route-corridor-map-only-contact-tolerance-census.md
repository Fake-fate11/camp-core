# V20 Offline CARLA Route-Corridor Contact-Tolerance Census Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (- [ ]) syntax for tracking.

**Goal:** Freeze one candidate-independent Town10HD_Opt route-boundary contact
tolerance before any new fixed-DP K=8 source probe.

**Architecture:** Add one runner around the existing deterministic route,
corridor builder, frozen measurement ceiling, and tolerance freezer. The
runner receives one offline native CARLA map, performs one measurement pass
and one final pass, and atomically writes one reconstructible receipt. No
builder refactor, dependency, server, or new orchestrator is added.

**Tech Stack:** Frozen TEST_PYTHON
/root/autodl-tmp/camp_v19_nuplan_env/bin/python (resolving exactly to
/root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9, Python 3.9.23, SHA256
d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c)
for repo tests, py_compile, and auxiliary evidence scripts; frozen CARLA_PYTHON
/root/miniconda3/bin/python3.12 (resolving exactly to itself, Python 3.12.3,
SHA256 0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1)
only for the sealed cp312 CARLA import and the one census command; pytest,
Python standard library, existing CAMP CARLA integration code, and official
CARLA 0.9.16 cp312 client.

## Runtime Authority

The exact AutoDL interpreter receipts above are authoritative. TEST_PYTHON
owns every remote repo test, py_compile, process scan, JSON read/write, and
other auxiliary script. CARLA_PYTHON owns only the sealed cp312 CARLA import
and the one frozen census COMMAND. Neither interpreter may be PATH-discovered,
substituted, installed, relinked, or mutated.

## Complexity Budget Authority

The checked-in runner and focused test, plus the commands and criteria below,
supersede this plan's embedded implementation snippets. This closure addresses
only production-import proof, interpreter identity before first functional use,
and noninterchangeable TEST_PYTHON/CARLA_PYTHON roles.

~~~bash
set -euo pipefail
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
CARLA_PYTHON=/root/miniconda3/bin/python3.12
TEST_PYTHON_RESOLVED=$(readlink -f "$TEST_PYTHON")
CARLA_PYTHON_RESOLVED=$(readlink -f "$CARLA_PYTHON")
test -x "$TEST_PYTHON" && test -x "$CARLA_PYTHON"
test "$TEST_PYTHON_RESOLVED" = /root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9
test "$CARLA_PYTHON_RESOLVED" = /root/miniconda3/bin/python3.12
test "$(sha256sum "$TEST_PYTHON_RESOLVED")" = "d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c  /root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9"
test "$(sha256sum "$CARLA_PYTHON_RESOLVED")" = "0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1  /root/miniconda3/bin/python3.12"
test "$("$TEST_PYTHON" --version 2>&1)" = "Python 3.9.23"
test "$("$CARLA_PYTHON" --version 2>&1)" = "Python 3.12.3"
RUNNER=/root/autodl-tmp/camp_core/scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py
"$TEST_PYTHON" -m pytest camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py -q
"$TEST_PYTHON" -m py_compile "$RUNNER" camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core "$CARLA_PYTHON" "$RUNNER" --preflight-only --output-json /root/autodl-tmp/v20_contact_tolerance_preflight.json
"$TEST_PYTHON" -m json.tool /root/autodl-tmp/v20_contact_tolerance_preflight.json > /dev/null
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core "$CARLA_PYTHON" "$RUNNER" --preflight-json /root/autodl-tmp/v20_contact_tolerance_preflight.json --camp-head "$(git rev-parse HEAD)" --output-json /root/autodl-tmp/v20_contact_tolerance_receipt.json
~~~

Success requires every identity/check command to exit 0, preflight booleans
no_map/no_census/no_server to be true, and one atomic census receipt with no
`.tmp`. Any identity, import, provenance, existing-output, or census mismatch
exits nonzero; execute only after the preflight succeeds.

## Global Constraints

- Work starts from CAMP/GitHub/AutoDL head
  9537f1998100a32b74cdb6cc6dc36db4837c77f4.
- Fixed DP remains
  7a1d33da277a1992ec474b5383a0c963c72e04e4.
- Use only map name Carla/Maps/Town10HD_Opt and official XODR
  /root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD_Opt.xodr.
- Require XODR SHA256
  5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7.
- Require CARLA source-root SHA256
  2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce.
- Require client root /root/autodl-tmp/camp_v19_carla_client,
  CLIENT_SHA256SUMS SHA256
  ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e,
  and libcarla SHA256
  c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2.
- TEST_PYTHON is exactly /root/autodl-tmp/camp_v19_nuplan_env/bin/python,
  resolves to /root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9, reports
  Python 3.9.23, and has SHA256
  d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c.
  It is the only interpreter for remote repo tests, py_compile, and auxiliary
  evidence JSON/process scripts.
- CARLA_PYTHON is exactly /root/miniconda3/bin/python3.12, resolves to itself,
  reports Python 3.12.3, and has SHA256
  0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1.
  It is used only for the sealed cp312 CARLA import and frozen census COMMAND.
  Do not download, install, relink, or mutate either environment.
- Production constructs exactly
  carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml). It never imports or
  calls carla.Client and never launches or connects to a server.
- Reuse _deterministic_route, build_pre_generation_route_corridor,
  FROZEN_LIFTING_TOLERANCES, and freeze_lifting_tolerances.
- Route selection is exactly 81 points at 5.0 m.
- First-pass contact tolerance is exactly
  FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m and is only a fail-closed
  measurement ceiling.
- Freeze once from the measured maximum, zero station/z errors, and the
  boundary-coordinate scale; use only the returned geometry_epsilon_m.
- Run the builder a second and final time with that frozen tolerance. Never
  change route, XODR, tolerance, or source rules from observed results.
- No candidate, DP request/worker, checkpoint, config, outcome, metric,
  future-label, holdout, selector, eligibility, actor, tick, promotion,
  deployment, activation, formal seed, Full36, or claim interface is allowed.
- Every gate artifact contains HEADS, COMMAND, stdout, stderr, EXIT_STATUS,
  one JSON, one MD, SHA256SUMS, and ROOT_SHA256. Additional evidence files are
  listed explicitly in each gate.
- Any remote git/network command starts with
  source /etc/network_turbo >/dev/null 2>&1 || true.
- Gate order is immutable: plan static review; TDD implementation; no-run
  preflight; exactly one offline census; independent result review; then and
  only then one source-only fixed-DP K=8 probe.

## File Map and Exact Interfaces

- Create
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py:
  pure census function plus thin offline CLI.
- Create
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py:
  fake-map behavior, failure, provenance, hashing, and CLI tests.
- Do not modify the builder, source-probe runner, fixed DP, or v19 evidence.

The public function is:

~~~python
def census_route_corridor_contact_tolerance(
    *,
    map_api: Any,
    opendrive_xml: str,
    camp_execution_head: str,
    carla_version: str,
    carla_module_path: str,
    carla_module_sha256: str,
    client_manifest_sha256: str,
    carla_source_root_sha256: str,
) -> dict[str, Any]:
~~~

The CLI is:

~~~bash
CARLA_PYTHON=/root/miniconda3/bin/python3.12
"$CARLA_PYTHON" census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  --camp-head "$(git rev-parse HEAD)" \
  --output-json /tmp/v20_contact_tolerance_receipt.json
~~~

The production execution command below derives and validates its concrete head
and output path at runtime; /tmp is only the interface example above.

The receipt has this exact top-level projection:

~~~python
{
    "schema_version": str,
    "provenance": {
        "camp_gate_start_head": str,
        "camp_execution_head": str,
        "fixed_dp_head": str,
        "carla_version": str,
        "carla_source_root_sha256": str,
        "carla_module_path": str,
        "carla_module_sha256": str,
        "client_manifest_sha256": str,
        "map_name": str,
        "xodr_sha256": str,
    },
    "route": {
        "point_count": 81,
        "sample_step_m": 5.0,
        "records": list[dict[str, object]],
        "sha256": str,
    },
    "corridor": {
        "measurement_sha256": str,
        "final_sha256": str,
        "evidence": dict[str, object],
        "evidence_sha256": str,
        "boundary_identity_receipts": list[dict[str, object]],
        "boundary_identity_receipts_sha256": str,
        "raw_contact_gaps_m": list[float],
        "max_contact_gap_m": float,
    },
    "tolerance": {
        "measurement_ceiling_m": float,
        "coordinate_scale_m": float,
        "allowance_formula": "max(1e-9, 64*ulp(coordinate_scale_m))",
        "allowance_m": float,
        "frozen_contact_tolerance_m": float,
        "builder_contact_tolerances_m": list[float],
    },
    "call_counters": {
        "_deterministic_route": 1,
        "build_pre_generation_route_corridor": 2,
        "freeze_lifting_tolerances": 1,
    },
    "forbidden_access_counters": {
        "server_connections": 0,
        "server_launches": 0,
        "world_gets": 0,
        "actor_spawns": 0,
        "world_ticks": 0,
        "candidate_reads": 0,
        "dp_request_reads": 0,
        "dp_worker_calls": 0,
        "outcome_reads": 0,
        "metric_calls": 0,
        "future_label_reads": 0,
        "holdout_reads": 0,
        "selector_calls": 0,
        "eligibility_calls": 0,
    },
    "receipt_sha256": str,
}
~~~

The corridor evidence is exactly the builder output excluding only
contact_tolerance_m and corridor_sha256. Its exact keys are schema_version,
map_sha256, route_sample_step_m, station_allowance_m, route_samples,
directed_edges, identity_directions, predecessor_receipt, boundary_receipts,
and max_contact_gap_m.

Each boundary identity receipt is the exact projection identity, direction,
exact_entry_s, exact_exit_s, lookup_entry_s, lookup_exit_s, entry_xyz,
exit_xyz, contact_to_next_m, and identity_verified.

Canonical hashes use canonical_json_sha256. receipt_sha256 is computed from
the complete top-level payload before receipt_sha256 is inserted. Independent
review removes only receipt_sha256 and recomputes the same hash.

---

### Task 1: Static-review this plan before implementation

**Files:**

- Verify:
  docs/superpowers/plans/2026-07-14-v20-carla-route-corridor-map-only-contact-tolerance-census.md
- Do not create either runner file yet.

**Interfaces:**

- Consumes: this committed plan and current v20 pointer.
- Produces: one sealed static-review artifact with status pass or fail.

- [ ] **Step 1: Run the exact static-review artifact command**

Run on AutoDL after the plan commit is pushed by an authorized controller:

~~~bash
set -euo pipefail
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
git fetch --prune origin
git pull --ff-only
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_plan_static_review_$STAMP
test ! -e "$ROOT"
mkdir "$ROOT"
printf 'camp_head=%s\norigin_main=%s\nfixed_dp_head=%s\n' \
  "$(git rev-parse HEAD)" \
  "$(git rev-parse origin/main)" \
  "$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD)" > "$ROOT/HEADS"
sha256sum docs/superpowers/plans/2026-07-14-v20-carla-route-corridor-map-only-contact-tolerance-census.md > "$ROOT/SOURCE_SHA256SUMS"
"$TEST_PYTHON" - <<'PY' > "$ROOT/PROCESSES" 2>> "$ROOT/stderr" || printf '{"capture_error":"process_scan_failed"}\n' > "$ROOT/PROCESSES"
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS" 2>> "$ROOT/stderr" || \
  printf 'listener_capture_failed\n' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -euo pipefail
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
"$TEST_PYTHON" - <<'PY'
import json
import os
import re
from pathlib import Path

root = Path(os.environ["ARTIFACT_ROOT"])
plan = Path(
    "/root/autodl-tmp/camp_core/docs/superpowers/plans/"
    "2026-07-14-v20-carla-route-corridor-map-only-contact-tolerance-census.md"
).read_text(encoding="utf-8")
required = (
    "superpowers:subagent-driven-development",
    "superpowers:executing-plans",
    "**Goal:**",
    "**Architecture:**",
    "**Tech Stack:**",
    "## Runtime Authority",
    "## Global Constraints",
    "### Task 1: Static-review this plan before implementation",
    "### Task 2: Add behavioral RED tests",
    "### Task 3: Implement the minimum runner",
    "### Task 4: Run the no-run preflight",
    "### Task 5: Execute exactly once",
    "### Task 6: Independently review without rerunning",
    "- [ ]",
)
argument_call = "parser." + "add_argument("
camp_argument = argument_call + chr(34) + "--camp-head" + chr(34)
output_argument = argument_call + chr(34) + "--output-json" + chr(34)
bash_blocks = re.findall(r"~~~bash\n(.*?)\n~~~", plan, flags=re.S)
unsafe_remote_python = []
remote_shell_lines = []
for block_index, block in enumerate(bash_blocks, 1):
    in_python = False
    for line_index, line in enumerate(block.splitlines(), 1):
        if in_python:
            if line == "PY":
                in_python = False
            continue
        remote_shell_lines.append(line)
        if (
            re.search(r"(?<![/\w.-])python3\.12(?=[\s)]|$)", line)
            or re.search(r"\bcommand\s+-v\s+python3\.12\b", line)
        ):
            unsafe_remote_python.append((block_index, line_index, line))
        if "<<'PY'" in line:
            in_python = True
remote_shell = "\n".join(remote_shell_lines)
test_python_assignments = re.findall(r"(?m)^TEST_PYTHON=(\S+)$", remote_shell)
carla_python_assignments = re.findall(r"(?m)^CARLA_PYTHON=(\S+)$", remote_shell)
checks = {
    "required_sections": all(item in plan for item in required),
    "checkbox_count": plan.count("- [ ]") >= 15,
    "no_angle_placeholders": re.search(r"<[A-Z][A-Z0-9_]*>", plan) is None,
    "static_review_precedes_tdd": plan.index("### Task 1") < plan.index("### Task 2"),
    "offline_map_only": 'carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)' in plan,
    "no_server_cli": (
        plan.count(camp_argument) == 1
        and plan.count(output_argument) == 1
        and plan.count(argument_call) == 2
    ),
    "exactly_once": "### Task 5: Execute exactly once" in plan,
    "absolute_dual_runtime_assignments": (
        bool(test_python_assignments)
        and set(test_python_assignments)
        == {"/root/autodl-tmp/camp_v19_nuplan_env/bin/python"}
        and bool(carla_python_assignments)
        and set(carla_python_assignments)
        == {"/root/miniconda3/bin/python3.12"}
    ),
    "no_remote_path_python3_12": not unsafe_remote_python,
    "processes_empty": not (root / "PROCESSES").read_text(),
    "listeners_empty": not (root / "LISTENERS").read_text(),
}
result = {"status": "pass" if all(checks.values()) else "fail", "checks": checks}
(root / "review.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
(root / "review.md").write_text(
    "# V20 census plan static review\n\n"
    + "\n".join(f"- {key}: {value}" for key, value in checks.items())
    + "\n",
    encoding="utf-8",
)
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["status"] == "pass" else 1)
PY
SH
set +e
ARTIFACT_ROOT="$ROOT" bash "$ROOT/COMMAND" > "$ROOT/stdout" 2>> "$ROOT/stderr"
STATUS=$?
set -e
printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS"
(cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS review.json review.md PROCESSES LISTENERS SOURCE_SHA256SUMS > SHA256SUMS)
(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256)
test "$STATUS" -eq 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
~~~

Expected: EXIT_STATUS is 0, review.json status is pass, stderr is empty, and
ROOT_SHA256 is one 64-hex line.

- [ ] **Step 2: Stop unless independent static review passes**

Run this read-only verification:

~~~bash
set -euo pipefail
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
CAMP_HEAD=$(git rev-parse HEAD)
ROOT=$("$TEST_PYTHON" - "$CAMP_HEAD" <<'PY'
import json
import sys
from pathlib import Path
head = sys.argv[1]
matches = []
for path in Path("/root/autodl-tmp").glob(
    "camp_dp_v20_carla_contact_tolerance_plan_static_review_*/review.json"
):
    heads = dict(
        line.split("=", 1)
        for line in (path.parent / "HEADS").read_text().splitlines()
    )
    if heads["camp_head"] == head and json.loads(path.read_text())["status"] == "pass":
        matches.append(path.parent)
if len(matches) != 1:
    raise SystemExit(f"expected one passing static review, found {len(matches)}")
print(matches[0])
PY
)
(cd "$ROOT" && sha256sum -c SHA256SUMS)
(cd /root/autodl-tmp/camp_core && sha256sum -c "$ROOT/SOURCE_SHA256SUMS")
test "$(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$ROOT/ROOT_SHA256")"
test "$(cat "$ROOT/EXIT_STATUS")" = 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
"$TEST_PYTHON" -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "pass"' "$ROOT/review.json"
~~~

No test or runner file may be created until this exits 0. Failure keeps
next_work_target at
v20_carla_route_corridor_map_only_contact_tolerance_census_plan_static_review_only.

---

### Task 2: Add behavioral RED tests

**Files:**

- Create:
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
- Create signature-only stub:
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py

**Interfaces:**

- Consumes: existing builder, deterministic route, tolerance constants/freezer.
- Produces: behavior tests that fail with census not implemented, not an import
  or collection failure.

- [ ] **Step 1: Create the signature-only stub**

~~~python
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


def census_route_corridor_contact_tolerance(
    *,
    map_api: Any,
    opendrive_xml: str,
    camp_execution_head: str,
    carla_version: str,
    carla_module_path: str,
    carla_module_sha256: str,
    client_manifest_sha256: str,
    carla_source_root_sha256: str,
) -> dict[str, Any]:
    raise NotImplementedError("census not implemented")


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("census CLI not implemented")


if __name__ == "__main__":
    raise SystemExit(main())
~~~

- [ ] **Step 2: Create the complete fake-map test file**

~~~python
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from camp_core.integrations.carla_causal_adapter import (
    build_pre_generation_route_corridor as real_builder,
)
from camp_core.integrations.carla_exact_speed_source import canonical_json_sha256
from scripts.integrations import (
    census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance
    as census,
)

XODR = """<OpenDRIVE>
<road id="1" length="200"><lanes><laneSection s="0">
<right><lane id="-1" type="driving"/></right>
</laneSection></lanes></road>
<road id="2" length="205"><lanes><laneSection s="0">
<right><lane id="-1" type="driving"/></right>
</laneSection></lanes></road>
</OpenDRIVE>"""


class Waypoint:
    def __init__(self, road_id, s, x, *, previous=()):
        self.road_id = road_id
        self.section_id = 0
        self.lane_id = -1
        self.s = float(s)
        self.lane_width = 3.5
        self.is_junction = False
        self.transform = SimpleNamespace(
            location=SimpleNamespace(x=float(x), y=0.0, z=0.0)
        )
        self._previous = tuple(previous)
        self._next = ()

    def previous(self, distance):
        assert distance == 5.0
        return list(self._previous)

    def next(self, distance):
        assert distance == 5.0
        return list(self._next)


class FakeMap:
    name = "Carla/Maps/Town10HD_Opt"

    def __init__(self, *, gap=0.25, predecessor_count=1, nonfinite=False):
        predecessor = Waypoint(1, 0.0, 0.0)
        road1 = [Waypoint(1, 5.0 * (i + 1), 5.0 * (i + 1)) for i in range(40)]
        road2 = [
            Waypoint(2, 5.0 * (i + 1), 200.0 + gap + 5.0 * (i + 1))
            for i in range(41)
        ]
        previous = [predecessor] * predecessor_count
        if predecessor_count == 2:
            previous[1] = Waypoint(1, 0.5, 0.5)
        road1[0]._previous = tuple(previous)
        self.route = road1 + road2
        for left, right in zip(self.route, self.route[1:]):
            left._next = (right,)
        self.gap = gap
        self.nonfinite = nonfinite
        self.actor_spawns = 0
        self.world_ticks = 0
        self.server_connections = 0

    def generate_waypoints(self, step):
        assert step == 5.0
        return [self.route[0]]

    def get_waypoint_xodr(self, road_id, lane_id, s):
        assert lane_id == -1
        x = float(s) if road_id == 1 else 200.0 + self.gap + float(s)
        if self.nonfinite and road_id == 2:
            x = float("nan")
        return Waypoint(road_id, s, x)

    def spawn_actor(self, *args, **kwargs):
        self.actor_spawns += 1
        raise AssertionError("actor API forbidden")

    def tick(self):
        self.world_ticks += 1
        raise AssertionError("tick API forbidden")


def run_census(monkeypatch, map_api=None):
    monkeypatch.setattr(
        census, "XODR_SHA256", hashlib.sha256(XODR.encode()).hexdigest()
    )
    return census.census_route_corridor_contact_tolerance(
        map_api=map_api or FakeMap(),
        opendrive_xml=XODR,
        camp_execution_head="a" * 40,
        carla_version=census.CARLA_VERSION,
        carla_module_path="/client/carla/libcarla.cpython-312-x86_64-linux-gnu.so",
        carla_module_sha256=census.LIBCARLA_SHA256,
        client_manifest_sha256=census.CLIENT_MANIFEST_SHA256,
        carla_source_root_sha256=census.CARLA_SOURCE_ROOT_SHA256,
    )


def test_two_pass_nonzero_gap_formula_and_determinism(monkeypatch):
    calls = Counter()
    original_route = census._deterministic_route
    original_builder = census.build_pre_generation_route_corridor
    original_freeze = census.freeze_lifting_tolerances

    def observed_route(*args, **kwargs):
        calls["_deterministic_route"] += 1
        return original_route(*args, **kwargs)

    def observed_builder(*args, **kwargs):
        calls["build_pre_generation_route_corridor"] += 1
        return original_builder(*args, **kwargs)

    def observed_freeze(*args, **kwargs):
        calls["freeze_lifting_tolerances"] += 1
        return original_freeze(*args, **kwargs)

    monkeypatch.setattr(census, "_deterministic_route", observed_route)
    monkeypatch.setattr(
        census, "build_pre_generation_route_corridor", observed_builder
    )
    monkeypatch.setattr(census, "freeze_lifting_tolerances", observed_freeze)
    first_map = FakeMap()
    first = run_census(monkeypatch, first_map)
    expected_calls = {
        "_deterministic_route": 1,
        "build_pre_generation_route_corridor": 2,
        "freeze_lifting_tolerances": 1,
    }
    assert dict(calls) == expected_calls
    assert first["call_counters"] == expected_calls
    assert (
        first_map.actor_spawns,
        first_map.world_ticks,
        first_map.server_connections,
    ) == (0, 0, 0)
    calls.clear()
    second_map = FakeMap()
    second = run_census(monkeypatch, second_map)
    tolerance = first["tolerance"]
    corridor = first["corridor"]

    assert first == second
    assert corridor["raw_contact_gaps_m"][0] > 0.0
    assert len(corridor["boundary_identity_receipts"]) == 2
    assert tolerance["builder_contact_tolerances_m"] == [
        census.FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m,
        tolerance["frozen_contact_tolerance_m"],
    ]
    expected_allowance = max(
        1e-9, 64.0 * math.ulp(tolerance["coordinate_scale_m"])
    )
    assert tolerance["allowance_m"] == pytest.approx(
        expected_allowance, rel=0.0, abs=1e-15
    )
    assert dict(calls) == expected_calls
    assert second["call_counters"] == expected_calls
    assert (
        second_map.actor_spawns,
        second_map.world_ticks,
        second_map.server_connections,
    ) == (0, 0, 0)


def test_nonfinite_predecessor_and_ceiling_fail_closed(monkeypatch):
    freeze_calls = 0
    original_freeze = census.freeze_lifting_tolerances

    def counted_freeze(**kwargs):
        nonlocal freeze_calls
        freeze_calls += 1
        return original_freeze(**kwargs)

    monkeypatch.setattr(census, "freeze_lifting_tolerances", counted_freeze)
    for map_api in (
        FakeMap(nonfinite=True),
        FakeMap(predecessor_count=0),
        FakeMap(predecessor_count=2),
        FakeMap(gap=2.0),
    ):
        with pytest.raises(ValueError):
            run_census(monkeypatch, map_api)
    assert freeze_calls == 0


def test_second_pass_drift_fails_closed(monkeypatch):
    calls = 0

    def drifting_builder(**kwargs):
        nonlocal calls
        calls += 1
        result = real_builder(**kwargs)
        if calls == 2:
            result = deepcopy(result)
            result["boundary_receipts"][0]["entry_xyz"][0] += 0.01
        return result

    monkeypatch.setattr(
        census, "build_pre_generation_route_corridor", drifting_builder
    )
    with pytest.raises(ValueError, match="evidence changed"):
        run_census(monkeypatch)
    assert calls == 2


def test_receipt_hashes_and_forbidden_access_are_reconstructible(monkeypatch):
    receipt = run_census(monkeypatch)
    sealed = dict(receipt)
    receipt_sha = sealed.pop("receipt_sha256")
    assert receipt_sha == canonical_json_sha256(sealed)
    assert receipt["route"]["sha256"] == canonical_json_sha256(
        receipt["route"]["records"]
    )
    corridor = receipt["corridor"]
    assert corridor["evidence_sha256"] == canonical_json_sha256(
        corridor["evidence"]
    )
    assert corridor["boundary_identity_receipts_sha256"] == canonical_json_sha256(
        corridor["boundary_identity_receipts"]
    )
    assert receipt["forbidden_access_counters"] == census.FORBIDDEN_COUNTERS
    text = json.dumps(
        {key: value for key, value in receipt.items() if key != "forbidden_access_counters"}
    ).lower()
    for forbidden in (
        "candidate",
        "outcome",
        "metric",
        "holdout",
        "selector",
        "dp_request",
        "dp_worker",
        "future_label",
        "eligibility",
        "server",
        "world",
        "actor",
        "tick",
    ):
        assert forbidden not in text


def test_cli_uses_one_offline_map_and_atomic_output(monkeypatch, tmp_path):
    xodr = tmp_path / "Town10HD_Opt.xodr"
    xodr.write_text(XODR, encoding="utf-8")
    client = tmp_path / "client"
    client.mkdir()
    manifest = client / "CLIENT_SHA256SUMS"
    manifest.write_text("client\n", encoding="utf-8")
    lib = client / "libcarla.cpython-312-x86_64-linux-gnu.so"
    lib.write_bytes(b"libcarla")
    source_root = tmp_path / "ROOT_SHA256"
    source_root.write_text("source\n", encoding="utf-8")
    output = tmp_path / "receipt.json"
    map_calls = []

    carla = ModuleType("carla")
    carla.__path__ = []
    carla.Map = lambda name, text: map_calls.append((name, text)) or FakeMap()
    libcarla = ModuleType("carla.libcarla")
    libcarla.__file__ = str(lib)
    monkeypatch.setitem(sys.modules, "carla", carla)
    monkeypatch.setitem(sys.modules, "carla.libcarla", libcarla)
    monkeypatch.setattr(census, "XODR_PATH", xodr)
    monkeypatch.setattr(census, "CLIENT_ROOT", client)
    monkeypatch.setattr(census, "CLIENT_MANIFEST_PATH", manifest)
    monkeypatch.setattr(census, "CARLA_SOURCE_ROOT_RECEIPT", source_root)
    monkeypatch.setattr(census, "XODR_SHA256", hashlib.sha256(XODR.encode()).hexdigest())
    monkeypatch.setattr(census, "CLIENT_MANIFEST_SHA256", hashlib.sha256(b"client\n").hexdigest())
    monkeypatch.setattr(census, "LIBCARLA_SHA256", hashlib.sha256(b"libcarla").hexdigest())
    monkeypatch.setattr(census, "CARLA_SOURCE_ROOT_SHA256", "source")
    monkeypatch.setattr(census, "_distribution_version", lambda name: "0.9.16")

    assert census.main(["--camp-head", "a" * 40, "--output-json", str(output)]) == 0
    assert len(map_calls) == 1
    assert output.exists()
    assert not output.with_suffix(".json.tmp").exists()


def test_cli_rejects_existing_output_or_tmp_before_input_access(monkeypatch, tmp_path):
    monkeypatch.setattr(census, "XODR_PATH", tmp_path / "missing.xodr")
    for suffix in ("output", "tmp"):
        output = tmp_path / f"receipt-{suffix}.json"
        occupied = (
            output
            if suffix == "output"
            else output.with_suffix(output.suffix + ".tmp")
        )
        occupied.write_text("occupied", encoding="utf-8")
        with pytest.raises(FileExistsError):
            census.main(["--camp-head", "a" * 40, "--output-json", str(output)])
~~~

- [ ] **Step 3: Run RED and verify behavior failure**

Run:

~~~powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
~~~

Expected: six tests fail from NotImplementedError containing census not
implemented or census CLI not implemented. Collection succeeds.

---

### Task 3: Implement the minimum runner

**Files:**

- Replace stub:
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py
- Test:
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py

**Interfaces:**

- Consumes: the Task 2 public signature and frozen provenance.
- Produces: one canonical receipt and one offline atomic CLI.

- [ ] **Step 1: Replace the stub with this implementation**

~~~python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any, Mapping, Sequence

from camp_core.integrations.carla_causal_adapter import (
    build_pre_generation_route_corridor,
)
from camp_core.integrations.carla_exact_speed_source import (
    canonical_json_sha256,
    freeze_lifting_tolerances,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe import (
    FIXED_DP_HEAD,
    FROZEN_LIFTING_TOLERANCES,
    _deterministic_route,
    _write_json_atomic,
)

SCHEMA = "dp_camp_v20_carla_route_corridor_contact_tolerance_census_v1"
CAMP_GATE_START_HEAD = "9537f1998100a32b74cdb6cc6dc36db4837c77f4"
EXPECTED_FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CARLA_VERSION = "0.9.16"
MAP_NAME = "Carla/Maps/Town10HD_Opt"
XODR_PATH = Path(
    "/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/"
    "OpenDrive/Town10HD_Opt.xodr"
)
XODR_SHA256 = "5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7"
CARLA_SOURCE_ROOT_SHA256 = (
    "2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce"
)
CARLA_SOURCE_ROOT_RECEIPT = Path(
    "/root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_"
    "20260713T000320CST/ROOT_SHA256"
)
CLIENT_ROOT = Path("/root/autodl-tmp/camp_v19_carla_client")
CLIENT_MANIFEST_PATH = CLIENT_ROOT / "CLIENT_SHA256SUMS"
CLIENT_MANIFEST_SHA256 = (
    "ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e"
)
LIBCARLA_SHA256 = (
    "c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2"
)
BOUNDARY_KEYS = (
    "identity",
    "direction",
    "exact_entry_s",
    "exact_exit_s",
    "lookup_entry_s",
    "lookup_exit_s",
    "entry_xyz",
    "exit_xyz",
    "contact_to_next_m",
    "identity_verified",
)
EVIDENCE_KEYS = (
    "schema_version",
    "map_sha256",
    "route_sample_step_m",
    "station_allowance_m",
    "route_samples",
    "directed_edges",
    "identity_directions",
    "predecessor_receipt",
    "boundary_receipts",
    "max_contact_gap_m",
)
FORBIDDEN_COUNTERS = {
    "server_connections": 0,
    "server_launches": 0,
    "world_gets": 0,
    "actor_spawns": 0,
    "world_ticks": 0,
    "candidate_reads": 0,
    "dp_request_reads": 0,
    "dp_worker_calls": 0,
    "outcome_reads": 0,
    "metric_calls": 0,
    "future_label_reads": 0,
    "holdout_reads": 0,
    "selector_calls": 0,
    "eligibility_calls": 0,
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _route_records(route: Sequence[Any]) -> list[dict[str, object]]:
    records = []
    for waypoint in route:
        location = waypoint.transform.location
        values = (waypoint.s, location.x, location.y, location.z)
        if any(not math.isfinite(float(value)) for value in values):
            raise ValueError("route waypoint geometry must be finite")
        records.append(
            {
                "road_id": str(waypoint.road_id),
                "section_id": int(waypoint.section_id),
                "lane_id": int(waypoint.lane_id),
                "s": float(waypoint.s),
                "xyz": [float(location.x), float(location.y), float(location.z)],
            }
        )
    return records


def _boundary_projection(
    corridor: Mapping[str, Any],
) -> tuple[list[dict[str, object]], list[float], float]:
    raw = corridor.get("boundary_receipts")
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError("census requires at least two boundary identities")
    receipts = [{key: item[key] for key in BOUNDARY_KEYS} for item in raw]
    gaps = []
    for index, receipt in enumerate(receipts):
        coordinates = [*receipt["entry_xyz"], *receipt["exit_xyz"]]
        if any(not math.isfinite(float(value)) for value in coordinates):
            raise ValueError("boundary coordinates must be finite")
        gap = receipt["contact_to_next_m"]
        if index < len(receipts) - 1:
            if gap is None or not math.isfinite(float(gap)) or float(gap) < 0.0:
                raise ValueError("boundary contact is missing or nonfinite")
            gaps.append(float(gap))
        elif gap is not None:
            raise ValueError("last boundary contact must be null")
    maximum = max(gaps)
    if maximum != float(corridor["max_contact_gap_m"]):
        raise ValueError("boundary maximum does not match raw contacts")
    return receipts, gaps, maximum


def _evidence(corridor: Mapping[str, Any]) -> dict[str, object]:
    if set(corridor) != {*EVIDENCE_KEYS, "contact_tolerance_m", "corridor_sha256"}:
        raise ValueError("corridor schema changed")
    return {key: corridor[key] for key in EVIDENCE_KEYS}


def census_route_corridor_contact_tolerance(
    *,
    map_api: Any,
    opendrive_xml: str,
    camp_execution_head: str,
    carla_version: str,
    carla_module_path: str,
    carla_module_sha256: str,
    client_manifest_sha256: str,
    carla_source_root_sha256: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", camp_execution_head):
        raise ValueError("CAMP execution head must be 40 lowercase hex")
    expected = (
        (FIXED_DP_HEAD, EXPECTED_FIXED_DP_HEAD, "fixed DP head"),
        (carla_version, CARLA_VERSION, "CARLA version"),
        (carla_module_sha256, LIBCARLA_SHA256, "libcarla SHA"),
        (client_manifest_sha256, CLIENT_MANIFEST_SHA256, "client manifest SHA"),
        (carla_source_root_sha256, CARLA_SOURCE_ROOT_SHA256, "CARLA source root"),
        (getattr(map_api, "name", None), MAP_NAME, "map name"),
        (_sha256_bytes(opendrive_xml.encode("utf-8")), XODR_SHA256, "XODR SHA"),
    )
    for actual, frozen, name in expected:
        if actual != frozen:
            raise ValueError(f"{name} mismatch")

    route = _deterministic_route(map_api, 5.0, 81)
    if len(route) != 81:
        raise ValueError("deterministic route must contain 81 points")
    route_records = _route_records(route)
    measurement_ceiling = FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m
    builder_kwargs = {
        "route": route,
        "map_api": map_api,
        "opendrive_xml": opendrive_xml,
        "route_sample_step_m": 5.0,
        "station_allowance_m": FROZEN_LIFTING_TOLERANCES.station_epsilon_m,
    }
    measurement = build_pre_generation_route_corridor(
        **builder_kwargs, contact_tolerance_m=measurement_ceiling
    )
    boundary_receipts, raw_gaps, maximum = _boundary_projection(measurement)
    coordinates = [
        float(value)
        for receipt in boundary_receipts
        for key in ("entry_xyz", "exit_xyz")
        for value in receipt[key]
    ]
    coordinate_scale = max(abs(value) for value in coordinates)
    if coordinate_scale <= 0.0:
        raise ValueError("boundary coordinate scale must be positive")
    frozen = freeze_lifting_tolerances(
        max_chord_error_m=maximum,
        max_station_roundtrip_error_m=0.0,
        max_z_roundtrip_error_m=0.0,
        coordinate_scale_m=coordinate_scale,
    )
    final_tolerance = frozen.geometry_epsilon_m
    final = build_pre_generation_route_corridor(
        **builder_kwargs, contact_tolerance_m=final_tolerance
    )
    final_receipts, final_gaps, final_maximum = _boundary_projection(final)
    measurement_evidence = _evidence(measurement)
    final_evidence = _evidence(final)
    if _canonical_bytes(measurement_evidence) != _canonical_bytes(final_evidence):
        raise ValueError("corridor evidence changed between passes")
    if final_receipts != boundary_receipts or final_gaps != raw_gaps:
        raise ValueError("boundary evidence changed between passes")
    if final_maximum != maximum or final_maximum > final_tolerance:
        raise ValueError("final contact maximum is invalid")

    payload = {
        "schema_version": SCHEMA,
        "provenance": {
            "camp_gate_start_head": CAMP_GATE_START_HEAD,
            "camp_execution_head": camp_execution_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "carla_version": carla_version,
            "carla_source_root_sha256": carla_source_root_sha256,
            "carla_module_path": carla_module_path,
            "carla_module_sha256": carla_module_sha256,
            "client_manifest_sha256": client_manifest_sha256,
            "map_name": MAP_NAME,
            "xodr_sha256": XODR_SHA256,
        },
        "route": {
            "point_count": 81,
            "sample_step_m": 5.0,
            "records": route_records,
            "sha256": canonical_json_sha256(route_records),
        },
        "corridor": {
            "measurement_sha256": measurement["corridor_sha256"],
            "final_sha256": final["corridor_sha256"],
            "evidence": measurement_evidence,
            "evidence_sha256": canonical_json_sha256(measurement_evidence),
            "boundary_identity_receipts": boundary_receipts,
            "boundary_identity_receipts_sha256": canonical_json_sha256(
                boundary_receipts
            ),
            "raw_contact_gaps_m": raw_gaps,
            "max_contact_gap_m": maximum,
        },
        "tolerance": {
            "measurement_ceiling_m": measurement_ceiling,
            "coordinate_scale_m": coordinate_scale,
            "allowance_formula": "max(1e-9, 64*ulp(coordinate_scale_m))",
            "allowance_m": final_tolerance - maximum,
            "frozen_contact_tolerance_m": final_tolerance,
            "builder_contact_tolerances_m": [
                measurement_ceiling,
                final_tolerance,
            ],
        },
        "call_counters": {
            "_deterministic_route": 1,
            "build_pre_generation_route_corridor": 2,
            "freeze_lifting_tolerances": 1,
        },
        "forbidden_access_counters": dict(FORBIDDEN_COUNTERS),
    }
    payload["receipt_sha256"] = canonical_json_sha256(payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args(argv)
    staging = args.output_json.with_suffix(args.output_json.suffix + ".tmp")
    if args.output_json.exists() or staging.exists():
        raise FileExistsError(f"output already exists: {args.output_json}")

    opendrive_xml = XODR_PATH.read_text(encoding="utf-8")
    if _sha256_bytes(opendrive_xml.encode("utf-8")) != XODR_SHA256:
        raise ValueError("official XODR SHA mismatch")
    if _sha256_path(CLIENT_MANIFEST_PATH) != CLIENT_MANIFEST_SHA256:
        raise ValueError("CARLA client manifest SHA mismatch")
    source_root = CARLA_SOURCE_ROOT_RECEIPT.read_text(encoding="utf-8").split()[0]
    if source_root != CARLA_SOURCE_ROOT_SHA256:
        raise ValueError("CARLA source-root receipt mismatch")
    if str(CLIENT_ROOT) not in sys.path:
        sys.path.insert(0, str(CLIENT_ROOT))
    import carla
    import carla.libcarla as libcarla

    carla_version = _distribution_version("carla")
    if carla_version != CARLA_VERSION:
        raise ValueError("CARLA distribution version mismatch")
    module_path = Path(libcarla.__file__).resolve()
    if CLIENT_ROOT.resolve() not in module_path.parents:
        raise ValueError("libcarla is outside the sealed client root")
    module_sha = _sha256_path(module_path)
    if module_sha != LIBCARLA_SHA256:
        raise ValueError("libcarla SHA mismatch")
    map_api = carla.Map(MAP_NAME, opendrive_xml)
    receipt = census_route_corridor_contact_tolerance(
        map_api=map_api,
        opendrive_xml=opendrive_xml,
        camp_execution_head=args.camp_head,
        carla_version=carla_version,
        carla_module_path=str(module_path),
        carla_module_sha256=module_sha,
        client_manifest_sha256=CLIENT_MANIFEST_SHA256,
        carla_source_root_sha256=source_root,
    )
    _write_json_atomic(args.output_json, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

- [ ] **Step 2: Run GREEN focused checks**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py -q
py -3.12 -m py_compile scripts\integrations\census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git diff --check
~~~

Expected: 22 passed, py_compile exits 0 without output, and diff check is
silent. The existing corridor file currently collects 16 cases and the new
file adds six.

- [ ] **Step 3: Run the full relevant regression**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_carla_causal_adapter.py camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py camp_core\tests\test_diffusion_planner_v19_dp_worker.py camp_core\tests\test_diffusion_planner_v19_nuplan_bridge.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
~~~

Expected: 165 passed.

- [ ] **Step 4: Commit only the runner and tests**

~~~powershell
git add -- scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git diff --cached --check
git commit -m "Add v20 map-only contact tolerance census"
~~~

Expected: one new commit with exactly two files. Do not push until local review
passes.

- [ ] **Step 5: Seal the TDD implementation gate**

After an authorized controller pushes the reviewed commit, run:

~~~bash
set -euo pipefail
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
git fetch --prune origin
git pull --ff-only
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_tdd_$STAMP
test ! -e "$ROOT"
mkdir "$ROOT"
CAMP_HEAD=$(git rev-parse HEAD)
DP_HEAD=$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD)
printf 'camp_head=%s\norigin_main=%s\nfixed_dp_head=%s\n' \
  "$CAMP_HEAD" "$(git rev-parse origin/main)" "$DP_HEAD" > "$ROOT/HEADS"
sha256sum \
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py \
  camp_core/camp_core/integrations/carla_causal_adapter.py \
  camp_core/camp_core/integrations/carla_exact_speed_source.py \
  scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py \
  > "$ROOT/SOURCE_SHA256SUMS"
"$TEST_PYTHON" - <<'PY' > "$ROOT/PROCESSES" 2>> "$ROOT/stderr" || printf '{"capture_error":"process_scan_failed"}\n' > "$ROOT/PROCESSES"
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS" 2>> "$ROOT/stderr" || \
  printf 'listener_capture_failed\n' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -euo pipefail
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
export PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core
"$TEST_PYTHON" -m pytest \
  camp_core/tests/test_carla_exact_speed_source.py \
  camp_core/tests/test_carla_causal_adapter.py \
  camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py \
  camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py \
  camp_core/tests/test_diffusion_planner_v19_dp_worker.py \
  camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
"$TEST_PYTHON" -m py_compile \
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git diff --check
test -z "$(git status --short --untracked-files=no)"
SH
set +e
bash "$ROOT/COMMAND" > "$ROOT/stdout" 2> "$ROOT/stderr"
STATUS=$?
set -e
test ! -s "$ROOT/PROCESSES" || STATUS=1
test ! -s "$ROOT/LISTENERS" || STATUS=1
printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS"
ARTIFACT_ROOT="$ROOT" STATUS="$STATUS" CAMP_HEAD="$CAMP_HEAD" "$TEST_PYTHON" - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ARTIFACT_ROOT"])
status = int(os.environ["STATUS"])
data = {
    "status": "pass" if status == 0 else "fail",
    "exit_status": status,
    "camp_head": os.environ["CAMP_HEAD"],
    "map_constructed": False,
    "census_executed": False,
}
(root / "implementation.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
(root / "implementation.md").write_text(
    "# V20 contact-tolerance TDD implementation\n\n"
    f"status: {data['status']}\nmap_constructed: false\ncensus_executed: false\n"
)
PY
(cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS implementation.json implementation.md PROCESSES LISTENERS SOURCE_SHA256SUMS > SHA256SUMS)
(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256)
test "$STATUS" -eq 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
~~~

Expected: 165 passed, EXIT_STATUS 0, implementation.json status pass, no map
or census execution, empty process/listener evidence, and a valid manifest/root
hash. Independently rehash this artifact before Task 4.

---

### Task 4: Run the no-run preflight

**Files:**

- Verify only: committed runner, test, existing builder/freezer/probe modules.
- Artifact JSON: preflight.json.
- Artifact MD: preflight.md.

**Interfaces:**

- Consumes: reviewed Task 3 commit.
- Produces: exact future execution root and argv without constructing a map.

- [ ] **Step 1: Push the reviewed implementation and run this exact preflight**

The authorized controller performs its git network action with the required
network prefix, then runs:

~~~bash
set -uo pipefail
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
EXPECTED_TEST_PYTHON_RESOLVED=/root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9
EXPECTED_TEST_PYTHON_VERSION='Python 3.9.23'
EXPECTED_TEST_PYTHON_SHA256=d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c
CARLA_PYTHON=/root/miniconda3/bin/python3.12
EXPECTED_CARLA_PYTHON_RESOLVED=/root/miniconda3/bin/python3.12
EXPECTED_CARLA_PYTHON_VERSION='Python 3.12.3'
EXPECTED_CARLA_PYTHON_SHA256=0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_preflight_$STAMP
EXECUTION_ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_$STAMP
mkdir "$ROOT" || { printf 'artifact root allocation failed: %s\n' "$ROOT" >&2; exit 1; }
: > "$ROOT/stdout"
: > "$ROOT/stderr"
: > "$ROOT/PROCESSES"
: > "$ROOT/LISTENERS"
STATUS=0
fail() {
  printf '%s\n' "$1" >> "$ROOT/stderr"
  STATUS=1
}
source /etc/network_turbo >/dev/null 2>&1 || true
git fetch --prune origin >> "$ROOT/stdout" 2>> "$ROOT/stderr" || fail git_fetch_failed
git pull --ff-only >> "$ROOT/stdout" 2>> "$ROOT/stderr" || fail git_pull_failed
CAMP_HEAD=$(git rev-parse HEAD 2>/dev/null || printf missing)
ORIGIN_HEAD=$(git rev-parse origin/main 2>/dev/null || printf missing)
DP_HEAD=$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD 2>/dev/null || printf missing)
test -x "$TEST_PYTHON" || fail test_python_not_executable
test -x "$CARLA_PYTHON" || fail carla_python_not_executable
TEST_PYTHON_RESOLVED=$(readlink -f "$TEST_PYTHON" 2>/dev/null || printf missing)
CARLA_PYTHON_RESOLVED=$(readlink -f "$CARLA_PYTHON" 2>/dev/null || printf missing)
TEST_PYTHON_VERSION=$("$TEST_PYTHON" --version 2>&1) || fail test_python_version_query_failed
CARLA_PYTHON_VERSION=$("$CARLA_PYTHON" --version 2>&1) || fail carla_python_version_query_failed
TEST_PYTHON_SHA256=$(sha256sum "$TEST_PYTHON_RESOLVED" 2>> "$ROOT/stderr" | awk '{print $1}') || fail test_python_hash_failed
CARLA_PYTHON_SHA256=$(sha256sum "$CARLA_PYTHON_RESOLVED" 2>> "$ROOT/stderr" | awk '{print $1}') || fail carla_python_hash_failed
printf 'camp_head=%s\norigin_main=%s\nfixed_dp_head=%s\n' \
  "$CAMP_HEAD" "$ORIGIN_HEAD" "$DP_HEAD" > "$ROOT/HEADS"
cat > "$ROOT/COMMAND" <<EOF
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core $CARLA_PYTHON /root/autodl-tmp/camp_core/scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py --camp-head $CAMP_HEAD --output-json $EXECUTION_ROOT/receipt.json
EOF
test "$CAMP_HEAD" = "$ORIGIN_HEAD" || fail camp_origin_head_mismatch
test -z "$(git status --short --untracked-files=no)" || fail camp_tracked_tree_dirty
test "$DP_HEAD" = 7a1d33da277a1992ec474b5383a0c963c72e04e4 || fail fixed_dp_head_mismatch
test -z "$(git -C /root/autodl-tmp/Diffusion-Planner status --short --untracked-files=no)" || fail fixed_dp_tracked_tree_dirty
test "$TEST_PYTHON_RESOLVED" = "$EXPECTED_TEST_PYTHON_RESOLVED" || fail test_python_resolved_path_mismatch
test "$CARLA_PYTHON_RESOLVED" = "$EXPECTED_CARLA_PYTHON_RESOLVED" || fail carla_python_resolved_path_mismatch
test "$TEST_PYTHON_VERSION" = "$EXPECTED_TEST_PYTHON_VERSION" || fail test_python_version_mismatch
test "$CARLA_PYTHON_VERSION" = "$EXPECTED_CARLA_PYTHON_VERSION" || fail carla_python_version_mismatch
test "$TEST_PYTHON_SHA256" = "$EXPECTED_TEST_PYTHON_SHA256" || fail test_python_sha256_mismatch
test "$CARLA_PYTHON_SHA256" = "$EXPECTED_CARLA_PYTHON_SHA256" || fail carla_python_sha256_mismatch
sha256sum "$TEST_PYTHON_RESOLVED" "$CARLA_PYTHON_RESOLVED" > "$ROOT/RUNTIME_SHA256SUMS" 2>> "$ROOT/stderr" || fail runtime_hash_generation_failed
sha256sum \
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py \
  camp_core/camp_core/integrations/carla_causal_adapter.py \
  camp_core/camp_core/integrations/carla_exact_speed_source.py \
  scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py \
  > "$ROOT/SOURCE_SHA256SUMS" 2>> "$ROOT/stderr" || fail source_hash_generation_failed
"$TEST_PYTHON" - <<'PY' > "$ROOT/PROCESSES" 2>> "$ROOT/stderr" || fail process_capture_failed
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS" 2>> "$ROOT/stderr" || fail listener_capture_failed
test ! -s "$ROOT/PROCESSES" || fail related_process_detected
test ! -s "$ROOT/LISTENERS" || fail carla_listener_detected
FREE_BYTES=$(df --output=avail -B1 /root/autodl-tmp 2>> "$ROOT/stderr" | tail -1 | tr -d ' ')
case "$FREE_BYTES" in
  ''|*[!0-9]*) fail disk_query_failed; FREE_BYTES=0 ;;
esac
test "$FREE_BYTES" -ge 10737418240 || fail disk_floor_failed
XODR=/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD_Opt.xodr
test "$(sha256sum "$XODR" 2>> "$ROOT/stderr" | awk '{print $1}')" = 5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7 || fail xodr_hash_mismatch
test "$(sha256sum /root/autodl-tmp/camp_v19_carla_client/CLIENT_SHA256SUMS 2>> "$ROOT/stderr" | awk '{print $1}')" = ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e || fail client_manifest_hash_mismatch
LIBCARLA=$(find /root/autodl-tmp/camp_v19_carla_client -type f -name 'libcarla.cpython-312-x86_64-linux-gnu.so' -print 2>> "$ROOT/stderr") || fail libcarla_search_failed
test "$(printf '%s\n' "$LIBCARLA" | sed '/^$/d' | wc -l)" -eq 1 || fail libcarla_count_mismatch
test "$(sha256sum "$LIBCARLA" 2>> "$ROOT/stderr" | awk '{print $1}')" = c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2 || fail libcarla_hash_mismatch
test "$(awk '{print $1; exit}' /root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_20260713T000320CST/ROOT_SHA256)" = 2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce || fail source_root_hash_mismatch
IMPORTED_LIBCARLA=$(PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client "$CARLA_PYTHON" - 2>> "$ROOT/stderr" <<'PY'
from importlib.metadata import version
import carla.libcarla as libcarla
assert version("carla") == "0.9.16"
from pathlib import Path
print(Path(libcarla.__file__).resolve())
PY
) || fail carla_import_failed
printf '%s\n' "$IMPORTED_LIBCARLA" > "$ROOT/CARLA_MODULE_PATH"
test "$IMPORTED_LIBCARLA" = "$(readlink -f "$LIBCARLA")" || fail imported_libcarla_path_mismatch
test ! -e "$EXECUTION_ROOT" || fail execution_root_exists
test ! -e "$EXECUTION_ROOT/receipt.json" || fail output_json_exists
test ! -e "$EXECUTION_ROOT/receipt.json.tmp" || fail output_tmp_exists
test "$(grep -Eoc -- '--host|--port|CarlaUE4|carla.Client' "$ROOT/COMMAND")" -eq 0 || fail forbidden_execution_argv
COMMAND_SHA256=$(sha256sum "$ROOT/COMMAND" | awk '{print $1}')
write_summary() {
  ARTIFACT_ROOT="$ROOT" EXECUTION_ROOT="$EXECUTION_ROOT" PYTHON_PATH="$CARLA_PYTHON" \
  TEST_PYTHON_PATH="$TEST_PYTHON" TEST_PYTHON_RESOLVED="$TEST_PYTHON_RESOLVED" \
  TEST_PYTHON_VERSION="$TEST_PYTHON_VERSION" TEST_PYTHON_SHA256="$TEST_PYTHON_SHA256" \
  CARLA_PYTHON_RESOLVED="$CARLA_PYTHON_RESOLVED" CARLA_PYTHON_VERSION="$CARLA_PYTHON_VERSION" \
  CARLA_PYTHON_SHA256="$CARLA_PYTHON_SHA256" \
  FREE_BYTES="$FREE_BYTES" LIBCARLA_PATH="$LIBCARLA" \
  IMPORTED_LIBCARLA_PATH="$IMPORTED_LIBCARLA" COMMAND_SHA256="$COMMAND_SHA256" \
  CAMP_HEAD="$CAMP_HEAD" STATUS="$STATUS" \
  "$TEST_PYTHON" - 2>> "$ROOT/stderr" <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ARTIFACT_ROOT"])
status = int(os.environ["STATUS"])
data = {
    "status": "pass" if status == 0 else "fail",
    "exit_status": status,
    "camp_head": os.environ["CAMP_HEAD"],
    "python_path": os.environ["PYTHON_PATH"],
    "test_python_path": os.environ["TEST_PYTHON_PATH"],
    "test_python_resolved": os.environ["TEST_PYTHON_RESOLVED"],
    "test_python_version": os.environ["TEST_PYTHON_VERSION"],
    "test_python_sha256": os.environ["TEST_PYTHON_SHA256"],
    "carla_python_path": os.environ["PYTHON_PATH"],
    "carla_python_resolved": os.environ["CARLA_PYTHON_RESOLVED"],
    "carla_python_version": os.environ["CARLA_PYTHON_VERSION"],
    "carla_python_sha256": os.environ["CARLA_PYTHON_SHA256"],
    "carla_version": "0.9.16",
    "selected_libcarla_path": os.environ["LIBCARLA_PATH"],
    "imported_libcarla_path": os.environ["IMPORTED_LIBCARLA_PATH"],
    "map_constructor": 'carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)',
    "execution_root": os.environ["EXECUTION_ROOT"],
    "output_json": os.environ["EXECUTION_ROOT"] + "/receipt.json",
    "output_tmp": os.environ["EXECUTION_ROOT"] + "/receipt.json.tmp",
    "free_bytes": int(os.environ["FREE_BYTES"]),
    "command_sha256": os.environ["COMMAND_SHA256"],
    "related_processes": (root / "PROCESSES").read_text().splitlines(),
    "listeners_2000_2001": (root / "LISTENERS").read_text().splitlines(),
}
(root / "preflight.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
(root / "preflight.md").write_text(
    "# V20 contact-tolerance census no-run preflight\n\n"
    f"status: {data['status']}\nexit_status: {status}\n"
)
PY
}
seal() {
  test "$SUMMARY_OK" = true \
    && printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS" \
    && (cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS preflight.json preflight.md PROCESSES LISTENERS SOURCE_SHA256SUMS RUNTIME_SHA256SUMS CARLA_MODULE_PATH > SHA256SUMS) \
    && (cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256) \
    && (cd "$ROOT" && sha256sum -c SHA256SUMS > /dev/null) 2>> "$ROOT/stderr" \
    && test "$(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$ROOT/ROOT_SHA256")"
}
SUMMARY_OK=false
write_summary && SUMMARY_OK=true
test "$SUMMARY_OK" = true || STATUS=1
if ! seal; then
  STATUS=1
  SUMMARY_OK=false
  write_summary && SUMMARY_OK=true
  seal || exit 1
fi
test "$STATUS" -eq 0
~~~

Expected pass: no map is constructed; EXIT_STATUS is 0; preflight.json status
is pass; PROCESSES and LISTENERS are empty; the imported and selected libcarla
paths match exactly and are sealed; execution_root, output_json, output_tmp,
Python, heads, hashes, and argv are exact. Any failed check records status fail,
its evidence and stderr, then seals before the final nonzero exit. A summary or
first-seal failure sets STATUS=1 and permits exactly one fail-marked reseal;
failure of that reseal exits nonzero.

- [ ] **Step 2: Independently review the preflight without execution**

Run:

~~~bash
set -euo pipefail
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
CAMP_HEAD=$(git rev-parse HEAD)
ROOT=$("$TEST_PYTHON" - "$CAMP_HEAD" <<'PY'
import json
import sys
from pathlib import Path
head = sys.argv[1]
matches = []
for path in Path("/root/autodl-tmp").glob(
    "camp_dp_v20_carla_contact_tolerance_preflight_*/preflight.json"
):
    data = json.loads(path.read_text())
    if data.get("status") == "pass" and data.get("camp_head") == head:
        matches.append(path.parent)
if len(matches) != 1:
    raise SystemExit(f"expected one passing preflight, found {len(matches)}")
print(matches[0])
PY
)
(cd "$ROOT" && sha256sum -c SHA256SUMS)
(cd /root/autodl-tmp/camp_core && sha256sum -c "$ROOT/SOURCE_SHA256SUMS")
(cd / && sha256sum -c "$ROOT/RUNTIME_SHA256SUMS")
test "$(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$ROOT/ROOT_SHA256")"
test "$(cat "$ROOT/EXIT_STATUS")" = 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
"$TEST_PYTHON" - "$ROOT/preflight.json" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert data["status"] == "pass"
assert data["free_bytes"] >= 10737418240
assert data["python_path"] == "/root/miniconda3/bin/python3.12"
assert data["test_python_path"] == "/root/autodl-tmp/camp_v19_nuplan_env/bin/python"
assert data["test_python_resolved"] == "/root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9"
assert data["test_python_version"] == "Python 3.9.23"
assert data["test_python_sha256"] == "d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c"
assert data["carla_python_path"] == "/root/miniconda3/bin/python3.12"
assert data["carla_python_resolved"] == "/root/miniconda3/bin/python3.12"
assert data["carla_python_version"] == "Python 3.12.3"
assert data["carla_python_sha256"] == "0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1"
assert data["map_constructor"] == 'carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)'
assert data["selected_libcarla_path"] == data["imported_libcarla_path"]
assert data["command_sha256"] == __import__("hashlib").sha256(
    (Path(sys.argv[1]).parent / "COMMAND").read_bytes()
).hexdigest()
for key in ("execution_root", "output_json", "output_tmp"):
    assert not Path(data[key]).exists()
PY
test "$(grep -Eoc -- '--host|--port|CarlaUE4|carla.Client' "$ROOT/COMMAND")" -eq 0
~~~

Any mismatch stops before Task 5. This check does not import CARLA or construct
carla.Map.

---

### Task 5: Execute exactly once

**Files:**

- Produce execution receipt.json and result.json/result.md only.
- Do not modify tracked files.

**Interfaces:**

- Consumes: one independently reviewed passing preflight.
- Produces: one sealed execution artifact, whether pass or fail.

- [ ] **Step 1: Derive the unique reviewed preflight and run its frozen command once**

~~~bash
set -uo pipefail
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
EXPECTED_TEST_PYTHON_RESOLVED=/root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9
EXPECTED_TEST_PYTHON_VERSION='Python 3.9.23'
EXPECTED_TEST_PYTHON_SHA256=d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c
CARLA_PYTHON=/root/miniconda3/bin/python3.12
EXPECTED_CARLA_PYTHON_RESOLVED=/root/miniconda3/bin/python3.12
EXPECTED_CARLA_PYTHON_VERSION='Python 3.12.3'
EXPECTED_CARLA_PYTHON_SHA256=0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1
CAMP_HEAD=$(git rev-parse HEAD)
ORIGIN_HEAD=$(git rev-parse origin/main)
DP_HEAD=$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD)
PREFLIGHT_ROOT=$("$TEST_PYTHON" - "$CAMP_HEAD" <<'PY'
import json
import sys
from pathlib import Path
head = sys.argv[1]
matches = []
for path in Path("/root/autodl-tmp").glob(
    "camp_dp_v20_carla_contact_tolerance_preflight_*/preflight.json"
):
    data = json.loads(path.read_text())
    if data.get("status") == "pass" and data.get("camp_head") == head:
        matches.append(path.parent)
if len(matches) != 1:
    print("")
else:
    print(matches[0])
PY
)
EXECUTION_ROOT_FROM_PREFLIGHT=
if test -n "$PREFLIGHT_ROOT"; then
  EXECUTION_ROOT_FROM_PREFLIGHT=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("execution_root", ""))' "$PREFLIGHT_ROOT/preflight.json")
fi
case "$EXECUTION_ROOT_FROM_PREFLIGHT" in
  /root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_*)
    EXECUTION_ROOT=$EXECUTION_ROOT_FROM_PREFLIGHT
    ;;
  *)
  STAMP=$(date -u +%Y%m%dT%H%M%SZ)
  EXECUTION_ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_selection_failure_$STAMP
    ;;
esac
ROOT_WAS_ABSENT=true
if ! mkdir "$EXECUTION_ROOT" 2>/dev/null; then
  ROOT_WAS_ABSENT=false
  STAMP=$(date -u +%Y%m%dT%H%M%SZ)
  EXECUTION_ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_existing_root_failure_$STAMP
  mkdir "$EXECUTION_ROOT" || { printf 'artifact root allocation failed: %s\n' "$EXECUTION_ROOT" >&2; exit 1; }
fi
printf 'camp_head=%s\norigin_main=%s\nfixed_dp_head=%s\n' \
  "$CAMP_HEAD" "$ORIGIN_HEAD" "$DP_HEAD" > "$EXECUTION_ROOT/HEADS"
: > "$EXECUTION_ROOT/COMMAND"
: > "$EXECUTION_ROOT/SOURCE_SHA256SUMS"
: > "$EXECUTION_ROOT/RUNTIME_SHA256SUMS"
printf '{}\n' > "$EXECUTION_ROOT/preflight.json"
: > "$EXECUTION_ROOT/stdout"
: > "$EXECUTION_ROOT/stderr"
: > "$EXECUTION_ROOT/PROCESSES.before"
: > "$EXECUTION_ROOT/LISTENERS.before"
: > "$EXECUTION_ROOT/PROCESSES.after"
: > "$EXECUTION_ROOT/LISTENERS.after"
STATUS=0
CENSUS_INVOKED=false
PREFLIGHT_REVERIFIED=false
fail() {
  printf '%s\n' "$1" >> "$EXECUTION_ROOT/stderr"
  STATUS=1
}
test -n "$PREFLIGHT_ROOT" || fail unique_passing_preflight_not_found
test -n "$EXECUTION_ROOT_FROM_PREFLIGHT" || fail frozen_execution_root_missing_or_invalid
test "$ROOT_WAS_ABSENT" = true || fail frozen_execution_root_already_existed
if test -n "$PREFLIGHT_ROOT"; then
  cp "$PREFLIGHT_ROOT/COMMAND" "$EXECUTION_ROOT/COMMAND" || fail preflight_command_copy_failed
  cp "$PREFLIGHT_ROOT/preflight.json" "$EXECUTION_ROOT/preflight.json" || fail preflight_json_copy_failed
  cp "$PREFLIGHT_ROOT/SOURCE_SHA256SUMS" "$EXECUTION_ROOT/SOURCE_SHA256SUMS" || fail preflight_source_manifest_copy_failed
  cp "$PREFLIGHT_ROOT/RUNTIME_SHA256SUMS" "$EXECUTION_ROOT/RUNTIME_SHA256SUMS" || fail preflight_runtime_manifest_copy_failed
  cp "$PREFLIGHT_ROOT/CARLA_MODULE_PATH" "$EXECUTION_ROOT/CARLA_MODULE_PATH" || fail preflight_carla_path_copy_failed
  (cd "$PREFLIGHT_ROOT" && sha256sum -c SHA256SUMS) \
    >> "$EXECUTION_ROOT/stdout" 2>> "$EXECUTION_ROOT/stderr" \
    || fail preflight_manifest_invalid
  test "$(cd "$PREFLIGHT_ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$PREFLIGHT_ROOT/ROOT_SHA256")" \
    || fail preflight_root_hash_invalid
  (cd /root/autodl-tmp/camp_core && sha256sum -c "$PREFLIGHT_ROOT/SOURCE_SHA256SUMS") \
    >> "$EXECUTION_ROOT/stdout" 2>> "$EXECUTION_ROOT/stderr" \
    || fail preflight_source_hashes_drifted
  (cd / && sha256sum -c "$PREFLIGHT_ROOT/RUNTIME_SHA256SUMS") \
    >> "$EXECUTION_ROOT/stdout" 2>> "$EXECUTION_ROOT/stderr" \
    || fail preflight_runtime_hashes_drifted
  test "$(cat "$PREFLIGHT_ROOT/EXIT_STATUS")" = 0 || fail preflight_exit_nonzero
  PREFLIGHT_STATUS=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_JSON_EXIT=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("exit_status"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_CAMP_HEAD=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("camp_head"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_COMMAND_SHA=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("command_sha256"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_OUTPUT=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("output_json"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_OUTPUT_TMP=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("output_tmp"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_PYTHON=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("python_path"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_TEST_PYTHON=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("test_python_path"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_SELECTED_LIB=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("selected_libcarla_path"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_IMPORTED_LIB=$("$TEST_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("imported_libcarla_path"))' "$PREFLIGHT_ROOT/preflight.json")
  PREFLIGHT_HEAD_CAMP=$(awk -F= '$1=="camp_head" {print $2}' "$PREFLIGHT_ROOT/HEADS")
  PREFLIGHT_HEAD_ORIGIN=$(awk -F= '$1=="origin_main" {print $2}' "$PREFLIGHT_ROOT/HEADS")
  PREFLIGHT_HEAD_DP=$(awk -F= '$1=="fixed_dp_head" {print $2}' "$PREFLIGHT_ROOT/HEADS")
  test "$PREFLIGHT_STATUS" = pass || fail preflight_status_not_pass
  test "$PREFLIGHT_JSON_EXIT" = 0 || fail preflight_json_exit_nonzero
  test "$PREFLIGHT_CAMP_HEAD" = "$CAMP_HEAD" || fail preflight_camp_head_mismatch
  test "$PREFLIGHT_HEAD_CAMP" = "$CAMP_HEAD" || fail preflight_heads_camp_mismatch
  test "$PREFLIGHT_HEAD_ORIGIN" = "$ORIGIN_HEAD" || fail preflight_heads_origin_mismatch
  test "$PREFLIGHT_HEAD_DP" = "$DP_HEAD" || fail preflight_heads_fixed_dp_mismatch
  test "$PREFLIGHT_PYTHON" = /root/miniconda3/bin/python3.12 || fail preflight_carla_python_mismatch
  test "$PREFLIGHT_TEST_PYTHON" = "$TEST_PYTHON" || fail preflight_test_python_mismatch
  test -x "$TEST_PYTHON" || fail point_of_use_test_python_not_executable
  test -x "$CARLA_PYTHON" || fail point_of_use_carla_python_not_executable
  test "$(readlink -f "$TEST_PYTHON")" = "$EXPECTED_TEST_PYTHON_RESOLVED" || fail point_of_use_test_python_resolved_path_mismatch
  test "$(readlink -f "$CARLA_PYTHON")" = "$EXPECTED_CARLA_PYTHON_RESOLVED" || fail point_of_use_carla_python_resolved_path_mismatch
  test "$("$TEST_PYTHON" --version 2>&1)" = "$EXPECTED_TEST_PYTHON_VERSION" || fail point_of_use_test_python_version_mismatch
  test "$("$CARLA_PYTHON" --version 2>&1)" = "$EXPECTED_CARLA_PYTHON_VERSION" || fail point_of_use_carla_python_version_mismatch
  test "$(sha256sum "$EXPECTED_TEST_PYTHON_RESOLVED" | awk '{print $1}')" = "$EXPECTED_TEST_PYTHON_SHA256" || fail point_of_use_test_python_sha256_mismatch
  test "$(sha256sum "$EXPECTED_CARLA_PYTHON_RESOLVED" | awk '{print $1}')" = "$EXPECTED_CARLA_PYTHON_SHA256" || fail point_of_use_carla_python_sha256_mismatch
  test "$PREFLIGHT_SELECTED_LIB" = "$PREFLIGHT_IMPORTED_LIB" || fail preflight_libcarla_path_mismatch
  test "$(cat "$PREFLIGHT_ROOT/CARLA_MODULE_PATH")" = "$PREFLIGHT_IMPORTED_LIB" || fail preflight_libcarla_evidence_mismatch
  test "$CAMP_HEAD" = "$ORIGIN_HEAD" || fail point_of_use_origin_head_mismatch
  test "$DP_HEAD" = 7a1d33da277a1992ec474b5383a0c963c72e04e4 || fail point_of_use_fixed_dp_head_mismatch
  test -z "$(git status --short --untracked-files=no)" || fail point_of_use_camp_tree_dirty
  test -z "$(git -C /root/autodl-tmp/Diffusion-Planner status --short --untracked-files=no)" || fail point_of_use_fixed_dp_tree_dirty
  test "$(sha256sum "$EXECUTION_ROOT/COMMAND" | awk '{print $1}')" = "$PREFLIGHT_COMMAND_SHA" || fail frozen_command_hash_mismatch
  EXPECTED_COMMAND="PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core $PREFLIGHT_PYTHON /root/autodl-tmp/camp_core/scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py --camp-head $CAMP_HEAD --output-json $PREFLIGHT_OUTPUT"
  test "$(cat "$EXECUTION_ROOT/COMMAND")" = "$EXPECTED_COMMAND" || fail frozen_command_literal_mismatch
  test "$(grep -Eoc -- '--host|--port|CarlaUE4|carla.Client' "$EXECUTION_ROOT/COMMAND")" -eq 0 || fail forbidden_execution_argv
  test "$PREFLIGHT_OUTPUT" = "$EXECUTION_ROOT/receipt.json" || fail frozen_output_path_mismatch
  test "$PREFLIGHT_OUTPUT_TMP" = "$EXECUTION_ROOT/receipt.json.tmp" || fail frozen_tmp_path_mismatch
  test ! -e "$PREFLIGHT_OUTPUT" || fail output_json_exists
  test ! -e "$PREFLIGHT_OUTPUT_TMP" || fail output_tmp_exists
fi
"$TEST_PYTHON" - <<'PY' > "$EXECUTION_ROOT/PROCESSES.before" 2>> "$EXECUTION_ROOT/stderr" || fail point_of_use_process_capture_failed
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$EXECUTION_ROOT/LISTENERS.before" 2>> "$EXECUTION_ROOT/stderr" || fail point_of_use_listener_capture_failed
test ! -s "$EXECUTION_ROOT/PROCESSES.before" || fail point_of_use_related_process_detected
test ! -s "$EXECUTION_ROOT/LISTENERS.before" || fail point_of_use_carla_listener_detected
if test "$STATUS" -eq 0; then
  PREFLIGHT_REVERIFIED=true
  CENSUS_INVOKED=true
  bash "$EXECUTION_ROOT/COMMAND" >> "$EXECUTION_ROOT/stdout" 2>> "$EXECUTION_ROOT/stderr"
  STATUS=$?
fi
if test "$CENSUS_INVOKED" = true; then
  test -f "$EXECUTION_ROOT/receipt.json" || fail receipt_missing
  test ! -e "$EXECUTION_ROOT/receipt.json.tmp" || fail output_tmp_left_behind
fi
"$TEST_PYTHON" - <<'PY' > "$EXECUTION_ROOT/PROCESSES.after" 2>> "$EXECUTION_ROOT/stderr" || fail post_execution_process_capture_failed
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$EXECUTION_ROOT/LISTENERS.after" 2>> "$EXECUTION_ROOT/stderr" || fail post_execution_listener_capture_failed
test ! -s "$EXECUTION_ROOT/PROCESSES.after" || fail post_execution_related_process_detected
test ! -s "$EXECUTION_ROOT/LISTENERS.after" || fail post_execution_carla_listener_detected
write_summary() {
  ARTIFACT_ROOT="$EXECUTION_ROOT" STATUS="$STATUS" \
  PREFLIGHT_REVERIFIED="$PREFLIGHT_REVERIFIED" CENSUS_INVOKED="$CENSUS_INVOKED" \
  "$TEST_PYTHON" - 2>> "$EXECUTION_ROOT/stderr" <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ARTIFACT_ROOT"])
status = int(os.environ["STATUS"])
data = {
    "status": "pass" if status == 0 and (root / "receipt.json").is_file() else "fail",
    "exit_status": status,
    "receipt_present": (root / "receipt.json").is_file(),
    "preflight_reverified": os.environ["PREFLIGHT_REVERIFIED"] == "true",
    "census_invoked": os.environ["CENSUS_INVOKED"] == "true",
    "point_of_use_process_rows": (root / "PROCESSES.before").read_text().splitlines(),
    "point_of_use_listener_rows": (root / "LISTENERS.before").read_text().splitlines(),
}
(root / "result.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
(root / "result.md").write_text(
    "# V20 offline map-only census execution\n\n"
    f"status: {data['status']}\nexit_status: {status}\n"
)
PY
}
seal() {
  test "$SUMMARY_OK" = true \
    && printf '%s\n' "$STATUS" > "$EXECUTION_ROOT/EXIT_STATUS" \
    && (cd "$EXECUTION_ROOT" && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name ROOT_SHA256 -printf '%f\n' | LC_ALL=C sort | xargs sha256sum > SHA256SUMS) \
    && (cd "$EXECUTION_ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256) \
    && (cd "$EXECUTION_ROOT" && sha256sum -c SHA256SUMS > /dev/null) 2>> "$EXECUTION_ROOT/stderr" \
    && test "$(cd "$EXECUTION_ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$EXECUTION_ROOT/ROOT_SHA256")"
}
SUMMARY_OK=false
write_summary && SUMMARY_OK=true
test "$SUMMARY_OK" = true || STATUS=1
if ! seal; then
  STATUS=1
  SUMMARY_OK=false
  write_summary && SUMMARY_OK=true
  seal || exit 1
fi
test "$STATUS" -eq 0
~~~

Expected pass: both sealed interpreter identities are point-of-use-reverified,
and the copied COMMAND is invoked
exactly once; EXIT_STATUS is 0; receipt.json and result.json/result.md exist;
fresh process/listener evidence is empty; all files are sealed. If any
preflight, source, provenance, command, output-path, process, or listener check
fails, census_invoked is false, no census command runs, and the nonzero failure
artifact is still sealed. A post-execution detection also seals terminal fail.
A summary or first-seal failure sets STATUS=1 and permits exactly one
fail-marked reseal; failure of that reseal exits nonzero.

---

### Task 6: Independently review without rerunning

**Files:**

- Read the execution artifact only.
- Produce review.json and review.md in a new sealed review root.

**Interfaces:**

- Consumes: one execution artifact.
- Produces: pass/fail reconstruction and the next legal target.

- [ ] **Step 1: Run the exact independent reconstruction**

~~~bash
set -uo pipefail
cd /root/autodl-tmp/camp_core
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
CAMP_HEAD=$(git rev-parse HEAD)
EXECUTION_ROOT=$("$TEST_PYTHON" - "$CAMP_HEAD" <<'PY'
import sys
from pathlib import Path
head = sys.argv[1]
matches = []
for root in Path("/root/autodl-tmp").glob(
    "camp_dp_v20_carla_contact_tolerance_execution_*"
):
    heads_path = root / "HEADS"
    exit_path = root / "EXIT_STATUS"
    if not heads_path.is_file() or not exit_path.is_file():
        continue
    heads = dict(
        line.split("=", 1) for line in heads_path.read_text().splitlines()
    )
    if heads.get("camp_head") == head:
        matches.append(root)
if len(matches) != 1:
    raise SystemExit(f"expected one execution, found {len(matches)}")
print(matches[0])
PY
)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_review_$STAMP
mkdir "$ROOT" || { printf 'artifact root allocation failed: %s\n' "$ROOT" >&2; exit 1; }
cp "$EXECUTION_ROOT/HEADS" "$ROOT/HEADS"
cp "$EXECUTION_ROOT/SOURCE_SHA256SUMS" "$ROOT/SOURCE_SHA256SUMS" 2>/dev/null || : > "$ROOT/SOURCE_SHA256SUMS"
cp "$EXECUTION_ROOT/RUNTIME_SHA256SUMS" "$ROOT/RUNTIME_SHA256SUMS" 2>/dev/null || : > "$ROOT/RUNTIME_SHA256SUMS"
: > "$ROOT/stdout"
: > "$ROOT/stderr"
"$TEST_PYTHON" - <<'PY' > "$ROOT/PROCESSES" 2>> "$ROOT/stderr" || printf '{"capture_error":"process_scan_failed"}\n' > "$ROOT/PROCESSES"
import json
from pathlib import Path
targets = {
    "CarlaUE4-Linux-Shipping",
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py",
    "run_diffusion_planner_dp_camp_v19_worker.py",
}
rows = []
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode(errors="replace") for part in path.read_bytes().split(b"\0") if part]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(Path(arg).name in targets for arg in argv):
        rows.append({"pid": int(path.parent.name), "argv": argv})
if rows:
    print(json.dumps(rows, sort_keys=True))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS" 2>> "$ROOT/stderr" \
  || printf 'listener_capture_failed\n' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -uo pipefail
TEST_PYTHON=/root/autodl-tmp/camp_v19_nuplan_env/bin/python
PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core \
"$TEST_PYTHON" - <<'PY'
import json
import math
import os
import traceback
from pathlib import Path
from camp_core.integrations.carla_exact_speed_source import (
    canonical_json_sha256,
    freeze_lifting_tolerances,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe import (
    FROZEN_LIFTING_TOLERANCES,
)

execution = Path(os.environ["EXECUTION_ROOT"])
review = Path(os.environ["ARTIFACT_ROOT"])
heads = dict(
    line.split("=", 1)
    for line in (execution / "HEADS").read_text().splitlines()
)
execution_exit = (execution / "EXIT_STATUS").read_text().strip()
receipt_path = execution / "receipt.json"
BOUNDARY_KEYS = (
    "identity",
    "direction",
    "exact_entry_s",
    "exact_exit_s",
    "lookup_entry_s",
    "lookup_exit_s",
    "entry_xyz",
    "exit_xyz",
    "contact_to_next_m",
    "identity_verified",
)
expected_calls = {
    "_deterministic_route": 1,
    "build_pre_generation_route_corridor": 2,
    "freeze_lifting_tolerances": 1,
}
expected_forbidden = {
    "server_connections": 0,
    "server_launches": 0,
    "world_gets": 0,
    "actor_spawns": 0,
    "world_ticks": 0,
    "candidate_reads": 0,
    "dp_request_reads": 0,
    "dp_worker_calls": 0,
    "outcome_reads": 0,
    "metric_calls": 0,
    "future_label_reads": 0,
    "holdout_reads": 0,
    "selector_calls": 0,
    "eligibility_calls": 0,
}
checks = {
    "execution_manifest_valid": os.environ["EXECUTION_MANIFEST_VALID"] == "true",
    "execution_root_hash_valid": os.environ["EXECUTION_ROOT_HASH_VALID"] == "true",
    "source_hashes_valid": os.environ["SOURCE_HASHES_VALID"] == "true",
    "runtime_hashes_valid": os.environ["RUNTIME_HASHES_VALID"] == "true",
    "execution_exit_zero": execution_exit == "0",
    "receipt_present": receipt_path.is_file(),
    "processes_empty": not (execution / "PROCESSES.before").read_text() and not (execution / "PROCESSES.after").read_text(),
    "listeners_empty": not (execution / "LISTENERS.before").read_text() and not (execution / "LISTENERS.after").read_text(),
    "review_processes_empty": not (review / "PROCESSES").read_text(),
    "review_listeners_empty": not (review / "LISTENERS").read_text(),
}
error = None
if receipt_path.is_file():
    try:
        receipt = json.loads(receipt_path.read_text())
        sealed = dict(receipt)
        receipt_sha = sealed.pop("receipt_sha256")
        provenance = receipt["provenance"]
        corridor = receipt["corridor"]
        tolerance = receipt["tolerance"]
        evidence = corridor["evidence"]
        evidence_boundaries = evidence["boundary_receipts"]
        documented_boundaries = [
            {key: row[key] for key in BOUNDARY_KEYS}
            for row in evidence_boundaries
        ]
        boundaries = corridor["boundary_identity_receipts"]
        gaps = [row["contact_to_next_m"] for row in boundaries[:-1]]
        maximum = max(gaps)
        coordinates = [
            float(value)
            for row in boundaries
            for key in ("entry_xyz", "exit_xyz")
            for value in row[key]
        ]
        scale = max(abs(value) for value in coordinates)
        frozen = freeze_lifting_tolerances(
            max_chord_error_m=maximum,
            max_station_roundtrip_error_m=0.0,
            max_z_roundtrip_error_m=0.0,
            coordinate_scale_m=scale,
        )
        measurement = dict(evidence)
        measurement["contact_tolerance_m"] = tolerance["measurement_ceiling_m"]
        final = dict(evidence)
        final["contact_tolerance_m"] = tolerance["frozen_contact_tolerance_m"]
        allowance_from_freezer = frozen.geometry_epsilon_m - maximum
        allowance_from_formula = max(1e-9, 64.0 * math.ulp(scale))
        checks.update({
            "schema": receipt["schema_version"] == "dp_camp_v20_carla_route_corridor_contact_tolerance_census_v1",
            "camp_gate_start": provenance["camp_gate_start_head"] == "9537f1998100a32b74cdb6cc6dc36db4837c77f4",
            "camp_execution_head": provenance["camp_execution_head"] == heads["camp_head"] == heads["origin_main"],
            "fixed_dp_head": provenance["fixed_dp_head"] == heads["fixed_dp_head"] == "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "carla_version": provenance["carla_version"] == "0.9.16",
            "carla_source_root": provenance["carla_source_root_sha256"] == "2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce",
            "carla_module": provenance["carla_module_sha256"] == "c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2" and provenance["carla_module_path"].startswith("/root/autodl-tmp/camp_v19_carla_client/"),
            "client_manifest": provenance["client_manifest_sha256"] == "ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e",
            "map_name": provenance["map_name"] == "Carla/Maps/Town10HD_Opt",
            "xodr_sha": provenance["xodr_sha256"] == "5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7",
            "receipt_sha": receipt_sha == canonical_json_sha256(sealed),
            "route_contract": receipt["route"]["point_count"] == 81 and receipt["route"]["sample_step_m"] == 5.0 and len(receipt["route"]["records"]) == 81,
            "route_sha": receipt["route"]["sha256"] == canonical_json_sha256(receipt["route"]["records"]),
            "evidence_sha": corridor["evidence_sha256"] == canonical_json_sha256(evidence),
            "boundary_projection": boundaries == documented_boundaries,
            "boundary_sha": corridor["boundary_identity_receipts_sha256"] == canonical_json_sha256(boundaries),
            "measurement_ceiling_exact": tolerance["measurement_ceiling_m"] == FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m,
            "measured_max_within_ceiling": maximum <= tolerance["measurement_ceiling_m"],
            "measurement_corridor_sha": corridor["measurement_sha256"] == canonical_json_sha256(measurement),
            "final_corridor_sha": corridor["final_sha256"] == canonical_json_sha256(final),
            "raw_gaps": gaps == corridor["raw_contact_gaps_m"],
            "maximum": maximum == corridor["max_contact_gap_m"] == evidence["max_contact_gap_m"],
            "coordinate_scale": scale == tolerance["coordinate_scale_m"],
            "frozen_tolerance": frozen.geometry_epsilon_m == tolerance["frozen_contact_tolerance_m"],
            "builder_tolerances": tolerance["builder_contact_tolerances_m"] == [FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m, frozen.geometry_epsilon_m],
            "allowance_from_freezer": math.isclose(tolerance["allowance_m"], allowance_from_freezer, rel_tol=0.0, abs_tol=1e-15),
            "allowance_formula_literal": tolerance["allowance_formula"] == "max(1e-9, 64*ulp(coordinate_scale_m))",
            "allowance_from_formula": math.isclose(tolerance["allowance_m"], allowance_from_formula, rel_tol=0.0, abs_tol=1e-15),
            "final_within_tolerance": maximum <= frozen.geometry_epsilon_m,
            "call_counters_exact": receipt["call_counters"] == expected_calls,
            "forbidden_counters_exact": receipt["forbidden_access_counters"] == expected_forbidden,
        })
    except Exception:
        error = traceback.format_exc()
        checks["scientific_reconstruction"] = False
else:
    error = "receipt.json is absent; terminal execution failure retained"

passed = all(checks.values())
result = {
    "status": "pass" if passed else "fail",
    "checks": checks,
    "execution_exit_status": execution_exit,
    "scientific_reconstruction_error": error,
    "next_work_target": (
        "v20_carla_route_corridor_source_only_fixed_dp_k8_probe_once"
        if passed
        else "stop_failed_map_only_contact_tolerance_census_review"
    ),
}
(review / "review.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
(review / "review.md").write_text(
    "# V20 map-only contact-tolerance census result review\n\n"
    + "\n".join(f"- {key}: {value}" for key, value in checks.items())
    + "\n"
)
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if passed else 1)
PY
SH
EXECUTION_MANIFEST_VALID=false
(cd "$EXECUTION_ROOT" && sha256sum -c SHA256SUMS) >> "$ROOT/stdout" 2>> "$ROOT/stderr" \
  && EXECUTION_MANIFEST_VALID=true
EXECUTION_ROOT_HASH_VALID=false
test "$(cd "$EXECUTION_ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$EXECUTION_ROOT/ROOT_SHA256")" \
  && EXECUTION_ROOT_HASH_VALID=true
SOURCE_HASHES_VALID=false
test -s "$EXECUTION_ROOT/SOURCE_SHA256SUMS" \
  && (cd /root/autodl-tmp/camp_core && sha256sum -c "$EXECUTION_ROOT/SOURCE_SHA256SUMS") >> "$ROOT/stdout" 2>> "$ROOT/stderr" \
  && SOURCE_HASHES_VALID=true
RUNTIME_HASHES_VALID=false
test -s "$EXECUTION_ROOT/RUNTIME_SHA256SUMS" \
  && (cd / && sha256sum -c "$EXECUTION_ROOT/RUNTIME_SHA256SUMS") >> "$ROOT/stdout" 2>> "$ROOT/stderr" \
  && RUNTIME_HASHES_VALID=true
set +e
EXECUTION_ROOT="$EXECUTION_ROOT" ARTIFACT_ROOT="$ROOT" \
EXECUTION_MANIFEST_VALID="$EXECUTION_MANIFEST_VALID" \
EXECUTION_ROOT_HASH_VALID="$EXECUTION_ROOT_HASH_VALID" \
SOURCE_HASHES_VALID="$SOURCE_HASHES_VALID" \
RUNTIME_HASHES_VALID="$RUNTIME_HASHES_VALID" \
bash "$ROOT/COMMAND" >> "$ROOT/stdout" 2>> "$ROOT/stderr"
STATUS=$?
test ! -s "$ROOT/PROCESSES" || STATUS=1
test ! -s "$ROOT/LISTENERS" || STATUS=1
SUMMARY_OK=false
if test -s "$ROOT/review.json" \
  && test -s "$ROOT/review.md" \
  && "$TEST_PYTHON" -m json.tool "$ROOT/review.json" > /dev/null 2>> "$ROOT/stderr"; then
  SUMMARY_OK=true
else
  STATUS=1
fi
mark_summary_failed() {
  ARTIFACT_ROOT="$ROOT" STATUS="$STATUS" "$TEST_PYTHON" - 2>> "$ROOT/stderr" <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ARTIFACT_ROOT"])
try:
    data = json.loads((root / "review.json").read_text())
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
checks = data.get("checks")
if not isinstance(checks, dict):
    checks = {"review_command_completed": False}
    data["checks"] = checks
checks["initial_artifact_seal"] = False
data.update({
    "status": "fail",
    "review_exit_status": int(os.environ["STATUS"]),
    "next_work_target": "stop_failed_map_only_contact_tolerance_census_review",
})
(root / "review.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
previous = (root / "review.md").read_text(errors="replace") if (root / "review.md").is_file() else "# V20 map-only contact-tolerance census result review\n"
(root / "review.md").write_text(previous.rstrip() + "\n\ninitial_artifact_seal: false\n")
PY
}
seal() {
  test "$SUMMARY_OK" = true \
    && printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS" \
    && (cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS review.json review.md PROCESSES LISTENERS SOURCE_SHA256SUMS RUNTIME_SHA256SUMS > SHA256SUMS) \
    && (cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256) \
    && (cd "$ROOT" && sha256sum -c SHA256SUMS > /dev/null) 2>> "$ROOT/stderr" \
    && test "$(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$ROOT/ROOT_SHA256")"
}
if ! seal; then
  STATUS=1
  SUMMARY_OK=false
  mark_summary_failed && SUMMARY_OK=true
  seal || exit 1
fi
test "$STATUS" -eq 0
~~~

Expected for a successful execution: every check is true, EXIT_STATUS is 0,
and the review artifact is sealed. For a nonzero execution or missing receipt,
the review records terminal fail and the retained execution status/error,
still seals its own artifact, and exits nonzero. Discovery and review use only
HEADS/EXIT_STATUS plus retained files; this command never imports CARLA,
constructs a map, or reruns the census. A summary or first-seal failure sets
STATUS=1 and permits exactly one fail-marked reseal; failure of that reseal
exits nonzero without rerunning the scientific review.

- [ ] **Step 2: Stop or advance exactly one gate**

On review failure, retain all artifacts and stop without changing any frozen
field or rerunning. On review pass, and only then, the next gate may plan and
execute exactly one source-only fixed-DP K=8 probe. That later probe preserves
DP/candidate/request/config/checkpoint bytes and still forbids outcomes,
future labels, holdout, promotion, deployment, activation, formal seeds,
Full36, and broad performance or safety claims.
