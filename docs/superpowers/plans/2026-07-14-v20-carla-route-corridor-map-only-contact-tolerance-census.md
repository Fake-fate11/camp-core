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

**Tech Stack:** Python 3.12, pytest, Python standard library, existing CAMP
CARLA integration code, official CARLA 0.9.16 cp312 client.

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
python census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
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
python3.12 - <<'PY' > "$ROOT/PROCESSES"
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
    raise SystemExit(str(rows))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -euo pipefail
python3.12 - <<'PY'
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
ARTIFACT_ROOT="$ROOT" bash "$ROOT/COMMAND" > "$ROOT/stdout" 2> "$ROOT/stderr"
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
CAMP_HEAD=$(git rev-parse HEAD)
ROOT=$(python3.12 - "$CAMP_HEAD" <<'PY'
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
python3.12 -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "pass"' "$ROOT/review.json"
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
    first = run_census(monkeypatch)
    second = run_census(monkeypatch)
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
    assert first["call_counters"] == {
        "_deterministic_route": 1,
        "build_pre_generation_route_corridor": 2,
        "freeze_lifting_tolerances": 1,
    }


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
    assert set(receipt["forbidden_access_counters"].values()) == {0}
    text = json.dumps(
        {key: value for key, value in receipt.items() if key != "forbidden_access_counters"}
    ).lower()
    for forbidden in ("candidate", "outcome", "metric", "holdout", "selector"):
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


def test_cli_rejects_existing_output_before_input_access(monkeypatch, tmp_path):
    output = tmp_path / "receipt.json"
    output.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(census, "XODR_PATH", tmp_path / "missing.xodr")
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
python3.12 - <<'PY' > "$ROOT/PROCESSES"
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
    raise SystemExit(str(rows))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -euo pipefail
export PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core
python3.12 -m pytest \
  camp_core/tests/test_carla_exact_speed_source.py \
  camp_core/tests/test_carla_causal_adapter.py \
  camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py \
  camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py \
  camp_core/tests/test_diffusion_planner_v19_dp_worker.py \
  camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
python3.12 -m py_compile \
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git diff --check
test -z "$(git status --short --untracked-files=no)"
SH
set +e
bash "$ROOT/COMMAND" > "$ROOT/stdout" 2> "$ROOT/stderr"
STATUS=$?
set -e
printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS"
ARTIFACT_ROOT="$ROOT" STATUS="$STATUS" CAMP_HEAD="$CAMP_HEAD" python3.12 - <<'PY'
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
set -euo pipefail
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
git fetch --prune origin
git pull --ff-only
CAMP_HEAD=$(git rev-parse HEAD)
test "$CAMP_HEAD" = "$(git rev-parse origin/main)"
test -z "$(git status --short --untracked-files=no)"
DP_HEAD=$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD)
test "$DP_HEAD" = 7a1d33da277a1992ec474b5383a0c963c72e04e4
test -z "$(git -C /root/autodl-tmp/Diffusion-Planner status --short --untracked-files=no)"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_preflight_$STAMP
EXECUTION_ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_$STAMP
test ! -e "$ROOT"
test ! -e "$EXECUTION_ROOT"
test ! -e "$EXECUTION_ROOT.tmp"
mkdir "$ROOT"
PYTHON=$(readlink -f "$(command -v python3.12)")
test "$("$PYTHON" -c 'import sys; print(sys.version_info[:2] == (3, 12))')" = True
printf 'camp_head=%s\norigin_main=%s\nfixed_dp_head=%s\n' \
  "$CAMP_HEAD" "$(git rev-parse origin/main)" "$DP_HEAD" > "$ROOT/HEADS"
sha256sum \
  scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py \
  camp_core/camp_core/integrations/carla_causal_adapter.py \
  camp_core/camp_core/integrations/carla_exact_speed_source.py \
  scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py \
  > "$ROOT/SOURCE_SHA256SUMS"
