"""Separate-role literal oracle for the V25 training-support reference."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_batch8_training_support_reference_contract_v1"
AUTHORITY_SHA256 = (
    "1c3f6c17db7c75883e7f1ffad447c5677dbbaaefa3eb9342dbbc069350dbf86c"
)
AUTHORITY_JSON = (
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
FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)
TIERS = ("easy", "borderline", "high_risk")
GEOMETRY = (
    "heading_change_abs_le_0_15rad",
    "heading_change_abs_gt_0_15_le_0_75rad",
    "heading_change_abs_gt_0_75rad",
)
SOURCES = ("mapped_signal", "no_signal")
OVERLAP_SPLITS = (
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


def _bytes(value: Any) -> bytes:
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


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_digest(value: Any) -> str:
    return _digest(_bytes(value))


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} is not SHA256")
    return value


def _field_tables() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    row = []
    for index, name in enumerate(ATOM_NAMES):
        row.append(
            {
                "field_id": f"normalized_atom_{index:02d}",
                "name": name,
                "unit": "training_scale_normalized_dimensionless",
                "formula": f"raw_atom[{index}]/training_scale[{index}]",
                "observation_unit": "candidate_row_with_pool_id_retained",
                "descriptive_value_count": 8000,
                "independent_n": 1000,
                "finite_required": True,
            }
        )
    for arm in ("static14d", "scene14d"):
        row.append(
            {
                "field_id": f"score_{arm}",
                "name": f"CAMP-{arm.title()} score",
                "unit": "dimensionless",
                "formula": "dot(clip(normalized_atoms,0,10),frozen_arm_weights)",
                "observation_unit": "candidate_row_with_pool_id_retained",
                "descriptive_value_count": 8000,
                "independent_n": 1000,
                "finite_required": True,
            }
        )
    pool = []
    for arm in ("static14d", "scene14d"):
        pool.extend(
            [
                {
                    "field_id": f"margin_{arm}",
                    "unit": "dimensionless",
                    "formula": (
                        "second_lowest_eligible_score-lowest_eligible_score;"
                        "requires_at_least_2_eligible_candidates"
                    ),
                    "observation_unit": "pool",
                    "value_count": 1000,
                    "independent_n": 1000,
                    "finite_required": True,
                },
                {
                    "field_id": f"eligible_count_{arm}",
                    "unit": "candidate_count",
                    "formula": "sum(strict_bool_eligibility_mask)",
                    "observation_unit": "pool",
                    "value_count": 1000,
                    "independent_n": 1000,
                    "finite_required": True,
                },
            ]
        )
    return row, pool


def _indices(count: int) -> dict[str, int]:
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("invalid quantile count")
    return {
        "q0_005_lower_index": int(math.floor(0.005 * (count - 1))),
        "q0_995_upper_index": int(math.ceil(0.995 * (count - 1))),
    }


def reference(values: Sequence[Any]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("reference preimage invalid")
    ordered = np.sort(array, kind="stable")
    idx = _indices(int(ordered.size))
    return {
        "count": int(ordered.size),
        **idx,
        "q0_005_lower": float(ordered[idx["q0_005_lower_index"]]),
        "q0_995_upper": float(ordered[idx["q0_995_upper_index"]]),
        "interval_inclusive": True,
    }


def _largest_remainder(
    counts: Mapping[tuple[str, str, str, str], int]
) -> dict[tuple[str, str, str, str], int]:
    ordered = sorted(counts)
    if not ordered or len(ordered) > 1000 or sum(counts.values()) < 1000:
        raise ValueError("review capacity failed")
    if any(type(counts[key]) is not int or counts[key] <= 0 for key in ordered):
        raise ValueError("review cell count invalid")
    quota = {key: 1 for key in ordered}
    remaining = 1000 - len(ordered)
    capacity = {key: counts[key] - 1 for key in ordered}
    denominator = sum(capacity.values())
    if remaining and denominator <= 0:
        raise ValueError("review capacity after minima failed")
    ideal = {
        key: (0.0 if remaining == 0 else remaining * capacity[key] / denominator)
        for key in ordered
    }
    for key in ordered:
        quota[key] += math.floor(ideal[key])
    extra = 1000 - sum(quota.values())
    order = sorted(
        ordered,
        key=lambda key: (-(ideal[key] - math.floor(ideal[key])), key),
    )
    for key in order[:extra]:
        quota[key] += 1
    if sum(quota.values()) != 1000:
        raise ValueError("review quota sum drifted")
    return quota


def review_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    if type(payload) is not dict or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("review contract schema drifted")
    if (
        payload.get("authority_canonical_json_exact") != AUTHORITY_JSON
        or payload.get("high_authority_sha256") != AUTHORITY_SHA256
        or _digest(AUTHORITY_JSON.encode("ascii")) != AUTHORITY_SHA256
        or _digest(_bytes(payload.get("high_authority"))[:-1]) != AUTHORITY_SHA256
    ):
        raise ValueError("review authority drifted")
    denominator = payload.get("denominator")
    if denominator != {
        "pool_count": 1000,
        "rows_per_pool": 8,
        "candidate_row_count": 8000,
        "formal_model_invocations": 1000,
        "selector_receipts_per_arm": 1000,
        "selector_receipt_total": 2000,
        "sampling_unit": "pool",
        "row_or_tick_independent_n_claimed": False,
    }:
        raise ValueError("review denominator drifted")
    manifest = payload.get("manifest_contract")
    if (
        type(manifest) is not dict
        or manifest.get("families") != list(FAMILIES)
        or manifest.get("risk_tiers") != list(TIERS)
        or manifest.get("route_geometry_bins") != list(GEOMETRY)
        or manifest.get("route_geometry_thresholds_rad") != [0.15, 0.75]
        or manifest.get("source_availability") != list(SOURCES)
        or manifest.get("zero_overlap_with") != list(OVERLAP_SPLITS)
        or manifest.get("no_drop_no_replace") is not True
    ):
        raise ValueError("review manifest contract drifted")
    row, pool = _field_tables()
    support = payload.get("support_field_contract")
    if (
        type(support) is not dict
        or support.get("row_fields") != row
        or support.get("pool_fields") != pool
        or support.get("field_count") != 20
        or support.get("row_reference_indices") != _indices(8000)
        or support.get("pool_reference_indices") != _indices(1000)
        or support.get("all_fields_required") is not True
        or support.get("weighted_total_created") is not False
    ):
        raise ValueError("review field contract drifted")
    pool_generation = payload.get("pool_generation_contract")
    if (
        type(pool_generation) is not dict
        or pool_generation.get("generator")
        != "new_single_invocation_batched_k8_candidate_pool"
        or pool_generation.get("same_ego_batch_size") != 8
        or pool_generation.get("agent_as_ego_batch") is not False
        or pool_generation.get("formal_model_calls_per_pool") != 1
        or pool_generation.get("candidate0_is_row0") is not True
        or pool_generation.get("candidate_tensor_immutable") is not True
    ):
        raise ValueError("review pool topology drifted")
    selector = payload.get("selector_contract")
    if (
        type(selector) is not dict
        or selector.get("arms") != ["Static14D", "Scene14D"]
        or selector.get("same_immutable_candidate_tensor") is not True
        or selector.get("post_pool_model_dp_latent_candidate_generation_calls") != 0
    ):
        raise ValueError("review selector topology drifted")
    if (
        payload.get("claim_authorized") is not False
        or payload.get("training_or_retraining_authorized") is not False
        or any(payload.get("prohibited_run_counts", {}).values())
    ):
        raise ValueError("review prohibition boundary drifted")
    return deepcopy(dict(payload))


def review_selected_manifest(
    manifest: Mapping[str, Any],
    *,
    eligible_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        type(manifest) is not dict
        or manifest.get("schema_version")
        != "camp_dp_v25_batch8_training_support_reference_input_manifest_v1"
        or manifest.get("authority_sha256") != AUTHORITY_SHA256
        or manifest.get("selected_pool_count") != 1000
        or manifest.get("candidate_row_count") != 8000
        or manifest.get("model_call_count") != 1000
        or manifest.get("selector_receipt_count") != 2000
        or manifest.get("no_drop_no_replace") is not True
    ):
        raise ValueError("review selected manifest header drifted")
    if _json_digest(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    ) != manifest.get("manifest_sha256"):
        raise ValueError("review selected manifest SHA drifted")
    cells: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for entry in eligible_entries:
        stratum = entry.get("stratum")
        key = (
            str(stratum.get("family")),
            str(stratum.get("risk_tier")),
            str(stratum.get("route_geometry")),
            str(stratum.get("source_availability")),
        )
        if (
            key[0] not in FAMILIES
            or key[1] not in TIERS
            or key[2] not in GEOMETRY
            or key[3] not in SOURCES
        ):
            raise ValueError("review eligible stratum invalid")
        cells[key].append(entry)
    clone_keys = [str(row.get("clone_key_sha256")) for row in eligible_entries]
    if (
        len(eligible_entries) < 1000
        or any(value != 1 for value in Counter(clone_keys).values())
        or set(FAMILIES) - {key[0] for key in cells}
    ):
        raise ValueError("review eligible manifest capacity invalid")
    quotas = _largest_remainder({key: len(value) for key, value in cells.items()})
    expected = []
    for key in sorted(cells):
        ordered = sorted(
            cells[key],
            key=lambda row: _digest(
                AUTHORITY_SHA256.encode("ascii")
                + bytes.fromhex(_sha(row.get("clone_key_sha256"), "clone"))
            ),
        )
        expected.extend(ordered[: quotas[key]])
    expected = sorted(
        expected,
        key=lambda row: _digest(
            AUTHORITY_SHA256.encode("ascii")
            + bytes.fromhex(_sha(row.get("clone_key_sha256"), "clone"))
        ),
    )
    actual = manifest.get("entries")
    if type(actual) is not list or len(actual) != 1000:
        raise ValueError("review manifest entry denominator invalid")
    if [row["clone_key_sha256"] for row in actual] != [
        row["clone_key_sha256"] for row in expected
    ]:
        raise ValueError("review selected manifest ordering drifted")
    for ordinal, row in enumerate(actual):
        if (
            row.get("pool_ordinal") != ordinal
            or row.get("pool_id") != f"training_support:{ordinal:04d}"
        ):
            raise ValueError("review pool ordinal/id drifted")
    return {
        "eligible_unique_pool_count": len(eligible_entries),
        "selected_pool_count": len(actual),
        "cell_count": len(cells),
        "family_count": len({key[0] for key in cells}),
    }
