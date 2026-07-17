from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    FRESH_B_SEEDS,
    PILOT_CASES_PER_FAMILY,
    SCENARIO_FAMILIES,
    RetainedScenarioCapabilityFailure,
    ScenarioCapabilityReason,
    V25ControlledSceneAdapter,
    build_controlled_scenario_case,
    build_controlled_scenario_plan,
    build_final_controlled_corpus_plan,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_runtime_signal_receipt,
)


def _route(index: int, family: str, *, traffic_light: bool = False) -> dict:
    x = np.linspace(0.0, 100.0, 101)
    centerline = np.column_stack((x, np.full_like(x, float(index % 7))))
    identity = f"{index + 1:064x}"[-64:]
    map_sha = {
        "map_family_d7f16a17d3eb": "a" * 64,
        "map_family_f62e06cd1303": "b" * 64,
        "map_family_828a913c2f9a": "c" * 64,
    }[family]
    return {
        "record_key": f"{family}/map/{index}/{identity[:16]}",
        "identity_sha256": identity,
        "map_family_id": family,
        "route_serialization_sha256": f"{index + 1000:064x}"[-64:],
        "source_map_path": f"/maps/{family}.osm",
        "source_map_sha256": map_sha,
        "source_route_length_m": 100.0,
        "centerline_samples_m": centerline.tolist(),
        "centerline_headings_rad": np.zeros(101).tolist(),
        "route_spec": {
            "map_path": f"/maps/{family}.osm",
            "start_pose": [0.0, float(index % 7), 0.0],
            "goal_pose": [100.0, float(index % 7), 0.0],
            "lanelet_ids": [index + 1],
            "route_length_m": 100.0,
        },
        "source_stratum": {
            "branch_intersection": index % 2 == 0,
            "short_progress_opportunity": index % 3 == 0,
            "tight_corridor": True,
            "traffic_light": traffic_light,
        },
    }


def _inventory() -> tuple[list[dict], list[dict]]:
    routes = []
    split = []
    index = 0
    specs = (
        ("map_family_d7f16a17d3eb", 375),
        ("map_family_f62e06cd1303", 2),
        ("map_family_828a913c2f9a", 24),
    )
    for family, count in specs:
        for local in range(count):
            route = _route(
                index,
                family,
                traffic_light=(family == "map_family_d7f16a17d3eb" and local < 32),
            )
            routes.append(route)
            if family == "map_family_d7f16a17d3eb":
                corridor = "1" * 64
            elif family == "map_family_f62e06cd1303":
                corridor = "2" * 64
            else:
                corridor = f"{3 + local % 3:x}" * 64
            split.append(
                {
                    "record_key": route["record_key"],
                    "corridor_group_sha256": corridor,
                }
            )
            index += 1
    return routes, split


def test_controlled_plan_freezes_coverage_capacity_and_honest_inventory_ceiling():
    routes, split = _inventory()
    plan = build_controlled_scenario_plan(routes, split)

    assert len(plan.pilot) == len(SCENARIO_FAMILIES) * PILOT_CASES_PER_FAMILY
    assert len(plan.train) == 1500
    assert len(plan.calibration) == 42
    assert len(plan.fresh_b) == 120
    assert sum(len(case["seeds"]) for case in plan.fresh_b) == 600
    assert {seed for case in plan.fresh_b for seed in case["seeds"]} == set(
        FRESH_B_SEEDS
    )
    assert plan.summary["fresh_b_route_ceiling"] == 24
    assert plan.summary["fresh_b_corridor_ceiling"] == 3
    assert plan.summary["combined_train_snapshot_capacity_at_64_ticks"] >= 150_000
    assert all(case["runner_eligible"] for case in plan.pilot)
    assert all(case["family"] != "red_light_phase_timing" for case in plan.fresh_b)
    unavailable_calibration = [
        case for case in plan.calibration if case["runner_eligible"] is False
    ]
    assert len(unavailable_calibration) == 6
    assert {case["family"] for case in unavailable_calibration} == {
        "red_light_phase_timing"
    }


def test_final_plan_uses_source_complete_routes_and_retains_ineligible_inventory():
    routes, split = _inventory()
    availability = {}
    train_seen = 0
    fresh_seen = 0
    for route in routes:
        family = route["map_family_id"]
        if family == "map_family_d7f16a17d3eb":
            complete = train_seen < 300
            train_seen += 1
        elif family == "map_family_f62e06cd1303":
            complete = True
        else:
            complete = fresh_seen < 20
            fresh_seen += 1
        availability[route["record_key"]] = {
            "speed_limit_complete": complete,
            "mapped_traffic_light": bool(route["source_stratum"]["traffic_light"]),
        }

    plan = build_final_controlled_corpus_plan(routes, split, availability)

    summary = plan["summary"]
    assert summary["split_counts"]["train"]["executable_identity_count"] == 1500
    assert summary["split_counts"]["train"]["source_ineligible_identity_count"] == 75
    assert summary["split_counts"]["fresh_b"]["executable_identity_count"] == 120
    assert summary["split_counts"]["fresh_b"]["source_ineligible_identity_count"] == 4
    assert summary["fresh_b_paired_run_count"] == 600
    assert summary["fresh_b_independent_route_ceiling"] == 20
    assert summary["combined_train_snapshot_capacity_at_64_ticks"] >= 150_000
    assert all(
        case["retention_role"] == "source_ineligible_retained"
        for case in plan["train"]
        if not case["runner_eligible"]
    )


