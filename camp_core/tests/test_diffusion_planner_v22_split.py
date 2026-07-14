import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "integrations" / "build_diffusion_planner_v22_split.py"


def _split_module():
    from camp_core.integrations import diffusion_planner_v22_split

    return diffusion_planner_v22_split


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _route(
    name: str,
    *,
    y: float,
    identity: str | None = None,
    lanelets=(),
    boundaries=(),
    topology_complex=None,
    entry_arm=None,
    exit_arm=None,
    logical_map="map-a",
):
    return {
        "record_key": name,
        "identity_sha256": identity or _sha(name),
        "logical_map_sha256": _sha(logical_map),
        "lanelet_ids": list(lanelets or [int(_sha(name)[:6], 16)]),
        "boundary_ids": list(boundaries),
        "centerline_samples_m": [[float(x), y] for x in range(25)],
        "centerline_headings_rad": [0.0] * 25,
        "topology_complex": topology_complex,
        "entry_arm": entry_arm,
        "exit_arm": exit_arm,
        "source_stratum": {
            "traffic_light": False,
            "branch_intersection": topology_complex is not None,
            "tight_corridor": False,
            "short_progress_opportunity": False,
        },
        "holdout_forbidden": False,
    }


def _group_by_record(grouping):
    return {
        record: group["group_sha256"]
        for group in grouping["groups"]
        for record in group["route_record_keys"]
    }


def test_leakage_graph_groups_all_source_only_rules_and_transitive_edges() -> None:
    module = _split_module()
    duplicate = _sha("duplicate")
    routes = [
        _route("a", y=0.0, lanelets=[1], boundaries=[10]),
        _route("b", y=100.0, lanelets=[1], boundaries=[20]),
        _route("c", y=200.0, lanelets=[3], boundaries=[20]),
        _route("d", y=300.0),
        _route("e", y=302.0),
        _route(
            "f",
            y=400.0,
            topology_complex="complex-1",
            entry_arm="north",
            exit_arm="east",
        ),
        _route(
            "g",
            y=500.0,
            topology_complex="complex-1",
            entry_arm="north",
            exit_arm="east",
        ),
        _route("h", y=600.0),
        _route("i", y=700.0, identity=duplicate),
        _route("j", y=800.0, identity=duplicate),
    ]

    grouping = module.build_leakage_groups(routes)
    group = _group_by_record(grouping)

    assert group["a"] == group["b"] == group["c"]
    assert group["d"] == group["e"]
    assert group["f"] == group["g"]
    assert group["i"] == group["j"]
    assert group["h"] not in {group["a"], group["d"], group["f"], group["i"]}
    reasons = {
        tuple(sorted((edge["route_a"], edge["route_b"]))): set(edge["reasons"])
        for edge in grouping["edges"]
    }
    assert "shared_lanelet" in reasons[("a", "b")]
    assert "shared_boundary" in reasons[("b", "c")]
    assert "overlapping_corridor" in reasons[("d", "e")]
    assert "same_topology_family" in reasons[("f", "g")]
    assert "equal_route_identity" in reasons[("i", "j")]


def test_split_freeze_allows_map_reuse_and_preregisters_both_arms() -> None:
    module = _split_module()
    routes = [
        _route("train-route", y=0.0),
        _route("cal-route", y=100.0),
        _route("holdout-route", y=200.0),
    ]
    grouping = module.build_leakage_groups(routes)
    manifest = module.freeze_split_manifest(
        grouping,
        seed_namespaces={
            "train": [22001, 22002],
            "calibration": [22101, 22102, 22103],
            "holdout": [22201, 22202, 22203, 22204, 22205],
        },
        targets={"train": 1, "calibration": 1, "holdout": 1},
    )

    module.validate_split_manifest(manifest)
    assert manifest["route_coverage"]["source_route_records"] == 3
    assert manifest["route_coverage"]["preregistered_unique_routes"] == 3
    assert manifest["excluded_pre_preregistration"] == []
    assert {
        route["logical_map_sha256"]
        for split in manifest["splits"].values()
        for route in split["routes"]
    } == {_sha("map-a")}
    assert len(manifest["expected_pairs"]) == 10
    assert all(
        pair["expected_arms"] == ["dp", "camp"]
        and pair["receipt_key"].endswith("/pair.json")
        for pair in manifest["expected_pairs"]
    )


@pytest.mark.parametrize("overlap", ("identity", "group", "seed"))
def test_split_validation_rejects_identity_group_or_seed_overlap(overlap) -> None:
    module = _split_module()
    grouping = module.build_leakage_groups(
        [_route("a", y=0.0), _route("b", y=100.0), _route("c", y=200.0)]
    )
    manifest = module.freeze_split_manifest(
        grouping,
        seed_namespaces={
            "train": [22001],
            "calibration": [22101],
            "holdout": [22201],
        },
        targets={"train": 1, "calibration": 1, "holdout": 1},
    )
    broken = copy.deepcopy(manifest)
    train = broken["splits"]["train"]
    calibration = broken["splits"]["calibration"]
    if overlap == "identity":
        calibration["routes"].append(copy.deepcopy(train["routes"][0]))
    elif overlap == "group":
        calibration["group_sha256"].append(train["group_sha256"][0])
    else:
        calibration["seed_namespace"].append(train["seed_namespace"][0])

    with pytest.raises(ValueError, match=overlap):
        module.validate_split_manifest(broken)


