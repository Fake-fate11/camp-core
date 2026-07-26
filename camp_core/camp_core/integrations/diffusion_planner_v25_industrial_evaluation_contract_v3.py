from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t

from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract_v2 as v2,
)


SCHEMA_VERSION = "camp_dp_v25_industrial_oriented_evaluation_contract_v3"
CAPABILITY_SCHEMA_VERSION = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v3"
)
STATUS = "frozen_outcome_independent_industrial_oriented_evaluation_contract_v3"
HIGH_AUTHORITY_SHA256 = v2.HIGH_AUTHORITY_SHA256
FAMILYWISE_METHOD = "holm_bonferroni_step_down_within_exact_family"
FAMILYWISE_ALPHA = 0.05
MARGIN_AUTHORITY = (
    "future_preregistered_nonnegative_leaf_margin_required_numeric_value_absent"
)

ADDED_LEAF_FIELDS = (
    "test_type",
    "symbolic_margin_authority",
    "oriented_cluster_delta",
    "null_hypothesis",
    "alternative_hypothesis",
    "p_value_rule",
    "familywise_decision_rule",
)
SCALAR_LEAF_FIELDS = tuple(v2.SCALAR_LEAF_FIELDS) + ADDED_LEAF_FIELDS

COLLISION_ONSET_ID = (
    "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
)
COLLISION_ONSET_FORMULA = (
    "for the first full-OBB false_to_true intersection interval [t-1,t], "
    "reconstruct constant interval velocities u_ego=(p_ego[t]-p_ego[t-1])/dt "
    "and u_actor=(p_actor[t]-p_actor[t-1])/dt; obtain the earliest continuous-SAT "
    "translation entry fraction tau in [0,1] using the t-1 OBB orientations; "
    "r_tau=((1-tau)*p_actor[t-1]+tau*p_actor[t])-"
    "((1-tau)*p_ego[t-1]+tau*p_ego[t]), v_rel_tau=u_actor-u_ego, and return "
    "max(0,-dot(r_tau,v_rel_tau)/max(norm(r_tau),1e-9)); initial overlap, no "
    "preceding interval, nonfinite inputs, no finite unique SAT entry, or "
    "norm(r_tau)<=1e-9 are typed missing and never converted to zero"
)
_BASE_V2_CONTRACT = v2.evaluation_contract_v2()

P_VALUE_RULE = (
    "n>=2 finite equal-cluster oriented deltas z; for NI use "
    "t=(mean(z)+M_leaf)/(sample_sd(z)/sqrt(n)), df=n-1, "
    "p=student_t.sf(t,df); if sample_sd=0 then p=0 iff mean(z)+M_leaf>0 "
    "else p=1; missing/nonfinite blocks the complete family"
)
HOLM_RULE = (
    "within the exact family sort by (p_value,leaf_id); at one-based rank i "
    "reject iff p_value<=0.05/(m-i+1); stop at the first non-rejection and "
    "retain that and all later leaves as not rejected; any required missing "
    "or failure blocks the complete family"
)


def _parents() -> list[dict[str, Any]]:
    parents = copy.deepcopy(_BASE_V2_CONTRACT["parent_endpoints"])
    onset = next(row for row in parents if row["endpoint_id"] == COLLISION_ONSET_ID)
    onset["formula"] = COLLISION_ONSET_FORMULA
    onset["event_definition"] = (
        "first per-run full-OBB intersection indicator false_to_true transition; "
        "initial overlap has no reconstructable onset interval"
    )
    onset["finite_rules"] = (
        "all positions and reconstructed velocities finite; dt=0.1; unique finite "
        "continuous-SAT tau in [0,1]; norm(r_tau)>1e-9"
    )
    onset["applicability"] = (
        "a false_to_true full-OBB intersection with a finite preceding interval "
        "and unique translation-SAT contact fraction"
    )
    onset["missing_policy"] = (
        "typed missing for initial overlap, no prior interval, nonfinite input, "
        "no finite unique SAT entry, or coincident contact centroids"
    )
    return parents


