from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_final_delivery import (
    FIXED_DP_HEAD,
    FINAL_INPUT_MANIFEST_SCHEMA_VERSION,
    MAIN_MODEL_NAMES,
    REQUIRED_ARTIFACT_ROLES,
    build_v25_final_delivery_evidence,
    validate_v25_final_delivery_input_manifest,
)


SHA = "1" * 64
HEAD = "2" * 40


def _contract() -> dict:
    sections = [
        "executive_claim_decision",
        "fixed_candidate_and_mathematical_contract",
        "fourteen_atom_scientific_audit_table",
        "causal_context_v2_schema_and_source_availability",
        "controlled_scenario_source_split_and_denominator",
        "training_scales_models_convergence_stability_and_wall_clock",
        "paper_9d_and_group_ablations",
        "legacy_benchmark_a_table",
        "fresh_benchmark_b_primary_three_arm_table",
        "fresh_benchmark_b_signal_safety_table",
        "performance_and_comfort_noninferiority",
        "coverage_failure_and_candidate_pool_accounting",
        "latency_by_stage",
        "artifact_roots_heads_and_reproducibility",
        "limitations_and_forbidden_claims",
    ]
    return {
        "schema_version": "camp_dp_v25_final_delivery_contract_v1",
        "status": "outcome_blind_frozen_before_fresh_b2_opening",
        "final_package_generated": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "fixed_dp_head": FIXED_DP_HEAD,
        "required_sections": sections,
        "candidate_contract": {"candidate_count": 8},
        "causal_context_table": {"schema_version": "camp_dp_v25_causal_context_raw_v2"},
        "forbidden_claims": ["real_world_road_safety", "deployment"],
    }


def _atom_audit() -> dict:
    return {
        "schema_version": "camp_dp_v25_train_only_atom_empirical_audit_v1",
        "atom_schema": "dp_camp_v10_14d",
        "status_scope": "train_only",
        "status_counts": {"PASS": 12, "WARN": 2, "FAIL": 0},
        "correctness_checks": {"finite": {"status": "PASS"}},
        "atom_rows": [
            {"index": index, "status": "PASS" if index < 12 else "WARN"}
            for index in range(14)
        ],
        "weighted_spearman_correlation_matrix": [[1.0]],
        "atom_delta_effective_rank": 8,
        "ablations": {"paper_9d": {"selected_index_flip_rate": 0.2}},
        "fresh_or_outcome_consumed": False,
    }


def _model(name: str) -> dict:
    count = 14 if name.endswith("14D") else 9
    return {
        "schema_version": "camp_dp_v25_trained_selector_report_v1",
        "model_name": name,
        "active_atom_indices": list(range(count)),
        "converged": True,
        "theta_column_simplex": True,
        "selection_eligibility": "source_valid_candidate_set",
        "physical_feasible_mask_consumed_by_training": False,
        "runtime_projection": False,
        "softmax": False,
        "context_source_complete_weighted_fraction": [1.0] * 26,
        "outcome_or_fresh_consumed": False,
    }


