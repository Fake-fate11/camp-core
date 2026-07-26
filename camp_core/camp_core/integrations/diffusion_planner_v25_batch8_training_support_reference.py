"""Outcome-free V25 batch8 training-support reference contract.

This module contains only deterministic manifest selection, typed support
field definitions, quantile rules, and fail-closed validation.  Model and
selector execution lives in separately sealed scripts.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_batch8_training_support_reference_contract_v1"
ARTIFACT_SCHEMA = (
    "camp_dp_v25_batch8_training_support_reference_contract_artifact_v1"
)
MANIFEST_SCHEMA = (
    "camp_dp_v25_batch8_training_support_reference_input_manifest_v1"
)
PREFLIGHT_SCHEMA = (
    "camp_dp_v25_batch8_training_support_reference_preflight_v1"
)
RAW_SCHEMA = "camp_dp_v25_batch8_training_support_reference_raw_v1"
REVIEW_SCHEMA = (
    "camp_dp_v25_batch8_training_support_reference_independent_review_v1"
)
AUTHORITY_SCHEMA = (
    "camp_dp_v25_batch8_training_support_reference_high_authority_v1"
)

HIGH_AUTHORITY_JSON = (
    '{"abort_before_model_if_eligible_unique_pools_below_1000":true,'
    '"accepted_training_root_sha256":"8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9",'
    '"all_fields_required_no_weighted_total":true,'
    '"allowed_post_pool_computation":["14D_atoms","Static14D_scores_masks_margin_selected_index_action","Scene14D_scores_masks_margin_selected_index_action"],'
    '"batch8_calibration_contract_review_root_sha256":"8f2b198be18ef01607f4e355e014f3de07f049981ee05c0c18b96017b9237457",'
    '"batch8_calibration_contract_root_sha256":"f4216e9e59d7cc81cf8d7ebd69e0bdd38b1399ec11d6fe95866994b309d53c1c",'
    '"calibration_threshold_validation_closed_loop_fresh_holdout_authorized":false,'
    '"candidate_row_count":8000,'
    '"candidate_row_support_fields":["normalized_atom_00_to_13","score_static14d","score_scene14d"],'
    '"candidate_rows_per_pool":8,"capacity_floor_bytes":10737418240,'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"decision":"authorized_training_support_contract_manifest_acquisition_and_independent_review",'
    '"exact_training_pool_count":1000,'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"fail_scope":"specific_field_or_pool_failure_returned_no_automatic_training",'
    '"failure_retention":"all_1000_pool_slots_retained_no_drop_replace_complete_case",'
    '"fixed_dp_head":"7a1d33da277a1992ec474b5383a0c963c72e04e4",'
    '"fixed_dp_model_weights_atoms_thresholds_change_authorized":false,'
    '"formal_model_invocations":1000,'
    '"implementation_head":"383d9944ac1bc912880d15ef3c5ed4944c07c9ed",'
    '"latent_policy":"one_prefrozen_unique8_latent_manifest_per_pool_row0_zero_rows1_7_independent_pcg64_float32",'
    '"later_calibration_pool_field_coverage":"5_of_5_pools_per_state",'
    '"later_calibration_required_passing_states":"at_least_61_of_64_per_field",'
    '"later_calibration_row_field_coverage":"at_least_38_of_40_rows_per_state",'
    '"manifest_must_precede_model":true,'
    '"manifest_selection":"id_free_clone_unique_stratified_largest_remainder_then_sha256_order_no_replacement",'
    '"model_calls_per_pool":1,"old_artifact_cas_write_authorized":false,'
    '"outcome_read_authorized":false,'
    '"pass_scope":"reference_well_formed_all_hard_gates_full_denominator_allows_future_320_calibration_no_retraining_triggered_not_no_retraining_proof",'
    '"pointer_head":"0df332d844a3dc3bec063c062e9e0ba8aebbbafc",'
    '"pool_level_support_fields":["margin_static14d","margin_scene14d","eligible_count_static14d","eligible_count_scene14d"],'
    '"post_pool_model_dp_latent_generation_calls":0,'
    '"producer_reviewer_independent_raw_reconstruction":true,'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"reference_interval":"empirical_q0_005_lower_and_q0_995_higher_inclusive",'
    '"reference_quantile_values_use_all_candidate_rows_but_independent_n_is_pool_count_1000":true,'
    '"return_to_high_after_review":true,'
    '"sampling_unit":"unique_training_only_same_ego_state_pool",'
    '"schema_version":"camp_dp_v25_batch8_training_support_reference_high_authority_v1",'
    '"selected_action_unit":"one_binding_receipt_per_arm_per_pool",'
    '"selector_receipt_total":2000,"selector_receipts_per_arm":1000,'
    '"strata":["seven_families","risk_tier","route_geometry","source_availability"],'
    '"training_or_retraining_authorized":false,'
    '"training_scale_sha256":"72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb",'
    '"zero_overlap_with":["development_calibration","independent_validation","legacy_nonholdout","Fresh_B2","Fresh_B3","Fresh_B4"]}'
)
HIGH_AUTHORITY_SHA256 = (
    "1c3f6c17db7c75883e7f1ffad447c5677dbbaaefa3eb9342dbbc069350dbf86c"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ACCEPTED_TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_SCALE_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
CALIBRATION_CONTRACT_ROOT = (
    "f4216e9e59d7cc81cf8d7ebd69e0bdd38b1399ec11d6fe95866994b309d53c1c"
)
CALIBRATION_CONTRACT_REVIEW_ROOT = (
    "8f2b198be18ef01607f4e355e014f3de07f049981ee05c0c18b96017b9237457"
)

POOL_COUNT = 1000
ROWS_PER_POOL = 8
ROW_COUNT = POOL_COUNT * ROWS_PER_POOL
MODEL_CALL_COUNT = POOL_COUNT
SELECTOR_RECEIPT_COUNT_PER_ARM = POOL_COUNT
SELECTOR_RECEIPT_COUNT = 2 * POOL_COUNT
CAPACITY_FLOOR_BYTES = 10 * 1024**3
TICK_INDEX = 0
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = "<f4"

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
SOURCE_AVAILABILITY = ("mapped_signal", "no_signal")
ROUTE_GEOMETRY_BINS = (
    "heading_change_abs_le_0_15rad",
    "heading_change_abs_gt_0_15_le_0_75rad",
    "heading_change_abs_gt_0_75rad",
)
ROUTE_GEOMETRY_THRESHOLDS_RAD = (0.15, 0.75)
ZERO_OVERLAP_SPLITS = (
    "development_calibration",
    "independent_validation",
    "legacy_nonholdout",
    "Fresh_B2",
    "Fresh_B3",
    "Fresh_B4",
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
POST_POOL_ZERO_FIELDS = (
    "model_call_count",
    "dp_call_count",
    "latent_generation_count",
    "candidate_generation_count",
)
REQUIRED_POOL_BINDINGS = (
    "input_manifest_sha256",
    "actual_state_sha256",
    "route_geometry_sha256",
    "source_record_sha256",
    "latent_manifest_sha256",
    "model_source_sha256",
    "checkpoint_sha256",
    "runtime_fingerprint_sha256",
    "forward_id",
    "pool_id",
    "candidate_tensor_sha256",
)
EXACT_DIR_KEYS = (
    "contract",
    "contract_review",
    "focused",
    "preflight",
    "preflight_review",
    "raw",
    "raw_review",
    "final_docs",
)
PROHIBITED_RUNS = (
    "calibration_320",
    "threshold_materialization",
    "independent_validation",
    "closed_loop",
    "fresh",
    "holdout",
    "training",
    "retraining",
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def _git_sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} must be lowercase Git SHA")
    return value


def _finite_number(value: Any, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{label} must be finite numeric")
    return float(value)


def latent_seed_for_clone(clone_payload_sha256: str) -> int:
    _sha(clone_payload_sha256, "clone payload")
    digest = hashlib.sha256(
        (HIGH_AUTHORITY_SHA256 + ":" + clone_payload_sha256).encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def materialize_latent(seed: int) -> np.ndarray:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("latent seed must be integer")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    latent[1:] = rng.standard_normal(latent[1:].shape).astype(np.float32)
    return np.ascontiguousarray(latent)


def latent_manifest(seed: int) -> dict[str, Any]:
    latent = materialize_latent(seed)
    row_sha = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in latent
    ]
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_unique_latent_manifest_v1"
        ),
        "policy": (
            "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
        ),
        "bit_generator": "PCG64",
        "seed": int(seed),
        "shape": list(LATENT_SHAPE),
        "dtype": LATENT_DTYPE,
        "finite": bool(np.isfinite(latent).all()),
        "row0_all_zero": bool(np.count_nonzero(latent[0]) == 0),
        "row_sha256": row_sha,
        "unique_row_sha256_count": len(set(row_sha)),
        "tensor_sha256": sha256_bytes(latent.tobytes(order="C")),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def _wrap_to_pi(value: float) -> float:
    return (float(value) + math.pi) % (2.0 * math.pi) - math.pi


def route_geometry_bin(route_polyline_local_m: Sequence[Sequence[Any]]) -> str:
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
    change = abs(_wrap_to_pi(float(headings[-1] - headings[0])))
    if change <= ROUTE_GEOMETRY_THRESHOLDS_RAD[0]:
        return ROUTE_GEOMETRY_BINS[0]
    if change <= ROUTE_GEOMETRY_THRESHOLDS_RAD[1]:
        return ROUTE_GEOMETRY_BINS[1]
    return ROUTE_GEOMETRY_BINS[2]


def source_availability(source_class: Any) -> str:
    if source_class not in SOURCE_AVAILABILITY:
        raise ValueError("training source availability class drifted")
    return str(source_class)


def build_clone_payload(source_row: Mapping[str, Any]) -> dict[str, Any]:
    if type(source_row) is not dict:
        raise TypeError("source row must be object")
    if (
        source_row.get("runner_eligible") is not True
        or source_row.get("retention_role") != "executable"
        or source_row.get("family") not in FAMILIES
        or source_row.get("tier") not in RISK_TIERS
        or source_row.get("seed") != 25001
    ):
        raise ValueError("source row is not an eligible training-only pool")
    chain = source_row.get("source_chain")
    if type(chain) is not dict:
        raise ValueError("source chain missing")
    semantic = chain.get("semantic_clone_payload")
    if type(semantic) is not dict:
        raise ValueError("semantic clone payload missing")
    semantic_sha = _sha(chain.get("semantic_clone_sha256"), "semantic clone")
    if sha256_json(semantic) != semantic_sha:
        raise ValueError("semantic clone payload SHA drifted")
    route_geometry_sha = _sha(
        chain.get("route_geometry_sha256"), "route geometry"
    )
    source_map_sha = _sha(
        source_row.get("source_map_sha256"), "source map"
    )
    source_chain_sha = _sha(
        chain.get("source_chain_sha256"), "source chain"
    )
    formal_case_sha = _sha(
        source_row.get("formal_case_sha256"), "formal case"
    )
    source_record = {
        "scenario_source_content_sha256": formal_case_sha,
        "semantic_clone_sha256": semantic_sha,
        "source_chain_sha256": source_chain_sha,
        "source_map_sha256": source_map_sha,
        "route_identity_sha256": _sha(
            source_row.get("route_identity_sha256"), "route identity"
        ),
        "route_geometry_sha256": route_geometry_sha,
        "scenario_seed": 25001,
        "tick_index": TICK_INDEX,
        "family": str(source_row["family"]),
        "risk_tier": str(source_row["tier"]),
        "route_geometry_bin": route_geometry_bin(
            semantic.get("route_polyline_local_m")
        ),
        "source_availability": source_availability(
            source_row.get("source_class")
        ),
    }
    source_record_sha = sha256_json(source_record)
    clone_payload = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_id_free_clone_payload_v1"
        ),
        "source_record": source_record,
        "source_record_sha256": source_record_sha,
    }
    clone_payload_sha = sha256_json(clone_payload)
    seed = latent_seed_for_clone(clone_payload_sha)
    latent = latent_manifest(seed)
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_pool_manifest_entry_v1"
        ),
        "source_record": source_record,
        "source_record_sha256": source_record_sha,
        "clone_payload_sha256": clone_payload_sha,
        "clone_key_sha256": sha256_json(
            {
                "source_record_sha256": source_record_sha,
                "latent_instance_sha256": latent["manifest_sha256"],
            }
        ),
        "latent_manifest": latent,
        "stratum": {
            "family": source_record["family"],
            "risk_tier": source_record["risk_tier"],
            "route_geometry": source_record["route_geometry_bin"],
            "source_availability": source_record["source_availability"],
        },
    }
    result["manifest_entry_sha256"] = sha256_json(result)
    return result


def materialize_input_tensor_manifest(
    actual_input_tensors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    if type(actual_input_tensors) is not dict or not actual_input_tensors:
        raise ValueError("actual input tensor bundle must be a nonempty dict")
    tensors = []
    for name in sorted(actual_input_tensors):
        if type(name) is not str or not name:
            raise ValueError("actual input tensor name drifted")
        value = np.ascontiguousarray(np.asarray(actual_input_tensors[name]))
        if (
            value.dtype.kind not in "biuf"
            or value.shape[0] != 1
            or not np.isfinite(value).all()
        ):
            raise ValueError("actual input tensor must be finite single-ego numeric")
        tensors.append(
            {
                "name": name,
                "dtype": value.dtype.str,
                "shape": list(value.shape),
                "tensor_sha256": sha256_bytes(value.tobytes(order="C")),
            }
        )
    manifest = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_actual_input_bundle_v1"
        ),
        "tensor_order": [row["name"] for row in tensors],
        "tensors": tensors,
    }
    manifest["bundle_sha256"] = sha256_json(manifest)
    return manifest


def finalize_pool_manifest_entry(
    base_entry: Mapping[str, Any],
    *,
    actual_input_tensors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    if type(base_entry) is not dict:
        raise TypeError("base manifest entry must be object")
    input_manifest = materialize_input_tensor_manifest(actual_input_tensors)
    source_record = deepcopy(base_entry.get("source_record"))
    if type(source_record) is not dict:
        raise ValueError("base source record missing")
    source_record_sha = _sha(
        base_entry.get("source_record_sha256"), "source record"
    )
    if sha256_json(source_record) != source_record_sha:
        raise ValueError("base source record SHA drifted")
    latent = deepcopy(base_entry.get("latent_manifest"))
    if type(latent) is not dict:
        raise ValueError("base latent manifest missing")
    latent_manifest_sha = _sha(
        latent.get("manifest_sha256"), "latent manifest"
    )
    if sha256_json(
        {key: value for key, value in latent.items() if key != "manifest_sha256"}
    ) != latent_manifest_sha:
        raise ValueError("base latent manifest SHA drifted")
    actual_state = {
        "source_record_sha256": source_record_sha,
        "actual_input_bundle_sha256": input_manifest["bundle_sha256"],
        "tick_index": TICK_INDEX,
    }
    actual_state_sha = sha256_json(actual_state)
    clone_payload = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_id_free_clone_payload_v2"
        ),
        "route_geometry_sha256": source_record["route_geometry_sha256"],
        "source_record_sha256": source_record_sha,
        "scenario_seed": source_record["scenario_seed"],
        "actual_state_sha256": actual_state_sha,
        "latent_instance_sha256": latent_manifest_sha,
    }
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_pool_manifest_entry_v2"
        ),
        "source_record": source_record,
        "source_record_sha256": source_record_sha,
        "actual_input_tensor_manifest": input_manifest,
        "actual_state": actual_state,
        "actual_state_sha256": actual_state_sha,
        "latent_manifest": latent,
        "clone_payload": clone_payload,
        "clone_key_sha256": sha256_json(clone_payload),
        "overlap_keys": {
            "route_geometry": source_record["route_geometry_sha256"],
            "source": source_record_sha,
            "state": actual_state_sha,
            "seed": sha256_json(
                {
                    "scenario_seed": source_record["scenario_seed"],
                    "source_record_sha256": source_record_sha,
                }
            ),
            "latent_instance": latent_manifest_sha,
        },
        "stratum": deepcopy(base_entry.get("stratum")),
    }
    result["manifest_entry_sha256"] = sha256_json(result)
    return result


def _cell_key(entry: Mapping[str, Any]) -> tuple[str, str, str, str]:
    value = entry.get("stratum")
    if type(value) is not dict or set(value) != {
        "family",
        "risk_tier",
        "route_geometry",
        "source_availability",
    }:
        raise ValueError("manifest stratum schema drifted")
    key = (
        str(value["family"]),
        str(value["risk_tier"]),
        str(value["route_geometry"]),
        str(value["source_availability"]),
    )
    if (
        key[0] not in FAMILIES
        or key[1] not in RISK_TIERS
        or key[2] not in ROUTE_GEOMETRY_BINS
        or key[3] not in SOURCE_AVAILABILITY
    ):
        raise ValueError("manifest stratum value drifted")
    return key


def largest_remainder_quotas(
    cell_counts: Mapping[tuple[str, str, str, str], int],
    *,
    total: int = POOL_COUNT,
) -> dict[tuple[str, str, str, str], int]:
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        raise ValueError("selection total must be positive integer")
    if not cell_counts:
        raise ValueError("selection requires nonempty cells")
    ordered = sorted(cell_counts)
    counts: dict[tuple[str, str, str, str], int] = {}
    for key in ordered:
        if (
            type(key) is not tuple
            or len(key) != 4
            or isinstance(cell_counts[key], bool)
            or not isinstance(cell_counts[key], int)
            or cell_counts[key] <= 0
        ):
            raise ValueError("cell count schema drifted")
        counts[key] = int(cell_counts[key])
    if len(counts) > total or sum(counts.values()) < total:
        raise ValueError("required cell coverage or eligible capacity is insufficient")
    quota = {key: 1 for key in ordered}
    remaining = total - len(ordered)
    capacity_after_min = {key: counts[key] - 1 for key in ordered}
    weight_total = sum(capacity_after_min.values())
    if remaining > 0 and weight_total <= 0:
        raise ValueError("eligible capacity after minimum allocation is insufficient")
    ideals = {
        key: (
            0.0
            if remaining == 0
            else remaining * capacity_after_min[key] / weight_total
        )
        for key in ordered
    }
    for key in ordered:
        quota[key] += int(math.floor(ideals[key]))
    remainder = total - sum(quota.values())
    rank = sorted(
        ordered,
        key=lambda key: (-(ideals[key] - math.floor(ideals[key])), key),
    )
    for key in rank[:remainder]:
        quota[key] += 1
    if (
        sum(quota.values()) != total
        or any(quota[key] < 1 or quota[key] > counts[key] for key in ordered)
    ):
        raise ValueError("largest-remainder quota invariant failed")
    return quota


def select_finalized_manifest_entries(
    entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    entries = [deepcopy(dict(row)) for row in entries]
    if any(
        row.get("schema_version")
        != "camp_dp_v25_batch8_training_support_pool_manifest_entry_v2"
        for row in entries
    ):
        raise ValueError("selection requires finalized actual-input entries")
    clone_counts = Counter(row["clone_key_sha256"] for row in entries)
    if any(value != 1 for value in clone_counts.values()):
        raise ValueError("eligible training clone keys are not unique")
    if len(entries) < POOL_COUNT:
        raise ValueError("eligible unique training pools below 1000")
    cells: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        cells[_cell_key(entry)].append(entry)
    missing_families = set(FAMILIES) - {key[0] for key in cells}
    if missing_families:
        raise ValueError("required seven-family coverage is unavailable")
    quotas = largest_remainder_quotas(
        {key: len(value) for key, value in cells.items()}
    )
    selected: list[dict[str, Any]] = []
    cell_rows = []
    for key in sorted(cells):
        rows = sorted(
            cells[key],
            key=lambda row: sha256_bytes(
                HIGH_AUTHORITY_SHA256.encode("ascii")
                + bytes.fromhex(row["clone_key_sha256"])
            ),
        )
        chosen = rows[: quotas[key]]
        selected.extend(chosen)
        cell_rows.append(
            {
                "cell": list(key),
                "eligible_count": len(rows),
                "quota": quotas[key],
                "selected_clone_key_sha256": [
                    row["clone_key_sha256"] for row in chosen
                ],
            }
        )
    selected = sorted(
        selected,
        key=lambda row: sha256_bytes(
            HIGH_AUTHORITY_SHA256.encode("ascii")
            + bytes.fromhex(row["clone_key_sha256"])
        ),
    )
    if len(selected) != POOL_COUNT or len(
        {row["clone_key_sha256"] for row in selected}
    ) != POOL_COUNT:
        raise ValueError("selected manifest denominator drifted")
    numbered = []
    for ordinal, entry in enumerate(selected):
        row = deepcopy(entry)
        row["pool_ordinal"] = ordinal
        row["pool_id"] = f"training_support:{ordinal:04d}"
        row["manifest_entry_sha256"] = sha256_json(
            {key: value for key, value in row.items() if key != "manifest_entry_sha256"}
        )
        numbered.append(row)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "authority_sha256": HIGH_AUTHORITY_SHA256,
        "selection_rule": (
            "required_nonempty_cell_one_then_largest_remainder_capacity_"
            "proportional_canonical_cell_tie_then_authority_clone_sha_order"
        ),
        "sampling_unit": "unique_training_only_same_ego_state_pool",
        "eligible_unique_pool_count": len(entries),
        "selected_pool_count": len(numbered),
        "candidate_row_count": ROW_COUNT,
        "model_call_count": MODEL_CALL_COUNT,
        "selector_receipt_count": SELECTOR_RECEIPT_COUNT,
        "cells": cell_rows,
        "entries": numbered,
        "no_drop_no_replace": True,
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest


def select_manifest_entries(
    source_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compatibility helper for source-only selection tests.

    Formal acquisition must call ``select_finalized_manifest_entries`` after
    exact single-ego input bytes have been captured before any model call.
    """

    bases = [build_clone_payload(source_row) for source_row in source_rows]
    if len({row["clone_key_sha256"] for row in bases}) != len(bases):
        raise ValueError("eligible training clone keys are not unique")
    entries = []
    for index, base in enumerate(bases):
        synthetic = {
            "source_only_selection_guard": np.asarray(
                [[index]], dtype=np.int64
            )
        }
        entries.append(
            finalize_pool_manifest_entry(
                base, actual_input_tensors=synthetic
            )
        )
    return select_finalized_manifest_entries(entries)


