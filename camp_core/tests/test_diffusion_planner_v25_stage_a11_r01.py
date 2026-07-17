from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.integrations.diffusion_planner import CAMPSelector
from camp_core.integrations.diffusion_planner_causal_atoms import (
    build_v25_atom_source_masks,
    clearance_hinge_costs,
    compute_authorized_red_stopping_margin_costs,
    lane_boundary_deviation_costs,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    SEMANTIC_PAYLOAD_SCHEMA_VERSION,
    SIGNAL_CHAIN_SCHEMA_VERSION,
    build_causal_signal_atom_input,
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
    build_runtime_signal_receipt,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_causal_signal_atom_input,
    validate_no_signal_chain,
    validate_signal_chain,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
    select_camp_candidate,
)
from scripts.integrations.build_diffusion_planner_v25_static_atom_ledger import (
    _dag_contract as producer_dag_contract,
)
from scripts.integrations.validate_diffusion_planner_v25_static_atom_ledger import (
    _expected_dag_contract as reviewer_dag_contract,
)
from scripts.integrations.preflight_diffusion_planner_v25_r0_authority_source import (
    _physical_signature_payload,
)
from scripts.integrations import review_diffusion_planner_v25_r0_red_k8 as r0_reviewer
from scripts.integrations import (
    review_diffusion_planner_v25_full_config_preflight as full_config_reviewer,
)


def test_stage_a_dag_plan_matches_independent_exact_contract() -> None:
    plan_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_atom_ledger_plan_v4.json"
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["dag"] == producer_dag_contract()
    assert plan["dag"] == reviewer_dag_contract()


def test_physical_signature_is_se2_and_controlled_order_invariant() -> None:
    controlled = [
        np.asarray([[0.0, 0.0], [10.0, 0.5], [20.0, 1.0]]),
        np.asarray([[0.0, 3.0], [10.0, 3.5], [20.0, 4.0]]),
    ]
    stop = np.asarray([[12.0, -2.0], [12.0, 6.0]])
    tangent = np.asarray([1.0, 0.05])
    baseline = _physical_signature_payload(controlled, stop, tangent)
    angle = 0.73
    rotation = np.asarray(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    translation = np.asarray([87.0, -31.0])
    transformed = _physical_signature_payload(
        [line @ rotation.T + translation for line in reversed(controlled)],
        stop @ rotation.T + translation,
        tangent @ rotation.T,
    )
    assert canonical_json_sha256(transformed) == canonical_json_sha256(baseline)

    mutated = _physical_signature_payload(
        [controlled[0] + np.asarray([0.0, 0.4]), controlled[1]], stop, tangent
    )
    assert canonical_json_sha256(mutated) != canonical_json_sha256(baseline)


def _case() -> dict:
    return {
        "scenario_id": "1" * 64,
        "route_identity_sha256": "2" * 64,
        "source_map_sha256": "3" * 64,
        "source_map_path": "/source/export/map.osm",
        "source_family": "source_a",
        "repository": "repo_a",
        "map_family_id": "map_a",
        "route_family_id": "route_a",
        "parameter_block_id": "block_a",
        "split": "train",
        "seed": 25001,
        "family": "red_light_phase_timing",
        "tier": "borderline",
        "semantic_variant": "red_straight",
        "parameters": {
            "headway_m": 22.0,
            "ego_speed_mps": 8.0,
            "other_speed_mps": 5.0,
            "deceleration_mps2": -4.0,
            "trigger_time_s": 1.5,
            "lateral_offset_m": 3.0,
            "lateral_speed_mps": 1.0,
            "crossing_speed_mps": 1.8,
            "variant": 4,
        },
        "actors": [
            {
                "id": "actor-a",
                "agent_type": "vehicle",
                "initial_xy": [15.0, 2.0],
                "initial_heading_rad": 0.2,
                "route_tangent": [1.0, 0.0],
                "route_normal": [0.0, 1.0],
                "trigger_time_s": 1.5,
                "longitudinal_speed_mps": 5.0,
                "lateral_offset_m": 2.0,
                "lateral_speed_mps": -1.0,
                "lateral_target_m": 0.0,
                "longitudinal_acceleration_mps2": -2.0,
                "length_m": 4.5,
                "width_m": 1.8,
                "wheelbase_m": 2.9,
            },
            {
                "id": "actor-b",
                "agent_type": "pedestrian",
                "initial_xy": [18.0, -1.0],
                "initial_heading_rad": math.pi / 2,
                "route_tangent": [1.0, 0.0],
                "route_normal": [0.0, 1.0],
                "trigger_time_s": 2.0,
                "longitudinal_speed_mps": 0.0,
                "lateral_offset_m": -1.0,
                "lateral_speed_mps": 1.2,
                "lateral_target_m": 2.0,
                "longitudinal_acceleration_mps2": 0.0,
                "length_m": 0.7,
                "width_m": 0.6,
                "wheelbase_m": 0.5,
            },
        ],
        "signal": {"phase": "red", "mapped_source_required": True},
    }


def _chain(stop_x: float = 20.0) -> dict:
    case = _case()
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[stop_x, -2.0], [stop_x, 2.0]], dtype=np.float64)
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    chain = {
        "schema_version": SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "regulatory_element_ids": [10],
        "physical_light_ids": [11],
        "bulb_ids": [12],
        "controlled_lanelet_ids": [20],
        "route_lanelet_ids": [20, 21],
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 13,
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
        "stop_line_route_distance_m": 0.01,
        "route_arc_m": float(stop_x),
        "route_length_m": 100.0,
        "route_tangent_world": [1.0, 0.0],
        "expected_current_phase": "red",
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {k: v for k, v in chain.items() if k != "source_chain_sha256"}
    )
    return validate_signal_chain(chain)


