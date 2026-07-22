from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration import (
    CALIBRATION_ROOT_BINDINGS,
    estimate_v25_noninferiority_margin_resolvability,
    freeze_v25_calibration_contract,
)
from camp_core.integrations.diffusion_planner_v25_fresh_b2 import (
    FROZEN_ROOT_BINDINGS,
    qualify_fresh_b2_preopen,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_preopen import (
    build_signal_complete_preopen_input_receipt,
    freeze_signal_complete_preopen_artifact,
    validate_signal_complete_preopen_artifact,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)
from camp_core.integrations.diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
)


def _materialize(tmp_path: Path, split: str) -> tuple[Path, dict]:
    suite = build_signal_complete_suite(split)
    for relative, payload in suite["map_payloads"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return tmp_path, validate_signal_complete_suite(suite)


def _runtime(plan: dict, map_root: Path) -> list[dict]:
    runtime = []
    for identity in plan["identities"]:
        prepared = build_signal_complete_runtime_case(
            identity, map_artifact=map_root, seeds=plan["seeds"]
        )
        runtime.append(prepared)
    return runtime


def _train_row() -> dict:
    return {
        "split": "train",
        "source_family": "sealed_corrected_controlled_train",
        "map_geometry_sha256": "1" * 64,
        "intersection_sha256": "2" * 64,
        "corridor_sha256": "3" * 64,
        "route_family_sha256": "4" * 64,
        "semantic_parameter_block_sha256": "5" * 64,
        "seed_namespace": "train-25001",
        "route_identity_sha256": "6" * 64,
        "scenario_family": "lead_vehicle_hard_brake",
    }


def _eligible_calibration_contract() -> dict:
    performance = {name: 0.0 for name in NONINFERIORITY_METRICS}
    rows = [
        {
            "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v1",
            "arm": "candidate0_operational_default",
            "cluster_id": f"calibration-corridor-{index % 50:02d}",
            "measurement_sha256": f"{index + 1:064x}",
            "performance": dict(performance),
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        }
        for index in range(100)
    ]
    return freeze_v25_calibration_contract(
        root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
        inventory={
            "map_count": 5,
            "intersection_count": 5,
            "corridor_count": 50,
            "route_count": 50,
            "planned_paired_run_count": 100,
            "paired_eligible_run_count": 100,
            "retained_failure_run_count": 0,
            "paired_eligible_rate": 1.0,
        },
        noninferiority_resolvability=(
            estimate_v25_noninferiority_margin_resolvability(rows)
        ),
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )


def _power_pilot_receipt() -> dict:
    return {
        "schema_version": "camp_dp_v25_power_pilot_variance_receipt_v1",
        "status": "sealed_train_or_calibration_pilot_variance",
        "source_artifact_root_sha256": "f" * 64,
        "source_split": "calibration_pilot",
        "calibration_arm": "candidate0_operational_default",
        "cluster_estimator": "equal_mass_independent_cluster_standard_deviation",
        "variance_target": "candidate0_safety_cost_proxy_disclosed_not_paired_delta",
        "safety_cost_cluster_standard_deviation": 0.2,
        "red_component_cluster_standard_deviation": 0.1,
        "total_independent_cluster_count": 50,
        "red_independent_cluster_count": 5,
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def test_preopen_inputs_have_zero_overlap_license_and_two_strata(tmp_path: Path) -> None:
    fresh_root, fresh_suite = _materialize(tmp_path, "fresh_b2")
    calibration = build_signal_complete_execution_plan("calibration")
    fresh = build_signal_complete_execution_plan("fresh_b2")
    runtime = _runtime(fresh, fresh_root)
    receipt = build_signal_complete_preopen_input_receipt(
        train_split_rows=[_train_row()],
        calibration_plan=calibration,
        fresh_plan=fresh,
        suite_receipt=fresh_suite,
        map_artifact=fresh_root,
        license_sha256=hashlib.sha256(b"MIT license").hexdigest(),
        runtime_source_receipts=runtime,
    )
    assert receipt["status"] == "outcome_blind_preopen_inputs_materialized"
    assert receipt["zero_overlap_receipt"]["status"] == "passed"
    assert len(receipt["map_license_rows"]) == 25
    assert len(receipt["fresh_rows"]) == 100
    assert {row["benchmark_stratum"] for row in receipt["fresh_rows"]} == {
        "naturalistic",
        "controlled_stress",
    }
    assert receipt["fresh_b2_opened"] is False

    qualified = qualify_fresh_b2_preopen(
        split_rows=receipt["split_rows"],
        map_license_rows=receipt["map_license_rows"],
        fresh_rows=receipt["fresh_rows"],
        frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
        calibration_contract=_eligible_calibration_contract(),
        calibration_contract_root_sha256="f" * 64,
        power_pilot_receipt=_power_pilot_receipt(),
    )
    assert qualified["status"] == "qualified"
    assert qualified["fresh_row_count"] == 100
    assert qualified["independent_unit_counts"]["corridors"] == 100
    assert qualified["independent_unit_counts"]["route_identities"] == 100
    assert qualified["fresh_open_authorized"] is False
    assert qualified["fresh_b2_opened"] is False

    artifact = freeze_signal_complete_preopen_artifact(
        preopen_input_receipt=receipt,
        frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
        calibration_contract=_eligible_calibration_contract(),
        calibration_contract_root_sha256="f" * 64,
        power_pilot_receipt=_power_pilot_receipt(),
    )
    reopened = validate_signal_complete_preopen_artifact(
        artifact,
        preopen_input_receipt=receipt,
        calibration_contract=_eligible_calibration_contract(),
        power_pilot_receipt=_power_pilot_receipt(),
    )
    assert reopened["qualification"] == qualified
    assert len(reopened["qualification_rows"]) == 100
    assert reopened["fresh_b2_opened"] is False

    mutated = copy.deepcopy(artifact)
    mutated["qualification_rows"][0]["route_length_m"] += 1.0
    with pytest.raises(ValueError, match="authority drifted"):
        validate_signal_complete_preopen_artifact(
            mutated,
            preopen_input_receipt=receipt,
            calibration_contract=_eligible_calibration_contract(),
            power_pilot_receipt=_power_pilot_receipt(),
        )


def test_preopen_never_accepts_runtime_k8_receipts_or_dp_forward(tmp_path: Path) -> None:
    fresh_root, fresh_suite = _materialize(tmp_path, "fresh_b2")
    calibration = build_signal_complete_execution_plan("calibration")
    fresh = build_signal_complete_execution_plan("fresh_b2")
    runtime = _runtime(fresh, fresh_root)
    runtime[0]["candidate_generation_executed"] = True
    with pytest.raises(ValueError, match="static source"):
        build_signal_complete_preopen_input_receipt(
            train_split_rows=[_train_row()],
            calibration_plan=calibration,
            fresh_plan=fresh,
            suite_receipt=fresh_suite,
            map_artifact=fresh_root,
            license_sha256="a" * 64,
            runtime_source_receipts=runtime,
        )
