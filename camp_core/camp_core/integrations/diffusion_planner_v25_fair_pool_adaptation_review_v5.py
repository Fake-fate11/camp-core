"""Separate-role raw-semantic review oracle for fair-pool contract v5.

This module intentionally does not import the v5 producer, any selector,
fairness, threshold, or metric implementation.  Array reconstruction, endpoint
formulas, state quantiles, and the v5 authority topology are local literals.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence
import zlib

import numpy as np

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v4 as v4_review,
)


SCHEMA = "camp_dp_v25_fair_pool_adaptation_contract_v5"
PACKAGE_SCHEMA = "camp_dp_v25_fair_pool_adaptation_qualification_package_v5"
ANCHOR_SCHEMA = "camp_dp_v25_fair_pool_high_trust_anchor_v2"
ARTIFACT_SCHEMA = "camp_dp_v25_fair_pool_content_artifact_v1"
REVIEW_SCHEMA = (
    "camp_dp_v25_fair_pool_content_artifact_independent_review_v1"
)
SEMANTIC_SCHEMA = (
    "camp_dp_v25_fair_pool_mode_repeat_raw_semantic_receipts_v1"
)
RUN_SCHEMA = "camp_dp_v25_fair_pool_raw_semantic_run_v1"
BLOB_SCHEMA = "camp_dp_v25_fair_pool_zlib_array_blob_v1"
EXPECTED_PAYLOAD_SHA256 = (
    "2188c208ef144e73e3e9b2596906842bc13709781b8758bb2047fa9fe944f5a6"
)
EXPECTED_V4_PAYLOAD_SHA256 = (
    "04cc1e685c61b6c1a5fe391b1fd1dbed4af07494a50e485b610389fca453cc6c"
)
CONTROL_TASK_ID = "019f92d8-c971-7b13-924e-873ae9f24c14"
MODES = ("sequential_batch1_x8", "single_invocation_batch8")
ARMS = ("static14d", "scene14d")
PHASE_MODE = {
    "sequential_within": MODES[0],
    "batch8_within": MODES[1],
    "cross_mode": "matched_repeat_cross_mode",
}
WITHIN_PAIRS = tuple(
    (left, right) for left in range(5) for right in range(5) if left < right
)
CROSS_PAIRS = tuple((index, index) for index in range(5))
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
WITHIN_IDS = (
    *(
        f"atom.normalized_delta.{index:02d}.{name}"
        for index, name in enumerate(ATOM_NAMES)
    ),
    "trajectory.ego.position_max_m",
    "trajectory.ego.heading_max_rad",
    "trajectory.ego.speed_max_mps",
    "trajectory.neighbor.position_max_m",
    "trajectory.neighbor.heading_max_rad",
    "trajectory.neighbor.speed_max_mps",
    "score.static14d.abs_delta",
    "score.scene14d.abs_delta",
)
CROSS_ONLY_IDS = (
    "score.static14d.within_mode_normalized_delta",
    "score.static14d.margin_ratio",
    "score.static14d.rank_error",
    "score.scene14d.within_mode_normalized_delta",
    "score.scene14d.margin_ratio",
    "score.scene14d.rank_error",
    "neighbor.relative_within_mode_inflation",
)
CROSS_IDS = (*WITHIN_IDS, *CROSS_ONLY_IDS)
NEIGHBOR_IDS = (
    "trajectory.neighbor.position_max_m",
    "trajectory.neighbor.heading_max_rad",
    "trajectory.neighbor.speed_max_mps",
)
SEMANTIC_NAMES = (
    "calibration_semantic_receipts",
    "calibration_semantic_receipts_review",
    "validation_semantic_receipts",
    "validation_semantic_receipts_review",
)
SEMANTIC_KINDS = {
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


def literal_validate_contract_v5(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("v5 review contract must be object")
    payload = dict(value)
    supplied = payload.pop("contract_payload_sha256", None)
    if (
        value.get("schema_version") != SCHEMA
        or supplied != EXPECTED_PAYLOAD_SHA256
        or supplied != _json_sha(payload)
        or value.get("status")
        != "frozen_raw_semantic_provenance_design_only_acquisition_unauthorized"
    ):
        raise ValueError("v5 review contract payload drifted")
    inherited = value.get("inherited_v4_contract")
    if (
        type(inherited) is not dict
        or inherited.get("contract_payload_sha256")
        != EXPECTED_V4_PAYLOAD_SHA256
    ):
        raise ValueError("v5 inherited v4 contract drifted")
    raw = value.get("raw_semantic_run_receipt")
    endpoint = value.get("endpoint_derivation")
    review = value.get("independent_review")
    if (
        raw.get("split_mode_repeat_state_denominator")
        != {
            "development_calibration": 640,
            "independent_validation": 640,
        }
        or raw.get("typed_preimages")
        != {
            "candidate_ego_trajectory": [8, 80, 4],
            "candidate_neighbor_trajectory": "[8,A,80,4]_A_ge_1",
            "atom_vectors": [8, 14],
            "selector_scores_per_arm": [8],
            "selector_mask_per_arm": [8],
            "selected_action_per_arm": [80, 4],
        }
        or endpoint.get("within_endpoint_ids") != list(WITHIN_IDS)
        or endpoint.get("cross_endpoint_ids") != list(CROSS_IDS)
        or endpoint.get("phase_key_count") != 73
        or endpoint.get("authoritative_input")
        != "typed_raw_semantic_run_receipts"
        or endpoint.get("endpoint_values_role") != "derived_cache_only"
        or endpoint.get("derived_cache_equality")
        != "exact_float64_hex_equality"
        or review.get("producer_v5_module_imported") is not False
        or review.get("producer_metric_threshold_decision_oracle_imported")
        is not False
        or value.get("decision", {}).get("acquisition_authorized") is not False
    ):
        raise ValueError("v5 review semantic literal drifted")
    expected_formula_keys = set(WITHIN_IDS).union(CROSS_ONLY_IDS)
    if set(endpoint.get("formula_registry", {})) != expected_formula_keys:
        raise ValueError("v5 review formula registry keyset drifted")
    return deepcopy(dict(value))


def review_contract_literal_v5(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    checked = literal_validate_contract_v5(value)
    return {
        "schema_version": checked["schema_version"],
        "contract_payload_sha256": checked["contract_payload_sha256"],
        "inherited_v4_payload_sha256": checked["inherited_v4_contract"][
            "contract_payload_sha256"
        ],
        "raw_semantic_run_count_per_split": 640,
        "raw_semantic_total_run_count": 1280,
        "numeric_phase_key_count": 73,
        "endpoint_values_are_derived_cache_only": True,
        "all_five_repeat_preimages_required": True,
        "reviewer_local_array_endpoint_threshold_oracle": True,
        "acquisition_authorized": False,
        "claim_authorized": False,
    }


def literal_decide_qualification_v5(
    contract: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    trust_anchor: Mapping[str, Any],
    expected_trust_anchor_root_sha256: str,
) -> dict[str, Any]:
    frozen = literal_validate_contract_v5(contract)
    anchor = _anchor(
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
        raise ValueError("v5 review package exact schema drifted")
    if (
        package["schema_version"] != PACKAGE_SCHEMA
        or package["contract_payload_sha256"]
        != frozen["contract_payload_sha256"]
        or package["trust_anchor_root_sha256"]
        != anchor["trust_anchor_root_sha256"]
    ):
        raise ValueError("v5 review package authority drifted")
    v4_anchor = package["v4_trust_anchor"]
    if (
        type(v4_anchor) is not dict
        or v4_anchor.get("trust_anchor_root_sha256")
        != anchor["v4_trust_anchor_root_sha256"]
    ):
        raise ValueError("v5 review nested v4 anchor drifted")
    semantic = _semantic_artifacts(
        package["semantic_artifacts"], anchor=anchor
    )
    v4_package = package["v4_package"]
    if type(v4_package) is not dict or type(
        v4_package.get("artifacts")
    ) is not dict:
        raise ValueError("v5 review nested v4 package drifted")
    artifacts = v4_package["artifacts"]
    calibration = _semantic_payload(
        semantic["calibration_semantic_receipts"]["payload"],
        split="development_calibration",
        expected_v4_root=artifacts["calibration_receipts"]["root_sha256"],
        v4_payload=artifacts["calibration_receipts"]["payload"],
        selector_source_sha=anchor["selector_source_sha256"],
    )
    validation = _semantic_payload(
        semantic["validation_semantic_receipts"]["payload"],
        split="independent_validation",
        expected_v4_root=artifacts["validation_receipts"]["root_sha256"],
        v4_payload=artifacts["validation_receipts"]["payload"],
        selector_source_sha=anchor["selector_source_sha256"],
    )
    thresholds = _within_thresholds(
        calibration,
        artifacts["calibration_receipts"]["payload"]["pair_receipts"],
        artifacts["threshold_freeze"]["payload"],
    )
    _full_cache(
        calibration,
        artifacts["calibration_receipts"]["payload"]["pair_receipts"],
        thresholds,
    )
    _full_cache(
        validation,
        artifacts["validation_receipts"]["payload"]["pair_receipts"],
        thresholds,
    )
    _repeat0(
        validation,
        artifacts["validation_receipts"]["payload"]["hard_state_receipts"],
    )
    decision = v4_review.literal_decide_qualification_v4(
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


def _anchor(
    value: Any, *, contract: Mapping[str, Any], expected_root: str
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
        raise ValueError("v5 review anchor exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("trust_anchor_root_sha256")
    if (
        supplied != _json_sha(payload)
        or supplied != _sha(expected_root)
        or value["schema_version"] != ANCHOR_SCHEMA
        or value["status"] != "trusted_by_versioned_High_control"
        or value["provider_task_id"] != CONTROL_TASK_ID
        or value["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
        or value["acquisition_authorized"] is not True
        or value["fresh_holdout_closed_loop_training_authorized"] is not False
        or type(value["semantic_artifact_roots"]) is not dict
        or set(value["semantic_artifact_roots"]) != set(SEMANTIC_NAMES)
    ):
        raise ValueError("v5 review external anchor drifted")
    for field in (
        "high_decision_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "v4_trust_anchor_root_sha256",
        "selector_source_sha256",
    ):
        _sha(value[field])
    for root in value["semantic_artifact_roots"].values():
        _sha(root)
    return deepcopy(dict(value))


def _semantic_artifacts(
    value: Any, *, anchor: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != set(SEMANTIC_NAMES):
        raise ValueError("v5 review semantic artifact keyset drifted")
    result = {}
    for name in SEMANTIC_NAMES:
        checked = _artifact(value[name], SEMANTIC_KINDS[name])
        if checked["root_sha256"] != anchor["semantic_artifact_roots"][name]:
            raise ValueError("v5 review semantic root drifted")
        result[name] = checked
    for source, review in (
        (
            "calibration_semantic_receipts",
            "calibration_semantic_receipts_review",
        ),
        (
            "validation_semantic_receipts",
            "validation_semantic_receipts_review",
        ),
    ):
        source_value = result[source]
        review_value = result[review]["payload"]
        if (
            type(review_value) is not dict
            or review_value.get("schema_version") != REVIEW_SCHEMA
            or review_value.get("status")
            != "passed_independent_literal_reconstruction"
            or review_value.get("source_root_sha256")
            != source_value["root_sha256"]
            or review_value.get("source_payload_sha256")
            != source_value["payload_sha256"]
            or review_value.get("reviewer_role_separate") is not True
            or review_value.get("producer_module_imported") is not False
        ):
            raise ValueError("v5 review semantic review binding drifted")
    return result


def _artifact(value: Any, kind: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "kind",
        "payload",
        "payload_sha256",
        "root_sha256",
    }:
        raise ValueError("v5 review artifact exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("root_sha256")
    if (
        value["schema_version"] != ARTIFACT_SCHEMA
        or value["kind"] != kind
        or type(value["payload"]) is not dict
        or value["payload_sha256"] != _json_sha(value["payload"])
        or supplied != _json_sha(payload)
    ):
        raise ValueError("v5 review artifact root drifted")
    return deepcopy(dict(value))


def _semantic_payload(
    value: Any,
    *,
    split: str,
    expected_v4_root: str,
    v4_payload: Mapping[str, Any],
    selector_source_sha: str,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "split",
        "v4_receipts_root_sha256",
        "run_count",
        "run_semantics",
    }:
        raise ValueError("v5 review semantic payload schema drifted")
    if (
        value["schema_version"] != SEMANTIC_SCHEMA
        or value["split"] != split
        or value["v4_receipts_root_sha256"] != expected_v4_root
        or value["run_count"] != 640
        or type(value["run_semantics"]) is not list
        or len(value["run_semantics"]) != 640
    ):
        raise ValueError("v5 review semantic denominator drifted")
    v4_runs = {
        (row["mode"], row["state_spec_id"], row["repeat_index"]): row
        for row in v4_payload["run_receipts"]
    }
    result = {}
    for row in value["run_semantics"]:
        checked = _run(
            row, v4_runs=v4_runs, selector_source_sha=selector_source_sha
        )
        key = (
            checked["mode"],
            checked["state_spec_id"],
            checked["repeat_index"],
        )
        if key in result:
            raise ValueError("v5 review semantic run duplicate")
        result[key] = checked
    if set(result) != set(v4_runs):
        raise ValueError("v5 review semantic run keyset drifted")
    return result


def _run(
    value: Any,
    *,
    v4_runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    selector_source_sha: str,
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
        raise ValueError("v5 review semantic run schema drifted")
    payload = dict(value)
    supplied = payload.pop("semantic_receipt_sha256")
    if supplied != _json_sha(payload) or value["schema_version"] != RUN_SCHEMA:
        raise ValueError("v5 review semantic run root drifted")
    key = (value["mode"], value["state_spec_id"], value["repeat_index"])
    if key not in v4_runs:
        raise ValueError("v5 review semantic run identity drifted")
    old = v4_runs[key]
    if value["v4_run_receipt_sha256"] != old["receipt_sha256"]:
        raise ValueError("v5 review v4 run root drifted")
    candidate = _blob(value["candidate_ego_trajectory"], (8, 80, 4))
    neighbor = _blob(value["candidate_neighbor_trajectory"], None)
    atoms = _blob(value["atom_vectors"], (8, 14))
    actors = value["neighbor_actor_fingerprints"]
    if (
        neighbor.ndim != 4
        or neighbor.shape[0] != 8
        or neighbor.shape[1] < 1
        or neighbor.shape[2:] != (80, 4)
        or type(actors) is not list
        or len(actors) != neighbor.shape[1]
        or actors != sorted(actors)
        or len(set(actors)) != len(actors)
    ):
        raise ValueError("v5 review neighbor roster drifted")
    for actor in actors:
        _sha(actor)
    candidate_sha, row_sha = _tensor_hash(candidate)
    neighbor_sha = hashlib.sha256(
        np.ascontiguousarray(neighbor).tobytes(order="C")
    ).hexdigest()
    atom_sha = hashlib.sha256(
        np.ascontiguousarray(atoms).tobytes(order="C")
    ).hexdigest()
    forward = value["forward_binding"]
    forward_fields = {
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
    }
    if type(forward) is not dict or set(forward) != forward_fields:
        raise ValueError("v5 review forward schema drifted")
    preimage_keys = (
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
    forward_sha = _json_sha({name: forward[name] for name in preimage_keys})
    pool_sha = _json_sha(
        {
            "forward_binding_sha256": forward_sha,
            "candidate_tensor_sha256": candidate_sha,
        }
    )
    if (
        forward["state_spec_id"] != value["state_spec_id"]
        or forward["mode"] != value["mode"]
        or forward["repeat_index"] != value["repeat_index"]
        or forward["input_manifest_sha256"] != old["input_manifest_sha256"]
        or forward["actual_state_sha256"] != old["actual_state_sha256"]
        or forward["actual_latent_manifest_sha256"]
        != old["actual_latent_manifest_sha256"]
        or forward["fixed_dp_head"] != old["fixed_dp_head"]
        or forward["checkpoint_sha256"] != old["checkpoint_sha256"]
        or forward["model_source_sha256"] != old["model_source_sha256"]
        or forward["selector_source_sha256"] != selector_source_sha
        or forward["model_call_count"] != old["model_call_count"]
        or forward["candidate_tensor_sha256"] != candidate_sha
        or forward["candidate_row_sha256"] != row_sha
        or forward["neighbor_tensor_sha256"] != neighbor_sha
        or forward["atom_tensor_sha256"] != atom_sha
        or forward["forward_binding_sha256"] != forward_sha
        or forward["forward_invocation_id"] != f"forward:{forward_sha}"
        or forward["pool_binding_sha256"] != pool_sha
        or forward["pool_id"] != f"pool:{pool_sha}"
        or old["forward_invocation_id"] != f"forward:{forward_sha}"
        or old["pool_id"] != f"pool:{pool_sha}"
        or old["candidate_tensor_sha256"] != candidate_sha
        or old["candidate_row_sha256"] != row_sha
        or old["all_finite"] is not True
    ):
        raise ValueError("v5 review forward/pool binding drifted")
    selectors = value["selectors"]
    if type(selectors) is not dict or set(selectors) != set(ARMS):
        raise ValueError("v5 review selector keyset drifted")
    checked = {
        arm: _selector(
            selectors[arm],
            arm=arm,
            state=value["state_spec_id"],
            mode=value["mode"],
            pool=f"pool:{pool_sha}",
            candidate_sha=candidate_sha,
            candidate=candidate,
            selector_source_sha=selector_source_sha,
        )
        for arm in ARMS
    }
    return {
        "state_spec_id": value["state_spec_id"],
        "mode": value["mode"],
        "repeat_index": value["repeat_index"],
        "v4_run_receipt_sha256": old["receipt_sha256"],
        "candidate": candidate,
        "neighbor": neighbor,
        "neighbor_actor_fingerprints": list(actors),
        "atoms": atoms,
        "scores": {arm: checked[arm]["scores"] for arm in ARMS},
        "masks": {arm: checked[arm]["mask"] for arm in ARMS},
        "selectors": checked,
        "candidate_sha256": candidate_sha,
        "row_sha256": row_sha,
        "forward_invocation_id": f"forward:{forward_sha}",
        "pool_id": f"pool:{pool_sha}",
    }


def _selector(
    value: Any,
    *,
    arm: str,
    state: str,
    mode: str,
    pool: str,
    candidate_sha: str,
    candidate: np.ndarray,
    selector_source_sha: str,
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
        raise ValueError("v5 review selector schema drifted")
    payload = dict(value)
    supplied = payload.pop("selector_receipt_sha256")
    scores = np.asarray(value["scores"], dtype=np.float64)
    mask = np.asarray(value["mask"])
    action = _blob(value["selected_action"], (80, 4))
    if (
        supplied != _json_sha(payload)
        or value["arm"] != arm
        or value["state_spec_id"] != state
        or value["mode"] != mode
        or value["selector_source_sha256"] != selector_source_sha
        or value["pool_id"] != pool
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
        raise ValueError("v5 review selector provenance drifted")
    eligible = np.flatnonzero(mask)
    best = float(np.min(scores[eligible]))
    index = int(eligible[scores[eligible] == best][0])
    if (
        value["selected_index"] != index
        or not np.array_equal(action, candidate[index])
        or value["executable"]
        not in {"executable", "non_executable_retained"}
        or value["terminal"]
        not in {"complete", "terminal_failure_retained"}
    ):
        raise ValueError("v5 review selector action drifted")
    return {
        "scores": scores.tolist(),
        "mask": mask.tolist(),
        "selected_index": index,
        "selected_action": action,
        "executable": value["executable"],
        "terminal": value["terminal"],
    }


def _within_thresholds(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    freeze: Mapping[str, Any],
) -> dict[tuple[str, str, str], float]:
    base = _base_by_pair(runs, pairs)
    for row in pairs:
        if row["phase"] != "cross_mode":
            _cache(
                row["endpoint_values"],
                base[(row["phase"], row["state_spec_id"], row["pair_index"])],
                WITHIN_IDS,
            )
    records = {
        (row["phase"], row["mode"], row["endpoint_id"]): row
        for row in freeze["records"]
    }
    states = sorted({row["state_spec_id"] for row in pairs})
    thresholds = {}
    for phase, mode in (
        ("sequential_within", MODES[0]),
        ("batch8_within", MODES[1]),
    ):
        for endpoint in WITHIN_IDS:
            values = {state: [] for state in states}
            roots = {state: [] for state in states}
            for row in pairs:
                if row["phase"] == phase:
                    identity = (
                        phase,
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
                _q99(values[state]) for state in states
            ]
            floor = _floor(endpoint)
            threshold = _bootstrap(statistics, floor)
            key = (phase, mode, endpoint)
            record = records.get(key)
            if (
                record is None
                or record["calibration_state_ids"] != states
                or record["state_pair_receipt_sha256"]
                != [roots[state] for state in states]
                or not _float_equal_list(
                    record["state_statistics"], statistics
                )
                or float(record["resolution_floor"]).hex()
                != float(floor).hex()
                or float(record["bootstrap_result"]).hex()
                != threshold.hex()
                or float(record["threshold"]).hex() != threshold.hex()
            ):
                raise ValueError("v5 review within threshold drifted")
            thresholds[key] = threshold
    return thresholds


def _full_cache(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    thresholds: Mapping[tuple[str, str, str], float],
) -> None:
    base = _base_by_pair(runs, pairs)
    inflation = _inflation(base, pairs)
    for row in pairs:
        identity = (row["phase"], row["state_spec_id"], row["pair_index"])
        expected = dict(base[identity])
        if row["phase"] == "cross_mode":
            left = runs[
                (MODES[0], row["state_spec_id"], row["left_repeat_index"])
            ]
            right = runs[
                (MODES[1], row["state_spec_id"], row["right_repeat_index"])
            ]
            for arm in ARMS:
                abs_id = f"score.{arm}.abs_delta"
                denominator = max(
                    thresholds[("sequential_within", MODES[0], abs_id)],
                    thresholds[("batch8_within", MODES[1], abs_id)],
                    1e-9,
                )
                expected[
                    f"score.{arm}.within_mode_normalized_delta"
                ] = expected[abs_id] / denominator
                expected[f"score.{arm}.margin_ratio"] = _margin(
                    left["scores"][arm],
                    right["scores"][arm],
                    left["masks"][arm],
                    right["masks"][arm],
                )
                expected[f"score.{arm}.rank_error"] = _rank_error(
                    left["scores"][arm],
                    right["scores"][arm],
                    left["masks"][arm],
                    right["masks"][arm],
                )
            expected["neighbor.relative_within_mode_inflation"] = inflation[
                row["state_spec_id"]
            ]
            keys = CROSS_IDS
        else:
            keys = WITHIN_IDS
        _cache(row["endpoint_values"], expected, keys)


def _base_by_pair(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str, int], dict[str, float]]:
    result = {}
    for row in pairs:
        phase = row["phase"]
        if phase == "sequential_within":
            left_mode = right_mode = MODES[0]
        elif phase == "batch8_within":
            left_mode = right_mode = MODES[1]
        elif phase == "cross_mode":
            left_mode, right_mode = MODES
        else:
            raise ValueError("v5 review pair phase drifted")
        left = runs[
            (left_mode, row["state_spec_id"], row["left_repeat_index"])
        ]
        right = runs[
            (right_mode, row["state_spec_id"], row["right_repeat_index"])
        ]
        result[(phase, row["state_spec_id"], row["pair_index"])] = _base(
            left, right
        )
    return result


def _base(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> dict[str, float]:
    if (
        left["neighbor_actor_fingerprints"]
        != right["neighbor_actor_fingerprints"]
        or left["neighbor"].shape != right["neighbor"].shape
    ):
        raise ValueError("v5 review neighbor roster drifted")
    values = {}
    for index, (name, scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES)):
        values[f"atom.normalized_delta.{index:02d}.{name}"] = float(
            np.max(np.abs(left["atoms"][:, index] - right["atoms"][:, index]))
            / scale
        )
    values.update(_trajectory("ego", left["candidate"], right["candidate"]))
    values.update(_trajectory("neighbor", left["neighbor"], right["neighbor"]))
    for arm in ARMS:
        if left["masks"][arm] != right["masks"][arm]:
            raise ValueError("v5 review score mask drifted")
        mask = np.asarray(left["masks"][arm], dtype=bool)
        if not mask.any():
            raise ValueError("v5 review score eligibility missing")
        ls = np.asarray(left["scores"][arm], dtype=np.float64)
        rs = np.asarray(right["scores"][arm], dtype=np.float64)
        values[f"score.{arm}.abs_delta"] = float(
            np.max(np.abs(ls[mask] - rs[mask]))
        )
    if set(values) != set(WITHIN_IDS):
        raise ValueError("v5 review base formula keyset drifted")
    return values


def _trajectory(
    role: str, left: np.ndarray, right: np.ndarray
) -> dict[str, float]:
    return {
        f"trajectory.{role}.position_max_m": float(
            np.max(np.linalg.norm(left[..., :2] - right[..., :2], axis=-1))
        ),
        f"trajectory.{role}.heading_max_rad": float(
            np.max(
                np.abs(
                    (left[..., 2] - right[..., 2] + np.pi)
                    % (2 * np.pi)
                    - np.pi
                )
            )
        ),
        f"trajectory.{role}.speed_max_mps": float(
            np.max(np.abs(left[..., 3] - right[..., 3]))
        ),
    }


def _inflation(
    base: Mapping[tuple[str, str, int], Mapping[str, float]],
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    result = {}
    for state in {row["state_spec_id"] for row in pairs}:
        ratios = []
        for endpoint in NEIGHBOR_IDS:
            values = {}
            for phase in (
                "sequential_within",
                "batch8_within",
                "cross_mode",
            ):
                values[phase] = _q99(
                    [
                        base[(phase, state, row["pair_index"])][endpoint]
                        for row in pairs
                        if row["phase"] == phase
                        and row["state_spec_id"] == state
                    ]
                )
            ratios.append(
                values["cross_mode"]
                / max(
                    values["sequential_within"],
                    values["batch8_within"],
                    _floor(endpoint),
                )
            )
        result[state] = float(max(ratios))
    return result


def _margin(
    left_scores: Sequence[float],
    right_scores: Sequence[float],
    left_mask: Sequence[bool],
    right_mask: Sequence[bool],
) -> float:
    if list(left_mask) != list(right_mask):
        raise ValueError("v5 review margin masks drifted")
    mask = np.asarray(left_mask, dtype=bool)
    if int(mask.sum()) < 2:
        raise ValueError("v5 review margin eligibility missing")
    left = np.sort(np.asarray(left_scores, dtype=np.float64)[mask])
    right = np.sort(np.asarray(right_scores, dtype=np.float64)[mask])
    lgap = float(left[1] - left[0])
    rgap = float(right[1] - right[0])
    return abs(lgap - rgap) / max(abs(lgap), abs(rgap), 1e-9)


def _rank_error(
    left_scores: Sequence[float],
    right_scores: Sequence[float],
    left_mask: Sequence[bool],
    right_mask: Sequence[bool],
) -> float:
    left_mask_array = np.asarray(left_mask, dtype=bool)
    right_mask_array = np.asarray(right_mask, dtype=bool)
    shared = np.flatnonzero(left_mask_array & right_mask_array)
    if len(shared) < 2:
        raise ValueError("v5 review rank eligibility missing")
    left = np.asarray(left_scores, dtype=np.float64)[shared]
    right = np.asarray(right_scores, dtype=np.float64)[shared]
    lranks = _average_ranks(left)
    rranks = _average_ranks(right)
    lconstant = bool(np.all(lranks == lranks[0]))
    rconstant = bool(np.all(rranks == rranks[0]))
    if lconstant or rconstant:
        if lconstant and rconstant and np.array_equal(left, right):
            return 0.0
        raise ValueError("v5 review rank evidence ambiguous")
    rho = float(np.corrcoef(lranks, rranks)[0, 1])
    if not math.isfinite(rho):
        raise ValueError("v5 review rank evidence nonfinite")
    return 1.0 - rho


def _repeat0(
    runs: Mapping[tuple[str, str, int], Mapping[str, Any]],
    rows: Any,
) -> None:
    if type(rows) is not list or len(rows) != 64:
        raise ValueError("v5 review repeat0 denominator drifted")
    for row in rows:
        state = row["state_spec_id"]
        for mode in MODES:
            semantic = runs[(mode, state, 0)]
            pool = row["candidate_pools"][mode]
            if (
                pool["run_receipt_sha256"]
                != semantic["v4_run_receipt_sha256"]
                or pool["forward_invocation_id"]
                != semantic["forward_invocation_id"]
                or pool["pool_id"] != semantic["pool_id"]
                or pool["tensor_sha256"] != semantic["candidate_sha256"]
                or pool["row_sha256"] != semantic["row_sha256"]
            ):
                raise ValueError("v5 review repeat0 pool drifted")
            for arm in ARMS:
                source = row["selectors"][arm][mode]
                expected = semantic["selectors"][arm]
                if (
                    source["pool_id"] != semantic["pool_id"]
                    or source["candidate_tensor_sha256"]
                    != semantic["candidate_sha256"]
                    or not _float_equal_list(
                        source["scores"], expected["scores"]
                    )
                    or source["mask"] != expected["mask"]
                    or source["selected_index"] != expected["selected_index"]
                    or not np.array_equal(
                        np.asarray(
                            source["selected_action_80x4"],
                            dtype=np.float64,
                        ),
                        expected["selected_action"],
                    )
                ):
                    raise ValueError("v5 review repeat0 selector drifted")


def _blob(
    value: Any, expected_shape: tuple[int, ...] | None
) -> np.ndarray:
    fields = {
        "schema_version",
        "dtype",
        "shape",
        "codec",
        "raw_byte_count",
        "raw_sha256",
        "encoded_sha256",
        "data_base64",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("v5 review array blob schema drifted")
    if (
        value["schema_version"] != BLOB_SCHEMA
        or value["dtype"] != "<f8"
        or value["codec"] != "zlib_level9_then_base64_standard"
        or type(value["shape"]) is not list
        or any(type(item) is not int or item <= 0 for item in value["shape"])
    ):
        raise ValueError("v5 review array blob metadata drifted")
    try:
        encoded = base64.b64decode(
            value["data_base64"].encode("ascii"), validate=True
        )
        raw = zlib.decompress(encoded)
    except (ValueError, UnicodeError, zlib.error) as error:
        raise ValueError("v5 review array blob bytes drifted") from error
    if (
        base64.b64encode(encoded).decode("ascii") != value["data_base64"]
        or len(raw) != value["raw_byte_count"]
        or hashlib.sha256(raw).hexdigest() != value["raw_sha256"]
        or hashlib.sha256(encoded).hexdigest() != value["encoded_sha256"]
    ):
        raise ValueError("v5 review array blob hash drifted")
    shape = tuple(value["shape"])
    if expected_shape is not None and shape != expected_shape:
        raise ValueError("v5 review array blob shape drifted")
    array = np.frombuffer(raw, dtype="<f8").copy()
    if array.size != math.prod(shape):
        raise ValueError("v5 review array blob byte count drifted")
    array = array.reshape(shape)
    if not np.isfinite(array).all():
        raise ValueError("v5 review array blob nonfinite")
    return array


def _tensor_hash(value: np.ndarray) -> tuple[str, list[str]]:
    array = np.ascontiguousarray(value.astype("<f8", copy=False))
    return (
        hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        [
            hashlib.sha256(
                np.ascontiguousarray(array[index]).tobytes(order="C")
            ).hexdigest()
            for index in range(8)
        ],
    )


def _cache(
    observed: Any, expected: Mapping[str, float], keys: Sequence[str]
) -> None:
    if (
        type(observed) is not dict
        or set(observed) != set(keys)
        or set(expected) != set(keys)
    ):
        raise ValueError("v5 review derived cache keyset drifted")
    for key in keys:
        value = float(observed[key])
        if (
            not math.isfinite(value)
            or value < 0
            or value.hex() != float(expected[key]).hex()
        ):
            raise ValueError(f"v5 review raw/cache mismatch: {key}")


def _q99(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError("v5 review q99 input drifted")
    index = int(math.ceil(0.99 * (len(array) - 1)))
    return float(np.sort(array, kind="mergesort")[index])


def _bootstrap(values: Sequence[float], floor: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (64,) or not np.isfinite(array).all():
        raise ValueError("v5 review bootstrap input drifted")
    rng = np.random.Generator(np.random.PCG64DXSM(825071))
    indices = rng.integers(0, 64, size=(10000, 64), dtype=np.int64)
    resampled = array[indices]
    state_index = int(math.ceil(0.99 * 63))
    statistics = np.sort(resampled, axis=1, kind="mergesort")[
        :, state_index
    ]
    upper_index = int(math.ceil(0.95 * 9999))
    upper = float(np.sort(statistics, kind="mergesort")[upper_index])
    return max(float(floor), upper)


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
    raise ValueError("v5 review resolution floor undefined")


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    index = 0
    while index < len(values):
        end = index + 1
        while end < len(values) and values[order[end]] == values[order[index]]:
            end += 1
        ranks[order[index:end]] = (index + 1 + end) / 2.0
        index = end
    return ranks


def _float_equal_list(
    left: Sequence[float], right: Sequence[float]
) -> bool:
    return len(left) == len(right) and all(
        float(a).hex() == float(b).hex() for a, b in zip(left, right)
    )


def _json_sha(value: Any) -> str:
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


def _sha(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("v5 review SHA256 drifted")
    return value