def _receipt(chain: dict) -> dict:
    return build_runtime_signal_receipt(
        chain,
        scenario_id=chain["scenario_id"],
        tick_index=3,
        decision_time_s=0.3,
        current_phase="red",
        applied_route_lanelet_ids=[20],
        applied_map_lanelet_ids=[],
    )


def _candidates() -> np.ndarray:
    trajectories = np.zeros((8, 80, 4), dtype=np.float32)
    for index in range(8):
        trajectories[index, :, 0] = np.linspace(0.0, 22.0 + index, 80)
        trajectories[index, :, 2] = 1.0
    return trajectories


def test_authorized_stop_line_is_explicit_ego_frame_atom_input() -> None:
    chain = _chain(20.0)
    signal_input = build_causal_signal_atom_input(
        chain,
        _receipt(chain),
        ego_position_world_m=[2.0, 1.0],
        ego_heading_rad=math.pi / 2,
    )
    validated = validate_causal_signal_atom_input(signal_input, chain, _receipt(chain))
    np.testing.assert_allclose(
        validated["stop_line_geometry_ego_m"], [[-3.0, -18.0], [1.0, -18.0]]
    )
    assert validated["source_chain_sha256"] == chain["source_chain_sha256"]
    assert validated["stop_line_geometry_sha256"] == chain["stop_line_geometry_sha256"]
    assert validated["applicable"] is True

    wrong = copy.deepcopy(signal_input)
    wrong["stop_line_geometry_ego_m"] = [[-3.0, -17.0], [1.0, -17.0]]
    with pytest.raises(ValueError, match="ego-frame stop line"):
        validate_causal_signal_atom_input(wrong, chain, _receipt(chain))


def test_red_stopping_cost_uses_only_authorized_stop_line_geometry() -> None:
    candidates = _candidates()
    far_chain = _chain(20.0)
    near_chain = _chain(12.0)
    far = build_causal_signal_atom_input(
        far_chain, _receipt(far_chain), ego_position_world_m=[0.0, 0.0], ego_heading_rad=0.0
    )
    near = build_causal_signal_atom_input(
        near_chain, _receipt(near_chain), ego_position_world_m=[0.0, 0.0], ego_heading_rad=0.0
    )
    far_cost = compute_authorized_red_stopping_margin_costs(candidates, far, 0.1)
    near_cost = compute_authorized_red_stopping_margin_costs(candidates, near, 0.1)
    assert np.any(np.abs(far_cost - near_cost) > 1e-9)

    substituted = copy.deepcopy(far)
    substituted["stop_line_geometry_ego_m"] = [[12.0, -2.0], [12.0, 2.0]]
    with pytest.raises(ValueError, match="ego-frame stop line"):
        compute_authorized_red_stopping_margin_costs(candidates, substituted, 0.1)


