from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_progress_support_descriptor_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _contract(status: str = "matched_progress_support_outcome_contract_passed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "matched_progress_support_outcome_contract_passed",
            "authorized_next_work": (
                "offline_progress_support_descriptor_separability_screen_only"
            ),
        }
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0, *, red: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
        "mean_jerk_mps3": 0.1,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _payload(risk: float) -> dict:
    candidates = 2
    support_steps = 3
    atoms = [[0.0] * len(PROGRESS_SUPPORT_ATOM_NAMES), [risk] + [0.0] * (len(PROGRESS_SUPPORT_ATOM_NAMES) - 1)]
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
        "candidate_route_progress_s_profile_m": [[0.0, 1.0, 2.0], [0.0, 1.0, 2.0 - risk]],
        "candidate_plan_arc_length_profile_m": [[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]],
        "candidate_speed_profile_mps": [[10.0, 10.0], [10.0, 10.0]],
        "candidate_route_remaining_m": [5.0, 5.0 + risk],
        "candidate_goal_alignment_progress_m": [2.0, 2.0 - risk],
        "progress_support_atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
        "progress_support_atoms": atoms,
        "latency_ms": {key: 0.1 for key in PROGRESS_SUPPORT_LATENCY_KEYS},
    }
    return payload


def _record(*, beneficial: bool, risk: float, seed: int = 1) -> dict:
    candidate = _outcome(2.0 if beneficial else -2.0)
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_support_logging": _payload(risk),
        "candidate_closed_loop_outcomes": [_outcome(0.0), candidate],
    }


def test_progress_support_descriptor_screen_finds_toy_atom_separator() -> None:
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


def test_progress_support_descriptor_screen_blocks_when_contract_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(beneficial=True, risk=0.1), "context": _context()}],
        matched_contract_report=_contract("matched_progress_support_outcome_contract_rejected"),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_matched_progress_support_outcome_contract_before_separability"
    )


def test_progress_support_descriptor_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(beneficial=True, risk=0.1, seed=11), "context": _context(seed=11)}],
            matched_contract_report=_contract(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_progress_support_descriptor_values_are_outcome_independent() -> None:
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
    assert base_report["single_descriptor_screens"] == mutated_report["single_descriptor_screens"]


def test_progress_support_descriptor_cli_reads_selection_log(tmp_path: Path) -> None:
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
