from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_next_design_gate import (
    build_report,
    render_markdown,
)


def _support_bottleneck(status: str = "current_fixed_dp_selector_calibration_exhausted"):
    return {
        "analysis": {"name": "dp_camp_support_bottleneck_synthesis_v1"},
        "final_decision": {"status": status},
    }


def _dp_prior_completion(status: str = "score_schema_gap_not_candidate_support_limit"):
    return {
        "analysis": {"name": "dp_prior_completion_joint_atom_audit_v1"},
        "final_decision": {"status": status},
        "ranked_candidates": [
            {
                "alpha": 0.0,
                "beta": 0.02,
                "bucket_failure_count": 3,
                "passed_joint_screen": False,
                "safety_delta_ci95_high": -0.006,
            }
        ],
    }


def _candidate_generation_controls():
    return {
        "analysis": {"name": "dp_candidate_generation_controls_audit_v1"},
        "admissibility": {
            "official_guidance_available": True,
            "prototype_support_available": True,
            "guidance_can_only_be_next_gate_if_default_off": True,
            "dp_source_modification_required": False,
            "camp_atom_schema_change_required": False,
        },
        "next_gate": {
            "decision": "predeclare_default_off_guidance_candidate_set_diagnostic"
        },
    }


def _spatial_report(endpoint_mean: float = 0.02, mode_mean: float = 1.0):
    return {
        "analysis": {"name": "dp_camp_candidate_spatial_diversity_v1"},
        "records": {"total": 100, "nonfallback": 90},
        "screens": [
            {
                "name": "balanced",
                "group_summaries": {
                    "all": {
                        "endpoint_pairwise_mean_m": {"mean": endpoint_mean},
                        "mode_count": {"mean": mode_mean},
                    }
                },
                "spatial_bottleneck_evidence": {
                    "global_low_diversity_evidence": True
                },
            }
        ],
    }


def test_next_design_preflight_keeps_only_conditional_new_paths() -> None:
    report = build_report(
        support_bottleneck=_support_bottleneck(),
        dp_prior_completion=_dp_prior_completion(),
        candidate_generation_controls=_candidate_generation_controls(),
        spatial_diversity={
            "k8": _spatial_report(),
            "k16": _spatial_report(endpoint_mean=0.03),
        },
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "next_design_preflight_has_conditional_paths"
    assert "current_descriptor_threshold_or_reweighting" in decision["rejected_paths"]
    assert "dp_prior_completion_atom_schema" in decision["rejected_paths"]
    assert "simple_k_noise_or_same_mode_generator" in decision["rejected_paths"]
    assert "materially_new_no_leak_atom_schema" in decision["conditional_paths"]
    assert "new_mode_seeking_candidate_generation" in decision["conditional_paths"]
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False

    markdown = render_markdown(report)
    assert "Next Design Gate Preflight" in markdown
    assert "not classical Benders decomposition" in markdown


def test_next_design_preflight_is_inconclusive_without_source_artifacts() -> None:
    report = build_report(
        support_bottleneck=_support_bottleneck(status="unexpected"),
    )

    routes = {route["name"]: route for route in report["design_routes"]}
    assert routes["dp_prior_completion_atom_schema"]["status"] == "inconclusive"
    assert routes["simple_k_noise_or_same_mode_generator"]["status"] == "inconclusive"
    assert report["final_decision"]["status"] == "next_design_preflight_inconclusive"
