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
        ("predecessor0", "no deterministic CARLA route", 0),
        ("predecessor2", "no deterministic CARLA route", 0),
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


def test_predecessor_topology_diagnosis_classifies_preregistered_branches(
    monkeypatch,
):
    census = _module()
    root_map = FakeMap(predecessor_count=0)
    root_map.route[0].s = 0.0
    root_map.route[0].transform.location.x = 0.0
    linked_xodr = XODR.replace(
        '<road id="1" length="200">',
        '<road id="1" length="200"><link>'
        '<predecessor elementType="road" elementId="0" contactPoint="end"/>'
        '</link>',
    ).replace(
        '<right><lane id="-1" type="driving"/></right>',
        '<right><lane id="-1" type="driving"><link>'
        '<predecessor id="-1"/></link></lane></right>',
        1,
    ).replace(
        "<OpenDRIVE>",
        '<OpenDRIVE><road id="0" length="10"><lanes><laneSection s="0">'
        '<right><lane id="-1" type="driving"/></right>'
        '</laneSection></lanes></road>',
    )
    road_only_xodr = linked_xodr.replace(
        '<lane id="-1" type="driving"><link>'
        '<predecessor id="-1"/></link></lane>',
        '<lane id="-1" type="driving"/>',
        1,
    )
    unrelated_junction_xodr = XODR.replace(
        '<road id="1" length="200">',
        '<road id="1" junction="9" length="200">',
    ).replace(
        "</OpenDRIVE>",
        '<junction id="9"><connection id="0" incomingRoad="0" '
        'connectingRoad="1" contactPoint="start">'
        '<laneLink from="-1" to="-2"/></connection></junction></OpenDRIVE>',
    )
    cases = (
        (
            root_map,
            XODR,
            "root_boundary_no_predecessor",
            True,
            "no",
            0,
        ),
        (
            FakeMap(predecessor_count=0),
            linked_xodr,
            "candidate_free_map_level_route_selection_only",
            False,
            "yes",
            1,
        ),
        (
            FakeMap(predecessor_count=0),
            road_only_xodr,
            "candidate_free_map_level_route_selection_only",
            False,
            "undetermined",
            0,
        ),
        (
            FakeMap(predecessor_count=0),
            unrelated_junction_xodr,
            "candidate_free_map_level_route_selection_only",
            False,
            "undetermined",
            0,
        ),
        (
            FakeMap(predecessor_count=1),
            XODR,
            "cardinality_one_builder_implementation_check",
            False,
            "no",
            0,
        ),
        (
            FakeMap(predecessor_count=2),
            XODR,
            "ambiguity_fail_closed",
            False,
            "no",
            0,
        ),
    )

    for map_api, xodr, branch, topology_root, lookup_omission, proof_count in cases:
        monkeypatch.setattr(
            census, "XODR_SHA256", hashlib.sha256(xodr.encode()).hexdigest()
        )
        receipt = census.diagnose_route_predecessor_topology(
            map_api=map_api,
            opendrive_xml=xodr,
            camp_execution_head="a" * 40,
        )
        sealed = dict(receipt)
        receipt_sha256 = sealed.pop("receipt_sha256")

        assert receipt_sha256 == canonical_json_sha256(sealed)
        assert receipt["branch"] == branch
        assert receipt["topology"]["true_opendrive_topology_root"] is topology_root
        assert (
            receipt["topology"]["lookup_omitted_legal_predecessor"]
            == lookup_omission
        )
        assert len(receipt["topology"]["legal_predecessor_proofs"]) == proof_count
        assert receipt["route_start"]["identity"] == ["1", 0, -1]
        assert all(
            value == 0 for value in receipt["forbidden_access_counters"].values()
        )