def _test_type(row: Mapping[str, Any]) -> str:
    role = str(row["guardrail_role"])
    if role == "evidence_missing_not_testable":
        return "not_testable"
    if role == "descriptive_only":
        return "descriptive"
    return "noninferiority"


def _oriented_delta(direction: str, test_type: str) -> str:
    if test_type in {"descriptive", "not_testable"}:
        return "not_applicable"
    if direction == "lower":
        return "z_j=baseline_cluster_mean_j-method_cluster_mean_j"
    if direction == "higher":
        return "z_j=method_cluster_mean_j-baseline_cluster_mean_j"
    raise ValueError("testable leaf must have lower or higher direction")


def _annotate_leaf(source: Mapping[str, Any]) -> dict[str, Any]:
    row = copy.deepcopy(dict(source))
    if row["leaf_id"] == COLLISION_ONSET_ID:
        row["formula"] = COLLISION_ONSET_FORMULA
    test_type = _test_type(row)
    if test_type == "noninferiority":
        row["multiplicity_family"] = str(row["multiplicity_family"])
        row["confidence_interval"] = (
            "unadjusted_one_sided_95pct_oriented_lower_bound_descriptive_only_"
            "not_familywise_claim_evidence"
        )
        row["familywise_method"] = FAMILYWISE_METHOD
        row["familywise_alpha"] = FAMILYWISE_ALPHA
        row["claim_gate_state"] = (
            "numeric_margin_not_authorized_until_future_preregistration"
        )
        row["btw_applicability"] = (
            "future_paired_unit_better_tie_worse_on_oriented_delta_exact_zero_tie"
        )
        margin = f"M[{row['leaf_id']}]>=0;" + MARGIN_AUTHORITY
        null = "H0:mu_z<=-M_leaf"
        alternative = "H1:mu_z>-M_leaf"
        p_rule = P_VALUE_RULE
        holm_rule = HOLM_RULE
    elif test_type == "descriptive":
        row["multiplicity_family"] = "descriptive_only_not_tested"
        row["confidence_interval"] = (
            "unadjusted_two_sided_95pct_equal_cluster_student_t_"
            "descriptive_only_not_familywise"
        )
        row["familywise_method"] = "none_descriptive_only"
        row["familywise_alpha"] = None
        row["claim_gate_state"] = "descriptive_only_not_claim_gate"
        row["btw_applicability"] = "not_applicable"
        margin = "not_applicable"
        null = "not_applicable"
        alternative = "not_applicable"
        p_rule = "not_applicable"
        holm_rule = "not_applicable"
    else:
        row["multiplicity_family"] = "not_testable"
        row["confidence_interval"] = "none_not_testable"
        row["familywise_method"] = "none_not_testable"
        row["familywise_alpha"] = None
        row["claim_gate_state"] = "not_testable_evidence_missing"
        row["btw_applicability"] = "not_applicable"
        margin = "not_applicable"
        null = "not_applicable"
        alternative = "not_applicable"
        p_rule = "not_applicable"
        holm_rule = "not_applicable"
    row.update(
        {
            "test_type": test_type,
            "symbolic_margin_authority": margin,
            "oriented_cluster_delta": _oriented_delta(str(row["direction"]), test_type),
            "null_hypothesis": null,
            "alternative_hypothesis": alternative,
            "p_value_rule": p_rule,
            "familywise_decision_rule": holm_rule,
        }
    )
    return row


