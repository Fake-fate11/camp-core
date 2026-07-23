from __future__ import annotations

import copy
import hashlib
import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    build_controlled_scenario_case,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_fixture import (
    build_nonfresh_map_suite,
    build_nonfresh_prepared_runtime_rows,
    build_nonfresh_production_equivalence_plan,
    build_nonfresh_runtime_qualification_rows,
    select_nonfresh_actual_native_fixtures,
)
from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_scene_adapter,
)
from scripts.integrations.materialize_diffusion_planner_v25_production_equivalence_authority import (
    _strict_external_json,
)


def test_actual_nonfresh_fixture_covers_three_real_signal_branches(
    tmp_path,
) -> None:
    map_bytes = b"<osm version='0.6'></osm>\n"
    map_sha = hashlib.sha256(map_bytes).hexdigest()
    source_map = tmp_path / "source.osm"
    source_map.write_bytes(map_bytes)
    cases = [
        _case(
            index=0,
            source_map=source_map,
            map_sha=map_sha,
            family="red_light_phase_timing",
            tier="borderline",
            traffic_light=True,
        ),
        _case(
            index=1,
            source_map=source_map,
            map_sha=map_sha,
            family="lead_vehicle_hard_brake",
            tier="easy",
            traffic_light=True,
        ),
        _case(
            index=2,
            source_map=source_map,
            map_sha=map_sha,
            family="pedestrian_cyclist_crossing",
            tier="high_risk",
            traffic_light=False,
        ),
    ]
    chains = [
        _mapped_chain(cases[0]),
        _mapped_chain(cases[1]),
        _no_signal_chain(cases[2]),
    ]
    chain_payload = {
        "schema_version": (
            "camp_dp_v25_full_r_semantic_authority_chains_v3"
        ),
        "identity_count": 3,
        "chains_root_sha256": canonical_json_sha256(chains),
        "chains": chains,
    }
    formal = {
        "schema_version": "camp_dp_v25_controlled_corpus_final_plan_v1",
        "train": list(reversed(cases)),
        "outcome_fields_consumed": [],
    }
    selected = select_nonfresh_actual_native_fixtures(
        formal_plan=formal,
        semantic_authority_chains=chain_payload,
    )
    assert [row["nonfresh_scenario_class"] for row in selected] == [
        "mapped_controlled_override",
        "mapped_observe",
        "no_signal",
    ]
    plan = build_nonfresh_production_equivalence_plan(
        selected_fixtures=selected,
        source_fixture_root_sha256="f" * 64,
    )
    assert plan["planned_arm_run_count"] == 9
    assert plan["ticks_per_arm_run"] == 64
    assert plan["identity_count"] == 3

    map_root = tmp_path / "authority"
    target = map_root / "maps" / f"{map_sha}.osm"
    target.parent.mkdir(parents=True)
    target.write_bytes(map_bytes)
    prepared = build_nonfresh_prepared_runtime_rows(
        plan=plan,
        selected_fixtures=selected,
        map_artifact=map_root,
    )
    adapters = [
        build_signal_complete_scene_adapter(row) for row in prepared
    ]
    assert adapters[0].mapped_signal_authority is not None
    assert adapters[1].mapped_signal_authority is not None
    assert adapters[2].no_signal_authority is not None
    assert all(
        row["semantic_parameter_block_sha256"]
        == identity["semantic_parameter_block_sha256"]
        for row, identity in zip(
            prepared, plan["identities"], strict=True
        )
    )
    qualifications = build_nonfresh_runtime_qualification_rows(plan)
    assert len(qualifications) == 3
    assert qualifications[2]["signal_source_class"] == "no_signal"
    suite = build_nonfresh_map_suite(
        plan=plan,
        map_artifact=map_root,
        source_map_paths={map_sha: str(source_map.resolve())},
    )
    assert suite["map_count"] == 1
    assert suite["fresh_identity_cas_created"] is False


