from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_logging_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _joint_bottleneck_report(
    status: str = "progress_lane_hard_joint_separability_bottleneck_diagnosed",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status
            == "progress_lane_hard_joint_separability_bottleneck_diagnosed",
            "primary_gap": (
                "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
            ),
            "authorized_next_work": (
                "reject_current_joint_support_descriptor_family_or_preflight_new_default_off_state_logging"
            ),
        },
        "formal_seed_records": 0,
        "counts": {
            "beneficial_total": 56,
            "beneficial_retained": 1,
            "beneficial_blocked": 55,
            "harmful_total": 180,
            "harmful_allowed": 0,
        },
        "diagnosis": {
            "primary_gap": (
                "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
            ),
            "best_screen_name": "atom_lateral_divergence_growth_v1:allow_low",
            "strict_safe_screen_count": 51,
            "high_retain_screen_count": 11,
            "camp_retraining_recommended": False,
        },
        "screen_tradeoff": {
            "best_high_retain_screen": {
                "screen_name": "atom_tail_speed_support_deficit_v1:allow_low",
                "beneficial_retain_rate": 0.75,
                "harmful_block_rate": 0.6722222222222223,
                "allowed_harmful_rate": 0.3597560975609756,
            }
        },
        "blocked_beneficial": {
            "count": 55,
            "dominant_contribution_family_counts": {
                "lane_hard_support": 55,
            },
            "reason_counts": {
                "beneficial_or_neutral_support_overlap": 55,
            },
            "top_examples": [
                {
                    "outcome_value_delta_vs_top1": 1.0,
                    "progress_delta_vs_top1_m": 0.0,
                }
            ],
        },
    }


def test_context_logging_preflight_authorizes_only_unit_tests() -> None:
    report = analyze(
        joint_bottleneck_report=_joint_bottleneck_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_field_definitions"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atom_definitions"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert all(field["passed_preflight"] for field in report["logging_field_reports"])
    assert all(atom["passed_preflight"] for atom in report["atom_reports"])
    assert all(check["passed"] for check in report["math_checks"])


def test_context_logging_preflight_blocks_when_source_not_ready() -> None:
    report = analyze(
        joint_bottleneck_report=_joint_bottleneck_report(
            "progress_lane_hard_joint_descriptor_separability_rejected"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_context_logging_preflight_rejects_formal_seed_when_forbidden() -> None:
    source = _joint_bottleneck_report()
    source["formal_seed_records"] = 1

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            joint_bottleneck_report=source,
            fail_on_formal_seeds=True,
        )


def test_context_logging_preflight_requires_lane_dominated_blocked_beneficial() -> None:
    source = _joint_bottleneck_report()
    source["blocked_beneficial"]["dominant_contribution_family_counts"] = {
        "progress_support": 55,
    }

    report = analyze(joint_bottleneck_report=source)

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS


def test_context_logging_preflight_is_outcome_example_independent() -> None:
    base = _joint_bottleneck_report()
    mutated = copy.deepcopy(base)
    mutated["blocked_beneficial"]["top_examples"][0]["outcome_value_delta_vs_top1"] = -99.0
    mutated["blocked_beneficial"]["top_examples"][0]["progress_delta_vs_top1_m"] = -99.0

    base_report = analyze(joint_bottleneck_report=base)
    mutated_report = analyze(joint_bottleneck_report=mutated)

    assert base_report["logging_field_reports"] == mutated_report["logging_field_reports"]
    assert base_report["atom_reports"] == mutated_report["atom_reports"]
    assert base_report["math_checks"] == mutated_report["math_checks"]
