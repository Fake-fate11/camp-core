from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_contract import (
    BRANCHES,
    HEADER_FIELDS_BY_BRANCH,
    LATENCY_FIELDS_BY_BRANCH,
    TICK_FIELDS_BY_BRANCH,
    actual_native_receipt_contract,
    actual_native_receipt_contract_sha256,
    validate_actual_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_review import (
    independent_candidate0_pool_evidence,
    independent_project_candidate0_supplementary,
    independent_validate_actual_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_fresh_receipt import (
    _build_supplementary_candidate0_pool,
    _native_receipt,
    project_candidate0_supplementary_native_receipt,
)


SHA = "a" * 64
GIT_SHA = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _header(branch: str, ticks: list[dict]) -> dict:
    native_root = (Path.cwd() / "nonfresh_native_fixture").resolve()
    value = {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "route_name": "nonfresh-receipt-abi-fixture",
        "route_sha256": "1" * 64,
        "logical_map_sha256": "2" * 64,
        "fixed_dp_head": GIT_SHA,
        "checkpoint_sha256": "3" * 64,
        "args_sha256": "4" * 64,
        "arm": "dp" if branch.startswith("candidate0_") else "camp",
        "scenario_seed": 25001,
        "spawn_config_sha256": "5" * 64,
        "initial_state_sha256": "6" * 64,
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "native_result": {
            "final_step": 63,
            "goal_reached": False,
            "reason": "max_steps",
            "n_npc_spawned": 0,
            "trajectory_log_path": str(native_root / "trajectory_log.json"),
            "clearance_log_path": str(native_root / "clearance_log.json"),
        },
        "safety": {},
        "secondary": {},
        "latency": {},
        "signal_safety": {},
        "runtime_annotation_compatibility": "not_required_python310_or_newer",
        "claim_authorized": False,
        "actual_native_receipt_contract_sha256": (
            actual_native_receipt_contract_sha256()
        ),
    }
    if branch in {"static14d", "scene14d"}:
        value["selector_scale_contract"] = {}
    assert set(value) == HEADER_FIELDS_BY_BRANCH[branch]
    return value


def _common_tick(index: int, branch: str) -> dict:
    row0 = f"{10_000 + index * 8:064x}"
    value = {
        "tick_index": index,
        "status": "ok",
        "input_sha256": f"{1_000 + index:064x}",
        "padding": {
            "observed_frames": 4,
            "padded_frames": 0,
            "padding_policy": "repeat_first",
        },
        "tracker": {"status": "ok"},
        "safety": {
            "tick_index": index,
            "position_xy": [float(index), 0.0],
            "speed_mps": 8.0,
            "ego_heading_rad": 0.0,
            "route_heading_rad": 0.0,
            "route_progress_m": float(index),
            "five_point_drivable_coverage": True,
            "min_obb_clearance_m": 10.0,
            "red_light_at_interval_start": False,
            "front_center_prev_xy": [float(index), 0.0],
            "front_center_xy": [float(index) + 0.8, 0.0],
            "red_stop_lines": [],
            "speed_limit_mps": 12.0,
            "constant_velocity_circle_ttc_diagnostic_s": None,
            "source_complete": True,
        },
        "latency_ms": {
            name: 0.25 for name in LATENCY_FIELDS_BY_BRANCH[branch]
        },
        "pre_decision_speed_mps": 8.0,
        "default_output_sha256": row0,
        "planning_started_ns": 1_000 + index * 100,
        "action_available_ns": 1_010 + index * 100,
        "receipt_projected_ns": 1_020 + index * 100,
    }
    return value


def _primary_tick(index: int) -> dict:
    value = _common_tick(index, "candidate0_primary")
    value.update(
        {
            "candidate0_action_first": True,
            "selected_index": 0,
            "selected_trajectory_sha256": value[
                "default_output_sha256"
            ],
            "selection_policy": "candidate0_operational_default",
            "score_contract": "candidate0_operational_default",
            "eligibility_mask_name": "candidate0_operational_default",
            "candidate0_operational_default": True,
            "candidate0_pool_evidence_collected_online": False,
            "candidate0_pool_evidence_required_post_action": True,
            "same_forward_claimed": False,
        }
    )
    assert set(value) == TICK_FIELDS_BY_BRANCH["candidate0_primary"]
    return value


def _supplementary_tick(index: int) -> dict:
    value = _common_tick(index, "candidate0_supplementary")
    value["planning_started_ns"] = 2_000 + index * 100
    value["action_available_ns"] = 2_010 + index * 100
    value["receipt_projected_ns"] = 2_020 + index * 100
    rows = [f"{10_000 + index * 8 + row:064x}" for row in range(8)]
    value.update(
        {
            "candidate_tensor_sha256_before": SHA,
            "candidate_tensor_sha256_after": SHA,
            "candidate_neighbor_sha256": "c" * 64,
            "selected_trajectory_sha256": rows[0],
            "global_rng_sha256_before": "d" * 64,
            "global_rng_sha256_after": "d" * 64,
            "candidate_row_sha256": rows,
            "selection_policy": "candidate0_operational_default",
            "score_contract": "candidate0_operational_default",
            "eligibility_mask_name": "candidate0_operational_default",
            "selected_index": 0,
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": rows[0],
                "candidate0_sha256": rows[0],
                "native_ranked_k8": False,
            },
            "causal_evidence_sha256": "e" * 64,
            "route_lanes_sha256": "f" * 64,
            "route_lanes_speed_limit_sha256": "1" * 64,
            "route_lanes_has_speed_limit_sha256": "2" * 64,
            "atom_matrix_sha256": "3" * 64,
            "candidate0_operational_default": True,
            "post_divergence_cross_arm_tensor_identity_required": True,
            "npc_operational_outputs_unchanged": True,
            "physical_feasible_mask": [True] + [False] * 7,
            "source_valid_mask": [True] * 8,
            "source_complete_mask": [True] * 8,
            "candidate_reasons": [[] for _ in range(8)],
            "all_k_high_risk": False,
            "controlled_scene": _controlled_scene(index),
        }
    )
    assert set(value) == TICK_FIELDS_BY_BRANCH["candidate0_supplementary"]
    return value


def _controlled_scene(index: int) -> dict:
    scenario = "nonfresh-receipt-abi-fixture"
    return {
        "scenario_id": scenario,
        "tick_index": index,
        "sim_time_s": float(index) * 0.1,
        "actor_count": 0,
        "actors": [],
        "signal": {
            "phase": "none",
            "source_row_count": 0,
            "applied": False,
            "source_receipt": {
                "schema_version": (
                    "camp_dp_v25_current_signal_runtime_receipt_v2"
                ),
                "scenario_id": scenario,
                "tick_index": index,
                "decision_time_s": float(index) * 0.1,
                "source_mode": "same_tick_no_signal_rule_no_v2i",
                "current_phase": "none",
                "route_geometry_sha256": "7" * 64,
                "route_lanelet_ids": [1],
                "traffic_light_regulatory_element_ids": [],
                "source_chain_sha256": "8" * 64,
                "semantic_clone_sha256": "9" * 64,
                "phase_remaining_available": False,
                "source_valid": True,
                "applicable": False,
            },
        },
        "outcome_fields_consumed": [],
        "candidate_tensor_consumed": False,
        "selected_trajectory_consumed": False,
        "model_input_cache": {
            "schema_version": (
                "camp_dp_v25_model_input_signal_cache_receipt_v1"
            ),
            "scenario_id": scenario,
            "tick_index": index,
            "signal_source_class": "no_signal",
            "phase_authority_mode": None,
            "scene_map_tl_sha256": "a" * 64,
            "model_cache_tl_sha256_before": "a" * 64,
            "model_cache_tl_sha256_after": "a" * 64,
            "model_route_lanes_tl_sha256": "b" * 64,
            "cache_matches_scene_after": True,
            "observe_cache_unchanged": True,
            "sync_applied_before_tensor_conversion": True,
            "future_schedule_consumed": False,
            "phase_remaining_available": False,
        },
    }


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _mapped_controlled_scene(
    index: int,
    *,
    route_rows: list[dict],
    map_rows: list[dict],
) -> dict:
    value = _controlled_scene(index)
    scenario = value["scenario_id"]
    route_ids = [row["lanelet_id"] for row in route_rows]
    map_ids = [row["lanelet_id"] for row in map_rows]
    route_sha = _canonical_sha(route_rows)
    map_sha = _canonical_sha(map_rows)
    value["signal"] = {
        "phase": "yellow",
        "source_row_count": len(route_rows) + len(map_rows),
        "applied": True,
        "source_receipt": {
            "schema_version": (
                "camp_dp_v25_family_independent_current_signal_receipt_v1"
            ),
            "scenario_id": scenario,
            "tick_index": index,
            "phase_authority_mode": "controlled_same_tick_override",
            "current_phase": "yellow",
            "decision_timestamp_s": float(index) * 0.1,
            "source_timestamp_s": float(index) * 0.1,
            "source_age_s": 0.0,
            "freshness": "same_tick",
            "source_id": "fixed_dp_current_request_route_map_signal_one_hot",
            "regulatory_element_id": 101,
            "physical_light_ids": [102],
            "bulb_ids": [103],
            "controlled_lanelet_ids": sorted(set(route_ids + map_ids)),
            "stop_line_id": 104,
            "stop_line_geometry_sha256": "1" * 64,
            "route_geometry_sha256": "2" * 64,
            "route_arc_m": 1.0,
            "source_chain_sha256": "3" * 64,
            "observed_route_lanelet_ids": route_ids,
            "observed_map_lanelet_ids": map_ids,
            "route_signal_tensor_sha256": route_sha,
            "map_signal_tensor_sha256": map_sha,
            "phase_remaining_available": False,
            "source_valid": True,
            "applicable": False,
        },
        "tensor_evidence": {
            "schema_version": (
                "camp_dp_v25_production_signal_tensor_evidence_v2"
            ),
            "tick_index": index,
            "decision_timestamp_s": float(index) * 0.1,
            "source_timestamp_s": float(index) * 0.1,
            "route_signal_rows": route_rows,
            "map_signal_rows": map_rows,
            "current_phase": "yellow",
            "route_signal_tensor_sha256": route_sha,
            "map_signal_tensor_sha256": map_sha,
            "future_schedule_consumed": False,
            "phase_remaining_available": False,
        },
    }
    value["model_input_cache"].update(
        {
            "signal_source_class": "mapped_signal",
            "phase_authority_mode": "controlled_same_tick_override",
            "observe_cache_unchanged": False,
        }
    )
    return value


def _candidate0_receipts() -> tuple[dict, dict]:
    primary_ticks = [_primary_tick(index) for index in range(64)]
    supplementary_ticks = [
        _supplementary_tick(index) for index in range(64)
    ]
    for primary, supplementary in zip(
        primary_ticks, supplementary_ticks, strict=True
    ):
        supplementary["input_sha256"] = primary["input_sha256"]
        supplementary["default_output_sha256"] = primary[
            "default_output_sha256"
        ]
        supplementary["selected_trajectory_sha256"] = primary[
            "selected_trajectory_sha256"
        ]
    primary = _header("candidate0_primary", primary_ticks)
    supplementary = _header(
        "candidate0_supplementary", supplementary_ticks
    )
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        supplementary[name] = primary[name]
    return primary, supplementary


def _method_tick(index: int, branch: str) -> dict:
    value = _supplementary_tick(index)
    value.pop("candidate0_operational_default")
    value.pop("post_divergence_cross_arm_tensor_identity_required")
    value["latency_ms"] = {
        name: 0.25 for name in LATENCY_FIELDS_BY_BRANCH[branch]
    }
    value.update(
        {
            "normalized_atom_matrix_sha256": "4" * 64,
            "scores": [float(item) for item in range(8)],
            "tie_break_contract": "lowest_eligible_candidate_index",
            "selection_policy": "v22_source_valid",
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "eligibility_mask_name": "source_valid_mask",
        }
    )
    if branch == "scene14d":
        names = actual_native_receipt_contract()["nested_schemas"][
            "v25_context"
        ]["context_feature_names"]
        value["v25_context"] = {
            "schema_version": "camp_dp_v25_causal_context_raw_v2",
            "raw_context": {name: 0.0 for name in names},
            "source_complete": {name: True for name in names},
            "source_receipt": {
                "mode": "no_v2i",
                "phase_remaining_available": False,
                "regulatory_signal_mapped": False,
            },
        }
        value["v25_scene_selector"] = {
            "context_scaler_sha256": "5" * 64,
            "fixed_dp_head": GIT_SHA,
            "model_name": "CAMP-Scene14D",
            "phi_sha256": "6" * 64,
            "runtime_projection": False,
            "schema_version": "camp_dp_v25_scene_weight_receipt_v3",
            "softmax": False,
            "theta_sha256": "7" * 64,
            "training_review_root_sha256": "8" * 64,
            "training_root_sha256": "9" * 64,
            "weights_sha256": "a" * 64,
        }
    assert set(value) == TICK_FIELDS_BY_BRANCH[branch]
    return value


def test_contract_freezes_all_four_actual_native_branches() -> None:
    contract = actual_native_receipt_contract()
    assert tuple(contract["branches"]) == BRANCHES
    assert (
        contract["reviewer_imports_production_validator_or_projector"] is False
    )
    assert contract["contract_sha256"] == actual_native_receipt_contract_sha256()
    for branch in BRANCHES:
        row = contract["branches"][branch]
        assert set(row["tick_native_types"]) == TICK_FIELDS_BY_BRANCH[branch]
        assert set(row["latency_fields"]) == LATENCY_FIELDS_BY_BRANCH[branch]


def test_real_candidate0_primary_and_supplementary_contract_round_trip() -> None:
    primary, raw_supplementary = _candidate0_receipts()
    validate_actual_native_receipt(
        primary, branch="candidate0_primary"
    )
    validate_actual_native_receipt(
        raw_supplementary, branch="candidate0_supplementary"
    )
    independent_validate_actual_native_receipt(
        primary, branch="candidate0_primary"
    )
    independent_validate_actual_native_receipt(
        raw_supplementary, branch="candidate0_supplementary"
    )
    projected = project_candidate0_supplementary_native_receipt(
        raw_supplementary
    )
    assert (
        independent_project_candidate0_supplementary(raw_supplementary)
        == projected
    )
    producer = _build_supplementary_candidate0_pool(primary, projected)
    independent = independent_candidate0_pool_evidence(primary, projected)
    assert independent == producer


def test_mapped_signal_rows_allow_one_empty_tensor_but_bind_authority() -> None:
    _, supplementary = _candidate0_receipts()
    yellow = [0.0, 1.0, 0.0, 0.0, 0.0]
    map_rows = [
        {
            "lanelet_id": 11,
            "signal_channels_8_12": [yellow] + [[0.0] * 5] * 19,
        }
    ]
    supplementary["ticks"][0]["controlled_scene"] = (
        _mapped_controlled_scene(0, route_rows=[], map_rows=map_rows)
    )
    assert (
        validate_actual_native_receipt(
            supplementary, branch="candidate0_supplementary"
        )
        == supplementary
    )
    assert (
        independent_validate_actual_native_receipt(
            supplementary, branch="candidate0_supplementary"
        )
        == supplementary
    )

    for mutation in ("both_empty", "id", "payload"):
        changed = copy.deepcopy(supplementary)
        signal = changed["ticks"][0]["controlled_scene"]["signal"]
        if mutation == "both_empty":
            signal["tensor_evidence"]["map_signal_rows"] = []
            signal["source_receipt"]["observed_map_lanelet_ids"] = []
            signal["source_row_count"] = 0
            empty_sha = _canonical_sha([])
            signal["tensor_evidence"]["map_signal_tensor_sha256"] = empty_sha
            signal["source_receipt"]["map_signal_tensor_sha256"] = empty_sha
        elif mutation == "id":
            signal["source_receipt"]["observed_map_lanelet_ids"] = [12]
        else:
            signal["tensor_evidence"]["map_signal_rows"][0][
                "signal_channels_8_12"
            ][0] = [0.0, 0.0, 1.0, 0.0, 0.0]
        with pytest.raises(ValueError):
            validate_actual_native_receipt(
                changed, branch="candidate0_supplementary"
            )
        with pytest.raises(ValueError):
            independent_validate_actual_native_receipt(
                changed, branch="candidate0_supplementary"
            )


def test_actual_native_sink_precedes_production_validation_and_projection() -> None:
    native_source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_dp_camp_v21_native.py"
    ).read_text(encoding="utf-8")
    receipt_boundary = native_source.index(
        "actual_native_receipt_sink(copy.deepcopy(receipt))"
    )
    validation = native_source.index(
        "validate_actual_native_receipt(",
        receipt_boundary,
    )
    assert receipt_boundary < validation

    execution_source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_v25_holdout_execution.py"
    ).read_text(encoding="utf-8")
    sink = execution_source.index(
        '"candidate0_supplementary_actual_native_raw.json"'
    )
    projection = execution_source.index(
        "project_candidate0_supplementary_native_receipt(diagnostic)"
    )
    assert sink < projection


