from __future__ import annotations

from typing import Any, Mapping, Sequence


FINAL_DELIVERY_SCHEMA_VERSION = "camp_dp_v25_final_delivery_evidence_v1"
FINAL_INPUT_MANIFEST_SCHEMA_VERSION = "camp_dp_v25_final_delivery_inputs_v1"
FINAL_CONTRACT_SCHEMA_VERSION = "camp_dp_v25_final_delivery_contract_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PRIMARY_ARMS = ("candidate0", "static14d", "scene14d")
MAIN_MODEL_NAMES = (
    "CAMP-Static14D",
    "CAMP-Scene14D",
    "CAMP-Static9D",
    "CAMP-Scene9D",
)
REQUIRED_ARTIFACT_ROLES = (
    "corrected_full_corpus",
    "train_only_atom_audit",
    "main_training",
    "auxiliary_static14d_full",
    "calibration_freeze",
    "power_pilot",
    "fresh_b2_preopen",
    "fresh_b2_execution",
    "fresh_b2_evaluation",
)
REQUIRED_CAMP_HEAD_ROLES = (
    "local",
    "origin_main",
    "fresh_github_main",
    "autodl",
)


def validate_v25_final_delivery_input_manifest(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the exact path/root handoff consumed by the final artifact."""

    result = _native_dict(value, "final delivery input manifest")
    expected_fields = {
        "schema_version",
        "fixed_dp_head",
        "fresh_open_count",
        "fresh_b2_opened",
        "outcome_used_to_change_protocol",
        "promotion_deployment_activation_authorized",
        "contract",
        "camp_heads",
        "artifacts",
    }
    if set(result) != expected_fields:
        raise ValueError("V25 final delivery input manifest field set drifted")
    contract = _native_dict(result["contract"], "final contract receipt")
    if (
        result["schema_version"] != FINAL_INPUT_MANIFEST_SCHEMA_VERSION
        or result["fixed_dp_head"] != FIXED_DP_HEAD
        or type(result["fresh_open_count"]) is not int
        or result["fresh_open_count"] != 1
        or result["fresh_b2_opened"] is not True
        or result["outcome_used_to_change_protocol"] is not False
        or result["promotion_deployment_activation_authorized"] is not False
        or set(contract) != {"path", "sha256"}
        or type(contract["path"]) is not str
        or not contract["path"]
    ):
        raise ValueError("V25 final delivery input manifest value drifted")
    _sha(contract["sha256"], "final delivery contract SHA")
    result["contract"] = contract
    result["camp_heads"] = _camp_heads(result["camp_heads"])
    result["artifacts"] = _artifact_registry(result["artifacts"])
    return result


def build_v25_final_delivery_evidence(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    atom_audit: Mapping[str, Any],
    training_report: Mapping[str, Any],
    training_model_reports: Mapping[str, Mapping[str, Any]],
    auxiliary_report: Mapping[str, Any],
    calibration_contract: Mapping[str, Any],
    preopen_qualification: Mapping[str, Any],
    benchmark_a: Mapping[str, Any],
    benchmark_b_evaluation: Mapping[str, Any],
    artifact_registry: Sequence[Mapping[str, Any]],
    camp_heads: Mapping[str, Any],
    fixed_dp_head: str,
    fresh_open_count: int,
) -> dict[str, Any]:
    """Assemble the single V25 final report without changing any decision.

    Scientific summaries and claim decisions are copied only from their sealed,
    independently reviewed upstream payloads.  This function does not inspect
    trajectories, rerun statistics, open Fresh B2, or infer a stronger claim.
    """

    frozen_contract = _contract(contract, contract_sha256)
    audit = _atom_audit(atom_audit)
    models = _model_reports(training_model_reports)
    training = _training_report(training_report)
    auxiliary = _auxiliary_report(auxiliary_report)
    calibration = _calibration_contract(calibration_contract)
    preopen = _preopen_qualification(preopen_qualification)
    legacy = _benchmark_a(benchmark_a)
    fresh = _benchmark_b(benchmark_b_evaluation)
    artifacts = _artifact_registry(artifact_registry)
    heads = _camp_heads(camp_heads)
    if fixed_dp_head != FIXED_DP_HEAD:
        raise ValueError("V25 final delivery fixed DP HEAD drifted")
    if type(fresh_open_count) is not int or fresh_open_count != 1:
        raise ValueError("V25 final delivery requires exactly one Fresh B2 opening")

    method_claims = {
        method: {
            "safety_improvement_claim_passed": _native_bool(
                fresh["method_reports"][method]["claim_decision"][
                    "safety_improvement_claim_passed"
                ],
                f"{method} safety claim",
            ),
            "red_light_improvement_claim_passed": _native_bool(
                fresh["method_reports"][method]["claim_decision"][
                    "red_light_improvement_claim_passed"
                ],
                f"{method} red-light claim",
            ),
            "claim_scope": fresh["method_reports"][method]["claim_decision"][
                "claim_scope"
            ],
        }
        for method in ("static14d", "scene14d")
    }
    any_safety_claim = any(
        item["safety_improvement_claim_passed"] for item in method_claims.values()
    )
    final_decision = (
        "method_specific_bounded_safety_claim_only"
        if any_safety_claim
        else "honest_no_claim"
    )
    primary_method_reports = fresh["method_reports"]
    training_table = {
        "artifact_report": training,
        "main_fair_2x2_model_reports": models,
        "auxiliary_static14d_full_report": auxiliary,
        "auxiliary_isolated_from_primary_runtime_calibration_fresh_and_claim": True,
    }
    sections = {
        "executive_claim_decision": {
            "decision": final_decision,
            "method_claims": method_claims,
            "fresh_open_count": fresh_open_count,
            "claim_scope": (
                "specific_frozen_fixed_dp_k8_signal_complete_benchmark_within_"
                "unchanged_fixed_dp_valid_k8_support_domain"
            ),
        },
        "fixed_candidate_and_mathematical_contract": frozen_contract[
            "candidate_contract"
        ],
        "fourteen_atom_scientific_audit_table": {
            "atom_schema": audit["atom_schema"],
            "status_scope": audit["status_scope"],
            "status_counts": audit["status_counts"],
            "correctness_checks": audit["correctness_checks"],
            "atom_rows": audit["atom_rows"],
            "correlation_matrix": audit["weighted_spearman_correlation_matrix"],
            "atom_delta_effective_rank": audit["atom_delta_effective_rank"],
            "ablations": audit["ablations"],
        },
        "causal_context_v2_schema_and_source_availability": {
            "contract": frozen_contract["causal_context_table"],
            "scene14d_report": models["CAMP-Scene14D"],
            "scene9d_ablation_report": models["CAMP-Scene9D"],
        },
        "controlled_scenario_source_split_and_denominator": preopen,
        "training_scales_models_convergence_stability_and_wall_clock": training_table,
        "paper_9d_and_group_ablations": {
            "static14d": models["CAMP-Static14D"],
            "scene14d": models["CAMP-Scene14D"],
            "static9d": models["CAMP-Static9D"],
            "scene9d": models["CAMP-Scene9D"],
            "atom_group_ablations": audit["ablations"],
        },
        "legacy_benchmark_a_table": legacy,
        "fresh_benchmark_b_primary_three_arm_table": {
            "arms": fresh["arms"],
            "full_plan_pair_count": fresh["full_plan_pair_count"],
            "shared_three_arm_paired_eligible_count": fresh[
                "shared_three_arm_paired_eligible_count"
            ],
            "method_reports": primary_method_reports,
        },
        "fresh_benchmark_b_signal_safety_table": {
            method: primary_method_reports[method]["signal_safety"]
            for method in ("static14d", "scene14d")
        },
        "performance_and_comfort_noninferiority": {
            "frozen_calibration_contract": calibration,
            "method_results": {
                method: _performance_noninferiority_result(
                    primary_method_reports[method]["claim_decision"], method
                )
                for method in ("static14d", "scene14d")
            },
        },
        "coverage_failure_and_candidate_pool_accounting": {
            "failure_accounting": fresh["failure_accounting"],
            "method_coverage": {
                method: primary_method_reports[method]["claim_decision"]["coverage"]
                for method in ("static14d", "scene14d")
            },
            "paired_arm_summaries": {
                method: primary_method_reports[method]["paired_arm_summaries"]
                for method in ("static14d", "scene14d")
            },
        },
        "latency_by_stage": fresh["latency_ms"],
        "artifact_roots_heads_and_reproducibility": {
            "contract_sha256": contract_sha256,
            "artifacts": artifacts,
            "camp_heads": heads,
            "fixed_dp_head": fixed_dp_head,
            "fresh_open_count": fresh_open_count,
        },
        "limitations_and_forbidden_claims": {
            "forbidden_claims": frozen_contract["forbidden_claims"],
            "benchmark_a_limits": legacy["evidence_limits"],
            "promotion_deployment_activation_authorized": False,
        },
    }
    required_sections = frozen_contract["required_sections"]
    if set(sections) != set(required_sections):
        raise ValueError("V25 final evidence section set drifted from frozen contract")
    return {
        "schema_version": FINAL_DELIVERY_SCHEMA_VERSION,
        "status": "final_evidence_assembled_from_reviewed_upstream_artifacts",
        "final_decision": final_decision,
        "method_claims": method_claims,
        "sections": sections,
        "required_sections_complete": True,
        "fresh_b2_opened_exactly_once": True,
        "outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }


def _contract(value: Mapping[str, Any], digest: str) -> dict[str, Any]:
    result = _native_dict(value, "final delivery contract")
    _sha(digest, "final delivery contract SHA")
    if (
        result.get("schema_version") != FINAL_CONTRACT_SCHEMA_VERSION
        or result.get("status") != "outcome_blind_frozen_before_fresh_b2_opening"
        or result.get("final_package_generated") is not False
        or result.get("fresh_b2_opened") is not False
        or result.get("outcome_fields_consumed") != []
        or result.get("fixed_dp_head") != FIXED_DP_HEAD
        or type(result.get("required_sections")) is not list
        or len(result["required_sections"]) != len(set(result["required_sections"]))
        or type(result.get("candidate_contract")) is not dict
        or type(result.get("causal_context_table")) is not dict
        or type(result.get("forbidden_claims")) is not list
    ):
        raise ValueError("V25 final delivery contract drifted")
    return result


def _atom_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "atom audit")
    if (
        result.get("schema_version")
        != "camp_dp_v25_train_only_atom_empirical_audit_v1"
        or result.get("atom_schema") != "dp_camp_v10_14d"
        or type(result.get("atom_rows")) is not list
        or len(result["atom_rows"]) != 14
        or type(result.get("status_counts")) is not dict
        or set(result["status_counts"]) != {"PASS", "WARN", "FAIL"}
        or sum(result["status_counts"].values()) != 14
        or result.get("fresh_or_outcome_consumed") is not False
    ):
        raise ValueError("V25 final delivery atom audit drifted")
    statuses = [row.get("status") if type(row) is dict else None for row in result["atom_rows"]]
    if any(status not in {"PASS", "WARN", "FAIL"} for status in statuses) or any(
        statuses.count(status) != result["status_counts"][status]
        for status in ("PASS", "WARN", "FAIL")
    ):
        raise ValueError("V25 final delivery atom status accounting drifted")
    return result


def _training_report(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "training report")
    if (
        result.get("schema_version")
        != "camp_dp_v25_strict_convex_training_artifact_v1"
        or result.get("status") != "passed_strict_convex_training"
        or result.get("all_models_converged") is not True
        or result.get("all_solver_status_optimal") is not True
        or result.get("fresh_b2_opened") is not False
        or result.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V25 final delivery training report drifted")
    return result


def _model_reports(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    raw = _native_dict(value, "training model reports")
    if set(raw) != set(MAIN_MODEL_NAMES):
        raise ValueError("V25 final delivery model registry drifted")
    result: dict[str, dict[str, Any]] = {}
    for name in MAIN_MODEL_NAMES:
        report = _native_dict(raw[name], name)
        expected_count = 14 if name.endswith("14D") else 9
        if (
            report.get("schema_version")
            != "camp_dp_v25_trained_selector_report_v1"
            or report.get("model_name") != name
            or report.get("converged") is not True
            or report.get("theta_column_simplex") is not True
            or report.get("selection_eligibility")
            != "source_valid_candidate_set"
            or report.get("physical_feasible_mask_consumed_by_training")
            is not False
            or report.get("runtime_projection") is not False
            or report.get("softmax") is not False
            or report.get("outcome_or_fresh_consumed") is not False
            or type(report.get("active_atom_indices")) is not list
            or report["active_atom_indices"] != list(range(expected_count))
        ):
            raise ValueError(f"V25 final delivery {name} report drifted")
        result[name] = report
    return result


def _auxiliary_report(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "auxiliary report")
    if (
        result.get("schema_version")
        != "camp_dp_v25_static14d_full_auxiliary_training_artifact_v1"
        or result.get("status") != "passed_static14d_full_auxiliary_training"
        or result.get("model_name") != "CAMP-Static14D-full"
        or result.get("eligible_for_calibration_or_fresh") is not False
        or result.get("closed_loop_outcome_consumed") is not False
        or result.get("fresh_b2_opened") is not False
    ):
        raise ValueError("V25 final delivery auxiliary report drifted")
    return result


def _calibration_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "calibration contract")
    if (
        result.get("schema_version") != "camp_dp_v25_calibration_freeze_v1"
        or result.get("status") != "calibration_freeze_passed"
        or result.get("fresh_b2_opened") is not False
        or result.get("one_time_opening_release_required") is not True
    ):
        raise ValueError("V25 final delivery calibration contract drifted")
    return result


def _preopen_qualification(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "preopen qualification")
    if (
        result.get("schema_version")
        != "camp_dp_v25_fresh_b2_preopen_qualification_v1"
        or result.get("status") not in {
            "qualified",
            "qualified_with_real_inventory_ceiling_disclosed",
        }
        or result.get("fresh_b2_opened") is not False
        or result.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V25 final delivery preopen qualification drifted")
    return result


def _benchmark_a(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "Benchmark A")
    if (
        result.get("schema_version")
        != "camp_dp_v25_legacy_benchmark_a_freeze_v1"
        or result.get("role")
        != "read_only_legacy_regression_evidence_not_fresh_confirmation"
        or result.get("holdout_open_count") != 1
        or result.get("holdout_rerun_authorized") is not False
        or result.get("methods", {}).get("static14d_v24", {}).get(
            "claim_decision"
        )
        != "honest_no_claim"
        or result.get("methods", {}).get("scene14d", {}).get("evaluated")
        is not False
    ):
        raise ValueError("V25 final delivery Benchmark A drifted")
    return result


def _benchmark_b(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _native_dict(value, "Benchmark B")
    if (
        result.get("schema_version")
        != "camp_dp_v25_fresh_b2_three_arm_evaluation_v2"
        or result.get("arms") != list(PRIMARY_ARMS)
        or result.get("fresh_b2_opened_once_after_nonce_consumption") is not True
        or result.get("failure_rows_retained_in_denominator") is not True
        or result.get("safetycost_imputed_for_failed_pairs") is not False
        or result.get("fresh_outcome_used_to_change_protocol") is not False
        or result.get("promotion_deployment_activation_authorized") is not False
        or type(result.get("method_reports")) is not dict
        or set(result["method_reports"]) != {"static14d", "scene14d"}
    ):
        raise ValueError("V25 final delivery Benchmark B drifted")
    return result


def _performance_noninferiority_result(
    claim: Mapping[str, Any], method: str
) -> dict[str, Any]:
    value = _native_dict(claim, f"{method} claim decision")
    normal = value.get("performance_comfort_noninferiority")
    if type(normal) is dict:
        return {
            "status": "computed",
            "metrics": normal,
        }
    if (
        value.get("schema_version")
        == "camp_dp_v25_fresh_b2_insufficient_evidence_no_claim_v1"
        and value.get("status")
        == "honest_no_claim_insufficient_shared_paired_evidence"
        and value.get("performance_comfort_noninferiority_available") is False
        and value.get("safety_improvement_claim_passed") is False
    ):
        return {
            "status": "unavailable_insufficient_shared_paired_evidence",
            "paired_eligible_count": value.get("paired_eligible_count"),
            "independent_cluster_count": value.get("independent_cluster_count"),
            "noninferiority_margins": value.get("noninferiority_margins"),
            "claim_passed": False,
        }
    raise ValueError(f"V25 final delivery {method} NI evidence drifted")


def _artifact_registry(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise ValueError("V25 final artifact registry must be a list")
    expected_fields = {
        "role",
        "path",
        "root_sha256",
        "review_path",
        "review_root_sha256",
    }
    result: list[dict[str, Any]] = []
    roles: list[str] = []
    for index, raw in enumerate(value):
        item = _native_dict(raw, f"artifact registry row {index}")
        if set(item) != expected_fields:
            raise ValueError("V25 final artifact registry field set drifted")
        if any(type(item[field]) is not str or not item[field] for field in expected_fields):
            raise ValueError("V25 final artifact registry contains an invalid string")
        _sha(item["root_sha256"], f"artifact {index} root")
        _sha(item["review_root_sha256"], f"artifact {index} review root")
        roles.append(item["role"])
        result.append(item)
    if len(set(roles)) != len(roles) or set(roles) != set(REQUIRED_ARTIFACT_ROLES):
        raise ValueError("V25 final artifact registry role coverage drifted")
    return result


def _camp_heads(value: Mapping[str, Any]) -> dict[str, str]:
    raw = _native_dict(value, "CAMP heads")
    if set(raw) != set(REQUIRED_CAMP_HEAD_ROLES):
        raise ValueError("V25 final CAMP head role set drifted")
    result: dict[str, str] = {}
    for role in REQUIRED_CAMP_HEAD_ROLES:
        head = raw[role]
        if type(head) is not str or len(head) != 40 or set(head) - set("0123456789abcdef"):
            raise ValueError(f"V25 final {role} CAMP HEAD is invalid")
        result[role] = head
    if len(set(result.values())) != 1:
        raise ValueError("V25 final CAMP heads are not aligned")
    return result


def _native_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a native dict")
    return dict(value)


def _native_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a native bool")
    return value


def _sha(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")
