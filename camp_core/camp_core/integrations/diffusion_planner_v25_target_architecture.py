"""Outcome-independent V25 target-architecture contract and machine gates.

This module does not execute Diffusion Planner, read holdout outcomes, or
authorize a scientific claim.  It defines the additive architecture
classification, the same-ego K=8 capability receipt contract, and the
selector-after-pool fail-closed boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

import numpy as np


AMENDMENT_SCHEMA = "camp_dp_v25_target_architecture_amendment_v1"
CAPABILITY_SCHEMA = "camp_dp_v25_same_ego_single_invocation_k8_capability_v1"
SELECTOR_GATE_SCHEMA = "camp_dp_v25_selector_after_frozen_pool_gate_v1"
FAIRNESS_DRAFT_SCHEMA = "camp_dp_v25_layered_fairness_contract_draft_v1"

FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
LEGACY_DECISION = "honest_no_claim_under_frozen_preregistered_all_gate"
CANDIDATE_COUNT = 8
BASELINE_RULE = "row0_outcome_independent_qualification_rule"
BATCH_SEQUENTIAL_ATOL = 1e-5
BATCH_SEQUENTIAL_RTOL = 1e-5

IMMUTABLE_ROOTS = {
    "b4_execution": "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
    "b4_execution_review": "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
    "corrected_evaluation": "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f",
    "corrected_evaluation_review": "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459",
    "evaluation_v2_second_correction": "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941",
    "evaluation_v2_second_correction_review": "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b",
}
CONTINUATION_LEDGER_SHA256 = (
    "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
)


def canonical_json_bytes(value: Any) -> bytes:
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


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(list(array.shape)))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def target_architecture_amendment() -> dict[str, Any]:
    """Return the frozen outcome-independent architecture amendment."""

    return {
        "schema_version": AMENDMENT_SCHEMA,
        "status": "scientific_contract_review_required",
        "outcome_independent": True,
        "superseding_additive_classification": {
            "existing_b4_architecture_class": (
                "compute_augmented_candidate_expansion_plus_reranking"
            ),
            "existing_b4_target_architecture_evidence": False,
            "existing_b4_preserved_as_exploratory_diagnostic": True,
            "target_architecture_class": (
                "single_model_invocation_same_ego_k8_pool_then_camp_rerank_select"
            ),
            "selector_may_generate_candidates": False,
            "selector_model_call_count_required": 0,
            "operational_default_batch_size": 1,
            "batch8_pass_meaning": (
                "new_single_invocation_batched_candidate_pool_generation_capability"
            ),
            "operational_default_previously_had_k8": False,
        },
        "immutable_evidence": {
            "roots": dict(IMMUTABLE_ROOTS),
            "continuation_ledger_sha256": CONTINUATION_LEDGER_SHA256,
            "fixed_dp_head": FIXED_DP_HEAD,
            "legacy_claim_decision": LEGACY_DECISION,
            "legacy_values_mutated": False,
            "sealed_artifacts_or_cas_written": False,
        },
        "capability_contract": {
            "development_nonholdout_only": True,
            "formal_model_forward_directly_verified": True,
            "same_ego_source_batch_size": 1,
            "candidate_axis": "expanded_same_ego_model_batch_axis",
            "candidate_count": CANDIDATE_COUNT,
            "primary_pool_model_invocation_count": 1,
            "diagnostic_repeat_model_invocation_count": 1,
            "diagnostic_sequential_model_invocation_count": CANDIDATE_COUNT,
            "batch_sequential_atol": BATCH_SEQUENTIAL_ATOL,
            "batch_sequential_rtol": BATCH_SEQUENTIAL_RTOL,
            "all_rows_finite_required": True,
            "all_row_sha_unique_required": True,
            "deterministic_repeat_required": True,
            "global_rng_unchanged_required": True,
            "temperature_input_policy": (
                "record_tensor_and_sha_or_explicit_not_exposed_by_fixed_dp_interface"
            ),
            "fixed_dp_source_or_weights_modification_allowed": False,
        },
        "selector_after_pool_contract": {
            "schema_version": SELECTOR_GATE_SCHEMA,
            "pool_frozen_before_selector": True,
            "arms": ["pool_baseline", "Static14D", "Scene14D"],
            "all_arms_same_pool_sha_required": True,
            "all_arms_same_pool_id_required": True,
            "all_arms_same_input_model_forward_bindings_required": True,
            "selector_model_call_count_required": 0,
            "latent_replacement_allowed": False,
            "model_callback_allowed": False,
            "trajectory_generation_allowed": False,
            "baseline_rule": BASELINE_RULE,
            "outcome_selected_rule": False,
        },
        "fairness_contract_draft": fairness_contract_draft(),
        "training_decision": {
            "training_authorized": False,
            "batch_vs_sequential_distribution_comparison_required": True,
            "if_nonequivalent": (
                "return_drift_and_possible_ood_package_without_training"
            ),
        },
        "claim_boundary": {
            "new_scientific_effect_claim_authorized": False,
            "fresh_authorized": False,
            "closed_loop_authorized": False,
            "training_authorized": False,
            "promotion_or_deployment_authorized": False,
            "next_authority": "high_incremental_architecture_qualification_review",
        },
    }


def fairness_contract_draft() -> dict[str, Any]:
    return {
        "schema_version": FAIRNESS_DRAFT_SCHEMA,
        "status": "draft_frozen_not_executed",
        "state_matched_offline_selector_replay": {
            "same_frozen_state": True,
            "same_k8_tensor": True,
            "arms": ["pool_baseline", "Static14D", "Scene14D"],
            "purpose": "isolate_reranker",
            "scientific_execution_authorized": False,
        },
        "compute_matched_closed_loop": {
            "each_arm_uses_same_versioned_pool_generator_contract": True,
            "each_arm_k8_compute_budget_equal": True,
            "post_divergence_cross_arm_tensor_identity_claimed": False,
            "reason": "arm_states_diverge_after_closed_loop_branching",
            "execution_authorized": False,
        },
        "latency_accounting": {
            "stages": [
                "pool_generation",
                "atoms",
                "context",
                "weight",
                "selector",
                "total",
            ],
            "baseline_includes_pool_generation_cost": True,
        },
        "statistics_endpoints_claim": {
            "authorized": False,
            "requires_future_prospective_preregistration": True,
        },
    }


def validate_target_architecture_amendment(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    expected = target_architecture_amendment()
    candidate = _plain_object(value, "architecture amendment")
    if candidate != expected:
        raise ValueError("target architecture amendment literal contract drifted")
    return candidate


@dataclass(frozen=True)
class FrozenCandidatePool:
    pool_id: str
    tensor_sha256: str
    row_sha256: tuple[str, ...]
    input_sha256: str
    model_sha256: str
    forward_invocation_id: str
    tensor: np.ndarray


def freeze_candidate_pool(
    tensor: np.ndarray,
    *,
    input_sha256: str,
    model_sha256: str,
    forward_invocation_id: str,
) -> FrozenCandidatePool:
    array = np.array(tensor, copy=True, order="C")
    if (
        array.ndim != 3
        or array.shape[0] != CANDIDATE_COUNT
        or array.shape[2] < 2
        or not np.all(np.isfinite(array))
    ):
        raise ValueError("candidate pool must be finite [8,T,D>=2]")
    tensor_sha = array_sha256(array)
    rows = tuple(array_sha256(row) for row in array)
    bindings = {
        "tensor_sha256": tensor_sha,
        "input_sha256": _sha(input_sha256, "input_sha256"),
        "model_sha256": _sha(model_sha256, "model_sha256"),
        "forward_invocation_id": _nonempty(
            forward_invocation_id, "forward_invocation_id"
        ),
    }
    pool_id = canonical_sha256(bindings)
    array.setflags(write=False)
    return FrozenCandidatePool(
        pool_id=pool_id,
        tensor_sha256=tensor_sha,
        row_sha256=rows,
        input_sha256=bindings["input_sha256"],
        model_sha256=bindings["model_sha256"],
        forward_invocation_id=bindings["forward_invocation_id"],
        tensor=array,
    )


class SelectorModelCallGuard:
    """Fail closed if a selector attempts any model/generation operation."""

    def __init__(self) -> None:
        self.model_call_count = 0
        self.latent_replacement_count = 0
        self.trajectory_generation_count = 0

    def model_callback(self, *_args: Any, **_kwargs: Any) -> None:
        self.model_call_count += 1
        raise RuntimeError("selector attempted a forbidden DP/model call")

    def replace_latent(self, *_args: Any, **_kwargs: Any) -> None:
        self.latent_replacement_count += 1
        raise RuntimeError("selector attempted forbidden latent replacement")

    def generate_trajectory(self, *_args: Any, **_kwargs: Any) -> None:
        self.trajectory_generation_count += 1
        raise RuntimeError("selector attempted forbidden trajectory generation")

    def assert_zero(self) -> None:
        if (
            self.model_call_count != 0
            or self.latent_replacement_count != 0
            or self.trajectory_generation_count != 0
        ):
            raise ValueError("selector-after-pool forbidden call count is nonzero")


def qualify_selector_after_pool(
    pool: FrozenCandidatePool,
    *,
    arm: str,
    selector: Callable[[FrozenCandidatePool, SelectorModelCallGuard], int],
) -> dict[str, Any]:
    if arm not in {"pool_baseline", "Static14D", "Scene14D"}:
        raise ValueError("unknown selector-after-pool arm")
    before_sha = array_sha256(pool.tensor)
    if before_sha != pool.tensor_sha256:
        raise ValueError("candidate pool drifted before selector")
    guard = SelectorModelCallGuard()
    selected = selector(pool, guard)
    guard.assert_zero()
    if isinstance(selected, bool) or not isinstance(selected, (int, np.integer)):
        raise TypeError("selected index must be an integer")
    selected_index = int(selected)
    if not 0 <= selected_index < CANDIDATE_COUNT:
        raise ValueError("selected index outside frozen K8")
    if arm == "pool_baseline" and selected_index != 0:
        raise ValueError("pool baseline must select frozen row0")
    after_sha = array_sha256(pool.tensor)
    if after_sha != before_sha:
        raise ValueError("selector mutated the frozen candidate tensor")
    return {
        "schema_version": SELECTOR_GATE_SCHEMA,
        "status": "passed_selector_after_frozen_pool_gate",
        "arm": arm,
        "pool_id": pool.pool_id,
        "candidate_tensor_sha256": pool.tensor_sha256,
        "input_sha256": pool.input_sha256,
        "model_sha256": pool.model_sha256,
        "forward_invocation_id": pool.forward_invocation_id,
        "selected_index": selected_index,
        "selected_row_sha256": pool.row_sha256[selected_index],
        "baseline_rule": BASELINE_RULE if arm == "pool_baseline" else None,
        "model_call_count_after_pool": 0,
        "latent_replacement_count_after_pool": 0,
        "trajectory_generation_count_after_pool": 0,
        "candidate_tensor_immutable": True,
        "outcome_values_read": False,
    }


def validate_capability_report(value: Mapping[str, Any]) -> dict[str, Any]:
    report = _plain_object(value, "capability report")
    required = {
        "schema_version",
        "status",
        "authority",
        "fixed_dp",
        "source_state",
        "candidate_axis",
        "latent",
        "temperature",
        "primary_pool_invocation",
        "determinism",
        "batch_vs_sequential",
        "selector_after_pool",
        "rng_boundary",
        "training_decision",
        "claim_boundary",
    }
    if set(report) != required:
        raise ValueError("capability report fields drifted")
    if report["schema_version"] != CAPABILITY_SCHEMA:
        raise ValueError("capability schema drifted")
    if report["status"] not in {
        "passed_same_ego_single_invocation_k8_capability",
        "blocked_same_ego_single_invocation_k8_capability",
    }:
        raise ValueError("capability status drifted")
    fixed = _plain_object(report["fixed_dp"], "fixed_dp")
    if (
        fixed.get("head") != FIXED_DP_HEAD
        or fixed.get("source_modified") is not False
        or fixed.get("checkpoint_modified") is not False
    ):
        raise ValueError("fixed DP authority drifted")
    state = _plain_object(report["source_state"], "source_state")
    if (
        state.get("role") != "development_nonholdout"
        or state.get("simulator_steps_advanced") != 0
        or state.get("source_batch_size") != 1
    ):
        raise ValueError("capability source state is not development same-ego")
    axis = _plain_object(report["candidate_axis"], "candidate_axis")
    if (
        axis.get("semantics") != "same_ego_candidate_batch"
        or axis.get("candidate_count") != CANDIDATE_COUNT
        or axis.get("agent_as_ego_batch") is not False
        or axis.get("all_nonlatent_rows_identical") is not True
    ):
        raise ValueError("candidate axis semantics drifted")
    primary = _plain_object(
        report["primary_pool_invocation"], "primary_pool_invocation"
    )
    if (
        primary.get("model_call_count") != 1
        or primary.get("output_shape", [None])[0] != CANDIDATE_COUNT
        or primary.get("finite") is not True
        or primary.get("unique_row_sha256_count") != CANDIDATE_COUNT
    ):
        raise ValueError("single-invocation K8 evidence drifted")
    deterministic = _plain_object(report["determinism"], "determinism")
    if (
        deterministic.get("repeat_model_call_count") != 1
        or deterministic.get("exact_equal") is not True
    ):
        raise ValueError("determinism evidence drifted")
    relation = _plain_object(
        report["batch_vs_sequential"], "batch_vs_sequential"
    )
    if (
        relation.get("sequential_model_call_count") != CANDIDATE_COUNT
        or relation.get("within_frozen_tolerance") is not True
        or relation.get("atol") != BATCH_SEQUENTIAL_ATOL
        or relation.get("rtol") != BATCH_SEQUENTIAL_RTOL
    ):
        raise ValueError("batch/sequential relation drifted")
    selector = _plain_object(report["selector_after_pool"], "selector_after_pool")
    arms = selector.get("arms")
    if type(arms) is not list or [row.get("arm") for row in arms] != [
        "pool_baseline",
        "Static14D",
        "Scene14D",
    ]:
        raise ValueError("selector arm inventory drifted")
    pool_ids = {row.get("pool_id") for row in arms}
    tensor_shas = {row.get("candidate_tensor_sha256") for row in arms}
    if (
        len(pool_ids) != 1
        or len(tensor_shas) != 1
        or any(row.get("model_call_count_after_pool") != 0 for row in arms)
    ):
        raise ValueError("selector-after-pool binding drifted")
    if report["training_decision"].get("training_executed") is not False:
        raise ValueError("training boundary drifted")
    claim = _plain_object(report["claim_boundary"], "claim_boundary")
    if (
        claim.get("fresh_or_closed_loop_executed") is not False
        or claim.get("scientific_effect_claim_authorized") is not False
        or claim.get("legacy_claim_decision") != LEGACY_DECISION
    ):
        raise ValueError("claim boundary drifted")
    if report["status"] == "passed_same_ego_single_invocation_k8_capability":
        if report["rng_boundary"].get("unchanged") is not True:
            raise ValueError("global RNG boundary drifted")
    return report


def _plain_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be a SHA256 string")
    int(value, 16)
    return value


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value
