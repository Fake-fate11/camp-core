from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_joint_screen_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _progress_report(status: str = "progress_support_separability_bottleneck_diagnosed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "progress_support_separability_bottleneck_diagnosed",
            "primary_gap": "beneficial_retain_low_and_allowed_harmful_high",
            "authorized_next_work": "reject_or_design_new_progress_support_descriptor_family",
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
        },
        "records": {"formal_seed_records": 0},
        "allowed_harmful": {
            "count": 41,
            "outcome_summary": {
                "lane_worse_count": 9,
                "hard_violation_delta_mean": 0.25,
            },
        },
        "blocked_beneficial": {"count": 30},
    }


def _lane_report(status: str = "lane_hard_violation_support_separability_bottleneck_diagnosed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status
            == "lane_hard_violation_support_separability_bottleneck_diagnosed",
            "primary_gap": (
                "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
            ),
            "authorized_next_work": (
                "reject_lane_hard_standalone_or_design_joint_progress_lane_hard_screen"
            ),
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
        },
        "source_records": {"formal_seed_records": 0},
        "screen_applications": {
            "best_high_retain_screen": {
                "counts": {
                    "beneficial_blocked": 2,
                    "beneficial_retained": 54,
                    "harmful_allowed": 156,
                    "harmful_blocked": 24,
                },
                "allowed_harmful": {
                    "reason_counts": {
                        "progress_loss": 138,
                        "outcome_value_loss": 108,
                        "lane_worse": 1,
                    }
                },
            },
            "best_strict_safe_screen": {
                "counts": {
                    "beneficial_blocked": 55,
                    "beneficial_retained": 1,
                    "harmful_allowed": 0,
                    "harmful_blocked": 180,
                }
            },
        },
    }


def test_joint_screen_preflight_authorizes_only_cologged_plan() -> None:
    report = analyze(
        progress_bottleneck_report=_progress_report(),
        lane_hard_bottleneck_report=_lane_report(),
        fail_on_formal_seeds=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    evidence = report["complementarity_evidence"]
    assert evidence["complementary_blind_spots_established"] is True
    assert evidence["lane_hard_high_retain_progress_loss_harmful"] == 138
    assert report["analysis"]["future_outcome_labels_used_for_descriptor_definitions"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert "not claimed to be classical Benders" in report["analysis"]["math_boundary"]


def test_joint_screen_preflight_blocks_when_progress_source_not_ready() -> None:
    report = analyze(
        progress_bottleneck_report=_progress_report(
            "progress_support_descriptor_separability_rejected"
        ),
        lane_hard_bottleneck_report=_lane_report(),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_joint_screen_preflight_rejects_when_complementarity_missing() -> None:
    lane = _lane_report()
    lane["screen_applications"]["best_high_retain_screen"]["allowed_harmful"][
        "reason_counts"
    ] = {"lane_worse": 1}

    report = analyze(
        progress_bottleneck_report=_progress_report(),
        lane_hard_bottleneck_report=lane,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "lane_hard_high_retain_progress_harmful_gap_not_established"
    )


def test_joint_screen_preflight_rejects_formal_seed_when_forbidden() -> None:
    progress = _progress_report()
    progress["records"]["formal_seed_records"] = 1

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            progress_bottleneck_report=progress,
            lane_hard_bottleneck_report=_lane_report(),
            fail_on_formal_seeds=True,
        )


def test_joint_screen_preflight_ignores_outcome_examples_for_design() -> None:
    base = _lane_report()
    mutated = copy.deepcopy(base)
    mutated["screen_applications"]["best_high_retain_screen"]["allowed_harmful"][
        "top_examples"
    ] = [{"candidate_index": 99, "outcome_value_delta_vs_top1": -999.0}]

    base_report = analyze(
        progress_bottleneck_report=_progress_report(),
        lane_hard_bottleneck_report=base,
    )
    mutated_report = analyze(
        progress_bottleneck_report=_progress_report(),
        lane_hard_bottleneck_report=mutated,
    )

    assert (
        base_report["complementarity_evidence"]
        == mutated_report["complementarity_evidence"]
    )
    assert base_report["analysis"] == mutated_report["analysis"]
