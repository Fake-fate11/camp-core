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
from scripts.integrations.analyze_diffusion_planner_lane_hard_violation_support_descriptor_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _contract(
    status: str = "matched_lane_hard_violation_support_outcome_contract_passed",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status
            == "matched_lane_hard_violation_support_outcome_contract_passed",
            "authorized_next_work": (
                "offline_lane_hard_violation_support_descriptor_separability_screen_only"
            ),
        }
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


def _payload(risk: float) -> dict:
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


def _record(*, beneficial: bool, risk: float, seed: int = 1) -> dict:
    candidate = _outcome(2.0 if beneficial else -2.0)
    return {
        "num_candidates": 2,
        "seed": seed,
        "lane_hard_violation_support_logging": _payload(risk),
        "candidate_closed_loop_outcomes": [_outcome(0.0), candidate],
    }


def test_lane_hard_descriptor_screen_finds_toy_atom_separator() -> None:
    items = [
        {"raw": _record(beneficial=True, risk=0.1), "context": _context()},
        {"raw": _record(beneficial=True, risk=0.2), "context": _context()},
        {"raw": _record(beneficial=False, risk=2.0), "context": _context()},
        {"raw": _record(beneficial=False, risk=3.0), "context": _context()},
    ]

    report = analyze_records(
        items,
        matched_contract_report=_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["analysis"]["thresholds_are_offline_oracle_diagnostics"] is True
    assert report["final_decision"]["online_selector_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_lane_hard_descriptor_screen_blocks_when_contract_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(beneficial=True, risk=0.1), "context": _context()}],
        matched_contract_report=_contract(
            "matched_lane_hard_violation_support_outcome_contract_rejected"
        ),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_matched_lane_hard_support_outcome_contract_before_separability"
    )


def test_lane_hard_descriptor_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [
                {
                    "raw": _record(beneficial=True, risk=0.1, seed=11),
                    "context": _context(seed=11),
                }
            ],
            matched_contract_report=_contract(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_lane_hard_descriptor_values_are_outcome_independent() -> None:
    base = _record(beneficial=True, risk=0.1)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert base_report["descriptor_coverage"] == mutated_report["descriptor_coverage"]
    assert base_report["normalization"] == mutated_report["normalization"]
    assert base_report["single_descriptor_screens"] == mutated_report[
        "single_descriptor_screens"
    ]


def test_lane_hard_descriptor_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(beneficial=True, risk=0.1),
                _record(beneficial=False, risk=2.0),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
