from __future__ import annotations

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_progress_support_separability_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


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


def _payload(risks: list[float]) -> dict:
    candidates = len(risks)
    support_steps = 3
    atoms = [
        [risk] + [0.0] * (len(PROGRESS_SUPPORT_ATOM_NAMES) - 1)
        for risk in risks
    ]
    return {
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
        "candidate_route_progress_s_profile_m": [
            [0.0, 1.0, 2.0 - risk] for risk in risks
        ],
        "candidate_plan_arc_length_profile_m": [
            [0.0, 1.0, 2.0] for _ in risks
        ],
        "candidate_speed_profile_mps": [[10.0, 10.0] for _ in risks],
        "candidate_route_remaining_m": [5.0 + risk for risk in risks],
        "candidate_goal_alignment_progress_m": [2.0 - risk for risk in risks],
        "progress_support_atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
        "progress_support_atoms": atoms,
        "latency_ms": {key: 0.1 for key in PROGRESS_SUPPORT_LATENCY_KEYS},
    }


def _record(risks: list[float], outcomes: list[dict]) -> dict:
    return {
        "num_candidates": len(risks),
        "seed": 1,
        "progress_support_logging": _payload(risks),
        "candidate_closed_loop_outcomes": outcomes,
    }


def _separability_report(status: str = "progress_support_descriptor_separability_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "progress_support_descriptors_do_not_separate_candidates",
            "authorized_next_work": "diagnose_progress_support_descriptor_bottleneck_before_retraining",
        },
        "failure_gap": {
            "best_screen": {
                "screen_name": "atom_route_progress_deficit_envelope_v1:allow_low",
                "descriptor_names": ["atom_route_progress_deficit_envelope_v1"],
                "coefficients": {"atom_route_progress_deficit_envelope_v1": 1.0},
                "threshold": 1.0,
                "promising_screen": False,
            }
        },
    }


def test_progress_support_bottleneck_diagnoses_blocked_beneficial_and_allowed_harmful() -> None:
    items = [
        {
            "raw": _record(
                [0.0, 0.1, 3.0],
                [_outcome(0.0), _outcome(2.0), _outcome(-2.0)],
            ),
            "context": {"log_path": "/tmp/a/camp_selection_log.json", "record_index": 0},
        },
        {
            "raw": _record(
                [0.0, 2.0, 0.1],
                [_outcome(0.0), _outcome(2.0), _outcome(-2.0)],
            ),
            "context": {"log_path": "/tmp/b/camp_selection_log.json", "record_index": 0},
        },
    ]

    report = analyze_records(items, separability_report=_separability_report())

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["counts"]["beneficial_blocked"] == 1
    assert report["counts"]["harmful_allowed"] == 1
    assert report["diagnosis"]["primary_gap"] == (
        "beneficial_retain_low_and_allowed_harmful_high"
    )
    assert report["blocked_beneficial"]["count"] == 1
    assert report["allowed_harmful"]["count"] == 1
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False


def test_progress_support_bottleneck_blocks_when_source_not_rejected() -> None:
    report = analyze_records(
        [
            {
                "raw": _record(
                    [0.0, 0.1],
                    [_outcome(0.0), _outcome(2.0)],
                ),
                "context": {
                    "log_path": "/tmp/a/camp_selection_log.json",
                    "record_index": 0,
                },
            }
        ],
        separability_report=_separability_report(
            "progress_support_descriptor_separability_promising_for_certificate_design"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_progress_support_separability_source_before_diagnosis"
    )
