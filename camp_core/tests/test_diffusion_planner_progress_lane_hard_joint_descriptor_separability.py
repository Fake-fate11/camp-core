from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (
    LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_joint_descriptor_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _progress_contract(status: str = "matched_progress_support_outcome_contract_passed") -> dict:
    return {
        "counts": {
            "records": 4,
            "outcome_records": 4,
            "candidate_rows": 8,
            "formal_seed_records": 0,
        },
        "final_decision": {
            "status": status,
            "passed": status == "matched_progress_support_outcome_contract_passed",
            "authorized_next_work": "offline_progress_support_descriptor_separability_screen_only",
        },
    }


def _lane_contract(
    status: str = "matched_lane_hard_violation_support_outcome_contract_passed",
) -> dict:
    return {
        "counts": {
            "records": 4,
            "outcome_records": 4,
            "candidate_rows": 8,
            "formal_seed_records": 0,
        },
        "final_decision": {
            "status": status,
            "passed": status
            == "matched_lane_hard_violation_support_outcome_contract_passed",
            "authorized_next_work": "offline_lane_hard_violation_support_descriptor_separability_screen_only",
        },
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0, *, lane: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": lane,
        "red_light_violation": False,
        "mean_jerk_mps3": 0.1,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _progress_payload(risk: float) -> dict:
    candidates = 2
    support_steps = 3
    atoms = [
        [0.0] * len(PROGRESS_SUPPORT_ATOM_NAMES),
        [risk] + [0.0] * (len(PROGRESS_SUPPORT_ATOM_NAMES) - 1),
    ]
    return {
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
        "candidate_route_progress_s_profile_m": [
            [0.0, 1.0, 2.0],
            [0.0, 1.0, 2.0 - risk],
        ],
        "candidate_plan_arc_length_profile_m": [
            [0.0, 1.0, 2.0],
            [0.0, 1.0, 2.0],
        ],
        "candidate_speed_profile_mps": [[10.0, 10.0], [10.0, 10.0]],
        "candidate_route_remaining_m": [5.0, 5.0 + risk],
        "candidate_goal_alignment_progress_m": [2.0, 2.0 - risk],
        "progress_support_atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
        "progress_support_atoms": atoms,
        "latency_ms": {key: 0.1 for key in PROGRESS_SUPPORT_LATENCY_KEYS},
    }


def _lane_payload(risk: float) -> dict:
    candidates = 2
    support_steps = 3
    atoms = [
        [0.0] * len(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES),
        [risk] + [0.0] * (len(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES) - 1),
    ]
    return {
        "schema_version": LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": candidates,
        "horizons": {"support_steps": support_steps, "dt_s": 0.1},
        "finite_checks": {
            **{name: True for name in LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES},
            "lane_hard_violation_support_atoms": True,
            "lane_hard_violation_support_atoms_nonnegative": True,
        },
        "candidate_route_lateral_error_profile_m": [
            [0.0, 0.0, 0.0],
            [0.0, risk, risk],
        ],
        "candidate_route_corridor_half_width_profile_m": [
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        "candidate_route_heading_error_profile_rad": [
            [0.0, 0.0, 0.0],
            [0.0, risk, risk],
        ],
        "candidate_lateral_error_rate_profile_mps": [
            [0.0, 0.0],
            [risk, risk],
        ],
        "lane_hard_violation_support_atom_names": list(
            LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES
        ),
        "lane_hard_violation_support_atoms": atoms,
    }


def _record(
    *,
    beneficial: bool,
    progress_risk: float,
    lane_risk: float,
    seed: int = 1,
) -> dict:
    candidate = _outcome(2.0 if beneficial else -2.0, lane=not beneficial)
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_support_logging": _progress_payload(progress_risk),
        "lane_hard_violation_support_logging": _lane_payload(lane_risk),
        "candidate_closed_loop_outcomes": [_outcome(0.0), candidate],
    }


def _items() -> list[dict]:
    return [
        {
            "raw": _record(beneficial=True, progress_risk=0.1, lane_risk=2.0),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=True, progress_risk=0.2, lane_risk=2.5),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=False, progress_risk=2.0, lane_risk=0.1),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=False, progress_risk=3.0, lane_risk=0.2),
            "context": _context(),
        },
    ]


def test_joint_descriptor_screen_finds_toy_progress_separator() -> None:
    report = analyze_records(
        _items(),
        progress_contract_report=_progress_contract(),
        lane_hard_contract_report=_lane_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["analysis"]["descriptor_families"]["progress_support"] > 0
    assert report["analysis"]["descriptor_families"]["lane_hard_support"] > 0
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_joint_descriptor_screen_blocks_when_contract_not_ready() -> None:
    report = analyze_records(
        _items(),
        progress_contract_report=_progress_contract(
            "matched_progress_support_outcome_contract_rejected"
        ),
        lane_hard_contract_report=_lane_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_joint_cologged_contract_before_separability"
    )


def test_joint_descriptor_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [
                {
                    "raw": _record(
                        beneficial=True,
                        progress_risk=0.1,
                        lane_risk=0.1,
                        seed=11,
                    ),
                    "context": _context(seed=11),
                }
            ],
            progress_contract_report=_progress_contract(),
            lane_hard_contract_report=_lane_contract(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_joint_descriptor_values_are_outcome_independent() -> None:
    base = _items()
    mutated = copy.deepcopy(base)
    mutated[0]["raw"]["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        base,
        progress_contract_report=_progress_contract(),
        lane_hard_contract_report=_lane_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )
    mutated_report = analyze_records(
        mutated,
        progress_contract_report=_progress_contract(),
        lane_hard_contract_report=_lane_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert base_report["descriptor_coverage"] == mutated_report["descriptor_coverage"]
    assert base_report["normalization"] == mutated_report["normalization"]
    assert base_report["ranked_screens"] == mutated_report["ranked_screens"]


def test_joint_descriptor_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(json.dumps([item["raw"] for item in _items()]), encoding="utf-8")

    report = analyze(
        [log_path],
        progress_contract_report=_progress_contract(),
        lane_hard_contract_report=_lane_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