def test_execution_enrichment_is_separate_from_actual_native_abi() -> None:
    primary, _ = _candidate0_receipts()
    enriched = copy.deepcopy(primary)
    enriched["fresh_decision_evidence_reference"] = {
        "schema_version": "camp_dp_v25_fresh_logical_file_reference_v1"
    }
    enriched["fresh_decision_evidence_count"] = 0
    projected = _native_receipt(enriched, "candidate0")
    assert set(projected) == set(primary)
    assert projected == primary

    missing = copy.deepcopy(enriched)
    missing.pop("fresh_decision_evidence_count")
    with pytest.raises(ValueError, match="enrichment field set"):
        _native_receipt(missing, "candidate0")

    wrong_type = copy.deepcopy(enriched)
    wrong_type["fresh_decision_evidence_count"] = False
    with pytest.raises(ValueError, match="enrichment type"):
        _native_receipt(wrong_type, "candidate0")


def test_post_divergence_identity_flag_is_supplementary_only() -> None:
    assert (
        "post_divergence_cross_arm_tensor_identity_required"
        in TICK_FIELDS_BY_BRANCH["candidate0_supplementary"]
    )
    assert (
        "post_divergence_cross_arm_tensor_identity_required"
        not in TICK_FIELDS_BY_BRANCH["static14d"]
    )
    assert (
        "post_divergence_cross_arm_tensor_identity_required"
        not in TICK_FIELDS_BY_BRANCH["scene14d"]
    )


