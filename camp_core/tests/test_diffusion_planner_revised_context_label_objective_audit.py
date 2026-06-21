from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_label_objective_audit import (
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


def _record(top1: dict, candidate: dict, *, risk: float, seed: int = 1) -> dict:
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(risk),
        "candidate_closed_loop_outcomes": [top1, candidate],
    }


def _context(index: int = 0, seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": index,
        "path_seeds": [seed],
    }


def _item(top1: dict, candidate: dict, *, risk: float, index: int = 0) -> dict:
    return {
        "raw": _record(top1, candidate, risk=risk),
        "context": _context(index),
    }


def _strict_good_item(*, risk: float = 2.0, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=False, lane=True, jerk=2.0, lateral=0.5),
        _outcome(2.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        risk=risk,
        index=index,
    )


def _permissive_beneficial_item(*, risk: float = 2.0, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        _outcome(2.0, feasible=True, lane=False, jerk=3.0, lateral=0.1),
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


def _bottleneck_report(
    status: str = "revised_context_atom_separability_bottleneck_diagnosed",
) -> dict:
    best = {
        "screen_name": f"{ATOM_DESCRIPTOR}:allow_low",
        "descriptor_names": [ATOM_DESCRIPTOR],
        "coefficients": {ATOM_DESCRIPTOR: 1.0},
        "threshold": 1.0,
        "harmful_block_rate": 1.0,
        "beneficial_retain_rate": 0.25,
        "allowed_harmful_rate": 0.0,
        "allowed_candidates": 1,
    }
    return {
        "records": {
            "total_records": 4,
            "payload_candidate_rows": 8,
            "classified_candidate_rows": 8,
            "alternative_rows": 4,
            "formal_seed_records": 0,
            "class_counts": {
                "beneficial_alternative": 2,
                "harmful_alternative": 2,
                "neutral_alternative": 0,
            },
        },
        "best_screen": best,
        "final_decision": {
            "status": status,
            "passed": status == "revised_context_atom_separability_bottleneck_diagnosed",
            "primary_gap": (
                "strict_atom_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
            ),
            "authorized_next_work": "revise_atom_label_or_objective_before_retraining",
        },
    }


def test_label_objective_audit_detects_permissive_beneficial_label() -> None:
    report = analyze_records(
        [
            _permissive_beneficial_item(index=0),
            _permissive_beneficial_item(index=1),
            _harmful_item(index=2),
        ],
        bottleneck_report=_bottleneck_report(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "beneficial_label_too_permissive_for_safety_score_intent"
    )
    assert report["label_audit"]["original_beneficial_count"] == 2
    assert report["label_audit"]["strict_safety_progress_comfort_good_count"] == 0
    assert report["hypothesis_diagnosis"]["camp_retraining_recommended"] is False
    assert report["final_decision"]["online_selector_authorized"] is False


def test_label_objective_audit_detects_atom_overpenalty() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=2.0, index=0),
            _strict_good_item(risk=2.0, index=1),
            _harmful_item(risk=2.0, index=2),
        ],
        bottleneck_report=_bottleneck_report(),
    )

    assert report["final_decision"]["primary_gap"] == (
        "revised_atoms_overpenalize_strict_good_candidates"
    )
    assert report["label_audit"]["strict_safety_progress_comfort_good_count"] == 2
    assert report["atom_audit"]["strict_good_blocked_count"] == 2
    assert report["atom_audit"]["strict_good_block_rate"] == 1.0


def test_label_objective_audit_detects_candidate_set_support_gap() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=0.1, index=0),
            _harmful_item(risk=2.0, index=1),
            _harmful_item(risk=2.0, index=2),
            _harmful_item(risk=2.0, index=3),
        ],
        bottleneck_report=_bottleneck_report(),
        min_strict_good_record_rate=0.5,
    )

    assert report["final_decision"]["primary_gap"] == (
        "dp_candidate_set_strict_good_support_insufficient"
    )
    assert report["candidate_set_audit"]["records_with_strict_good_candidate"] == 1
    assert report["candidate_set_audit"]["record_count"] == 4


def test_label_objective_audit_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [_strict_good_item()],
        bottleneck_report=_bottleneck_report(
            "revised_context_atom_separability_bottleneck_source_not_ready"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_revised_context_label_objective_source_before_audit"
    )


def test_label_objective_audit_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    rows = [
        _strict_good_item(index=0)["raw"],
        _harmful_item(index=1)["raw"],
    ]
    log_path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(
        [log_path],
        bottleneck_report=_bottleneck_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