def test_cli_preflight_and_execution_roles_are_separate(monkeypatch, tmp_path):
    census = _module()
    calls = Counter()
    preflight_output = tmp_path / "preflight.json"
    execution_output = tmp_path / "receipt.json"
    diagnosis_output = tmp_path / "diagnosis.json"
    runtime = {"carla_python": {"path": "/sealed/python"}}
    production_import = {"module_paths": {"runner": "/sealed/runner.py"}}
    provenance = {
        "opendrive_xml": XODR,
        "carla_version": census.CARLA_VERSION,
        "carla_module_path": "/sealed/libcarla.so",
        "carla_module_sha256": census.LIBCARLA_SHA256,
        "client_manifest_sha256": census.CLIENT_MANIFEST_SHA256,
        "carla_source_root_sha256": census.CARLA_SOURCE_ROOT_SHA256,
    }
    public_provenance = {
        key: value for key, value in provenance.items() if key != "opendrive_xml"
    }

    def preflight_receipt():
        calls["preflight"] += 1
        return {
            "schema_version": "v20_production_import_runtime_v1",
            "runtime": runtime,
            "provenance": public_provenance,
            "production_import": production_import,
            "no_map": True,
            "no_census": True,
            "no_server": True,
        }

    monkeypatch.setattr(census, "_production_preflight_receipt", preflight_receipt)
    monkeypatch.setattr(census, "_verified_runtime_identity", lambda: runtime)
    monkeypatch.setattr(census, "_verified_provenance", lambda: provenance)
    monkeypatch.setattr(
        census, "_production_import_evidence", lambda: production_import
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
            [
                "--preflight-json",
                str(preflight_output),
                "--camp-head",
                "a" * 40,
                "--output-json",
                str(execution_output),
            ]
        )
        == 0
    )
    assert json.loads(execution_output.read_text()) == {"receipt": "ok"}
    assert calls == {"preflight": 1, "map": 1, "census": 1}
    assert not execution_output.with_suffix(".json.tmp").exists()

    monkeypatch.setattr(
        census,
        "diagnose_route_predecessor_topology",
        lambda **kwargs: calls.update(diagnosis=1) or {"diagnosis": "ok"},
    )
    assert (
        census.main(
            [
                "--diagnose-predecessor-topology-only",
                "--preflight-json",
                str(preflight_output),
                "--camp-head",
                "a" * 40,
                "--output-json",
                str(diagnosis_output),
            ]
        )
        == 0
    )
    assert json.loads(diagnosis_output.read_text()) == {"diagnosis": "ok"}
    assert calls == {"preflight": 1, "map": 2, "census": 1, "diagnosis": 1}

    missing_key = json.loads(preflight_output.read_text())
    missing_key.pop("no_server")
    invalid_preflight = tmp_path / "invalid-preflight.json"
    invalid_preflight.write_text(json.dumps(missing_key), encoding="utf-8")
    with pytest.raises(ValueError, match="preflight receipt schema"):
        census._verified_preflight_receipt(invalid_preflight)
    missing_key["no_server"] = True
    missing_key["unexpected"] = True
    invalid_preflight.write_text(json.dumps(missing_key), encoding="utf-8")
    with pytest.raises(ValueError, match="preflight receipt schema"):
        census._verified_preflight_receipt(invalid_preflight)

    with pytest.raises(ValueError, match="--preflight-json"):
        census.main(
            [
                "--camp-head",
                "a" * 40,
                "--output-json",
                str(tmp_path / "missing-preflight-argument.json"),
            ]
        )

    monkeypatch.setattr(
        census,
        "_production_import_evidence",
        lambda: {"module_paths": {"runner": "/drifted/runner.py"}},
    )
    with pytest.raises(ValueError, match="preflight production_import mismatch"):
        census.main(
            [
                "--preflight-json",
                str(preflight_output),
                "--camp-head",
                "a" * 40,
                "--output-json",
                str(tmp_path / "drifted.json"),
            ]
        )
    assert calls == {"preflight": 1, "map": 2, "census": 1, "diagnosis": 1}


@pytest.mark.parametrize("occupied", ("output", "tmp"))
def test_existing_output_fails_before_any_input_access(monkeypatch, tmp_path, occupied):
    census = _module()
    output = tmp_path / "receipt.json"
    target = output if occupied == "output" else output.with_suffix(".json.tmp")
    target.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(census, "XODR_PATH", tmp_path / "missing.xodr")

    with pytest.raises(FileExistsError):
        census.main(["--camp-head", "a" * 40, "--output-json", str(output)])