def _leaves(parents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    base = v2._scalar_leaves(parents)  # versioned, outcome-independent v2 registry
    return [_annotate_leaf(row) for row in base]


def decision_topology(leaves: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tested_families: dict[str, list[str]] = {}
    descriptive: list[str] = []
    not_testable: list[str] = []
    hard_safety: list[str] = []
    guardrails: list[str] = []
    for row in leaves:
        leaf_id = str(row["leaf_id"])
        if row["test_type"] == "noninferiority":
            tested_families.setdefault(str(row["multiplicity_family"]), []).append(
                leaf_id
            )
            if row["guardrail_role"] == "hard_safety":
                hard_safety.append(leaf_id)
            else:
                guardrails.append(leaf_id)
        elif row["test_type"] == "descriptive":
            descriptive.append(leaf_id)
        else:
            not_testable.append(leaf_id)
    return {
        "statistical_unit": (
            "future preregistered scenario/corridor-intersection cluster after "
            "per-run aggregation"
        ),
        "ticks_rows_arms_seeds_are_independent_n": False,
        "cluster_weighting": "equal_cluster_weight",
        "oriented_delta_lower": (
            "baseline_cluster_mean-method_cluster_mean"
        ),
        "oriented_delta_higher": (
            "method_cluster_mean-baseline_cluster_mean"
        ),
        "supported_test_types": [
            "noninferiority",
            "superiority",
            "descriptive",
            "not_testable",
        ],
        "active_test_types_in_v3": ["noninferiority", "descriptive", "not_testable"],
        "noninferiority_hypotheses": {
            "null": "H0:mu_z<=-M_leaf",
            "alternative": "H1:mu_z>-M_leaf",
            "margin_authority": MARGIN_AUTHORITY,
            "numeric_margin_currently_authorized": False,
        },
        "superiority_hypotheses_if_future_preregistered": {
            "null": "H0:mu_z<=0",
            "alternative": "H1:mu_z>0",
            "currently_assigned_leaf_count": 0,
        },
        "student_t_one_sided_p_value_rule": P_VALUE_RULE,
        "zero_variance_rule": (
            "p=0 iff the oriented null-bound numerator is strictly positive; "
            "otherwise p=1"
        ),
        "minimum_cluster_count": 2,
        "familywise_method": FAMILYWISE_METHOD,
        "familywise_alpha": FAMILYWISE_ALPHA,
        "holm_order": "stable_ascending_(p_value,leaf_id)",
        "holm_comparison": "p_value<=alpha/(m-i+1)",
        "holm_stop_rule": "stop_at_first_non_rejection",
        "tested_families": {
            key: sorted(value) for key, value in sorted(tested_families.items())
        },
        "descriptive_only_leaves": sorted(descriptive),
        "not_testable_leaves": sorted(not_testable),
        "hard_safety_iut_members": sorted(hard_safety),
        "guardrail_iut_members": sorted(guardrails),
        "hard_safety_combination": (
            "all hard_safety_iut_members reject their frozen H0 after their exact "
            "family Holm procedure and no member/family is missing"
        ),
        "guardrail_combination": (
            "all guardrail_iut_members reject their frozen H0 after their exact "
            "family Holm procedure and no member/family is missing"
        ),
        "hierarchy": (
            "evidence_integrity_then_hard_safety_IUT_then_guardrail_IUT; "
            "descriptive leaves never compensate"
        ),
        "missing_policy": (
            "any required leaf missing, nonfinite, failed, or absent blocks the "
            "complete multiplicity family and therefore its IUT layer"
        ),
        "ordinary_ci_role": (
            "unadjusted 95pct intervals are descriptive only and never familywise "
            "claim evidence; familywise decisions use frozen Holm-adjusted p-values"
        ),
        "btw_rule": (
            "on oriented paired-unit deltas: better if z>0, tie only if z==0, "
            "worse if z<0; B+T+W equals the full retained paired denominator"
        ),
        "current_claim_gate_authorized": False,
        "weighted_compensation_allowed": False,
    }


def _build_contract() -> dict[str, Any]:
    base = _BASE_V2_CONTRACT
    parents = _parents()
    leaves = _leaves(parents)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "supersedes_schema_version": v2.SCHEMA_VERSION,
        "superseded_v2_role": "immutable_superseded_pre_final_diagnostic",
        "high_authority": copy.deepcopy(base["high_authority"]),
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "bindings": copy.deepcopy(base["bindings"]),
        "parent_endpoint_count": len(parents),
        "parent_endpoints": parents,
        "scalar_leaf_required_fields": list(SCALAR_LEAF_FIELDS),
        "scalar_leaf_count": len(leaves),
        "scalar_leaf_registry": leaves,
        "source_bindings": copy.deepcopy(base["source_bindings"]),
        "sealed_source_requirements": copy.deepcopy(base["sealed_source_requirements"]),
        "decision_topology": decision_topology(leaves),
        "legacy": copy.deepcopy(base["legacy"]),
        "evaluation_and_selector_training_decoupled": True,
        "claim_authorized": False,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
    }


def evaluation_contract_v3() -> dict[str, Any]:
    result = _build_contract()
    validate_evaluation_contract_v3(result)
    return result


def validate_evaluation_contract_v3(contract: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    expected = _build_contract()
    if value != expected:
        raise ValueError("industrial v3 contract semantic preimage drifted")
    leaves = value["scalar_leaf_registry"]
    if len(leaves) != 161 or len({row["leaf_id"] for row in leaves}) != 161:
        raise ValueError("industrial v3 scalar leaf exact topology drifted")
    if any(set(row) != set(SCALAR_LEAF_FIELDS) for row in leaves):
        raise ValueError("industrial v3 scalar leaf schema drifted")
    onset = next(row for row in leaves if row["leaf_id"] == COLLISION_ONSET_ID)
    if (
        onset["direction"] != "lower"
        or "max(0,-dot(r_tau,v_rel_tau)" not in onset["formula"]
        or "typed missing" not in onset["formula"]
    ):
        raise ValueError("industrial v3 collision onset proxy drifted")
    if value["decision_topology"]["current_claim_gate_authorized"] is not False:
        raise ValueError("industrial v3 claim gate must remain false")
    return value


def oriented_paired_cluster_delta(
    direction: str,
    method_cluster_means: Sequence[float],
    baseline_cluster_means: Sequence[float],
) -> np.ndarray:
    method = np.asarray(method_cluster_means, dtype=np.float64)
    baseline = np.asarray(baseline_cluster_means, dtype=np.float64)
    if method.ndim != 1 or baseline.shape != method.shape or method.size < 2:
        raise ValueError("paired cluster vectors must be same 1D shape with n>=2")
    if not np.all(np.isfinite(method)) or not np.all(np.isfinite(baseline)):
        raise ValueError("paired cluster vectors must be finite")
    if direction == "lower":
        return baseline - method
    if direction == "higher":
        return method - baseline
    raise ValueError("directed test requires lower or higher")


def collision_onset_relative_closing_speed_proxy(
    ego_position_previous: Sequence[float],
    ego_position_current: Sequence[float],
    actor_position_previous: Sequence[float],
    actor_position_current: Sequence[float],
    *,
    dt_s: float,
    continuous_sat_entry_fraction: float | None,
    initial_overlap: bool = False,
    has_preceding_interval: bool = True,
) -> dict[str, Any]:
    if initial_overlap:
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "initial_overlap_has_no_false_to_true_onset_interval",
        }
    if not has_preceding_interval:
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "no_preceding_interval_for_collision_onset",
        }
    arrays = [
        np.asarray(value, dtype=np.float64)
        for value in (
            ego_position_previous,
            ego_position_current,
            actor_position_previous,
            actor_position_current,
        )
    ]
    if any(value.shape != (2,) for value in arrays):
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "position_shape_not_xy",
        }
    if (
        not math.isfinite(dt_s)
        or dt_s <= 0
        or any(not np.all(np.isfinite(value)) for value in arrays)
    ):
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "nonfinite_or_invalid_interval_input",
        }
    if continuous_sat_entry_fraction is None or not math.isfinite(
        continuous_sat_entry_fraction
    ):
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "no_finite_unique_continuous_sat_entry",
        }
    tau = float(continuous_sat_entry_fraction)
    if not 0.0 <= tau <= 1.0:
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "continuous_sat_entry_outside_interval",
        }
    ego_previous, ego_current, actor_previous, actor_current = arrays
    ego_velocity = (ego_current - ego_previous) / dt_s
    actor_velocity = (actor_current - actor_previous) / dt_s
    relative_velocity = actor_velocity - ego_velocity
    relative_position = (
        (1.0 - tau) * actor_previous
        + tau * actor_current
        - ((1.0 - tau) * ego_previous + tau * ego_current)
    )
    distance = float(np.linalg.norm(relative_position))
    if not math.isfinite(distance) or distance <= 1e-9:
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "coincident_centroids_at_contact",
        }
    value = max(
        0.0,
        -float(np.dot(relative_position, relative_velocity)) / max(distance, 1e-9),
    )
    if not math.isfinite(value):
        return {
            "status": "evidence_missing",
            "value": None,
            "reason": "nonfinite_reconstructed_closing_speed",
        }
    return {
        "status": "computed",
        "value": value,
        "reason": "nonnegative_collision_onset_kinematic_proxy",
    }


