"""Outcome-independent batch8-only V25 calibration contract design.

This module defines topology and pure mathematics only.  It does not execute
the model, pool generator, selectors, calibration, threshold materialization,
validation, or closed loop.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_batch8_primary_calibration_contract_v1"
ARTIFACT_SCHEMA = "camp_dp_v25_batch8_primary_calibration_contract_artifact_v1"
AUTHORITY_SCHEMA = (
    "camp_dp_v25_batch8_primary_calibration_contract_design_high_authority_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
POINTER_HEAD = "b5b965ff3e2f3b91f7b6b0ab482d1b05ace4f320"
PRIMARY_MODE = "single_invocation_batch8"
PHASE = "batch8_within"
GENERATOR = "new_single_invocation_batched_k8_candidate_pool"

HIGH_AUTHORITY_JSON = (
    '{"actual_calibration_acquisition_authorized":false,'
    '"batch8_first_state_diagnostic_root_sha256":"6a9e1a364b6d25716a471d340'
    '39553b11521c2d911563df0e3ee0edf1ed3eec5",'
    '"batch8_first_state_review_root_sha256":"92e33a3e1747764a65d6d6b8e38645'
    'f7faa9825b2b08c980255025ac840073c3",'
    '"batch8_primary_contract_review_root_sha256":"a0cd179311b5ce1fd18b7e76415'
    '4d92041bfda57216c0be2365aa20100133978",'
    '"batch8_primary_contract_root_sha256":"15cf642f5abcb1cd44687e8f4298517f47'
    'e8c878633602e9b42fcffe7c30e5d7",'
    '"calibration_outcomes_may_not_set_training_support_thresholds":true,'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"cross_mode_numeric_endpoint_count":0,'
    '"decision":"authorized_outcome_independent_batch8_only_calibration_contract_'
    'design_and_independent_review",'
    '"development_calibration_state_count":64,'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"fixed_dp_head":"7a1d33da277a1992ec474b5383a0c963c72e04e4",'
    '"fixed_dp_model_weights_atoms_change_authorized":false,'
    '"formal_phase_keys":["batch8_within"],'
    '"future_acquisition_requires_new_high_authority":true,'
    '"hard_gates":["single_model_call_same_ego_B8","latent_finite_unique8",'
    '"candidate_neighbor_finite","candidate_unique8","fingerprints_exact",'
    '"candidate_tensor_immutable","post_pool_model_dp_latent_generation_calls_zero",'
    '"static_scene_masks_nonempty_and_selected_action_bound"],'
    '"no_weighted_total":true,"old_artifacts_roots_cas_immutable":true,'
    '"pass_scope":"bounded_repeatability_and_prespecified_training_support_only_no_'
    'benefit_or_general_ood_claim","planned_model_invocations":320,'
    '"planned_pair_receipts":640,"planned_static_scene_selector_receipts":640,'
    '"pointer_head":"b5b965ff3e2f3b91f7b6b0ab482d1b05ace4f320",'
    '"primary_mode":"single_invocation_batch8",'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"repeats_per_state":5,'
    '"schema_version":"camp_dp_v25_batch8_primary_calibration_contract_design_high_'
    'authority_v1","sequential_scope":"legacy_non_gating_diagnostic_only",'
    '"statistical_unit":"state",'
    '"threshold_design":"per_state_q99_higher_over_10_pairs_then_64_state_'
    'bootstrap_ucb_with_frozen_resolution_floor",'
    '"threshold_materialization_authorized":false,'
    '"training_support_audit_required":true,'
    '"training_support_thresholds_must_derive_only_from_sealed_training_artifacts_'
    'before_acquisition":true,'
    '"validation_closed_loop_fresh_holdout_training_authorized":false,'
    '"within_numeric_endpoint_count":22,"within_repeat_pairs_per_state":10}'
)
HIGH_AUTHORITY_SHA256 = (
    "81dbf890717297cebf477ee9192c98c5c4f641bd3b976cab5154d6da872a5f7b"
)

TRAINING_ROOT = "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
TRAINING_SCALE_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
V5_CONTRACT_ROOT = "78584ecc74a1a4f42e18fe0f4ee81e4fd0f48e98e33fd56c7128954c2ce0e4c6"
V5_CONTRACT_REVIEW_ROOT = (
    "3e0f5c5247fc3fc4e877d0c2597022a5b31c2e297023fd39cc0a58060c0491e5"
)
V5_FOCUSED_ROOT = "aaeb20cd5278bc8566c621eb4c654e8250d690559502e5f9debf539477b87388"
V5_FINAL_DOCS_ROOT = (
    "6b70bc461a91b17e7a16788ac943daa50a715a73a2f8401811efc751d9b2694b"
)
PRIMARY_CONTRACT_ROOT = (
    "15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7"
)
PRIMARY_CONTRACT_REVIEW_ROOT = (
    "a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978"
)
FIRST_STATE_ROOT = "6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5"
FIRST_STATE_REVIEW_ROOT = (
    "92e33a3e1747764a65d6d6b8e38645f7faa9825b2b08c980255025ac840073c3"
)

ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
ATOM_SCALES = (
    1315.8699005569194,
    5202.799211059529,
    6271.815530966072,
    1.8198095597643642,
    93.9868956456402,
    118.0999680225589,
    147.7588020436164,
    2902.5946193744476,
    56.41673006314134,
    8.752781754669478,
    40.5,
    1.0534432082550127,
    28.22741708820042,
    2.608169233773669,
)

EXACT_DIR_KEYS = ("contract", "contract_review", "focused", "final_docs_focused")
SOURCE_KEYS = ("producer", "reviewer", "freeze_script", "review_script", "tests")
PROHIBITED_RUNS = (
    "model",
    "pool",
    "selector",
    "calibration",
    "threshold_materialization",
    "validation",
    "closed_loop",
    "fresh",
    "holdout",
    "training",
    "retraining",
)
HARD_GATES = (
    "single_model_call_same_ego_B8",
    "latent_finite_unique8",
    "candidate_neighbor_finite",
    "candidate_unique8",
    "fingerprints_exact",
    "candidate_tensor_immutable",
    "post_pool_model_dp_latent_generation_calls_zero",
    "static_scene_masks_nonempty_and_selected_action_bound",
)
POST_POOL_ZERO_FIELDS = (
    "model_call_count",
    "dp_call_count",
    "latent_generation_count",
    "candidate_generation_count",
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


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def endpoint_registry() -> list[dict[str, Any]]:
    """Return the exact 22 batch8-within numeric endpoints."""

    records: list[dict[str, Any]] = []
    for index, name in enumerate(ATOM_NAMES):
        records.append(
            _endpoint(
                f"atom.normalized_delta.{index:02d}.{name}",
                f"max_row_abs((a[:,{index}]-b[:,{index}])/training_scale[{index}])",
                "training_scale_normalized",
                1e-8,
                "[8,14]_float64_pair",
                "all_8_rows_and_training_scale_finite;scale_gt_0",
            )
        )
    for endpoint_id, formula, units, floor, shape in (
        (
            "trajectory.ego.position_max_m",
            "max_row_t_l2_xy",
            "m",
            1e-4,
            "[8,80,2]_float64_pair",
        ),
        (
            "trajectory.ego.heading_max_rad",
            "max_row_t_abs_wrap_to_pi_delta",
            "rad",
            1e-5,
            "[8,80]_float64_pair",
        ),
        (
            "trajectory.ego.speed_max_mps",
            "max_row_t_abs_delta",
            "m/s",
            1e-4,
            "[8,80]_float64_pair",
        ),
        (
            "trajectory.neighbor.position_max_m",
            "max_row_actor_t_l2_xy_after_exact_actor_slot_fingerprint",
            "m",
            1e-4,
            "[8,A,80,2]_float64_pair_A_ge_1",
        ),
        (
            "trajectory.neighbor.heading_max_rad",
            "max_row_actor_t_abs_wrap_to_pi_delta",
            "rad",
            1e-5,
            "[8,A,80]_float64_pair_A_ge_1",
        ),
        (
            "trajectory.neighbor.speed_max_mps",
            "max_row_actor_t_abs_delta",
            "m/s",
            1e-4,
            "[8,A,80]_float64_pair_A_ge_1",
        ),
        (
            "score.static14d.abs_delta",
            "max_shared_eligible_abs_score_delta",
            "dimensionless",
            1e-9,
            "[8]_float64_pair_plus_equal_masks",
        ),
        (
            "score.scene14d.abs_delta",
            "max_shared_eligible_abs_score_delta",
            "dimensionless",
            1e-9,
            "[8]_float64_pair_plus_equal_masks",
        ),
    ):
        applicability = (
            "masks_equal_and_nonempty_and_shared_eligible_scores_finite"
            if endpoint_id.startswith("score.")
            else "exact_shape_actor_roster_and_all_values_finite"
        )
        records.append(
            _endpoint(endpoint_id, formula, units, floor, shape, applicability)
        )
    if len(records) != 22 or len({r["endpoint_id"] for r in records}) != 22:
        raise AssertionError("batch8-within registry cardinality drifted")
    return records


def empirical_q99_higher(values: Sequence[float]) -> float:
    array = _finite_vector(values, 10, "within-state pair values")
    return float(np.sort(array, kind="mergesort")[9])


def bootstrap_ucb(
    state_q99_values: Sequence[float],
    *,
    resolution_floor: float,
) -> float:
    values = _finite_vector(state_q99_values, 64, "state q99 values")
    floor = _positive(resolution_floor, "resolution floor")
    generator = np.random.Generator(np.random.PCG64DXSM(825071))
    indices = generator.integers(
        0, 64, size=(10000, 64), endpoint=False, dtype=np.int64
    )
    statistics = np.sort(values[indices], axis=1, kind="mergesort")[:, 63]
    upper = float(np.sort(statistics, kind="mergesort")[9500])
    return max(floor, upper)


def planned_run_ids() -> list[str]:
    return [
        f"development_calibration:{state:03d}:single_invocation_batch8:repeat{repeat}"
        for state in range(64)
        for repeat in range(5)
    ]


def planned_pair_ids() -> list[str]:
    return [
        f"development_calibration:{state:03d}:batch8_within:r{left}_r{right}"
        for state in range(64)
        for left in range(5)
        for right in range(left + 1, 5)
    ]


def hard_gate_failures(run_receipt: Mapping[str, Any]) -> list[str]:
    """Derive hard failures from a future typed run receipt.

    This function is for synthetic contract tests only in this design phase.
    """

    receipt = _plain_dict(run_receipt, "run receipt")
    expected = {
        "formal_model_invocation_count",
        "source_ego_state_count",
        "expanded_batch_size",
        "agent_as_ego_batch",
        "latent_finite",
        "latent_unique_count",
        "candidate_finite",
        "candidate_unique_count",
        "neighbor_finite",
        "fingerprints_exact",
        "candidate_tensor_pre_sha256",
        "candidate_tensor_post_sha256",
        "post_pool_calls",
        "static14d",
        "scene14d",
    }
    if set(receipt) != expected:
        raise ValueError("run receipt keyset drifted")
    failures: list[str] = []
    if (
        receipt["formal_model_invocation_count"] != 1
        or receipt["source_ego_state_count"] != 1
        or receipt["expanded_batch_size"] != 8
        or receipt["agent_as_ego_batch"] is not False
    ):
        failures.append("single_model_call_same_ego_B8")
    if (
        receipt["latent_finite"] is not True
        or receipt["latent_unique_count"] != 8
    ):
        failures.append("latent_finite_unique8")
    if (
        receipt["candidate_finite"] is not True
        or receipt["neighbor_finite"] is not True
    ):
        failures.append("candidate_neighbor_finite")
    if receipt["candidate_unique_count"] != 8:
        failures.append("candidate_unique8")
    if receipt["fingerprints_exact"] is not True:
        failures.append("fingerprints_exact")
    for key in ("candidate_tensor_pre_sha256", "candidate_tensor_post_sha256"):
        _sha(receipt[key], key)
    if receipt["candidate_tensor_pre_sha256"] != receipt["candidate_tensor_post_sha256"]:
        failures.append("candidate_tensor_immutable")
    calls = _plain_dict(receipt["post_pool_calls"], "post_pool_calls")
    if set(calls) != set(POST_POOL_ZERO_FIELDS) or any(
        type(calls[key]) is not int or calls[key] != 0 for key in calls
    ):
        failures.append("post_pool_model_dp_latent_generation_calls_zero")
    for arm in ("static14d", "scene14d"):
        arm_receipt = _plain_dict(receipt[arm], arm)
        if set(arm_receipt) != {
            "mask_nonempty",
            "selected_index",
            "selected_action_sha256",
            "pool_id",
            "candidate_tensor_sha256",
        }:
            raise ValueError(f"{arm} receipt keyset drifted")
        try:
            _sha(arm_receipt["selected_action_sha256"], f"{arm}.action")
            _sha(arm_receipt["candidate_tensor_sha256"], f"{arm}.tensor")
        except (TypeError, ValueError):
            failures.append("static_scene_masks_nonempty_and_selected_action_bound")
            continue
        if (
            arm_receipt["mask_nonempty"] is not True
            or type(arm_receipt["selected_index"]) is not int
            or not 0 <= arm_receipt["selected_index"] < 8
            or type(arm_receipt["pool_id"]) is not str
            or not arm_receipt["pool_id"]
            or arm_receipt["candidate_tensor_sha256"]
            != receipt["candidate_tensor_pre_sha256"]
        ):
            failures.append("static_scene_masks_nonempty_and_selected_action_bound")
    return sorted(set(failures), key=HARD_GATES.index)


def contract_design(
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    _git_head(implementation_head)
    exact = _exact_map(exact_dirs, EXACT_DIR_KEYS, "exact_dirs", sha=False)
    sources = _exact_map(source_sha256, SOURCE_KEYS, "source_sha256", sha=True)
    registry = endpoint_registry()
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "scientific_contract_review_required_acquisition_unauthorized",
        "high_authority": {
            "schema_version": AUTHORITY_SCHEMA,
            "canonical_json_ascii": HIGH_AUTHORITY_JSON,
            "sha256": HIGH_AUTHORITY_SHA256,
        },
        "implementation": {
            "head": implementation_head,
            "exact_dirs": exact,
            "source_sha256": sources,
        },
        "preserved_evidence": {
            "v5_contract_root_sha256": V5_CONTRACT_ROOT,
            "v5_contract_review_root_sha256": V5_CONTRACT_REVIEW_ROOT,
            "v5_focused_root_sha256": V5_FOCUSED_ROOT,
            "v5_final_docs_root_sha256": V5_FINAL_DOCS_ROOT,
            "batch8_primary_contract_root_sha256": PRIMARY_CONTRACT_ROOT,
            "batch8_primary_contract_review_root_sha256": (
                PRIMARY_CONTRACT_REVIEW_ROOT
            ),
            "batch8_first_state_root_sha256": FIRST_STATE_ROOT,
            "batch8_first_state_review_root_sha256": FIRST_STATE_REVIEW_ROOT,
            "old_artifacts_roots_cas_immutable": True,
        },
        "generator": {
            "name": GENERATOR,
            "mode": PRIMARY_MODE,
            "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
            "formal_model_invocations_per_run": 1,
            "expanded_batch_size": 8,
            "source_ego_state_count": 1,
            "agent_as_ego_batch": False,
            "candidate0_rule": "candidate_tensor_row0",
        },
        "calibration_topology": {
            "split": "development_calibration",
            "state_count": 64,
            "repeats_per_state": 5,
            "planned_run_count": 320,
            "planned_model_invocation_count": 320,
            "unordered_repeat_pairs_per_state": 10,
            "planned_pair_receipt_count": 640,
            "selector_arms": ["Static14D", "Scene14D"],
            "selector_receipts_per_arm": 320,
            "planned_static_scene_selector_receipt_count": 640,
            "statistical_unit": "state",
            "row_tick_as_independent_unit_allowed": False,
            "drop_replace_or_complete_case_allowed": False,
            "failure_retention": "all_320_run_slots_and_640_pairs_retained",
            "run_id_sha256": sha256_json(planned_run_ids()),
            "pair_id_sha256": sha256_json(planned_pair_ids()),
        },
        "numeric_contract": {
            "phase_keys": [PHASE],
            "within_numeric_endpoint_count": 22,
            "cross_mode_numeric_endpoint_count": 0,
            "sequential_numeric_endpoint_count": 0,
            "endpoint_registry": registry,
            "endpoint_registry_sha256": sha256_json(registry),
            "pair_cache_role": "derived_from_typed_raw_receipts_only",
            "missing_or_nonfinite": "retained_and_qualification_fail_closed",
        },
        "threshold_contract": {
            "materialization_authorized": False,
            "within_state": {
                "pair_count": 10,
                "statistic": "empirical_q99_higher",
                "formula": "sorted_values[ceil(0.99*(10-1))]=sorted_values[9]",
            },
            "across_states": {
                "state_count": 64,
                "state_statistic": "q99_higher",
                "bootstrap_resamples": 10000,
                "sample_size": 64,
                "with_replacement": True,
                "rng": "numpy.random.Generator(PCG64DXSM(825071))",
                "index_generation": (
                    "integers(0,64,size=(10000,64),endpoint=False,dtype=int64)"
                ),
                "per_resample_index": 63,
                "upper_confidence_quantile": 0.95,
                "upper_index": 9500,
                "final": "max(resolution_floor,sorted_bootstrap[9500])",
            },
            "comparison": "pair_error <= frozen_threshold_is_pass",
            "exceedance": "pair_error > frozen_threshold",
            "all_22_endpoints_required": True,
            "weighted_total": False,
        },
        "training_support_audit": _training_support_contract(),
        "hard_gate_contract": {
            "required_per_run": list(HARD_GATES),
            "post_pool_zero_call_fields": list(POST_POOL_ZERO_FIELDS),
            "static_scene_selector_receipts_must_bind_same_pool_tensor": True,
            "any_failure": "retain_run_and_fail_qualification",
            "hard_failure_categories": [
                "runtime_instability",
                "selector_functional_failure",
                "authority_failure",
            ],
        },
        "decision_semantics": {
            "qualification_pass_boolean": (
                "all_320_hard_receipts_pass AND all_22_bounded_repeatability_"
                "endpoints_pass AND prespecified_training_support_audit_pass"
            ),
            "training_support_missing_result": "evidence_missing_training_support_gap",
            "runtime_failure_result": "runtime_instability",
            "selector_failure_result": "selector_functional_failure",
            "pass_scope": (
                "bounded_repeatability_and_prespecified_training_support_only_"
                "no_benefit_or_general_ood_claim"
            ),
            "no_retraining_conclusion_authorized": False,
            "benefit_claim_authorized": False,
            "general_ood_claim_authorized": False,
            "weighted_total": False,
        },
        "sequential_legacy": {
            "mode": "sequential_batch1_x8",
            "scope": "legacy_non_gating_diagnostic_only",
            "formal_denominator_count": 0,
            "pair_receipt_count": 0,
            "numeric_key_count": 0,
            "threshold_contribution_count": 0,
            "hard_gate_contribution_count": 0,
            "primary_latency_contribution_count": 0,
        },
        "run_counters": {key: 0 for key in PROHIBITED_RUNS},
        "prohibitions": {
            "actual_calibration_acquisition": True,
            "threshold_materialization": True,
            "validation_closed_loop_fresh_holdout_training": True,
            "fixed_dp_model_weights_atoms_change": True,
            "old_artifact_or_cas_write": True,
            "claim_promotion_deployment": True,
        },
    }
    return contract


def validate_contract_design(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _plain_dict(value, "contract")
    implementation = _plain_dict(candidate.get("implementation"), "implementation")
    expected = contract_design(
        implementation_head=implementation.get("head"),
        exact_dirs=implementation.get("exact_dirs"),
        source_sha256=implementation.get("source_sha256"),
    )
    if candidate != expected:
        raise ValueError("batch8 calibration contract literal drifted")
    if hashlib.sha256(HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest() != (
        HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("High authority hash drifted")
    if json.dumps(
        json.loads(HIGH_AUTHORITY_JSON),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ) != HIGH_AUTHORITY_JSON:
        raise ValueError("High authority is not canonical")
    return deepcopy(candidate)


def _training_support_contract() -> dict[str, Any]:
    return {
        "required_before_any_future_acquisition": True,
        "current_status": "evidence_missing_prespecified_training_support_reference",
        "current_authority_binds_only_atom_normalization_scales": True,
        "scale_authority": {
            "artifact_root_sha256": TRAINING_ROOT,
            "relative_path": "runtime_atom_scales.json",
            "file_sha256": TRAINING_SCALE_SHA256,
            "names_json_pointer": "/atom_names",
            "scales_json_pointer": "/scales",
            "index": [
                {"index": i, "name": name, "scale": scale}
                for i, (name, scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES))
            ],
            "zero_or_nonfinite": "authority_failure",
        },
        "missing_prespecified_reference": {
            "same_ego_batch8_training_candidate_rows": True,
            "static14d_training_scores_masks_selected_actions": True,
            "scene14d_training_scores_masks_selected_actions": True,
            "sealed_reference_artifact_root_and_independent_review": True,
        },
        "future_reference_schema": {
            "source": "sealed_training_artifacts_only",
            "calibration_or_validation_values_allowed": False,
            "continuous_fields": [
                *(f"normalized_atom.{i:02d}.{name}" for i, name in enumerate(ATOM_NAMES)),
                "score.static14d",
                "score.scene14d",
                "margin.static14d",
                "margin.scene14d",
                "eligible_count.static14d",
                "eligible_count.scene14d",
            ],
            "reference_interval": {
                "lower": "empirical_q0_005_lower",
                "upper": "empirical_q0_995_higher",
                "lower_formula": "sorted_values[floor(0.005*(n-1))]",
                "upper_formula": "sorted_values[ceil(0.995*(n-1))]",
                "finite_training_sample_count_minimum": 1000,
                "equality_inside": "lower <= value <= upper",
            },
            "calibration_state_coverage": {
                "row_observations_per_state": 40,
                "formula": "inside_reference_count/40",
                "minimum_per_state": 0.95,
                "equality_passes": True,
                "required_passing_states": 61,
                "state_count": 64,
            },
            "multiplicity": (
                "all_20_prespecified_fields_must_pass_no_weighted_total"
            ),
            "mask_and_action_hard_conditions": (
                "nonempty_masks_and_selected_action_bound_for_both_arms_each_run"
            ),
        },
        "thresholds_materialized": False,
        "calibration_may_set_training_support_thresholds": False,
        "no_retraining_conclusion_authorized": False,
        "future_acquisition_requires_new_high_authority": True,
    }


def _endpoint(
    endpoint_id: str,
    formula: str,
    units: str,
    resolution_floor: float,
    input_shape: str,
    applicability: str,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "mode": PRIMARY_MODE,
        "endpoint_id": endpoint_id,
        "formula": formula,
        "units": units,
        "resolution_floor": resolution_floor,
        "input_shape": input_shape,
        "applicability": applicability,
        "missing_rule": "retain_state_and_fail_closed",
        "finite_required": True,
        "direction": "lower",
    }


def _finite_vector(value: Sequence[float], size: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (size,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must be finite [{size}]")
    return array


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be finite positive")
    return result


def _plain_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _exact_map(
    value: Mapping[str, str],
    keys: tuple[str, ...],
    label: str,
    *,
    sha: bool,
) -> dict[str, str]:
    if type(value) is not dict or tuple(value.keys()) != keys:
        raise ValueError(f"{label} ordered keyset drifted")
    result = dict(value)
    for key, item in result.items():
        if type(item) is not str or not item:
            raise ValueError(f"{label}.{key} must be nonempty")
        if sha:
            _sha(item, f"{label}.{key}")
    return result


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be SHA256")
    int(value, 16)
    return value


def _git_head(value: Any) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError("implementation HEAD must be a git SHA")
    int(value, 16)
    return value
