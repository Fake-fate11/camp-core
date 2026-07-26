"""Independent local-literal semantic oracle for multiroute-v2."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping


EXPECTED_SCHEMA = "camp_dp_v25_industrial_v3_multiroute_v2_contract_v1"
EXPECTED_AUTHORITY = (
    "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
)
EXPECTED_PARENT = (
    "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
)
EXPECTED_CONTINUATION = (
    "89e716d0fd13acea517853f93a67b1ab68abe312ae4815f2a4b8c678c0ec3a13"
)
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_ARMS = ["pool_matched_candidate0", "Static14D", "Scene14D"]
EXPECTED_LATENCY = [
    "pool_generation",
    "atoms",
    "context",
    "weights",
    "selector_pure_incremental",
    "end_to_end",
]
EXPECTED_EXACT_PREFIX = (
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_9bef998d_89e716d0_"
)
EXPECTED_ROLES = [
    "contract",
    "contract_review",
    "hardening_matrix",
    "hardening_matrix_review",
    "hardening_focused",
    "preflight",
    "preflight_review",
    "execution",
    "execution_review",
    "evaluation",
    "evaluation_review",
    "final_docs",
]


def _canonical_sha(value: Any) -> str:
    encoded = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def review_contract_semantics(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    digest = row.pop("contract_sha256", None)
    if digest != _canonical_sha(row):
        raise ValueError("reviewer contract byte-semantic digest drifted")
    if row.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("reviewer contract schema drifted")
    authority = row.get("authority")
    if authority != {
        "source_authority_sha256": EXPECTED_AUTHORITY,
        "parent_b5ca_authority_sha256": EXPECTED_PARENT,
        "continuation_sha256": EXPECTED_CONTINUATION,
        "base_head": "af33d4e6588b885311fc3b5b4f30fc3fed2ee891",
        "fixed_dp_head": EXPECTED_FIXED_DP,
    }:
        raise ValueError("reviewer contract authority drifted")
    denominator = row.get("denominator")
    if (
        denominator.get("independent_cluster_count") != 100
        or denominator.get("paired_units") != 100
        or denominator.get("arms") != EXPECTED_ARMS
        or denominator.get("planned_arm_runs") != 300
        or denominator.get("ticks_per_arm") != 64
        or denominator.get("planned_tick_slots") != 19_200
        or denominator.get("planned_formal_model_calls") != 19_200
        or denominator.get("drop_replace_complete_case") is not False
    ):
        raise ValueError("reviewer denominator semantics drifted")
    generator = row.get("generator")
    if (
        generator.get("name")
        != "new_single_invocation_batched_k8_candidate_pool"
        or generator.get("same_ego_expanded_batch_size") != 8
        or generator.get("agent_as_ego_batch") is not False
        or generator.get("formal_model_calls_per_attempted_tick") != 1
        or generator.get("sequential_calls") != 0
        or generator.get("latent_shape") != [8, 321, 81, 4]
        or generator.get("latent_dtype") != "<f4"
        or generator.get("latent_arm_or_forward_or_time_inputs") is not False
        or generator.get("row0_zero_rows1_7_unique") is not True
        or generator.get("candidate_shape") != [8, 80, 4]
        or generator.get("neighbor_shape") != [8, 32, 80, 4]
        or generator.get("post_pool_model_dp_latent_generation_calls") != 0
    ):
        raise ValueError("reviewer generator topology drifted")
    runtime = row.get("runtime_source_transform")
    if (
        runtime.get("mapped_signal_non_red_family_same_tick_phase") != "green"
        or runtime.get("red_light_family_phase")
        != "sealed_controlled_scenario_tier_phase"
        or runtime.get("no_signal_phase") != "none"
        or runtime.get("future_phase_or_phase_remaining_consumed") is not False
        or runtime.get("actors_applied_before_tensor_conversion") is not True
        or runtime.get("signal_applied_before_tensor_conversion") is not True
        or runtime.get("certified_signal_safety_capture_required") is not True
    ):
        raise ValueError("reviewer runtime source semantics drifted")
    selector = row.get("selector")
    if (
        selector.get("production_paths")
        != ["candidate0", "Static14D", "Scene14D_no_V2I"]
        or selector.get("simplex_nonnegative_atol") != 1e-9
        or selector.get("candidate_tensor_immutable") is not True
        or selector.get("tie_break") != "lowest_eligible_index"
        or selector.get("training_or_weight_change") is not False
    ):
        raise ValueError("reviewer selector contract drifted")
    capture = row.get("capture")
    if (
        capture.get("parent_endpoint_count") != 56
        or capture.get("scalar_leaf_count") != 161
        or capture.get("accepted_reconstructable_baseline") != 119
        or capture.get("baseline_evidence_missing") != 41
        or capture.get("baseline_scientifically_inapplicable") != 1
        or capture.get("weighted_total") is not False
        or "legacy_exploratory" not in capture.get("legacy_safetycost_role", "")
    ):
        raise ValueError("reviewer evaluation topology drifted")
    statistics = row.get("statistics")
    if (
        statistics.get("independent_n") != 100
        or statistics.get("cluster_first") is not True
        or statistics.get("candidate0_reference") is not True
        or statistics.get("better_tie_worse_tie_rule")
        != "exact_zero_float64_delta"
        or statistics.get("ticks_arms_rows_as_independent_n") is not False
        or statistics.get("claim_authorized") is not False
        or statistics.get("numeric_margin_authority")
        != "numeric_margin_not_authorized_until_future_preregistration"
    ):
        raise ValueError("reviewer statistics contract drifted")
    if row.get("latency_namespaces") != EXPECTED_LATENCY:
        raise ValueError("reviewer latency namespaces drifted")
    dirs = row.get("exact_dirs")
    if set(dirs) != set(EXPECTED_ROLES):
        raise ValueError("reviewer exact-dir role set drifted")
    for role in EXPECTED_ROLES:
        if dirs[role] != EXPECTED_EXACT_PREFIX + role:
            raise ValueError("reviewer exact-dir identity drifted")
    permissions = row.get("permissions")
    if not permissions or any(permissions.values()):
        raise ValueError("reviewer forbidden permission was enabled")
    restored = deepcopy(dict(value))
    return restored