def one_sided_student_t_p_value(
    oriented_deltas: Sequence[float], margin: float
) -> dict[str, float | int]:
    values = np.asarray(oriented_deltas, dtype=np.float64)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(values)):
        raise ValueError("oriented deltas must be a finite 1D vector with n>=2")
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("NI margin must be finite and nonnegative")
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    numerator = mean + float(margin)
    if sd == 0.0:
        statistic = math.inf if numerator > 0 else -math.inf if numerator < 0 else 0.0
        p_value = 0.0 if numerator > 0 else 1.0
    else:
        statistic = numerator / (sd / math.sqrt(values.size))
        p_value = float(student_t.sf(statistic, df=values.size - 1))
    return {
        "n": int(values.size),
        "df": int(values.size - 1),
        "oriented_mean": mean,
        "sample_sd": sd,
        "margin": float(margin),
        "statistic": statistic,
        "p_value": p_value,
    }


def holm_step_down(
    p_values: Mapping[str, float],
    expected_leaf_ids: Sequence[str],
    *,
    alpha: float = FAMILYWISE_ALPHA,
) -> dict[str, Any]:
    expected = tuple(sorted(expected_leaf_ids))
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("Holm family must be nonempty and unique")
    if set(p_values) != set(expected):
        raise ValueError("Holm family missing or unknown leaf")
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("Holm alpha invalid")
    ordered = []
    for leaf_id, raw in p_values.items():
        value = float(raw)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("Holm p-value invalid")
        ordered.append((value, leaf_id))
    ordered.sort(key=lambda item: (item[0], item[1]))
    decisions: list[dict[str, Any]] = []
    stopped = False
    m = len(ordered)
    for index, (p_value, leaf_id) in enumerate(ordered, start=1):
        threshold = alpha / (m - index + 1)
        rejected = (not stopped) and p_value <= threshold
        if not rejected:
            stopped = True
        decisions.append(
            {
                "rank": index,
                "leaf_id": leaf_id,
                "p_value": p_value,
                "threshold": threshold,
                "rejected": rejected,
            }
        )
    return {
        "family_size": m,
        "alpha": alpha,
        "ordered_decisions": decisions,
        "all_rejected": all(row["rejected"] for row in decisions),
    }


