from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_matched_progress_lane_hard_context_outcomes import (
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


def _context_payload(*, include_outcome_key: bool = False) -> dict:
    candidates = 2
    support_steps = 4
    payload = {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": candidates,
        "horizons": {"support_steps": support_steps, "dt_s": 0.1},
        "field_shapes": {
            "route_curvature_context_abs_radpm": [support_steps - 1],
            "candidate_lateral_error_rate_profile_mps": [
                candidates,
                support_steps - 1,
            ],
            "candidate_speed_profile_mps": [candidates, support_steps - 1],
            "candidate_route_progress_delta_profile_m": [
                candidates,
                support_steps - 1,
            ],
            "candidate_route_corridor_margin_profile_m": [candidates, support_steps],
            "candidate_route_heading_error_profile_rad": [candidates, support_steps],
        },
        "finite_checks": {
            **{name: True for name in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES},
            "progress_lane_hard_context_atoms": True,
            "progress_lane_hard_context_atoms_nonnegative": True,
        },
        "route_curvature_context_abs_radpm": [0.0, 0.1, 0.2],
        "candidate_lateral_error_rate_profile_mps": [
            [0.0, 0.1, 0.2],
            [0.2, 0.3, 0.4],
        ],
        "candidate_speed_profile_mps": [[5.0, 5.0, 5.0], [4.0, 4.0, 4.0]],
        "candidate_route_progress_delta_profile_m": [
            [0.5, 0.5, 0.5],
            [0.4, 0.4, 0.4],
        ],
        "candidate_route_corridor_margin_profile_m": [
            [1.0, 1.0, 1.0, 1.0],
            [0.8, 0.8, 0.8, 0.8],
        ],
        "candidate_route_heading_error_profile_rad": [
            [0.0, 0.1, 0.1, 0.1],
            [0.2, 0.2, 0.2, 0.2],
        ],
        "progress_lane_hard_context_atom_names": list(
            PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES
        ),
        "progress_lane_hard_context_atoms": [
            [0.0] * len(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES),
            [0.1] * len(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES),
        ],
        "latency_ms": {key: 0.1 for key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS},
    }
    if include_outcome_key:
        payload["candidate_closed_loop_outcomes"] = [_outcome(), _outcome()]
    return payload


def _record(*, seed: int = 1, include_outcome_key: bool = False) -> dict:
    latency = {key: 0.1 for key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS}
    return {
        "seed": seed,
        "progress_lane_hard_context_logging": _context_payload(
            include_outcome_key=include_outcome_key
        ),
        "candidate_closed_loop_outcomes": [_outcome(0.0), _outcome(1.0)],
        **latency,
    }


def _write_log(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_matched_context_outcome_contract_passes(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "camp_selection_log.json", [_record()])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_progress_lane_hard_context_outcome_contract_passed"
    )
    assert report["counts"]["progress_lane_hard_context_records"] == 1
    assert report["counts"]["outcome_records"] == 1
    assert report["counts"]["candidate_rows"] == 2
    assert report["analysis"]["future_outcome_leakage"] is False


def test_matched_context_outcome_contract_rejects_payload_outcomes(
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
        "matched_progress_lane_hard_context_outcome_contract_rejected"
    )
    assert any(
        "context payload contains candidate outcomes" in error
        for error in report["validation"]["errors"]
    )


def test_matched_context_outcome_contract_rejects_missing_context_payload(
    tmp_path: Path,
) -> None:
    record = _record()
    record.pop("progress_lane_hard_context_logging")
    log_path = _write_log(tmp_path / "camp_selection_log.json", [record])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_progress_lane_hard_context_outcome_contract_rejected"
    )
    assert any(
        "progress_lane_hard_context_logging missing" in error
        for error in report["validation"]["errors"]
    )


def test_matched_context_outcome_contract_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    log_path = _write_log(tmp_path / "seed_11" / "camp_selection_log.json", [_record(seed=11)])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_progress_lane_hard_context_outcome_contract_rejected"
    )
    assert report["counts"]["formal_seed_records"] >= 1
