from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_fresh_coverage import (
    build_fresh_b2_explicit_coverage,
    validate_fresh_b2_explicit_coverage,
)
from .diffusion_planner_v25_fresh_preopen_authority import (
    project_train_split_rows,
)
from .diffusion_planner_v25_fresh_storage import validate_storage_manifest
from .diffusion_planner_v25_holdout_contract import (
    ARMS,
    SCIENTIFIC_TERMINAL_STATUSES,
    canonical_sha256,
    freeze_experiment_protocol,
    freeze_holdout_identity,
    strict_equal,
    validate_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_holdout_failure_closeout import (
    validate_consumed_holdout_failure_closeout,
)
from .diffusion_planner_v25_holdout_preflight import (
    validate_production_composition_preflight,
)
from .diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
    validate_signal_complete_suite_receipt,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)
from .diffusion_planner_v25_signal_complete_preopen import (
    project_holdout_qualification_rows,
    project_signal_complete_license_rows,
    project_signal_complete_split_rows,
)
from .diffusion_planner_v25_split import validate_v25_holdout_zero_overlap
from .diffusion_planner_v25_split import validate_signal_complete_map_license


SCHEMA_VERSION = "camp_dp_v25_fresh_b3_consolidated_preopen_authority_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_COUNTS = {
    "map_count": 25,
    "intersection_count": 100,
    "corridor_count": 100,
    "route_count": 100,
    "semantic_block_count": 100,
    "seed_count": 5,
    "paired_unit_count": 500,
    "arm_run_count": 1500,
    "tick_capacity": 96_000,
}

PROTOCOL_ASSET_FIELDS = frozenset(
    {
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_contract_sha256",
        "threshold_contract_sha256",
        "noninferiority_contract_sha256",
        "multiplicity_contract_sha256",
        "claim_contract_sha256",
        "failure_contract_sha256",
    }
)

AUTHORITY_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "implementation_head",
        "fixed_dp_head",
        "critical_implementation_manifest",
        "upstream_bindings",
        "holdout_identity",
        "experiment_protocol",
        "b2_consumed_failure",
        "b2_consumed_failure_review",
        "production_composition_preflight",
        "production_composition_preflight_review",
        "materialized_inventory",
        "map_suite",
        "map_license_rows",
        "route_assets",
        "execution_plan",
        "runtime_qualification_rows",
        "coverage",
        "zero_overlap",
        "power",
        "evaluation",
        "storage",
        "capacity",
        "atom_mechanism",
        "fresh_b1_disposition",
        "one_time_state",
        "preopen_model_loaded",
        "preopen_dp_forward_executed",
        "fresh_open_authorized",
        "fresh_b3_opened",
        "outcome_fields_consumed",
        "authority_payload_sha256",
    }
)