class AgentType(Enum):
    VEHICLE = "vehicle"
    PEDESTRIAN = "pedestrian"
    BICYCLE = "bicycle"


@dataclass
class Agent:
    id: str
    agent_type: AgentType
    length: float
    width: float
    wheelbase: float
    past_trajectory: np.ndarray
    past_velocities: np.ndarray | None = None
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    steering_angle: float = 0.0
    yaw_rate: float = 0.0
    future_trajectory: np.ndarray | None = None
    goal_pose: np.ndarray | None = None
    route_lanes: np.ndarray | None = None
    route_speed_limit: np.ndarray | None = None
    route_has_speed_limit: np.ndarray | None = None
    turn_indicators: np.ndarray | None = None
    age_steps: int = 999
    route_lanelet_ids: list[int] | None = None

    @property
    def current_position(self) -> np.ndarray:
        return self.past_trajectory[-1, :2].copy()


def _scene(*, signal: bool = False):
    trajectory = np.zeros((31, 3), dtype=np.float32)
    route_lanes = np.zeros((2, 20, 33), dtype=np.float32)
    map_lanes = np.zeros((4, 20, 33), dtype=np.float32)
    route_lanes[:, :, 12] = 1.0
    map_lanes[:, :, 12] = 1.0
    if signal:
        route_lanes[0, :, 12] = 0.0
        route_lanes[0, :, 8] = 1.0
        map_lanes[0, :, 12] = 0.0
        map_lanes[0, :, 8] = 1.0
    ego = Agent(
        id="ego",
        agent_type=AgentType.VEHICLE,
        length=4.8,
        width=1.9,
        wheelbase=3.1,
        past_trajectory=trajectory,
        past_velocities=np.zeros((31, 2), dtype=np.float32),
        route_lanes=route_lanes,
        route_lanelet_ids=[1, 2],
    )
    scene = SimpleNamespace(
        agents=[ego],
        ego_agent=ego,
        dt=0.1,
        map_data=SimpleNamespace(lanes=map_lanes),
    )
    return scene


def _signal_authority(case: dict) -> dict:
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]], dtype=np.float64)
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    chain = {
        "schema_version": SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "regulatory_element_ids": [100],
        "physical_light_ids": [101],
        "bulb_ids": [102],
        "controlled_lanelet_ids": [1],
        "route_lanelet_ids": [1, 2],
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 103,
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
        "stop_line_route_distance_m": 0.0,
        "route_arc_m": 20.0,
        "route_length_m": 100.0,
        "expected_current_phase": case["signal"]["phase"],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return chain


def test_scene_adapter_injects_scripted_actor_without_candidate_or_outcome_inputs():
    route = _route(0, "map_family_d7f16a17d3eb")
    case = build_controlled_scenario_case(
        route=route,
        corridor_group_sha256="1" * 64,
        split="pilot_development",
        family="lead_vehicle_hard_brake",
        tier="high_risk",
        variant=0,
        seeds=[25991],
    )
    scene = _scene()
    adapter = V25ControlledSceneAdapter(case)

    first = adapter(scene, 0)
    second = adapter(scene, 20)

    assert len(scene.agents) == 2
    assert scene.agents[1].id.startswith("static_npc_v25_")
    assert first["candidate_tensor_consumed"] is False
    assert first["selected_trajectory_consumed"] is False
    assert first["outcome_fields_consumed"] == []
    assert second["actors"][0]["scripted_exogenous"] is True
    assert np.linalg.norm(scene.agents[1].current_position - scene.agents[0].current_position) > 0


def test_scene_adapter_only_overwrites_existing_mapped_signal_rows():
    route = _route(0, "map_family_d7f16a17d3eb", traffic_light=True)
    case = build_controlled_scenario_case(
        route=route,
        corridor_group_sha256="1" * 64,
        split="pilot_development",
        family="red_light_phase_timing",
        tier="high_risk",
        variant=0,
        seeds=[25991],
    )
    scene = _scene(signal=True)
    chain = _signal_authority(case)
    adapter = V25ControlledSceneAdapter(case, red_signal_authority=chain)
    adapter.bind_map_lanelet_ids([1, 3, 4, 5])
    receipt = adapter(scene, 0)

    assert receipt["signal"]["applied"] is True
    assert receipt["signal"]["source_row_count"] == 2
    assert np.all(scene.ego_agent.route_lanes[0, :, 10] == 1.0)
    assert np.all(scene.map_data.lanes[0, :, 10] == 1.0)
    assert np.all(scene.map_data.lanes[1:, :, 12] == 1.0)
    validate_runtime_signal_receipt(
        receipt["signal"]["source_receipt"], chain
    )


def test_scene_adapter_raises_typed_capability_failure_for_missing_signal_source():
    route = _route(0, "map_family_d7f16a17d3eb", traffic_light=True)
    case = build_controlled_scenario_case(
        route=route,
        corridor_group_sha256="1" * 64,
        split="train",
        family="red_light_phase_timing",
        tier="high_risk",
        variant=0,
        seeds=[25001],
    )

    with pytest.raises(RetainedScenarioCapabilityFailure) as captured:
        V25ControlledSceneAdapter(case)(_scene(signal=False), 0)

    assert captured.value.as_receipt() == {
        "scenario_id": case["scenario_id"],
        "family": "red_light_phase_timing",
        "reason": ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value,
    }