def test_actual_nonfresh_fixture_selects_route_distinct_real_branches(
    tmp_path,
) -> None:
    map_bytes = b"<osm version='0.6'></osm>\n"
    map_sha = hashlib.sha256(map_bytes).hexdigest()
    source_map = tmp_path / "source.osm"
    source_map.write_bytes(map_bytes)
    cases = [
        _case(
            index=0,
            source_map=source_map,
            map_sha=map_sha,
            family="red_light_phase_timing",
            tier="borderline",
            traffic_light=True,
        ),
        _case(
            index=0,
            source_map=source_map,
            map_sha=map_sha,
            family="lead_vehicle_hard_brake",
            tier="easy",
            traffic_light=True,
        ),
        _case(
            index=1,
            source_map=source_map,
            map_sha=map_sha,
            family="lead_vehicle_hard_brake",
            tier="easy",
            traffic_light=True,
        ),
        _case(
            index=2,
            source_map=source_map,
            map_sha=map_sha,
            family="pedestrian_cyclist_crossing",
            tier="high_risk",
            traffic_light=False,
        ),
    ]
    chains = [
        _mapped_chain(cases[0]),
        _mapped_chain(cases[1]),
        _mapped_chain(cases[2]),
        _no_signal_chain(cases[3]),
    ]
    selected = select_nonfresh_actual_native_fixtures(
        formal_plan={
            "schema_version": (
                "camp_dp_v25_controlled_corpus_final_plan_v1"
            ),
            "train": cases,
            "outcome_fields_consumed": [],
        },
        semantic_authority_chains={
            "schema_version": (
                "camp_dp_v25_full_r_semantic_authority_chains_v3"
            ),
            "identity_count": len(chains),
            "chains_root_sha256": canonical_json_sha256(chains),
            "chains": chains,
        },
    )
    routes = [
        row["case"]["route_identity_sha256"] for row in selected
    ]
    assert len(set(routes)) == 3
    assert (
        selected[1]["case"]["scenario_id"] == cases[2]["scenario_id"]
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_class", "fixture class is unavailable"),
        ("chain_hash", "semantic-chain authority drifted"),
    ],
)
def test_actual_nonfresh_fixture_rejects_missing_class_or_chain_drift(
    mutation: str,
    message: str,
) -> None:
    source = "/maps/source.osm"
    map_sha = "a" * 64
    cases = [
        _case(
            index=0,
            source_map=source,
            map_sha=map_sha,
            family="red_light_phase_timing",
            tier="borderline",
            traffic_light=True,
        ),
        _case(
            index=1,
            source_map=source,
            map_sha=map_sha,
            family="lead_vehicle_hard_brake",
            tier="easy",
            traffic_light=True,
        ),
        _case(
            index=2,
            source_map=source,
            map_sha=map_sha,
            family="pedestrian_cyclist_crossing",
            tier="high_risk",
            traffic_light=False,
        ),
    ]
    chains = [
        _mapped_chain(cases[0]),
        _mapped_chain(cases[1]),
        _no_signal_chain(cases[2]),
    ]
    if mutation == "missing_class":
        chains = chains[:-1]
    payload = {
        "schema_version": (
            "camp_dp_v25_full_r_semantic_authority_chains_v3"
        ),
        "identity_count": len(chains),
        "chains_root_sha256": canonical_json_sha256(chains),
        "chains": chains,
    }
    if mutation == "chain_hash":
        payload["chains_root_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=message):
        select_nonfresh_actual_native_fixtures(
            formal_plan={
                "schema_version": (
                    "camp_dp_v25_controlled_corpus_final_plan_v1"
                ),
                "train": cases,
                "outcome_fields_consumed": [],
            },
            semantic_authority_chains=payload,
        )


def test_external_fixture_json_is_strict_but_not_camp_canonical(
    tmp_path,
) -> None:
    path = tmp_path / "pretty.json"
    path.write_text(
        json.dumps({"rows": [1, 2, 3]}, indent=2) + "\n",
        encoding="utf-8",
    )
    assert _strict_external_json(path) == {"rows": [1, 2, 3]}


@pytest.mark.parametrize(
    "raw",
    (
        b'{"rows":[],"rows":[1]}\n',
        b'{"rows":[NaN]}\n',
        b'["not-an-object"]\n',
        b'{"rows":["\xff"]}\n',
    ),
)
def test_external_fixture_json_rejects_invalid_bytes(
    tmp_path, raw: bytes
) -> None:
    path = tmp_path / "invalid.json"
    path.write_bytes(raw)
    with pytest.raises((UnicodeDecodeError, ValueError)):
        _strict_external_json(path)


def _case(
    *,
    index: int,
    source_map,
    map_sha: str,
    family: str,
    tier: str,
    traffic_light: bool,
) -> dict:
    route = {
        "record_key": f"route/{index}",
        "identity_sha256": f"{index + 1:064x}",
        "map_family_id": "map_family_d7f16a17d3eb",
        "route_serialization_sha256": f"{index + 101:064x}",
        "source_map_path": str(source_map),
        "source_map_sha256": map_sha,
        "source_route_length_m": 100.0,
        "centerline_samples_m": np.column_stack(
            (np.linspace(0.0, 100.0, 101), np.zeros(101))
        ).tolist(),
        "centerline_headings_rad": np.zeros(101).tolist(),
        "route_spec": {
            "map_path": str(source_map),
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [100.0, 0.0, 0.0],
            "lanelet_ids": [index + 1],
            "route_length_m": 100.0,
        },
        "source_stratum": {
            "branch_intersection": True,
            "short_progress_opportunity": False,
            "tight_corridor": True,
            "traffic_light": traffic_light,
        },
    }
    return build_controlled_scenario_case(
        route=route,
        corridor_group_sha256=f"{index + 10:064x}",
        split="train",
        family=family,
        tier=tier,
        variant=index,
        seeds=[25001],
    )


def _mapped_chain(case: dict) -> dict:
    route = np.column_stack(
        (np.linspace(0.0, 100.0, 101), np.zeros(101))
    )
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]])
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    controlled = case["signal"]["phase"] != "none"
    chain = {
        "schema_version": MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "phase_authority_mode": (
            "controlled_same_tick_override"
            if controlled
            else "observe_same_tick_request"
        ),
        "expected_current_phase": (
            case["signal"]["phase"] if controlled else None
        ),
        "formal_phase": case["signal"]["phase"],
        "formal_mapped_source_required": controlled,
        "formal_route_mapped_traffic_light": True,
        "phase_remaining_available": False,
        "regulatory_element_ids": [100],
        "physical_light_ids": [101],
        "bulb_ids": [102],
        "controlled_lanelet_ids": [case["route_spec"]["lanelet_ids"][0]],
        "route_lanelet_ids": list(case["route_spec"]["lanelet_ids"]),
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic[
                    "route_polyline_local_m"
                ],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 103,
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(
            stop.tolist()
        ),
        "stop_line_route_distance_m": 0.0,
        "route_arc_m": 20.0,
        "route_length_m": 100.0,
        "route_tangent_world": [1.0, 0.0],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in chain.items()
            if key != "source_chain_sha256"
        }
    )
    return chain


def _no_signal_chain(case: dict) -> dict:
    route = np.column_stack(
        (np.linspace(0.0, 100.0, 101), np.zeros(101))
    )
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=None
    )
    chain = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "route_lanelet_ids": list(case["route_spec"]["lanelet_ids"]),
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic[
                    "route_polyline_local_m"
                ]
            }
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in chain.items()
            if key != "source_chain_sha256"
        }
    )
    return chain
