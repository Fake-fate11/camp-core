from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_component_overlap import (
    NEXT_WORK_LIMITATION,
    NEXT_WORK_REDESIGN,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


ROUGHNESS_CONFLICT = "relaxed_strict_atom_roughness_corridor_conflict_v1"


def _outcome(
    *,
    feasible: bool,
    red: bool = False,
    lane: bool = False,
    progress: float = 1.0,
    jerk: float = 1.0,
    lateral: float = 0.1,
) -> dict:
    return {
        "value": 0.0,
        "feasible": feasible,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "red_light_violation": red,
        "lane_violation": lane,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _payload(*, roughness: float, margin_drop: float) -> dict:
    return {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": 2,
        "horizons": {"support_steps": 4, "dt_s": 0.1},
        "budgets": {"corridor_safety_margin_m": 0.25},
        "finite_checks": {name: True for name in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES},
        "route_curvature_context_abs_radpm": [0.0, 0.0, 0.0, 0.0],
        "candidate_lateral_error_rate_profile_mps": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, roughness * 0.1, 0.0, 0.0],
        ],
        "candidate_speed_profile_mps": [
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0],
        ],
        "candidate_route_progress_delta_profile_m": [
            [0.4, 0.4, 0.4, 0.4],
            [0.4, 0.4, 0.4, 0.4],
        ],
        "candidate_route_corridor_margin_profile_m": [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0 - margin_drop, 1.0 - margin_drop, 1.0 - margin_drop],
        ],
        "candidate_route_heading_error_profile_rad": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ],
    }


def _record(
    top1: dict,
    candidate: dict,
    *,
    roughness: float,
    margin_drop: float,
    seed: int = 1,
) -> dict:
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(
            roughness=roughness,
            margin_drop=margin_drop,
        ),
        "candidate_closed_loop_outcomes": [top1, candidate],
    }


def _beneficial_item(
    *,
    roughness: float,
    margin_drop: float,
    index: int = 0,
    seed: int = 1,
) -> dict:
    top1 = _outcome(feasible=True, red=True, progress=1.0, jerk=1.0, lateral=0.2)
    candidate = _outcome(feasible=True, red=False, progress=1.05, jerk=1.0, lateral=0.2)
    return {
        "raw": _record(
            top1,
            candidate,
            roughness=roughness,
            margin_drop=margin_drop,
            seed=seed,
        ),
        "context": _context(index, seed),
    }


def _harmful_item(
    *,
    roughness: float,
    margin_drop: float,
    index: int = 0,
    seed: int = 1,
) -> dict:
    top1 = _outcome(feasible=True, progress=1.0, jerk=1.0, lateral=0.1)
    candidate = _outcome(
        feasible=False,
        lane=True,
        progress=1.05,
        jerk=3.0,
        lateral=0.4,
    )
    return {
        "raw": _record(
            top1,
            candidate,
            roughness=roughness,
            margin_drop=margin_drop,
            seed=seed,
        ),
        "context": _context(index, seed),
    }


def _context(index: int, seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/sample/seed_{seed}/camp_selection_log.json",
        "record_index": index,
        "path_seeds": [seed],
    }


def _bottleneck_report(
    status: str = "relaxed_strict_label_atom_bottleneck_diagnosed",
    *,
    threshold: float = 0.5,
) -> dict:
    best_screen = {
        "screen_name": f"{ROUGHNESS_CONFLICT}:allow_low",
        "descriptor_names": [ROUGHNESS_CONFLICT],
        "coefficients": {ROUGHNESS_CONFLICT: 1.0},
        "direction": "allow_low",
        "threshold": threshold,
        "harmful_block_rate": 1.0,
        "beneficial_retain_rate": 0.0,
        "allowed_harmful_rate": 0.0,
        "allowed_candidates": 0,
        "promising_screen": False,
    }
    return {
        "analysis": {
            "selected_label_params": {
                "progress_loss_budget_m": 0.1,
                "comfort_jerk_delta_budget": 0.5,
                "comfort_lateral_delta_budget": 0.1,
                "safety_improvement_margin": 0.0,
                "harmful_safety_margin": 0.05,
            },
        },
        "best_screen": best_screen,
        "blocked_actions": {
            "new_replay_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "online_optimization_promotion_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "final_decision": {
            "status": status,
            "passed": status == "relaxed_strict_label_atom_bottleneck_diagnosed",
            "primary_gap": (
                "relaxed_strict_atom_threshold_tradeoff_overblocks_or_leaks_harmful"
            ),
            "authorized_next_work": "reject_or_redesign_relaxed_strict_no_leak_atom_family",
        },
    }


def test_component_overlap_finds_existing_component_separator() -> None:
    report = analyze_records(
        [
            _beneficial_item(roughness=1.0, margin_drop=1.0, index=0),
            _beneficial_item(roughness=1.0, margin_drop=1.0, index=1),
            _harmful_item(roughness=10.0, margin_drop=0.1, index=2),
            _harmful_item(roughness=10.0, margin_drop=0.1, index=3),
        ],
        bottleneck_report=_bottleneck_report(),
        target_retain_rate=0.5,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == NEXT_WORK_REDESIGN
    assert report["diagnosis"]["promising_component_separator_found"] is True
    assert report["best_component_screen"]["descriptor"] == (
        "relaxed_strict_atom_lateral_rate_change_surrogate_v1"
    )
    assert report["best_component_screen"]["good_retain_rate"] == 1.0
    assert report["best_component_screen"]["harmful_block_rate"] == 1.0


def test_component_overlap_rejects_when_components_overlap() -> None:
    report = analyze_records(
        [
            _beneficial_item(roughness=1.0, margin_drop=1.0, index=0),
            _beneficial_item(roughness=1.0, margin_drop=1.0, index=1),
            _harmful_item(roughness=1.0, margin_drop=1.0, index=2),
            _harmful_item(roughness=1.0, margin_drop=1.0, index=3),
        ],
        bottleneck_report=_bottleneck_report(),
        target_retain_rate=0.5,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == NEXT_WORK_LIMITATION
    assert report["diagnosis"]["promising_component_separator_found"] is False
    assert report["best_component_screen"]["harmful_block_rate"] == 0.0


def test_component_overlap_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [
            _beneficial_item(roughness=1.0, margin_drop=1.0, index=0),
            _harmful_item(roughness=10.0, margin_drop=0.1, index=1),
        ],
        bottleneck_report=_bottleneck_report("unexpected_status"),
        target_retain_rate=0.5,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_component_overlap_source_before_diagnosis"
    )


def test_component_overlap_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [_beneficial_item(roughness=1.0, margin_drop=1.0, seed=11)],
            bottleneck_report=_bottleneck_report(),
            fail_on_formal_seeds=True,
        )


def test_component_overlap_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    rows = [
        _beneficial_item(roughness=1.0, margin_drop=1.0, index=0)["raw"],
        _harmful_item(roughness=10.0, margin_drop=0.1, index=1)["raw"],
    ]
    log_path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(
        [log_path],
        bottleneck_report=_bottleneck_report(),
        target_retain_rate=0.5,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["formal_seed_records"] == 0
