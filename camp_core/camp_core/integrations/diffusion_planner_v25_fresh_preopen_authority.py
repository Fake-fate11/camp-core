from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .diffusion_planner_artifact_seal import verify_complete_seal
from .diffusion_planner_v25_calibration_preregistration import (
    validate_paired_calibration_preregistration,
)
from .diffusion_planner_v25_fresh_coverage import (
    build_fresh_b2_explicit_coverage,
    validate_fresh_b2_explicit_coverage,
)
from .diffusion_planner_v25_fresh_storage import validate_storage_manifest
from .diffusion_planner_v25_atom_mechanism import validate_atom_mechanism_binding
from .diffusion_planner_v25_signal_complete_maps import (
    SOURCE_FAMILY,
    validate_signal_complete_suite,
)
from .diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
    validate_signal_complete_execution_plan,
)
from .diffusion_planner_v25_signal_complete_preopen import (
    project_fresh_b2_qualification_rows,
    project_signal_complete_license_rows,
    project_signal_complete_split_rows,
)
from .diffusion_planner_v25_split import validate_v25_zero_overlap
from .diffusion_planner_v25_statistics import prospective_cluster_sensitivity


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_preopen_authority_v1"
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
TRACKED_AUTHORITY_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_atom_mechanism.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b3_preopen.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_preopen.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_calibration.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_calibration_artifact.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_calibration_corpus.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_final_delivery.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_b2.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_coverage.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_execution.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_execution_review.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_opening.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_preopen_authority.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_receipt.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_storage.py",
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_actual_native_receipt_contract.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_actual_native_receipt_review.py"
    ),
    "camp_core/camp_core/integrations/diffusion_planner_v25_evaluation.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_contract.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_execution.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_failure_closeout.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_opening.py",
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_holdout_opening_rc.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_holdout_preopen_dispatch.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_holdout_plan_dispatch.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_production_equivalence_authority.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_production_equivalence_certificate.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_production_equivalence_fixture.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_role_provenance.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_role_provenance_review.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_holdout_state.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_holdout_lifecycle_preflight.py"
    ),
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_preflight.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_holdout_protocol.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_paired_calibration.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_execution.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_maps.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_plan.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_preopen.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_routes.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_runtime.py",
    "configs/integrations/diffusion_planner_v25_final_delivery_contract_v1.json",
    "configs/integrations/diffusion_planner_v25_atom_mechanism_v1.json",
    "configs/integrations/diffusion_planner_v25_fresh_b2_preopen_authority_v1.json",
    "configs/integrations/diffusion_planner_v25_fresh_b2_preregistration_draft_v1.json",
    "configs/integrations/diffusion_planner_v25_holdout_normative_contract_v1.json",
    "configs/integrations/diffusion_planner_v25_holdout_normative_contract_v2.json",
    "scripts/integrations/build_diffusion_planner_v25_final_evidence.py",
    "scripts/integrations/create_diffusion_planner_v25_fresh_b2_opening.py",
    "scripts/integrations/create_diffusion_planner_v25_holdout_opening.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b2_consumed_failure_closeout.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b3_production_preflight.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b3_preopen.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b4_preopen.py",
    "scripts/integrations/freeze_diffusion_planner_v25_atom_mechanism.py",
    "scripts/integrations/freeze_diffusion_planner_v25_calibration_from_paired.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_fresh_b2.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/freeze_diffusion_planner_v25_fresh_b2_preopen.py",
    "scripts/integrations/freeze_diffusion_planner_v25_holdout_production_preflight.py",
    (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_production_equivalence_certificate.py"
    ),
    (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_production_equivalence_authority.py"
    ),
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_maps.py",
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_plan.py",
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_routes.py",
    "scripts/integrations/qualify_diffusion_planner_v25_fresh_storage.py",
    "scripts/integrations/qualify_diffusion_planner_v25_signal_complete_runtime.py",
    "scripts/integrations/review_diffusion_planner_v25_fresh_b2_evaluation.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
    "scripts/integrations/review_diffusion_planner_v25_atom_mechanism.py",
    "scripts/integrations/review_diffusion_planner_v25_calibration_from_paired.py",
    "scripts/integrations/review_diffusion_planner_v25_fresh_b2_execution.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_execution.py",
    "scripts/integrations/review_diffusion_planner_v25_fresh_b2_preopen.py",
    "scripts/integrations/review_diffusion_planner_v25_b2_consumed_failure_closeout.py",
    "scripts/integrations/review_diffusion_planner_v25_b3_production_preflight.py",
    "scripts/integrations/review_diffusion_planner_v25_b3_preopen.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_preopen.py",
    "scripts/integrations/review_diffusion_planner_v25_final_evidence.py",
    "scripts/integrations/review_diffusion_planner_v25_fresh_storage.py",
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_maps.py",
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_plan.py",
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_routes.py",
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_runtime.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_production_preflight.py",
    (
        "scripts/integrations/"
        "review_diffusion_planner_v25_production_equivalence_authority.py"
    ),
    (
        "scripts/integrations/"
        "review_diffusion_planner_v25_production_equivalence_certificate.py"
    ),
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    (
        "scripts/integrations/"
        "run_diffusion_planner_v25_b4_production_rc_focused_tests.py"
    ),
    "scripts/integrations/run_diffusion_planner_v25_fresh_b2_execution.py",
    "scripts/integrations/run_diffusion_planner_v25_holdout_execution.py",
)