def capability_matrix_v3(
    contract: Mapping[str, Any], source_dirs: Mapping[str, str]
) -> dict[str, Any]:
    validated = validate_evaluation_contract_v3(contract)
    audit = v2.audit_sealed_sources(source_dirs)
    rows: list[dict[str, Any]] = []
    for leaf in validated["scalar_leaf_registry"]:
        binding = v2.SOURCE_BINDINGS[leaf["source_binding_id"]]
        evidence = []
        for artifact_name in binding["artifacts"]:
            inventory = audit["inventories"][artifact_name]
            for filename, sha in inventory["entries"].items():
                evidence.append(
                    {
                        "artifact_name": artifact_name,
                        "artifact_root_sha256": inventory["artifact_root_sha256"],
                        "artifact_review_root_sha256": inventory[
                            "artifact_review_root_sha256"
                        ],
                        "inventory_file": filename,
                        "inventory_file_sha256": sha,
                        "inventory_manifest_sha256": inventory[
                            "inventory_manifest_sha256"
                        ],
                    }
                )
        rows.append(
            {
                "leaf_id": leaf["leaf_id"],
                "parent_id": leaf["parent_id"],
                "evidence_class": binding["evidence_class"],
                "evidence_inventory": evidence,
                "canonical_json_pointers": list(binding["json_pointers"]),
                "source_shape": binding["shape"],
                "source_units": binding["units"],
                "applicability_prerequisites": binding["prerequisites"],
                "transform_inputs": binding["transform_inputs"],
                "reason": binding["reason"],
                "structure_only": True,
                "outcome_values_read": False,
            }
        )
    result = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "sealed_structure_only_scalar_leaf_capability_audit_v3",
        "contract_sha256": v2.canonical_sha256(validated),
        "scalar_leaf_count": len(rows),
        "rows": rows,
        "sealed_inventory_audit": audit["inventories"],
        "structure_only": True,
        "outcome_values_read": False,
        "model_pool_selector_call_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }
    validate_capability_matrix_v3(result, validated, source_dirs)
    return result


