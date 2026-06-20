from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (
    LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS,
    LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_matched_lane_hard_violation_support_outcomes import (
    analyze,
)


def _outcome(value: float = 0.0) -> dict:
    return {
        "value": value,
        "feasible": True,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 0.1,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _lane_hard_payload(*, include_outcome_key: bool = False) -> dict:
    candidates = 2
    support_steps = 3
    payload = {
        "schema_version": LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": candidates,
        "horizons": {"support_steps": support_steps, "dt_s": 0.1},
        "field_shapes": {
            "candidate_route_lateral_error_profile_m": [candidates, support_steps],
            "candidate_route_corridor_half_width_profile_m": [
                candidates,
                support_steps,
            ],
            "candidate_route_heading_error_profile_rad": [candidates, support_steps],
            "candidate_lateral_error_rate_profile_mps": [
                candidates,
                support_steps - 1,
            ],
        },
        "finite_checks": {
            **{name: True for name in LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES},
            "lane_hard_violation_support_atoms": True,
            "lane_hard_violation_support_atoms_nonnegative": True,
        },
        "candidate_route_lateral_error_profile_m": [[0.0, 0.1, 0.2], [0.0, 0.2, 0.3]],
        "candidate_route_corridor_half_width_profile_m": [[1.75, 1.75, 1.75]] * candidates,
        "candidate_route_heading_error_profile_rad": [[0.0, 0.1, 0.2], [0.0, 0.2, 0.3]],
        "candidate_lateral_error_rate_profile_mps": [[1.0, 1.0], [2.0, 1.0]],
        "lane_hard_violation_support_atom_names": list(
            LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES
        ),
        "lane_hard_violation_support_atoms": [
            [0.0] * len(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES)
        ]
        * candidates,
        "latency_ms": {key: 0.1 for key in LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS},
    }
    if include_outcome_key:
        payload["candidate_closed_loop_outcomes"] = [_outcome(), _outcome()]
    return payload


def _record(*, seed: int = 1, include_outcome_key: bool = False) -> dict:
    latency = {key: 0.1 for key in LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS}
    return {
        "seed": seed,
        "lane_hard_violation_support_logging": _lane_hard_payload(
            include_outcome_key=include_outcome_key
        ),
        "candidate_closed_loop_outcomes": [_outcome(0.0), _outcome(1.0)],
        **latency,
    }


def _write_log(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_matched_lane_hard_outcome_contract_passes(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "camp_selection_log.json", [_record()])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_lane_hard_violation_support_outcome_contract_passed"
    )
    assert report["counts"]["lane_hard_support_records"] == 1
    assert report["counts"]["outcome_records"] == 1
    assert report["counts"]["candidate_rows"] == 2
    assert report["analysis"]["future_outcome_leakage"] is False


def test_matched_lane_hard_outcome_contract_rejects_payload_outcomes(
    tmp_path: Path,
) -> None:
    log_path = _write_log(
        tmp_path / "camp_selection_log.json",
        [_record(include_outcome_key=True)],
    )

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_lane_hard_violation_support_outcome_contract_rejected"
    )
    assert any(
        "payload contains candidate outcomes" in error
        for error in report["validation"]["errors"]
    )


def test_matched_lane_hard_outcome_contract_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    log_path = _write_log(
        tmp_path / "seed_11" / "camp_selection_log.json",
        [_record(seed=11)],
    )

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_lane_hard_violation_support_outcome_contract_rejected"
    )
    assert report["counts"]["formal_seed_records"] >= 1