python3.12 - <<'PY' > "$ROOT/PROCESSES"
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
    raise SystemExit(str(rows))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS"
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
FREE_BYTES=$(df --output=avail -B1 /root/autodl-tmp | tail -1 | tr -d ' ')
test "$FREE_BYTES" -ge 10737418240
XODR=/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD_Opt.xodr
test "$(sha256sum "$XODR" | awk '{print $1}')" = 5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7
test "$(sha256sum /root/autodl-tmp/camp_v19_carla_client/CLIENT_SHA256SUMS | awk '{print $1}')" = ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e
LIBCARLA=$(find /root/autodl-tmp/camp_v19_carla_client -type f -name 'libcarla.cpython-312-x86_64-linux-gnu.so' -print)
test "$(printf '%s\n' "$LIBCARLA" | sed '/^$/d' | wc -l)" -eq 1
test "$(sha256sum "$LIBCARLA" | awk '{print $1}')" = c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2
test "$(awk '{print $1; exit}' /root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_20260713T000320CST/ROOT_SHA256)" = 2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client "$PYTHON" - <<'PY'
from importlib.metadata import version
import carla.libcarla as libcarla
assert version("carla") == "0.9.16"
print(libcarla.__file__)
PY
cat > "$ROOT/COMMAND" <<EOF
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core $PYTHON /root/autodl-tmp/camp_core/scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py --camp-head $CAMP_HEAD --output-json $EXECUTION_ROOT/receipt.json
EOF
test "$(grep -Eoc -- '--host|--port|CarlaUE4|carla.Client' "$ROOT/COMMAND")" -eq 0
ARTIFACT_ROOT="$ROOT" EXECUTION_ROOT="$EXECUTION_ROOT" PYTHON_PATH="$PYTHON" \
FREE_BYTES="$FREE_BYTES" LIBCARLA_PATH="$LIBCARLA" CAMP_HEAD="$CAMP_HEAD" \
python3.12 - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ARTIFACT_ROOT"])
data = {
    "status": "pass",
    "camp_head": os.environ["CAMP_HEAD"],
    "python_path": os.environ["PYTHON_PATH"],
    "carla_version": "0.9.16",
    "carla_module_path": os.environ["LIBCARLA_PATH"],
    "map_constructor": 'carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)',
    "execution_root": os.environ["EXECUTION_ROOT"],
    "output_json": os.environ["EXECUTION_ROOT"] + "/receipt.json",
    "output_tmp": os.environ["EXECUTION_ROOT"] + "/receipt.json.tmp",
    "free_bytes": int(os.environ["FREE_BYTES"]),
    "related_processes": [],
    "listeners_2000_2001": [],
}
(root / "preflight.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
(root / "preflight.md").write_text(
    "# V20 contact-tolerance census no-run preflight\n\nstatus: pass\n"
)
PY
: > "$ROOT/stdout"
: > "$ROOT/stderr"
printf '0\n' > "$ROOT/EXIT_STATUS"
(cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS preflight.json preflight.md PROCESSES LISTENERS SOURCE_SHA256SUMS > SHA256SUMS)
(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256)
~~~

Expected: no map is constructed; EXIT_STATUS is 0; preflight.json status is
pass; PROCESSES, LISTENERS, stdout, and stderr are empty; execution_root,
output_json, output_tmp, Python, heads, hashes, and argv are exact.

- [ ] **Step 2: Independently review the preflight without execution**

Run:

~~~bash
set -euo pipefail
cd /root/autodl-tmp/camp_core
CAMP_HEAD=$(git rev-parse HEAD)
ROOT=$(python3.12 - "$CAMP_HEAD" <<'PY'
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
test "$(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$ROOT/ROOT_SHA256")"
test "$(cat "$ROOT/EXIT_STATUS")" = 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
python3.12 - "$ROOT/preflight.json" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert data["status"] == "pass"
assert data["free_bytes"] >= 10737418240
assert data["map_constructor"] == 'carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)'
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
set -euo pipefail
cd /root/autodl-tmp/camp_core
CAMP_HEAD=$(git rev-parse HEAD)
PREFLIGHT_ROOT=$(python3.12 - "$CAMP_HEAD" <<'PY'
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
EXECUTION_ROOT=$(python3.12 -c 'import json,sys; print(json.load(open(sys.argv[1]))["execution_root"])' "$PREFLIGHT_ROOT/preflight.json")
OUTPUT_JSON=$(python3.12 -c 'import json,sys; print(json.load(open(sys.argv[1]))["output_json"])' "$PREFLIGHT_ROOT/preflight.json")
OUTPUT_TMP=$(python3.12 -c 'import json,sys; print(json.load(open(sys.argv[1]))["output_tmp"])' "$PREFLIGHT_ROOT/preflight.json")
test ! -e "$EXECUTION_ROOT"
test ! -e "$OUTPUT_JSON"
test ! -e "$OUTPUT_TMP"
mkdir "$EXECUTION_ROOT"
cp "$PREFLIGHT_ROOT/HEADS" "$EXECUTION_ROOT/HEADS"
cp "$PREFLIGHT_ROOT/COMMAND" "$EXECUTION_ROOT/COMMAND"
cp "$PREFLIGHT_ROOT/preflight.json" "$EXECUTION_ROOT/preflight.json"
cp "$PREFLIGHT_ROOT/SOURCE_SHA256SUMS" "$EXECUTION_ROOT/SOURCE_SHA256SUMS"
cp "$PREFLIGHT_ROOT/PROCESSES" "$EXECUTION_ROOT/PROCESSES.before"
cp "$PREFLIGHT_ROOT/LISTENERS" "$EXECUTION_ROOT/LISTENERS.before"
set +e
bash "$EXECUTION_ROOT/COMMAND" > "$EXECUTION_ROOT/stdout" 2> "$EXECUTION_ROOT/stderr"
STATUS=$?
set -e
printf '%s\n' "$STATUS" > "$EXECUTION_ROOT/EXIT_STATUS"
python3.12 - <<'PY' > "$EXECUTION_ROOT/PROCESSES.after"
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
    raise SystemExit(str(rows))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$EXECUTION_ROOT/LISTENERS.after"
ARTIFACT_ROOT="$EXECUTION_ROOT" STATUS="$STATUS" python3.12 - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ARTIFACT_ROOT"])
status = int(os.environ["STATUS"])
data = {
    "status": "pass" if status == 0 and (root / "receipt.json").is_file() else "fail",
    "exit_status": status,
    "receipt_present": (root / "receipt.json").is_file(),
}
(root / "result.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
(root / "result.md").write_text(
    "# V20 offline map-only census execution\n\n"
    f"status: {data['status']}\nexit_status: {status}\n"
)
PY
(cd "$EXECUTION_ROOT" && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name ROOT_SHA256 -printf '%f\n' | LC_ALL=C sort | xargs sha256sum > SHA256SUMS)
(cd "$EXECUTION_ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256)
test "$STATUS" -eq 0
test -f "$OUTPUT_JSON"
test ! -e "$OUTPUT_TMP"
test ! -s "$EXECUTION_ROOT/PROCESSES.before"
test ! -s "$EXECUTION_ROOT/PROCESSES.after"
test ! -s "$EXECUTION_ROOT/LISTENERS.before"
test ! -s "$EXECUTION_ROOT/LISTENERS.after"
~~~

Expected: the frozen COMMAND is invoked exactly once; EXIT_STATUS is 0;
receipt.json and result.json/result.md exist; no temp, process, or listener
evidence exists; all files are sealed. Any failure is terminal and retained.

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
set -euo pipefail
cd /root/autodl-tmp/camp_core
CAMP_HEAD=$(git rev-parse HEAD)
EXECUTION_ROOT=$(python3.12 - "$CAMP_HEAD" <<'PY'
import json
import sys
from pathlib import Path
head = sys.argv[1]
matches = []
for path in Path("/root/autodl-tmp").glob(
    "camp_dp_v20_carla_contact_tolerance_execution_*/receipt.json"
):
    receipt = json.loads(path.read_text())
    if receipt["provenance"]["camp_execution_head"] == head:
        matches.append(path.parent)
if len(matches) != 1:
    raise SystemExit(f"expected one execution, found {len(matches)}")
print(matches[0])
PY
)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ROOT=/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_execution_review_$STAMP
test ! -e "$ROOT"
mkdir "$ROOT"
cp "$EXECUTION_ROOT/HEADS" "$ROOT/HEADS"
cp "$EXECUTION_ROOT/SOURCE_SHA256SUMS" "$ROOT/SOURCE_SHA256SUMS"
python3.12 - <<'PY' > "$ROOT/PROCESSES"
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
    raise SystemExit(str(rows))
PY
ss -H -ltnp 'sport = :2000 or sport = :2001' > "$ROOT/LISTENERS"
cat > "$ROOT/COMMAND" <<'SH'
set -euo pipefail
PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core \
python3.12 - <<'PY'
import json
import math
import os
from pathlib import Path
from camp_core.integrations.carla_exact_speed_source import (
    canonical_json_sha256,
    freeze_lifting_tolerances,
)

execution = Path(os.environ["EXECUTION_ROOT"])
review = Path(os.environ["ARTIFACT_ROOT"])
receipt = json.loads((execution / "receipt.json").read_text())
sealed = dict(receipt)
receipt_sha = sealed.pop("receipt_sha256")
heads = dict(
    line.split("=", 1)
    for line in (execution / "HEADS").read_text().splitlines()
)
provenance = receipt["provenance"]
corridor = receipt["corridor"]
tolerance = receipt["tolerance"]
evidence = corridor["evidence"]
measurement = dict(evidence)
measurement["contact_tolerance_m"] = tolerance["measurement_ceiling_m"]
final = dict(evidence)
final["contact_tolerance_m"] = tolerance["frozen_contact_tolerance_m"]
boundaries = corridor["boundary_identity_receipts"]
gaps = [
    row["contact_to_next_m"]
    for row in boundaries[:-1]
]
coordinates = [
    float(value)
    for row in boundaries
    for key in ("entry_xyz", "exit_xyz")
    for value in row[key]
]
scale = max(abs(value) for value in coordinates)
maximum = max(gaps)
frozen = freeze_lifting_tolerances(
    max_chord_error_m=maximum,
    max_station_roundtrip_error_m=0.0,
    max_z_roundtrip_error_m=0.0,
    coordinate_scale_m=scale,
)
expected_calls = {
    "_deterministic_route": 1,
    "build_pre_generation_route_corridor": 2,
    "freeze_lifting_tolerances": 1,
}
checks = {
    "execution_exit_zero": (execution / "EXIT_STATUS").read_text().strip() == "0",
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
    "boundary_sha": corridor["boundary_identity_receipts_sha256"] == canonical_json_sha256(boundaries),
    "measurement_corridor_sha": corridor["measurement_sha256"] == canonical_json_sha256(measurement),
    "final_corridor_sha": corridor["final_sha256"] == canonical_json_sha256(final),
    "raw_gaps": gaps == corridor["raw_contact_gaps_m"],
    "maximum": maximum == corridor["max_contact_gap_m"],
    "coordinate_scale": scale == tolerance["coordinate_scale_m"],
    "frozen_tolerance": frozen.geometry_epsilon_m == tolerance["frozen_contact_tolerance_m"],
    "builder_tolerances": tolerance["builder_contact_tolerances_m"] == [tolerance["measurement_ceiling_m"], tolerance["frozen_contact_tolerance_m"]],
    "allowance": math.isclose(
        tolerance["allowance_m"],
        max(1e-9, 64.0 * math.ulp(scale)),
        rel_tol=0.0,
        abs_tol=1e-15,
    ),
    "final_within_tolerance": maximum <= tolerance["frozen_contact_tolerance_m"],
    "call_counters": receipt["call_counters"] == expected_calls,
    "forbidden_counters": set(receipt["forbidden_access_counters"].values()) == {0},
    "processes_empty": not (execution / "PROCESSES.before").read_text() and not (execution / "PROCESSES.after").read_text(),
    "listeners_empty": not (execution / "LISTENERS.before").read_text() and not (execution / "LISTENERS.after").read_text(),
}
result = {
    "status": "pass" if all(checks.values()) else "fail",
    "checks": checks,
    "next_work_target": (
        "v20_carla_route_corridor_source_only_fixed_dp_k8_probe_once"
        if all(checks.values())
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
raise SystemExit(0 if result["status"] == "pass" else 1)
PY
SH
set +e
EXECUTION_ROOT="$EXECUTION_ROOT" ARTIFACT_ROOT="$ROOT" bash "$ROOT/COMMAND" > "$ROOT/stdout" 2> "$ROOT/stderr"
STATUS=$?
set -e
printf '%s\n' "$STATUS" > "$ROOT/EXIT_STATUS"
(cd "$EXECUTION_ROOT" && sha256sum -c SHA256SUMS)
(cd /root/autodl-tmp/camp_core && sha256sum -c "$EXECUTION_ROOT/SOURCE_SHA256SUMS")
test "$(cd "$EXECUTION_ROOT" && sha256sum SHA256SUMS | awk '{print $1}')" = "$(cat "$EXECUTION_ROOT/ROOT_SHA256")"
(cd "$ROOT" && sha256sum HEADS COMMAND stdout stderr EXIT_STATUS review.json review.md PROCESSES LISTENERS SOURCE_SHA256SUMS > SHA256SUMS)
(cd "$ROOT" && sha256sum SHA256SUMS | awk '{print $1}' > ROOT_SHA256)
test "$STATUS" -eq 0
test ! -s "$ROOT/PROCESSES"
test ! -s "$ROOT/LISTENERS"
~~~

Expected: every check is true, EXIT_STATUS is 0, and the review artifact is
sealed. This command never imports CARLA, constructs a map, or reruns the
census.

- [ ] **Step 2: Stop or advance exactly one gate**

On review failure, retain all artifacts and stop without changing any frozen
field or rerunning. On review pass, and only then, the next gate may plan and
execute exactly one source-only fixed-DP K=8 probe. That later probe preserves
DP/candidate/request/config/checkpoint bytes and still forbids outcomes,
future labels, holdout, promotion, deployment, activation, formal seeds,
Full36, and broad performance or safety claims.
