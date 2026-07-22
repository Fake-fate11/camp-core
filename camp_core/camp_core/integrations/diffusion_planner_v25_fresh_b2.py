from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_calibration import validate_v25_calibration_contract
from .diffusion_planner_v25_route_signal_authority import (
    PHASE_AUTHORITY_MODES,
    validate_mapped_signal_chain,
)
from .diffusion_planner_v25_semantic_authority import validate_no_signal_chain
from .diffusion_planner_v25_split import (
    SPLIT_ROLES,
    validate_signal_complete_map_license,
    validate_v25_zero_overlap,
)
from .diffusion_planner_v25_statistics import (
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
    prospective_cluster_sensitivity,
)
from .diffusion_planner_v25_evaluation import (
    BENCHMARK_STRATA,
    NATURALISTIC_SCENARIO_FAMILY,
    NATURALISTIC_TIER,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FRESH_ROW_FIELDS = frozenset(
    {
        "source_family",
        "map_geometry_sha256",
        "map_file_sha256",
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "route_identity_sha256",
        "benchmark_stratum",
        "scenario_family",
        "tier",
        "signal_source_class",
        "phase_authority_mode",
        "source_chain",
        "route_length_m",
        "speed_source_sha256",
        "static_signal_chain_qualified",
        "runtime_same_tick_signal_receipt_required",
        "runtime_fixed_dp_k8_support_required",
        "preopen_dp_forward_executed",
        "outcome_fields_consumed",
    }
)
FROZEN_ROOT_BINDINGS = frozenset(
    {
        "training_artifact_root",
        "training_review_root",
        "calibration_artifact_root",
        "calibration_review_root",
        "noninferiority_freeze_root",
        "power_pilot_root",
        "scenario_manifest_root",
    }
)
TIERS = ("easy", "borderline", "high_risk")
FRESH_QUALIFICATION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "fixed_dp_head",
        "frozen_root_bindings",
        "calibration_contract_root_sha256",
        "calibration_contract_status",
        "zero_overlap_receipt",
        "map_license_receipt",
        "power_pilot_receipt",
        "fresh_row_count",
        "independent_unit_counts",
        "signal_source_class_counts",
        "benchmark_stratum_counts",
        "phase_authority_mode_counts",
        "family_tier_counts",
        "target_minimum_corridors",
        "target_minimum_routes",
        "real_inventory_ceiling_below_target",
        "safety_cost_power",
        "red_component_power",
        "seed_or_tick_counted_as_independent",
        "certified_signal_safety_source_required",
        "phase_remaining_available_without_v2i",
        "fresh_b_v1_superseded_before_opening",
        "fresh_open_authorized",
        "one_time_opening_release_required",
        "fresh_b2_opened",
        "outcome_fields_consumed",
        "claim_scope",
    }
)
POWER_PILOT_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "source_artifact_root_sha256",
        "source_split",
        "calibration_arm",
        "cluster_estimator",
        "variance_target",
        "safety_cost_cluster_standard_deviation",
        "red_component_cluster_standard_deviation",
        "total_independent_cluster_count",
        "red_independent_cluster_count",
        "camp_method_outcomes_consumed",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
)
_INDEPENDENT_COUNT_FIELDS = frozenset(
    {
        "source_families",
        "map_geometries",
        "intersections",
        "corridors",
        "route_identities",
        "semantic_parameter_blocks",
        "total_power_clusters",
        "red_power_clusters",
    }
)
_ZERO_OVERLAP_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "row_count",
        "split_row_counts",
        "independent_unit_counts",
        "source_family_strata",
        "same_route_all_seeds_one_split",
        "map_export_clones_deduplicated_by_geometry_sha",
        "semantic_clones_deduplicated_independent_of_source",
        "identity_fields_used_as_model_features",
        "fresh_outcome_consumed",
    }
)
_SPLIT_UNIT_FIELDS = frozenset(
    {
        "map",
        "intersection",
        "corridor",
        "route_family",
        "semantic_parameter_block",
        "seed_namespace",
        "route_identity",
    }
)
_MAP_LICENSE_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "map_file_count",
        "unique_geometry_count",
        "source_kind_counts",
        "all_licenses_affirmative",
        "fresh_outcome_consumed",
    }
)


