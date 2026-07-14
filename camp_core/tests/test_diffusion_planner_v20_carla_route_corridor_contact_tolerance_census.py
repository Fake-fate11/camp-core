from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from camp_core.integrations.carla_causal_adapter import (
    build_pre_generation_route_corridor as real_builder,
)
from camp_core.integrations.carla_exact_speed_source import canonical_json_sha256


MODULE = (
    "scripts.integrations."
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance"
)
XODR = """<OpenDRIVE>
<road id="1" length="200"><lanes><laneSection s="0">
<right><lane id="-1" type="driving"/></right>
</laneSection></lanes></road>
<road id="2" length="205"><lanes><laneSection s="0">
<right><lane id="-1" type="driving"/></right>
</laneSection></lanes></road>
</OpenDRIVE>"""


def _module():
    return importlib.import_module(MODULE)


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


def _run_census(monkeypatch, map_api=None):
    census = _module()
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


def test_nonzero_two_identity_two_pass_receipt_is_reconstructible(monkeypatch):
    census = _module()
    calls = Counter()
    for name in (
        "_deterministic_route",
        "build_pre_generation_route_corridor",
        "freeze_lifting_tolerances",
    ):
        original = getattr(census, name)

        def observed(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(census, name, observed)

    map_api = FakeMap()
    receipt = _run_census(monkeypatch, map_api)
    expected_calls = {
        "_deterministic_route": 1,
        "build_pre_generation_route_corridor": 2,
        "freeze_lifting_tolerances": 1,
    }
    sealed = dict(receipt)
    receipt_sha = sealed.pop("receipt_sha256")

    assert dict(calls) == receipt["call_counters"] == expected_calls
    assert receipt_sha == canonical_json_sha256(sealed)
    assert receipt["route"]["sha256"] == canonical_json_sha256(
        receipt["route"]["records"]
    )
    corridor = receipt["corridor"]
    assert len(corridor["boundary_identity_receipts"]) == 2
    assert corridor["raw_contact_gaps_m"][0] > 0.0
    assert corridor["evidence_sha256"] == canonical_json_sha256(
        corridor["evidence"]
    )
    tolerance = receipt["tolerance"]
    assert tolerance["builder_contact_tolerances_m"] == [
        census.FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m,
        tolerance["frozen_contact_tolerance_m"],
    ]
    assert tolerance["allowance_m"] == pytest.approx(
        max(1e-9, 64.0 * math.ulp(tolerance["coordinate_scale_m"])),
        rel=0.0,
        abs=1e-15,
    )
    assert all(value == 0 for value in receipt["forbidden_access_counters"].values())
    assert (map_api.server_connections, map_api.actor_spawns, map_api.world_ticks) == (
        0,
        0,
        0,
    )


@pytest.mark.parametrize(
    ("case", "message", "freeze_count"),
    (
        ("nonfinite", "invalid", 0),
        ("predecessor0", "predecessor", 0),
        ("predecessor2", "predecessor", 0),
        ("ceiling", "contact", 0),
        ("drift", "evidence changed", 1),
    ),
)
def test_fail_closed_inputs_and_second_pass_drift(
    monkeypatch, case, message, freeze_count
):
    census = _module()
    freezes = 0
    original_freeze = census.freeze_lifting_tolerances

    def observed_freeze(**kwargs):
        nonlocal freezes
        freezes += 1
        return original_freeze(**kwargs)

    monkeypatch.setattr(census, "freeze_lifting_tolerances", observed_freeze)
    if case == "drift":
        builder_calls = 0

        def drifting_builder(**kwargs):
            nonlocal builder_calls
            builder_calls += 1
            result = real_builder(**kwargs)
            if builder_calls == 2:
                result = deepcopy(result)
                result["boundary_receipts"][0]["entry_xyz"][0] += 0.01
            return result

        monkeypatch.setattr(
            census, "build_pre_generation_route_corridor", drifting_builder
        )
        map_api = FakeMap()
    else:
        map_api = {
            "nonfinite": FakeMap(nonfinite=True),
            "predecessor0": FakeMap(predecessor_count=0),
            "predecessor2": FakeMap(predecessor_count=2),
            "ceiling": FakeMap(gap=2.0),
        }[case]

    with pytest.raises(ValueError, match=message):
        _run_census(monkeypatch, map_api)
    assert freezes == freeze_count


def test_cli_preflight_and_execution_roles_are_separate(monkeypatch, tmp_path):
    census = _module()
    calls = Counter()
    preflight_output = tmp_path / "preflight.json"
    execution_output = tmp_path / "receipt.json"

    def preflight_receipt():
        calls["preflight"] += 1
        return {"schema_version": "v20_production_import_runtime_v1", "no_map": True}

    monkeypatch.setattr(census, "_production_preflight_receipt", preflight_receipt)
    monkeypatch.setattr(census, "_verified_runtime_identity", lambda: {})
    monkeypatch.setattr(
        census,
        "_verified_provenance",
        lambda: {
            "opendrive_xml": XODR,
            "carla_version": census.CARLA_VERSION,
            "carla_module_path": "/sealed/libcarla.so",
            "carla_module_sha256": census.LIBCARLA_SHA256,
            "client_manifest_sha256": census.CLIENT_MANIFEST_SHA256,
            "carla_source_root_sha256": census.CARLA_SOURCE_ROOT_SHA256,
        },
    )

    def map_constructor(name, opendrive_xml):
        calls["map"] += 1
        assert name == census.MAP_NAME and opendrive_xml == XODR
        return FakeMap()

    monkeypatch.setattr(
        census,
        "_load_sealed_carla",
        lambda provenance: SimpleNamespace(Map=map_constructor),
    )
    monkeypatch.setattr(
        census,
        "census_route_corridor_contact_tolerance",
        lambda **kwargs: calls.update(census=1) or {"receipt": "ok"},
    )

    assert (
        census.main(["--preflight-only", "--output-json", str(preflight_output)])
        == 0
    )
    assert json.loads(preflight_output.read_text())["no_map"] is True
    assert calls == {"preflight": 1}

    assert (
        census.main(
            ["--camp-head", "a" * 40, "--output-json", str(execution_output)]
        )
        == 0
    )
    assert json.loads(execution_output.read_text()) == {"receipt": "ok"}
    assert calls == {"preflight": 1, "map": 1, "census": 1}
    assert not execution_output.with_suffix(".json.tmp").exists()


@pytest.mark.parametrize("occupied", ("output", "tmp"))
def test_existing_output_fails_before_any_input_access(monkeypatch, tmp_path, occupied):
    census = _module()
    output = tmp_path / "receipt.json"
    target = output if occupied == "output" else output.with_suffix(".json.tmp")
    target.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(census, "XODR_PATH", tmp_path / "missing.xodr")

    with pytest.raises(FileExistsError):
        census.main(["--camp-head", "a" * 40, "--output-json", str(output)])


def test_runtime_role_and_authoritative_plan_commands(monkeypatch):
    census = _module()
    assert "carla" not in census.sys.modules
    import_prefix = Path(census.__file__).read_text(encoding="utf-8").split(
        "def _load_sealed_carla", 1
    )[0]
    assert re.search(r"(?m)^\s*(?:import carla|from carla)", import_prefix) is None
    monkeypatch.setattr(census.sys, "executable", census.TEST_PYTHON)
    with pytest.raises(ValueError, match="CARLA_PYTHON"):
        census._verified_runtime_identity()

    root = Path(__file__).resolve().parents[2]
    plan = (
        root
        / "docs/superpowers/plans/"
        "2026-07-14-v20-carla-route-corridor-map-only-contact-tolerance-census.md"
    ).read_text(encoding="utf-8")
    note = plan.split("## Complexity Budget Authority", 1)[1].split("\n## ", 1)[0]
    assert note.index("sha256sum \"$TEST_PYTHON_RESOLVED\"") < note.index(
        '"$TEST_PYTHON" -m pytest'
    )
    assert '"$TEST_PYTHON" -m pytest' in note
    assert '"$TEST_PYTHON" -m py_compile' in note
    assert '"$TEST_PYTHON" -m json.tool' in note
    assert '"$CARLA_PYTHON" "$RUNNER" --preflight-only' in note
    assert '"$CARLA_PYTHON" "$RUNNER" --camp-head' in note
    assert '"$CARLA_PYTHON" -m pytest' not in note
    assert '"$TEST_PYTHON" "$RUNNER"' not in note
    for block in re.findall(r"~~~bash\n(.*?)\n~~~", note, re.S):
        assert re.search(
            r"(?<![/\w.$-])python(?:3(?:\.\d+)?)?(?=[\s;|&()<>'\"]|$)",
            block,
        ) is None
