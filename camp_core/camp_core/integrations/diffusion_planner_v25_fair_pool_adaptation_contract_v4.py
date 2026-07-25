"""Fail-closed qualification-provenance correction for fair-pool contract v3.

v4 is design-only.  It does not authorize or perform acquisition.  It makes a
future qualification decision consume an out-of-band High trust anchor plus a
complete, content-addressed authority/preflight/calibration/freeze/validation
chain.  Numeric and hard decisions are rebuilt from the sealed preimages; the
caller cannot provide a status, a within-mode boolean, or a free threshold.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest_v2 as input_manifest,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    action_equivalent,
    bootstrap_upper_threshold,
    empirical_quantile_higher,
    sha256_json,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v3 import (
    CROSS_NUMERIC_IDS,
    FIXED_DP_HEAD,
    GENERATOR_NAME,
    MODE_BY_PHASE,
    WITHIN_NUMERIC_IDS,
    adaptation_contract_v3,
    decide_qualification_v3,
    validate_contract_v3,
)


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v4"
QUALIFICATION_PACKAGE_SCHEMA = (
    "camp_dp_v25_fair_pool_adaptation_qualification_package_v4"
)
TRUST_ANCHOR_SCHEMA = "camp_dp_v25_fair_pool_high_trust_anchor_v1"
CONTENT_ARTIFACT_SCHEMA = "camp_dp_v25_fair_pool_content_artifact_v1"
CONTENT_REVIEW_SCHEMA = (
    "camp_dp_v25_fair_pool_content_artifact_independent_review_v1"
)
V3_CONTRACT_ROOT = (
    "4365d56f0a7faa3bc73035fa731f3985ceff601c17ec0c75fbd1b81e4bc5a7ec"
)
V3_REVIEW_ROOT = (
    "5f64756e952be9b502e4b40f8acf1f40e83cef3219858ab9ea5835e78f05d1e1"
)
CONTROL_TASK_ID = "019f92d8-c971-7b13-924e-873ae9f24c14"
MODES = ("sequential_batch1_x8", "single_invocation_batch8")
ARMS = ("static14d", "scene14d")
REPEAT_INDICES = tuple(range(5))
WITHIN_PAIRS = tuple(
    (left, right)
    for left in REPEAT_INDICES
    for right in REPEAT_INDICES
    if left < right
)
CROSS_PAIRS = tuple((index, index) for index in REPEAT_INDICES)
ARTIFACT_NAMES = (
    "acquisition_authority",
    "acquisition_authority_review",
    "split_preflight",
    "split_preflight_review",
    "calibration_receipts",
    "calibration_receipts_review",
    "threshold_freeze",
    "threshold_freeze_review",
    "validation_receipts",
    "validation_receipts_review",
)
ARTIFACT_KIND = {
    "acquisition_authority": "future_high_acquisition_authority",
    "acquisition_authority_review": (
        "future_high_acquisition_authority_independent_review"
    ),
    "split_preflight": "input_only_split_preflight",
    "split_preflight_review": "input_only_split_preflight_independent_review",
    "calibration_receipts": "development_calibration_receipts",
    "calibration_receipts_review": (
        "development_calibration_receipts_independent_review"
    ),
    "threshold_freeze": "prevalidation_threshold_freeze",
    "threshold_freeze_review": (
        "prevalidation_threshold_freeze_independent_review"
    ),
    "validation_receipts": "independent_validation_receipts",
    "validation_receipts_review": (
        "independent_validation_receipts_independent_review"
    ),
}


def adaptation_contract_v4() -> dict[str, Any]:
    inherited = adaptation_contract_v3()
    numeric_keys = _numeric_keys()
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_provenance_design_only_acquisition_unauthorized",
        "superseded_preacquisition_diagnostic": {
            "schema_version": inherited["schema_version"],
            "payload_sha256": inherited["contract_payload_sha256"],
            "contract_root_sha256": V3_CONTRACT_ROOT,
            "review_root_sha256": V3_REVIEW_ROOT,
            "scope": "qualification_structure_without_sealed_provenance",
        },
        "inherited_v3_contract": inherited,
        "trust_anchor": {
            "schema_version": TRUST_ANCHOR_SCHEMA,
            "provider": "versioned_High_control_decision",
            "provider_task_id": CONTROL_TASK_ID,
            "consumer_argument": (
                "expected_trust_anchor_root_sha256_from_out_of_band_High_"
                "control_not_from_qualification_package"
            ),
            "exact_artifact_root_names": list(ARTIFACT_NAMES),
            "contract_and_review_roots_exact": True,
            "input_manifest_authority_root_exact": True,
            "arbitrary_but_well_formed_package_roots": "authority_failure",
        },
        "two_stage_authority": {
            "sequence": [
                "high_acquisition_authority_independently_reviewed",
                "input_only_preflight_independently_reviewed",
                "development_calibration_receipts_independently_reviewed",
                "threshold_freeze_independently_reviewed_before_validation",
                "independent_validation_receipts_independently_reviewed",
                "qualification_consumer_decision",
            ],
            "calibration_before_validation": True,
            "validation_model_pool_selector_call_count_at_freeze": 0,
            "validation_receipts_bind_exact_threshold_freeze_root": True,
            "post_validation_threshold_generation_or_mutation": (
                "authority_failure"
            ),
        },
        "sealed_artifact_schema": {
            "schema_version": CONTENT_ARTIFACT_SCHEMA,
            "root_formula": (
                "sha256(canonical_json_without_root_of_exact_kind_payload_"
                "payload_sha256)"
            ),
            "review_schema_version": CONTENT_REVIEW_SCHEMA,
            "review_must_bind_source_root_and_payload_sha256": True,
            "review_roots_are_pinned_by_external_trust_anchor": True,
        },
        "preflight_provenance": {
            "validator": (
                "diffusion_planner_v25_fair_pool_input_manifest_v2."
                "validate_preflight_receipt"
            ),
            "full_preimages_required": [
                "route_asset_bytes",
                "map_asset_bytes",
                "prepared_runtime_cases_bytes",
                "actual_input_tensors_for_all_128_states",
                "complete_input_only_preflight_receipt",
            ],
            "status_string_without_revalidation": "authority_failure",
        },
        "acquisition_receipt_schema": {
            "split_state_counts": {
                "development_calibration": 64,
                "independent_validation": 64,
            },
            "repeat_count_per_mode": 5,
            "within_pair_topology": [list(pair) for pair in WITHIN_PAIRS],
            "cross_pair_topology": [list(pair) for pair in CROSS_PAIRS],
            "run_receipt_bindings": [
                "actual_input_manifest_sha256",
                "actual_state_sha256",
                "actual_latent_manifest_sha256",
                "fixed_dp_head",
                "checkpoint_sha256",
                "model_source_sha256",
                "forward_invocation_id",
                "model_call_count",
                "pool_id",
                "candidate_tensor_sha256",
                "candidate_row_sha256",
            ],
            "pair_receipt_values": (
                "exact_applicable_endpoint_values_plus_two_exact_run_roots"
            ),
            "state_is_decision_unit": True,
        },
        "threshold_freeze_schema": {
            "required_numeric_key_count": len(numeric_keys),
            "required_numeric_keys": [list(key) for key in numeric_keys],
            "calibration_state_count": 64,
            "within_pair_receipts_per_state": 10,
            "cross_pair_receipts_per_state": 5,
            "state_statistic": "empirical_q99_higher_of_pair_values",
            "bootstrap": {
                "bit_generator": "PCG64DXSM",
                "seed": 825071,
                "resamples": 10000,
                "state_sample_size": 64,
                "with_replacement": True,
                "state_quantile": 0.99,
                "confidence_quantile": 0.95,
                "upper_sorted_index_zero_based": 9500,
            },
            "threshold": "max(endpoint_resolution_floor,bootstrap_upper)",
            "validation_exceedance": "value > threshold",
            "validation_pass": (
                "exceedance_count<=2_and_clopper_pearson_upper95<=0.10"
            ),
            "caller_threshold_or_self_hash_accepted": False,
        },
        "validation_receipt_schema": {
            "numeric_values": (
                "recomputed_from_bound_pair_receipts_not_caller_rows"
            ),
            "candidate_tensor": {
                "dtype": "<f8",
                "shape": [8, 80, 4],
                "row_and_tensor_sha_recomputed": True,
            },
            "selector_receipt": {
                "same_pool_id_and_tensor_sha_required": True,
                "mask_shape": [8],
                "score_shape": [8],
                "selected_index": (
                    "smallest_eligible_index_among_exact_minimum_scores"
                ),
                "selected_action": "exact_candidate_tensor_selected_row",
                "post_pool_dp_model_latent_generation_calls": 0,
                "tensor_pre_sha_equals_post_sha": True,
            },
            "hard_statuses_are_derived_from_receipts": True,
            "naked_all_finite_mask_action_or_call_count_accepted": False,
        },
        "decision": {
            "consumer": "decide_qualification_v4",
            "caller_status_or_within_boolean_accepted": False,
            "external_trust_anchor_required": True,
            "complete_artifact_chain_required": True,
            "threshold_recomputed": True,
            "hard_and_numeric_receipts_rebuilt": True,
            "v3_phase_topology_reused_after_provenance_validation": True,
            "pass_interpretation": inherited["scope"]["pass_interpretation"],
            "benefit_claim": False,
            "retraining_decision": "not_authorized",
        },
        "run_and_claim_boundary": deepcopy(
            inherited["run_and_claim_boundary"]
        ),
    }
    contract["contract_payload_sha256"] = sha256_json(contract)
    return contract


def validate_contract_v4(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or value != adaptation_contract_v4():
        raise ValueError("v4 contract literal drifted")
    payload = deepcopy(dict(value))
    supplied = payload.pop("contract_payload_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("v4 contract payload SHA drifted")
    validate_contract_v3(value["inherited_v3_contract"])
    return deepcopy(dict(value))


def make_content_artifact(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if type(kind) is not str or not kind or type(payload) is not dict:
        raise ValueError("content artifact input drifted")
    result = {
        "schema_version": CONTENT_ARTIFACT_SCHEMA,
        "kind": kind,
        "payload": deepcopy(dict(payload)),
        "payload_sha256": sha256_json(payload),
    }
    result["root_sha256"] = sha256_json(result)
    return result


def make_content_review(
    source: Mapping[str, Any],
    *,
    review_kind: str,
) -> dict[str, Any]:
    checked = _validate_content_artifact(source, expected_kind=source["kind"])
    payload = {
        "schema_version": CONTENT_REVIEW_SCHEMA,
        "status": "passed_independent_literal_reconstruction",
        "source_kind": checked["kind"],
        "source_root_sha256": checked["root_sha256"],
        "source_payload_sha256": checked["payload_sha256"],
        "reviewer_role_separate": True,
        "producer_module_imported": False,
    }
    return make_content_artifact(review_kind, payload)


def make_trust_anchor(
    contract: Mapping[str, Any],
    *,
    contract_root_sha256: str,
    contract_review_root_sha256: str,
    input_manifest_authority_root_sha256: str,
    artifact_roots: Mapping[str, str],
    high_decision_sha256: str,
) -> dict[str, Any]:
    frozen = validate_contract_v4(contract)
    if type(artifact_roots) is not dict or set(artifact_roots) != set(
        ARTIFACT_NAMES
    ):
        raise ValueError("trust anchor artifact root keyset drifted")
    result = {
        "schema_version": TRUST_ANCHOR_SCHEMA,
        "status": "trusted_by_versioned_High_control",
        "provider_task_id": CONTROL_TASK_ID,
        "high_decision_sha256": _sha256(
            high_decision_sha256, "High decision"
        ),
        "contract_payload_sha256": frozen["contract_payload_sha256"],
        "contract_root_sha256": _sha256(
            contract_root_sha256, "contract root"
        ),
        "contract_review_root_sha256": _sha256(
            contract_review_root_sha256, "contract review root"
        ),
        "input_manifest_authority_root_sha256": _sha256(
            input_manifest_authority_root_sha256,
            "input manifest authority root",
        ),
        "artifact_roots": {
            name: _sha256(artifact_roots[name], f"{name} root")
            for name in ARTIFACT_NAMES
        },
        "sequence": list(frozen["two_stage_authority"]["sequence"]),
        "validation_started_after_threshold_freeze": True,
        "acquisition_authorized": True,
        "fresh_holdout_closed_loop_training_authorized": False,
    }
    result["trust_anchor_root_sha256"] = sha256_json(result)
    return result


def decide_qualification_v4(
    contract: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    trust_anchor: Mapping[str, Any],
    expected_trust_anchor_root_sha256: str,
) -> dict[str, Any]:
    frozen = validate_contract_v4(contract)
    anchor = _validate_trust_anchor(
        trust_anchor,
        contract=frozen,
        expected_root=expected_trust_anchor_root_sha256,
    )
    artifacts = _validate_package(package, contract=frozen, anchor=anchor)
    authority = _validate_authority_payload(
        artifacts["acquisition_authority"]["payload"],
        contract=frozen,
        anchor=anchor,
    )
    manifests = _revalidate_preflight(
        artifacts["split_preflight"]["payload"],
        contract=frozen,
        anchor=anchor,
        authority=authority,
    )
    calibration = _validate_receipt_payload(
        artifacts["calibration_receipts"]["payload"],
        contract=frozen,
        anchor=anchor,
        manifests=manifests,
        split="development_calibration",
    )
    freeze = _validate_threshold_freeze(
        artifacts["threshold_freeze"]["payload"],
        contract=frozen,
        anchor=anchor,
        calibration=calibration,
    )
    validation = _validate_receipt_payload(
        artifacts["validation_receipts"]["payload"],
        contract=frozen,
        anchor=anchor,
        manifests=manifests,
        split="independent_validation",
    )
    v3_receipt = _derive_v3_receipt(
        contract=frozen,
        anchor=anchor,
        preflight_artifact=artifacts["split_preflight"],
        freeze=freeze,
        validation=validation,
        validation_payload=artifacts["validation_receipts"]["payload"],
    )
    decision = decide_qualification_v3(
        frozen["inherited_v3_contract"],
        v3_receipt,
    )
    return {
        **decision,
        "schema_version": (
            "camp_dp_v25_fair_pool_adaptation_qualification_decision_v4"
        ),
        "trust_anchor_root_sha256": anchor[
            "trust_anchor_root_sha256"
        ],
        "complete_artifact_chain_validated": True,
        "preflight_revalidated_from_full_preimages": True,
        "thresholds_recomputed_from_calibration_receipts": True,
        "validation_values_rebuilt_from_bound_pair_receipts": True,
        "hard_evidence_rebuilt_from_bound_pool_selector_receipts": True,
        "caller_supplied_threshold_status_or_within_boolean_used": False,
    }


def _validate_trust_anchor(
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
        "input_manifest_authority_root_sha256",
        "artifact_roots",
        "sequence",
        "validation_started_after_threshold_freeze",
        "acquisition_authorized",
        "fresh_holdout_closed_loop_training_authorized",
        "trust_anchor_root_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("external trust anchor exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("trust_anchor_root_sha256")
    if supplied != sha256_json(payload) or supplied != _sha256(
        expected_root, "externally trusted anchor root"
    ):
        raise ValueError("external High trust anchor root drifted")
    if (
        value["schema_version"] != TRUST_ANCHOR_SCHEMA
        or value["status"] != "trusted_by_versioned_High_control"
        or value["provider_task_id"] != CONTROL_TASK_ID
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["sequence"]
        != contract["two_stage_authority"]["sequence"]
        or value["validation_started_after_threshold_freeze"] is not True
        or value["acquisition_authorized"] is not True
        or value["fresh_holdout_closed_loop_training_authorized"] is not False
    ):
        raise ValueError("external High trust anchor authority drifted")
    for field in (
        "high_decision_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "input_manifest_authority_root_sha256",
    ):
        _sha256(value[field], field)
    roots = value["artifact_roots"]
    if type(roots) is not dict or set(roots) != set(ARTIFACT_NAMES):
        raise ValueError("external trust anchor artifact roots drifted")
    for name in ARTIFACT_NAMES:
        _sha256(roots[name], f"{name} root")
    return dict(value)


def _validate_package(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "contract_payload_sha256",
        "trust_anchor_root_sha256",
        "artifacts",
    }:
        raise ValueError("qualification package exact schema drifted")
    if (
        value["schema_version"] != QUALIFICATION_PACKAGE_SCHEMA
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["trust_anchor_root_sha256"]
        != anchor["trust_anchor_root_sha256"]
    ):
        raise ValueError("qualification package authority drifted")
    supplied = value["artifacts"]
    if type(supplied) is not dict or set(supplied) != set(ARTIFACT_NAMES):
        raise ValueError("qualification package artifact keyset drifted")
    checked = {}
    for name in ARTIFACT_NAMES:
        checked[name] = _validate_content_artifact(
            supplied[name],
            expected_kind=ARTIFACT_KIND[name],
            expected_root=anchor["artifact_roots"][name],
        )
    for source_name, review_name in (
        ("acquisition_authority", "acquisition_authority_review"),
        ("split_preflight", "split_preflight_review"),
        ("calibration_receipts", "calibration_receipts_review"),
        ("threshold_freeze", "threshold_freeze_review"),
        ("validation_receipts", "validation_receipts_review"),
    ):
        _validate_review_payload(
            checked[review_name]["payload"],
            source=checked[source_name],
        )
    return checked


def _validate_content_artifact(
    value: Mapping[str, Any],
    *,
    expected_kind: str,
    expected_root: str | None = None,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "kind",
        "payload",
        "payload_sha256",
        "root_sha256",
    }:
        raise ValueError("content artifact exact schema drifted")
    if (
        value["schema_version"] != CONTENT_ARTIFACT_SCHEMA
        or value["kind"] != expected_kind
        or type(value["payload"]) is not dict
        or value["payload_sha256"] != sha256_json(value["payload"])
    ):
        raise ValueError("content artifact payload drifted")
    payload = dict(value)
    supplied = payload.pop("root_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("content artifact root drifted")
    if expected_root is not None and supplied != expected_root:
        raise ValueError("content artifact is not externally trusted")
    return deepcopy(dict(value))


def _validate_review_payload(
    value: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
) -> None:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "status",
        "source_kind",
        "source_root_sha256",
        "source_payload_sha256",
        "reviewer_role_separate",
        "producer_module_imported",
    }:
        raise ValueError("independent content review schema drifted")
    if (
        value["schema_version"] != CONTENT_REVIEW_SCHEMA
        or value["status"] != "passed_independent_literal_reconstruction"
        or value["source_kind"] != source["kind"]
        or value["source_root_sha256"] != source["root_sha256"]
        or value["source_payload_sha256"] != source["payload_sha256"]
        or value["reviewer_role_separate"] is not True
        or value["producer_module_imported"] is not False
    ):
        raise ValueError("independent content review binding drifted")


def _validate_authority_payload(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "contract_payload_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "input_manifest_acquisition_authority",
        "authorized_phases",
        "acquisition_authorized",
        "fresh_holdout_closed_loop_training_authorized",
    }:
        raise ValueError("acquisition authority payload schema drifted")
    if (
        value["schema_version"]
        != "camp_dp_v25_fair_pool_future_acquisition_authority_v1"
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["contract_root_sha256"] != anchor["contract_root_sha256"]
        or value["contract_review_root_sha256"]
        != anchor["contract_review_root_sha256"]
        or value["authorized_phases"]
        != [
            "input_only_preflight",
            "development_calibration",
            "threshold_freeze",
            "independent_validation",
        ]
        or value["acquisition_authorized"] is not True
        or value["fresh_holdout_closed_loop_training_authorized"] is not False
    ):
        raise ValueError("acquisition authority payload drifted")
    binding = value["input_manifest_acquisition_authority"]
    if (
        type(binding) is not dict
        or binding.get("authority_artifact_root_sha256")
        != anchor["input_manifest_authority_root_sha256"]
        or binding.get("authorized_contract_root_sha256")
        != anchor["contract_root_sha256"]
        or binding.get("authorized_contract_review_root_sha256")
        != anchor["contract_review_root_sha256"]
    ):
        raise ValueError("input-manifest acquisition authority drifted")
    return deepcopy(dict(value))


def _revalidate_preflight(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "receipt",
        "route_asset_bytes_hex",
        "map_asset_bytes_hex",
        "prepared_runtime_cases_bytes_hex",
        "actual_input_tensors",
    }:
        raise ValueError("preflight artifact payload schema drifted")
    if value["schema_version"] != (
        "camp_dp_v25_fair_pool_full_preflight_preimages_v1"
    ):
        raise ValueError("preflight preimage schema drifted")
    route = _hex_bytes(value["route_asset_bytes_hex"], "route asset")
    map_bytes = _hex_bytes(value["map_asset_bytes_hex"], "map asset")
    prepared = _hex_bytes(
        value["prepared_runtime_cases_bytes_hex"], "B4 prepared cases"
    )
    tensors = _decode_tensor_preimages(value["actual_input_tensors"])
    inherited = contract["inherited_v3_contract"]
    checked = input_manifest.validate_preflight_receipt(
        value["receipt"],
        acquisition_authority=authority[
            "input_manifest_acquisition_authority"
        ],
        expected_acquisition_authority_root_sha256=anchor[
            "input_manifest_authority_root_sha256"
        ],
        expected_authorized_contract_root_sha256=anchor[
            "contract_root_sha256"
        ],
        expected_authorized_contract_review_root_sha256=anchor[
            "contract_review_root_sha256"
        ],
        calibration_specs=inherited["state_specifications"][
            "development_calibration"
        ],
        validation_specs=inherited["state_specifications"][
            "independent_validation"
        ],
        route_asset_bytes=route,
        map_asset_bytes=map_bytes,
        prepared_runtime_cases_bytes=prepared,
        actual_input_tensors_by_state_id=tensors,
    )
    manifests = checked["calibration_manifests"] + checked[
        "validation_manifests"
    ]
    return {
        row["state_spec_id"]: row
        for row in manifests
    }


def _decode_tensor_preimages(value: Any) -> dict[str, dict[str, np.ndarray]]:
    if type(value) is not list or len(value) != 128:
        raise ValueError("actual input tensor preimage denominator drifted")
    result: dict[str, dict[str, np.ndarray]] = {}
    for state in value:
        if type(state) is not dict or set(state) != {
            "state_spec_id",
            "tensors",
        }:
            raise ValueError("actual input tensor state schema drifted")
        state_id = state["state_spec_id"]
        if type(state_id) is not str or state_id in result:
            raise ValueError("actual input tensor state duplicate")
        rows = state["tensors"]
        if type(rows) is not list or not rows:
            raise ValueError("actual input tensor list drifted")
        tensors = {}
        for row in rows:
            if type(row) is not dict or set(row) != {
                "name",
                "dtype",
                "shape",
                "data_hex",
            }:
                raise ValueError("actual input tensor preimage schema drifted")
            name = row["name"]
            if type(name) is not str or not name or name in tensors:
                raise ValueError("actual input tensor name drifted")
            dtype = np.dtype(row["dtype"])
            if dtype.kind not in "biuf":
                raise ValueError("actual input tensor dtype drifted")
            shape = tuple(row["shape"])
            if (
                not shape
                or any(type(item) is not int or item <= 0 for item in shape)
            ):
                raise ValueError("actual input tensor shape drifted")
            raw = _hex_bytes(row["data_hex"], "actual input tensor")
            array = np.frombuffer(raw, dtype=dtype).copy()
            if array.size != math.prod(shape):
                raise ValueError("actual input tensor byte count drifted")
            tensors[name] = array.reshape(shape)
        result[state_id] = tensors
    return result


def _validate_receipt_payload(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    manifests: Mapping[str, Mapping[str, Any]],
    split: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "split",
        "authority_root_sha256",
        "preflight_root_sha256",
        "threshold_freeze_root_sha256",
        "threshold_freeze_review_root_sha256",
        "run_receipts",
        "pair_receipts",
        "hard_state_receipts",
    }:
        raise ValueError("acquisition receipt payload exact schema drifted")
    if (
        value["schema_version"]
        != "camp_dp_v25_fair_pool_mode_repeat_receipts_v1"
        or value["split"] != split
        or value["authority_root_sha256"]
        != anchor["artifact_roots"]["acquisition_authority"]
        or value["preflight_root_sha256"]
        != anchor["artifact_roots"]["split_preflight"]
    ):
        raise ValueError("acquisition receipt authority drifted")
    if split == "development_calibration":
        if (
            value["threshold_freeze_root_sha256"] is not None
            or value["threshold_freeze_review_root_sha256"] is not None
            or value["hard_state_receipts"] != []
        ):
            raise ValueError("calibration receipt phase drifted")
    else:
        if (
            value["threshold_freeze_root_sha256"]
            != anchor["artifact_roots"]["threshold_freeze"]
            or value["threshold_freeze_review_root_sha256"]
            != anchor["artifact_roots"]["threshold_freeze_review"]
        ):
            raise ValueError("validation did not bind frozen thresholds")
    specs = contract["inherited_v3_contract"]["state_specifications"][split]
    state_ids = [row["state_spec_id"] for row in specs]
    manifest_by_id = {state_id: manifests[state_id] for state_id in state_ids}
    runs = _validate_run_receipts(
        value["run_receipts"],
        state_ids=state_ids,
        manifests=manifest_by_id,
    )
    pairs, statistics, pair_roots = _validate_pair_receipts(
        value["pair_receipts"],
        state_ids=state_ids,
        runs=runs,
    )
    return {
        "state_ids": state_ids,
        "runs": runs,
        "pairs": pairs,
        "statistics": statistics,
        "pair_roots": pair_roots,
        "hard_state_receipts": value["hard_state_receipts"],
    }


def _validate_run_receipts(
    value: Any,
    *,
    state_ids: Sequence[str],
    manifests: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if type(value) is not list or len(value) != 64 * 2 * 5:
        raise ValueError("run receipt denominator drifted")
    result = {}
    fields = {
        "state_spec_id",
        "mode",
        "repeat_index",
        "input_manifest_sha256",
        "actual_state_sha256",
        "actual_latent_manifest_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "model_source_sha256",
        "forward_invocation_id",
        "model_call_count",
        "pool_id",
        "candidate_tensor_sha256",
        "candidate_row_sha256",
        "all_finite",
        "receipt_sha256",
    }
    expected_checkpoint = (
        "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
    )
    expected_model = (
        "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
    )
    for row in value:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("run receipt exact schema drifted")
        payload = dict(row)
        supplied = payload.pop("receipt_sha256")
        if supplied != sha256_json(payload):
            raise ValueError("run receipt content root drifted")
        key = (row["mode"], row["state_spec_id"], row["repeat_index"])
        if (
            row["state_spec_id"] not in state_ids
            or row["mode"] not in MODES
            or row["repeat_index"] not in REPEAT_INDICES
            or key in result
        ):
            raise ValueError("run receipt identity drifted")
        manifest = manifests[row["state_spec_id"]]
        expected_calls = 8 if row["mode"] == MODES[0] else 1
        row_shas = row["candidate_row_sha256"]
        if (
            row["input_manifest_sha256"] != manifest["manifest_sha256"]
            or row["actual_state_sha256"] != manifest["actual_state_sha256"]
            or row["actual_latent_manifest_sha256"]
            != manifest["actual_latent_tensor_manifest"]["manifest_sha256"]
            or row["fixed_dp_head"] != FIXED_DP_HEAD
            or row["checkpoint_sha256"] != expected_checkpoint
            or row["model_source_sha256"] != expected_model
            or type(row["forward_invocation_id"]) is not str
            or not row["forward_invocation_id"]
            or row["model_call_count"] != expected_calls
            or type(row["pool_id"]) is not str
            or not row["pool_id"]
            or _sha256(
                row["candidate_tensor_sha256"], "candidate tensor"
            )
            != row["candidate_tensor_sha256"]
            or type(row_shas) is not list
            or len(row_shas) != 8
            or len(set(row_shas)) != 8
            or row["all_finite"] is not True
        ):
            raise ValueError("run receipt authority or K8 binding drifted")
        for digest in row_shas:
            _sha256(digest, "candidate row")
        result[key] = dict(row)
    expected = {
        (mode, state_id, repeat)
        for mode in MODES
        for state_id in state_ids
        for repeat in REPEAT_INDICES
    }
    if set(result) != expected:
        raise ValueError("run receipt keyset drifted")
    return result


def _validate_pair_receipts(
    value: Any,
    *,
    state_ids: Sequence[str],
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
) -> tuple[
    dict[tuple[str, str, str, int], dict[str, Any]],
    dict[tuple[str, str, str], list[float]],
    dict[tuple[str, str, str], list[list[str]]],
]:
    expected_count = 64 * (10 + 10 + 5)
    if type(value) is not list or len(value) != expected_count:
        raise ValueError("pair receipt denominator drifted")
    records = {}
    state_values = {
        key: {state_id: [] for state_id in state_ids}
        for key in _numeric_keys()
    }
    state_roots = {
        key: {state_id: [] for state_id in state_ids}
        for key in _numeric_keys()
    }
    fields = {
        "phase",
        "mode",
        "state_spec_id",
        "pair_index",
        "left_repeat_index",
        "right_repeat_index",
        "left_run_receipt_sha256",
        "right_run_receipt_sha256",
        "endpoint_values",
        "receipt_sha256",
    }
    for row in value:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("pair receipt exact schema drifted")
        payload = dict(row)
        supplied = payload.pop("receipt_sha256")
        if supplied != sha256_json(payload):
            raise ValueError("pair receipt content root drifted")
        phase = row["phase"]
        mode = row["mode"]
        if phase in {"sequential_within", "batch8_within"}:
            expected_mode = MODE_BY_PHASE[phase]
            topology = WITHIN_PAIRS
            endpoints = WITHIN_NUMERIC_IDS
            left_mode = right_mode = expected_mode
        elif phase == "cross_mode":
            expected_mode = MODE_BY_PHASE[phase]
            topology = CROSS_PAIRS
            endpoints = CROSS_NUMERIC_IDS
            left_mode, right_mode = MODES
        else:
            raise ValueError("pair receipt phase drifted")
        if (
            mode != expected_mode
            or row["state_spec_id"] not in state_ids
            or type(row["pair_index"]) is not int
            or not 0 <= row["pair_index"] < len(topology)
            or (
                row["left_repeat_index"],
                row["right_repeat_index"],
            )
            != topology[row["pair_index"]]
        ):
            raise ValueError("pair receipt topology drifted")
        identity = (
            phase,
            mode,
            row["state_spec_id"],
            row["pair_index"],
        )
        if identity in records:
            raise ValueError("pair receipt duplicate")
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
        if (
            row["left_run_receipt_sha256"] != left["receipt_sha256"]
            or row["right_run_receipt_sha256"] != right["receipt_sha256"]
        ):
            raise ValueError("pair receipt run binding drifted")
        endpoint_values = row["endpoint_values"]
        if type(endpoint_values) is not dict or set(endpoint_values) != set(
            endpoints
        ):
            raise ValueError("pair endpoint keyset drifted")
        for endpoint_id in endpoints:
            observed = float(endpoint_values[endpoint_id])
            if not math.isfinite(observed) or observed < 0.0:
                raise ValueError("pair endpoint value drifted")
            key = (phase, mode, endpoint_id)
            state_values[key][row["state_spec_id"]].append(observed)
            state_roots[key][row["state_spec_id"]].append(supplied)
        records[identity] = dict(row)
    expected_identities = {
        (phase, MODE_BY_PHASE[phase], state_id, pair_index)
        for phase, topology in (
            ("sequential_within", WITHIN_PAIRS),
            ("batch8_within", WITHIN_PAIRS),
            ("cross_mode", CROSS_PAIRS),
        )
        for state_id in state_ids
        for pair_index in range(len(topology))
    }
    if set(records) != expected_identities:
        raise ValueError("pair receipt keyset drifted")
    statistics = {
        key: [
            empirical_quantile_higher(state_values[key][state_id], 0.99)
            for state_id in state_ids
        ]
        for key in _numeric_keys()
    }
    roots = {
        key: [state_roots[key][state_id] for state_id in state_ids]
        for key in _numeric_keys()
    }
    return records, statistics, roots


def _validate_threshold_freeze(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    calibration: Mapping[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "contract_root_sha256",
        "acquisition_authority_root_sha256",
        "calibration_receipts_root_sha256",
        "calibration_receipts_review_root_sha256",
        "validation_model_pool_selector_call_count_before_seal",
        "records",
    }:
        raise ValueError("threshold freeze exact schema drifted")
    if (
        value["schema_version"]
        != "camp_dp_v25_fair_pool_threshold_freeze_v1"
        or value["contract_root_sha256"] != anchor["contract_root_sha256"]
        or value["acquisition_authority_root_sha256"]
        != anchor["artifact_roots"]["acquisition_authority"]
        or value["calibration_receipts_root_sha256"]
        != anchor["artifact_roots"]["calibration_receipts"]
        or value["calibration_receipts_review_root_sha256"]
        != anchor["artifact_roots"]["calibration_receipts_review"]
        or value["validation_model_pool_selector_call_count_before_seal"] != 0
    ):
        raise ValueError("threshold freeze authority or chronology drifted")
    rows = value["records"]
    keys = _numeric_keys()
    if type(rows) is not list or len(rows) != len(keys):
        raise ValueError("threshold freeze key denominator drifted")
    result = {}
    fields = {
        "phase",
        "mode",
        "endpoint_id",
        "calibration_state_ids",
        "state_pair_receipt_sha256",
        "state_statistics",
        "bootstrap_preimage_sha256",
        "resolution_floor",
        "bootstrap_result",
        "threshold",
    }
    for row in rows:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("threshold freeze record schema drifted")
        key = (row["phase"], row["mode"], row["endpoint_id"])
        if key not in keys or key in result:
            raise ValueError("threshold freeze record key drifted")
        statistics = calibration["statistics"][key]
        roots = calibration["pair_roots"][key]
        floor = _resolution_floor(key[2])
        bootstrap = bootstrap_upper_threshold(
            statistics,
            resolution_floor=floor,
        )
        preimage = {
            "algorithm": contract["threshold_freeze_schema"]["bootstrap"],
            "phase": key[0],
            "mode": key[1],
            "endpoint_id": key[2],
            "calibration_state_ids": calibration["state_ids"],
            "state_pair_receipt_sha256": roots,
            "state_statistics": statistics,
            "resolution_floor": floor,
        }
        if (
            row["calibration_state_ids"] != calibration["state_ids"]
            or row["state_pair_receipt_sha256"] != roots
            or row["state_statistics"] != statistics
            or row["bootstrap_preimage_sha256"] != sha256_json(preimage)
            or float(row["resolution_floor"]) != floor
            or float(row["bootstrap_result"]) != bootstrap
            or float(row["threshold"]) != max(floor, bootstrap)
        ):
            raise ValueError("threshold freeze recomputation drifted")
        result[key] = dict(row)
    if set(result) != set(keys):
        raise ValueError("threshold freeze required record omitted")
    return result


def _derive_v3_receipt(
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    preflight_artifact: Mapping[str, Any],
    freeze: Mapping[tuple[str, str, str], Mapping[str, Any]],
    validation: Mapping[str, Any],
    validation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    numeric = []
    for key in _numeric_keys():
        threshold = float(freeze[key]["threshold"])
        authority = {
            "schema_version": (
                "camp_dp_v25_fair_pool_threshold_authority_v1"
            ),
            "phase": key[0],
            "mode": key[1],
            "endpoint_id": key[2],
            "calibration_state_count": 64,
            "threshold": threshold,
            "algorithm": (
                "q99_higher_then_10000_state_bootstrap_pcg64dxsm_"
                "seed825071_one_sided95_index9500_max_resolution_floor"
            ),
        }
        authority["authority_sha256"] = sha256_json(authority)
        numeric.append(
            {
                "phase": key[0],
                "mode": key[1],
                "endpoint_id": key[2],
                "state_values": [
                    {"state_spec_id": state_id, "value": value}
                    for state_id, value in zip(
                        validation["state_ids"],
                        validation["statistics"][key],
                    )
                ],
                "threshold": threshold,
                "threshold_authority": authority,
            }
        )
    hard = _derive_hard_evidence(
        contract=contract,
        validation=validation,
        value=validation_payload["hard_state_receipts"],
    )
    hard["split_preflight"] = {
        "status": "passed_before_first_model_pool_selector_call",
        "receipt_sha256": preflight_artifact["root_sha256"],
        "contract_root_sha256": anchor["contract_root_sha256"],
        "contract_review_root_sha256": anchor[
            "contract_review_root_sha256"
        ],
        "acquisition_authority_root_sha256": anchor[
            "input_manifest_authority_root_sha256"
        ],
    }
    inherited = contract["inherited_v3_contract"]
    return {
        "schema_version": (
            "camp_dp_v25_fair_pool_adaptation_qualification_receipt_v3"
        ),
        "contract_payload_sha256": inherited["contract_payload_sha256"],
        "contract_root_sha256": anchor["contract_root_sha256"],
        "contract_review_root_sha256": anchor[
            "contract_review_root_sha256"
        ],
        "acquisition_authority_root_sha256": anchor[
            "input_manifest_authority_root_sha256"
        ],
        "numeric_evidence": numeric,
        "hard_evidence": hard,
    }


def _derive_hard_evidence(
    *,
    contract: Mapping[str, Any],
    validation: Mapping[str, Any],
    value: Any,
) -> dict[str, Any]:
    if type(value) is not list or len(value) != 64:
        raise ValueError("validation hard-state denominator drifted")
    state_ids = validation["state_ids"]
    runs = validation["runs"]
    k8 = {mode: [] for mode in MODES}
    pool = []
    masks = {arm: [] for arm in ARMS}
    actions = {arm: [] for arm in ARMS}
    fields = {
        "state_spec_id",
        "candidate_pools",
        "selectors",
        "receipt_sha256",
    }
    for expected_state, row in zip(state_ids, value):
        if type(row) is not dict or set(row) != fields:
            raise ValueError("validation hard-state exact schema drifted")
        payload = dict(row)
        supplied = payload.pop("receipt_sha256")
        if supplied != sha256_json(payload) or row[
            "state_spec_id"
        ] != expected_state:
            raise ValueError("validation hard-state root or order drifted")
        pools = row["candidate_pools"]
        if type(pools) is not dict or set(pools) != set(MODES):
            raise ValueError("candidate pool mode keyset drifted")
        checked_pools = {}
        for mode in MODES:
            checked = _validate_candidate_pool(
                pools[mode],
                run=runs[(mode, expected_state, 0)],
            )
            checked_pools[mode] = checked
            k8[mode].append(
                {
                    "state_spec_id": expected_state,
                    "all_finite": True,
                    "row_sha256": checked["row_sha256"],
                }
            )
        selectors = row["selectors"]
        if type(selectors) is not dict or set(selectors) != set(ARMS):
            raise ValueError("selector arm keyset drifted")
        checked_selectors = {}
        for arm in ARMS:
            arm_value = selectors[arm]
            if type(arm_value) is not dict or set(arm_value) != set(MODES):
                raise ValueError("selector mode keyset drifted")
            checked_selectors[arm] = {
                mode: _validate_selector_receipt(
                    arm_value[mode],
                    state_id=expected_state,
                    arm=arm,
                    mode=mode,
                    pool=checked_pools[mode],
                )
                for mode in MODES
            }
            left = checked_selectors[arm][MODES[0]]
            right = checked_selectors[arm][MODES[1]]
            masks[arm].append(
                {
                    "state_spec_id": expected_state,
                    "sequential_mask": left["mask"],
                    "batch8_mask": right["mask"],
                }
            )
            actions[arm].append(
                {
                    "state_spec_id": expected_state,
                    "sequential_selected_index": left["selected_index"],
                    "batch8_selected_index": right["selected_index"],
                    "sequential_action_80x4": left["selected_action_80x4"],
                    "batch8_action_80x4": right["selected_action_80x4"],
                    "sequential_executable": left["executable"],
                    "batch8_executable": right["executable"],
                    "sequential_terminal": left["terminal"],
                    "batch8_terminal": right["terminal"],
                }
            )
        zero_call_and_immutable = all(
            checked_selectors[arm][mode]["zero_call_and_immutable"]
            for arm in ARMS
            for mode in MODES
        )
        if not zero_call_and_immutable:
            raise ValueError("post-pool call or tensor mutation detected")
        pool.append(
            {
                "state_spec_id": expected_state,
                "pre_tensor_sha256": checked_pools[MODES[0]][
                    "tensor_sha256"
                ],
                "post_tensor_sha256": checked_pools[MODES[0]][
                    "tensor_sha256"
                ],
                "dp_model_call_count_after_pool": 0,
                "latent_replacement_count_after_pool": 0,
                "candidate_generation_count_after_pool": 0,
            }
        )
    inherited = contract["inherited_v3_contract"]
    fingerprint = {
        "fixed_dp_head": FIXED_DP_HEAD,
        "generator": GENERATOR_NAME,
        "candidate_k": 8,
        "checkpoint_sha256": inherited["model_fingerprint_authority"][
            "checkpoint_sha256"
        ],
        "model_source_sha256": inherited["model_fingerprint_authority"][
            "model_source_sha256"
        ],
        "decoder_source_sha256": inherited[
            "model_fingerprint_authority"
        ]["decoder_source_sha256"],
        "encoder_source_sha256": inherited[
            "model_fingerprint_authority"
        ]["encoder_source_sha256"],
        "route_asset_sha256": inherited["input_authority"][
            "source_scene_algorithm"
        ]["route_asset_sha256"],
        "map_geometry_sha256": inherited["input_authority"][
            "source_scene_algorithm"
        ]["map_asset_sha256"],
        "dtype": "float32",
    }
    return {
        "fingerprints": {
            "expected": fingerprint,
            "observed_by_mode": {mode: deepcopy(fingerprint) for mode in MODES},
        },
        "k8": k8,
        "pool": pool,
        "masks": masks,
        "actions": actions,
    }


def _validate_candidate_pool(
    value: Mapping[str, Any],
    *,
    run: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "run_receipt_sha256",
        "state_spec_id",
        "mode",
        "forward_invocation_id",
        "pool_id",
        "input_manifest_sha256",
        "latent_manifest_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "dtype",
        "shape",
        "candidate_tensor",
        "tensor_sha256",
        "row_sha256",
    }:
        raise ValueError("candidate pool preimage schema drifted")
    array = np.asarray(value["candidate_tensor"], dtype=np.float64)
    if (
        value["run_receipt_sha256"] != run["receipt_sha256"]
        or value["state_spec_id"] != run["state_spec_id"]
        or value["mode"] != run["mode"]
        or value["forward_invocation_id"] != run["forward_invocation_id"]
        or value["pool_id"] != run["pool_id"]
        or value["input_manifest_sha256"] != run["input_manifest_sha256"]
        or value["latent_manifest_sha256"]
        != run["actual_latent_manifest_sha256"]
        or value["fixed_dp_head"] != FIXED_DP_HEAD
        or value["checkpoint_sha256"] != run["checkpoint_sha256"]
        or value["dtype"] != "<f8"
        or value["shape"] != [8, 80, 4]
        or array.shape != (8, 80, 4)
        or not np.isfinite(array).all()
    ):
        raise ValueError("candidate pool provenance drifted")
    canonical = np.ascontiguousarray(array.astype("<f8", copy=False))
    tensor_sha = hashlib.sha256(canonical.tobytes(order="C")).hexdigest()
    row_sha = [
        hashlib.sha256(
            np.ascontiguousarray(canonical[index]).tobytes(order="C")
        ).hexdigest()
        for index in range(8)
    ]
    if (
        value["tensor_sha256"] != tensor_sha
        or value["row_sha256"] != row_sha
        or len(set(row_sha)) != 8
        or run["candidate_tensor_sha256"] != tensor_sha
        or run["candidate_row_sha256"] != row_sha
    ):
        raise ValueError("candidate tensor or row hash drifted")
    return {
        "array": canonical,
        "tensor_sha256": tensor_sha,
        "row_sha256": row_sha,
        "pool_id": value["pool_id"],
    }


def _validate_selector_receipt(
    value: Mapping[str, Any],
    *,
    state_id: str,
    arm: str,
    mode: str,
    pool: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "state_spec_id",
        "arm",
        "mode",
        "pool_id",
        "candidate_tensor_sha256",
        "pre_tensor_sha256",
        "post_tensor_sha256",
        "scores",
        "mask",
        "selected_index",
        "selected_action_80x4",
        "executable",
        "terminal",
        "dp_model_call_count_after_pool",
        "latent_replacement_count_after_pool",
        "candidate_generation_count_after_pool",
        "receipt_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("selector receipt exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("receipt_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("selector receipt content root drifted")
    scores = np.asarray(value["scores"], dtype=np.float64)
    mask = np.asarray(value["mask"])
    if (
        value["state_spec_id"] != state_id
        or value["arm"] != arm
        or value["mode"] != mode
        or value["pool_id"] != pool["pool_id"]
        or value["candidate_tensor_sha256"] != pool["tensor_sha256"]
        or value["pre_tensor_sha256"] != pool["tensor_sha256"]
        or value["post_tensor_sha256"] != pool["tensor_sha256"]
        or scores.shape != (8,)
        or not np.isfinite(scores).all()
        or mask.shape != (8,)
        or mask.dtype != np.bool_
        or not mask.any()
    ):
        raise ValueError("selector pool/score/mask binding drifted")
    eligible = np.flatnonzero(mask)
    best_score = float(np.min(scores[eligible]))
    expected_index = int(eligible[scores[eligible] == best_score][0])
    selected = np.asarray(value["selected_action_80x4"], dtype=np.float64)
    expected_action = pool["array"][expected_index]
    if (
        value["selected_index"] != expected_index
        or selected.shape != (80, 4)
        or not np.isfinite(selected).all()
        or not np.array_equal(selected, expected_action)
        or value["executable"]
        not in {"executable", "non_executable_retained"}
        or value["terminal"]
        not in {"complete", "terminal_failure_retained"}
    ):
        raise ValueError("selector selected action binding drifted")
    zero = (
        value["dp_model_call_count_after_pool"] == 0
        and value["latent_replacement_count_after_pool"] == 0
        and value["candidate_generation_count_after_pool"] == 0
    )
    return {
        "scores": scores.tolist(),
        "mask": mask.tolist(),
        "selected_index": expected_index,
        "selected_action_80x4": selected.tolist(),
        "executable": value["executable"],
        "terminal": value["terminal"],
        "zero_call_and_immutable": zero,
    }


def _numeric_keys() -> tuple[tuple[str, str, str], ...]:
    keys = []
    for endpoint in WITHIN_NUMERIC_IDS:
        keys.append(("sequential_within", MODES[0], endpoint))
        keys.append(("batch8_within", MODES[1], endpoint))
    keys.extend(
        ("cross_mode", MODE_BY_PHASE["cross_mode"], endpoint)
        for endpoint in CROSS_NUMERIC_IDS
    )
    return tuple(keys)


def _resolution_floor(endpoint_id: str) -> float:
    if endpoint_id.startswith("atom."):
        return 1e-8
    if "position_max_m" in endpoint_id:
        return 1e-4
    if "heading_max_rad" in endpoint_id:
        return 1e-5
    if "speed_max_mps" in endpoint_id:
        return 1e-4
    if endpoint_id.startswith("score."):
        return 1e-9
    if endpoint_id == "neighbor.relative_within_mode_inflation":
        return 1e-9
    raise ValueError(f"resolution floor undefined: {endpoint_id}")


def _hex_bytes(value: Any, label: str) -> bytes:
    if type(value) is not str:
        raise ValueError(f"{label} hex drifted")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{label} hex drifted") from error


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
