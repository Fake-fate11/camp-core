"""Independent literal review of the V25 batch8-only calibration contract.

The reviewer intentionally does not import the producer contract, threshold,
selector, pool, or model modules.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA = "camp_dp_v25_batch8_primary_calibration_contract_v1"
AUTHORITY_SHA = "81dbf890717297cebf477ee9192c98c5c4f641bd3b976cab5154d6da872a5f7b"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TRAINING_ROOT = "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
TRAINING_SCALE_SHA = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
V5_ROOT = "78584ecc74a1a4f42e18fe0f4ee81e4fd0f48e98e33fd56c7128954c2ce0e4c6"
PRIMARY_ROOT = "15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7"
FIRST_STATE_ROOT = "6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5"
EXACT_DIR_KEYS = ("contract", "contract_review", "focused", "final_docs_focused")
SOURCE_KEYS = ("producer", "reviewer", "freeze_script", "review_script", "tests")
RUN_KEYS = {
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
}
HARD_GATES = [
    "single_model_call_same_ego_B8",
    "latent_finite_unique8",
    "candidate_neighbor_finite",
    "candidate_unique8",
    "fingerprints_exact",
    "candidate_tensor_immutable",
    "post_pool_model_dp_latent_generation_calls_zero",
    "static_scene_masks_nonempty_and_selected_action_bound",
]
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


def independent_literal_review(
    value: Mapping[str, Any],
    *,
    expected_implementation_head: str,
    expected_exact_dirs: Mapping[str, str],
    expected_source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    contract = _object(value, "contract")
    _keys(
        contract,
        {
            "schema_version",
            "status",
            "high_authority",
            "implementation",
            "preserved_evidence",
            "generator",
            "calibration_topology",
            "numeric_contract",
            "threshold_contract",
            "training_support_audit",
            "hard_gate_contract",
            "decision_semantics",
            "sequential_legacy",
            "run_counters",
            "prohibitions",
        },
        "contract",
    )
    if (
        contract["schema_version"] != SCHEMA
        or contract["status"]
        != "scientific_contract_review_required_acquisition_unauthorized"
    ):
        raise ValueError("contract identity drifted")
    _review_authority(contract["high_authority"])
    _review_implementation(
        contract["implementation"],
        expected_implementation_head,
        expected_exact_dirs,
        expected_source_sha256,
    )
    _review_preserved(contract["preserved_evidence"])
    _review_generator(contract["generator"])
    _review_topology(contract["calibration_topology"])
    _review_numeric(contract["numeric_contract"])
    _review_threshold(contract["threshold_contract"])
    _review_training_support(contract["training_support_audit"])
    _review_hard(contract["hard_gate_contract"])
    _review_decision(contract["decision_semantics"])
    _review_sequential(contract["sequential_legacy"])
    counters = _object(contract["run_counters"], "run counters")
    if set(counters) != RUN_KEYS or any(counters[key] != 0 for key in RUN_KEYS):
        raise ValueError("forbidden run counter drifted")
    prohibitions = _object(contract["prohibitions"], "prohibitions")
    if set(prohibitions) != {
        "actual_calibration_acquisition",
        "threshold_materialization",
        "validation_closed_loop_fresh_holdout_training",
        "fixed_dp_model_weights_atoms_change",
        "old_artifact_or_cas_write",
        "claim_promotion_deployment",
    } or set(prohibitions.values()) != {True}:
        raise ValueError("prohibition topology drifted")
    return {
        "schema_version": (
            "camp_dp_v25_batch8_primary_calibration_contract_independent_review_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "topology_320_runs_640_pairs_rebuilt": True,
        "selector_receipt_640_topology_rebuilt": True,
        "numeric_registry_22_rebuilt": True,
        "threshold_math_rebuilt": True,
        "training_support_gap_and_future_formula_rebuilt": True,
        "hard_gates_and_failure_retention_rebuilt": True,
        "sequential_and_cross_exclusion_rebuilt": True,
        "model_pool_selector_call_count": 0,
        "producer_threshold_endpoint_decision_oracle_imported": False,
        "claim_authorized": False,
    }


def empirical_q99_higher(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (10,) or not np.all(np.isfinite(array)):
        raise ValueError("review q99 requires finite [10]")
    return float(np.sort(array, kind="mergesort")[9])


def bootstrap_ucb(values: Sequence[float], floor: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (64,) or not np.all(np.isfinite(array)):
        raise ValueError("review bootstrap requires finite [64]")
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise TypeError("floor must be numeric")
    floor = float(floor)
    if not math.isfinite(floor) or floor <= 0:
        raise ValueError("floor must be finite positive")
    rng = np.random.Generator(np.random.PCG64DXSM(825071))
    indexes = rng.integers(
        0, 64, size=(10000, 64), endpoint=False, dtype=np.int64
    )
    per_sample = np.sort(array[indexes], axis=1, kind="mergesort")[:, 63]
    return max(floor, float(np.sort(per_sample, kind="mergesort")[9500]))


def _review_authority(value: Any) -> None:
    authority = _object(value, "authority")
    if set(authority) != {"schema_version", "canonical_json_ascii", "sha256"}:
        raise ValueError("authority keyset drifted")
    raw = authority["canonical_json_ascii"]
    if (
        authority["schema_version"]
        != "camp_dp_v25_batch8_primary_calibration_contract_design_high_authority_v1"
        or type(raw) is not str
        or authority["sha256"] != AUTHORITY_SHA
        or hashlib.sha256(raw.encode("ascii")).hexdigest() != AUTHORITY_SHA
    ):
        raise ValueError("authority binding drifted")
    decoded = json.loads(raw)
    if (
        decoded.get("decision")
        != "authorized_outcome_independent_batch8_only_calibration_contract_"
        "design_and_independent_review"
        or decoded.get("actual_calibration_acquisition_authorized") is not False
        or decoded.get("planned_model_invocations") != 320
        or decoded.get("planned_pair_receipts") != 640
        or decoded.get("within_numeric_endpoint_count") != 22
        or decoded.get("cross_mode_numeric_endpoint_count") != 0
        or decoded.get("formal_phase_keys") != ["batch8_within"]
        or decoded.get("hard_gates") != HARD_GATES
    ):
        raise ValueError("authority semantic oracle failed")


def _review_implementation(
    value: Any,
    head: str,
    dirs: Mapping[str, str],
    sources: Mapping[str, str],
) -> None:
    implementation = _object(value, "implementation")
    _git_head(head)
    if (
        implementation.get("head") != head
        or tuple(implementation.get("exact_dirs", {}).keys()) != EXACT_DIR_KEYS
        or implementation.get("exact_dirs") != dict(dirs)
        or tuple(implementation.get("source_sha256", {}).keys()) != SOURCE_KEYS
        or implementation.get("source_sha256") != dict(sources)
    ):
        raise ValueError("implementation binding drifted")
    for sha in sources.values():
        _sha(sha)


def _review_preserved(value: Any) -> None:
    preserved = _object(value, "preserved evidence")
    if (
        preserved.get("v5_contract_root_sha256") != V5_ROOT
        or preserved.get("batch8_primary_contract_root_sha256") != PRIMARY_ROOT
        or preserved.get("batch8_first_state_root_sha256") != FIRST_STATE_ROOT
        or preserved.get("old_artifacts_roots_cas_immutable") is not True
    ):
        raise ValueError("preserved evidence drifted")
    for key, item in preserved.items():
        if key.endswith("_sha256"):
            _sha(item)


def _review_generator(value: Any) -> None:
    generator = _object(value, "generator")
    if generator != {
        "name": "new_single_invocation_batched_k8_candidate_pool",
        "mode": "single_invocation_batch8",
        "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
        "formal_model_invocations_per_run": 1,
        "expanded_batch_size": 8,
        "source_ego_state_count": 1,
        "agent_as_ego_batch": False,
        "candidate0_rule": "candidate_tensor_row0",
    }:
        raise ValueError("generator topology drifted")


def _review_topology(value: Any) -> None:
    topology = _object(value, "topology")
    run_ids = [
        f"development_calibration:{state:03d}:single_invocation_batch8:repeat{repeat}"
        for state in range(64)
        for repeat in range(5)
    ]
    pair_ids = [
        f"development_calibration:{state:03d}:batch8_within:r{left}_r{right}"
        for state in range(64)
        for left in range(5)
        for right in range(left + 1, 5)
    ]
    if (
        len(run_ids) != 320
        or len(pair_ids) != 640
        or topology.get("state_count") != 64
        or topology.get("repeats_per_state") != 5
        or topology.get("planned_run_count") != 320
        or topology.get("planned_model_invocation_count") != 320
        or topology.get("unordered_repeat_pairs_per_state") != 10
        or topology.get("planned_pair_receipt_count") != 640
        or topology.get("selector_receipts_per_arm") != 320
        or topology.get("planned_static_scene_selector_receipt_count") != 640
        or topology.get("statistical_unit") != "state"
        or topology.get("row_tick_as_independent_unit_allowed") is not False
        or topology.get("drop_replace_or_complete_case_allowed") is not False
        or topology.get("run_id_sha256") != _sha_json(run_ids)
        or topology.get("pair_id_sha256") != _sha_json(pair_ids)
    ):
        raise ValueError("calibration topology drifted")


def _review_numeric(value: Any) -> None:
    numeric = _object(value, "numeric")
    registry = _expected_registry()
    if (
        numeric.get("phase_keys") != ["batch8_within"]
        or numeric.get("within_numeric_endpoint_count") != 22
        or numeric.get("cross_mode_numeric_endpoint_count") != 0
        or numeric.get("sequential_numeric_endpoint_count") != 0
        or numeric.get("endpoint_registry") != registry
        or numeric.get("endpoint_registry_sha256") != _sha_json(registry)
        or numeric.get("missing_or_nonfinite")
        != "retained_and_qualification_fail_closed"
    ):
        raise ValueError("numeric registry drifted")
    ids = [row["endpoint_id"] for row in registry]
    if len(ids) != 22 or len(set(ids)) != 22:
        raise ValueError("numeric registry cardinality drifted")
    if any(
        token in endpoint
        for endpoint in ids
        for token in ("cross_mode", "margin_ratio", "rank_error", "relative_within")
    ):
        raise ValueError("cross endpoint entered within registry")


def _review_threshold(value: Any) -> None:
    threshold = _object(value, "threshold")
    within = _object(threshold.get("within_state"), "within threshold")
    across = _object(threshold.get("across_states"), "across threshold")
    if (
        threshold.get("materialization_authorized") is not False
        or within.get("pair_count") != 10
        or within.get("statistic") != "empirical_q99_higher"
        or across.get("state_count") != 64
        or across.get("bootstrap_resamples") != 10000
        or across.get("sample_size") != 64
        or across.get("with_replacement") is not True
        or across.get("rng") != "numpy.random.Generator(PCG64DXSM(825071))"
        or across.get("per_resample_index") != 63
        or across.get("upper_index") != 9500
        or threshold.get("comparison") != "pair_error <= frozen_threshold_is_pass"
        or threshold.get("exceedance") != "pair_error > frozen_threshold"
        or threshold.get("all_22_endpoints_required") is not True
        or threshold.get("weighted_total") is not False
    ):
        raise ValueError("threshold mathematics drifted")


def _review_training_support(value: Any) -> None:
    audit = _object(value, "training support")
    scale = _object(audit.get("scale_authority"), "scale authority")
    missing = _object(
        audit.get("missing_prespecified_reference"), "missing reference"
    )
    future = _object(audit.get("future_reference_schema"), "future reference")
    interval = _object(future.get("reference_interval"), "support interval")
    coverage = _object(
        future.get("calibration_state_coverage"), "support coverage"
    )
    index = scale.get("index")
    expected_index = [
        {"index": i, "name": name, "scale": atom_scale}
        for i, (name, atom_scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES))
    ]
    if (
        audit.get("required_before_any_future_acquisition") is not True
        or audit.get("current_status")
        != "evidence_missing_prespecified_training_support_reference"
        or audit.get("current_authority_binds_only_atom_normalization_scales")
        is not True
        or scale.get("artifact_root_sha256") != TRAINING_ROOT
        or scale.get("file_sha256") != TRAINING_SCALE_SHA
        or index != expected_index
        or set(missing.values()) != {True}
        or future.get("source") != "sealed_training_artifacts_only"
        or future.get("calibration_or_validation_values_allowed") is not False
        or len(future.get("continuous_fields", [])) != 20
        or interval.get("lower") != "empirical_q0_005_lower"
        or interval.get("upper") != "empirical_q0_995_higher"
        or interval.get("lower_formula")
        != "sorted_values[floor(0.005*(n-1))]"
        or interval.get("upper_formula")
        != "sorted_values[ceil(0.995*(n-1))]"
        or interval.get("finite_training_sample_count_minimum") != 1000
        or interval.get("equality_inside") != "lower <= value <= upper"
        or coverage
        != {
            "row_observations_per_state": 40,
            "formula": "inside_reference_count/40",
            "minimum_per_state": 0.95,
            "equality_passes": True,
            "required_passing_states": 61,
            "state_count": 64,
        }
        or future.get("multiplicity")
        != "all_20_prespecified_fields_must_pass_no_weighted_total"
        or audit.get("thresholds_materialized") is not False
        or audit.get("calibration_may_set_training_support_thresholds") is not False
        or audit.get("no_retraining_conclusion_authorized") is not False
        or audit.get("future_acquisition_requires_new_high_authority") is not True
    ):
        raise ValueError("training support contract drifted")


def _review_hard(value: Any) -> None:
    hard = _object(value, "hard gates")
    if (
        hard.get("required_per_run") != HARD_GATES
        or hard.get("post_pool_zero_call_fields")
        != [
            "model_call_count",
            "dp_call_count",
            "latent_generation_count",
            "candidate_generation_count",
        ]
        or hard.get("static_scene_selector_receipts_must_bind_same_pool_tensor")
        is not True
        or hard.get("any_failure") != "retain_run_and_fail_qualification"
    ):
        raise ValueError("hard gate topology drifted")


def _review_decision(value: Any) -> None:
    decision = _object(value, "decision")
    if (
        decision.get("qualification_pass_boolean")
        != "all_320_hard_receipts_pass AND all_22_bounded_repeatability_"
        "endpoints_pass AND prespecified_training_support_audit_pass"
        or decision.get("training_support_missing_result")
        != "evidence_missing_training_support_gap"
        or decision.get("runtime_failure_result") != "runtime_instability"
        or decision.get("selector_failure_result") != "selector_functional_failure"
        or decision.get("no_retraining_conclusion_authorized") is not False
        or decision.get("benefit_claim_authorized") is not False
        or decision.get("general_ood_claim_authorized") is not False
        or decision.get("weighted_total") is not False
    ):
        raise ValueError("decision semantics drifted")


def _review_sequential(value: Any) -> None:
    sequential = _object(value, "sequential")
    if sequential != {
        "mode": "sequential_batch1_x8",
        "scope": "legacy_non_gating_diagnostic_only",
        "formal_denominator_count": 0,
        "pair_receipt_count": 0,
        "numeric_key_count": 0,
        "threshold_contribution_count": 0,
        "hard_gate_contribution_count": 0,
        "primary_latency_contribution_count": 0,
    }:
        raise ValueError("sequential exclusion drifted")


def _expected_registry() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(ATOM_NAMES):
        rows.append(
            _record(
                f"atom.normalized_delta.{index:02d}.{name}",
                f"max_row_abs((a[:,{index}]-b[:,{index}])/training_scale[{index}])",
                "training_scale_normalized",
                1e-8,
                "[8,14]_float64_pair",
                "all_8_rows_and_training_scale_finite;scale_gt_0",
            )
        )
    extras = (
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
    )
    for endpoint_id, formula, units, floor, shape in extras:
        applicability = (
            "masks_equal_and_nonempty_and_shared_eligible_scores_finite"
            if endpoint_id.startswith("score.")
            else "exact_shape_actor_roster_and_all_values_finite"
        )
        rows.append(_record(endpoint_id, formula, units, floor, shape, applicability))
    return rows


def _record(
    endpoint_id: str,
    formula: str,
    units: str,
    floor: float,
    shape: str,
    applicability: str,
) -> dict[str, Any]:
    return {
        "phase": "batch8_within",
        "mode": "single_invocation_batch8",
        "endpoint_id": endpoint_id,
        "formula": formula,
        "units": units,
        "resolution_floor": floor,
        "input_shape": shape,
        "applicability": applicability,
        "missing_rule": "retain_state_and_fail_closed",
        "finite_required": True,
        "direction": "lower",
    }


def _sha_json(value: Any) -> str:
    raw = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keyset drifted")


def _sha(value: Any) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError("expected SHA256")
    int(value, 16)
    return value


def _git_head(value: Any) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError("expected git HEAD")
    int(value, 16)
    return value