def validate_capability_matrix_v3(
    matrix: Mapping[str, Any],
    contract: Mapping[str, Any],
    source_dirs: Mapping[str, str],
) -> dict[str, Any]:
    value = copy.deepcopy(dict(matrix))
    expected = capability_matrix_v3.__wrapped__(contract, source_dirs)
    if value != expected:
        raise ValueError("industrial v3 capability semantic preimage drifted")
    return value


def _build_capability(
    contract: Mapping[str, Any], source_dirs: Mapping[str, str]
) -> dict[str, Any]:
    validated = validate_evaluation_contract_v3(contract)
    audit = v2.audit_sealed_sources(source_dirs)
    rows = []
    for leaf in validated["scalar_leaf_registry"]:
        binding = v2.SOURCE_BINDINGS[leaf["source_binding_id"]]
        evidence = []
        for artifact_name in binding["artifacts"]:
            inventory = audit["inventories"][artifact_name]
            for filename, sha in inventory["entries"].items():
                evidence.append(
                    {
                        "artifact_name": artifact_name,
                        "artifact_root_sha256": inventory["artifact_root_sha256"],
                        "artifact_review_root_sha256": inventory[
                            "artifact_review_root_sha256"
                        ],
                        "inventory_file": filename,
                        "inventory_file_sha256": sha,
                        "inventory_manifest_sha256": inventory[
                            "inventory_manifest_sha256"
                        ],
                    }
                )
        rows.append(
            {
                "leaf_id": leaf["leaf_id"],
                "parent_id": leaf["parent_id"],
                "evidence_class": binding["evidence_class"],
                "evidence_inventory": evidence,
                "canonical_json_pointers": list(binding["json_pointers"]),
                "source_shape": binding["shape"],
                "source_units": binding["units"],
                "applicability_prerequisites": binding["prerequisites"],
                "transform_inputs": binding["transform_inputs"],
                "reason": binding["reason"],
                "structure_only": True,
                "outcome_values_read": False,
            }
        )
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "sealed_structure_only_scalar_leaf_capability_audit_v3",
        "contract_sha256": v2.canonical_sha256(validated),
        "scalar_leaf_count": len(rows),
        "rows": rows,
        "sealed_inventory_audit": audit["inventories"],
        "structure_only": True,
        "outcome_values_read": False,
        "model_pool_selector_call_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }


capability_matrix_v3.__wrapped__ = _build_capability  # type: ignore[attr-defined]
