"""Raw-semantic provenance closure for fair-pool adaptation contract v4.

v5 remains outcome-independent and design-only.  It does not authorize or
perform acquisition.  It makes every numeric qualification value a derived
cache of typed, sealed per-run tensors and selector receipts.  A High-pinned
semantic artifact chain is required in addition to the preserved v4 chain.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import math
from typing import Any, Mapping, Sequence
import zlib

import numpy as np

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v4 as v4,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    ATOM_NAMES,
    ATOM_SCALES,
    bootstrap_upper_threshold,
    empirical_quantile_higher,
    sha256_json,
    spearman_rank_error,
)


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v5"
QUALIFICATION_PACKAGE_SCHEMA = (
    "camp_dp_v25_fair_pool_adaptation_qualification_package_v5"
)
TRUST_ANCHOR_SCHEMA = "camp_dp_v25_fair_pool_high_trust_anchor_v2"
SEMANTIC_RECEIPT_SCHEMA = (
    "camp_dp_v25_fair_pool_mode_repeat_raw_semantic_receipts_v1"
)
SEMANTIC_RUN_SCHEMA = "camp_dp_v25_fair_pool_raw_semantic_run_v1"
ARRAY_BLOB_SCHEMA = "camp_dp_v25_fair_pool_zlib_array_blob_v1"
V4_CONTRACT_ROOT = (
    "69bd196a91cea572484ca28b044966acd3ad85b868409d1907bec99a6ea0af47"
)
V4_REVIEW_ROOT = (
    "2611ac2322f124daa1f1134e662447c5823cef0db88a9e12fb04abdc0561f954"
)
CONTROL_TASK_ID = v4.CONTROL_TASK_ID
SEMANTIC_ARTIFACT_NAMES = (
    "calibration_semantic_receipts",
    "calibration_semantic_receipts_review",
    "validation_semantic_receipts",
    "validation_semantic_receipts_review",
)
SEMANTIC_ARTIFACT_KIND = {
    "calibration_semantic_receipts": (
        "development_calibration_raw_semantic_receipts"
    ),
    "calibration_semantic_receipts_review": (
        "development_calibration_raw_semantic_receipts_independent_review"
    ),
    "validation_semantic_receipts": (
        "independent_validation_raw_semantic_receipts"
    ),
    "validation_semantic_receipts_review": (
        "independent_validation_raw_semantic_receipts_independent_review"
    ),
}
NEIGHBOR_ENDPOINTS = (
    "trajectory.neighbor.position_max_m",
    "trajectory.neighbor.heading_max_rad",
    "trajectory.neighbor.speed_max_mps",
)


def adaptation_contract_v5() -> dict[str, Any]:
    inherited = v4.adaptation_contract_v4()
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_raw_semantic_provenance_design_only_acquisition_unauthorized",
        "superseded_preacquisition_diagnostic": {
            "schema_version": inherited["schema_version"],
            "payload_sha256": inherited["contract_payload_sha256"],
            "contract_root_sha256": V4_CONTRACT_ROOT,
            "review_root_sha256": V4_REVIEW_ROOT,
            "scope": (
                "trusted_artifact_topology_without_independently_"
                "reconstructed_numeric_semantics"
            ),
        },
        "inherited_v4_contract": inherited,
        "external_semantic_trust_anchor": {
            "schema_version": TRUST_ANCHOR_SCHEMA,
            "provider": "versioned_High_control_decision",
            "provider_task_id": CONTROL_TASK_ID,
            "expected_root_argument_is_out_of_band": True,
            "pins_v4_trust_anchor_root": True,
            "pins_selector_source_sha256": True,
            "exact_semantic_artifact_root_names": list(
                SEMANTIC_ARTIFACT_NAMES
            ),
            "package_cannot_self_authorize": True,
        },
        "raw_semantic_run_receipt": {
            "schema_version": SEMANTIC_RUN_SCHEMA,
            "split_mode_repeat_state_denominator": {
                "development_calibration": 64 * 2 * 5,
                "independent_validation": 64 * 2 * 5,
            },
            "array_codec": {
                "schema_version": ARRAY_BLOB_SCHEMA,
                "dtype": "<f8",
                "codec": "zlib_level9_then_base64_standard",
                "canonical_base64_required": True,
                "raw_and_encoded_sha256_recomputed": True,
            },
            "typed_preimages": {
                "candidate_ego_trajectory": [8, 80, 4],
                "candidate_neighbor_trajectory": "[8,A,80,4]_A_ge_1",
                "atom_vectors": [8, 14],
                "selector_scores_per_arm": [8],
                "selector_mask_per_arm": [8],
                "selected_action_per_arm": [80, 4],
            },
            "trajectory_field_order": [
                "x_m",
                "y_m",
                "heading_rad",
                "speed_mps",
            ],
            "neighbor_actor_fingerprints_exact_sorted": True,
            "training_scale_authority": deepcopy(
                inherited["inherited_v3_contract"][
                    "training_scale_authority"
                ]
            ),
            "forward_binding": (
                "sha256(canonical_input_state_latent_model_checkpoint_mode_"
                "repeat_candidate_neighbor_atom_preimage)"
            ),
            "forward_invocation_id": "forward:<forward_binding_sha256>",
            "pool_id": (
                "pool:<sha256(forward_binding_sha256_plus_candidate_tensor_sha256)>"
            ),
            "all_five_repeats_require_raw_candidate_and_selector_preimages": True,
            "validation_repeat0_must_equal_v4_hard_pool_selector_receipts": True,
        },
        "endpoint_derivation": {
            "authoritative_input": "typed_raw_semantic_run_receipts",
            "endpoint_values_role": "derived_cache_only",
            "derived_cache_equality": "exact_float64_hex_equality",
            "within_endpoint_ids": list(v4.WITHIN_NUMERIC_IDS),
            "cross_endpoint_ids": list(v4.CROSS_NUMERIC_IDS),
            "formula_registry": _formula_registry(),
            "phase_key_count": len(v4._numeric_keys()),
            "cross_normalized_score_order": (
                "first_reconstruct_all_within_pair_values_and_verify_"
                "within_score_thresholds_then_derive_cross_values"
            ),
            "neighbor_relative_inflation": (
                "per_state_max_over_three_neighbor_endpoints_of_"
                "cross_q99_higher_div_max(seq_q99_higher,batch_q99_higher,"
                "endpoint_resolution_floor);same_state_value_cached_on_each_"
                "of_five_cross_pairs"
            ),
            "nonfinite_missing_or_inapplicable": "authority_failure",
        },
        "independent_review": {
            "producer_v5_module_imported": False,
            "producer_metric_threshold_decision_oracle_imported": False,
            "reconstructs_array_bytes_and_all_73_phase_values": True,
            "reconstructs_forward_pool_selector_bindings": True,
            "reconstructs_state_q99_and_threshold_freeze": True,
        },
        "adversarial_fail_closed": [
            "all_endpoint_caches_changed_to_zero_and_all_artifacts_reviews_anchor_resealed",
            "arbitrary_finite_nonnegative_endpoint_cache",
            "repeat1_through_4_candidate_tensor_bytes_or_hash_changed",
            "forward_or_pool_binding_not_derived_from_raw_preimage",
            "selector_scores_masks_action_not_bound_to_same_pool",
        ],
        "decision": {
            "consumer": "decide_qualification_v5",
            "v4_decision_runs_only_after_raw_semantic_reconstruction": True,
            "exploratory_contract_design_only": True,
            "acquisition_authorized": False,
            "benefit_claim": False,
            "retraining_decision": "not_authorized",
        },
        "run_and_claim_boundary": deepcopy(
            inherited["run_and_claim_boundary"]
        ),
    }
    contract["contract_payload_sha256"] = sha256_json(contract)
    return contract


def validate_contract_v5(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or value != adaptation_contract_v5():
        raise ValueError("v5 contract literal drifted")
    payload = deepcopy(dict(value))
    supplied = payload.pop("contract_payload_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("v5 contract payload SHA drifted")
    v4.validate_contract_v4(value["inherited_v4_contract"])
    return deepcopy(dict(value))


def make_semantic_artifact(
    kind: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    return v4.make_content_artifact(kind, payload)


def make_semantic_review(
    source: Mapping[str, Any], *, review_kind: str
) -> dict[str, Any]:
    return v4.make_content_review(source, review_kind=review_kind)


def make_trust_anchor_v5(
    contract: Mapping[str, Any],
    *,
    contract_root_sha256: str,
    contract_review_root_sha256: str,
    v4_trust_anchor_root_sha256: str,
    selector_source_sha256: str,
    semantic_artifact_roots: Mapping[str, str],
    high_decision_sha256: str,
) -> dict[str, Any]:
    frozen = validate_contract_v5(contract)
    if (
        type(semantic_artifact_roots) is not dict
        or set(semantic_artifact_roots) != set(SEMANTIC_ARTIFACT_NAMES)
    ):
        raise ValueError("v5 semantic anchor root keyset drifted")
    value = {
        "schema_version": TRUST_ANCHOR_SCHEMA,
        "status": "trusted_by_versioned_High_control",
        "provider_task_id": CONTROL_TASK_ID,
        "high_decision_sha256": _sha(high_decision_sha256, "High decision"),
        "contract_payload_sha256": frozen["contract_payload_sha256"],
        "contract_root_sha256": _sha(contract_root_sha256, "contract root"),
        "contract_review_root_sha256": _sha(
            contract_review_root_sha256, "contract review root"
        ),
        "v4_trust_anchor_root_sha256": _sha(
            v4_trust_anchor_root_sha256, "v4 trust anchor"
        ),
        "selector_source_sha256": _sha(
            selector_source_sha256, "selector source"
        ),
        "semantic_artifact_roots": {
            name: _sha(semantic_artifact_roots[name], f"{name} root")
            for name in SEMANTIC_ARTIFACT_NAMES
        },
        "acquisition_authorized": True,
        "fresh_holdout_closed_loop_training_authorized": False,
    }
    value["trust_anchor_root_sha256"] = sha256_json(value)
    return value


def encode_array_blob(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    if array.ndim == 0 or not np.isfinite(array).all():
        raise ValueError("array blob requires finite non-scalar float64")
    raw = array.tobytes(order="C")
    encoded = zlib.compress(raw, level=9)
    return {
        "schema_version": ARRAY_BLOB_SCHEMA,
        "dtype": "<f8",
        "shape": list(array.shape),
        "codec": "zlib_level9_then_base64_standard",
        "raw_byte_count": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        "data_base64": base64.b64encode(encoded).decode("ascii"),
    }


def decide_qualification_v5(
    contract: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    trust_anchor: Mapping[str, Any],
    expected_trust_anchor_root_sha256: str,
) -> dict[str, Any]:
    frozen = validate_contract_v5(contract)
    anchor = _validate_anchor(
        trust_anchor,
        contract=frozen,
        expected_root=expected_trust_anchor_root_sha256,
    )
    if type(package) is not dict or set(package) != {
        "schema_version",
        "contract_payload_sha256",
        "trust_anchor_root_sha256",
        "v4_package",
        "v4_trust_anchor",
        "semantic_artifacts",
    }:
        raise ValueError("v5 package exact schema drifted")
    if (
        package["schema_version"] != QUALIFICATION_PACKAGE_SCHEMA
        or package["contract_payload_sha256"]
        != frozen["contract_payload_sha256"]
        or package["trust_anchor_root_sha256"]
        != anchor["trust_anchor_root_sha256"]
    ):
        raise ValueError("v5 package authority drifted")
    v4_anchor = package["v4_trust_anchor"]
    if (
        type(v4_anchor) is not dict
        or v4_anchor.get("trust_anchor_root_sha256")
        != anchor["v4_trust_anchor_root_sha256"]
    ):
        raise ValueError("nested v4 trust anchor drifted")
    semantic = _validate_semantic_artifacts(
        package["semantic_artifacts"], anchor=anchor
    )
    v4_package = package["v4_package"]
    if type(v4_package) is not dict:
        raise ValueError("nested v4 package drifted")
    v4_artifacts = v4_package.get("artifacts")
    if type(v4_artifacts) is not dict:
        raise ValueError("nested v4 artifacts drifted")
    calibration_runs = _validate_semantic_payload(
        semantic["calibration_semantic_receipts"]["payload"],
        expected_split="development_calibration",
        expected_v4_receipts_root=v4_artifacts["calibration_receipts"][
            "root_sha256"
        ],
        v4_receipt_payload=v4_artifacts["calibration_receipts"]["payload"],
        selector_source_sha256=anchor["selector_source_sha256"],
    )
    validation_runs = _validate_semantic_payload(
        semantic["validation_semantic_receipts"]["payload"],
        expected_split="independent_validation",
        expected_v4_receipts_root=v4_artifacts["validation_receipts"][
            "root_sha256"
        ],
        v4_receipt_payload=v4_artifacts["validation_receipts"]["payload"],
        selector_source_sha256=anchor["selector_source_sha256"],
    )
    freeze_payload = v4_artifacts["threshold_freeze"]["payload"]
    within_thresholds = _verify_within_caches_and_thresholds(
        runs=calibration_runs,
        pair_rows=v4_artifacts["calibration_receipts"]["payload"][
            "pair_receipts"
        ],
        freeze_payload=freeze_payload,
        contract=frozen,
    )
    _verify_full_pair_cache(
        runs=calibration_runs,
        pair_rows=v4_artifacts["calibration_receipts"]["payload"][
            "pair_receipts"
        ],
        within_thresholds=within_thresholds,
    )
    _verify_full_pair_cache(
        runs=validation_runs,
        pair_rows=v4_artifacts["validation_receipts"]["payload"][
            "pair_receipts"
        ],
        within_thresholds=within_thresholds,
    )
    _verify_validation_repeat0_hard_bindings(
        validation_runs,
        v4_artifacts["validation_receipts"]["payload"][
            "hard_state_receipts"
        ],
    )
    decision = v4.decide_qualification_v4(
        frozen["inherited_v4_contract"],
        v4_package,
        trust_anchor=v4_anchor,
        expected_trust_anchor_root_sha256=anchor[
            "v4_trust_anchor_root_sha256"
        ],
    )
    return {
        **decision,
        "schema_version": (
            "camp_dp_v25_fair_pool_adaptation_qualification_decision_v5"
        ),
        "v5_trust_anchor_root_sha256": anchor[
            "trust_anchor_root_sha256"
        ],
        "raw_semantic_run_receipt_count": 1280,
        "numeric_phase_key_count_reconstructed": 73,
        "endpoint_values_used_as_authority": False,
        "all_five_repeat_tensors_and_selectors_reconstructed": True,
        "forward_pool_ids_derived_from_raw_preimages": True,
        "independent_semantic_artifact_reviews_bound": True,
    }


def derive_pair_cache_v5(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    *,
    within_thresholds: Mapping[tuple[str, str, str], float],
) -> dict[tuple[str, str, int], dict[str, float]]:
    base = _base_values_by_pair(runs, pair_rows)
    inflation = _neighbor_inflation_by_state(base, pair_rows)
    result: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in pair_rows:
        identity = (
            row["phase"],
            row["state_spec_id"],
            row["pair_index"],
        )
        values = dict(base[identity])
        if row["phase"] == "cross_mode":
            left = runs[
                (
                    v4.MODES[0],
                    row["state_spec_id"],
                    row["left_repeat_index"],
                )
            ]
            right = runs[
                (
                    v4.MODES[1],
                    row["state_spec_id"],
                    row["right_repeat_index"],
                )
            ]
            for arm in v4.ARMS:
                abs_id = f"score.{arm}.abs_delta"
                denominator = max(
                    within_thresholds[
                        ("sequential_within", v4.MODES[0], abs_id)
                    ],
                    within_thresholds[
                        ("batch8_within", v4.MODES[1], abs_id)
                    ],
                    1e-9,
                )
                values[
                    f"score.{arm}.within_mode_normalized_delta"
                ] = values[abs_id] / denominator
                values[f"score.{arm}.margin_ratio"] = _margin_ratio(
                    left["scores"][arm],
                    right["scores"][arm],
                    left["masks"][arm],
                    right["masks"][arm],
                )
                rank = spearman_rank_error(
                    left["scores"][arm],
                    right["scores"][arm],
                    left["masks"][arm],
                    right["masks"][arm],
                )
                if rank["status"] != "computed":
                    raise ValueError("score rank evidence is ambiguous")
                values[f"score.{arm}.rank_error"] = float(
                    rank["rank_error"]
                )
            values["neighbor.relative_within_mode_inflation"] = inflation[
                row["state_spec_id"]
            ]
        result[identity] = values
    return result


def _formula_registry() -> dict[str, str]:
    result = {
        f"atom.normalized_delta.{index:02d}.{name}": (
            f"max_8_abs(left_atom[:,{index}]-right_atom[:,{index}])/"
            f"training_scale[{index}]"
        )
        for index, name in enumerate(ATOM_NAMES)
    }
    result.update(
        {
            "trajectory.ego.position_max_m": (
                "max_8x80_l2_delta(candidate_ego_xy)"
            ),
            "trajectory.ego.heading_max_rad": (
                "max_8x80_abs_wrap_to_pi_delta(candidate_ego_heading)"
            ),
            "trajectory.ego.speed_max_mps": (
                "max_8x80_abs_delta(candidate_ego_speed)"
            ),
            "trajectory.neighbor.position_max_m": (
                "max_8xAx80_l2_delta(exact_actor_fingerprint_neighbor_xy)"
            ),
            "trajectory.neighbor.heading_max_rad": (
                "max_8xAx80_abs_wrap_to_pi_delta(neighbor_heading)"
            ),
            "trajectory.neighbor.speed_max_mps": (
                "max_8xAx80_abs_delta(neighbor_speed)"
            ),
            "score.static14d.abs_delta": (
                "max_shared_eligible_abs_score_delta_equal_masks"
            ),
            "score.scene14d.abs_delta": (
                "max_shared_eligible_abs_score_delta_equal_masks"
            ),
            "score.static14d.within_mode_normalized_delta": (
                "cross_abs/max(seq_within_threshold,batch8_within_threshold,1e-9)"
            ),
            "score.scene14d.within_mode_normalized_delta": (
                "cross_abs/max(seq_within_threshold,batch8_within_threshold,1e-9)"
            ),
            "score.static14d.margin_ratio": (
                "abs(runner_up_minus_best_gap_delta)/max(abs(left_gap),abs(right_gap),1e-9)"
            ),
            "score.scene14d.margin_ratio": (
                "abs(runner_up_minus_best_gap_delta)/max(abs(left_gap),abs(right_gap),1e-9)"
            ),
            "score.static14d.rank_error": (
                "1-spearman_average_exact_tie_ranks_on_shared_eligible"
            ),
            "score.scene14d.rank_error": (
                "1-spearman_average_exact_tie_ranks_on_shared_eligible"
            ),
            "neighbor.relative_within_mode_inflation": (
                "per_state_max_three_neighbor_cross_q99_over_max_two_within_q99_and_floor"
            ),
        }
    )
    return result


def _validate_anchor(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    expected_root: str,
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "provider_task_id",
        "high_decision_sha256",
        "contract_payload_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "v4_trust_anchor_root_sha256",
        "selector_source_sha256",
        "semantic_artifact_roots",
        "acquisition_authorized",
        "fresh_holdout_closed_loop_training_authorized",
        "trust_anchor_root_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("v5 trust anchor exact schema drifted")
    supplied = value["trust_anchor_root_sha256"]
    payload = dict(value)
    payload.pop("trust_anchor_root_sha256")
    if (
        supplied != sha256_json(payload)
        or supplied != _sha(expected_root, "external v5 trust anchor")
        or value["schema_version"] != TRUST_ANCHOR_SCHEMA
        or value["status"] != "trusted_by_versioned_High_control"
        or value["provider_task_id"] != CONTROL_TASK_ID
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["acquisition_authorized"] is not True
        or value["fresh_holdout_closed_loop_training_authorized"] is not False
        or type(value["semantic_artifact_roots"]) is not dict
        or set(value["semantic_artifact_roots"])
        != set(SEMANTIC_ARTIFACT_NAMES)
    ):
        raise ValueError("external v5 trust anchor drifted")
    for field in (
        "high_decision_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "v4_trust_anchor_root_sha256",
        "selector_source_sha256",
    ):
        _sha(value[field], field)
    for name, root in value["semantic_artifact_roots"].items():
        _sha(root, f"{name} root")
    return deepcopy(dict(value))


def _validate_semantic_artifacts(
    value: Any, *, anchor: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != set(
        SEMANTIC_ARTIFACT_NAMES
    ):
        raise ValueError("semantic artifact keyset drifted")
    result = {}
    for name in SEMANTIC_ARTIFACT_NAMES:
        expected_kind = SEMANTIC_ARTIFACT_KIND[name]
        checked = _content_artifact(value[name], expected_kind)
        if checked["root_sha256"] != anchor["semantic_artifact_roots"][name]:
            raise ValueError("semantic artifact external root drifted")
        result[name] = checked
    for source_name, review_name in (
        (
            "calibration_semantic_receipts",
            "calibration_semantic_receipts_review",
        ),
        (
            "validation_semantic_receipts",
            "validation_semantic_receipts_review",
        ),
    ):
        source = result[source_name]
        review = result[review_name]["payload"]
        if (
            type(review) is not dict
            or review.get("status")
            != "passed_independent_literal_reconstruction"
            or review.get("source_root_sha256") != source["root_sha256"]
            or review.get("source_payload_sha256")
            != source["payload_sha256"]
            or review.get("reviewer_role_separate") is not True
            or review.get("producer_module_imported") is not False
        ):
            raise ValueError("semantic independent review binding drifted")
    return result


def _content_artifact(value: Any, expected_kind: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "kind",
        "payload",
        "payload_sha256",
        "root_sha256",
    }:
        raise ValueError("semantic content artifact schema drifted")
    payload = dict(value)
    supplied_root = payload.pop("root_sha256")
    if (
        value["schema_version"] != v4.CONTENT_ARTIFACT_SCHEMA
        or value["kind"] != expected_kind
        or type(value["payload"]) is not dict
        or value["payload_sha256"] != sha256_json(value["payload"])
        or supplied_root != sha256_json(payload)
    ):
        raise ValueError("semantic content artifact root drifted")
    return deepcopy(dict(value))


def _validate_semantic_payload(
    value: Mapping[str, Any],
    *,
    expected_split: str,
    expected_v4_receipts_root: str,
    v4_receipt_payload: Mapping[str, Any],
    selector_source_sha256: str,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "split",
        "v4_receipts_root_sha256",
        "run_count",
        "run_semantics",
    }:
        raise ValueError("raw semantic payload exact schema drifted")
    if (
        value["schema_version"] != SEMANTIC_RECEIPT_SCHEMA
        or value["split"] != expected_split
        or value["v4_receipts_root_sha256"]
        != expected_v4_receipts_root
        or value["run_count"] != 640
        or type(value["run_semantics"]) is not list
        or len(value["run_semantics"]) != 640
    ):
        raise ValueError("raw semantic payload denominator drifted")
    v4_runs = {
        (row["mode"], row["state_spec_id"], row["repeat_index"]): row
        for row in v4_receipt_payload["run_receipts"]
    }
    result = {}
    for raw in value["run_semantics"]:
        checked = _validate_semantic_run(
            raw,
            v4_runs=v4_runs,
            selector_source_sha256=selector_source_sha256,
        )
        key = (
            checked["mode"],
            checked["state_spec_id"],
            checked["repeat_index"],
        )
        if key in result:
            raise ValueError("raw semantic run duplicate")
        result[key] = checked
    if set(result) != set(v4_runs):
        raise ValueError("raw semantic run keyset drifted")
    return result


def _validate_semantic_run(
    value: Any,
    *,
    v4_runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    selector_source_sha256: str,
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "state_spec_id",
        "mode",
        "repeat_index",
        "v4_run_receipt_sha256",
        "forward_binding",
        "candidate_ego_trajectory",
        "candidate_neighbor_trajectory",
        "neighbor_actor_fingerprints",
        "atom_vectors",
        "selectors",
        "semantic_receipt_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("raw semantic run exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("semantic_receipt_sha256")
    if (
        supplied != sha256_json(payload)
        or value["schema_version"] != SEMANTIC_RUN_SCHEMA
    ):
        raise ValueError("raw semantic run root drifted")
    key = (value["mode"], value["state_spec_id"], value["repeat_index"])
    if key not in v4_runs:
        raise ValueError("raw semantic run identity drifted")
    run = v4_runs[key]
    if value["v4_run_receipt_sha256"] != run["receipt_sha256"]:
        raise ValueError("raw semantic run v4 binding drifted")
    candidate = _array_blob(
        value["candidate_ego_trajectory"], expected_shape=(8, 80, 4)
    )
    neighbor = _array_blob(value["candidate_neighbor_trajectory"])
    atoms = _array_blob(value["atom_vectors"], expected_shape=(8, 14))
    if (
        neighbor.ndim != 4
        or neighbor.shape[0] != 8
        or neighbor.shape[1] < 1
        or neighbor.shape[2:] != (80, 4)
        or type(value["neighbor_actor_fingerprints"]) is not list
        or len(value["neighbor_actor_fingerprints"]) != neighbor.shape[1]
        or value["neighbor_actor_fingerprints"]
        != sorted(value["neighbor_actor_fingerprints"])
        or len(set(value["neighbor_actor_fingerprints"]))
        != neighbor.shape[1]
    ):
        raise ValueError("neighbor semantic roster drifted")
    for fingerprint in value["neighbor_actor_fingerprints"]:
        _sha(fingerprint, "neighbor actor fingerprint")
    candidate_sha, row_sha = _tensor_hashes(candidate)
    neighbor_sha = hashlib.sha256(
        np.ascontiguousarray(neighbor).tobytes(order="C")
    ).hexdigest()
    atom_sha = hashlib.sha256(
        np.ascontiguousarray(atoms).tobytes(order="C")
    ).hexdigest()
    forward = value["forward_binding"]
    if type(forward) is not dict or set(forward) != {
        "state_spec_id",
        "mode",
        "repeat_index",
        "input_manifest_sha256",
        "actual_state_sha256",
        "actual_latent_manifest_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "model_source_sha256",
        "selector_source_sha256",
        "model_call_count",
        "candidate_tensor_sha256",
        "candidate_row_sha256",
        "neighbor_tensor_sha256",
        "atom_tensor_sha256",
        "forward_binding_sha256",
        "forward_invocation_id",
        "pool_binding_sha256",
        "pool_id",
    }:
        raise ValueError("forward binding exact schema drifted")
    forward_preimage = {
        key: forward[key]
        for key in (
            "state_spec_id",
            "mode",
            "repeat_index",
            "input_manifest_sha256",
            "actual_state_sha256",
            "actual_latent_manifest_sha256",
            "fixed_dp_head",
            "checkpoint_sha256",
            "model_source_sha256",
            "selector_source_sha256",
            "model_call_count",
            "candidate_tensor_sha256",
            "candidate_row_sha256",
            "neighbor_tensor_sha256",
            "atom_tensor_sha256",
        )
    }
    forward_sha = sha256_json(forward_preimage)
    pool_sha = sha256_json(
        {
            "forward_binding_sha256": forward_sha,
            "candidate_tensor_sha256": candidate_sha,
        }
    )
    if (
        forward["state_spec_id"] != value["state_spec_id"]
        or forward["mode"] != value["mode"]
        or forward["repeat_index"] != value["repeat_index"]
        or forward["input_manifest_sha256"]
        != run["input_manifest_sha256"]
        or forward["actual_state_sha256"] != run["actual_state_sha256"]
        or forward["actual_latent_manifest_sha256"]
        != run["actual_latent_manifest_sha256"]
        or forward["fixed_dp_head"] != run["fixed_dp_head"]
        or forward["checkpoint_sha256"] != run["checkpoint_sha256"]
        or forward["model_source_sha256"] != run["model_source_sha256"]
        or forward["selector_source_sha256"] != selector_source_sha256
        or forward["model_call_count"] != run["model_call_count"]
        or forward["candidate_tensor_sha256"] != candidate_sha
        or forward["candidate_row_sha256"] != row_sha
        or forward["neighbor_tensor_sha256"] != neighbor_sha
        or forward["atom_tensor_sha256"] != atom_sha
        or forward["forward_binding_sha256"] != forward_sha
        or forward["forward_invocation_id"] != f"forward:{forward_sha}"
        or forward["pool_binding_sha256"] != pool_sha
        or forward["pool_id"] != f"pool:{pool_sha}"
        or run["forward_invocation_id"] != f"forward:{forward_sha}"
        or run["pool_id"] != f"pool:{pool_sha}"
        or run["candidate_tensor_sha256"] != candidate_sha
        or run["candidate_row_sha256"] != row_sha
        or run["all_finite"] is not True
    ):
        raise ValueError("forward/pool raw semantic binding drifted")
    selectors = value["selectors"]
    if type(selectors) is not dict or set(selectors) != set(v4.ARMS):
        raise ValueError("raw selector arm keyset drifted")
    checked_selectors = {
        arm: _semantic_selector(
            selectors[arm],
            arm=arm,
            state_id=value["state_spec_id"],
            mode=value["mode"],
            pool_id=f"pool:{pool_sha}",
            candidate_sha=candidate_sha,
            candidate=candidate,
            selector_source_sha256=selector_source_sha256,
        )
        for arm in v4.ARMS
    }
    return {
        "state_spec_id": value["state_spec_id"],
        "mode": value["mode"],
        "repeat_index": value["repeat_index"],
        "v4_run_receipt_sha256": run["receipt_sha256"],
        "candidate": candidate,
        "neighbor": neighbor,
        "neighbor_actor_fingerprints": list(
            value["neighbor_actor_fingerprints"]
        ),
        "atoms": atoms,
        "scores": {
            arm: checked_selectors[arm]["scores"] for arm in v4.ARMS
        },
        "masks": {
            arm: checked_selectors[arm]["mask"] for arm in v4.ARMS
        },
        "selectors": checked_selectors,
        "candidate_sha256": candidate_sha,
        "row_sha256": row_sha,
        "forward_invocation_id": f"forward:{forward_sha}",
        "pool_id": f"pool:{pool_sha}",
    }


def _semantic_selector(
    value: Any,
    *,
    arm: str,
    state_id: str,
    mode: str,
    pool_id: str,
    candidate_sha: str,
    candidate: np.ndarray,
    selector_source_sha256: str,
) -> dict[str, Any]:
    fields = {
        "arm",
        "state_spec_id",
        "mode",
        "selector_source_sha256",
        "pool_id",
        "candidate_tensor_sha256",
        "pre_tensor_sha256",
        "post_tensor_sha256",
        "scores",
        "mask",
        "selected_index",
        "selected_action",
        "executable",
        "terminal",
        "dp_model_call_count_after_pool",
        "latent_replacement_count_after_pool",
        "candidate_generation_count_after_pool",
        "selector_receipt_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("raw semantic selector exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("selector_receipt_sha256")
    scores = np.asarray(value["scores"], dtype=np.float64)
    mask = np.asarray(value["mask"])
    selected = _array_blob(
        value["selected_action"], expected_shape=(80, 4)
    )
    if (
        supplied != sha256_json(payload)
        or value["arm"] != arm
        or value["state_spec_id"] != state_id
        or value["mode"] != mode
        or value["selector_source_sha256"] != selector_source_sha256
        or value["pool_id"] != pool_id
        or value["candidate_tensor_sha256"] != candidate_sha
        or value["pre_tensor_sha256"] != candidate_sha
        or value["post_tensor_sha256"] != candidate_sha
        or scores.shape != (8,)
        or not np.isfinite(scores).all()
        or mask.shape != (8,)
        or mask.dtype != np.bool_
        or not mask.any()
        or value["dp_model_call_count_after_pool"] != 0
        or value["latent_replacement_count_after_pool"] != 0
        or value["candidate_generation_count_after_pool"] != 0
    ):
        raise ValueError("raw semantic selector provenance drifted")
    eligible = np.flatnonzero(mask)
    best = float(np.min(scores[eligible]))
    expected_index = int(eligible[scores[eligible] == best][0])
    if (
        value["selected_index"] != expected_index
        or not np.array_equal(selected, candidate[expected_index])
        or value["executable"]
        not in {"executable", "non_executable_retained"}
        or value["terminal"]
        not in {"complete", "terminal_failure_retained"}
    ):
        raise ValueError("raw semantic selector action drifted")
    return {
        "scores": scores.tolist(),
        "mask": mask.tolist(),
        "selected_index": expected_index,
        "selected_action": selected,
        "executable": value["executable"],
        "terminal": value["terminal"],
        "selector_receipt_sha256": supplied,
    }


def _verify_within_caches_and_thresholds(
    *,
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    freeze_payload: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[tuple[str, str, str], float]:
    base = _base_values_by_pair(runs, pair_rows)
    for row in pair_rows:
        if row["phase"] == "cross_mode":
            continue
        identity = (
            row["phase"],
            row["state_spec_id"],
            row["pair_index"],
        )
        _exact_cache(
            row["endpoint_values"],
            base[identity],
            expected_keys=v4.WITHIN_NUMERIC_IDS,
        )
    records = {
        (row["phase"], row["mode"], row["endpoint_id"]): row
        for row in freeze_payload["records"]
    }
    state_ids = sorted(
        {row["state_spec_id"] for row in pair_rows},
        key=lambda item: item,
    )
    thresholds = {}
    for phase, mode in (
        ("sequential_within", v4.MODES[0]),
        ("batch8_within", v4.MODES[1]),
    ):
        for endpoint in v4.WITHIN_NUMERIC_IDS:
            values = {
                state_id: [] for state_id in state_ids
            }
            roots = {state_id: [] for state_id in state_ids}
            for row in pair_rows:
                if row["phase"] != phase:
                    continue
                identity = (
                    row["phase"],
                    row["state_spec_id"],
                    row["pair_index"],
                )
                values[row["state_spec_id"]].append(
                    base[identity][endpoint]
                )
                roots[row["state_spec_id"]].append(
                    row["receipt_sha256"]
                )
            statistics = [
                empirical_quantile_higher(values[state_id], 0.99)
                for state_id in state_ids
            ]
            floor = v4._resolution_floor(endpoint)
            expected_threshold = bootstrap_upper_threshold(
                statistics, resolution_floor=floor
            )
            key = (phase, mode, endpoint)
            record = records.get(key)
            if (
                record is None
                or record["calibration_state_ids"] != state_ids
                or record["state_pair_receipt_sha256"]
                != [roots[state_id] for state_id in state_ids]
                or not _float_list_exact(
                    record["state_statistics"], statistics
                )
                or float(record["resolution_floor"]).hex()
                != float(floor).hex()
                or float(record["bootstrap_result"]).hex()
                != float(expected_threshold).hex()
                or float(record["threshold"]).hex()
                != float(expected_threshold).hex()
            ):
                raise ValueError("within threshold raw-semantic derivation drifted")
            thresholds[key] = expected_threshold
    return thresholds


def _verify_full_pair_cache(
    *,
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    within_thresholds: Mapping[tuple[str, str, str], float],
) -> None:
    expected = derive_pair_cache_v5(
        runs, pair_rows, within_thresholds=within_thresholds
    )
    for row in pair_rows:
        identity = (
            row["phase"],
            row["state_spec_id"],
            row["pair_index"],
        )
        endpoints = (
            v4.CROSS_NUMERIC_IDS
            if row["phase"] == "cross_mode"
            else v4.WITHIN_NUMERIC_IDS
        )
        _exact_cache(
            row["endpoint_values"],
            expected[identity],
            expected_keys=endpoints,
        )


def _base_values_by_pair(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str, int], dict[str, float]]:
    result = {}
    for row in pair_rows:
        phase = row["phase"]
        if phase == "sequential_within":
            left_mode = right_mode = v4.MODES[0]
        elif phase == "batch8_within":
            left_mode = right_mode = v4.MODES[1]
        elif phase == "cross_mode":
            left_mode, right_mode = v4.MODES
        else:
            raise ValueError("raw semantic pair phase drifted")
        left = runs[
            (
                left_mode,
                row["state_spec_id"],
                row["left_repeat_index"],
            )
        ]
        right = runs[
            (
                right_mode,
                row["state_spec_id"],
                row["right_repeat_index"],
            )
        ]
        result[(phase, row["state_spec_id"], row["pair_index"])] = (
            _base_pair_values(left, right)
        )
    return result


def _base_pair_values(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> dict[str, float]:
    if left["neighbor_actor_fingerprints"] != right[
        "neighbor_actor_fingerprints"
    ] or left["neighbor"].shape != right["neighbor"].shape:
        raise ValueError("neighbor actor roster is not pair-identical")
    values = {}
    for index, (name, scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES)):
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError("training atom scale drifted")
        values[f"atom.normalized_delta.{index:02d}.{name}"] = float(
            np.max(np.abs(left["atoms"][:, index] - right["atoms"][:, index]))
            / scale
        )
    values.update(_trajectory_values("ego", left["candidate"], right["candidate"]))
    values.update(_trajectory_values("neighbor", left["neighbor"], right["neighbor"]))
    for arm in v4.ARMS:
        if left["masks"][arm] != right["masks"][arm]:
            raise ValueError("score mask applicability drifted")
        mask = np.asarray(left["masks"][arm], dtype=bool)
        if not mask.any():
            raise ValueError("score endpoint has no eligible candidate")
        lscore = np.asarray(left["scores"][arm], dtype=np.float64)
        rscore = np.asarray(right["scores"][arm], dtype=np.float64)
        values[f"score.{arm}.abs_delta"] = float(
            np.max(np.abs(lscore[mask] - rscore[mask]))
        )
    if set(values) != set(v4.WITHIN_NUMERIC_IDS):
        raise ValueError("base endpoint formula registry drifted")
    return values


def _trajectory_values(
    role: str, left: np.ndarray, right: np.ndarray
) -> dict[str, float]:
    position = np.linalg.norm(left[..., :2] - right[..., :2], axis=-1)
    heading = np.abs(
        (left[..., 2] - right[..., 2] + np.pi) % (2 * np.pi) - np.pi
    )
    speed = np.abs(left[..., 3] - right[..., 3])
    return {
        f"trajectory.{role}.position_max_m": float(np.max(position)),
        f"trajectory.{role}.heading_max_rad": float(np.max(heading)),
        f"trajectory.{role}.speed_max_mps": float(np.max(speed)),
    }


def _neighbor_inflation_by_state(
    base: Mapping[tuple[str, str, int], Mapping[str, float]],
    pair_rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    state_ids = {row["state_spec_id"] for row in pair_rows}
    result = {}
    for state_id in state_ids:
        ratios = []
        for endpoint in NEIGHBOR_ENDPOINTS:
            phase_values = {}
            for phase in (
                "sequential_within",
                "batch8_within",
                "cross_mode",
            ):
                values = [
                    base[(phase, state_id, row["pair_index"])][endpoint]
                    for row in pair_rows
                    if row["phase"] == phase
                    and row["state_spec_id"] == state_id
                ]
                phase_values[phase] = empirical_quantile_higher(
                    values, 0.99
                )
            ratios.append(
                phase_values["cross_mode"]
                / max(
                    phase_values["sequential_within"],
                    phase_values["batch8_within"],
                    v4._resolution_floor(endpoint),
                )
            )
        result[state_id] = float(max(ratios))
    return result


def _margin_ratio(
    left_scores: Sequence[float],
    right_scores: Sequence[float],
    left_mask: Sequence[bool],
    right_mask: Sequence[bool],
) -> float:
    if list(left_mask) != list(right_mask):
        raise ValueError("margin masks differ")
    mask = np.asarray(left_mask, dtype=bool)
    if int(mask.sum()) < 2:
        raise ValueError("margin requires two eligible candidates")
    left = np.sort(np.asarray(left_scores, dtype=np.float64)[mask])
    right = np.sort(np.asarray(right_scores, dtype=np.float64)[mask])
    left_gap = float(left[1] - left[0])
    right_gap = float(right[1] - right[0])
    return abs(left_gap - right_gap) / max(
        abs(left_gap), abs(right_gap), 1e-9
    )


def _verify_validation_repeat0_hard_bindings(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    hard_rows: Any,
) -> None:
    if type(hard_rows) is not list or len(hard_rows) != 64:
        raise ValueError("validation repeat0 hard denominator drifted")
    for row in hard_rows:
        state_id = row["state_spec_id"]
        for mode in v4.MODES:
            semantic = runs[(mode, state_id, 0)]
            pool = row["candidate_pools"][mode]
            if (
                pool["run_receipt_sha256"]
                != semantic["v4_run_receipt_sha256"]
                or pool["forward_invocation_id"]
                != semantic["forward_invocation_id"]
                or pool["pool_id"] != semantic["pool_id"]
                or pool["tensor_sha256"]
                != semantic["candidate_sha256"]
                or pool["row_sha256"] != semantic["row_sha256"]
            ):
                raise ValueError("validation repeat0 pool semantic drifted")
            for arm in v4.ARMS:
                source = row["selectors"][arm][mode]
                expected = semantic["selectors"][arm]
                if (
                    source["pool_id"] != semantic["pool_id"]
                    or source["candidate_tensor_sha256"]
                    != semantic["candidate_sha256"]
                    or not _float_list_exact(
                        source["scores"], expected["scores"]
                    )
                    or source["mask"] != expected["mask"]
                    or source["selected_index"]
                    != expected["selected_index"]
                    or not np.array_equal(
                        np.asarray(
                            source["selected_action_80x4"],
                            dtype=np.float64,
                        ),
                        expected["selected_action"],
                    )
                ):
                    raise ValueError(
                        "validation repeat0 selector semantic drifted"
                    )


def _array_blob(
    value: Any, *, expected_shape: tuple[int, ...] | None = None
) -> np.ndarray:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "dtype",
        "shape",
        "codec",
        "raw_byte_count",
        "raw_sha256",
        "encoded_sha256",
        "data_base64",
    }:
        raise ValueError("array blob exact schema drifted")
    if (
        value["schema_version"] != ARRAY_BLOB_SCHEMA
        or value["dtype"] != "<f8"
        or value["codec"] != "zlib_level9_then_base64_standard"
        or type(value["shape"]) is not list
        or not value["shape"]
        or any(type(item) is not int or item <= 0 for item in value["shape"])
    ):
        raise ValueError("array blob metadata drifted")
    try:
        encoded = base64.b64decode(
            value["data_base64"].encode("ascii"), validate=True
        )
        raw = zlib.decompress(encoded)
    except (ValueError, UnicodeError, zlib.error) as error:
        raise ValueError("array blob bytes drifted") from error
    if (
        base64.b64encode(encoded).decode("ascii") != value["data_base64"]
        or len(raw) != value["raw_byte_count"]
        or hashlib.sha256(raw).hexdigest() != value["raw_sha256"]
        or hashlib.sha256(encoded).hexdigest() != value["encoded_sha256"]
    ):
        raise ValueError("array blob hash drifted")
    shape = tuple(value["shape"])
    if expected_shape is not None and shape != expected_shape:
        raise ValueError("array blob shape drifted")
    array = np.frombuffer(raw, dtype="<f8").copy()
    if array.size != math.prod(shape):
        raise ValueError("array blob byte count drifted")
    array = array.reshape(shape)
    if not np.isfinite(array).all():
        raise ValueError("array blob nonfinite")
    return array


def _tensor_hashes(value: np.ndarray) -> tuple[str, list[str]]:
    canonical = np.ascontiguousarray(value.astype("<f8", copy=False))
    return (
        hashlib.sha256(canonical.tobytes(order="C")).hexdigest(),
        [
            hashlib.sha256(
                np.ascontiguousarray(canonical[index]).tobytes(order="C")
            ).hexdigest()
            for index in range(8)
        ],
    )


def _exact_cache(
    observed: Any,
    expected: Mapping[str, float],
    *,
    expected_keys: Sequence[str],
) -> None:
    if type(observed) is not dict or set(observed) != set(expected_keys):
        raise ValueError("derived endpoint cache keyset drifted")
    if set(expected) != set(expected_keys):
        raise ValueError("raw endpoint formula keyset drifted")
    for endpoint in expected_keys:
        value = float(observed[endpoint])
        if (
            not math.isfinite(value)
            or value < 0.0
            or value.hex() != float(expected[endpoint]).hex()
        ):
            raise ValueError(
                f"derived endpoint cache differs from raw preimage: {endpoint}"
            )


def _float_list_exact(left: Sequence[float], right: Sequence[float]) -> bool:
    return len(left) == len(right) and all(
        float(a).hex() == float(b).hex() for a, b in zip(left, right)
    )


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