def build_preopen_authority(
    *,
    repo_root: Path,
    implementation_head: str,
    upstream_bindings: Mapping[str, Mapping[str, str]],
    train_source_rows: Sequence[Mapping[str, Any]],
    calibration_preregistration: Mapping[str, Any],
    calibration_preregistration_sha256: str,
    calibration_analysis: Mapping[str, Any],
    suite_receipt: Mapping[str, Any],
    map_artifact: Path,
    license_sha256: str,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
    storage_manifest: Mapping[str, Any],
    storage_review_status: str,
    atom_mechanism_binding: Mapping[str, Any],
    free_bytes_before: int,
    output_parent: Path,
) -> dict[str, Any]:
    """Build the single outcome-blind Fresh-B2 pre-open decision payload."""

    _require_git_head(implementation_head, "implementation_head")
    if _git_head(repo_root) != implementation_head:
        raise ValueError("Fresh B2 implementation HEAD drifted")
    roots = _upstream_bindings(upstream_bindings)
    prereg = validate_paired_calibration_preregistration(calibration_preregistration)
    if _sha256_bytes(canonical_json_bytes(prereg)) != calibration_preregistration_sha256:
        raise ValueError("Fresh B2 accepted preregistration bytes drifted")
    if (
        prereg["fresh_b2_opened"] is not False
        or prereg["fresh_outcome_fields_consumed"] != []
        or prereg["fresh_open_authorized"] is not False
        or prereg["calibration_result_driven_protocol_change_authorized"] is not False
    ):
        raise ValueError("Fresh B2 preregistration/opening boundary drifted")

    suite = validate_signal_complete_suite(suite_receipt)
    plan = validate_signal_complete_execution_plan(
        build_signal_complete_execution_plan("fresh_b2")
    )
    if suite["split"] != "fresh_b2" or plan["source_family"] != SOURCE_FAMILY:
        raise ValueError("Fresh B2 materialized map/plan authority drifted")
    calibration_plan = build_signal_complete_execution_plan("calibration")
    train_rows = project_train_split_rows(train_source_rows)
    split_rows = (
        train_rows
        + project_signal_complete_split_rows(calibration_plan)
        + project_signal_complete_split_rows(plan)
    )
    zero_overlap = validate_v25_zero_overlap(split_rows)
    license_rows = project_signal_complete_license_rows(
        suite,
        map_artifact=map_artifact,
        license_sha256=license_sha256,
    )
    qualification_rows = project_fresh_b2_qualification_rows(
        plan,
        prepared_runtime_cases=prepared_runtime_cases,
    )
    coverage = build_fresh_b2_explicit_coverage(
        plan,
        prepared_runtime_cases=prepared_runtime_cases,
    )
    if coverage["census"] != {**coverage["census"], **EXPECTED_COUNTS}:
        raise ValueError("Fresh B2 frozen coverage denominator drifted")

    power = fresh_power_at_corridor_ceiling(calibration_analysis, corridor_count=100)
    storage = validate_storage_manifest(storage_manifest)
    capacity = capacity_decision(
        storage,
        free_bytes_before=free_bytes_before,
        output_parent=output_parent,
        storage_review_status=storage_review_status,
    )
    critical_manifest = tracked_implementation_manifest(repo_root)
    evaluation = frozen_evaluation_contract(
        prereg,
        preregistration_sha256=calibration_preregistration_sha256,
    )
    mechanism = validate_atom_mechanism_binding(atom_mechanism_binding)
    state = {
        "schema_version": "camp_dp_v25_fresh_b2_unopened_state_v1",
        "fresh_b_v1_disposition": "superseded_before_opening_original_manifest_machine_root_unavailable",
        "fresh_b_v1_root_reconstructed_or_fabricated": False,
        "fresh_b2_open_authorized": False,
        "one_time_release_required": True,
        "nonce_created": False,
        "nonce_marker_created": False,
        "execution_output_created": False,
        "outcome_files_created_or_read": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b2_preopen_authority",
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest": critical_manifest,
        "upstream_bindings": roots,
        "materialized_inventory": {
            **EXPECTED_COUNTS,
            "source_family": SOURCE_FAMILY,
            "license_spdx": "MIT",
            "project_authored": True,
            "immutable_map_file_count": len(license_rows),
            "map_file_sha256": sorted(row["map_file_sha256"] for row in license_rows),
            "map_geometry_sha256": sorted(row["map_geometry_sha256"] for row in license_rows),
        },
        "plan": plan,
        "qualification_rows": qualification_rows,
        "explicit_coverage": coverage,
        "split_rows_sha256": canonical_json_sha256(split_rows),
        "zero_overlap_receipt": zero_overlap,
        "map_license_rows": license_rows,
        "power": power,
        "storage": storage,
        "capacity": capacity,
        "evaluation": evaluation,
        "atom_mechanism": mechanism,
        "one_time_state": state,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_open_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    return validate_preopen_authority(result)


def validate_preopen_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "implementation_head",
        "fixed_dp_head",
        "critical_implementation_manifest",
        "upstream_bindings",
        "materialized_inventory",
        "plan",
        "qualification_rows",
        "explicit_coverage",
        "split_rows_sha256",
        "zero_overlap_receipt",
        "map_license_rows",
        "power",
        "storage",
        "capacity",
        "evaluation",
        "atom_mechanism",
        "one_time_state",
        "preopen_model_loaded",
        "preopen_dp_forward_executed",
        "training_executed",
        "calibration_executed",
        "fresh_open_authorized",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 pre-open authority field set drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b2_preopen_authority",
        "fixed_dp_head": FIXED_DP_HEAD,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_open_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not strict_equal(value.get(key), item) for key, item in exact.items()):
        raise ValueError("Fresh B2 pre-open closed-state contract drifted")
    _require_git_head(value["implementation_head"], "implementation_head")
    _upstream_bindings(value["upstream_bindings"])
    plan = validate_signal_complete_execution_plan(value["plan"])
    coverage = validate_fresh_b2_explicit_coverage(value["explicit_coverage"], plan=plan)
    inventory = value["materialized_inventory"]
    if type(inventory) is not dict or any(inventory.get(key) != item for key, item in EXPECTED_COUNTS.items()):
        raise ValueError("Fresh B2 materialized inventory drifted")
    if coverage["census"]["static_signal_chain_qualified_count"] != 100:
        raise ValueError("Fresh B2 static signal-chain coverage is incomplete")
    validate_storage_manifest(value["storage"])
    validate_atom_mechanism_binding(value["atom_mechanism"])
    capacity = value["capacity"]
    if (
        type(capacity) is not dict
        or capacity.get("status") != "passed_fresh_b2_storage_capacity"
        or capacity.get("projected_free_after_fresh_bytes") < 10 * 1024**3
        or capacity.get("reserve_beyond_10gib_floor_bytes") < 1024**3
    ):
        raise ValueError("Fresh B2 storage capacity hard gate failed")
    state = value["one_time_state"]
    if (
        type(state) is not dict
        or state.get("fresh_b2_opened") is not False
        or state.get("nonce_created") is not False
        or state.get("outcome_files_created_or_read") is not False
        or state.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 unopened state drifted")
    return json.loads(json.dumps(value))


def project_train_split_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, row in enumerate(source_rows):
        if type(row) is not dict or row.get("runner_eligible") is not True:
            continue
        chain = row.get("source_chain")
        if type(chain) is not dict:
            raise ValueError(f"train source row {index} lacks a source chain")
        route_geometry = _require_sha(chain.get("route_geometry_sha256"), "route_geometry_sha256")
        semantic = _require_sha(chain.get("semantic_clone_sha256"), "semantic_clone_sha256")
        source_map = _require_sha(row.get("source_map_sha256"), "source_map_sha256")
        result.append(
            {
                "split": "train",
                "source_family": "fixed_dp_formal_controlled_train",
                "map_geometry_sha256": route_geometry,
                "intersection_sha256": (
                    _require_sha(chain.get("stop_line_geometry_sha256"), "stop_line_geometry_sha256")
                    if row.get("source_class") == "mapped_signal"
                    else None
                ),
                "corridor_sha256": route_geometry,
                "route_family_sha256": route_geometry,
                "semantic_parameter_block_sha256": semantic,
                "seed_namespace": canonical_json_sha256({"split": "train", "seed": int(row["seed"])}),
                "route_identity_sha256": _require_sha(row.get("route_identity_sha256"), "route_identity_sha256"),
                "scenario_family": str(row["family"]),
            }
        )
        del source_map
    if len(result) != 1500:
        raise ValueError("Fresh B2 train split must bind all 1500 executable identities")
    return result


def fresh_power_at_corridor_ceiling(
    calibration_analysis: Mapping[str, Any], *, corridor_count: int
) -> dict[str, Any]:
    if type(corridor_count) is not int or corridor_count != 100:
        raise ValueError("Fresh B2 power must use the real 100-corridor ceiling")
    source = calibration_analysis.get("fresh_b2_power_sensitivity")
    if type(source) is not dict:
        raise ValueError("accepted calibration power receipt is missing")
    comparisons: dict[str, Any] = {}
    for arm in ("camp_static14d_minus_candidate0", "camp_scene14d_no_v2i_minus_candidate0"):
        item = source.get(arm)
        if type(item) is not dict:
            raise ValueError(f"accepted calibration power arm missing: {arm}")
        comparisons[arm] = {}
        for metric in ("safety_cost_total", "red_light_component"):
            receipt = item.get(metric)
            if type(receipt) is not dict:
                raise ValueError(f"accepted calibration power metric missing: {arm}/{metric}")
            comparisons[arm][metric] = prospective_cluster_sensitivity(
                float(receipt["cluster_standard_deviation"]),
                corridor_count,
                confidence=0.95,
                power=0.80,
            )
    return {
        "schema_version": "camp_dp_v25_fresh_b2_prospective_power_v1",
        "status": "frozen_at_real_100_corridor_ceiling",
        "independent_corridor_ceiling": 100,
        "seed_count": 5,
        "seeds_or_ticks_counted_as_independent": False,
        "variance_source": "accepted_calibration_equal_mass_corridor_cluster_variance",
        "comparisons": comparisons,
        "scene_underpowered_risk_disclosed": True,
        "scope": "project_authored_controlled_benchmark_only",
    }


def capacity_decision(
    storage_manifest: Mapping[str, Any],
    *,
    free_bytes_before: int,
    output_parent: Path,
    storage_review_status: str,
) -> dict[str, Any]:
    storage = validate_storage_manifest(storage_manifest)
    if type(free_bytes_before) is not int or free_bytes_before <= 0:
        raise ValueError("Fresh B2 free-byte authority is invalid")
    projected = int(storage["metrics"]["projected_1500_arm_upper_bound_nbytes"])
    remaining = free_bytes_before - projected
    reserve = remaining - 10 * 1024**3
    if storage_review_status != "passed_independent_fresh_storage_equivalence_and_capacity_review":
        raise ValueError("Fresh B2 storage independent review is not accepted")
    if remaining < 10 * 1024**3 or reserve < 1024**3:
        raise ValueError("Fresh B2 projected storage breaches floor/reserve")
    return {
        "schema_version": "camp_dp_v25_fresh_b2_storage_capacity_decision_v1",
        "status": "passed_fresh_b2_storage_capacity",
        "canonical_output_parent": str(output_parent.resolve()),
        "free_bytes_before": free_bytes_before,
        "projected_total_increment_bytes": projected,
        "projected_free_after_fresh_bytes": remaining,
        "ten_gib_floor_bytes": 10 * 1024**3,
        "reserve_beyond_10gib_floor_bytes": reserve,
        "storage_review_status": storage_review_status,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def frozen_evaluation_contract(
    preregistration: Mapping[str, Any], *, preregistration_sha256: str
) -> dict[str, Any]:
    prereg = validate_paired_calibration_preregistration(preregistration)
    return {
        "schema_version": "camp_dp_v25_fresh_b2_evaluation_freeze_v1",
        "status": "bit_exact_to_accepted_calibration_preregistration",
        "accepted_preregistration_sha256": _require_sha(preregistration_sha256, "preregistration_sha256"),
        "primary_arms": list(prereg["primary_arms"]),
        "paper_subset_ablations": list(prereg["paper_subset_ablations"]),
        "primary": json.loads(json.dumps(prereg["primary"])),
        "noninferiority": json.loads(json.dumps(prereg["noninferiority"])),
        "component_guardrails": json.loads(json.dumps(prereg["component_guardrails"])),
        "paired_statistics": json.loads(json.dumps(prereg["paired_statistics"])),
        "coverage": json.loads(json.dumps(prereg["coverage"])),
        "latency": json.loads(json.dumps(prereg["latency"])),
        "balanced_arm_order_and_independent_reset": True,
        "claim_requires_primary_component_and_all_ni_gates": True,
        "calibration_claim_authorized_is_opening_gate": False,
        "calibration_result_driven_change_authorized": False,
        "claim_scope": "project_authored_controlled_benchmark_and_unchanged_fixed_dp_valid_k8_support_domain",
        "real_world_or_broad_map_claim_authorized": False,
        "promotion_or_deployment_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def tracked_implementation_manifest(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    rows = []
    for relative in TRACKED_AUTHORITY_FILES:
        subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
            stderr=subprocess.STDOUT,
        )
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError(f"Fresh B2 tracked authority path is unsafe: {relative}")
        rows.append({"path": relative, "sha256": _file_sha256(path)})
    return {
        "schema_version": "camp_dp_v25_fresh_b2_critical_implementation_manifest_v1",
        "paths": rows,
        "manifest_sha256": canonical_json_sha256(rows),
    }


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value))


def strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _upstream_bindings(value: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, str]]:
    if type(value) is not dict or not value:
        raise ValueError("Fresh B2 upstream bindings are missing")
    result: dict[str, dict[str, str]] = {}
    for role, binding in sorted(value.items()):
        if type(role) is not str or type(binding) is not dict or set(binding) != {"path", "root_sha256"}:
            raise ValueError("Fresh B2 upstream binding schema drifted")
        path = Path(str(binding["path"]))
        if not path.is_absolute() or str(path.resolve()) != str(path):
            raise ValueError(f"Fresh B2 upstream path is not canonical: {role}")
        root = _require_sha(binding["root_sha256"], f"{role}.root_sha256")
        result[role] = {"path": str(path), "root_sha256": root}
    return result


def verify_bound_artifact(path: Path, root_sha256: str, *, exit_code: int) -> dict[str, Any]:
    seal = verify_complete_seal(path, root_sha256, label=path.name)
    if (path / "run.exit").read_bytes() != f"{exit_code}\n".encode("ascii"):
        raise ValueError(f"bound artifact run.exit drifted: {path}")
    return seal


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_sha(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _require_git_head(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 40 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a full Git commit")
    return value
