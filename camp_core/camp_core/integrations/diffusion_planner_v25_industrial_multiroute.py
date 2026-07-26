"""Outcome-independent V25 industrial-v3 multi-route validation contract.

This module deliberately contains no model, selector, outcome, or artifact I/O.
It freezes the scientific topology and an exact integer feasibility/selection
algorithm used before the first model call.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    evaluation_contract_v3,
)


SCHEMA_VERSION = (
    "camp_dp_v25_industrial_v3_multiroute_independent_nonholdout_contract_v1"
)
AUTHORITY_SCHEMA = (
    "camp_dp_v25_industrial_v3_multiroute_independent_nonholdout_"
    "high_authority_v1"
)
AUTHORITY_SHA256 = (
    "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
)
BASE_HEAD = "923e6b29b004778628cf63fe9981f64d45571c4f"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
LOCAL_INTERPRETER = (
    r"C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)
AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"

UPSTREAM_ROOTS = {
    "industrial_contract": (
        "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
    ),
    "industrial_contract_review": (
        "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
    ),
    "industrial_capability": (
        "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
    ),
    "industrial_capability_review": (
        "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
    ),
}

EXACT_DIRS = {
    "contract": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "contract_923e6b29_b5ca942b"
    ),
    "contract_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "contract_review_923e6b29_b5ca942b"
    ),
    "manifest": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "manifest_923e6b29_b5ca942b"
    ),
    "manifest_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "manifest_review_923e6b29_b5ca942b"
    ),
    "hardening_matrix": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "hardening_matrix_923e6b29_b5ca942b"
    ),
    "hardening_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "hardening_matrix_review_923e6b29_b5ca942b"
    ),
    "hardening_focused": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "hardening_focused_923e6b29_b5ca942b"
    ),
    "preflight": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "preflight_923e6b29_b5ca942b"
    ),
    "preflight_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "preflight_review_923e6b29_b5ca942b"
    ),
    "execution": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "execution_923e6b29_b5ca942b"
    ),
    "execution_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "execution_review_923e6b29_b5ca942b"
    ),
    "evaluation": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "evaluation_923e6b29_b5ca942b"
    ),
    "evaluation_review": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "evaluation_review_923e6b29_b5ca942b"
    ),
    "final_docs": (
        "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_"
        "final_docs_focused_923e6b29_b5ca942b"
    ),
}

FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)
RISK_TIERS = ("easy", "borderline", "high_risk")
ROUTE_BINS = (
    "heading_change_abs_le_0_15rad",
    "heading_change_abs_gt_0_15_le_0_75rad",
    "heading_change_abs_gt_0_75rad",
)
SOURCE_AVAILABILITY = ("mapped_signal", "no_signal")
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")

FAMILY_RISK_QUOTAS = (
    (5, 5, 5),
    (5, 5, 5),
    (5, 5, 4),
    (5, 4, 5),
    (4, 5, 5),
    (5, 5, 4),
    (4, 5, 5),
)
FAMILY_ROUTE_QUOTAS = (
    (5, 5, 5),
    (5, 5, 5),
    (5, 5, 4),
    (4, 5, 5),
    (5, 5, 4),
    (5, 4, 5),
    (4, 5, 5),
)
FAMILY_SOURCE_QUOTAS = (
    (8, 7),
    (7, 8),
    (7, 7),
    (7, 7),
    (8, 6),
    (6, 8),
    (7, 7),
)
ROUTE_SOURCE_QUOTAS = ((17, 16), (17, 17), (16, 17))

CLUSTER_COUNT = 100
TICKS_PER_ARM = 64
ARM_RUN_COUNT = 300
PLANNED_TICK_SLOTS = 19_200
PLANNED_MODEL_CALLS = 19_200
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = "<f4"

CAPTURE_CLASSES = (
    "runner_capture_direct",
    "runner_capture_plus_frozen_transform",
    "route_inapplicable",
    "receipt_field_gap_fixable_before_model",
    "transform_ambiguity",
    "permanent_evidence_missing",
)
ZERO_OVERLAP_LEVELS = (
    "route",
    "state",
    "geometry",
    "semantic",
    "source",
    "seed",
    "latent_instance",
    "composite",
)
ZERO_OVERLAP_AUTHORITIES = (
    "bounded_single_route",
    "corrected_64_state_development",
    "training",
    "calibration",
    "legacy_nonholdout",
    "Fresh_B2",
    "Fresh_B3",
    "Fresh_B4",
)
CLONE_PAYLOAD_FIELDS = (
    "schema_version",
    "canonical_route_lanelet_arc_sha256",
    "route_geometry_sha256",
    "semantic_family",
    "risk_tier",
    "source_availability",
    "certified_signal_stopline_inventory_sha256",
    "canonical_state_actor_geometry_sha256",
    "scenario_source_bytes_sha256",
    "scenario_seed_sha256",
    "latent_instance_sha256",
)
PROHIBITED_CLONE_FIELDS = (
    "database_id",
    "scenario_id",
    "route_id",
    "state_id",
    "record_key",
)

PARAMETER_NAMES = (
    "interpreter",
    "schema_and_version_dispatch",
    "simplex_nonnegative_tolerance",
    "atom_scales",
    "static14d_weights",
    "scene14d_theta_and_context_policy",
    "atom_source_and_applicability",
    "physical_eligibility_mask",
    "tie_and_lowest_index",
    "terminal_and_failure_retention",
    "full_denominator",
    "latency_namespaces",
    "camp_head",
    "fixed_dp_head",
    "model_and_checkpoint",
    "route_and_cluster",
    "latent_policy",
    "capture_matrix",
    "artifact_seal_and_atomic_replace",
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def _parameter_rows() -> list[dict[str, Any]]:
    sources = {
        "interpreter": "entrypoint executable/version/prefix/import receipt",
        "schema_and_version_dispatch": "exact versioned typed contract",
        "simplex_nonnegative_tolerance": "TRAINED_SIMPLEX_NONNEGATIVE_ATOL",
        "atom_scales": "sealed accepted-training 14D scale file",
        "static14d_weights": "sealed accepted-training Static14D archive",
        "scene14d_theta_and_context_policy": "sealed Scene14D no-V2I archive",
        "atom_source_and_applicability": "canonical causal 14D atom contract",
        "physical_eligibility_mask": "canonical physical/source-valid mask",
        "tie_and_lowest_index": "production selector tie contract",
        "terminal_and_failure_retention": "typed terminal receipt contract",
        "full_denominator": "authority cluster/arm/tick topology",
        "latency_namespaces": "pool/atoms/context/weights/selector/e2e schema",
        "camp_head": "git HEAD and tracked-clean receipt",
        "fixed_dp_head": "fixed-DP HEAD and tracked-clean receipt",
        "model_and_checkpoint": "source/model/checkpoint/runtime fingerprints",
        "route_and_cluster": "sealed selected cluster manifest",
        "latent_policy": "authority+clone+tick prefrozen latent manifest",
        "capture_matrix": "161-leaf source/capture mapping",
        "artifact_seal_and_atomic_replace": "artifact seal implementation",
    }
    callsites = {
        "interpreter": "all formal wrappers",
        "schema_and_version_dispatch": "contract/manifest/runner/evaluator",
        "simplex_nonnegative_tolerance": "both production selector callsites",
        "atom_scales": "runtime asset loader to selector",
        "static14d_weights": "Static14D production selector",
        "scene14d_theta_and_context_policy": "Scene14D production selector",
        "atom_source_and_applicability": "canonical 14D materializer",
        "physical_eligibility_mask": "selector eligibility keyword",
        "tie_and_lowest_index": "masked score argmin and tie receipt",
        "terminal_and_failure_retention": "all 300 arm runners",
        "full_denominator": "manifest/runner/review/evaluator",
        "latency_namespaces": "all per-tick receipts",
        "camp_head": "all preflight and artifact HEADS",
        "fixed_dp_head": "preflight and model loader",
        "model_and_checkpoint": "model loader and every forward receipt",
        "route_and_cluster": "route loader and every arm receipt",
        "latent_policy": "required latent provider",
        "capture_matrix": "runner receipt to evaluator/reviewer",
        "artifact_seal_and_atomic_replace": "every formal writer",
    }
    rules = {
        "interpreter": "absolute approved runtime; version>=3.10; no bare python",
        "schema_and_version_dispatch": "exact version only; no legacy fallback",
        "simplex_nonnegative_tolerance": "required keyword exact 1e-9",
        "atom_scales": "finite positive float64[14] and exact SHA",
        "static14d_weights": "finite accepted float64[14] and exact SHA",
        "scene14d_theta_and_context_policy": "no-V2I exact archive and context",
        "atom_source_and_applicability": "source/applicability receipt retained",
        "physical_eligibility_mask": "strict bool[8], nonempty, no fallback",
        "tie_and_lowest_index": "exact tie set; lowest eligible index",
        "terminal_and_failure_retention": "typed failure retained; no retry/drop",
        "full_denominator": "100*3*64=19200; n=100 clusters",
        "latency_namespaces": "baseline CAMP stages null/n-a, never zero",
        "camp_head": BASE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "model_and_checkpoint": "exact frozen fingerprints",
        "route_and_cluster": "100 exact selected clone keys; no IDs in key",
        "latent_policy": "row0 zero, unique8, same clone/tick bytes across arms",
        "capture_matrix": "161 exact leaves; unknown/omitted/duplicate fail closed",
        "artifact_seal_and_atomic_replace": "staging then atomic replace and seal",
    }
    return [
        {
            "parameter": name,
            "sealed_source": sources[name],
            "production_loader_and_callsite": callsites[name],
            "frozen_value_or_rule": rules[name],
            "producer_validation": "required keyword/typed config/assertion",
            "execution_reviewer": "reviewer-local literal reconstruction",
            "evaluator": "industrial-v3 leaf source binding",
            "evaluation_reviewer": "reviewer-local formula/source reconstruction",
        }
        for name in PARAMETER_NAMES
    ]


def contract() -> dict[str, Any]:
    industrial = evaluation_contract_v3()
    value = {
        "schema_version": SCHEMA_VERSION,
        "authority_schema": AUTHORITY_SCHEMA,
        "authority_sha256": AUTHORITY_SHA256,
        "base_head": BASE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "status": "frozen_outcome_independent_multiroute_contract",
        "exact_dirs": dict(EXACT_DIRS),
        "upstream_roots": dict(UPSTREAM_ROOTS),
        "manifest": {
            "cluster_count": CLUSTER_COUNT,
            "independent_unit": "route_corridor_semantic_cluster",
            "families": list(FAMILIES),
            "risk_tiers": list(RISK_TIERS),
            "route_bins": list(ROUTE_BINS),
            "source_availability": list(SOURCE_AVAILABILITY),
            "family_risk_quotas": [list(row) for row in FAMILY_RISK_QUOTAS],
            "family_route_quotas": [list(row) for row in FAMILY_ROUTE_QUOTAS],
            "family_source_quotas": [list(row) for row in FAMILY_SOURCE_QUOTAS],
            "route_source_quotas": [list(row) for row in ROUTE_SOURCE_QUOTAS],
            "selection_rule": (
                "id_free_clone_sha_sorted_lexicographically_smallest_feasible_"
                "ordered_sha_vector_exact_integer_feasibility"
            ),
            "clone_payload_fields": list(CLONE_PAYLOAD_FIELDS),
            "prohibited_clone_fields": list(PROHIBITED_CLONE_FIELDS),
            "zero_overlap_levels": list(ZERO_OVERLAP_LEVELS),
            "zero_overlap_authorities": list(ZERO_OVERLAP_AUTHORITIES),
            "no_drop_replace_suffix_or_complete_case": True,
        },
        "architecture": {
            "generator": GENERATOR_NAME,
            "arms": list(ARMS),
            "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
            "formal_model_calls_per_attempted_tick": 1,
            "sequential_calls": 0,
            "candidate0_rule": "same_arm_same_tick_immutable_pool_row0",
            "post_pool_model_dp_latent_candidate_generation_calls": 0,
            "cross_arm_pool_equality_after_state_divergence_claimed": False,
        },
        "denominator": {
            "paired_cluster_count": CLUSTER_COUNT,
            "arm_run_count": ARM_RUN_COUNT,
            "ticks_per_arm": TICKS_PER_ARM,
            "planned_tick_slots": PLANNED_TICK_SLOTS,
            "planned_formal_model_calls": PLANNED_MODEL_CALLS,
            "terminal_equation": "complete+failed+unattempted=19200",
            "hard_pass_unattempted_count": 0,
            "failure_retention": "full_denominator_no_drop_replace_or_retry",
        },
        "latent": {
            "shape": list(LATENT_SHAPE),
            "dtype": LATENT_DTYPE,
            "row0_exact_zero": True,
            "rows1_to_7_unique": True,
            "seed_preimage": "authority_sha256|cluster_clone_key_sha256|tick_ordinal",
            "arm_repeat_forward_time_in_seed": False,
            "same_cluster_tick_bytes_across_arms": True,
        },
        "capture_matrix": {
            "parent_count": industrial["parent_endpoint_count"],
            "leaf_count": industrial["scalar_leaf_count"],
            "leaf_registry_sha256": canonical_sha256(
                industrial["scalar_leaf_registry"]
            ),
            "classes": list(CAPTURE_CLASSES),
            "accepted_capability_baseline": {
                "reconstructable": 119,
                "evidence_missing": 41,
                "scientifically_inapplicable": 1,
            },
            "prior_bounded_observation": {
                "computed": 100,
                "evidence_missing": 57,
                "scientifically_inapplicable": 4,
            },
            "fixable_receipt_gap_must_close_before_model": True,
            "unsupported_leaf_stays_typed_missing": True,
        },
        "statistics": {
            "independent_n": 100,
            "cluster_first": True,
            "ticks_arms_or_k8_rows_as_independent_n": False,
            "comparisons": [
                "Static14D_minus_pool_matched_candidate0",
                "Scene14D_minus_pool_matched_candidate0",
            ],
            "outputs": [
                "direction_oriented_paired_delta",
                "three_arm_cluster_summary",
                "exact_zero_better_tie_worse",
                "ordinary_two_sided_paired_student_t_ci95",
                "full_denominator_missing_and_failure",
                "v3_family_holm_status_or_unexecutable_reason",
            ],
            "holm_only_with_prespecified_test_and_margin_authority": True,
            "numeric_margin_authorized": False,
            "ordinary_ci_is_not_familywise_claim_evidence": True,
            "hard_stage_pass_depends_on_effect_direction": False,
        },
        "hardening": {
            "parameter_propagation_matrix": _parameter_rows(),
            "production_entrypoints_and_consumers_must_be_enumerated": True,
            "pass_and_typed_fail_zero_model_dry_run": True,
            "implicit_defaults_allowed": False,
            "mutation_classes": [
                "missing_required_keyword",
                "default_fallback",
                "wrong_interpreter",
                "wrong_schema_or_version",
                "extra_missing_duplicate_field",
                "nan_or_inf",
                "path_alias",
                "non_atomic_write",
                "resign_or_repin",
                "wrong_root_or_head",
            ],
            "residual_risk_classes": [
                "actually_executed",
                "static_only",
                "unexecuted",
            ],
            "zero_bug_claimed": False,
        },
        "capacity": {
            "class_projection": "ceil(single_route_payload_bytes*100*1.25)",
            "persistent": "sum(projected_classes)+2GiB",
            "peak": "max(projected_classes)",
            "reserve": "max(5GiB,ceil(peak*0.25))",
            "free_rule": "free-persistent-peak>=10GiB+reserve",
            "inode_rule": "free_inodes-ceil(single_route_files*100*1.25)>=100000",
        },
        "interpreter": {
            "local": LOCAL_INTERPRETER,
            "autodl": AUTODL_INTERPRETER,
            "minimum_version": [3, 10],
            "bare_python_or_python3_allowed": False,
        },
        "claim_boundary": {
            "legacy_safetycost_role": "immutable_legacy_exploratory_diagnostic_only",
            "weighted_total_allowed": False,
            "fresh_or_confirmatory_claim": False,
            "industrial_iso_sae_realroad_unseen_map_top1_deployment_claim": False,
            "legacy_honest_no_claim_unchanged": True,
        },
        "prohibitions": {
            "training_or_retraining": False,
            "fresh_holdout_or_new_nonce": False,
            "outcome_read": False,
            "old_artifact_or_cas_write": False,
            "fixed_dp_weights_theta_atoms_scales_change": False,
        },
    }
    return validate_contract(value)


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = deepcopy(dict(value))
    if (
        candidate.get("schema_version") != SCHEMA_VERSION
        or candidate.get("authority_sha256") != AUTHORITY_SHA256
        or candidate.get("base_head") != BASE_HEAD
        or candidate.get("fixed_dp_head") != FIXED_DP_HEAD
        or candidate.get("exact_dirs") != EXACT_DIRS
    ):
        raise ValueError("multi-route authority or identity drifted")
    manifest = candidate.get("manifest", {})
    if (
        manifest.get("cluster_count") != CLUSTER_COUNT
        or manifest.get("families") != list(FAMILIES)
        or manifest.get("risk_tiers") != list(RISK_TIERS)
        or manifest.get("route_bins") != list(ROUTE_BINS)
        or manifest.get("source_availability") != list(SOURCE_AVAILABILITY)
        or manifest.get("family_risk_quotas")
        != [list(row) for row in FAMILY_RISK_QUOTAS]
        or manifest.get("family_route_quotas")
        != [list(row) for row in FAMILY_ROUTE_QUOTAS]
        or manifest.get("family_source_quotas")
        != [list(row) for row in FAMILY_SOURCE_QUOTAS]
        or manifest.get("route_source_quotas")
        != [list(row) for row in ROUTE_SOURCE_QUOTAS]
        or manifest.get("clone_payload_fields") != list(CLONE_PAYLOAD_FIELDS)
        or manifest.get("prohibited_clone_fields") != list(PROHIBITED_CLONE_FIELDS)
    ):
        raise ValueError("multi-route manifest topology drifted")
    denominator = candidate.get("denominator", {})
    if (
        denominator.get("paired_cluster_count") != 100
        or denominator.get("arm_run_count") != 300
        or denominator.get("planned_tick_slots") != 19_200
        or denominator.get("planned_formal_model_calls") != 19_200
    ):
        raise ValueError("multi-route denominator drifted")
    if candidate.get("hardening", {}).get(
        "parameter_propagation_matrix"
    ) != _parameter_rows():
        raise ValueError("parameter propagation matrix drifted")
    if (
        candidate.get("capture_matrix", {}).get("leaf_count") != 161
        or candidate.get("claim_boundary", {}).get("weighted_total_allowed")
        is not False
        or candidate.get("claim_boundary", {}).get(
            "legacy_safetycost_role"
        )
        != "immutable_legacy_exploratory_diagnostic_only"
    ):
        raise ValueError("industrial-v3 capture or claim boundary drifted")
    return candidate


def latent_seed(clone_key_sha256: str, tick_ordinal: int) -> int:
    _sha(clone_key_sha256, "cluster clone key")
    if type(tick_ordinal) is not int or not 0 <= tick_ordinal < 64:
        raise ValueError("tick ordinal must be int in [0,64)")
    digest = hashlib.sha256(
        f"{AUTHORITY_SHA256}|{clone_key_sha256}|{tick_ordinal}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def latent_tensor(clone_key_sha256: str, tick_ordinal: int) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(latent_seed(clone_key_sha256, tick_ordinal)))
    value = np.zeros(LATENT_SHAPE, dtype=np.float32)
    value[1:] = rng.standard_normal(value[1:].shape).astype(np.float32)
    value = np.ascontiguousarray(value)
    row_sha = [hashlib.sha256(row.tobytes(order="C")).hexdigest() for row in value]
    if not np.isfinite(value).all() or len(set(row_sha)) != 8:
        raise ValueError("multi-route latent policy did not produce finite unique8")
    return value


def route_geometry_bin(
    route_polyline_local_m: Sequence[Sequence[Any]],
) -> str:
    points = np.asarray(route_polyline_local_m, dtype=np.float64)
    if (
        points.ndim != 2
        or points.shape[0] < 2
        or points.shape[1] != 2
        or not np.isfinite(points).all()
    ):
        raise ValueError("route polyline must be finite [N>=2,2]")
    delta = np.diff(points, axis=0)
    norm = np.linalg.norm(delta, axis=1)
    delta = delta[norm > 1e-9]
    if delta.shape[0] == 0:
        raise ValueError("route polyline has no nonzero segment")
    headings = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    change = abs(
        (float(headings[-1] - headings[0]) + math.pi) % (2.0 * math.pi)
        - math.pi
    )
    if change <= 0.15:
        return ROUTE_BINS[0]
    if change <= 0.75:
        return ROUTE_BINS[1]
    return ROUTE_BINS[2]


def validate_clone_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = deepcopy(dict(value))
    if set(payload) != set(CLONE_PAYLOAD_FIELDS):
        raise ValueError("clone payload field set drifted")
    if any(name in payload for name in PROHIBITED_CLONE_FIELDS):
        raise ValueError("ID-bearing field entered clone payload")
    if payload.get("schema_version") != (
        "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
    ):
        raise ValueError("clone payload schema drifted")
    for name in CLONE_PAYLOAD_FIELDS:
        if name == "schema_version":
            continue
        if name == "semantic_family":
            if payload[name] not in FAMILIES:
                raise ValueError("clone semantic family drifted")
        elif name == "risk_tier":
            if payload[name] not in RISK_TIERS:
                raise ValueError("clone risk tier drifted")
        elif name == "source_availability":
            if payload[name] not in SOURCE_AVAILABILITY:
                raise ValueError("clone source availability drifted")
        else:
            _sha(payload[name], f"clone {name}")
    return payload


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    expected = {
        "clone_payload",
        "clone_key_sha256",
        "route_bin",
        "overlap_keys",
        "source_binding",
    }
    if set(row) != expected:
        raise ValueError("eligible candidate schema drifted")
    payload = validate_clone_payload(row["clone_payload"])
    if canonical_sha256(payload) != _sha(row["clone_key_sha256"], "clone key"):
        raise ValueError("clone key does not match canonical payload")
    if row["route_bin"] not in ROUTE_BINS:
        raise ValueError("candidate route bin drifted")
    overlap = row["overlap_keys"]
    if type(overlap) is not dict or set(overlap) != set(ZERO_OVERLAP_LEVELS):
        raise ValueError("candidate overlap layer schema drifted")
    for level in ZERO_OVERLAP_LEVELS:
        _sha(overlap[level], f"overlap {level}")
    if overlap["route"] != payload["canonical_route_lanelet_arc_sha256"]:
        raise ValueError("candidate route overlap key drifted")
    if overlap["geometry"] != payload["route_geometry_sha256"]:
        raise ValueError("candidate geometry overlap key drifted")
    if overlap["semantic"] != canonical_sha256(
        {
            "family": payload["semantic_family"],
            "tier": payload["risk_tier"],
            "signal_stopline": payload[
                "certified_signal_stopline_inventory_sha256"
            ],
            "actor_geometry": payload["canonical_state_actor_geometry_sha256"],
        }
    ):
        raise ValueError("candidate semantic overlap key drifted")
    if overlap["source"] != payload["scenario_source_bytes_sha256"]:
        raise ValueError("candidate source overlap key drifted")
    if overlap["seed"] != payload["scenario_seed_sha256"]:
        raise ValueError("candidate seed overlap key drifted")
    if overlap["latent_instance"] != payload["latent_instance_sha256"]:
        raise ValueError("candidate latent overlap key drifted")
    if overlap["composite"] != row["clone_key_sha256"]:
        raise ValueError("candidate composite overlap key drifted")
    binding = row["source_binding"]
    if (
        type(binding) is not dict
        or set(binding)
        != {
            "artifact_path",
            "artifact_root_sha256",
            "inventory_entry_path",
            "inventory_entry_sha256",
        }
    ):
        raise ValueError("candidate exact source binding drifted")
    _sha(binding["artifact_root_sha256"], "source artifact root")
    _sha(binding["inventory_entry_sha256"], "source inventory entry")
    return row


def _cell(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    payload = row["clone_payload"]
    return (
        FAMILIES.index(payload["semantic_family"]),
        RISK_TIERS.index(payload["risk_tier"]),
        ROUTE_BINS.index(row["route_bin"]),
        SOURCE_AVAILABILITY.index(payload["source_availability"]),
    )


def _risk_allocations(
    family: int,
    route_source: tuple[int, ...],
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> tuple[tuple[int, ...], ...]:
    """Enumerate exact 3-risk allocations for six route/source columns."""

    risk_target = FAMILY_RISK_QUOTAS[family]
    columns = [(route, source) for route in range(3) for source in range(2)]
    results: list[tuple[int, ...]] = []
    current: list[int] = []

    def rec(column: int, remaining: tuple[int, int, int]) -> None:
        if column == len(columns):
            if remaining == (0, 0, 0):
                results.append(tuple(current))
            return
        route, source = columns[column]
        target = route_source[column]
        lows = [
            int(lower.get((family, risk, route, source), 0)) for risk in range(3)
        ]
        highs = [
            int(upper.get((family, risk, route, source), 0)) for risk in range(3)
        ]
        for a in range(lows[0], min(highs[0], remaining[0], target) + 1):
            for b in range(
                lows[1],
                min(highs[1], remaining[1], target - a) + 1,
            ):
                c = target - a - b
                if not lows[2] <= c <= min(highs[2], remaining[2]):
                    continue
                next_remaining = (
                    remaining[0] - a,
                    remaining[1] - b,
                    remaining[2] - c,
                )
                minimum_remaining = [
                    sum(
                        int(
                            lower.get(
                                (
                                    family,
                                    risk,
                                    later_route,
                                    later_source,
                                ),
                                0,
                            )
                        )
                        for later_route, later_source in columns[column + 1 :]
                    )
                    for risk in range(3)
                ]
                maximum_remaining = [
                    sum(
                        int(
                            upper.get(
                                (
                                    family,
                                    risk,
                                    later_route,
                                    later_source,
                                ),
                                0,
                            )
                        )
                        for later_route, later_source in columns[column + 1 :]
                    )
                    for risk in range(3)
                ]
                if any(
                    next_remaining[risk] < minimum_remaining[risk]
                    or next_remaining[risk] > maximum_remaining[risk]
                    for risk in range(3)
                ):
                    continue
                current.extend((a, b, c))
                rec(column + 1, next_remaining)
                del current[-3:]

    rec(0, tuple(risk_target))
    return tuple(results)


def _family_options(
    family: int,
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
    """Return (route-source totals, full 18-cell counts) feasible for a family."""

    route_target = FAMILY_ROUTE_QUOTAS[family]
    source0_target = FAMILY_SOURCE_QUOTAS[family][0]
    options: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for r0s0 in range(route_target[0] + 1):
        for r1s0 in range(route_target[1] + 1):
            r2s0 = source0_target - r0s0 - r1s0
            if not 0 <= r2s0 <= route_target[2]:
                continue
            route_source = (
                r0s0,
                route_target[0] - r0s0,
                r1s0,
                route_target[1] - r1s0,
                r2s0,
                route_target[2] - r2s0,
            )
            aggregate_ok = True
            for route in range(3):
                for source in range(2):
                    target = route_source[route * 2 + source]
                    low = sum(
                        int(lower.get((family, risk, route, source), 0))
                        for risk in range(3)
                    )
                    high = sum(
                        int(upper.get((family, risk, route, source), 0))
                        for risk in range(3)
                    )
                    if not low <= target <= high:
                        aggregate_ok = False
            if not aggregate_ok:
                continue
            allocations = _risk_allocations(family, route_source, lower, upper)
            for allocation in allocations:
                # allocation is column-major risk triplets; normalize to the
                # canonical (risk, route, source) order.
                full = []
                for risk in range(3):
                    for route in range(3):
                        for source in range(2):
                            column = route * 2 + source
                            full.append(allocation[column * 3 + risk])
                options.append((route_source, tuple(full)))
    return tuple(options)


def find_feasible_counts(
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> dict[tuple[int, int, int, int], int] | None:
    """Find one exact quota table within cell lower/upper bounds."""

    family_options = [
        _family_options(family, lower, upper) for family in range(len(FAMILIES))
    ]
    if any(not options for options in family_options):
        return None
    global_target = tuple(
        ROUTE_SOURCE_QUOTAS[route][source]
        for route in range(3)
        for source in range(2)
    )
    states: dict[tuple[int, ...], tuple[int, ...]] = {(0,) * 6: ()}
    for family, options in enumerate(family_options):
        next_states: dict[tuple[int, ...], tuple[int, ...]] = {}
        for accumulated, picks in states.items():
            for option_index, (route_source, _full) in enumerate(options):
                combined = tuple(
                    accumulated[index] + route_source[index] for index in range(6)
                )
                if any(
                    combined[index] > global_target[index] for index in range(6)
                ):
                    continue
                next_states.setdefault(combined, picks + (option_index,))
        states = next_states
        if not states:
            return None
    picks = states.get(global_target)
    if picks is None:
        return None
    result: dict[tuple[int, int, int, int], int] = {}
    for family, option_index in enumerate(picks):
        full = family_options[family][option_index][1]
        index = 0
        for risk in range(3):
            for route in range(3):
                for source in range(2):
                    result[(family, risk, route, source)] = full[index]
                    index += 1
    return result


def select_lexicographically_smallest_feasible(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [validate_candidate(row) for row in candidates]
    rows.sort(key=lambda row: row["clone_key_sha256"])
    keys = [row["clone_key_sha256"] for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("eligible clone keys are not unique")
    remaining = Counter(_cell(row) for row in rows)
    lower: Counter[tuple[int, int, int, int]] = Counter()
    initial = find_feasible_counts(lower, remaining)
    if initial is None:
        raise ValueError("eligible inventory cannot satisfy frozen quota topology")
    selected: list[dict[str, Any]] = []
    for row in rows:
        cell = _cell(row)
        remaining[cell] -= 1
        trial = Counter(lower)
        trial[cell] += 1
        upper = Counter(
            {
                key: trial[key] + remaining[key]
                for key in set(trial).union(remaining)
            }
        )
        if find_feasible_counts(trial, upper) is not None:
            lower = trial
            selected.append(row)
    if len(selected) != CLUSTER_COUNT:
        raise RuntimeError("lexicographic selection did not produce 100 clusters")
    validate_selected_manifest(selected)
    numbered = []
    for ordinal, row in enumerate(selected):
        item = deepcopy(row)
        item["cluster_ordinal"] = ordinal
        item["cluster_id"] = f"multiroute_cluster:{ordinal:03d}"
        item["entry_sha256"] = canonical_sha256(item)
        numbered.append(item)
    result = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_manifest_v1",
        "authority_sha256": AUTHORITY_SHA256,
        "selection_rule": (
            "id_free_clone_sha_sorted_lexicographically_smallest_feasible_"
            "ordered_sha_vector_exact_integer_feasibility"
        ),
        "eligible_count": len(rows),
        "selected_count": len(numbered),
        "entries": numbered,
        "selected_clone_key_sha256": [
            row["clone_key_sha256"] for row in numbered
        ],
        "no_drop_replace_suffix_or_complete_case": True,
    }
    result["manifest_sha256"] = canonical_sha256(result)
    return result


def validate_selected_manifest(rows: Sequence[Mapping[str, Any]]) -> None:
    validated = [validate_candidate(row) for row in rows]
    if len(validated) != CLUSTER_COUNT:
        raise ValueError("selected manifest must contain exactly 100 clusters")
    counts = Counter(_cell(row) for row in validated)
    for family in range(7):
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for route in range(3)
                for source in range(2)
            )
            for risk in range(3)
        ) != FAMILY_RISK_QUOTAS[family]:
            raise ValueError("selected family-risk quota drifted")
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for source in range(2)
            )
            for route in range(3)
        ) != FAMILY_ROUTE_QUOTAS[family]:
            raise ValueError("selected family-route quota drifted")
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for route in range(3)
            )
            for source in range(2)
        ) != FAMILY_SOURCE_QUOTAS[family]:
            raise ValueError("selected family-source quota drifted")
    if tuple(
        tuple(
            sum(counts[(family, risk, route, source)] for family in range(7) for risk in range(3))
            for source in range(2)
        )
        for route in range(3)
    ) != ROUTE_SOURCE_QUOTAS:
        raise ValueError("selected route-source quota drifted")


def overlap_report(
    selected: Sequence[Mapping[str, Any]],
    forbidden: Mapping[str, Mapping[str, Iterable[str]]],
) -> dict[str, Any]:
    if set(forbidden) != set(ZERO_OVERLAP_AUTHORITIES):
        raise ValueError("forbidden authority inventory set drifted")
    selected_layers = {
        level: {str(row["overlap_keys"][level]) for row in selected}
        for level in ZERO_OVERLAP_LEVELS
    }
    report = {}
    for authority in ZERO_OVERLAP_AUTHORITIES:
        layers = forbidden[authority]
        if set(layers) != set(ZERO_OVERLAP_LEVELS):
            raise ValueError("forbidden overlap layer set drifted")
        intersections = {
            level: sorted(selected_layers[level].intersection(set(layers[level])))
            for level in ZERO_OVERLAP_LEVELS
        }
        report[authority] = {
            "forbidden_counts": {
                level: len(set(layers[level])) for level in ZERO_OVERLAP_LEVELS
            },
            "intersection_counts": {
                level: len(intersections[level]) for level in ZERO_OVERLAP_LEVELS
            },
            "intersection_sha256": {
                level: canonical_sha256(intersections[level])
                for level in ZERO_OVERLAP_LEVELS
            },
        }
        if any(intersections[level] for level in ZERO_OVERLAP_LEVELS):
            raise ValueError(f"selected manifest overlaps {authority}")
    return report


def capture_matrix_template(
    capability_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(capability_rows) != 161:
        raise ValueError("industrial capability row denominator drifted")
    result = []
    seen = set()
    for row in capability_rows:
        leaf_id = str(row.get("leaf_id"))
        if not leaf_id or leaf_id in seen:
            raise ValueError("industrial capability leaf identity drifted")
        seen.add(leaf_id)
        evidence = row.get("evidence_class")
        if evidence == "scientifically_inapplicable":
            capture_class = "route_inapplicable"
        elif evidence == "evidence_missing":
            capture_class = "permanent_evidence_missing"
        else:
            capture_class = "runner_capture_plus_frozen_transform"
        result.append(
            {
                "leaf_id": leaf_id,
                "accepted_evidence_class": evidence,
                "capture_class": capture_class,
                "runner_receipt_field_paths": [],
                "frozen_transform_id": None,
                "route_applicability_rule": str(row.get("applicability", "")),
                "gap_reason": None,
                "must_close_before_model": capture_class
                == "receipt_field_gap_fixable_before_model",
            }
        )
    return result


def capacity_decision(
    *,
    free_bytes: int,
    free_inodes: int,
    class_bytes_and_files: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    if (
        type(free_bytes) is not int
        or type(free_inodes) is not int
        or min(free_bytes, free_inodes) < 0
        or not class_bytes_and_files
    ):
        raise ValueError("capacity input is invalid")
    projected = {}
    for name, pair in sorted(class_bytes_and_files.items()):
        if (
            type(name) is not str
            or not name
            or not isinstance(pair, Sequence)
            or len(pair) != 2
        ):
            raise ValueError("capacity class schema drifted")
        payload_bytes, files = pair
        if (
            isinstance(payload_bytes, bool)
            or isinstance(files, bool)
            or not isinstance(payload_bytes, int)
            or not isinstance(files, int)
            or min(payload_bytes, files) < 0
        ):
            raise ValueError("capacity class values drifted")
        projected[name] = {
            "single_route_bytes": payload_bytes,
            "single_route_files": files,
            "projected_bytes": math.ceil(payload_bytes * 100 * 1.25),
            "projected_files": math.ceil(files * 100 * 1.25),
        }
    persistent = sum(row["projected_bytes"] for row in projected.values()) + 2 * 1024**3
    peak = max(row["projected_bytes"] for row in projected.values())
    reserve = max(5 * 1024**3, math.ceil(peak * 0.25))
    file_projection = sum(row["projected_files"] for row in projected.values())
    remaining_bytes = free_bytes - persistent - peak
    remaining_inodes = free_inodes - file_projection
    passed = (
        remaining_bytes >= 10 * 1024**3 + reserve
        and remaining_inodes >= 100_000
    )
    return {
        "classes": projected,
        "free_bytes": free_bytes,
        "free_inodes": free_inodes,
        "persistent_bytes": persistent,
        "peak_bytes": peak,
        "reserve_bytes": reserve,
        "projected_file_count": file_projection,
        "remaining_bytes_after_persistent_and_peak": remaining_bytes,
        "remaining_inodes": remaining_inodes,
        "passed": passed,
    }
