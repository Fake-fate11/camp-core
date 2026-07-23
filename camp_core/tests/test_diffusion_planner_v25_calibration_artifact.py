from __future__ import annotations

import copy
import hashlib
import json

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (
    build_calibration_freeze_payload,
    validate_calibration_freeze_payload,
)


ROOT_BINDINGS = {
    "atom_audit_root": "1" * 64,
    "atom_audit_review_root": "2" * 64,
    "training_root": "3" * 64,
    "training_review_root": "4" * 64,
    "calibration_corpus_root": "5" * 64,
    "calibration_review_root": "6" * 64,
    "zero_overlap_root": "7" * 64,
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
        ).encode()
    ).hexdigest()


def _rows(*, unresolved: bool = False) -> list[dict]:
    rows = []
    for cluster in range(50):
        for repeat in range(2):
            perturbation = 3.0 if unresolved and repeat else 0.01 * repeat
            index = cluster * 2 + repeat
            identity = {
                "schema_version": "camp_dp_v25_exact_candidate0_repeatability_identity_v1",
                "route_identity_sha256": f"{index + 1000:064x}",
                "scenario_identity_sha256": f"{index + 2000:064x}",
                "semantic_parameter_block_sha256": f"{index + 3000:064x}",
                "scenario_seed": 25001 + index,
                "spawn_config_sha256": f"{index + 4000:064x}",
                "initial_state_sha256": f"{index + 5000:064x}",
                "initial_input_sha256": f"{index + 6000:064x}",
                "same_initial_state_and_exogenous_schedule_per_pair": True,
            }
            rows.append(
                {
                    "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v2",
                    "arm": "candidate0_operational_default",
                    "heterogeneity_cluster_id": f"map-{cluster % 5:02d}",
                    "run_instance_sha256": f"{index + 7000:064x}",
                    "repeatability_identity": identity,
                    "repeatability_identity_sha256": _canonical_sha(identity),
                    "measurement_sha256": f"{index + 8000:064x}",
                    "performance": {
                        "progress": 80.0 + perturbation,
                        "completion": 0.8 + 0.001 * repeat,
                        "mean_jerk": 0.5 + 0.01 * repeat,
                        "max_jerk": 2.0 + 0.02 * repeat,
                        "mean_lateral_acceleration": 0.3 + 0.01 * repeat,
                        "max_lateral_acceleration": 1.0 + 0.02 * repeat,
                        "maximum_deceleration": 2.0 + 0.02 * repeat,
                    },
                    "fresh_b2_opened": False,
                    "fresh_outcome_fields_consumed": [],
                }
            )
    return rows


def _inventory() -> dict:
    return {
        "map_count": 5,
        "intersection_count": 50,
        "corridor_count": 50,
        "route_count": 50,
        "planned_paired_run_count": 100,
        "paired_eligible_run_count": 100,
        "retained_failure_run_count": 0,
        "paired_eligible_rate": 1.0,
    }


def _build(*, unresolved: bool = False) -> dict:
    return build_calibration_freeze_payload(
        root_bindings=ROOT_BINDINGS,
        inventory=_inventory(),
        candidate0_rows=_rows(unresolved=unresolved),
        frozen_model_registry_sha256="8" * 64,
        training_scale_sha256="9" * 64,
        context_scaler_sha256="a" * 64,
    )


def test_calibration_freeze_passes_without_tuning_from_method_or_fresh() -> None:
    payload = _build()
    assert payload["status"] == "calibration_freeze_passed"
    assert payload["candidate0_row_count"] == 100
    assert payload["calibration_contract"]["operational_overspeed_tolerance_mps"] == 0.1
    assert payload["calibration_contract"]["inventory"]["corridor_count"] == 50
    assert payload["camp_method_outcomes_consumed"] is False
    assert payload["margin_enlargement_authorized"] is False
    assert payload["fresh_b2_opened"] is False
    assert validate_calibration_freeze_payload(payload) == payload


def test_cross_scenario_heterogeneity_does_not_block_fresh_or_enlarge_margin() -> None:
    payload = _build(unresolved=True)
    assert payload["status"] == "calibration_freeze_passed"
    assert payload["calibration_contract"]["fresh_preopen_qualification_allowed"] is True
    assert payload["noninferiority_resolvability"][
        "q95_within_map_cross_scenario_heterogeneity"
    ]["progress"] > 1.0
    assert payload["noninferiority_resolvability"]["repeatability_status"] == (
        "not_estimable_no_exact_candidate0_duplicates"
    )
    assert payload["calibration_contract"]["noninferiority"]["margins"]["progress"] == 1.0
    assert payload["margin_enlargement_authorized"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("fresh_b2_opened",), True),
        (("candidate0_row_count",), 99),
        (("candidate0_rows", 0, "arm"), "camp_static14d"),
        (("calibration_contract", "operational_overspeed_tolerance_mps"), 0.2),
    ),
)
def test_calibration_freeze_mutations_fail_closed(path: tuple, value: object) -> None:
    payload = copy.deepcopy(_build())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        validate_calibration_freeze_payload(payload)
