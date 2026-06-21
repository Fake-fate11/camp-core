from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_relaxed_strict_label_atom_schema_preflight import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _payload() -> dict:
    return {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": 2,
        "horizons": {"support_steps": 5, "dt_s": 0.1},
        "budgets": {
            "corridor_safety_margin_m": 0.25,
        },
        "finite_checks": {
            **{name: True for name in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES},
        },
        "route_curvature_context_abs_radpm": [0.0, 0.0, 0.0, 0.0],
        "candidate_lateral_error_rate_profile_mps": [
            [0.0, 0.0, 0.0, 0.0],
            [0.1, 0.4, -0.2, 0.3],
        ],
        "candidate_speed_profile_mps": [
            [4.0, 4.0, 4.0, 4.0],
            [3.0, 5.0, 4.0, 6.0],
        ],
        "candidate_route_progress_delta_profile_m": [
            [0.4, 0.4, 0.4, 0.4],
            [0.4, 0.4, 0.4, 0.4],
        ],
        "candidate_route_corridor_margin_profile_m": [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 0.2, 0.1, 0.05],
        ],
        "candidate_route_heading_error_profile_rad": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.3, 0.1, 0.6],
        ],
    }


def _outcome(value: float = 0.0) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": 1.0,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
    }


def _record(seed: int = 1) -> dict:
    return {
        "num_candidates": 2,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(),
        "candidate_closed_loop_outcomes": [_outcome(0.0), _outcome(10.0)],
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/sample/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _bottleneck_report(
    status: str = "revised_context_relaxed_strict_label_atom_bottleneck_diagnosed",
) -> dict:
    return {
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
            "passed": True,
            "primary_gap": (
                "relaxed_strict_label_atom_overlap_blocks_beneficial_and_allows_harmful"
            ),
            "authorized_next_work": "predeclare_relaxed_strict_label_no_leak_atom_schema",
        },
    }


def test_relaxed_strict_label_atom_schema_preflight_authorizes_only_payload_unit_gate() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        bottleneck_report=_bottleneck_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "default_off_relaxed_strict_label_atom_payload_implementation_unit_tests_only"
    )
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["classic_benders_claim_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert all(row["passed_preflight"] for row in report["atom_reports"])
    assert all(row["nonzero_candidate_rows"] > 0 for row in report["atom_reports"])
    assert all(check["passed"] for check in report["math_checks"])


def test_relaxed_strict_label_atom_schema_preflight_blocks_when_source_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        bottleneck_report=_bottleneck_report("unexpected_status"),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_relaxed_strict_label_bottleneck_source_before_schema_preflight"
    )


def test_relaxed_strict_label_atom_schema_preflight_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(seed=11), "context": _context(seed=11)}],
            bottleneck_report=_bottleneck_report(),
            fail_on_formal_seeds=True,
        )


def test_relaxed_strict_label_atom_schema_preflight_is_outcome_independent() -> None:
    base = _record()
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["value"] = 1000.0
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = -10.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        bottleneck_report=_bottleneck_report(),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        bottleneck_report=_bottleneck_report(),
    )

    base_atoms = {row["name"]: row["summary"] for row in base_report["atom_reports"]}
    mutated_atoms = {
        row["name"]: row["summary"] for row in mutated_report["atom_reports"]
    }
    assert base_atoms == mutated_atoms


def test_relaxed_strict_label_product_atom_is_fixed_coefficient_only() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        bottleneck_report=_bottleneck_report(),
    )

    product_rows = [
        row for row in report["atom_reports"] if row["uses_product_of_current_tick_features"]
    ]
    assert [row["name"] for row in product_rows] == ["roughness_corridor_conflict_v1"]
    assert all(row["fixed_coefficient_affine_only"] for row in product_rows)
    assert not any(row["trajectory_coordinate_convexity_claim"] for row in product_rows)
    assert not any(row["classical_benders_claim"] for row in product_rows)