@pytest.mark.parametrize("field", ("map_id", "route_id", "split"))
def test_selector_feature_denylist_rejects_identity_fields(field) -> None:
    module = _split_module()

    with pytest.raises(ValueError, match="forbidden selector feature"):
        module.validate_feature_fields(["route_length_m", field])

    module.validate_feature_fields(["speed_excess", "route_progress_shortfall"])


def test_source_route_rejects_observed_outcome_fields() -> None:
    module = _split_module()
    route = _route("leaky", y=0.0)
    route["safety_cost"] = 1.0

    with pytest.raises(ValueError, match="outcome field"):
        module.build_leakage_groups([route])


def test_true_ceiling_no_go_keeps_every_source_record_accounted() -> None:
    module = _split_module()
    routes = [_route(str(index), y=100.0 * index) for index in range(3)]
    for route in routes:
        route["holdout_forbidden"] = True
    grouping = module.build_leakage_groups(routes)

    manifest = module.freeze_split_manifest(
        grouping,
        seed_namespaces={
            "train": [22001],
            "calibration": [22101],
            "holdout": [22201],
        },
        targets={"train": 1, "calibration": 1, "holdout": 1},
    )

    assert manifest["status"] == "no_go_true_ceiling"
    assert manifest["target_reached"]["holdout"] is False
    assert manifest["achieved_route_counts"]["holdout"] == 0
    coverage = manifest["route_coverage"]
    assert coverage["source_route_records"] == (
        coverage["preregistered_unique_routes"]
        + coverage["excluded_pre_preregistration_records"]
    )


def test_global_group_allocation_prioritizes_pilot_and_main_hard_targets() -> None:
    module = _split_module()
    records = []
    groups = []
    offset = 0
    for group_index, (size, holdout_forbidden) in enumerate(
        ((759, False), (152, True), (4, False))
    ):
        members = []
        identities = []
        for index in range(size):
            route = _route(
                f"g{group_index}-{index}",
                y=float(offset + index) * 10.0,
                logical_map=f"map-{group_index}",
            )
            route["holdout_forbidden"] = holdout_forbidden
            records.append(route)
            members.append(route["record_key"])
            identities.append(route["identity_sha256"])
        offset += size
        groups.append(
            {
                "group_sha256": _sha(f"group-{group_index}"),
                "route_record_keys": members,
                "route_identity_sha256": sorted(identities),
                "route_record_count": size,
                "unique_route_count": size,
                "logical_map_sha256": [_sha(f"map-{group_index}")],
                "source_stratum_counts": {
                    "traffic_light": 0,
                    "branch_intersection": 0,
                    "tight_corridor": 0,
                    "short_progress_opportunity": 0,
                },
                "holdout_forbidden": holdout_forbidden,
            }
        )
    grouping = {
        "schema_version": "v22_route_leakage_groups_v1",
        "route_records": records,
        "groups": groups,
        "edges": [],
    }

    manifest = module.freeze_split_manifest(
        grouping,
        seed_namespaces={
            "train": [22001, 22002, 22003, 22004, 22005, 22006, 22007, 22008],
            "calibration": [22101, 22102, 22103],
            "holdout": [22201, 22202, 22203, 22204, 22205],
        },
        targets={"train": 500, "calibration": 30, "holdout": 100},
    )

    assert manifest["status"] == "frozen"
    assert manifest["achieved_route_counts"] == {
        "train": 4,
        "calibration": 30,
        "holdout": 100,
    }
    assert manifest["target_reached"] == {
        "train": False,
        "calibration": True,
        "holdout": True,
    }
    assert len(manifest["expected_pairs"]) == 622


def test_split_manifest_is_byte_deterministic() -> None:
    module = _split_module()
    routes = [_route(str(index), y=100.0 * index) for index in range(6)]
    grouping = module.build_leakage_groups(routes)
    kwargs = {
        "seed_namespaces": {
            "train": [22001, 22002],
            "calibration": [22101],
            "holdout": [22201],
        },
        "targets": {"train": 2, "calibration": 1, "holdout": 1},
    }

    first = module.freeze_split_manifest(grouping, **kwargs)
    second = module.freeze_split_manifest(grouping, **kwargs)

    assert module.canonical_json_bytes(first) == module.canonical_json_bytes(second)


def test_cli_synthetic_fixture_writes_byte_identical_frozen_manifest(tmp_path) -> None:
    routes = [_route(str(index), y=100.0 * index) for index in range(3)]
    config = {
        "schema_version": "v22_split_preregistration_v1",
        "synthetic_fixture": True,
        "route_records": routes,
        "leakage_thresholds": {
            "sample_spacing_m": 1.0,
            "overlap_distance_m": 3.0,
            "min_overlap_samples": 20,
            "max_heading_delta_deg": 15.0,
        },
        "targets": {"train": 1, "calibration": 1, "holdout": 1},
        "seed_namespaces": {
            "train": [22001],
            "calibration": [22101],
            "holdout": [22201],
        },
        "selector_feature_fields": ["progress_shortfall"],
        "materialize_route_assets": False,
        "outcome_fields": [],
        "full36_authorized": False,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "camp_core")
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--config",
                str(config_path),
                "--output-dir",
                str(output),
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        for name in (
            "HEADS",
            "COMMAND",
            "stdout.txt",
            "stderr.txt",
            "summary.json",
            "summary.md",
            "split_manifest.json",
            "SHA256SUMS",
            "ROOT_SHA256SUMS",
        ):
            assert (output / name).is_file()

    assert (outputs[0] / "split_manifest.json").read_bytes() == (
        outputs[1] / "split_manifest.json"
    ).read_bytes()
