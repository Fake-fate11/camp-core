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
from scripts.integrations.analyze_diffusion_planner_revised_context_atom_separability_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


ATOM_DESCRIPTOR = f"revised_atom_{PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES[0]}"


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


def _record(*, beneficial: bool, risk: float, seed: int = 1) -> dict:
    candidate = _outcome(2.0 if beneficial else -2.0, lane=not beneficial)
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(risk),
        "candidate_closed_loop_outcomes": [_outcome(0.0), candidate],
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _item(*, beneficial: bool, risk: float, seed: int = 1) -> dict:
    return {
        "raw": _record(beneficial=beneficial, risk=risk, seed=seed),
        "context": _context(seed),
    }


def _separability_report(
    status: str = "revised_progress_lane_hard_context_atom_separability_rejected",
) -> dict:
    strict = {
        "screen_name": f"{ATOM_DESCRIPTOR}:allow_low",
        "descriptor_names": [ATOM_DESCRIPTOR],
        "coefficients": {ATOM_DESCRIPTOR: 1.0},
        "threshold": 1.0,
        "harmful_block_rate": 1.0,
        "beneficial_retain_rate": 0.25,
        "allowed_harmful_rate": 0.0,
        "allowed_candidates": 1,
        "promising_screen": False,
    }
    high_retain = {
        "screen_name": f"{ATOM_DESCRIPTOR}:allow_low_high_retain",
        "descriptor_names": [ATOM_DESCRIPTOR],
        "coefficients": {ATOM_DESCRIPTOR: 1.0},
        "threshold": 3.0,
        "harmful_block_rate": 0.1,
        "beneficial_retain_rate": 1.0,
        "allowed_harmful_rate": 0.5,
        "allowed_candidates": 12,
        "promising_screen": False,
    }
    return {
        "records": {
            "total_records": 4,
            "outcome_records": 4,
            "missing_outcome_records": 0,
            "candidate_rows": 8,
            "classified_candidate_rows": 8,
            "alternative_rows": 4,
            "formal_seed_records": 0,
            "class_counts": {
                "beneficial_alternative": 2,
                "harmful_alternative": 2,
                "neutral_alternative": 0,
            },
        },
        "ranked_screens": [strict, high_retain],
        "single_descriptor_screens": [strict, high_retain],
        "affine_screens": [],
        "failure_gap": {
            "primary_gap": "beneficial_retain_rate_insufficient",
            "best_screen": strict,
        },
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "revised_context_atoms_do_not_separate_candidates",
            "promising_screen_count": 0,
            "authorized_next_work": (
                "diagnose_revised_context_atom_bottleneck_before_retraining"
            ),
        },
    }


def _diagnostic_items() -> list[dict]:
    return [
        _item(beneficial=True, risk=0.1),
        _item(beneficial=True, risk=2.0),
        _item(beneficial=False, risk=0.1),
        _item(beneficial=False, risk=2.0),
    ]


def test_revised_context_atom_bottleneck_diagnoses_tradeoff() -> None:
    report = analyze_records(
        _diagnostic_items(),
        separability_report=_separability_report(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["counts"]["beneficial_blocked"] == 1
    assert report["counts"]["harmful_allowed"] == 1
    assert report["diagnosis"]["primary_gap"] == (
        "strict_atom_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
    )
    assert report["diagnosis"]["camp_retraining_recommended"] is False
    assert report["diagnosis"]["stale_camp_weight_bottleneck_supported"] is False
    assert report["screen_tradeoff"]["strict_safe_screen_count"] == 1
    assert report["screen_tradeoff"]["high_retain_screen_count"] == 1
    assert report["allowed_harmful"]["reason_counts"]["lane_worse"] == 1
    assert (
        report["screen_applications"]["best_high_retain_screen"]["counts"][
            "harmful_allowed"
        ]
        == 2
    )


def test_revised_context_atom_bottleneck_blocks_when_source_not_rejected() -> None:
    report = analyze_records(
        _diagnostic_items(),
        separability_report=_separability_report(
            "revised_progress_lane_hard_context_atom_separability_promising_for_certificate_design"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_revised_atom_bottleneck_source_before_diagnosis"
    )


def test_revised_context_atom_bottleneck_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [_item(beneficial=True, risk=0.1, seed=11)],
            separability_report=_separability_report(),
            fail_on_formal_seeds=True,
        )


def test_revised_context_atom_bottleneck_descriptor_overlap_is_outcome_independent() -> None:
    items = _diagnostic_items()
    mutated = copy.deepcopy(items)
    mutated[0]["raw"]["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base = analyze_records(items, separability_report=_separability_report())
    changed = analyze_records(mutated, separability_report=_separability_report())

    assert base["descriptor_overlap"] == changed["descriptor_overlap"]
    assert base["screen_tradeoff"] == changed["screen_tradeoff"]
    assert base["counts"] == changed["counts"]


def test_revised_context_atom_bottleneck_cli_reads_selection_log(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps([row["raw"] for row in _diagnostic_items()]),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        separability_report=_separability_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