def test_r0_reviewer_strictly_recomputes_red_atom_masks_and_k8() -> None:
    chain = _chain(20.0)
    receipt = _receipt(chain)
    causal = build_causal_signal_atom_input(
        chain,
        receipt,
        ego_position_world_m=[0.0, 0.0],
        ego_heading_rad=0.0,
    )
    candidates = _candidates()
    raw = np.zeros((8, 14), dtype=np.float64)
    raw[:, 12] = compute_authorized_red_stopping_margin_costs(
        candidates, causal, 0.1
    )
    row = {
        "raw_atom_matrix": raw.tolist(),
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [False] * 8,
        "atom_source_valid_mask": [[True] * 14 for _ in range(8)],
        "atom_applicable_mask": [[True] * 14 for _ in range(8)],
        "candidate_tensor": candidates.tolist(),
        "causal_signal_atom_input": causal,
        "current_phase": "red",
        "dt_s": 0.1,
        "all_k_high_risk": True,
    }
    checked = r0_reviewer._independently_validate_tick_atoms(
        row, chain=chain, signal_receipt=receipt
    )
    assert checked[5].shape == (8, 80, 4)

    mutations = []
    non_bool = copy.deepcopy(row)
    non_bool["source_valid_mask"][0] = 1
    mutations.append(non_bool)
    mismatched_source = copy.deepcopy(row)
    mismatched_source["atom_source_valid_mask"][0][0] = False
    mutations.append(mismatched_source)
    drifted_atom = copy.deepcopy(row)
    drifted_atom["raw_atom_matrix"][0][12] += 0.25
    mutations.append(drifted_atom)
    invalid_heading = copy.deepcopy(row)
    invalid_heading["candidate_tensor"][0][0][2:4] = [0.0, 0.0]
    mutations.append(invalid_heading)
    for mutated in mutations:
        with pytest.raises(ValueError):
            r0_reviewer._independently_validate_tick_atoms(
                mutated, chain=chain, signal_receipt=receipt
            )

    for mutation in ("nearby", "missing", "multi", "phase", "chain"):
        changed = copy.deepcopy(row)
        signal = changed["causal_signal_atom_input"]
        if mutation == "nearby":
            signal["stop_line_geometry_ego_m"][0][0] += 1.0
        elif mutation == "missing":
            signal.pop("stop_line_geometry_ego_m")
        elif mutation == "multi":
            signal["stop_line_geometry_ego_m"].append([21.0, 0.0])
        elif mutation == "phase":
            signal["current_phase"] = "green"
        else:
            signal["source_chain_sha256"] = "f" * 64
        with pytest.raises(ValueError):
            r0_reviewer._independently_validate_tick_atoms(
                changed, chain=chain, signal_receipt=receipt
            )


@pytest.mark.parametrize("phase", ["green", "yellow"])
def test_r0_reviewer_requires_zero_nonapplicable_signal_atoms(phase: str) -> None:
    chain = dict(_chain())
    chain["expected_current_phase"] = phase
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    receipt = build_runtime_signal_receipt(
        chain,
        scenario_id=chain["scenario_id"],
        tick_index=3,
        decision_time_s=0.3,
        current_phase=phase,
        applied_route_lanelet_ids=[20],
        applied_map_lanelet_ids=[],
    )
    causal = build_causal_signal_atom_input(
        chain, receipt, ego_position_world_m=[0.0, 0.0], ego_heading_rad=0.0
    )
    applicable = [[True] * 14 for _ in range(8)]
    for row in applicable:
        row[10] = False
        row[12] = False
    tick = {
        "raw_atom_matrix": np.zeros((8, 14)).tolist(),
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [True] * 8,
        "atom_source_valid_mask": [[True] * 14 for _ in range(8)],
        "atom_applicable_mask": applicable,
        "candidate_tensor": _candidates().tolist(),
        "causal_signal_atom_input": causal,
        "current_phase": phase,
        "dt_s": 0.1,
        "all_k_high_risk": False,
    }
    r0_reviewer._independently_validate_tick_atoms(
        tick, chain=chain, signal_receipt=receipt
    )
    tick["raw_atom_matrix"][0][12] = 1.0
    with pytest.raises(ValueError, match="applicability"):
        r0_reviewer._independently_validate_tick_atoms(
            tick, chain=chain, signal_receipt=receipt
        )


