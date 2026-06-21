from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_sensitivity import (
    DIAGNOSED_STATUS,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


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


def _strict_good_item(*, risk: float = 0.1, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=False, lane=True, jerk=2.0, lateral=0.5),
        _outcome(2.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        risk=risk,
        index=index,
    )


def _harmful_item(*, risk: float = 2.0, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        _outcome(-2.0, feasible=False, lane=True, jerk=4.0, lateral=1.0),
        risk=risk,
        index=index,
    )


def _strict_label_report(
    status: str = "revised_context_strict_label_separability_rejected",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "strict_beneficial_support_insufficient",
            "authorized_next_work": (
                "relax_or_redefine_strict_label_or_expand_nonformal_support"
            ),
        }
    }


def _label_objective_report() -> dict:
    return {
        "final_decision": {
            "status": "revised_context_label_objective_audit_diagnosed",
            "passed": True,
            "primary_gap": "beneficial_label_too_permissive_for_safety_score_intent",
            "authorized_next_work": (
                "predeclare_revised_label_or_atom_change_before_new_replay"
            ),
        }
    }


def _one_point_kwargs() -> dict:
    return {
        "progress_loss_budgets_m": [0.05],
        "safety_improvement_margins": [0.05],
        "comfort_jerk_delta_budgets": [0.0],
        "comfort_lateral_delta_budgets": [0.0],
    }


def test_strict_label_sensitivity_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [_strict_good_item(), _harmful_item(index=1)],
        strict_label_report=_strict_label_report(
            "revised_context_strict_label_separability_promising"
        ),
        label_objective_audit_report=_label_objective_report(),
        min_strict_beneficial_candidates=1,
        min_harmful_candidates=1,
        **_one_point_kwargs(),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["grid_summary"]["grid_count"] == 0


def test_strict_label_sensitivity_reports_support_limited() -> None:
    report = analyze_records(
        [_strict_good_item(index=0), _harmful_item(index=1), _harmful_item(index=2)],
        strict_label_report=_strict_label_report(),
        label_objective_audit_report=_label_objective_report(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
        **_one_point_kwargs(),
    )

    assert report["final_decision"]["status"] == DIAGNOSED_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "no_nearby_strict_label_has_sufficient_beneficial_support"
    )
    assert report["grid_summary"]["max_strict_beneficial_candidates"] == 1


def test_strict_label_sensitivity_reports_support_without_separability() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=2.0, index=0),
            _strict_good_item(risk=3.0, index=1),
            _harmful_item(risk=0.1, index=2),
            _harmful_item(risk=0.2, index=3),
        ],
        strict_label_report=_strict_label_report(),
        label_objective_audit_report=_label_objective_report(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
        **_one_point_kwargs(),
    )

    assert report["final_decision"]["status"] == DIAGNOSED_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "support_exists_but_revised_atoms_do_not_separate_relaxed_strict_label"
    )
    assert report["grid_summary"]["support_sufficient_count"] == 1
    assert report["grid_summary"]["promising_count"] == 0


def test_strict_label_sensitivity_finds_toy_promising_grid_point() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=0.1, index=0),
            _strict_good_item(risk=0.2, index=1),
            _harmful_item(risk=2.0, index=2),
            _harmful_item(risk=3.0, index=3),
        ],
        strict_label_report=_strict_label_report(),
        label_objective_audit_report=_label_objective_report(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
        **_one_point_kwargs(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["grid_summary"]["promising_count"] == 1
    assert report["top_grid_results"][0]["best_screen"]["beneficial_retain_rate"] == 1.0


def test_strict_label_sensitivity_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _strict_good_item(index=0)["raw"],
                _strict_good_item(index=1)["raw"],
                _harmful_item(index=2)["raw"],
                _harmful_item(index=3)["raw"],
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        strict_label_report=_strict_label_report(),
        label_objective_audit_report=_label_objective_report(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
        **_one_point_kwargs(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["grid_summary"]["grid_count"] == 1
