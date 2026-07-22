from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .diffusion_planner_v25_calibration import (
    COMPONENT_REGRESSION_MARGINS,
    NONINFERIORITY_ENGINEERING_MARGINS,
    NONINFERIORITY_MARGIN_UNITS,
    SAFETY_COMPONENT_NATIVE_FIELDS,
    SAFETY_COST_COMPONENT_WEIGHTS,
)
from .diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    SAFETY_COMPONENTS,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_preregistration_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PRIMARY_ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)
PAPER_SUBSET_ABLATIONS = ("camp_static9d", "camp_scene9d_no_v2i")
ROOT_ROLES = (
    "training",
    "training_review",
    "atom_audit",
    "atom_audit_review",
    "map",
    "map_review",
    "base_plan",
    "base_plan_review",
    "paired_plan",
    "paired_plan_review",
    "route",
    "route_review",
    "runtime",
    "runtime_review",
)
LATENCY_FIELDS = (
    "default_inference",
    "candidate_inference",
    "atom_materialization",
    "context",
    "scene_weight",
    "selector",
    "tracker",
    "hook_total",
    "total_planning",
)


def freeze_paired_calibration_preregistration(
    *,
    root_artifacts: Mapping[str, Mapping[str, str]],
    zero_overlap_receipt: Mapping[str, Any],
    model_authority: Mapping[str, str],
) -> dict[str, Any]:
    roots = _root_artifacts(root_artifacts)
    overlap = _zero_overlap(zero_overlap_receipt)
    models = _model_authority(model_authority)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "paired_calibration_preregistered_fresh_closed",
        "fixed_dp_head": FIXED_DP_HEAD,
        "root_artifacts": roots,
        "zero_overlap_receipt": overlap,
        "model_authority": models,
        "primary_arms": list(PRIMARY_ARMS),
        "paper_subset_ablations": list(PAPER_SUBSET_ABLATIONS),
        "main_method_dimension": 14,
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate0_called_native_ranked_top1": False,
        "sequential_fixed_k8": True,
        "candidate_tensor_modified": False,
        "trajectory_postprocess_authorized": False,
        "independent_reset_per_arm": True,
        "same_initial_state_and_exogenous_schedule_per_pair": True,
        "pair_count": 100,
        "arm_run_count": 300,
        "ticks_per_arm_run": 64,
        "total_tick_capacity": 19_200,
        "map_count": 5,
        "intersection_count": 5,
        "corridor_count": 5,
        "route_count": 50,
        "seed_count": 2,
        "seeds": [25301, 25302],
        "seeds_or_ticks_counted_as_independent": False,
        "cluster_hierarchy": [
            "source_family",
            "map",
            "intersection",
            "corridor",
            "route_family",
            "semantic_parameter_block",
        ],
        "primary": {
            "safety_cost": "total",
            "components": list(SAFETY_COMPONENTS),
            "component_weights": dict(SAFETY_COST_COMPONENT_WEIGHTS),
            "native_component_fields": dict(SAFETY_COMPONENT_NATIVE_FIELDS),
            "operational_overspeed_tolerance_mps": 0.1,
            "speed_margin_atoms_mps": [0.0, 0.5, 1.0],
        },
        "noninferiority": {
            "metrics": list(NONINFERIORITY_METRICS),
            "estimator": "one_sided_95_percent_upper_equal_mass_cluster_mean_student_t",
            "harm_delta_contract": "method_minus_candidate0_positive_is_worse",
            "margins": dict(NONINFERIORITY_ENGINEERING_MARGINS),
            "margin_units": dict(NONINFERIORITY_MARGIN_UNITS),
            "all_metrics_must_pass": True,
            "multiplicity": "intersection_union_no_adjustment",
            "margin_source": "preregistered_engineering_acceptability_not_outcome_tuned",
        },
        "component_guardrails": {
            "estimator": "one_sided_95_percent_upper_equal_mass_cluster_mean_student_t",
            "margins": dict(COMPONENT_REGRESSION_MARGINS),
            "all_components_must_pass": True,
        },
        "paired_statistics": {
            "cluster_estimator": "equal_mass_cluster_mean_student_t",
            "confidence_level": 0.95,
            "better_tie_worse_tolerance": 1e-12,
            "comparisons": [
                "camp_static14d_minus_candidate0",
                "camp_scene14d_no_v2i_minus_candidate0",
            ],
            "calibration_is_descriptive_not_safety_confirmation": True,
            "fresh_claim_thresholds_tuned_from_calibration": False,
        },
        "coverage": {
            "planned_pair_denominator": 100,
            "minimum_overall_paired_eligible_rate": 0.95,
            "minimum_family_and_source_rate_exclusive": 0.90,
            "minimum_family_tier_rate_exclusive": 0.80,
            "all_failures_retained": True,
            "complete_case_filtering": False,
            "replacement_or_imputation": False,
        },
        "scene_context": {
            "schema": "dp_camp_v25_context_v2",
            "raw_dimension": 26,
            "phase_remaining_available": False,
            "phase_remaining_available_count_required": 0,
            "same_tick_current_phase_allowed": True,
            "v2i_enabled": False,
            "runtime_projection": False,
            "softmax": False,
            "theta_column_simplex": True,
            "weight_nonnegative_simplex": True,
            "score_affine": True,
        },
        "atom_calibration": {
            "approved_atom_count": 14,
            "paper_subset_indices": list(range(9)),
            "required_statistics": [
                "source_coverage",
                "zero_rate",
                "positive_rate",
                "k8_range",
                "k8_variance",
                "q05",
                "q50",
                "q95",
                "q99",
                "clip_saturation",
                "scale_drift",
                "selected_index_impact",
            ],
            "weak_support_deletes_atom": False,
            "red_without_legal_source": "unavailable_masked_not_continuous_floor",
        },
        "numerical_layout_sensitivity": {
            "official_layout": "frozen_producer_einsum_accumulation_layout",
            "diagnostic_layout": "mathematically_equivalent_alternate_accumulation",
            "formal_results_use_diagnostic_layout": False,
            "required_outputs": [
                "score_margin",
                "lowest_index_tie_count",
                "selected_flip_count",
                "selected_flip_rate",
            ],
        },
        "latency": {
            "fields": list(LATENCY_FIELDS),
            "statistics": ["mean", "median", "p95", "p99", "max"],
            "selector_and_k8_system_overhead_reported_separately": True,
        },
        "power": {
            "prospective_before_fresh": True,
            "variance_source": "reviewed_calibration_cluster_variance",
            "independent_units": ["map", "intersection", "corridor", "route"],
            "reported": [
                "safety_cost_total_mde",
                "red_component_mde",
                "expected_ci_width",
                "assumptions",
            ],
            "seeds_or_ticks_inflate_independence": False,
        },
        "training_or_model_parameter_change_authorized": False,
        "calibration_result_driven_protocol_change_authorized": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "fresh_open_authorized": False,
        "promotion_or_deployment_authorized": False,
    }