def test_r0_reviewer_accepts_certified_no_signal_and_rejects_missing_source() -> None:
    case = _case()
    case["family"] = "lead_vehicle_hard_brake"
    case["signal"] = {"phase": "none", "mapped_source_required": False}
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=None
    )
    chain = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "route_lanelet_ids": [20, 21],
        "route_geometry_sha256": canonical_json_sha256(
            semantic["route_polyline_local_m"]
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    chain = validate_no_signal_chain(chain)
    receipt = build_runtime_no_signal_receipt(
        chain, scenario_id=chain["scenario_id"], tick_index=3, decision_time_s=0.3
    )
    causal = build_no_signal_causal_atom_input(chain, receipt)
    applicable = [[True] * 14 for _ in range(8)]
    for row in applicable:
        row[10] = False
        row[12] = False
    tick = {
        "raw_atom_matrix": np.zeros((8, 14)).tolist(),
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [True] * 8,
        "atom_source_valid_mask": [[True] * 14 for _ in range(8)],
        "atom_applicable_mask": applicable,
        "candidate_tensor": _candidates().tolist(),
        "causal_signal_atom_input": causal,
        "current_phase": "none",
        "dt_s": 0.1,
        "all_k_high_risk": False,
    }
    r0_reviewer._independently_validate_tick_atoms(
        tick, chain=chain, signal_receipt=receipt
    )
    tick["causal_signal_atom_input"]["source_state"] = "unavailable"
    with pytest.raises(ValueError):
        r0_reviewer._independently_validate_tick_atoms(
            tick, chain=chain, signal_receipt=receipt
        )


def test_full_config_reviewer_independently_rebuilds_exact_receipt(
    tmp_path: Path,
) -> None:
    preflight = tmp_path / "preflight"
    routes = preflight / "routes"
    routes.mkdir(parents=True)
    case = _case()
    map_path = tmp_path / "map.osm"
    map_path.write_bytes(b"independent-map")
    map_sha = full_config_reviewer.file_sha256(map_path)
    case["source_map_path"] = str(map_path)
    case["source_map_sha256"] = map_sha
    case["seeds"] = [25001]
    case["runner_eligible"] = True
    case["retention_role"] = "executable"
    route_path = routes / f"{case['route_identity_sha256']}.pkl"
    route_path.write_bytes(b"independent-route")

    chain = _chain()
    chain["source_map_sha256"] = map_sha
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    checkpoint = tmp_path / "checkpoint.pth"
    args_json = tmp_path / "args.json"
    checkpoint.write_bytes(b"checkpoint")
    args_json.write_text("{}\n", encoding="utf-8")
    template = {
        "fixed_dp": {
            "head": full_config_reviewer.FIXED_DP_HEAD,
            "checkpoint": {
                "path": str(checkpoint),
                "sha256": full_config_reviewer.file_sha256(checkpoint),
            },
            "args_json": {
                "path": str(args_json),
                "sha256": full_config_reviewer.file_sha256(args_json),
            },
        }
    }
    receipts = full_config_reviewer._independent_config_receipts(
        preflight=preflight,
        cases=[case],
        chains=[chain],
        template=template,
        generation_scales_sha256="a" * 64,
        static_weights_sha256="b" * 64,
    )
    assert len(receipts) == 1
    assert set(receipts[0]) == full_config_reviewer.CONFIG_RECEIPT_FIELDS
    assert receipts[0]["route_sha256"] == full_config_reviewer.file_sha256(
        route_path
    )

    for field, replacement in (
        ("source_map_sha256", "c" * 64),
        ("scenario_id", "d" * 64),
    ):
        drifted = copy.deepcopy(chain)
        drifted[field] = replacement
        drifted["source_chain_sha256"] = canonical_json_sha256(
            {
                key: value
                for key, value in drifted.items()
                if key != "source_chain_sha256"
            }
        )
        with pytest.raises(ValueError):
            full_config_reviewer._independent_config_receipts(
                preflight=preflight,
                cases=[case],
                chains=[drifted],
                template=template,
                generation_scales_sha256="a" * 64,
                static_weights_sha256="b" * 64,
            )


def test_lane_and_clearance_formulas_use_asymmetric_boundary_and_obb_surface() -> None:
    lateral = np.asarray([[2.5, -1.5], [0.5, -0.5]])
    left = np.asarray([[2.0, 2.0], [1.0, 1.0]])
    right = np.asarray([[1.0, 1.0], [3.0, 3.0]])
    lane = lane_boundary_deviation_costs(lateral, left, right, 0.1)
    np.testing.assert_allclose(lane, [0.05, 0.0])

    obb_surface_clearance = np.asarray([[2.0, 3.5], [0.0, 3.0]])
    clearance = clearance_hinge_costs(obb_surface_clearance, 0.1)
    np.testing.assert_allclose(clearance, [0.1, 0.9])


def test_semantic_clone_is_se2_actor_order_source_id_outcome_independent() -> None:
    case = _case()
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]])
    baseline = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    clone = copy.deepcopy(case)
    clone["actors"] = list(reversed(clone["actors"]))
    clone.update(
        scenario_id="4" * 64,
        route_identity_sha256="5" * 64,
        source_map_sha256="6" * 64,
        source_map_path="/clone/map.osm",
        source_family="clone",
        repository="clone",
        map_family_id="clone",
        route_family_id="clone",
        parameter_block_id="clone",
        split="calibration",
        seed=999,
    )
    angle = 0.7
    rotation = np.asarray(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    translation = np.asarray([300.0, -75.0])
    for actor in clone["actors"]:
        actor["initial_xy"] = (np.asarray(actor["initial_xy"]) @ rotation.T + translation).tolist()
        actor["route_tangent"] = (np.asarray(actor["route_tangent"]) @ rotation.T).tolist()
        actor["route_normal"] = (np.asarray(actor["route_normal"]) @ rotation.T).tolist()
        actor["initial_heading_rad"] = float(actor["initial_heading_rad"] + angle)
        actor["id"] = "clone-" + actor["id"]
    transformed = build_semantic_clone_payload(
        clone,
        route_polyline_world=route @ rotation.T + translation,
        stop_line_world=stop @ rotation.T + translation,
    )
    assert canonical_json_sha256(transformed) == canonical_json_sha256(baseline)

    for container, key in (("parameters", "future_schedule"), ("actors", "outcome_collision")):
        invalid = copy.deepcopy(case)
        if container == "parameters":
            invalid[container][key] = [1, 2, 3]
        else:
            invalid[container][0][key] = True
        with pytest.raises(ValueError, match="forbidden|whitelist"):
            build_semantic_clone_payload(
                invalid, route_polyline_world=route, stop_line_world=stop
            )


def test_semantic_clone_v3_opposite_heading_has_no_pi_branch_cut() -> None:
    case = _case()
    case["family"] = "unprotected_turn_oncoming_conflict"
    case["semantic_variant"] = "unprotected_left_oncoming"
    case["actors"][0]["initial_heading_rad"] = math.pi
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]])
    baseline = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    assert baseline["schema_version"] == SEMANTIC_PAYLOAD_SCHEMA_VERSION
    assert baseline["schema_version"].endswith("_v3")
    assert "initial_heading_local_rad" not in baseline["actors"][0]
    assert all(
        "initial_heading_local_unit" in actor for actor in baseline["actors"]
    )

    angles = np.concatenate(
        (
            np.linspace(-math.pi, math.pi, 201),
            np.random.default_rng(25001).uniform(-8.0 * math.pi, 8.0 * math.pi, 64),
        )
    )
    translation = np.asarray([173.0, -91.0])
    expected = canonical_json_sha256(baseline)
    for angle in angles:
        rotation = np.asarray(
            [
                [math.cos(float(angle)), -math.sin(float(angle))],
                [math.sin(float(angle)), math.cos(float(angle))],
            ]
        )
        transformed_case = copy.deepcopy(case)
        transformed_case["actors"] = list(reversed(transformed_case["actors"]))
        for actor in transformed_case["actors"]:
            actor["initial_xy"] = (
                np.asarray(actor["initial_xy"]) @ rotation.T + translation
            ).tolist()
            actor["route_tangent"] = (
                np.asarray(actor["route_tangent"]) @ rotation.T
            ).tolist()
            actor["route_normal"] = (
                np.asarray(actor["route_normal"]) @ rotation.T
            ).tolist()
            actor["initial_heading_rad"] = float(
                actor["initial_heading_rad"] + angle
            )
            actor["id"] = "rotated-" + actor["id"]
        transformed = build_semantic_clone_payload(
            transformed_case,
            route_polyline_world=route @ rotation.T + translation,
            stop_line_world=stop @ rotation.T + translation,
        )
        assert canonical_json_sha256(transformed) == expected


