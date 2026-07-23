from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract,
    actual_native_receipt_contract_sha256,
)
from .diffusion_planner_v25_b3_preopen import (
    _capacity as _b3_capacity,
    _denormalize_coverage as _b3_denormalize_coverage,
    _normalize_coverage as _b3_normalize_coverage,
)
from .diffusion_planner_v25_fresh_coverage import (
    build_fresh_b2_explicit_coverage,
    validate_fresh_b2_explicit_coverage,
)
from .diffusion_planner_v25_fresh_preopen_authority import (
    project_train_split_rows,
)
from .diffusion_planner_v25_fresh_storage import validate_storage_manifest
from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    freeze_holdout_identity,
    freeze_replacement_experiment_protocol,
    strict_equal,
    validate_experiment_protocol,
    validate_holdout_identity,
    validate_replacement_experiment_protocol,
)
from .diffusion_planner_v25_holdout_failure_closeout import (
    validate_consumed_holdout_failure_closeout,
)
from .diffusion_planner_v25_holdout_terminal_closeout import (
    validate_terminal_failure_closeout,
)
from .diffusion_planner_v25_production_equivalence_certificate import (
    validate_production_equivalence_certificate,
)
from .diffusion_planner_v25_signal_complete_maps import (
    GENERATOR_FAMILY,
    GENERATOR_PROVENANCE,
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
from .diffusion_planner_v25_split import (
    validate_signal_complete_map_license,
    validate_v25_replacement_holdout_zero_overlap,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_consolidated_preopen_authority_v1"
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
REQUIRED_UPSTREAM_BINDINGS = frozenset(
    {
        "b2_consumed_failure",
        "b2_consumed_failure_review",
        "b3_terminal_closeout",
        "b3_terminal_closeout_review",
        "production_equivalence_certificate",
        "production_equivalence_certificate_review",
        "storage",
        "storage_review",
        "atom_mechanism",
        "atom_mechanism_review",
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
        "protocol_amendment",
        "actual_native_receipt_contract",
        "b2_consumed_failure",
        "b2_consumed_failure_review",
        "b3_terminal_closeout",
        "b3_terminal_closeout_review",
        "production_equivalence_certificate",
        "production_equivalence_certificate_review",
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
        "generator_provenance",
        "fresh_b1_disposition",
        "prior_holdout_disposition",
        "one_time_state",
        "preopen_model_loaded",
        "preopen_dp_forward_executed",
        "fresh_open_authorized",
        "fresh_b4_opened",
        "outcome_fields_consumed",
        "authority_payload_sha256",
    }
)


def build_b4_holdout_identity(
    *, suite: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    suite_value = (
        validate_signal_complete_suite(suite)
        if "map_payloads" in suite
        else validate_signal_complete_suite_receipt(suite)
    )
    plan_value = validate_signal_complete_execution_plan(plan)
    if suite_value["split"] != "fresh_b4" or plan_value["split"] != "fresh_b4":
        raise ValueError("Fresh B4 identity requires the frozen B4 suite and plan")
    counts = _counts(plan_value)
    return freeze_holdout_identity(
        split="fresh_b4",
        scenario_manifest_sha256=canonical_sha256(plan_value["identities"]),
        map_suite_payload_sha256=canonical_sha256(suite_value),
        route_census_sha256=canonical_sha256(
            sorted(row["route_identity_sha256"] for row in plan_value["identities"])
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


def build_b4_protocol_amendment(
    *, suite: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    suite_value = (
        validate_signal_complete_suite(suite)
        if "map_payloads" in suite
        else validate_signal_complete_suite_receipt(suite)
    )
    plan_value = validate_signal_complete_execution_plan(plan)
    if suite_value["split"] != "fresh_b4" or plan_value["split"] != "fresh_b4":
        raise ValueError("Fresh B4 protocol amendment split drifted")
    payload = {
        "schema_version": "camp_dp_v25_fresh_b4_protocol_amendment_v1",
        "status": "frozen_outcome_blind_replacement_holdout_extension",
        "generator_family": suite_value["generator_family"],
        "generator_provenance": suite_value["generator_provenance"],
        "map_suite_payload_sha256": canonical_sha256(suite_value),
        "execution_plan_sha256": canonical_sha256(plan_value),
        "seed_namespace": list(plan_value["seeds"]),
        "family_tier_risk_generation_rule": (
            "deterministic_v25_signal_complete_plan_constants_no_outcome_selection"
        ),
        "scientific_model_atom_margin_claim_rules_changed": False,
        "b2_or_b3_raw_values_used": False,
        "outcome_fields_consumed": [],
    }
    payload["holdout_generation_rule_sha256"] = canonical_sha256(payload)
    return payload


def build_b4_preopen_authority(
    *,
    implementation_head: str,
    critical_implementation_manifest: Mapping[str, Any],
    upstream_bindings: Mapping[str, Mapping[str, str]],
    train_source_rows: Sequence[Mapping[str, Any]],
    calibration_plan: Mapping[str, Any],
    b2_plan: Mapping[str, Any],
    b3_plan: Mapping[str, Any],
    b4_suite: Mapping[str, Any],
    b4_plan: Mapping[str, Any],
    b4_map_artifact: Path,
    route_asset_manifest: Mapping[str, Any],
    license_sha256: str,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
    prior_experiment_protocol: Mapping[str, Any],
    b2_consumed_failure: Mapping[str, Any],
    b2_consumed_failure_review: Mapping[str, Any],
    b3_terminal_closeout: Mapping[str, Any],
    b3_terminal_closeout_review: Mapping[str, Any],
    production_equivalence_certificate: Mapping[str, Any],
    production_equivalence_certificate_review: Mapping[str, Any],
    power: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    storage_manifest: Mapping[str, Any],
    atom_mechanism_binding: Mapping[str, Any],
    atom_mechanism_review_binding: Mapping[str, Any],
    free_bytes_before: int,
    output_parent: Path,
    operational_attempt_exists: bool,
    scientific_ledger_exists: bool,
) -> dict[str, Any]:
    _git_head(implementation_head, "implementation_head")
    if (
        type(operational_attempt_exists) is not bool
        or type(scientific_ledger_exists) is not bool
        or operational_attempt_exists
        or scientific_ledger_exists
    ):
        raise ValueError("Fresh B4 operational/scientific one-time state is not empty")
    manifest = _critical_manifest(critical_implementation_manifest)
    bindings = _bindings(upstream_bindings)
    if not REQUIRED_UPSTREAM_BINDINGS <= set(bindings):
        raise ValueError("Fresh B4 required upstream bindings are missing")
    suite = validate_signal_complete_suite(b4_suite)
    plan = validate_signal_complete_execution_plan(b4_plan)
    calibration = validate_signal_complete_execution_plan(calibration_plan)
    consumed_b2 = validate_signal_complete_execution_plan(b2_plan)
    consumed_b3 = validate_signal_complete_execution_plan(b3_plan)
    if (
        suite["split"] != "fresh_b4"
        or plan["split"] != "fresh_b4"
        or calibration["split"] != "calibration"
        or consumed_b2["split"] != "fresh_b2"
        or consumed_b3["split"] != "fresh_b3"
    ):
        raise ValueError("Fresh B4 split authority drifted")
    counts = _counts(plan)
    identity = build_b4_holdout_identity(suite=suite, plan=plan)
    amendment = build_b4_protocol_amendment(suite=suite, plan=plan)
    prior_protocol = validate_experiment_protocol(prior_experiment_protocol)
    protocol = freeze_replacement_experiment_protocol(
        prior_experiment_protocol=prior_protocol,
        holdout_generation_rule_sha256=amendment[
            "holdout_generation_rule_sha256"
        ],
        protocol_revision="fresh_b4_outcome_blind_extension_v1",
    )
    b2_closeout = validate_consumed_holdout_failure_closeout(
        b2_consumed_failure
    )
    b3_closeout = validate_terminal_failure_closeout(b3_terminal_closeout)
    if (
        b2_closeout["raw_outcome_values_inspected"] is not False
        or b3_closeout["raw_outcome_values_inspected"] is not False
        or b3_closeout["status"]
        != "consumed_one_shot_engineering_failure_no_evaluation_no_claim"
    ):
        raise ValueError("prior holdout values cannot influence Fresh B4")
    _review(
        b2_consumed_failure_review,
        source_root_sha256=bindings["b2_consumed_failure"]["root_sha256"],
        status="passed_independent_consumed_holdout_failure_review",
        label="B2 failure review",
    )
    _review(
        b3_terminal_closeout_review,
        source_root_sha256=bindings["b3_terminal_closeout"]["root_sha256"],
        status="passed_independent_holdout_terminal_failure_closeout_review",
        label="B3 closeout review",
    )
    certificate = validate_production_equivalence_certificate(
        production_equivalence_certificate,
        implementation_head=implementation_head,
        manifest_sha256=manifest["manifest_sha256"],
    )
    _review(
        production_equivalence_certificate_review,
        source_root_sha256=bindings["production_equivalence_certificate"][
            "root_sha256"
        ],
        status="passed_independent_nonfresh_production_equivalence_review",
        label="production-equivalence review",
    )
    qualification = project_holdout_qualification_rows(
        plan,
        prepared_runtime_cases=prepared_runtime_cases,
        expected_split="fresh_b4",
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
        + project_signal_complete_split_rows(consumed_b3)
        + project_signal_complete_split_rows(plan)
    )
    zero_overlap = validate_v25_replacement_holdout_zero_overlap(split_rows)
    license_rows = project_signal_complete_license_rows(
        suite,
        map_artifact=b4_map_artifact,
        license_sha256=license_sha256,
    )
    route_assets = _route_assets(route_asset_manifest, counts=counts)
    storage = validate_storage_manifest(storage_manifest)
    capacity = _capacity(
        storage,
        free_bytes_before=free_bytes_before,
        output_parent=output_parent,
    )
    abi = actual_native_receipt_contract()
    state = {
        "schema_version": "camp_dp_v25_fresh_b4_unopened_state_v1",
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "operational_attempt_exists": False,
        "scientific_ledger_exists": False,
        "nonce_created": False,
        "opening_release_created": False,
        "execution_output_created": False,
        "outcome_files_created_or_read": False,
        "fresh_b4_opened": False,
        "second_scientific_exposure_allowed": False,
        "outcome_fields_consumed": [],
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b4_preopen_authority",
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest": manifest,
        "upstream_bindings": bindings,
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "protocol_amendment": amendment,
        "actual_native_receipt_contract": abi,
        "b2_consumed_failure": dict(b2_closeout),
        "b2_consumed_failure_review": dict(b2_consumed_failure_review),
        "b3_terminal_closeout": dict(b3_closeout),
        "b3_terminal_closeout_review": dict(b3_terminal_closeout_review),
        "production_equivalence_certificate": certificate,
        "production_equivalence_certificate_review": dict(
            production_equivalence_certificate_review
        ),
        "materialized_inventory": {
            **counts,
            "source_family": plan["source_family"],
            "generator_family": GENERATOR_FAMILY,
            "generator_provenance": GENERATOR_PROVENANCE,
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
        "runtime_qualification_rows": qualification,
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
        "generator_provenance": {
            "generator_family": GENERATOR_FAMILY,
            "generator_provenance": GENERATOR_PROVENANCE,
            "source_family_used_as_independence_evidence": False,
            "clone_aware_geometry_semantic_seed_overlap_used": True,
        },
        "fresh_b1_disposition": {
            "status": "superseded_before_opening",
            "machine_root_reopenable": False,
            "root_reconstructed_or_fabricated": False,
            "materialized_row_count": 0,
        },
        "prior_holdout_disposition": {
            "fresh_b2": "consumed_one_shot_engineering_failure_no_evaluation",
            "fresh_b3": (
                "post_exposure_engineering_fatal_consumed_no_evaluation"
            ),
            "raw_values_used_for_b4_design": False,
            "pooled_into_b4": False,
        },
        "one_time_state": state,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_open_authorized": False,
        "fresh_b4_opened": False,
        "outcome_fields_consumed": [],
    }
    result["authority_payload_sha256"] = canonical_sha256(result)
    return validate_b4_preopen_authority(result)


def validate_b4_preopen_authority(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != AUTHORITY_FIELDS:
        raise ValueError("Fresh B4 preopen authority field set drifted")
    identity = validate_holdout_identity(value["holdout_identity"])
    protocol = validate_replacement_experiment_protocol(
        value["experiment_protocol"]
    )
    plan = validate_signal_complete_execution_plan(value["execution_plan"])
    suite = validate_signal_complete_suite_receipt(value["map_suite"])
    if (
        identity["split"] != "fresh_b4"
        or plan["split"] != "fresh_b4"
        or suite["split"] != "fresh_b4"
        or identity["execution_plan_sha256"] != canonical_sha256(plan)
        or identity["map_suite_payload_sha256"] != canonical_sha256(suite)
        or protocol["holdout_generation_rule_sha256"]
        != value["protocol_amendment"]["holdout_generation_rule_sha256"]
    ):
        raise ValueError("Fresh B4 identity/protocol/materialization drifted")
    expected_amendment = build_b4_protocol_amendment(suite=suite, plan=plan)
    if not strict_equal(value["protocol_amendment"], expected_amendment):
        raise ValueError("Fresh B4 protocol amendment drifted")
    abi = actual_native_receipt_contract()
    if (
        not strict_equal(value["actual_native_receipt_contract"], abi)
        or abi["contract_sha256"] != actual_native_receipt_contract_sha256()
    ):
        raise ValueError("Fresh B4 actual-native ABI drifted")
    manifest = _critical_manifest(value["critical_implementation_manifest"])
    bindings = _bindings(value["upstream_bindings"])
    if not REQUIRED_UPSTREAM_BINDINGS <= set(bindings):
        raise ValueError("Fresh B4 required upstream binding drifted")
    b2 = validate_consumed_holdout_failure_closeout(
        value["b2_consumed_failure"]
    )
    b3 = validate_terminal_failure_closeout(value["b3_terminal_closeout"])
    if (
        b2["raw_outcome_values_inspected"] is not False
        or b3["raw_outcome_values_inspected"] is not False
    ):
        raise ValueError("prior Fresh outcome values were inspected")
    _review(
        value["b2_consumed_failure_review"],
        source_root_sha256=bindings["b2_consumed_failure"]["root_sha256"],
        status="passed_independent_consumed_holdout_failure_review",
        label="B2 failure review",
    )
    _review(
        value["b3_terminal_closeout_review"],
        source_root_sha256=bindings["b3_terminal_closeout"]["root_sha256"],
        status="passed_independent_holdout_terminal_failure_closeout_review",
        label="B3 closeout review",
    )
    validate_production_equivalence_certificate(
        value["production_equivalence_certificate"],
        implementation_head=value["implementation_head"],
        manifest_sha256=manifest["manifest_sha256"],
    )
    _review(
        value["production_equivalence_certificate_review"],
        source_root_sha256=bindings["production_equivalence_certificate"][
            "root_sha256"
        ],
        status="passed_independent_nonfresh_production_equivalence_review",
        label="production-equivalence review",
    )
    counts = _counts(plan)
    inventory = value["materialized_inventory"]
    if type(inventory) is not dict or any(
        inventory.get(name) != expected for name, expected in counts.items()
    ):
        raise ValueError("Fresh B4 materialized inventory drifted")
    license_receipt = validate_signal_complete_map_license(
        value["map_license_rows"]
    )
    if (
        license_receipt["map_file_count"] != 25
        or license_receipt["unique_geometry_count"] != 25
        or inventory.get("immutable_map_file_count") != 25
        or inventory.get("generator_family") != GENERATOR_FAMILY
        or inventory.get("generator_provenance") != GENERATOR_PROVENANCE
        or inventory.get("source_family") != plan["source_family"]
        or inventory.get("license_spdx") != "MIT"
        or inventory.get("project_authored") is not True
    ):
        raise ValueError("Fresh B4 map/license/provenance drifted")
    _route_assets(value["route_assets"], counts=counts)
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
        raise ValueError("Fresh B4 runtime qualification denominator drifted")
    coverage = _denormalize_coverage(value["coverage"])
    validate_fresh_b2_explicit_coverage(coverage, plan=plan)
    zero = value["zero_overlap"]
    if (
        type(zero) is not dict
        or zero.get("status")
        != "passed_train_calibration_b2_b3_b4_zero_overlap"
        or zero.get("source_family_used_as_independence_evidence") is not False
        or zero.get("b2_outcome_values_consumed") is not False
        or zero.get("b3_outcome_values_consumed") is not False
        or zero.get("b4_outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B4 zero-overlap receipt drifted")
    storage = validate_storage_manifest(value["storage"])
    expected_capacity = _capacity(
        storage,
        free_bytes_before=value["capacity"]["free_bytes_before"],
        output_parent=Path(value["capacity"]["canonical_output_parent"]),
    )
    if not strict_equal(value["capacity"], expected_capacity):
        raise ValueError("Fresh B4 capacity receipt drifted")
    if value["atom_mechanism"] != {
        "source": bindings["atom_mechanism"],
        "review": bindings["atom_mechanism_review"],
        "used_for_model_or_protocol_change": False,
        "mechanism_association_only": True,
    }:
        raise ValueError("Fresh B4 atom-mechanism binding drifted")
    expected_state = {
        "schema_version": "camp_dp_v25_fresh_b4_unopened_state_v1",
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "operational_attempt_exists": False,
        "scientific_ledger_exists": False,
        "nonce_created": False,
        "opening_release_created": False,
        "execution_output_created": False,
        "outcome_files_created_or_read": False,
        "fresh_b4_opened": False,
        "second_scientific_exposure_allowed": False,
        "outcome_fields_consumed": [],
    }
    if not strict_equal(value["one_time_state"], expected_state):
        raise ValueError("Fresh B4 unopened state drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b4_preopen_authority",
        "fixed_dp_head": FIXED_DP_HEAD,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_open_authorized": False,
        "fresh_b4_opened": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if not strict_equal(value.get(name), expected):
            raise ValueError(f"Fresh B4 preopen {name} drifted")
    payload = dict(value)
    stored = payload.pop("authority_payload_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError("Fresh B4 authority payload SHA drifted")
    return json.loads(json.dumps(value))


def _route_assets(
    value: Mapping[str, Any], *, counts: Mapping[str, int]
) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    if (
        type(result) is not dict
        or result.get("schema_version")
        != "camp_dp_v25_signal_complete_route_assets_v1"
        or result.get("status")
        != "materialized_signal_complete_fixed_dp_routes"
        or result.get("split") != "fresh_b4"
        or result.get("route_count") != counts["route_count"]
        or result.get("map_count") != counts["map_count"]
        or type(result.get("route_assets")) is not list
        or len(result["route_assets"]) != counts["route_count"]
        or result.get("fixed_dp_modified") is not False
        or result.get("map_semantics_modified") is not False
        or result.get("model_loaded") is not False
        or result.get("candidate_generation_executed") is not False
        or result.get("fresh_b2_opened") is not False
        or result.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B4 route asset manifest drifted")
    return result


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
        raise ValueError("Fresh B4 denominator drifted")
    return result


def _normalize_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _b3_normalize_coverage(value)
    result["schema_version"] = "camp_dp_v25_fresh_b4_explicit_coverage_v1"
    for row in result["coverage_rows"]:
        row["schema_version"] = (
            "camp_dp_v25_fresh_b4_explicit_coverage_row_v1"
        )
    return result


def _denormalize_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value))
    if result.get("schema_version") != (
        "camp_dp_v25_fresh_b4_explicit_coverage_v1"
    ):
        raise ValueError("Fresh B4 coverage schema drifted")
    result["schema_version"] = "camp_dp_v25_fresh_b3_explicit_coverage_v1"
    for row in result["coverage_rows"]:
        if row.get("schema_version") != (
            "camp_dp_v25_fresh_b4_explicit_coverage_row_v1"
        ):
            raise ValueError("Fresh B4 coverage row schema drifted")
        row["schema_version"] = (
            "camp_dp_v25_fresh_b3_explicit_coverage_row_v1"
        )
    return _b3_denormalize_coverage(result)


def _capacity(
    storage: Mapping[str, Any],
    *,
    free_bytes_before: int,
    output_parent: Path,
) -> dict[str, Any]:
    prior = _b3_capacity(
        storage,
        free_bytes_before=free_bytes_before,
        output_parent=output_parent,
    )
    prior["schema_version"] = (
        "camp_dp_v25_fresh_b4_storage_capacity_decision_v1"
    )
    prior["status"] = "passed_fresh_b4_storage_capacity"
    prior["fresh_b4_opened"] = prior.pop("fresh_b3_opened")
    return prior


def _critical_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "paths",
        "manifest_sha256",
    }:
        raise ValueError("Fresh B4 critical manifest field set drifted")
    if value["manifest_sha256"] != canonical_sha256(value["paths"]):
        raise ValueError("Fresh B4 critical manifest SHA drifted")
    return json.loads(json.dumps(value))


def _bindings(
    value: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or not value:
        raise ValueError("Fresh B4 upstream bindings are missing")
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
        "root_sha256": _sha(value["root_sha256"], f"{name}.root_sha256"),
    }


def _review(
    value: Mapping[str, Any],
    *,
    source_root_sha256: str,
    status: str,
    label: str,
) -> None:
    if (
        type(value) is not dict
        or value.get("status") != status
        or value.get("reviewed_root_sha256") != source_root_sha256
    ):
        raise ValueError(f"{label} drifted")


def _sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _git_head(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase Git SHA")
    return value
