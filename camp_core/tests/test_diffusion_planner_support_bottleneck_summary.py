from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_support_bottleneck import (
    build_report,
    render_markdown,
)


def _decision(status: str, reasons: list[str] | None = None) -> dict[str, object]:
    return {
        "status": status,
        "reasons": reasons or [status],
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
    }


def _support_quality(status: str = "no_leak_guarded_candidate_support_insufficient"):
    return {
        "analysis": {"name": "dp_candidate_support_quality_v1"},
        "records": {"total_records": 100},
        "support_diagnosis": {
            "dense_lane_change": {
                "oracle_outcome_nonregressing_improvement_rate": 0.5,
                "strict_guarded_improvement_rate": 0.0,
            }
        },
        "final_decision": _decision(status),
    }


def _descriptor_screen(status: str = "descriptor_only_offline_screen_rejected"):
    return {
        "analysis": {"name": "dp_descriptor_only_offline_selector_screen_v1"},
        "records": {"total_records": 100},
        "final_decision": _decision(status),
    }


def _materiality_gap(status: str = "postprocess_or_tracker_descriptor_gap_present"):
    return {
        "analysis": {"name": "dp_camp_materiality_gap_v1"},
        "records": {"nonfallback": 100, "with_oracle_donor": 60, "total": 120},
        "rates": {
            "raw_jerk_proxy_improvement_rate": 0.8,
            "tracker_jerk_proxy_improvement_rate": 0.4,
            "rollout_h3_jerk_improvement_rate": 0.5,
        },
        "final_decision": _decision(status),
    }


def _postprocess_tracker(
    status: str = "postprocess_tracker_descriptor_signal_insufficient",
):
    return {
        "analysis": {"name": "dp_camp_postprocess_tracker_descriptor_audit_v1"},
        "records": {
            "total": 120,
            "raw_gain_donor_rows": 60,
            "preserved_rows": 4,
            "flipped_rows": 56,
        },
        "final_decision": {
            **_decision(status),
            "top_descriptor": {
                "key": "rollout_h3_max_vector_jerk_mps3_delta",
                "standardized_abs_difference": 0.6,
            },
        },
    }


def test_support_bottleneck_summary_rejects_current_selector_calibration() -> None:
    report = build_report(
        support_quality=_support_quality(),
        descriptor_screen=_descriptor_screen(),
        materiality_gap=_materiality_gap(),
        postprocess_tracker=_postprocess_tracker(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_fixed_dp_selector_calibration_exhausted"
    assert "descriptor_only_screen_rejected" in decision["reasons"]
    assert decision["online_selector_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert report["metrics"]["postprocess_preserved_rate"] == 4 / 60

    markdown = render_markdown(report)
    assert "Support Bottleneck Synthesis" in markdown
    assert "not run DP" in markdown
    assert "not classical Benders decomposition" in markdown
    assert "DP-side Benders subproblem" in markdown


def test_support_bottleneck_summary_is_inconclusive_on_status_mismatch() -> None:
    report = build_report(
        support_quality=_support_quality(
            status="no_leak_guarded_candidate_support_present"
        ),
        descriptor_screen=_descriptor_screen(),
        materiality_gap=_materiality_gap(),
        postprocess_tracker=_postprocess_tracker(),
    )

    decision = report["final_decision"]
    assert decision["status"] == "support_bottleneck_synthesis_inconclusive"
    assert decision["status_failures"][0]["artifact"] == "support_quality"
    assert decision["closed_loop_smoke_authorized"] is False
