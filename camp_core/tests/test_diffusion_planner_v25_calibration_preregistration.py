from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (
    ROOT_ROLES,
    freeze_paired_calibration_preregistration,
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
    validate_calibration_fresh_zero_overlap,
)


def _payload() -> dict:
    roots = {
        role: {"path": f"/root/autodl-tmp/{role}", "root_sha256": "1" * 64}
        for role in ROOT_ROLES
    }
    overlap = validate_calibration_fresh_zero_overlap(
        build_signal_complete_execution_plan("calibration"),
        build_signal_complete_execution_plan("fresh_b2"),
    )
    models = {
        "model_registry_sha256": "2" * 64,
        "training_scale_sha256": "5" * 64,
        "context_scaler_sha256": "4" * 64,
        "atom_scales_file_sha256": "5" * 64,
        "static14d_weights_file_sha256": "6" * 64,
        "scene14d_theta_sha256": "7" * 64,
    }
    return freeze_paired_calibration_preregistration(
        root_artifacts=roots,
        zero_overlap_receipt=overlap,
        model_authority=models,
    )


def test_paired_calibration_preregistration_freezes_fresh_closed_contract() -> None:
    payload = _payload()
    assert validate_paired_calibration_preregistration(payload) == payload
    assert payload["primary_arms"] == [
        "candidate0_operational_default",
        "camp_static14d",
        "camp_scene14d_no_v2i",
    ]
    assert payload["paper_subset_ablations"] == [
        "camp_static9d",
        "camp_scene9d_no_v2i",
    ]
    assert payload["pair_count"] == 100
    assert payload["arm_run_count"] == 300
    assert payload["primary"]["operational_overspeed_tolerance_mps"] == 0.1
    assert payload["primary"]["speed_margin_atoms_mps"] == [0.0, 0.5, 1.0]
    assert payload["scene_context"]["phase_remaining_available"] is False
    assert payload["fresh_b2_opened"] is False
    assert payload["fresh_open_authorized"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("primary", "operational_overspeed_tolerance_mps"), 0.5),
        (("noninferiority", "margins", "progress"), 2.0),
        (("scene_context", "phase_remaining_available"), True),
        (("coverage", "planned_pair_denominator"), 99),
        (("fresh_b2_opened",), True),
        (("paper_subset_ablations",), ["camp_static9d"]),
    ],
)
def test_paired_calibration_preregistration_mutations_fail_closed(
    path: tuple[object, ...], value: object
) -> None:
    mutated = copy.deepcopy(_payload())
    target: object = mutated
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError, match="differs from freeze"):
        validate_paired_calibration_preregistration(mutated)