def test_v25_atom_masks_separate_source_applicability_and_physical_feasibility() -> None:
    source, applicable = build_v25_atom_source_masks(
        route_speed_source_valid=np.asarray([True] * 7 + [False]),
        signal_source_state="available",
        current_phase="green",
    )
    assert source.shape == applicable.shape == (8, 14)
    assert source.dtype == applicable.dtype == np.bool_
    assert source[:7].all()
    assert not source[7, 4:7].any()
    assert source[:, 10].all() and source[:, 12].all()
    assert not applicable[:, 10].any() and not applicable[:, 12].any()

    no_signal_source, no_signal_applicable = build_v25_atom_source_masks(
        route_speed_source_valid=np.ones(8, dtype=bool),
        signal_source_state="not_applicable",
        current_phase="none",
    )
    assert no_signal_source[:, [10, 12]].all()
    assert not no_signal_applicable[:, [10, 12]].any()

    with pytest.raises(ValueError, match="unavailable"):
        build_v25_atom_source_masks(
            route_speed_source_valid=np.ones(8, dtype=bool),
            signal_source_state="unavailable",
            current_phase="red",
        )


def test_native_selector_requires_strict_direct_source_mask_and_subset() -> None:
    candidates = _candidates()
    base = {
        "canonical_eligible": True,
        "atom_matrix": np.zeros((8, 14)),
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "source_valid_mask": np.ones(8, dtype=bool),
        "candidate_reasons": [()] * 8,
    }
    result = select_camp_candidate(
        candidates=candidates,
        materialized=base,
        atom_scales=np.ones(14),
        weights=np.ones(14) / 14.0,
        eligibility_mask_name="source_valid_mask",
    )
    assert result["selected_index"] == 0

    for mutation, pattern in (
        (lambda row: row.pop("source_valid_mask"), "source_valid_mask"),
        (lambda row: row.update(source_valid_mask=np.ones(8, dtype=np.int8)), "strict booleans"),
        (lambda row: row.update(source_valid_mask=np.ones(7, dtype=bool)), "shape"),
        (
            lambda row: row.update(
                source_valid_mask=np.asarray([True] + [False] * 7),
                physical_feasible_mask=np.asarray([True, True] + [False] * 6),
            ),
            "subset",
        ),
    ):
        changed = copy.deepcopy(base)
        mutation(changed)
        with pytest.raises((KeyError, ValueError), match=pattern):
            select_camp_candidate(
                candidates=candidates,
                materialized=changed,
                atom_scales=np.ones(14),
                weights=np.ones(14) / 14.0,
                eligibility_mask_name="source_valid_mask",
            )


