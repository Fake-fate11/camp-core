"""Separate-role literal review oracle for fair-pool adaptation contract v4.

This module intentionally does not import the v4 producer, its input-manifest
module, the fairness implementation, or any selector implementation.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    action_equivalent,
    bootstrap_upper_threshold,
    empirical_quantile_higher,
    sha256_json,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_review_v3 import (
    CROSS_NUMERIC_IDS,
    WITHIN_NUMERIC_IDS,
    _literal_hard_statuses,
    _literal_numeric_statuses,
    literal_validate_preflight_receipt_v3,
)


SCHEMA = "camp_dp_v25_fair_pool_adaptation_contract_v4"
PACKAGE_SCHEMA = "camp_dp_v25_fair_pool_adaptation_qualification_package_v4"
ANCHOR_SCHEMA = "camp_dp_v25_fair_pool_high_trust_anchor_v1"
ARTIFACT_SCHEMA = "camp_dp_v25_fair_pool_content_artifact_v1"
REVIEW_SCHEMA = (
    "camp_dp_v25_fair_pool_content_artifact_independent_review_v1"
)
EXPECTED_PAYLOAD_SHA256 = (
    "04cc1e685c61b6c1a5fe391b1fd1dbed4af07494a50e485b610389fca453cc6c"
)
EXPECTED_INHERITED_V3_PAYLOAD_SHA256 = (
    "38c7d9f3298a284c59828ab81b475ed998d9b295daae73a28654915bce95d31f"
)
CONTROL_TASK_ID = "019f92d8-c971-7b13-924e-873ae9f24c14"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
GENERATOR = "new_single_invocation_batched_k8_candidate_pool"
MODES = ("sequential_batch1_x8", "single_invocation_batch8")
PHASE_MODE = {
    "sequential_within": MODES[0],
    "batch8_within": MODES[1],
    "cross_mode": "matched_repeat_cross_mode",
}
WITHIN_PAIRS = tuple(
    (left, right)
    for left in range(5)
    for right in range(5)
    if left < right
)
CROSS_PAIRS = tuple((index, index) for index in range(5))
ARMS = ("static14d", "scene14d")
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
KINDS = {
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


def review_contract_literal_v4(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "status",
        "superseded_preacquisition_diagnostic",
        "inherited_v3_contract",
        "trust_anchor",
        "two_stage_authority",
        "sealed_artifact_schema",
        "preflight_provenance",
        "acquisition_receipt_schema",
        "threshold_freeze_schema",
        "validation_receipt_schema",
        "decision",
        "run_and_claim_boundary",
        "contract_payload_sha256",
    }:
        raise ValueError("reviewer v4 contract top-level schema drifted")
    payload = deepcopy(dict(value))
    supplied = payload.pop("contract_payload_sha256")
    if (
        value["schema_version"] != SCHEMA
        or supplied != sha256_json(payload)
        or supplied != EXPECTED_PAYLOAD_SHA256
    ):
        raise ValueError("reviewer v4 contract payload drifted")
    inherited = value["inherited_v3_contract"]
    inherited_payload = deepcopy(dict(inherited))
    inherited_supplied = inherited_payload.pop("contract_payload_sha256", None)
    if (
        inherited.get("schema_version")
        != "camp_dp_v25_fair_pool_adaptation_contract_v3"
        or inherited_supplied != sha256_json(inherited_payload)
        or inherited_supplied != EXPECTED_INHERITED_V3_PAYLOAD_SHA256
    ):
        raise ValueError("reviewer inherited v3 payload drifted")
    if value["trust_anchor"] != {
        "schema_version": ANCHOR_SCHEMA,
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
    }:
        raise ValueError("reviewer trust-anchor contract drifted")
    if value["two_stage_authority"]["sequence"] != _sequence():
        raise ValueError("reviewer two-stage sequence drifted")
    freeze = value["threshold_freeze_schema"]
    if (
        freeze["required_numeric_key_count"] != 73
        or freeze["required_numeric_keys"]
        != [list(key) for key in _numeric_keys()]
        or freeze["caller_threshold_or_self_hash_accepted"] is not False
        or freeze["calibration_state_count"] != 64
        or freeze["within_pair_receipts_per_state"] != 10
        or freeze["cross_pair_receipts_per_state"] != 5
    ):
        raise ValueError("reviewer threshold-freeze contract drifted")
    validation = value["validation_receipt_schema"]
    if (
        validation["candidate_tensor"]["shape"] != [8, 80, 4]
        or validation["candidate_tensor"]["dtype"] != "<f8"
        or validation[
            "naked_all_finite_mask_action_or_call_count_accepted"
        ]
        is not False
        or validation["hard_statuses_are_derived_from_receipts"] is not True
    ):
        raise ValueError("reviewer validation receipt contract drifted")
    boundary = value["run_and_claim_boundary"]
    zero = (
        "actual_input_manifest_materialization_count",
        "calibration_run_count",
        "repeat_model_run_count",
        "pool_run_count",
        "selector_run_count",
        "closed_loop_run_count",
        "fresh_run_count",
        "holdout_run_count",
        "training_run_count",
    )
    if (
        boundary["acquisition_authorized"] is not False
        or boundary["claim_authorized"] is not False
        or any(boundary[field] != 0 for field in zero)
    ):
        raise ValueError("reviewer run boundary drifted")
    return {
        "status": "passed_independent_literal_contract_review_v4",
        "payload_sha256": supplied,
        "numeric_key_count": 73,
        "artifact_root_count": 10,
        "external_trust_anchor_required": True,
        "threshold_and_hard_receipts_rebuilt": True,
        "acquisition_authorized": False,
    }


def literal_decide_qualification_v4(
    contract: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    trust_anchor: Mapping[str, Any],
    expected_trust_anchor_root_sha256: str,
) -> dict[str, Any]:
    review_contract_literal_v4(contract)
    anchor = _anchor(
        trust_anchor,
        expected=expected_trust_anchor_root_sha256,
        contract=contract,
    )
    artifacts = _package(package, contract=contract, anchor=anchor)
    authority = _authority(
        artifacts["acquisition_authority"]["payload"],
        contract=contract,
        anchor=anchor,
    )
    manifests = _preflight(
        artifacts["split_preflight"]["payload"],
        contract=contract,
        anchor=anchor,
        authority=authority,
    )
    calibration = _receipts(
        artifacts["calibration_receipts"]["payload"],
        contract=contract,
        anchor=anchor,
        manifests=manifests,
        split="development_calibration",
    )
    freeze = _freeze(
        artifacts["threshold_freeze"]["payload"],
        contract=contract,
        anchor=anchor,
        calibration=calibration,
    )
    validation = _receipts(
        artifacts["validation_receipts"]["payload"],
        contract=contract,
        anchor=anchor,
        manifests=manifests,
        split="independent_validation",
    )
    receipt = _v3_receipt(
        contract=contract,
        anchor=anchor,
        preflight=artifacts["split_preflight"],
        freeze=freeze,
        validation=validation,
        validation_payload=artifacts["validation_receipts"]["payload"],
    )
    inherited = contract["inherited_v3_contract"]
    statuses = _literal_numeric_statuses(
        inherited, receipt["numeric_evidence"]
    )
    statuses.update(_literal_hard_statuses(inherited, receipt))
    if "authority_failure" in set(statuses.values()):
        status, classification = "BLOCK", "authority_failure"
    elif "evidence_missing" in set(statuses.values()):
        status, classification = "BLOCK", "evidence_missing"
    else:
        sequential = all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase == "sequential_within"
        )
        batch8 = all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase == "batch8_within"
        )
        if not sequential or not batch8:
            status, classification = (
                "BLOCK",
                "within_mode_generator_instability",
            )
        elif not all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase in {"cross_mode", "global"}
        ):
            status, classification = "BLOCK", "cross_mode_functional_drift"
        else:
            status, classification = "PASS", "bounded_scope_no_trigger"
    decision = {
        "status": status,
        "classification": classification,
        "derived_within_mode_pass": {
            MODES[0]: all(
                value == "pass"
                for (phase, _mode, _endpoint), value in statuses.items()
                if phase == "sequential_within"
            ),
            MODES[1]: all(
                value == "pass"
                for (phase, _mode, _endpoint), value in statuses.items()
                if phase == "batch8_within"
            ),
        },
        "cross_mode_entered": all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase in {"sequential_within", "batch8_within"}
        ),
        "derived_result_count": len(statuses),
        "caller_supplied_status_or_within_boolean_used": False,
    }
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


def _anchor(
    value: Mapping[str, Any],
    *,
    expected: str,
    contract: Mapping[str, Any],
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
        raise ValueError("reviewer trust anchor schema drifted")
    payload = dict(value)
    root = payload.pop("trust_anchor_root_sha256")
    if root != sha256_json(payload) or root != _sha(expected, "trusted root"):
        raise ValueError("reviewer external trust anchor root drifted")
    if (
        value["schema_version"] != ANCHOR_SCHEMA
        or value["status"] != "trusted_by_versioned_High_control"
        or value["provider_task_id"] != CONTROL_TASK_ID
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["sequence"] != _sequence()
        or value["validation_started_after_threshold_freeze"] is not True
        or value["acquisition_authorized"] is not True
        or value["fresh_holdout_closed_loop_training_authorized"] is not False
    ):
        raise ValueError("reviewer trust anchor authority drifted")
    roots = value["artifact_roots"]
    if type(roots) is not dict or set(roots) != set(ARTIFACT_NAMES):
        raise ValueError("reviewer trust root keyset drifted")
    for field in (
        "high_decision_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "input_manifest_authority_root_sha256",
    ):
        _sha(value[field], field)
    for name in ARTIFACT_NAMES:
        _sha(roots[name], name)
    return dict(value)


def _package(
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
        raise ValueError("reviewer qualification package schema drifted")
    if (
        value["schema_version"] != PACKAGE_SCHEMA
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["trust_anchor_root_sha256"]
        != anchor["trust_anchor_root_sha256"]
    ):
        raise ValueError("reviewer qualification package authority drifted")
    artifacts = value["artifacts"]
    if type(artifacts) is not dict or set(artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("reviewer qualification artifact keyset drifted")
    checked = {
        name: _artifact(
            artifacts[name],
            kind=KINDS[name],
            root=anchor["artifact_roots"][name],
        )
        for name in ARTIFACT_NAMES
    }
    for source, review in (
        ("acquisition_authority", "acquisition_authority_review"),
        ("split_preflight", "split_preflight_review"),
        ("calibration_receipts", "calibration_receipts_review"),
        ("threshold_freeze", "threshold_freeze_review"),
        ("validation_receipts", "validation_receipts_review"),
    ):
        _review(checked[review]["payload"], source=checked[source])
    return checked


def _artifact(
    value: Mapping[str, Any],
    *,
    kind: str,
    root: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "kind",
        "payload",
        "payload_sha256",
        "root_sha256",
    }:
        raise ValueError("reviewer content artifact schema drifted")
    payload = dict(value)
    supplied = payload.pop("root_sha256")
    if (
        value["schema_version"] != ARTIFACT_SCHEMA
        or value["kind"] != kind
        or type(value["payload"]) is not dict
        or value["payload_sha256"] != sha256_json(value["payload"])
        or supplied != sha256_json(payload)
        or supplied != root
    ):
        raise ValueError("reviewer content artifact root drifted")
    return deepcopy(dict(value))


def _review(value: Mapping[str, Any], *, source: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": REVIEW_SCHEMA,
        "status": "passed_independent_literal_reconstruction",
        "source_kind": source["kind"],
        "source_root_sha256": source["root_sha256"],
        "source_payload_sha256": source["payload_sha256"],
        "reviewer_role_separate": True,
        "producer_module_imported": False,
    }
    if value != expected:
        raise ValueError("reviewer independent review binding drifted")


def _authority(
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
        raise ValueError("reviewer authority schema drifted")
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
        raise ValueError("reviewer authority drifted")
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
        raise ValueError("reviewer input authority drifted")
    return dict(value)


def _preflight(
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
        raise ValueError("reviewer preflight payload schema drifted")
    tensors = _tensor_preimages(value["actual_input_tensors"])
    inherited = contract["inherited_v3_contract"]
    checked = literal_validate_preflight_receipt_v3(
        value["receipt"],
        expected_acquisition_authority_root_sha256=anchor[
            "input_manifest_authority_root_sha256"
        ],
        expected_contract_root_sha256=anchor["contract_root_sha256"],
        expected_contract_review_root_sha256=anchor[
            "contract_review_root_sha256"
        ],
        calibration_specs=inherited["state_specifications"][
            "development_calibration"
        ],
        validation_specs=inherited["state_specifications"][
            "independent_validation"
        ],
        route_asset_bytes=_hex(value["route_asset_bytes_hex"]),
        map_asset_bytes=_hex(value["map_asset_bytes_hex"]),
        prepared_runtime_cases_bytes=_hex(
            value["prepared_runtime_cases_bytes_hex"]
        ),
        actual_input_tensors_by_state_id=tensors,
    )
    if (
        checked["acquisition_authority"]
        != authority["input_manifest_acquisition_authority"]
    ):
        raise ValueError("reviewer preflight authority mismatch")
    return {
        row["state_spec_id"]: row
        for row in (
            checked["calibration_manifests"]
            + checked["validation_manifests"]
        )
    }


def _tensor_preimages(value: Any) -> dict[str, dict[str, np.ndarray]]:
    if type(value) is not list or len(value) != 128:
        raise ValueError("reviewer tensor preimage denominator drifted")
    result = {}
    for state in value:
        if type(state) is not dict or set(state) != {
            "state_spec_id",
            "tensors",
        }:
            raise ValueError("reviewer tensor state schema drifted")
        state_id = state["state_spec_id"]
        if state_id in result or type(state["tensors"]) is not list:
            raise ValueError("reviewer tensor state duplicate")
        named = {}
        for row in state["tensors"]:
            if type(row) is not dict or set(row) != {
                "name",
                "dtype",
                "shape",
                "data_hex",
            }:
                raise ValueError("reviewer tensor schema drifted")
            dtype = np.dtype(row["dtype"])
            shape = tuple(row["shape"])
            array = np.frombuffer(_hex(row["data_hex"]), dtype=dtype).copy()
            if (
                dtype.kind not in "biuf"
                or not shape
                or array.size != math.prod(shape)
                or row["name"] in named
            ):
                raise ValueError("reviewer tensor preimage drifted")
            named[row["name"]] = array.reshape(shape)
        result[state_id] = named
    return result


def _receipts(
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
        raise ValueError("reviewer receipt payload schema drifted")
    if (
        value["schema_version"]
        != "camp_dp_v25_fair_pool_mode_repeat_receipts_v1"
        or value["split"] != split
        or value["authority_root_sha256"]
        != anchor["artifact_roots"]["acquisition_authority"]
        or value["preflight_root_sha256"]
        != anchor["artifact_roots"]["split_preflight"]
    ):
        raise ValueError("reviewer receipt authority drifted")
    if split == "development_calibration":
        if (
            value["threshold_freeze_root_sha256"] is not None
            or value["threshold_freeze_review_root_sha256"] is not None
            or value["hard_state_receipts"] != []
        ):
            raise ValueError("reviewer calibration phase drifted")
    elif (
        value["threshold_freeze_root_sha256"]
        != anchor["artifact_roots"]["threshold_freeze"]
        or value["threshold_freeze_review_root_sha256"]
        != anchor["artifact_roots"]["threshold_freeze_review"]
    ):
        raise ValueError("reviewer validation threshold binding drifted")
    specs = contract["inherited_v3_contract"]["state_specifications"][split]
    state_ids = [row["state_spec_id"] for row in specs]
    runs = _runs(
        value["run_receipts"],
        state_ids=state_ids,
        manifests={state_id: manifests[state_id] for state_id in state_ids},
    )
    pairs, statistics, roots = _pairs(
        value["pair_receipts"],
        state_ids=state_ids,
        runs=runs,
    )
    return {
        "state_ids": state_ids,
        "runs": runs,
        "pairs": pairs,
        "statistics": statistics,
        "pair_roots": roots,
        "hard": value["hard_state_receipts"],
    }


def _runs(
    value: Any,
    *,
    state_ids: Sequence[str],
    manifests: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
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
    if type(value) is not list or len(value) != 640:
        raise ValueError("reviewer run denominator drifted")
    result = {}
    for row in value:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("reviewer run schema drifted")
        payload = dict(row)
        root = payload.pop("receipt_sha256")
        key = (row["mode"], row["state_spec_id"], row["repeat_index"])
        manifest = manifests.get(row["state_spec_id"])
        expected_calls = 8 if row["mode"] == MODES[0] else 1
        shas = row["candidate_row_sha256"]
        if (
            root != sha256_json(payload)
            or row["mode"] not in MODES
            or row["repeat_index"] not in range(5)
            or key in result
            or manifest is None
            or row["input_manifest_sha256"] != manifest["manifest_sha256"]
            or row["actual_state_sha256"] != manifest["actual_state_sha256"]
            or row["actual_latent_manifest_sha256"]
            != manifest["actual_latent_tensor_manifest"]["manifest_sha256"]
            or row["fixed_dp_head"] != FIXED_DP_HEAD
            or row["checkpoint_sha256"]
            != "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
            or row["model_source_sha256"]
            != "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
            or type(row["forward_invocation_id"]) is not str
            or not row["forward_invocation_id"]
            or row["model_call_count"] != expected_calls
            or type(row["pool_id"]) is not str
            or not row["pool_id"]
            or _sha(row["candidate_tensor_sha256"], "tensor")
            != row["candidate_tensor_sha256"]
            or type(shas) is not list
            or len(shas) != 8
            or len(set(shas)) != 8
            or row["all_finite"] is not True
        ):
            raise ValueError("reviewer run authority drifted")
        for digest in shas:
            _sha(digest, "row")
        result[key] = dict(row)
    expected = {
        (mode, state_id, repeat)
        for mode in MODES
        for state_id in state_ids
        for repeat in range(5)
    }
    if set(result) != expected:
        raise ValueError("reviewer run keyset drifted")
    return result


def _pairs(
    value: Any,
    *,
    state_ids: Sequence[str],
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
) -> tuple[dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
    if type(value) is not list or len(value) != 1600:
        raise ValueError("reviewer pair denominator drifted")
    values = {
        key: {state_id: [] for state_id in state_ids}
        for key in _numeric_keys()
    }
    roots = deepcopy(values)
    result = {}
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
            raise ValueError("reviewer pair schema drifted")
        payload = dict(row)
        root = payload.pop("receipt_sha256")
        phase = row["phase"]
        if phase in {"sequential_within", "batch8_within"}:
            mode = PHASE_MODE[phase]
            topology = WITHIN_PAIRS
            endpoints = WITHIN_NUMERIC_IDS
            left_mode = right_mode = mode
        elif phase == "cross_mode":
            mode = PHASE_MODE[phase]
            topology = CROSS_PAIRS
            endpoints = CROSS_NUMERIC_IDS
            left_mode, right_mode = MODES
        else:
            raise ValueError("reviewer pair phase drifted")
        pair_index = row["pair_index"]
        identity = (phase, mode, row["state_spec_id"], pair_index)
        if (
            root != sha256_json(payload)
            or row["mode"] != mode
            or row["state_spec_id"] not in state_ids
            or type(pair_index) is not int
            or not 0 <= pair_index < len(topology)
            or (
                row["left_repeat_index"],
                row["right_repeat_index"],
            )
            != topology[pair_index]
            or identity in result
        ):
            raise ValueError("reviewer pair topology drifted")
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
            or type(row["endpoint_values"]) is not dict
            or set(row["endpoint_values"]) != set(endpoints)
        ):
            raise ValueError("reviewer pair binding drifted")
        for endpoint in endpoints:
            number = float(row["endpoint_values"][endpoint])
            if not math.isfinite(number) or number < 0:
                raise ValueError("reviewer pair numeric drifted")
            key = (phase, mode, endpoint)
            values[key][row["state_spec_id"]].append(number)
            roots[key][row["state_spec_id"]].append(root)
        result[identity] = dict(row)
    statistics = {
        key: [
            empirical_quantile_higher(values[key][state_id], 0.99)
            for state_id in state_ids
        ]
        for key in _numeric_keys()
    }
    root_rows = {
        key: [roots[key][state_id] for state_id in state_ids]
        for key in _numeric_keys()
    }
    if len(result) != 1600:
        raise ValueError("reviewer pair keyset drifted")
    return result, statistics, root_rows


def _freeze(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    calibration: Mapping[str, Any],
) -> dict[Any, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "contract_root_sha256",
        "acquisition_authority_root_sha256",
        "calibration_receipts_root_sha256",
        "calibration_receipts_review_root_sha256",
        "validation_model_pool_selector_call_count_before_seal",
        "records",
    }:
        raise ValueError("reviewer freeze schema drifted")
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
        raise ValueError("reviewer freeze authority drifted")
    rows = value["records"]
    if type(rows) is not list or len(rows) != 73:
        raise ValueError("reviewer freeze denominator drifted")
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
            raise ValueError("reviewer freeze record schema drifted")
        key = (row["phase"], row["mode"], row["endpoint_id"])
        if key not in _numeric_keys() or key in result:
            raise ValueError("reviewer freeze key drifted")
        floor = _floor(key[2])
        stats = calibration["statistics"][key]
        roots = calibration["pair_roots"][key]
        upper = bootstrap_upper_threshold(stats, resolution_floor=floor)
        preimage = {
            "algorithm": contract["threshold_freeze_schema"]["bootstrap"],
            "phase": key[0],
            "mode": key[1],
            "endpoint_id": key[2],
            "calibration_state_ids": calibration["state_ids"],
            "state_pair_receipt_sha256": roots,
            "state_statistics": stats,
            "resolution_floor": floor,
        }
        if (
            row["calibration_state_ids"] != calibration["state_ids"]
            or row["state_pair_receipt_sha256"] != roots
            or row["state_statistics"] != stats
            or row["bootstrap_preimage_sha256"] != sha256_json(preimage)
            or float(row["resolution_floor"]) != floor
            or float(row["bootstrap_result"]) != upper
            or float(row["threshold"]) != upper
        ):
            raise ValueError("reviewer freeze recomputation drifted")
        result[key] = dict(row)
    if set(result) != set(_numeric_keys()):
        raise ValueError("reviewer freeze endpoint omitted")
    return result


def _v3_receipt(
    *,
    contract: Mapping[str, Any],
    anchor: Mapping[str, Any],
    preflight: Mapping[str, Any],
    freeze: Mapping[Any, Any],
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
                    {"state_spec_id": state_id, "value": observed}
                    for state_id, observed in zip(
                        validation["state_ids"],
                        validation["statistics"][key],
                    )
                ],
                "threshold": threshold,
                "threshold_authority": authority,
            }
        )
    hard = _hard(
        contract=contract,
        validation=validation,
        rows=validation_payload["hard_state_receipts"],
    )
    hard["split_preflight"] = {
        "status": "passed_before_first_model_pool_selector_call",
        "receipt_sha256": preflight["root_sha256"],
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


def _hard(
    *,
    contract: Mapping[str, Any],
    validation: Mapping[str, Any],
    rows: Any,
) -> dict[str, Any]:
    if type(rows) is not list or len(rows) != 64:
        raise ValueError("reviewer hard denominator drifted")
    k8 = {mode: [] for mode in MODES}
    pool_rows = []
    masks = {arm: [] for arm in ARMS}
    actions = {arm: [] for arm in ARMS}
    fields = {
        "state_spec_id",
        "candidate_pools",
        "selectors",
        "receipt_sha256",
    }
    for state_id, row in zip(validation["state_ids"], rows):
        if type(row) is not dict or set(row) != fields:
            raise ValueError("reviewer hard state schema drifted")
        payload = dict(row)
        root = payload.pop("receipt_sha256")
        if root != sha256_json(payload) or row["state_spec_id"] != state_id:
            raise ValueError("reviewer hard state root drifted")
        pools = {}
        for mode in MODES:
            pools[mode] = _pool(
                row["candidate_pools"][mode],
                run=validation["runs"][(mode, state_id, 0)],
            )
            k8[mode].append(
                {
                    "state_spec_id": state_id,
                    "all_finite": True,
                    "row_sha256": pools[mode]["row_sha256"],
                }
            )
        selectors = {}
        for arm in ARMS:
            selectors[arm] = {
                mode: _selector(
                    row["selectors"][arm][mode],
                    state_id=state_id,
                    arm=arm,
                    mode=mode,
                    pool=pools[mode],
                )
                for mode in MODES
            }
            left, right = selectors[arm][MODES[0]], selectors[arm][MODES[1]]
            masks[arm].append(
                {
                    "state_spec_id": state_id,
                    "sequential_mask": left["mask"],
                    "batch8_mask": right["mask"],
                }
            )
            actions[arm].append(
                {
                    "state_spec_id": state_id,
                    "sequential_selected_index": left["selected_index"],
                    "batch8_selected_index": right["selected_index"],
                    "sequential_action_80x4": left["action"],
                    "batch8_action_80x4": right["action"],
                    "sequential_executable": left["executable"],
                    "batch8_executable": right["executable"],
                    "sequential_terminal": left["terminal"],
                    "batch8_terminal": right["terminal"],
                }
            )
        if not all(
            selectors[arm][mode]["zero"]
            for arm in ARMS
            for mode in MODES
        ):
            raise ValueError("reviewer post-pool call drifted")
        pool_rows.append(
            {
                "state_spec_id": state_id,
                "pre_tensor_sha256": pools[MODES[0]]["tensor_sha256"],
                "post_tensor_sha256": pools[MODES[0]]["tensor_sha256"],
                "dp_model_call_count_after_pool": 0,
                "latent_replacement_count_after_pool": 0,
                "candidate_generation_count_after_pool": 0,
            }
        )
    inherited = contract["inherited_v3_contract"]
    fp = {
        "fixed_dp_head": FIXED_DP_HEAD,
        "generator": GENERATOR,
        "candidate_k": 8,
        "checkpoint_sha256": inherited["model_fingerprint_authority"][
            "checkpoint_sha256"
        ],
        "model_source_sha256": inherited["model_fingerprint_authority"][
            "model_source_sha256"
        ],
        "decoder_source_sha256": inherited["model_fingerprint_authority"][
            "decoder_source_sha256"
        ],
        "encoder_source_sha256": inherited["model_fingerprint_authority"][
            "encoder_source_sha256"
        ],
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
            "expected": fp,
            "observed_by_mode": {mode: deepcopy(fp) for mode in MODES},
        },
        "k8": k8,
        "pool": pool_rows,
        "masks": masks,
        "actions": actions,
    }


def _pool(value: Mapping[str, Any], *, run: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
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
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("reviewer pool schema drifted")
    array = np.asarray(value["candidate_tensor"], dtype=np.float64)
    canonical = np.ascontiguousarray(array.astype("<f8", copy=False))
    tensor_sha = hashlib.sha256(canonical.tobytes(order="C")).hexdigest()
    row_sha = [
        hashlib.sha256(
            np.ascontiguousarray(canonical[index]).tobytes(order="C")
        ).hexdigest()
        for index in range(8)
    ]
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
        or value["tensor_sha256"] != tensor_sha
        or value["row_sha256"] != row_sha
        or len(set(row_sha)) != 8
        or run["candidate_tensor_sha256"] != tensor_sha
        or run["candidate_row_sha256"] != row_sha
    ):
        raise ValueError("reviewer candidate pool binding drifted")
    return {
        "array": canonical,
        "tensor_sha256": tensor_sha,
        "row_sha256": row_sha,
        "pool_id": value["pool_id"],
    }


def _selector(
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
        raise ValueError("reviewer selector schema drifted")
    payload = dict(value)
    root = payload.pop("receipt_sha256")
    scores = np.asarray(value["scores"], dtype=np.float64)
    mask = np.asarray(value["mask"])
    if (
        root != sha256_json(payload)
        or value["state_spec_id"] != state_id
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
        raise ValueError("reviewer selector binding drifted")
    eligible = np.flatnonzero(mask)
    best = float(np.min(scores[eligible]))
    index = int(eligible[scores[eligible] == best][0])
    action = np.asarray(value["selected_action_80x4"], dtype=np.float64)
    if (
        value["selected_index"] != index
        or action.shape != (80, 4)
        or not np.array_equal(action, pool["array"][index])
        or value["executable"]
        not in {"executable", "non_executable_retained"}
        or value["terminal"]
        not in {"complete", "terminal_failure_retained"}
    ):
        raise ValueError("reviewer selector action drifted")
    return {
        "mask": mask.tolist(),
        "selected_index": index,
        "action": action.tolist(),
        "executable": value["executable"],
        "terminal": value["terminal"],
        "zero": (
            value["dp_model_call_count_after_pool"] == 0
            and value["latent_replacement_count_after_pool"] == 0
            and value["candidate_generation_count_after_pool"] == 0
        ),
    }


def _numeric_keys() -> tuple[tuple[str, str, str], ...]:
    keys = []
    for endpoint in WITHIN_NUMERIC_IDS:
        keys.append(("sequential_within", MODES[0], endpoint))
        keys.append(("batch8_within", MODES[1], endpoint))
    keys.extend(
        ("cross_mode", PHASE_MODE["cross_mode"], endpoint)
        for endpoint in CROSS_NUMERIC_IDS
    )
    return tuple(keys)


def _floor(endpoint: str) -> float:
    if endpoint.startswith("atom."):
        return 1e-8
    if "position_max_m" in endpoint:
        return 1e-4
    if "heading_max_rad" in endpoint:
        return 1e-5
    if "speed_max_mps" in endpoint:
        return 1e-4
    if endpoint.startswith("score."):
        return 1e-9
    if endpoint == "neighbor.relative_within_mode_inflation":
        return 1e-9
    raise ValueError("reviewer resolution floor undefined")


def _sequence() -> list[str]:
    return [
        "high_acquisition_authority_independently_reviewed",
        "input_only_preflight_independently_reviewed",
        "development_calibration_receipts_independently_reviewed",
        "threshold_freeze_independently_reviewed_before_validation",
        "independent_validation_receipts_independently_reviewed",
        "qualification_consumer_decision",
    ]


def _hex(value: Any) -> bytes:
    if type(value) is not str:
        raise ValueError("reviewer hex preimage drifted")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("reviewer hex preimage drifted") from error


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