def test_runtime_role_and_authoritative_plan_commands(monkeypatch, tmp_path):
    census = _module()
    assert "carla" not in census.sys.modules
    import_prefix = Path(census.__file__).read_text(encoding="utf-8").split(
        "def _load_sealed_carla", 1
    )[0]
    assert re.search(r"(?m)^\s*(?:import carla|from carla)", import_prefix) is None
    monkeypatch.setattr(census.sys, "executable", census.TEST_PYTHON)
    with pytest.raises(ValueError, match="CARLA_PYTHON"):
        census._verified_runtime_identity()

    client_root = tmp_path / "client"
    files = {
        "carla/__init__.py": b"from .libcarla import Map\n",
        "carla/libcarla.cpython-312-x86_64-linux-gnu.so": b"sealed libcarla",
        **{f"carla/payload_{index:02d}.bin": f"payload {index}".encode() for index in range(14)},
    }
    for relative, content in files.items():
        path = client_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    hashes = {
        relative: hashlib.sha256(content).hexdigest()
        for relative, content in files.items()
    }
    manifest_path = client_root / "CLIENT_SHA256SUMS"

    def write_manifest(lines=None):
        rows = lines or [
            f"{sha256}  {relative}" for relative, sha256 in sorted(hashes.items())
        ]
        manifest_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    write_manifest()
    monkeypatch.setattr(census, "CLIENT_ROOT", client_root)
    monkeypatch.setattr(census, "CLIENT_MANIFEST_PATH", manifest_path)
    entries = census._verified_client_manifest()
    assert entries == dict(sorted(hashes.items()))

    payload = client_root / "carla/payload_00.bin"
    payload.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="client file SHA256 mismatch"):
        census._verified_client_manifest()
    payload.write_bytes(files["carla/payload_00.bin"])
    for invalid_line in (
        "malformed",
        f"{'0' * 64}  /absolute",
        f"{'0' * 64}  carla/../escape",
    ):
        write_manifest([invalid_line, *manifest_path.read_text().splitlines()[1:]])
        with pytest.raises(ValueError, match="client manifest"):
            census._verified_client_manifest()
        write_manifest()
    rows = manifest_path.read_text().splitlines()
    write_manifest([rows[0], rows[0], *rows[2:]])
    with pytest.raises(ValueError, match="duplicate client manifest"):
        census._verified_client_manifest()
    write_manifest()
    extra = client_root / "carla/unlisted.bin"
    extra.write_bytes(b"unlisted")
    with pytest.raises(ValueError, match="client manifest file set mismatch"):
        census._verified_client_manifest()
    extra.unlink()

    map_type = object()
    init_path = client_root / "carla/__init__.py"
    lib_path = client_root / "carla/libcarla.cpython-312-x86_64-linux-gnu.so"
    carla = SimpleNamespace(
        __file__=str(init_path), __path__=[str(init_path.parent)], Map=map_type
    )
    libcarla = SimpleNamespace(__file__=str(lib_path), Map=map_type)
    monkeypatch.setattr(
        census.importlib,
        "import_module",
        lambda name: {"carla": carla, "carla.libcarla": libcarla}[name],
    )
    monkeypatch.setattr(census, "distribution_version", lambda name: "0.9.16")
    provenance = {
        "carla_init_path": str(init_path.resolve()),
        "carla_init_sha256": hashes["carla/__init__.py"],
        "carla_module_path": str(lib_path.resolve()),
        "carla_module_sha256": hashes[
            "carla/libcarla.cpython-312-x86_64-linux-gnu.so"
        ],
    }
    assert census._load_sealed_carla(provenance) is carla
    carla.Map = object()
    with pytest.raises(ValueError, match="Map identity mismatch"):
        census._load_sealed_carla(provenance)

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
    assert (
        '"$CARLA_PYTHON" "$RUNNER" --preflight-json '
        "/root/autodl-tmp/v20_contact_tolerance_preflight.json --camp-head"
    ) in note
    assert '"$CARLA_PYTHON" -m pytest' not in note
    assert '"$TEST_PYTHON" "$RUNNER"' not in note
    for block in re.findall(r"~~~bash\n(.*?)\n~~~", note, re.S):
        assert re.search(
            r"(?<![/\w.$-])python(?:3(?:\.\d+)?)?(?=[\s;|&()<>'\"]|$)",
            block,
        ) is None