def _inputs(*, safety_claim: bool = False) -> dict:
    claim = {
        "safety_improvement_claim_passed": safety_claim,
        "red_light_improvement_claim_passed": False,
        "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
        "performance_comfort_noninferiority": {"progress": {"passed": True}},
        "coverage": {"passed": True},
    }
    method = {
        "claim_decision": claim,
        "signal_safety": {"red_light_violation_rate": {}},
        "paired_arm_summaries": {"candidate0": {}, "method": {}},
    }
    return {
        "contract": _contract(),
        "contract_sha256": SHA,
        "atom_audit": _atom_audit(),
        "training_report": {
            "schema_version": "camp_dp_v25_strict_convex_training_artifact_v1",
            "status": "passed_strict_convex_training",
            "all_models_converged": True,
            "all_solver_status_optimal": True,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
        "training_model_reports": {name: _model(name) for name in MAIN_MODEL_NAMES},
        "auxiliary_report": {
            "schema_version": "camp_dp_v25_static14d_full_auxiliary_training_artifact_v1",
            "status": "passed_static14d_full_auxiliary_training",
            "model_name": "CAMP-Static14D-full",
            "eligible_for_calibration_or_fresh": False,
            "closed_loop_outcome_consumed": False,
            "fresh_b2_opened": False,
        },
        "calibration_contract": {
            "schema_version": "camp_dp_v25_calibration_freeze_v1",
            "status": "calibration_freeze_passed",
            "fresh_b2_opened": False,
            "one_time_opening_release_required": True,
        },
        "preopen_qualification": {
            "schema_version": "camp_dp_v25_fresh_b2_preopen_qualification_v1",
            "status": "qualified_with_real_inventory_ceiling_disclosed",
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
            "zero_overlap_receipt": {"status": "passed"},
        },
        "benchmark_a": {
            "schema_version": "camp_dp_v25_legacy_benchmark_a_freeze_v1",
            "role": "read_only_legacy_regression_evidence_not_fresh_confirmation",
            "holdout_open_count": 1,
            "holdout_rerun_authorized": False,
            "methods": {
                "static14d_v24": {"claim_decision": "honest_no_claim"},
                "scene14d": {"evaluated": False},
            },
            "evidence_limits": {"real_world_safety_supported": False},
        },
        "benchmark_b_evaluation": {
            "schema_version": "camp_dp_v25_fresh_b2_three_arm_evaluation_v2",
            "arms": ["candidate0", "static14d", "scene14d"],
            "fresh_b2_opened_once_after_nonce_consumption": True,
            "full_plan_pair_count": 100,
            "shared_three_arm_paired_eligible_count": 98,
            "method_reports": {
                "static14d": copy.deepcopy(method),
                "scene14d": copy.deepcopy(method),
            },
            "failure_accounting": {"full_plan_arm_run_count": 300},
            "latency_ms": {"candidate0": {}, "static14d": {}, "scene14d": {}},
            "failure_rows_retained_in_denominator": True,
            "safetycost_imputed_for_failed_pairs": False,
            "fresh_outcome_used_to_change_protocol": False,
            "promotion_deployment_activation_authorized": False,
        },
        "artifact_registry": [
            {
                "role": role,
                "path": f"/root/autodl-tmp/{role}",
                "root_sha256": SHA,
                "review_path": f"/root/autodl-tmp/{role}_review",
                "review_root_sha256": SHA,
            }
            for role in REQUIRED_ARTIFACT_ROLES
        ],
        "camp_heads": {
            "local": HEAD,
            "origin_main": HEAD,
            "fresh_github_main": HEAD,
            "autodl": HEAD,
        },
        "fixed_dp_head": FIXED_DP_HEAD,
        "fresh_open_count": 1,
    }


def _input_manifest() -> dict:
    values = _inputs()
    return {
        "schema_version": FINAL_INPUT_MANIFEST_SCHEMA_VERSION,
        "fixed_dp_head": FIXED_DP_HEAD,
        "fresh_open_count": 1,
        "fresh_b2_opened": True,
        "outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
        "contract": {
            "path": "configs/integrations/diffusion_planner_v25_final_delivery_contract_v1.json",
            "sha256": SHA,
        },
        "camp_heads": values["camp_heads"],
        "artifacts": values["artifact_registry"],
    }


def test_final_delivery_assembles_all_frozen_sections_and_honest_no_claim() -> None:
    result = build_v25_final_delivery_evidence(**_inputs())
    assert result["final_decision"] == "honest_no_claim"
    assert result["required_sections_complete"] is True
    assert result["fresh_b2_opened_exactly_once"] is True
    assert set(result["sections"]) == set(_contract()["required_sections"])
    assert result["sections"]["legacy_benchmark_a_table"]["methods"][
        "static14d_v24"
    ]["claim_decision"] == "honest_no_claim"
    assert result["sections"]["latency_by_stage"] == {
        "candidate0": {},
        "static14d": {},
        "scene14d": {},
    }


def test_final_delivery_preserves_method_specific_claim_without_broadening() -> None:
    values = _inputs(safety_claim=True)
    values["benchmark_b_evaluation"]["method_reports"]["scene14d"][
        "claim_decision"
    ]["safety_improvement_claim_passed"] = False
    result = build_v25_final_delivery_evidence(**values)
    assert result["final_decision"] == "method_specific_bounded_safety_claim_only"
    assert result["method_claims"]["static14d"][
        "safety_improvement_claim_passed"
    ] is True
    assert result["method_claims"]["scene14d"][
        "safety_improvement_claim_passed"
    ] is False
    assert result["promotion_deployment_activation_authorized"] is False


def test_final_delivery_preserves_insufficient_support_honest_no_claim() -> None:
    values = _inputs()
    insufficient = {
        "schema_version": "camp_dp_v25_fresh_b2_insufficient_evidence_no_claim_v1",
        "status": "honest_no_claim_insufficient_shared_paired_evidence",
        "paired_eligible_count": 0,
        "independent_cluster_count": 0,
        "minimum_required_paired_count": 2,
        "minimum_required_independent_cluster_count": 2,
        "coverage": {"passed": False},
        "component_regression_margins": {},
        "noninferiority_margins": {"progress": 1.0},
        "safetycost_imputed": False,
        "total_safety_inference_available": False,
        "component_inference_available": False,
        "performance_comfort_noninferiority_available": False,
        "safety_improvement_claim_passed": False,
        "red_light_improvement_claim_passed": False,
        "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
        "real_world_or_all_map_claim_authorized": False,
    }
    for method in ("static14d", "scene14d"):
        values["benchmark_b_evaluation"]["method_reports"][method][
            "claim_decision"
        ] = copy.deepcopy(insufficient)
    result = build_v25_final_delivery_evidence(**values)
    assert result["final_decision"] == "honest_no_claim"
    ni = result["sections"]["performance_and_comfort_noninferiority"][
        "method_results"
    ]
    assert ni["static14d"]["status"] == (
        "unavailable_insufficient_shared_paired_evidence"
    )
    assert ni["scene14d"]["claim_passed"] is False


def test_final_delivery_input_manifest_freezes_heads_roots_and_one_opening() -> None:
    result = validate_v25_final_delivery_input_manifest(_input_manifest())
    assert result["fresh_open_count"] == 1
    assert result["fresh_b2_opened"] is True
    assert set(row["role"] for row in result["artifacts"]) == set(
        REQUIRED_ARTIFACT_ROLES
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fresh_open_count", 0),
        ("fresh_b2_opened", False),
        ("outcome_used_to_change_protocol", True),
        ("promotion_deployment_activation_authorized", True),
    ],
)
def test_final_delivery_input_manifest_rejects_opening_or_protocol_drift(
    field: str, value: object
) -> None:
    manifest = _input_manifest()
    manifest[field] = value
    with pytest.raises(ValueError, match="value drifted"):
        validate_v25_final_delivery_input_manifest(manifest)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("fresh_count", "exactly one Fresh"),
        ("heads", "not aligned"),
        ("missing_artifact", "role coverage"),
        ("extra_artifact", "role coverage"),
        ("auxiliary", "auxiliary report drifted"),
        ("model_projection", "Scene14D report drifted"),
        ("physical_eligibility", "Scene14D report drifted"),
        ("missing_section", "section set drifted"),
    ],
)
def test_final_delivery_fails_closed_on_authority_or_role_drift(
    mutation: str, match: str
) -> None:
    values = _inputs()
    if mutation == "fresh_count":
        values["fresh_open_count"] = 2
    elif mutation == "heads":
        values["camp_heads"]["autodl"] = "3" * 40
    elif mutation == "missing_artifact":
        values["artifact_registry"].pop()
    elif mutation == "extra_artifact":
        values["artifact_registry"].append(
            {
                "role": "unregistered_extra_evidence",
                "path": "/sealed/extra",
                "root_sha256": "e" * 64,
                "review_path": "/sealed/extra-review",
                "review_root_sha256": "f" * 64,
            }
        )
    elif mutation == "auxiliary":
        values["auxiliary_report"]["eligible_for_calibration_or_fresh"] = True
    elif mutation == "model_projection":
        values["training_model_reports"]["CAMP-Scene14D"]["runtime_projection"] = True
    elif mutation == "physical_eligibility":
        values["training_model_reports"]["CAMP-Scene14D"][
            "physical_feasible_mask_consumed_by_training"
        ] = True
    elif mutation == "missing_section":
        values["contract"]["required_sections"].pop()
    with pytest.raises(ValueError, match=match):
        build_v25_final_delivery_evidence(**values)