def row_field_registry() -> list[dict[str, Any]]:
    fields = []
    for index, name in enumerate(ATOM_NAMES):
        fields.append(
            {
                "field_id": f"normalized_atom_{index:02d}",
                "name": name,
                "unit": "training_scale_normalized_dimensionless",
                "formula": f"raw_atom[{index}]/training_scale[{index}]",
                "observation_unit": "candidate_row_with_pool_id_retained",
                "descriptive_value_count": ROW_COUNT,
                "independent_n": POOL_COUNT,
                "finite_required": True,
            }
        )
    for arm in ("static14d", "scene14d"):
        fields.append(
            {
                "field_id": f"score_{arm}",
                "name": f"CAMP-{arm.title()} score",
                "unit": "dimensionless",
                "formula": "dot(clip(normalized_atoms,0,10),frozen_arm_weights)",
                "observation_unit": "candidate_row_with_pool_id_retained",
                "descriptive_value_count": ROW_COUNT,
                "independent_n": POOL_COUNT,
                "finite_required": True,
            }
        )
    return fields


def pool_field_registry() -> list[dict[str, Any]]:
    fields = []
    for arm in ("static14d", "scene14d"):
        fields.extend(
            [
                {
                    "field_id": f"margin_{arm}",
                    "unit": "dimensionless",
                    "formula": (
                        "second_lowest_eligible_score-lowest_eligible_score;"
                        "requires_at_least_2_eligible_candidates"
                    ),
                    "observation_unit": "pool",
                    "value_count": POOL_COUNT,
                    "independent_n": POOL_COUNT,
                    "finite_required": True,
                },
                {
                    "field_id": f"eligible_count_{arm}",
                    "unit": "candidate_count",
                    "formula": "sum(strict_bool_eligibility_mask)",
                    "observation_unit": "pool",
                    "value_count": POOL_COUNT,
                    "independent_n": POOL_COUNT,
                    "finite_required": True,
                },
            ]
        )
    return fields