@pytest.mark.parametrize("branch", ["static14d", "scene14d"])
def test_method_actual_native_contract_round_trip(branch: str) -> None:
    value = _header(
        branch,
        [_method_tick(index, branch) for index in range(64)],
    )
    assert validate_actual_native_receipt(value, branch=branch) == value
    assert (
        independent_validate_actual_native_receipt(value, branch=branch)
        == value
    )


@pytest.mark.parametrize("branch", ["static14d", "scene14d"])
@pytest.mark.parametrize(
    "field,stale_value",
    [
        ("score_contract", "score_k(w)=a_k^T w"),
        ("tie_break_contract", "lowest_index"),
    ],
)
def test_method_actual_native_contract_rejects_stale_shorthand(
    branch: str, field: str, stale_value: str
) -> None:
    value = _header(
        branch,
        [_method_tick(index, branch) for index in range(64)],
    )
    value["ticks"][0][field] = stale_value
    with pytest.raises(ValueError):
        validate_actual_native_receipt(value, branch=branch)
    with pytest.raises(ValueError):
        independent_validate_actual_native_receipt(value, branch=branch)


@pytest.mark.parametrize(
    "branch,mutation",
    [
        ("candidate0_primary", "missing"),
        ("candidate0_primary", "extra"),
        ("candidate0_primary", "bool_int"),
        ("candidate0_supplementary", "shape"),
        ("candidate0_supplementary", "cross_branch"),
    ],
)
def test_actual_native_abi_mutations_fail_closed(
    branch: str, mutation: str
) -> None:
    primary, supplementary = _candidate0_receipts()
    value = copy.deepcopy(
        primary if branch == "candidate0_primary" else supplementary
    )
    if mutation == "missing":
        value["ticks"][0].pop("input_sha256")
    elif mutation == "extra":
        value["ticks"][0]["futureOutcome"] = True
    elif mutation == "bool_int":
        value["ticks"][0]["planning_started_ns"] = False
    elif mutation == "shape":
        value["ticks"][0]["source_valid_mask"] = [True] * 7
    elif mutation == "cross_branch":
        value["ticks"][0]["candidate0_action_first"] = True
    with pytest.raises((TypeError, ValueError)):
        validate_actual_native_receipt(value, branch=branch)


