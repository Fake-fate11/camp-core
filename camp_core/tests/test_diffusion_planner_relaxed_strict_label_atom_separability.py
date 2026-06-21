from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_separability import (
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
        "candidate_count": 3,
        "horizons": {"support_steps": 5, "dt_s": 0.1},
        "budgets": {"corridor_safety_margin_m": 0.25},
        "finite_checks": {
            **{name: True for name in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES},
        },
        "route_curvature_context_abs_radpm": [0.0, 0.0, 0.0, 0.0],
        "candidate_lateral_error_rate_profile_mps": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.8, -0.8, 0.8],
        ],
        "candidate_speed_profile_mps": [
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0],
            [0.0, 4.0, 0.0, 4.0],
        ],
        "candidate_route_progress_delta_profile_m": [
            [0.4, 0.4, 0.4, 0.4],
            [0.4, 0.4, 0.4, 0.4],
            [0.4, 0.4, 0.4, 0.4],
        ],
        "candidate_route_corridor_margin_profile_m": [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 0.8, 0.4, 0.1],
        ],
        "candidate_route_heading_error_profile_rad": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.5],
        ],
    }


def _outcome(
    *,
    feasible: bool = True,
    red: bool = False,
    jerk: float = 0.0,
    lateral: float = 0.0,
) -> dict:
    return {
        "value": 0.0,
        "feasible": feasible,
        "progress_m": 1.0,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
    }


def _record(seed: int = 1) -> dict:
    return {
        "num_candidates": 3,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(),
        "candidate_closed_loop_outcomes": [
            _outcome(red=True),
            _outcome(red=False),
            _outcome(red=True, jerk=10.0),
        ],
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/sample/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _preflight_report(status: str = "revised_context_relaxed_strict_label_atom_schema_preflight_ready") -> dict:
    return {
        "analysis": {
            "future_outcome_labels_used_for_atoms": False,
            "runtime_atom_schema_version": (
                PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION
            ),
            "runtime_atom_names": list(PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES),
        },
        "final_decision": {
            "status": status,
            "passed": status == "revised_context_relaxed_strict_label_atom_schema_preflight_ready",
            "primary_gap": "relaxed_strict_label_no_leak_atom_schema_preflight_passed",
            "authorized_next_work": (
                "default_off_relaxed_strict_label_atom_payload_implementation_unit_tests_only"
            ),
        },
    }


def _sensitivity_report() -> dict:
    params = {
        "progress_loss_budget_m": 0.05,
        "safety_improvement_margin": 0.0,
        "comfort_jerk_delta_budget": 0.0,
        "comfort_lateral_delta_budget": 0.0,
    }
    return {
        "final_decision": {
            "status": "revised_context_strict_label_sensitivity_diagnosed",
            "passed": True,
            "primary_gap": (
                "support_exists_but_revised_atoms_do_not_separate_relaxed_strict_label"
            ),
            "authorized_next_work": "diagnose_relaxed_strict_label_atom_bottleneck_before_replay",
        },
        "grid_summary": {
            "best_by_support": {
                "params": params,
                "class_counts": {"beneficial_alternative": 1, "harmful_alternative": 1},
            },
            "best_by_screen": {
                "params": params,
                "class_counts": {"beneficial_alternative": 1, "harmful_alternative": 1},
            },
        },
    }


def test_relaxed_strict_atom_screen_can_find_promising_no_leak_separator() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        preflight_report=_preflight_report(),
        sensitivity_report=_sensitivity_report(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_relaxed_strict_label_atom_certificate_design_only"
    )
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["future_outcome_labels_used_for_classification"] is True
    assert report["analysis"]["runtime_atom_names"] == list(
        PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES
    )
    assert all(not report["final_decision"][key] for key in report["blocked_actions"])
    assert any(row["promising_screen"] for row in report["ranked_screens"])
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_relaxed_strict_atom_screen_blocks_when_preflight_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        preflight_report=_preflight_report("unexpected_status"),
        sensitivity_report=_sensitivity_report(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_relaxed_strict_atom_schema_preflight_before_separability"
    )


def test_relaxed_strict_atom_screen_blocks_malformed_preflight_analysis() -> None:
    malformed = _preflight_report()
    malformed["analysis"] = "not_an_object"

    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        preflight_report=malformed,
        sensitivity_report=_sensitivity_report(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["preflight_gate"]["future_outcome_labels_used_for_atoms"] is None


def test_relaxed_strict_atom_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(seed=11), "context": _context(seed=11)}],
            preflight_report=_preflight_report(),
            sensitivity_report=_sensitivity_report(),
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
            fail_on_formal_seeds=True,
        )


def test_relaxed_strict_payload_features_are_outcome_independent() -> None:
    base = _record()
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    mutated["candidate_closed_loop_outcomes"][2]["mean_jerk_mps3"] = 0.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        preflight_report=_preflight_report(),
        sensitivity_report=_sensitivity_report(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        preflight_report=_preflight_report(),
        sensitivity_report=_sensitivity_report(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert (
        base_report["payload_descriptor_coverage"]
        == mutated_report["payload_descriptor_coverage"]
    )