def test_generic_14d_requires_k8_explicit_source_mask_and_route_progress() -> None:
    selector = CAMPSelector(
        atom_scales=np.ones(14),
        static_weights=np.ones(14),
        mode="static",
        fallback_mode="top1",
    )
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101))),
        speed_limit=20.0,
    )
    candidates = _candidates().astype(np.float64)
    common = dict(
        candidate_planned_red_light_cost=np.zeros(8),
        candidate_red_stopping_margin_cost=np.zeros(8),
        candidate_dp_prior_jerk_excess_cost=np.zeros(8),
        external_feasible_mask=np.ones(8, dtype=bool),
        apply_context_feasibility=False,
    )
    with pytest.raises(ValueError, match="explicit candidate_source_valid_mask"):
        selector.select(candidates, context, candidate_progress=np.arange(8.0), **common)
    with pytest.raises(ValueError, match="explicit route-projected candidate_progress"):
        selector.select(
            candidates,
            context,
            candidate_source_valid_mask=np.ones(8, dtype=bool),
            **common,
        )
    with pytest.raises(ValueError, match="K=8"):
        selector.select(
            candidates[:7],
            context,
            candidate_progress=np.arange(7.0),
            candidate_source_valid_mask=np.ones(7, dtype=bool),
            candidate_planned_red_light_cost=np.zeros(7),
            candidate_red_stopping_margin_cost=np.zeros(7),
            candidate_dp_prior_jerk_excess_cost=np.zeros(7),
            external_feasible_mask=np.ones(7, dtype=bool),
            apply_context_feasibility=False,
        )
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
