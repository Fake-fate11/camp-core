from __future__ import annotations

import copy

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


def _rows(*, unresolved: bool = False) -> list[dict]:
    rows = []
    for cluster in range(50):
        for repeat in range(2):
            perturbation = 3.0 if unresolved and repeat else 0.01 * repeat
            rows.append(
                {
                    "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v1",
                    "arm": "candidate0_operational_default",
                    "cluster_id": f"corridor-{cluster:02d}",
                    "measurement_sha256": f"{cluster * 2 + repeat + 1000:064x}",
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


def test_unresolvable_preregistered_margin_blocks_fresh_without_enlargement() -> None:
    payload = _build(unresolved=True)
    assert payload["status"] == "calibration_freeze_scientifically_ineligible"
    assert payload["calibration_contract"]["fresh_preopen_qualification_allowed"] is False
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
