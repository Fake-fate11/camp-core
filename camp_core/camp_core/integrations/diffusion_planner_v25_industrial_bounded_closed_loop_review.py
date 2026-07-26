"""Independent literal oracle for the bounded industrial-v3 closed loop.

This module intentionally does not import the producer contract, runner, or
evaluator.  Constants and decision rules are reviewer-local.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v21_native import (
    array_sha256,
    candidate_latents,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v3 import (
    review_contract_v3_literal,
)


EXPECTED_SCHEMA = "camp_dp_v25_industrial_v3_bounded_nonholdout_closed_loop_v1"
EXPECTED_AUTHORITY = (
    "5e55899b63b8b9897d4bce65c19075784a6c560a509d892c8d156d13f7ef420e"
)
EXPECTED_BASE = "a8b665a019662afbc1f3dffedeb21ca74c543fa5"
EXPECTED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_ROUTE = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
EXPECTED_ARMS = ["pool_matched_candidate0", "Static14D", "Scene14D"]
EXPECTED_PARAMETERS = [
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
    "route",
    "latent_policy",
    "artifact_seal_and_atomic_replace",
]


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def review_contract_literal(
    value: Mapping[str, Any],
    industrial_v3_contract: Mapping[str, Any],
) -> dict[str, Any]:
    row = copy.deepcopy(dict(value))
    if (
        row.get("schema_version") != EXPECTED_SCHEMA
        or row.get("authority_sha256") != EXPECTED_AUTHORITY
        or row.get("base_head") != EXPECTED_BASE
        or row.get("fixed_dp_head") != EXPECTED_DP
    ):
        raise ValueError("reviewer bounded authority binding drifted")
    architecture = row.get("architecture")
    if (
        type(architecture) is not dict
        or architecture.get("generator")
        != "new_single_invocation_batched_k8_candidate_pool"
        or architecture.get("candidate_axis")
        != "same_ego_expanded_batch_dimension_B_equals_8"
        or architecture.get("formal_model_calls_per_tick") != 1
        or architecture.get("sequential_model_calls") != 0
        or architecture.get("post_pool_model_dp_latent_candidate_generation_calls")
        != 0
        or architecture.get("arms") != EXPECTED_ARMS
        or architecture.get("candidate0_rule") != "immutable_pool_row0"
        or architecture.get("post_divergence_cross_arm_input_or_pool_equality_claimed")
        is not False
    ):
        raise ValueError("reviewer bounded architecture drifted")
    source = row.get("source")
    if (
        type(source) is not dict
        or source.get("route_sha256") != EXPECTED_ROUTE
        or source.get("fresh_or_b4_outcome_read") is not False
        or source.get("zero_overlap_levels")
        != ["route", "state", "geometry", "source", "seed", "latent_instance"]
    ):
        raise ValueError("reviewer bounded source topology drifted")
    denominator = row.get("denominator")
    if (
        type(denominator) is not dict
        or denominator.get("arm_runs") != 3
        or denominator.get("ticks_per_arm") != 64
        or denominator.get("planned_ticks") != 192
        or denominator.get("per_arm_identity") != EXPECTED_ARMS
        or denominator.get("failure_retention")
        != "typed_full_denominator_no_drop_replace_or_retry"
    ):
        raise ValueError("reviewer bounded denominator drifted")
    matrix = row.get("pre_execution_hardening", {}).get(
        "parameter_propagation_matrix"
    )
    if (
        type(matrix) is not list
        or [item.get("parameter") for item in matrix] != EXPECTED_PARAMETERS
        or any(
            not isinstance(item.get(key), str) or not item[key]
            for item in matrix
            for key in (
                "sealed_source",
                "production_loader_and_callsite",
                "frozen_value_or_rule",
                "receipt",
                "producer_validation",
                "execution_reviewer",
                "evaluator",
                "evaluation_reviewer",
            )
        )
    ):
        raise ValueError("reviewer propagation matrix drifted")
    reviewed_v3 = review_contract_v3_literal(industrial_v3_contract)
    evaluation = row.get("evaluation")
    if (
        type(evaluation) is not dict
        or evaluation.get("parent_endpoint_count") != 56
        or evaluation.get("scalar_leaf_count") != 161
        or evaluation.get("scalar_leaf_registry_sha256")
        != _sha(reviewed_v3["scalar_leaf_registry"])
        or evaluation.get("legacy_safetycost_role")
        != "immutable_legacy_exploratory_diagnostic_only"
        or evaluation.get("weighted_total_allowed") is not False
        or evaluation.get("independent_cluster_count") != 1
        or evaluation.get("inferential_status")
        != "not_evaluable_bounded_single_cluster"
        or evaluation.get("claim_authorized") is not False
    ):
        raise ValueError("reviewer industrial evaluation boundary drifted")
    if row.get("interpreter") != {
        "local": (
            r"C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime"
            r"\dependencies\python\python.exe"
        ),
        "autodl": "/root/autodl-tmp/dp312_venv/bin/python",
        "minimum_version": [3, 10],
        "bare_python_or_python3_allowed": False,
    }:
        raise ValueError("reviewer interpreter governance drifted")
    return row


def reviewer_tick_seed(tick: int) -> int:
    if type(tick) is not int or not 0 <= tick < 64:
        raise ValueError("reviewer tick out of range")
    digest = hashlib.sha256(
        f"{EXPECTED_AUTHORITY}|{EXPECTED_ROUTE}|{tick}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:4], "big")


def review_latent_manifest(rows: Sequence[Mapping[str, Any]]) -> None:
    if len(rows) != 64:
        raise ValueError("reviewer latent manifest denominator drifted")
    for tick, receipt in enumerate(rows):
        value = np.asarray(
            candidate_latents(reviewer_tick_seed(tick), noise_scale=1.0)
        )
        expected = {
            "tick_ordinal": tick,
            "seed_uint32": reviewer_tick_seed(tick),
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "tensor_sha256": array_sha256(value),
            "row_sha256": [array_sha256(item) for item in value],
            "row_unique_cardinality": 8,
            "row0_all_zero": True,
        }
        if dict(receipt) != expected:
            raise ValueError("reviewer latent bytes or binding drifted")


def review_execution_receipts(
    arms: Sequence[Mapping[str, Any]],
    latent_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    review_latent_manifest(latent_rows)
    if len(arms) != 3:
        raise ValueError("reviewer arm inventory drifted")
    total = 0
    for expected_arm, arm in zip(EXPECTED_ARMS, arms):
        if arm.get("arm") != expected_arm:
            raise ValueError("reviewer arm order drifted")
        ticks = arm.get("ticks")
        if type(ticks) is not list or len(ticks) > 64:
            raise ValueError("reviewer attempted tick inventory drifted")
        statuses = {"complete": 0, "failed": 0, "unattempted": 0}
        for index in range(64):
            if index >= len(ticks):
                statuses["unattempted"] += 1
                continue
            receipt = ticks[index]
            status = receipt.get("terminal_status")
            if status not in {"complete", "failed"}:
                raise ValueError("reviewer typed terminal status drifted")
            statuses[status] += 1
            if receipt.get("tick_index") != index:
                raise ValueError("reviewer tick ordinal drifted")
            if receipt.get("latent_tensor_sha256") != latent_rows[index][
                "tensor_sha256"
            ]:
                raise ValueError("reviewer cross-arm latent binding drifted")
            if receipt.get("primary_pool_model_call_count") != 1:
                raise ValueError("reviewer model call count drifted")
            zero = receipt.get("zero_call_receipt")
            if (
                type(zero) is not dict
                or zero.get("dp_or_model_calls_after_pool") != 0
                or zero.get("latent_replacements_after_pool") != 0
                or zero.get("candidate_generations_after_pool") != 0
                or zero.get("candidate_tensor_sha256_before")
                != zero.get("candidate_tensor_sha256_after")
            ):
                raise ValueError("reviewer post-pool or tensor gate drifted")
            selected = receipt.get("selected_index")
            if expected_arm == "pool_matched_candidate0" and selected != 0:
                raise ValueError("reviewer candidate0 row0 binding drifted")
            rows = receipt.get("candidate_row_sha256")
            if type(rows) is not list or len(rows) != 8 or len(set(rows)) != 8:
                raise ValueError("reviewer K8 diversity receipt drifted")
        declared = {
            name: int(arm.get(f"{name}_tick_count", -1))
            for name in statuses
        }
        if declared != statuses or sum(declared.values()) != 64:
            raise ValueError("reviewer terminal accounting drifted")
        total += 64
    if total != 192:
        raise ValueError("reviewer full denominator drifted")
    return {"planned_ticks": total, "arm_count": 3}


def review_evaluation(
    report: Mapping[str, Any],
    expected_leaf_ids: Sequence[str],
) -> dict[str, Any]:
    row = copy.deepcopy(dict(report))
    if (
        row.get("schema_version")
        != "camp_dp_v25_industrial_v3_bounded_evaluation_v1"
        or row.get("inferential_status")
        != "not_evaluable_bounded_single_cluster"
        or row.get("claim_authorized") is not False
        or row.get("weighted_total_present") is not False
        or row.get("legacy_safetycost_computed") is not False
    ):
        raise ValueError("reviewer bounded evaluation boundary drifted")
    leaves = row.get("scalar_leaf_vector")
    if type(leaves) is not list:
        raise ValueError("reviewer scalar leaves missing")
    ids = [item.get("leaf_id") for item in leaves]
    if ids != list(expected_leaf_ids) or len(set(ids)) != len(ids):
        raise ValueError("reviewer scalar leaf exact topology drifted")
    for leaf in leaves:
        if leaf.get("status") not in {
            "computed_descriptive",
            "evidence_missing",
            "scientifically_inapplicable",
            "typed_execution_failure",
        }:
            raise ValueError("reviewer scalar leaf status drifted")
        if leaf.get("inferential_status") != "not_evaluable_bounded_single_cluster":
            raise ValueError("reviewer leaf inference boundary drifted")
    return row
