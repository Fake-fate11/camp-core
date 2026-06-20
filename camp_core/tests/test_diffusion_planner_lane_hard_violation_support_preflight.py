from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_lane_hard_violation_support_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _bottleneck_report(
    *,
    status: str = "progress_support_separability_bottleneck_diagnosed",
    lane_worse_count: int = 9,
    hard_violation_delta_mean: float = 0.25,
    zero_progress_support: bool = True,
) -> dict:
    contribution = 0.0 if zero_progress_support else 0.1
    return {
        "final_decision": {
            "status": status,
            "passed": status == "progress_support_separability_bottleneck_diagnosed",
            "primary_gap": "beneficial_retain_low_and_allowed_harmful_high",
            "authorized_next_work": "reject_or_design_new_progress_support_descriptor_family",
        },
        "counts": {
            "beneficial_total": 56,
            "beneficial_blocked": 30,
            "beneficial_retained": 26,
            "harmful_total": 180,
            "harmful_allowed": 41,
            "harmful_blocked": 139,
            "neutral_total": 100,
        },
        "blocked_beneficial": {
            "count": 30,
            "outcome_summary": {
                "hard_violation_delta_mean": -0.06,
                "lane_worse_count": 0,
            },
            "top_examples": [
                {
                    "candidate_index": 1,
                    "hard_violation_delta_vs_top1": 0,
                }
            ],
        },
        "allowed_harmful": {
            "count": 41,
            "outcome_summary": {
                "hard_violation_delta_mean": hard_violation_delta_mean,
                "lane_worse_count": lane_worse_count,
            },
            "descriptor_contribution_mean": {
                "atom_route_progress_deficit_envelope_v1": contribution,
                "atom_tail_speed_support_deficit_v1": 0.0,
            },
            "top_examples": [
                {
                    "candidate_index": 2,
                    "hard_violation_delta_vs_top1": hard_violation_delta_mean,
                }
            ],
        },
    }


def test_lane_hard_violation_preflight_authorizes_only_unit_tests() -> None:
    report = analyze(
        bottleneck_report=_bottleneck_report(),
        fail_on_formal_seeds=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_field_definitions"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atom_definitions"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert all(field["passed_preflight"] for field in report["logging_field_reports"])
    assert all(atom["passed_preflight"] for atom in report["atom_reports"])
    assert all(check["passed"] for check in report["math_checks"])


def test_lane_hard_violation_preflight_blocks_when_source_not_ready() -> None:
    report = analyze(
        bottleneck_report=_bottleneck_report(
            status="progress_support_descriptor_separability_rejected"
        )
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_lane_hard_violation_preflight_rejects_formal_seed_when_forbidden() -> None:
    source = _bottleneck_report()
    source["records"] = {"formal_seed_records": 1}

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            bottleneck_report=source,
            fail_on_formal_seeds=True,
        )


def test_lane_hard_violation_preflight_requires_established_lane_or_hard_gap() -> None:
    report = analyze(
        bottleneck_report=_bottleneck_report(
            lane_worse_count=0,
            hard_violation_delta_mean=0.0,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "lane_hard_violation_blind_spot_not_established"
    )


def test_lane_hard_violation_preflight_requires_zero_progress_support_blind_spot() -> None:
    report = analyze(
        bottleneck_report=_bottleneck_report(zero_progress_support=False)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "allowed_harmful_not_zero_progress_support_risk"
    )


def test_lane_hard_violation_preflight_is_outcome_example_independent() -> None:
    base = _bottleneck_report()
    mutated = copy.deepcopy(base)
    mutated["allowed_harmful"]["top_examples"][0]["hard_violation_delta_vs_top1"] = 99.0
    mutated["blocked_beneficial"]["top_examples"][0]["candidate_index"] = 7

    base_report = analyze(bottleneck_report=base)
    mutated_report = analyze(bottleneck_report=mutated)

    assert base_report["logging_field_reports"] == mutated_report["logging_field_reports"]
    assert base_report["atom_reports"] == mutated_report["atom_reports"]
    assert base_report["math_checks"] == mutated_report["math_checks"]