def validate_paired_calibration_preregistration(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("paired calibration preregistration must be a mapping")
    try:
        expected = freeze_paired_calibration_preregistration(
            root_artifacts=value["root_artifacts"],
            zero_overlap_receipt=value["zero_overlap_receipt"],
            model_authority=value["model_authority"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("paired calibration preregistration structure drifted") from exc
    if not _strict_equal(value, expected):
        raise ValueError("paired calibration preregistration differs from freeze")
    return expected


def _root_artifacts(
    value: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or set(value) != set(ROOT_ROLES):
        raise ValueError("paired calibration root role set drifted")
    result: dict[str, dict[str, str]] = {}
    for role in ROOT_ROLES:
        binding = value[role]
        if type(binding) is not dict or set(binding) != {"path", "root_sha256"}:
            raise ValueError(f"paired calibration {role} binding drifted")
        if type(binding["path"]) is not str or not binding["path"]:
            raise ValueError(f"paired calibration {role} path is invalid")
        _require_sha(binding["root_sha256"], f"{role}.root_sha256")
        result[role] = dict(binding)
    return result


def _zero_overlap(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_fields = {
        "schema_version",
        "status",
        "checks",
        "calibration_route_count",
        "fresh_b2_route_count",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise ValueError("calibration/Fresh zero-overlap receipt fields drifted")
    checks = value.get("checks")
    if (
        value.get("schema_version") != "camp_dp_v25_signal_complete_zero_overlap_v1"
        or value.get("status") != "passed_signal_complete_zero_overlap"
        or type(checks) is not dict
        or not checks
        or any(type(item) is not bool or item is not True for item in checks.values())
        or value.get("calibration_route_count") != 50
        or value.get("fresh_b2_route_count") != 100
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
    ):
        raise ValueError("calibration/Fresh zero-overlap receipt drifted")
    return copy.deepcopy(value)


def _model_authority(value: Mapping[str, str]) -> dict[str, str]:
    fields = {
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_scales_file_sha256",
        "static14d_weights_file_sha256",
        "scene14d_theta_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("paired calibration model authority fields drifted")
    result = dict(value)
    for name, digest in result.items():
        _require_sha(digest, name)
    return result


def _require_sha(value: Any, name: str) -> None:
    if type(value) is not str or len(value) != 64 or set(value) - set(
        "0123456789abcdef"
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def canonical_sha256(value: Any) -> str:
    raw = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