def test_production_consumer_field_access_is_covered_by_abi() -> None:
    public_tick_fields = set().union(*TICK_FIELDS_BY_BRANCH.values())
    projected_only = {
        "supplementary_only",
        "same_forward_claimed",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate_row_sha256",
        "default_output_sha256",
        "selected_trajectory_sha256",
        "default_candidate0_identity",
        "selected_index",
        "source_valid_mask",
        "physical_feasible_mask",
        "source_complete_mask",
        "atom_matrix_sha256",
        "latency_ms",
        "planning_started_ns",
        "action_available_ns",
        "receipt_projected_ns",
        "input_sha256",
        "tick_index",
    }
    accessed = set()
    for function in (_native_receipt, _build_supplementary_candidate0_pool):
        tree = ast.parse(inspect.getsource(function))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                accessed.add(node.args[0].value)
    header_fields = set().union(*HEADER_FIELDS_BY_BRANCH.values())
    allowed = public_tick_fields | projected_only | header_fields
    assert accessed - allowed == set()


def test_every_declared_branch_field_is_required_and_typed() -> None:
    candidate0_primary, candidate0_supplementary = _candidate0_receipts()
    fixtures = {
        "candidate0_primary": candidate0_primary,
        "candidate0_supplementary": candidate0_supplementary,
        "static14d": _header(
            "static14d",
            [_method_tick(index, "static14d") for index in range(64)],
        ),
        "scene14d": _header(
            "scene14d",
            [_method_tick(index, "scene14d") for index in range(64)],
        ),
    }
    for branch, receipt in fixtures.items():
        for field in HEADER_FIELDS_BY_BRANCH[branch]:
            missing = copy.deepcopy(receipt)
            del missing[field]
            with pytest.raises(ValueError):
                validate_actual_native_receipt(missing, branch=branch)
            with pytest.raises(ValueError):
                independent_validate_actual_native_receipt(
                    missing, branch=branch
                )
        for field in TICK_FIELDS_BY_BRANCH[branch]:
            missing = copy.deepcopy(receipt)
            del missing["ticks"][0][field]
            with pytest.raises(ValueError):
                validate_actual_native_receipt(missing, branch=branch)
            with pytest.raises(ValueError):
                independent_validate_actual_native_receipt(
                    missing, branch=branch
                )
            wrong_type = copy.deepcopy(receipt)
            wrong_type["ticks"][0][field] = None
            with pytest.raises(ValueError):
                validate_actual_native_receipt(wrong_type, branch=branch)
            with pytest.raises(ValueError):
                independent_validate_actual_native_receipt(
                    wrong_type, branch=branch
                )