def build_b3_preopen_authority(
    *,
    implementation_head: str,
    critical_implementation_manifest: Mapping[str, Any],
    upstream_bindings: Mapping[str, Mapping[str, str]],
    train_source_rows: Sequence[Mapping[str, Any]],
    calibration_plan: Mapping[str, Any],
    b2_plan: Mapping[str, Any],
    b3_suite: Mapping[str, Any],
    b3_plan: Mapping[str, Any],
    b3_map_artifact: Path,
    route_asset_manifest: Mapping[str, Any],
    license_sha256: str,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
    protocol_assets: Mapping[str, str],
    b2_consumed_failure: Mapping[str, Any],
    b2_consumed_failure_review: Mapping[str, Any],
    production_composition_preflight: Mapping[str, Any],
    production_composition_preflight_review: Mapping[str, Any],
    power: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    storage_manifest: Mapping[str, Any],
    storage_binding: Mapping[str, Any],
    storage_review_binding: Mapping[str, Any],
    atom_mechanism_binding: Mapping[str, Any],
    atom_mechanism_review_binding: Mapping[str, Any],
    free_bytes_before: int,
    output_parent: Path,
    cas_tombstone_exists: bool,
) -> dict[str, Any]:
    _require_git_head(implementation_head, "implementation_head")
    if type(cas_tombstone_exists) is not bool or cas_tombstone_exists:
        raise ValueError("Fresh B3 holdout identity is already reserved or consumed")
    manifest = _critical_manifest(critical_implementation_manifest)
    bindings = _bindings(upstream_bindings)
    suite = validate_signal_complete_suite(b3_suite)
    plan = validate_signal_complete_execution_plan(b3_plan)
    calibration = validate_signal_complete_execution_plan(calibration_plan)
    consumed_b2 = validate_signal_complete_execution_plan(b2_plan)
    if (
        suite["split"] != "fresh_b3"
        or plan["split"] != "fresh_b3"
        or calibration["split"] != "calibration"
        or consumed_b2["split"] != "fresh_b2"
        or plan["source_family"] == calibration["source_family"]
        or plan["source_family"] == consumed_b2["source_family"]
    ):
        raise ValueError("Fresh B3 split/source-family authority drifted")
    counts = _counts(plan)
    identity = build_b3_holdout_identity(suite=suite, plan=plan)
    assets = _protocol_assets(protocol_assets)
    protocol = build_b3_experiment_protocol(assets)
    b2_closeout = validate_consumed_holdout_failure_closeout(
        b2_consumed_failure
    )
    if b2_closeout["raw_outcome_values_inspected"] is not False:
        raise ValueError("Fresh B2 values cannot influence B3")
    preflight = validate_production_composition_preflight(
        production_composition_preflight
    )
    if (
        preflight["holdout_identity"]["holdout_identity_sha256"]
        != identity["holdout_identity_sha256"]
        or preflight["experiment_protocol"]["experiment_protocol_sha256"]
        != protocol["experiment_protocol_sha256"]
    ):
        raise ValueError("Fresh B3 production preflight authority drifted")
    _review_binding(
        b2_consumed_failure_review,
        source_root_sha256=bindings["b2_consumed_failure"]["root_sha256"],
        expected_status="passed_independent_consumed_holdout_failure_review",
        label="B2 failure review",
    )
    _review_binding(
        production_composition_preflight_review,
        source_root_sha256=bindings["production_composition_preflight"][
            "root_sha256"
        ],
        expected_status=(
            "passed_independent_production_composition_preflight_review"
        ),
        label="production preflight review",
    )
    qualification_rows = project_holdout_qualification_rows(
        plan,
        prepared_runtime_cases=prepared_runtime_cases,
        expected_split="fresh_b3",
    )
    coverage = _normalize_coverage(
        build_fresh_b2_explicit_coverage(
            plan, prepared_runtime_cases=prepared_runtime_cases
        )
    )
    split_rows = (
        project_train_split_rows(train_source_rows)
        + project_signal_complete_split_rows(calibration)
        + project_signal_complete_split_rows(consumed_b2)
        + project_signal_complete_split_rows(plan)
    )
    zero_overlap = validate_v25_holdout_zero_overlap(split_rows)
    license_rows = project_signal_complete_license_rows(
        suite,
        map_artifact=b3_map_artifact,
        license_sha256=license_sha256,
    )
    route_assets = json.loads(json.dumps(route_asset_manifest))
    if (
        type(route_assets) is not dict
        or route_assets.get("schema_version")
        != "camp_dp_v25_signal_complete_route_assets_v1"
        or route_assets.get("status")
        != "materialized_signal_complete_fixed_dp_routes"
        or route_assets.get("split") != "fresh_b3"
        or route_assets.get("route_count") != counts["route_count"]
        or route_assets.get("map_count") != counts["map_count"]
        or type(route_assets.get("route_assets")) is not list
        or len(route_assets["route_assets"]) != counts["route_count"]
        or route_assets.get("fixed_dp_modified") is not False
        or route_assets.get("map_semantics_modified") is not False
        or route_assets.get("model_loaded") is not False
        or route_assets.get("candidate_generation_executed") is not False
        or route_assets.get("fresh_b2_opened") is not False
        or route_assets.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B3 route asset manifest drifted")
    storage = validate_storage_manifest(storage_manifest)
    capacity = _capacity(
        storage,
        free_bytes_before=free_bytes_before,
        output_parent=output_parent,
    )
    state = {
        "schema_version": "camp_dp_v25_fresh_b3_unopened_state_v1",
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "cas_tombstone_exists": False,
        "nonce_created": False,
        "opening_release_created": False,
        "execution_output_created": False,
        "outcome_files_created_or_read": False,
        "fresh_b3_opened": False,
        "second_opening_allowed": False,
        "outcome_fields_consumed": [],
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b3_preopen_authority",
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest": manifest,
        "upstream_bindings": bindings,
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "b2_consumed_failure": _artifact_binding(
            bindings["b2_consumed_failure"],
            b2_consumed_failure["closeout_payload_sha256"],
        ),
        "b2_consumed_failure_review": dict(b2_consumed_failure_review),
        "production_composition_preflight": _artifact_binding(
            bindings["production_composition_preflight"],
            preflight["preflight_payload_sha256"],
        ),
        "production_composition_preflight_review": dict(
            production_composition_preflight_review
        ),
        "materialized_inventory": {
            **counts,
            "source_family": plan["source_family"],
            "license_spdx": "MIT",
            "project_authored": True,
            "immutable_map_file_count": len(license_rows),
            "map_file_sha256": sorted(
                row["map_file_sha256"] for row in license_rows
            ),
            "map_geometry_sha256": sorted(
                row["map_geometry_sha256"] for row in license_rows
            ),
        },
        "map_suite": suite,
        "map_license_rows": license_rows,
        "route_assets": route_assets,
        "execution_plan": plan,
        "runtime_qualification_rows": qualification_rows,
        "coverage": coverage,
        "zero_overlap": zero_overlap,
        "power": json.loads(json.dumps(power)),
        "evaluation": json.loads(json.dumps(evaluation)),
        "storage": storage,
        "capacity": capacity,
        "atom_mechanism": {
            "source": _binding(atom_mechanism_binding, "atom mechanism"),
            "review": _binding(
                atom_mechanism_review_binding, "atom mechanism review"
            ),
            "used_for_model_or_protocol_change": False,
            "mechanism_association_only": True,
        },
        "fresh_b1_disposition": {
            "status": "superseded_before_opening",
            "machine_root_reopenable": False,
            "root_reconstructed_or_fabricated": False,
            "materialized_row_count": 0,
        },
        "one_time_state": state,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_open_authorized": False,
        "fresh_b3_opened": False,
        "outcome_fields_consumed": [],
    }
    result["authority_payload_sha256"] = canonical_sha256(result)
    return validate_b3_preopen_authority(result)


def build_b3_holdout_identity(
    *,
    suite: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    suite_value = (
        validate_signal_complete_suite(suite)
        if "map_payloads" in suite
        else validate_signal_complete_suite_receipt(suite)
    )
    plan_value = validate_signal_complete_execution_plan(plan)
    if suite_value["split"] != "fresh_b3" or plan_value["split"] != "fresh_b3":
        raise ValueError("Fresh B3 identity requires the frozen B3 suite and plan")
    counts = _counts(plan_value)
    return freeze_holdout_identity(
        split="fresh_b3",
        scenario_manifest_sha256=canonical_sha256(plan_value["identities"]),
        map_suite_payload_sha256=canonical_sha256(suite_value),
        route_census_sha256=canonical_sha256(
            sorted(
                row["route_identity_sha256"]
                for row in plan_value["identities"]
            )
        ),
        corridor_census_sha256=canonical_sha256(
            sorted(row["corridor_sha256"] for row in plan_value["identities"])
        ),
        semantic_census_sha256=canonical_sha256(
            sorted(
                row["semantic_parameter_block_sha256"]
                for row in plan_value["identities"]
            )
        ),
        execution_plan_sha256=canonical_sha256(plan_value),
        seeds=plan_value["seeds"],
        arm_order_commit_sha256=canonical_sha256(
            [
                {
                    "unit_ordinal": row["unit_ordinal"],
                    "unit_sha256": row["unit_sha256"],
                    "ordered_arms": row["ordered_arms"],
                }
                for row in plan_value["execution_units"]
            ]
        ),
        paired_unit_count=counts["paired_unit_count"],
        arm_run_count=counts["arm_run_count"],
        tick_capacity=counts["tick_capacity"],
    )


def build_b3_experiment_protocol(
    protocol_assets: Mapping[str, str],
) -> dict[str, Any]:
    assets = _protocol_assets(protocol_assets)
    return freeze_experiment_protocol(
        **assets,
        candidate0_semantics=(
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        same_forward_contract="forward_execution_id_plus_input_model_action_digest",
        latency_contract=(
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        terminal_truth_table="exclusive_scientific_terminal_or_artifact_fatal_v1",
    )


def validate_b3_preopen_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != AUTHORITY_FIELDS:
        raise ValueError("Fresh B3 preopen authority field set drifted")
    identity = validate_holdout_identity(value["holdout_identity"])
    protocol = validate_experiment_protocol(value["experiment_protocol"])
    plan = validate_signal_complete_execution_plan(value["execution_plan"])
    suite = _validate_b3_map_suite_receipt(value["map_suite"])
    if (
        identity["split"] != "fresh_b3"
        or plan["split"] != "fresh_b3"
        or suite["split"] != "fresh_b3"
        or identity["execution_plan_sha256"] != canonical_sha256(plan)
        or identity["map_suite_payload_sha256"] != canonical_sha256(suite)
    ):
        raise ValueError("Fresh B3 identity/materialization binding drifted")
    coverage = _denormalize_coverage(value["coverage"])
    validate_fresh_b2_explicit_coverage(coverage, plan=plan)
    _critical_manifest(value["critical_implementation_manifest"])
    bindings = _bindings(value["upstream_bindings"])
    required_bindings = {
        "b2_consumed_failure",
        "b2_consumed_failure_review",
        "production_composition_preflight",
        "production_composition_preflight_review",
        "storage",
        "storage_review",
        "atom_mechanism",
        "atom_mechanism_review",
    }
    if not required_bindings <= set(bindings):
        raise ValueError("Fresh B3 required upstream bindings are missing")
    b2_binding = value["b2_consumed_failure"]
    preflight_binding = value["production_composition_preflight"]
    for name, binding, upstream_name in (
        ("B2 failure", b2_binding, "b2_consumed_failure"),
        (
            "production preflight",
            preflight_binding,
            "production_composition_preflight",
        ),
    ):
        if (
            type(binding) is not dict
            or set(binding) != {"path", "root_sha256", "payload_sha256"}
            or {
                "path": binding["path"],
                "root_sha256": binding["root_sha256"],
            }
            != bindings[upstream_name]
        ):
            raise ValueError(f"Fresh B3 {name} artifact binding drifted")
        _require_sha(binding["payload_sha256"], f"{name}.payload_sha256")
    _review_binding(
        value["b2_consumed_failure_review"],
        source_root_sha256=bindings["b2_consumed_failure"]["root_sha256"],
        expected_status="passed_independent_consumed_holdout_failure_review",
        label="B2 failure review",
    )
    _review_binding(
        value["production_composition_preflight_review"],
        source_root_sha256=bindings["production_composition_preflight"][
            "root_sha256"
        ],
        expected_status=(
            "passed_independent_production_composition_preflight_review"
        ),
        label="production preflight review",
    )
    counts = _counts(plan)
    inventory = value["materialized_inventory"]
    if type(inventory) is not dict or any(
        inventory.get(name) != expected for name, expected in counts.items()
    ):
        raise ValueError("Fresh B3 materialized inventory drifted")
    license_receipt = validate_signal_complete_map_license(
        value["map_license_rows"]
    )
    route_assets = value["route_assets"]
    if (
        license_receipt["map_file_count"] != 25
        or license_receipt["unique_geometry_count"] != 25
        or inventory.get("immutable_map_file_count") != 25
        or inventory.get("map_file_sha256")
        != sorted(row["map_file_sha256"] for row in value["map_license_rows"])
        or inventory.get("map_geometry_sha256")
        != sorted(
            row["map_geometry_sha256"] for row in value["map_license_rows"]
        )
        or inventory.get("source_family") != plan["source_family"]
        or inventory.get("license_spdx") != "MIT"
        or inventory.get("project_authored") is not True
    ):
        raise ValueError("Fresh B3 map/license inventory drifted")
    if (
        type(route_assets) is not dict
        or route_assets.get("schema_version")
        != "camp_dp_v25_signal_complete_route_assets_v1"
        or route_assets.get("status")
        != "materialized_signal_complete_fixed_dp_routes"
        or route_assets.get("split") != "fresh_b3"
        or route_assets.get("route_count") != counts["route_count"]
        or route_assets.get("map_count") != counts["map_count"]
        or type(route_assets.get("route_assets")) is not list
        or len(route_assets["route_assets"]) != counts["route_count"]
        or route_assets.get("fixed_dp_modified") is not False
        or route_assets.get("map_semantics_modified") is not False
        or route_assets.get("model_loaded") is not False
        or route_assets.get("candidate_generation_executed") is not False
        or route_assets.get("fresh_b2_opened") is not False
        or route_assets.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B3 route asset authority drifted")
    qualification = value["runtime_qualification_rows"]
    if (
        type(qualification) is not list
        or len(qualification) != 100
        or len(
            {
                row.get("route_identity_sha256")
                for row in qualification
                if type(row) is dict
            }
        )
        != 100
    ):
        raise ValueError("Fresh B3 runtime qualification denominator drifted")
    zero = value["zero_overlap"]
    if (
        type(zero) is not dict
        or zero.get("status")
        != "passed_train_calibration_b2_b3_zero_overlap"
        or zero.get("fresh_b1_root_reconstructed_or_fabricated") is not False
        or zero.get("b2_outcome_values_consumed") is not False
        or zero.get("b3_outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B3 zero-overlap receipt drifted")
    storage = validate_storage_manifest(value["storage"])
    capacity = value["capacity"]
    expected_capacity = _capacity(
        storage,
        free_bytes_before=capacity["free_bytes_before"],
        output_parent=Path(capacity["canonical_output_parent"]),
    )
    if not strict_equal(capacity, expected_capacity):
        raise ValueError("Fresh B3 storage capacity receipt drifted")
    atom = value["atom_mechanism"]
    if (
        type(atom) is not dict
        or set(atom)
        != {
            "source",
            "review",
            "used_for_model_or_protocol_change",
            "mechanism_association_only",
        }
        or atom["source"] != bindings["atom_mechanism"]
        or atom["review"] != bindings["atom_mechanism_review"]
        or atom["used_for_model_or_protocol_change"] is not False
        or atom["mechanism_association_only"] is not True
    ):
        raise ValueError("Fresh B3 atom-mechanism binding drifted")
    state = value["one_time_state"]
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b3_preopen_authority",
        "fixed_dp_head": FIXED_DP_HEAD,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_open_authorized": False,
        "fresh_b3_opened": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if not strict_equal(value.get(name), expected):
            raise ValueError(f"Fresh B3 preopen {name} drifted")
    expected_state = {
        "schema_version": "camp_dp_v25_fresh_b3_unopened_state_v1",
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "cas_tombstone_exists": False,
        "nonce_created": False,
        "opening_release_created": False,
        "execution_output_created": False,
        "outcome_files_created_or_read": False,
        "fresh_b3_opened": False,
        "second_opening_allowed": False,
        "outcome_fields_consumed": [],
    }
    if not strict_equal(state, expected_state):
        raise ValueError("Fresh B3 unopened state drifted")
    if value["fresh_b1_disposition"] != {
        "status": "superseded_before_opening",
        "machine_root_reopenable": False,
        "root_reconstructed_or_fabricated": False,
        "materialized_row_count": 0,
    }:
        raise ValueError("Fresh B1 disposition drifted")
    payload = dict(value)
    stored = payload.pop("authority_payload_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError("Fresh B3 authority payload SHA drifted")
    del protocol
    return json.loads(json.dumps(value))


def _counts(plan: Mapping[str, Any]) -> dict[str, int]:
    result = {
        "map_count": plan["map_count"],
        "intersection_count": plan["intersection_count"],
        "corridor_count": plan["corridor_count"],
        "route_count": plan["route_count"],
        "semantic_block_count": plan["identity_count"],
        "seed_count": len(plan["seeds"]),
        "paired_unit_count": plan["execution_unit_count"],
        "arm_run_count": plan["planned_arm_run_count"],
        "tick_capacity": plan["planned_arm_run_count"]
        * plan["ticks_per_arm_run"],
    }
    if result != EXPECTED_COUNTS:
        raise ValueError("Fresh B3 denominator drifted")
    return result


def _validate_b3_map_suite_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Reopen the accepted B3 receipt across the provenance-field schema bump."""

    try:
        return validate_signal_complete_suite_receipt(value)
    except ValueError as current_error:
        expected = validate_signal_complete_suite(
            build_signal_complete_suite("fresh_b3")
        )
        legacy_expected = dict(expected)
        legacy_expected.pop("generator_family")
        legacy_expected.pop("generator_provenance")
        if type(value) is not dict or value != legacy_expected:
            raise current_error
        return dict(value)


def _normalize_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    result["schema_version"] = "camp_dp_v25_fresh_b3_explicit_coverage_v1"
    result["holdout_opened"] = result.pop("fresh_b2_opened")
    for row in result["coverage_rows"]:
        row["schema_version"] = (
            "camp_dp_v25_fresh_b3_explicit_coverage_row_v1"
        )
        row["holdout_opened"] = row.pop("fresh_b2_opened")
    return result


def _denormalize_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    if result.get("schema_version") != (
        "camp_dp_v25_fresh_b3_explicit_coverage_v1"
    ):
        raise ValueError("Fresh B3 coverage schema drifted")
    result["schema_version"] = "camp_dp_v25_fresh_b2_explicit_coverage_v1"
    result["fresh_b2_opened"] = result.pop("holdout_opened")
    for row in result["coverage_rows"]:
        if row.get("schema_version") != (
            "camp_dp_v25_fresh_b3_explicit_coverage_row_v1"
        ):
            raise ValueError("Fresh B3 coverage row schema drifted")
        row["schema_version"] = (
            "camp_dp_v25_fresh_b2_explicit_coverage_row_v1"
        )
        row["fresh_b2_opened"] = row.pop("holdout_opened")
    return result


def _capacity(
    storage: Mapping[str, Any],
    *,
    free_bytes_before: int,
    output_parent: Path,
) -> dict[str, Any]:
    if type(free_bytes_before) is not int or free_bytes_before <= 0:
        raise ValueError("Fresh B3 free-byte authority is invalid")
    projected = int(
        storage["metrics"]["projected_1500_arm_upper_bound_nbytes"]
    )
    remaining = free_bytes_before - projected
    floor = 10 * 1024**3
    reserve = remaining - floor
    if remaining < floor or reserve < 1024**3:
        raise ValueError("Fresh B3 projected storage breaches floor/reserve")
    return {
        "schema_version": "camp_dp_v25_fresh_b3_storage_capacity_decision_v1",
        "status": "passed_fresh_b3_storage_capacity",
        "canonical_output_parent": str(Path(output_parent).resolve()),
        "free_bytes_before": free_bytes_before,
        "projected_total_increment_bytes": projected,
        "projected_free_after_fresh_bytes": remaining,
        "ten_gib_floor_bytes": floor,
        "reserve_beyond_10gib_floor_bytes": reserve,
        "fresh_b3_opened": False,
        "outcome_fields_consumed": [],
    }


def _critical_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "paths",
        "manifest_sha256",
    }:
        raise ValueError("Fresh B3 critical manifest field set drifted")
    if value["manifest_sha256"] != canonical_sha256(value["paths"]):
        raise ValueError("Fresh B3 critical manifest SHA drifted")
    return json.loads(json.dumps(value))


def _protocol_assets(value: Mapping[str, str]) -> dict[str, str]:
    if type(value) is not dict or set(value) != PROTOCOL_ASSET_FIELDS:
        raise ValueError("Fresh B3 protocol asset field set drifted")
    return {
        name: _require_sha(value[name], name)
        for name in sorted(PROTOCOL_ASSET_FIELDS)
    }


def _bindings(
    value: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or not value:
        raise ValueError("Fresh B3 upstream bindings are missing")
    return {
        name: _binding(binding, name)
        for name, binding in sorted(value.items())
    }


def _binding(value: Mapping[str, Any], name: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"{name} binding field set drifted")
    path = value["path"]
    if type(path) is not str or not path.startswith("/root/autodl-tmp/"):
        raise ValueError(f"{name} path drifted")
    return {
        "path": path,
        "root_sha256": _require_sha(
            value["root_sha256"], f"{name}.root_sha256"
        ),
    }


def _artifact_binding(
    binding: Mapping[str, str], payload_sha256: str
) -> dict[str, str]:
    return {
        **dict(binding),
        "payload_sha256": _require_sha(payload_sha256, "payload_sha256"),
    }


def _review_binding(
    review: Mapping[str, Any],
    *,
    source_root_sha256: str,
    expected_status: str,
    label: str,
) -> None:
    if (
        type(review) is not dict
        or review.get("status") != expected_status
        or review.get("reviewed_root_sha256") != source_root_sha256
    ):
        raise ValueError(f"{label} drifted")


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _require_git_head(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase Git SHA")
    return value
