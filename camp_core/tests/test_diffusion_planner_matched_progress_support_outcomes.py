from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_matched_progress_support_outcomes import (
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


def _progress_payload(*, include_outcome_key: bool = False) -> dict:
    candidates = 2
    support_steps = 3
    payload = {
        "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": candidates,
        "horizons": {"support_steps": support_steps, "dt_s": 0.1},
        "field_shapes": {
            "candidate_route_progress_s_profile_m": [candidates, support_steps],
            "candidate_plan_arc_length_profile_m": [candidates, support_steps],
            "candidate_speed_profile_mps": [candidates, support_steps - 1],
            "candidate_route_remaining_m": [candidates],
            "candidate_goal_alignment_progress_m": [candidates],
        },
        "finite_checks": {
            **{name: True for name in PROGRESS_SUPPORT_FIELD_NAMES},
            "progress_support_atoms": True,
            "progress_support_atoms_nonnegative": True,
        },
        "candidate_route_progress_s_profile_m": [[0.0, 1.0, 2.0], [0.0, 0.9, 1.8]],
        "candidate_plan_arc_length_profile_m": [[0.0, 1.0, 2.0], [0.0, 1.1, 2.2]],
        "candidate_speed_profile_mps": [[10.0, 10.0], [9.0, 9.0]],
        "candidate_route_remaining_m": [5.0, 5.2],
        "candidate_goal_alignment_progress_m": [2.0, 1.8],
        "progress_support_atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
        "progress_support_atoms": [[0.0] * len(PROGRESS_SUPPORT_ATOM_NAMES)] * candidates,
        "latency_ms": {key: 0.1 for key in PROGRESS_SUPPORT_LATENCY_KEYS},
    }
    if include_outcome_key:
        payload["candidate_closed_loop_outcomes"] = [_outcome(), _outcome()]
    return payload


def _record(*, seed: int = 1, include_outcome_key: bool = False) -> dict:
    latency = {key: 0.1 for key in PROGRESS_SUPPORT_LATENCY_KEYS}
    return {
        "seed": seed,
        "progress_support_logging": _progress_payload(
            include_outcome_key=include_outcome_key
        ),
        "candidate_closed_loop_outcomes": [_outcome(0.0), _outcome(1.0)],
        **latency,
    }


def _write_log(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_matched_progress_support_outcome_contract_passes(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "camp_selection_log.json", [_record()])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == (
        "matched_progress_support_outcome_contract_passed"
    )
    assert report["counts"]["progress_support_records"] == 1
    assert report["counts"]["outcome_records"] == 1
    assert report["counts"]["candidate_rows"] == 2
    assert report["analysis"]["future_outcome_leakage"] is False


def test_matched_progress_support_outcome_contract_rejects_payload_outcomes(
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
        "matched_progress_support_outcome_contract_rejected"
    )
    assert any(
        "payload contains candidate outcomes" in error
        for error in report["validation"]["errors"]
    )


def test_matched_progress_support_outcome_contract_rejects_formal_seed(
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
        "matched_progress_support_outcome_contract_rejected"
    )
    assert report["counts"]["formal_seed_records"] >= 1