def qualify_fresh_b2_preopen(
    *,
    split_rows: Sequence[Mapping[str, Any]],
    map_license_rows: Sequence[Mapping[str, Any]],
    fresh_rows: Sequence[Mapping[str, Any]],
    frozen_root_bindings: Mapping[str, str],
    calibration_contract: Mapping[str, Any],
    calibration_contract_root_sha256: str,
    power_pilot_receipt: Mapping[str, Any],
    target_effect: float | None = None,
) -> dict[str, Any]:
    """Qualify a source-complete Fresh B2 manifest without opening outcomes."""

    roots = _validate_roots(frozen_root_bindings)
    _require_sha(calibration_contract_root_sha256, "calibration_contract_root_sha256")
    if calibration_contract_root_sha256 != roots["noninferiority_freeze_root"]:
        raise ValueError("Fresh B2 calibration freeze root binding drifted")
    calibration = validate_v25_calibration_contract(calibration_contract)
    if (
        calibration["status"] != "calibration_freeze_passed"
        or calibration["fixed_dp_head"] != FIXED_DP_HEAD
        or calibration["fresh_preopen_qualification_allowed"] is not True
        or calibration["fresh_open_authorized"] is not False
        or calibration["one_time_opening_release_required"] is not True
        or calibration["fresh_b2_opened"] is not False
        or calibration["fresh_outcome_fields_consumed"] != []
    ):
        raise ValueError("Fresh B2 requires an eligible unopened calibration freeze")
    pilot = _validate_power_pilot_receipt(
        power_pilot_receipt,
        expected_root_sha256=roots["power_pilot_root"],
    )
    split_receipt = validate_v25_zero_overlap(split_rows)
    license_receipt = validate_signal_complete_map_license(map_license_rows)
    rows = [_validate_fresh_row(row, index) for index, row in enumerate(fresh_rows)]
    if not rows:
        raise ValueError("Fresh B2 qualification rows must be nonempty")

    fresh_split_rows = [row for row in split_rows if row.get("split") == "fresh_b2"]
    split_routes = {str(row["route_identity_sha256"]) for row in fresh_split_rows}
    qualification_routes = {row["route_identity_sha256"] for row in rows}
    if split_routes != qualification_routes:
        raise ValueError("Fresh B2 qualification routes do not match frozen split")
    split_by_route = {
        str(row["route_identity_sha256"]): row for row in fresh_split_rows
    }
    if len(split_by_route) != len(fresh_split_rows):
        raise ValueError("Fresh B2 split route identities are duplicated")

    licenses = {
        (str(row["map_file_sha256"]), str(row["map_geometry_sha256"]))
        for row in map_license_rows
    }
    family_tiers: Counter[tuple[str, str]] = Counter()
    source_classes: Counter[str] = Counter()
    benchmark_strata: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    cluster_keys: set[tuple[str, str]] = set()
    red_clusters: set[tuple[str, str]] = set()
    for row in rows:
        split = split_by_route[row["route_identity_sha256"]]
        for field in (
            "source_family",
            "map_geometry_sha256",
            "intersection_sha256",
            "corridor_sha256",
            "route_family_sha256",
            "semantic_parameter_block_sha256",
            "scenario_family",
        ):
            if row[field] != split[field]:
                raise ValueError(f"Fresh B2 qualification/split {field} drifted")
        if (row["map_file_sha256"], row["map_geometry_sha256"]) not in licenses:
            raise ValueError("Fresh B2 map lacks an affirmative license binding")
        chain = row["source_chain"]
        if row["signal_source_class"] == "mapped_signal":
            validated = validate_mapped_signal_chain(chain)
            if (
                row["phase_authority_mode"] not in PHASE_AUTHORITY_MODES
                or validated["phase_authority_mode"] != row["phase_authority_mode"]
                or validated["route_identity_sha256"]
                != row["route_identity_sha256"]
                or validated["source_map_sha256"] != row["map_file_sha256"]
                or row["intersection_sha256"] is None
            ):
                raise ValueError("Fresh B2 mapped signal source chain drifted")
            cluster = (row["map_geometry_sha256"], row["intersection_sha256"])
            modes[row["phase_authority_mode"]] += 1
        else:
            validated = validate_no_signal_chain(chain)
            if (
                row["phase_authority_mode"] is not None
                or validated["route_identity_sha256"]
                != row["route_identity_sha256"]
                or validated["source_map_sha256"] != row["map_file_sha256"]
            ):
                raise ValueError("Fresh B2 no-signal source chain drifted")
            cluster = (row["map_geometry_sha256"], row["corridor_sha256"])
        cluster_keys.add(cluster)
        if row["scenario_family"] == "red_light_phase_timing":
            if row["signal_source_class"] != "mapped_signal":
                raise ValueError("Fresh B2 red-light family must be signal-complete")
            red_clusters.add(cluster)
        family_tiers[(row["scenario_family"], row["tier"])] += 1
        source_classes[row["signal_source_class"]] += 1
        benchmark_strata[row["benchmark_stratum"]] += 1

    if set(benchmark_strata) != set(BENCHMARK_STRATA):
        raise ValueError("Fresh B2 requires naturalistic and controlled-stress strata")

    missing_cells = [
        f"{family}/{tier}"
        for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
        for tier in TIERS
        if family_tiers[(family, tier)] == 0
    ]
    if missing_cells:
        raise ValueError(f"Fresh B2 family/tier coverage is incomplete: {missing_cells}")
    if len(cluster_keys) < 2 or len(red_clusters) < 2:
        raise ValueError("Fresh B2 power requires at least two total and red clusters")

    counts = {
        "source_families": len({row["source_family"] for row in rows}),
        "map_geometries": len({row["map_geometry_sha256"] for row in rows}),
        "intersections": len(
            {
                (row["map_geometry_sha256"], row["intersection_sha256"])
                for row in rows
                if row["intersection_sha256"] is not None
            }
        ),
        "corridors": len(
            {(row["map_geometry_sha256"], row["corridor_sha256"]) for row in rows}
        ),
        "route_identities": len(qualification_routes),
        "semantic_parameter_blocks": len(
            {row["semantic_parameter_block_sha256"] for row in rows}
        ),
        "total_power_clusters": len(cluster_keys),
        "red_power_clusters": len(red_clusters),
    }
    limited = counts["corridors"] < 25 or counts["route_identities"] < 100
    result = {
        "schema_version": "camp_dp_v25_fresh_b2_preopen_qualification_v1",
        "status": (
            "qualified_with_real_inventory_ceiling_disclosed"
            if limited
            else "qualified"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "frozen_root_bindings": roots,
        "calibration_contract_root_sha256": calibration_contract_root_sha256,
        "calibration_contract_status": calibration["status"],
        "zero_overlap_receipt": split_receipt,
        "map_license_receipt": license_receipt,
        "power_pilot_receipt": pilot,
        "fresh_row_count": len(rows),
        "independent_unit_counts": counts,
        "signal_source_class_counts": dict(sorted(source_classes.items())),
        "benchmark_stratum_counts": dict(sorted(benchmark_strata.items())),
        "phase_authority_mode_counts": dict(sorted(modes.items())),
        "family_tier_counts": {
            f"{family}/{tier}": family_tiers[(family, tier)]
            for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
            for tier in TIERS
        },
        "target_minimum_corridors": 25,
        "target_minimum_routes": 100,
        "real_inventory_ceiling_below_target": limited,
        "safety_cost_power": prospective_cluster_sensitivity(
            pilot["safety_cost_cluster_standard_deviation"],
            len(cluster_keys),
            target_effect=target_effect,
        ),
        "red_component_power": prospective_cluster_sensitivity(
            pilot["red_component_cluster_standard_deviation"],
            len(red_clusters),
            target_effect=target_effect,
        ),
        "seed_or_tick_counted_as_independent": False,
        "certified_signal_safety_source_required": True,
        "phase_remaining_available_without_v2i": False,
        "fresh_b_v1_superseded_before_opening": True,
        "fresh_open_authorized": False,
        "one_time_opening_release_required": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "claim_scope": "specific_signal_complete_benchmark_and_fixed_dp_valid_k8_support_domain",
    }
    return validate_fresh_b2_preopen_qualification(result)


def validate_fresh_b2_preopen_qualification(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Strictly reopen the outcome-blind Fresh B2 pre-open decision."""

    if type(value) is not dict or set(value) != FRESH_QUALIFICATION_FIELDS:
        raise ValueError("Fresh B2 qualification field set drifted")
    result = dict(value)
    roots = _validate_roots(result["frozen_root_bindings"])
    _require_sha(
        result["calibration_contract_root_sha256"],
        "calibration_contract_root_sha256",
    )
    exact = {
        "schema_version": "camp_dp_v25_fresh_b2_preopen_qualification_v1",
        "fixed_dp_head": FIXED_DP_HEAD,
        "calibration_contract_status": "calibration_freeze_passed",
        "target_minimum_corridors": 25,
        "target_minimum_routes": 100,
        "seed_or_tick_counted_as_independent": False,
        "certified_signal_safety_source_required": True,
        "phase_remaining_available_without_v2i": False,
        "fresh_b_v1_superseded_before_opening": True,
        "fresh_open_authorized": False,
        "one_time_opening_release_required": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "claim_scope": (
            "specific_signal_complete_benchmark_and_fixed_dp_valid_k8_support_domain"
        ),
    }
    if any(not _strict_json_equal(result.get(name), expected) for name, expected in exact.items()):
        raise ValueError("Fresh B2 qualification exact value drifted")
    if result["calibration_contract_root_sha256"] != roots["noninferiority_freeze_root"]:
        raise ValueError("Fresh B2 qualification calibration root drifted")

    counts = result["independent_unit_counts"]
    if (
        type(counts) is not dict
        or set(counts) != _INDEPENDENT_COUNT_FIELDS
        or any(type(item) is not int or item < 0 for item in counts.values())
        or counts["total_power_clusters"] < 2
        or counts["red_power_clusters"] < 2
    ):
        raise ValueError("Fresh B2 independent-unit counts drifted")
    row_count = result["fresh_row_count"]
    if type(row_count) is not int or row_count < 1:
        raise ValueError("Fresh B2 qualification row count is invalid")
    limited = bool(counts["corridors"] < 25 or counts["route_identities"] < 100)
    expected_status = (
        "qualified_with_real_inventory_ceiling_disclosed" if limited else "qualified"
    )
    if (
        result["status"] != expected_status
        or result["real_inventory_ceiling_below_target"] is not limited
    ):
        raise ValueError("Fresh B2 inventory-ceiling status drifted")

    family_tiers = result["family_tier_counts"]
    expected_family_tiers = {
        f"{family}/{tier}"
        for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
        for tier in TIERS
    }
    if (
        type(family_tiers) is not dict
        or set(family_tiers) != expected_family_tiers
        or any(type(item) is not int or item < 1 for item in family_tiers.values())
    ):
        raise ValueError("Fresh B2 family/tier coverage drifted")
    strata = result["benchmark_stratum_counts"]
    controlled_count = sum(family_tiers.values())
    if (
        type(strata) is not dict
        or set(strata) != set(BENCHMARK_STRATA)
        or any(type(item) is not int or item < 1 for item in strata.values())
        or strata["controlled_stress"] != controlled_count
        or sum(strata.values()) != row_count
    ):
        raise ValueError("Fresh B2 benchmark-stratum accounting drifted")
    for name in ("signal_source_class_counts", "phase_authority_mode_counts"):
        mapping = result[name]
        if (
            type(mapping) is not dict
            or not mapping
            or any(type(key) is not str or not key for key in mapping)
            or any(type(item) is not int or item < 1 for item in mapping.values())
        ):
            raise ValueError(f"Fresh B2 {name} drifted")
    if sum(result["signal_source_class_counts"].values()) != row_count:
        raise ValueError("Fresh B2 signal-source denominator drifted")

    _validate_zero_overlap_receipt(result["zero_overlap_receipt"], row_count)
    _validate_map_license_receipt(result["map_license_receipt"])
    pilot = _validate_power_pilot_receipt(
        result["power_pilot_receipt"],
        expected_root_sha256=roots["power_pilot_root"],
    )
    safety_power = _validate_power_receipt(
        result["safety_cost_power"], counts["total_power_clusters"]
    )
    red_power = _validate_power_receipt(
        result["red_component_power"], counts["red_power_clusters"]
    )
    if not _strict_json_equal(safety_power["target_effect"], red_power["target_effect"]):
        raise ValueError("Fresh B2 total/red target effect drifted")
    if (
        safety_power["cluster_standard_deviation"]
        != pilot["safety_cost_cluster_standard_deviation"]
        or red_power["cluster_standard_deviation"]
        != pilot["red_component_cluster_standard_deviation"]
    ):
        raise ValueError("Fresh B2 power variance differs from the sealed pilot")
    return result


def _validate_fresh_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    if type(row) is not dict or set(row) != FRESH_ROW_FIELDS:
        raise ValueError(f"Fresh B2 row {index} field set drifted")
    result = dict(row)
    for field in (
        "source_family",
        "map_geometry_sha256",
        "map_file_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "route_identity_sha256",
        "scenario_family",
        "tier",
        "benchmark_stratum",
        "signal_source_class",
        "speed_source_sha256",
    ):
        if type(result[field]) is not str or not result[field]:
            raise ValueError(f"Fresh B2 row {index} {field} is invalid")
    for field in (
        "map_geometry_sha256",
        "map_file_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "route_identity_sha256",
        "speed_source_sha256",
    ):
        _require_sha(result[field], field)
    if result["intersection_sha256"] is not None:
        _require_sha(result["intersection_sha256"], "intersection_sha256")
    if result["benchmark_stratum"] not in BENCHMARK_STRATA:
        raise ValueError("Fresh B2 benchmark stratum is invalid")
    if result["benchmark_stratum"] == "naturalistic":
        if (
            result["scenario_family"] != NATURALISTIC_SCENARIO_FAMILY
            or result["tier"] != NATURALISTIC_TIER
        ):
            raise ValueError("Fresh B2 naturalistic metadata drifted")
    elif (
        result["scenario_family"] not in REQUIRED_CONTROLLED_EVENT_FAMILIES
        or result["tier"] not in TIERS
    ):
        raise ValueError("Fresh B2 controlled scenario metadata drifted")
    if result["signal_source_class"] not in {"mapped_signal", "no_signal"}:
        raise ValueError("Fresh B2 signal source class is invalid")
    if (
        type(result["route_length_m"]) not in (int, float)
        or not np.isfinite(float(result["route_length_m"]))
        or float(result["route_length_m"]) <= 0.0
        or result["static_signal_chain_qualified"] is not True
        or result["runtime_same_tick_signal_receipt_required"] is not True
        or result["runtime_fixed_dp_k8_support_required"] is not True
        or result["preopen_dp_forward_executed"] is not False
        or result["outcome_fields_consumed"] != []
        or not isinstance(result["source_chain"], Mapping)
    ):
        raise ValueError("Fresh B2 route/source qualification values are invalid")
    return result


def validate_fresh_b2_manifest_row(
    row: Mapping[str, Any], *, index: int = 0
) -> dict[str, Any]:
    """Public exact-schema validator used by the one-shot execution layer."""

    if type(index) is not int or index < 0:
        raise ValueError("Fresh B2 manifest row index must be a nonnegative int")
    return _validate_fresh_row(row, index)


def _validate_roots(value: Mapping[str, str]) -> dict[str, str]:
    if type(value) is not dict or set(value) != FROZEN_ROOT_BINDINGS:
        raise ValueError("Fresh B2 frozen root binding keyset drifted")
    result = dict(value)
    for name, digest in result.items():
        _require_sha(digest, name)
    return result


def _validate_power_receipt(
    value: Mapping[str, Any], independent_cluster_count: int
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("Fresh B2 power receipt must be a dict")
    for name in (
        "confidence",
        "power",
        "cluster_standard_deviation",
        "expected_two_sided_ci_half_width",
        "normal_approximation_mde",
    ):
        item = value.get(name)
        if type(item) is not float or not np.isfinite(item):
            raise ValueError(f"Fresh B2 power receipt {name} drifted")
    target_effect = value.get("target_effect")
    if target_effect is not None and (
        type(target_effect) is not float
        or not np.isfinite(target_effect)
        or target_effect <= 0.0
    ):
        raise ValueError("Fresh B2 power receipt target_effect drifted")
    expected = prospective_cluster_sensitivity(
        value["cluster_standard_deviation"],
        independent_cluster_count,
        confidence=value["confidence"],
        power=value["power"],
        target_effect=target_effect,
    )
    if not _strict_json_equal(value, expected):
        raise ValueError("Fresh B2 power receipt does not independently recompute")
    return expected


def _validate_power_pilot_receipt(
    value: Mapping[str, Any], *, expected_root_sha256: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != POWER_PILOT_RECEIPT_FIELDS:
        raise ValueError("Fresh B2 power pilot receipt field set drifted")
    _require_sha(expected_root_sha256, "power_pilot_root")
    result = dict(value)
    exact = {
        "schema_version": "camp_dp_v25_power_pilot_variance_receipt_v1",
        "status": "sealed_train_or_calibration_pilot_variance",
        "source_artifact_root_sha256": expected_root_sha256,
        "calibration_arm": "candidate0_operational_default",
        "cluster_estimator": "equal_mass_independent_cluster_standard_deviation",
        "variance_target": "candidate0_safety_cost_proxy_disclosed_not_paired_delta",
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if any(not _strict_json_equal(result.get(name), expected) for name, expected in exact.items()):
        raise ValueError("Fresh B2 power pilot receipt exact value drifted")
    if result["source_split"] not in {"train_pilot", "calibration_pilot"}:
        raise ValueError("Fresh B2 power pilot source split drifted")
    for name in (
        "safety_cost_cluster_standard_deviation",
        "red_component_cluster_standard_deviation",
    ):
        item = result[name]
        if type(item) is not float or not np.isfinite(item) or item < 0.0:
            raise ValueError(f"Fresh B2 power pilot {name} drifted")
    for name in ("total_independent_cluster_count", "red_independent_cluster_count"):
        item = result[name]
        if type(item) is not int or item < 2:
            raise ValueError(f"Fresh B2 power pilot {name} drifted")
    return result


def _validate_zero_overlap_receipt(
    value: Mapping[str, Any], fresh_row_count: int
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ZERO_OVERLAP_RECEIPT_FIELDS:
        raise ValueError("Fresh B2 zero-overlap receipt field set drifted")
    exact = {
        "schema_version": "camp_dp_v25_zero_overlap_receipt_v1",
        "status": "passed",
        "same_route_all_seeds_one_split": True,
        "map_export_clones_deduplicated_by_geometry_sha": True,
        "semantic_clones_deduplicated_independent_of_source": True,
        "identity_fields_used_as_model_features": False,
        "fresh_outcome_consumed": False,
    }
    if any(not _strict_json_equal(value[name], expected) for name, expected in exact.items()):
        raise ValueError("Fresh B2 zero-overlap receipt value drifted")
    row_count = value["row_count"]
    split_counts = value["split_row_counts"]
    if (
        type(row_count) is not int
        or row_count < fresh_row_count + 2
        or type(split_counts) is not dict
        or set(split_counts) != set(SPLIT_ROLES)
        or any(type(item) is not int or item < 1 for item in split_counts.values())
        or sum(split_counts.values()) != row_count
        or split_counts["fresh_b2"] != fresh_row_count
    ):
        raise ValueError("Fresh B2 zero-overlap split accounting drifted")
    units = value["independent_unit_counts"]
    if type(units) is not dict or set(units) != _SPLIT_UNIT_FIELDS:
        raise ValueError("Fresh B2 zero-overlap unit fields drifted")
    for name, counts in units.items():
        if (
            type(counts) is not dict
            or set(counts) != set(SPLIT_ROLES)
            or any(type(item) is not int or item < 0 for item in counts.values())
            or (name != "intersection" and any(item < 1 for item in counts.values()))
        ):
            raise ValueError("Fresh B2 zero-overlap unit accounting drifted")
    if units["route_identity"]["fresh_b2"] != fresh_row_count:
        raise ValueError("Fresh B2 zero-overlap route denominator drifted")
    strata = value["source_family_strata"]
    if (
        type(strata) is not dict
        or set(strata) != set(SPLIT_ROLES)
        or any(
            type(items) is not list
            or not items
            or len(set(items)) != len(items)
            or any(type(item) is not str or not item for item in items)
            for items in strata.values()
        )
    ):
        raise ValueError("Fresh B2 zero-overlap source strata drifted")
    return dict(value)


def _validate_map_license_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _MAP_LICENSE_RECEIPT_FIELDS:
        raise ValueError("Fresh B2 map-license receipt field set drifted")
    exact = {
        "schema_version": "camp_dp_v25_signal_complete_map_license_receipt_v1",
        "status": "passed",
        "all_licenses_affirmative": True,
        "fresh_outcome_consumed": False,
    }
    if any(not _strict_json_equal(value[name], expected) for name, expected in exact.items()):
        raise ValueError("Fresh B2 map-license receipt value drifted")
    file_count = value["map_file_count"]
    geometry_count = value["unique_geometry_count"]
    source_counts = value["source_kind_counts"]
    if (
        type(file_count) is not int
        or file_count < 1
        or type(geometry_count) is not int
        or not 1 <= geometry_count <= file_count
        or type(source_counts) is not dict
        or not source_counts
        or any(type(name) is not str or not name for name in source_counts)
        or any(type(item) is not int or item < 1 for item in source_counts.values())
        or sum(source_counts.values()) != file_count
    ):
        raise ValueError("Fresh B2 map-license receipt accounting drifted")
    return dict(value)


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right)
        )
    return bool(left == right)


def _require_sha(value: Any, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
