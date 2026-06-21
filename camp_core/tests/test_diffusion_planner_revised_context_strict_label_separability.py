from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_separability import (
    READY_STATUS,
    REJECT_STATUS,
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


def _item(
    top1: dict,
    candidate: dict,
    *,
    risk: float,
    index: int = 0,
    seed: int = 1,
) -> dict:
    return {
        "raw": _record(top1, candidate, risk=risk, seed=seed),
        "context": _context(index, seed=seed),
    }


def _strict_good_item(
    *,
    risk: float = 0.1,
    index: int = 0,
    seed: int = 1,
) -> dict:
    return _item(
        _outcome(0.0, feasible=False, lane=True, jerk=2.0, lateral=0.5),
        _outcome(2.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        risk=risk,
        index=index,
        seed=seed,
    )


def _harmful_item(*, risk: float = 2.0, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        _outcome(-2.0, feasible=False, lane=True, jerk=4.0, lateral=1.0),
        risk=risk,
        index=index,
    )


def _neutral_item(*, risk: float = 0.5, index: int = 0) -> dict:
    return _item(
        _outcome(0.0, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        _outcome(0.1, feasible=True, lane=False, jerk=1.0, lateral=0.1),
        risk=risk,
        index=index,
    )


def _source_audit(
    status: str = "revised_context_label_objective_audit_diagnosed",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "revised_context_label_objective_audit_diagnosed",
            "primary_gap": "beneficial_label_too_permissive_for_safety_score_intent",
            "authorized_next_work": (
                "predeclare_revised_label_or_atom_change_before_new_replay"
            ),
        }
    }


def test_strict_label_separability_rejects_insufficient_support() -> None:
    report = analyze_records(
        [
            _strict_good_item(index=0),
            _harmful_item(index=1),
            _harmful_item(index=2),
        ],
        label_objective_audit_report=_source_audit(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "strict_beneficial_support_insufficient"
    )
    assert report["records"]["class_counts"]["beneficial_alternative"] == 1
    assert report["final_decision"]["camp_retraining_authorized"] is False


def test_strict_label_separability_finds_toy_separator() -> None:
    report = analyze_records(
        [
            _strict_good_item(risk=0.1, index=0),
            _strict_good_item(risk=0.2, index=1),
            _harmful_item(risk=2.0, index=2),
            _harmful_item(risk=3.0, index=3),
        ],
        label_objective_audit_report=_source_audit(),
        min_strict_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert report["records"]["class_counts"]["harmful_alternative"] == 2
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0
    assert report["final_decision"]["online_selector_authorized"] is False


def test_strict_label_separability_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [_strict_good_item(), _harmful_item(index=1)],
        label_objective_audit_report=_source_audit(
            "revised_context_label_objective_audit_source_not_ready"
        ),
        min_strict_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_label_objective_audit_before_strict_label_screen"
    )


def test_strict_label_descriptor_coverage_is_outcome_independent() -> None:
    items = [_strict_good_item(), _harmful_item(index=1), _neutral_item(index=2)]
    mutated = copy.deepcopy(items)
    mutated[0]["raw"]["candidate_closed_loop_outcomes"][1]["value"] = 99.0

    base = analyze_records(
        items,
        label_objective_audit_report=_source_audit(),
        min_strict_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    changed = analyze_records(
        mutated,
        label_objective_audit_report=_source_audit(),
        min_strict_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert (
        base["payload_descriptor_coverage"]
        == changed["payload_descriptor_coverage"]
    )
    assert base["normalization"] == changed["normalization"]


def test_strict_label_separability_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [_strict_good_item(index=0, seed=11)],
            label_objective_audit_report=_source_audit(),
            min_strict_beneficial_candidates=1,
            min_harmful_candidates=1,
            fail_on_formal_seeds=True,
        )


def test_strict_label_separability_cli_reads_selection_log(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    rows = [
        _strict_good_item(index=0)["raw"],
        _harmful_item(index=1)["raw"],
    ]
    log_path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(
        [log_path],
        label_objective_audit_report=_source_audit(),
        min_strict_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
