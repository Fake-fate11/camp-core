from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_relaxed_strict_label_atom_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


ATOM_DESCRIPTOR = f"revised_atom_{PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES[0]}"


def _outcome(
    value: float,
    progress: float = 10.0,
    *,
    feasible: bool = True,
    lane: bool = False,
    jerk: float = 1.0,
    lateral: float = 0.1,
) -> dict:
    return {
        "value": value,
        "feasible": feasible,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": lane,
        "red_light_violation": False,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _payload(risk: float) -> dict:
    atom_count = len(PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES)
    revised_atoms = [
        [0.0] * atom_count,
        [risk] + [0.0] * (atom_count - 1),
    ]
    return {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": 2,
        "finite_checks": {
            "revised_progress_lane_hard_context_atoms": True,
            "revised_progress_lane_hard_context_atoms_nonnegative": True,
        },
        "revised_progress_lane_hard_context_atom_schema_version": (
            PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION
        ),
        "revised_progress_lane_hard_context_atom_names": list(
            PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES
        ),
        "revised_progress_lane_hard_context_atoms": revised_atoms,
    }


def _record(top1: dict, candidate: dict, *, risk: float) -> dict:
    return {
        "num_candidates": 2,
        "seed": 1,
        "progress_lane_hard_context_logging": _payload(risk),
        "candidate_closed_loop_outcomes": [top1, candidate],
    }


def _context(index: int = 0) -> dict:
    return {
        "log_path": "/tmp/route/seed_1/camp_selection_log.json",
        "record_index": index,
        "path_seeds": [1],
    }


def _item(top1: dict, candidate: dict, *, risk: float, index: int = 0) -> dict:
    return {"raw": _record(top1, candidate, risk=risk), "context": _context(index)}


def _strict_good_item(*, risk: float = 2.0, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=False, lane=True, jerk=2.0, lateral=0.5),
        _outcome(2.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        risk=risk,
        index=index,
    )


def _harmful_item(*, risk: float = 0.1, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        _outcome(-2.0, feasible=False, lane=True, jerk=4.0, lateral=1.0),
        risk=risk,
        index=index,
    )


def _sensitivity_report(
    status: str = "revised_context_strict_label_sensitivity_diagnosed",
    *,
    threshold: float = 1.0,
) -> dict:
    return {
        "grid_summary": {
            "best_by_support": {
                "params": {
                    "progress_loss_budget_m": 0.05,
                    "safety_improvement_margin": 0.05,
                    "comfort_jerk_delta_budget": 0.0,
                    "comfort_lateral_delta_budget": 0.0,
                },
                "best_screen": {
                    "screen_name": f"{ATOM_DESCRIPTOR}:allow_low",
                    "descriptor_names": [ATOM_DESCRIPTOR],
                    "threshold": threshold,
                    "harmful_block_rate": 1.0,
                    "beneficial_retain_rate": 0.25,
                    "allowed_harmful_rate": 0.0,
                    "allowed_candidates": 1,
                },
                "class_counts": {
                    "beneficial_alternative": 2,
                    "harmful_alternative": 2,
                    "neutral_alternative": 0,
                },
            }
        },
        "final_decision": {
            "status": status,
            "passed": status == "revised_context_strict_label_sensitivity_diagnosed",
            "primary_gap": (
                "support_exists_but_revised_atoms_do_not_separate_relaxed_strict_label"
            ),
            "authorized_next_work": (
                "diagnose_relaxed_strict_label_atom_bottleneck_before_replay"
            ),
        },
    }


def test_relaxed_strict_label_bottleneck_diagnoses_overlap() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=2.0, index=0),
            _strict_good_item(risk=3.0, index=1),
            _harmful_item(risk=0.1, index=2),
            _harmful_item(risk=0.2, index=3),
        ],
        sensitivity_report=_sensitivity_report(threshold=1.0),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["diagnosis"]["primary_gap"] == (
        "relaxed_strict_label_atom_overlap_blocks_beneficial_and_allows_harmful"
    )
    assert report["counts"]["beneficial_blocked"] == 2
    assert report["counts"]["harmful_allowed"] == 2
    assert report["diagnosis"]["camp_retraining_recommended"] is False
    assert report["final_decision"]["online_selector_authorized"] is False


def test_relaxed_strict_label_bottleneck_diagnoses_overblocking() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=2.0, index=0),
            _strict_good_item(risk=3.0, index=1),
            _harmful_item(risk=4.0, index=2),
            _harmful_item(risk=5.0, index=3),
        ],
        sensitivity_report=_sensitivity_report(threshold=1.0),
    )

    assert report["diagnosis"]["primary_gap"] == (
        "relaxed_strict_label_atoms_overblock_beneficial"
    )
    assert report["counts"]["beneficial_blocked"] == 2
    assert report["counts"]["harmful_allowed"] == 0


def test_relaxed_strict_label_bottleneck_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [_strict_good_item(), _harmful_item(index=1)],
        sensitivity_report=_sensitivity_report(
            "revised_context_strict_label_sensitivity_source_not_ready"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_relaxed_strict_label_bottleneck_source_before_diagnosis"
    )


def test_relaxed_strict_label_bottleneck_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    rows = [
        _strict_good_item(index=0)["raw"],
        _strict_good_item(index=1)["raw"],
        _harmful_item(index=2)["raw"],
        _harmful_item(index=3)["raw"],
    ]
    log_path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze([log_path], sensitivity_report=_sensitivity_report())

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
