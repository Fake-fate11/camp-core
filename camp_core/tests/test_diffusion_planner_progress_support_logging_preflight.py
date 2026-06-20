from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_support_logging_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _residual_report(status: str = "affine_allowed_harmful_residual_diagnosed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "affine_allowed_harmful_residual_diagnosed",
            "primary_gap": "allowed_harmful_residual_classified",
            "authorized_next_work": (
                "reject_observable_route_or_design_new_logging_preflight"
            ),
        },
        "records": {
            "formal_seed_records": 0,
        },
        "residual_allowed_harmful": {
            "count": 32,
            "dominant_primary_reason": "progress_loss",
            "primary_reason_counts": {
                "progress_loss": 24,
                "lane_violation": 6,
                "comfort_regression": 2,
            },
            "multi_label_counts": {
                "progress_loss": 24,
                "value_loss": 9,
                "comfort_regression": 9,
                "hard_violation": 6,
                "lane_violation": 6,
                "red_light_violation": 0,
            },
            "examples": [
                {
                    "primary_reason": "progress_loss",
                    "progress_delta_vs_top1_m": -1.0,
                }
            ],
        },
    }


def test_progress_support_logging_preflight_authorizes_only_unit_tests() -> None:
    report = analyze(
        affine_residual_report=_residual_report(),
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


def test_progress_support_logging_preflight_blocks_when_source_not_ready() -> None:
    report = analyze(
        affine_residual_report=_residual_report("constrained_affine_upper_bound_rejected"),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_progress_support_logging_preflight_rejects_formal_seed_when_forbidden() -> None:
    source = _residual_report()
    source["records"]["formal_seed_records"] = 1

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            affine_residual_report=source,
            fail_on_formal_seeds=True,
        )


def test_progress_support_logging_preflight_requires_progress_dominated_residual() -> None:
    source = _residual_report()
    source["residual_allowed_harmful"]["dominant_primary_reason"] = "lane_violation"

    report = analyze(affine_residual_report=source)

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS


def test_progress_support_logging_preflight_is_outcome_example_independent() -> None:
    base = _residual_report()
    mutated = copy.deepcopy(base)
    mutated["residual_allowed_harmful"]["examples"][0]["primary_reason"] = "lane_violation"
    mutated["residual_allowed_harmful"]["examples"][0]["progress_delta_vs_top1_m"] = 0.0

    base_report = analyze(affine_residual_report=base)
    mutated_report = analyze(affine_residual_report=mutated)

    assert base_report["logging_field_reports"] == mutated_report["logging_field_reports"]
    assert base_report["atom_reports"] == mutated_report["atom_reports"]
    assert base_report["math_checks"] == mutated_report["math_checks"]