def inclusive_quantile_indices(count: int) -> dict[str, int]:
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("quantile count must be positive integer")
    return {
        "q0_005_lower_index": int(math.floor(0.005 * (count - 1))),
        "q0_995_upper_index": int(math.ceil(0.995 * (count - 1))),
    }


def inclusive_reference_interval(values: Sequence[Any]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("reference values must be nonempty finite vector")
    ordered = np.sort(array, kind="stable")
    indices = inclusive_quantile_indices(int(ordered.size))
    return {
        "count": int(ordered.size),
        **indices,
        "q0_005_lower": float(ordered[indices["q0_005_lower_index"]]),
        "q0_995_upper": float(ordered[indices["q0_995_upper_index"]]),
        "interval_inclusive": True,
    }


def contract_payload(
    *,
    implementation_head: str,
    pointer_head_at_authority: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    _git_sha(implementation_head, "implementation head")
    _git_sha(pointer_head_at_authority, "pointer head")
    if type(exact_dirs) is not dict or tuple(sorted(exact_dirs)) != tuple(
        sorted(EXACT_DIR_KEYS)
    ):
        raise ValueError("exact dirs keyset drifted")
    if any(
        type(value) is not str or not value.startswith("/root/autodl-tmp/")
        for value in exact_dirs.values()
    ):
        raise ValueError("exact dirs must be absolute AutoDL paths")
    if type(source_sha256) is not dict or not source_sha256:
        raise ValueError("source SHA registry missing")
    for key, value in source_sha256.items():
        _sha(value, f"source {key}")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "high_authority": json.loads(HIGH_AUTHORITY_JSON),
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "authority_canonical_json_exact": HIGH_AUTHORITY_JSON,
        "implementation_head": implementation_head,
        "pointer_head_at_authority": pointer_head_at_authority,
        "fixed_dp_head": FIXED_DP_HEAD,
        "accepted_training_root_sha256": ACCEPTED_TRAINING_ROOT,
        "training_scale_sha256": TRAINING_SCALE_SHA256,
        "batch8_calibration_contract_root_sha256": CALIBRATION_CONTRACT_ROOT,
        "batch8_calibration_contract_review_root_sha256": (
            CALIBRATION_CONTRACT_REVIEW_ROOT
        ),
        "exact_dirs": dict(exact_dirs),
        "source_sha256": dict(source_sha256),
        "denominator": {
            "pool_count": POOL_COUNT,
            "rows_per_pool": ROWS_PER_POOL,
            "candidate_row_count": ROW_COUNT,
            "formal_model_invocations": MODEL_CALL_COUNT,
            "selector_receipts_per_arm": SELECTOR_RECEIPT_COUNT_PER_ARM,
            "selector_receipt_total": SELECTOR_RECEIPT_COUNT,
            "sampling_unit": "pool",
            "row_or_tick_independent_n_claimed": False,
        },
        "manifest_contract": {
            "schema_version": MANIFEST_SCHEMA,
            "families": list(FAMILIES),
            "risk_tiers": list(RISK_TIERS),
            "route_geometry_bins": list(ROUTE_GEOMETRY_BINS),
            "route_geometry_thresholds_rad": list(
                ROUTE_GEOMETRY_THRESHOLDS_RAD
            ),
            "source_availability": list(SOURCE_AVAILABILITY),
            "selection": (
                "required_nonempty_cell_one_then_largest_remainder_"
                "capacity_proportional_canonical_cell_tie_then_"
                "sha256_authority_plus_clone_bytes_order"
            ),
            "zero_overlap_with": list(ZERO_OVERLAP_SPLITS),
            "tick_index": TICK_INDEX,
            "no_drop_no_replace": True,
            "abort_before_model_if_eligible_unique_pools_below_1000": True,
        },
        "pool_generation_contract": {
            "generator": "new_single_invocation_batched_k8_candidate_pool",
            "same_ego_batch_size": 8,
            "agent_as_ego_batch": False,
            "formal_model_calls_per_pool": 1,
            "latent_shape": list(LATENT_SHAPE),
            "latent_dtype": LATENT_DTYPE,
            "latent_policy": (
                "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
            ),
            "candidate0_is_row0": True,
            "candidate_tensor_immutable": True,
            "post_pool_zero_fields": list(POST_POOL_ZERO_FIELDS),
            "required_pool_bindings": list(REQUIRED_POOL_BINDINGS),
        },
        "support_field_contract": {
            "row_fields": row_field_registry(),
            "pool_fields": pool_field_registry(),
            "field_count": 20,
            "all_fields_required": True,
            "weighted_total_created": False,
            "row_reference_indices": inclusive_quantile_indices(ROW_COUNT),
            "pool_reference_indices": inclusive_quantile_indices(POOL_COUNT),
            "finite_or_missing_rule": (
                "any_missing_or_nonfinite_field_retained_and_reference_fails"
            ),
            "pool_first_summaries_required": True,
        },
        "selector_contract": {
            "arms": ["Static14D", "Scene14D"],
            "same_immutable_candidate_tensor": True,
            "masks_strict_bool_nonempty": True,
            "selected_index_and_action_exact_row_binding": True,
            "margin_requires_at_least_two_eligible": True,
            "post_pool_model_dp_latent_candidate_generation_calls": 0,
        },
        "future_calibration_coverage": {
            "row_fields": "at_least_38_of_40_rows_per_state",
            "pool_fields": "5_of_5_pools_per_state",
            "required_passing_states_per_field": "at_least_61_of_64",
            "thresholds_set_from_this_acquisition": False,
        },
        "capacity_contract": {
            "floor_bytes": CAPACITY_FLOOR_BYTES,
            "projected_bytes_plus_reserve_required": True,
            "projected_end_free_strictly_greater_or_equal_floor": True,
        },
        "failure_retention": (
            "all_1000_pool_slots_retained_no_drop_replace_complete_case"
        ),
        "pass_scope": (
            "reference_well_formed_all_hard_gates_full_denominator_allows_"
            "future_320_calibration_no_retraining_triggered_not_no_"
            "retraining_proof"
        ),
        "claim_authorized": False,
        "training_or_retraining_authorized": False,
        "prohibited_run_counts": {key: 0 for key in PROHIBITED_RUNS},
    }
    return payload


def validate_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    if type(payload) is not dict:
        raise TypeError("contract must be object")
    required = {
        "schema_version",
        "high_authority",
        "high_authority_sha256",
        "authority_canonical_json_exact",
        "implementation_head",
        "pointer_head_at_authority",
        "fixed_dp_head",
        "accepted_training_root_sha256",
        "training_scale_sha256",
        "batch8_calibration_contract_root_sha256",
        "batch8_calibration_contract_review_root_sha256",
        "exact_dirs",
        "source_sha256",
        "denominator",
        "manifest_contract",
        "pool_generation_contract",
        "support_field_contract",
        "selector_contract",
        "future_calibration_coverage",
        "capacity_contract",
        "failure_retention",
        "pass_scope",
        "claim_authorized",
        "training_or_retraining_authorized",
        "prohibited_run_counts",
    }
    if set(payload) != required:
        raise ValueError("contract exact schema drifted")
    expected = contract_payload(
        implementation_head=str(payload["implementation_head"]),
        pointer_head_at_authority=str(payload["pointer_head_at_authority"]),
        exact_dirs=payload["exact_dirs"],
        source_sha256=payload["source_sha256"],
    )
    if payload != expected:
        raise ValueError("contract semantic payload drifted")
    if (
        sha256_bytes(HIGH_AUTHORITY_JSON.encode("ascii"))
        != HIGH_AUTHORITY_SHA256
        or sha256_bytes(canonical_bytes(payload["high_authority"])[:-1])
        != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("High authority canonical SHA drifted")
    return deepcopy(expected)


def validate_zero_overlap(
    selected_clone_keys: Iterable[str],
    forbidden_clone_keys: Mapping[str, Iterable[str]],
) -> dict[str, int]:
    selected = {_sha(value, "selected clone key") for value in selected_clone_keys}
    if len(selected) != POOL_COUNT:
        raise ValueError("selected clone denominator drifted")
    if type(forbidden_clone_keys) is not dict or set(forbidden_clone_keys) != set(
        ZERO_OVERLAP_SPLITS
    ):
        raise ValueError("forbidden split registry drifted")
    counts = {}
    for split in ZERO_OVERLAP_SPLITS:
        forbidden = {
            _sha(value, f"{split} forbidden clone key")
            for value in forbidden_clone_keys[split]
        }
        overlap = selected & forbidden
        if overlap:
            raise ValueError(f"training manifest overlaps {split}")
        counts[split] = len(forbidden)
    return counts


def validate_pool_receipt_topology(
    manifest: Mapping[str, Any],
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        type(manifest) is not dict
        or manifest.get("selected_pool_count") != POOL_COUNT
        or type(receipts) not in (list, tuple)
        or len(receipts) != POOL_COUNT
    ):
        raise ValueError("pool receipt denominator drifted")
    entries = manifest.get("entries")
    if type(entries) is not list or len(entries) != POOL_COUNT:
        raise ValueError("pool manifest entries drifted")
    states: set[str] = set()
    complete = 0
    failed = 0
    for ordinal, (entry, receipt) in enumerate(zip(entries, receipts)):
        if type(entry) is not dict or type(receipt) is not dict:
            raise ValueError("pool receipt row must be object")
        state = _sha(entry.get("actual_state_sha256"), "actual state")
        if state in states:
            raise ValueError("duplicate training state/pool is forbidden")
        states.add(state)
        if (
            entry.get("pool_ordinal") != ordinal
            or receipt.get("pool_ordinal") != ordinal
            or receipt.get("pool_id") != entry.get("pool_id")
            or receipt.get("manifest_entry_sha256")
            != entry.get("manifest_entry_sha256")
            or receipt.get("formal_model_call_count") != 1
            or receipt.get("selector_receipt_count") != 2
            or receipt.get("post_pool_model_call_count") != 0
            or receipt.get("post_pool_dp_call_count") != 0
            or receipt.get("post_pool_latent_generation_count") != 0
            or receipt.get("post_pool_candidate_generation_count") != 0
            or receipt.get("outcome_fields_read") != []
        ):
            raise ValueError("pool receipt topology or binding drifted")
        if receipt.get("status") == "complete":
            if (
                len(receipt.get("candidate_row_sha256", [])) != 8
                or len(set(receipt["candidate_row_sha256"])) != 8
            ):
                raise ValueError("complete pool must contain eight unique rows")
            complete += 1
        elif receipt.get("status") == "failed_retained":
            failed += 1
        else:
            raise ValueError("pool receipt terminal state drifted")
    return {
        "pool_slot_count": POOL_COUNT,
        "complete_pool_count": complete,
        "failed_pool_count": failed,
        "formal_model_call_count": POOL_COUNT,
        "selector_receipt_count": SELECTOR_RECEIPT_COUNT,
        "unique_actual_state_count": len(states),
    }


def validate_reference_cache(
    *,
    row_values: Mapping[str, Sequence[Any]],
    pool_values: Mapping[str, Sequence[Any]],
    row_references: Mapping[str, Any],
    pool_references: Mapping[str, Any],
) -> dict[str, Any]:
    row_ids = {row["field_id"] for row in row_field_registry()}
    pool_ids = {row["field_id"] for row in pool_field_registry()}
    if (
        type(row_values) is not dict
        or type(pool_values) is not dict
        or set(row_values) != row_ids
        or set(pool_values) != pool_ids
        or set(row_references) != row_ids
        or set(pool_references) != pool_ids
    ):
        raise ValueError("reference field registry incomplete")
    for field_id, values in row_values.items():
        array = np.asarray(values, dtype=np.float64).reshape(-1)
        if array.size != ROW_COUNT or not np.isfinite(array).all():
            raise ValueError(f"row reference denominator invalid: {field_id}")
        if row_references[field_id] != inclusive_reference_interval(array.tolist()):
            raise ValueError(f"row reference cache drifted: {field_id}")
    for field_id, values in pool_values.items():
        array = np.asarray(values, dtype=np.float64).reshape(-1)
        if array.size != POOL_COUNT or not np.isfinite(array).all():
            raise ValueError(f"pool reference denominator invalid: {field_id}")
        if pool_references[field_id] != inclusive_reference_interval(array.tolist()):
            raise ValueError(f"pool reference cache drifted: {field_id}")
    return {
        "row_field_count": len(row_ids),
        "pool_field_count": len(pool_ids),
        "row_value_count_per_field": ROW_COUNT,
        "pool_value_count_per_field": POOL_COUNT,
    }
