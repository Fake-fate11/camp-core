from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    COMPLETE_STATUS,
    EXPECTED_VALIDATED_DATASET_SHA256,
    validate_training_sufficiency_preflight,
)


SCHEMA_VERSION = "dp_native_fallback_risk_training_split_manifest_v1"
DATASET_SHA = EXPECTED_VALIDATED_DATASET_SHA256
VALIDATOR_SHA = "276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078"
SPLIT_POLICY = "sha256(record_identity_hash + split_salt)"
SPLIT_SALT = "fallback_risk_training_split_v1"
GROUP_KEY_FIELDS = ("source_log", "run_id", "record_index")
FORMAL_SEEDS = {11, 12, 13}
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
UNIT_TESTS_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests.md"
)
FORBIDDEN_SPLIT_FEATURES = {
    "selected_index",
    "candidate_rank",
    "closed_loop_outcome",
    "learned_weights",
}
FORBIDDEN_FINAL_FLAGS = (
    "training_authorized",
    "fallback_dataset_training_sufficiency_claim",
    "camp_retraining_authorized_now",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def build_reference_split_manifest(dataset: Any, *, enabled: bool) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "default_off": True,
            "enabled": enabled,
            "dataset_read": False,
            "synthetic_static_contract_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_modified": False,
        },
        "dataset_sha256": None,
        "validator_output_sha256": None,
        "split_policy": SPLIT_POLICY,
        "split_salt": SPLIT_SALT,
        "group_key_fields": list(GROUP_KEY_FIELDS),
        "training_groups": [],
        "validation_groups": [],
        "record_assignments": [],
        "record_counts": {
            "accepted_records": 0,
            "training_records": 0,
            "validation_records": 0,
        },
        "final_decision": _decision(
            status="dp_native_fallback_risk_training_split_manifest_default_off_disabled",
            passed=True,
            enabled=False,
            errors=[],
        ),
    }
    if not enabled:
        return report

    report["analysis"]["dataset_read"] = True
    errors: list[str] = []
    records = _validate_dataset(dataset, errors)
    if not errors:
        assignments = [_assignment(record) for record in records]
        training = sorted(
            item["group_id"] for item in assignments if item["split"] == "training"
        )
        validation = sorted(
            item["group_id"] for item in assignments if item["split"] == "validation"
        )
        if not training or not validation:
            errors.append("split_train_or_validation_empty")
        report["training_groups"] = training
        report["validation_groups"] = validation
        report["record_assignments"] = sorted(
            assignments,
            key=lambda item: item["record_identity_hash"],
        )
        report["record_counts"] = {
            "accepted_records": len(assignments),
            "training_records": len(training),
            "validation_records": len(validation),
        }

    if isinstance(dataset, dict):
        report["dataset_sha256"] = dataset.get("dataset_sha256")
        report["validator_output_sha256"] = dataset.get("validator_output_sha256")
    report["final_decision"] = _decision(
        status=(
            "dp_native_fallback_risk_training_split_manifest_rejected"
            if errors
            else "dp_native_fallback_risk_training_split_manifest_complete"
        ),
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def validate_split_manifest_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "schema_version",
        "dataset_sha256",
        "validator_output_sha256",
        "split_policy",
        "split_salt",
        "group_key_fields",
        "training_groups",
        "validation_groups",
        "record_assignments",
        "record_counts",
        "final_decision",
    ):
        if field not in report:
            errors.append(f"{field}_missing")
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if report.get("dataset_sha256") != DATASET_SHA:
        errors.append("dataset_sha256_mismatch")
    if report.get("validator_output_sha256") != VALIDATOR_SHA:
        errors.append("validator_output_sha256_mismatch")
    if report.get("split_policy") != SPLIT_POLICY:
        errors.append("split_policy_mismatch")
    if report.get("split_salt") != SPLIT_SALT:
        errors.append("split_salt_mismatch")
    if tuple(report.get("group_key_fields") or ()) != GROUP_KEY_FIELDS:
        errors.append("group_key_fields_mismatch")

    training = set(report.get("training_groups") or ())
    validation = set(report.get("validation_groups") or ())
    if not training or not validation:
        errors.append("split_train_or_validation_empty")
    if training & validation:
        errors.append("split_train_validation_overlap")

    assignments = report.get("record_assignments")
    if not isinstance(assignments, list):
        errors.append("record_assignments_not_list")
        assignments = []
    assignment_hashes = [
        item.get("record_identity_hash")
        for item in assignments
        if isinstance(item, dict)
    ]
    if len(assignment_hashes) != len(set(assignment_hashes)):
        errors.append("duplicate_record_assignment")
    if len(assignments) != report.get("record_counts", {}).get("accepted_records"):
        errors.append("record_counts_accepted_mismatch")
    if len(training) + len(validation) != report.get("record_counts", {}).get(
        "accepted_records"
    ):
        errors.append("record_counts_split_mismatch")
    for item in assignments:
        if not isinstance(item, dict):
            errors.append("record_assignment_not_object")
            continue
        if item.get("split") not in {"training", "validation"}:
            errors.append("record_assignment_split_invalid")
        if item.get("group_id") not in training | validation:
            errors.append("record_assignment_group_missing")

    decision = report.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("final_decision_not_object")
        return sorted(set(errors))
    for flag in FORBIDDEN_FINAL_FLAGS:
        if decision.get(flag) is not False:
            errors.append(f"{flag}_leak")
    return sorted(set(errors))


def _validate_dataset(dataset: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(dataset, dict):
        errors.append("dataset_not_object")
        return []
    if dataset.get("dataset_sha256") != DATASET_SHA:
        errors.append("dataset_sha256_mismatch")
    if dataset.get("validator_output_sha256") != VALIDATOR_SHA:
        errors.append("validator_output_sha256_mismatch")
    if dataset.get("records_scope") != "records_without_feasible_candidate_only":
        errors.append("records_scope_mismatch")
    if dataset.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_included")
    split_features = set(dataset.get("split_feature_sources") or ())
    for feature in split_features & FORBIDDEN_SPLIT_FEATURES:
        errors.append(f"{feature}_used_as_split_feature")
    records = dataset.get("records")
    if not isinstance(records, list):
        errors.append("records_not_list")
        return []
    if len(records) != 15:
        errors.append("validated_fallback_record_count_mismatch")

    seen_group_keys: set[tuple[Any, ...]] = set()
    seen_hashes: set[str] = set()
    valid_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            errors.append("record_not_object")
            continue
        _validate_record(record, seen_group_keys, seen_hashes, errors)
        valid_records.append(record)
    return valid_records


def _validate_record(
    record: dict[str, Any],
    seen_group_keys: set[tuple[Any, ...]],
    seen_hashes: set[str],
    errors: list[str],
) -> None:
    for field in (
        "source_log",
        "source_log_sha256",
        "run_id",
        "record_index",
        "candidate_count",
        "oracle_index",
        "record_identity_hash",
        "records_without_feasible_candidate",
        "seed",
        "formal_eval_artifact_included",
    ):
        if field not in record:
            errors.append(f"{field}_missing")
    group_key = tuple(record.get(field) for field in GROUP_KEY_FIELDS)
    if group_key in seen_group_keys:
        errors.append("group_key_collision")
    seen_group_keys.add(group_key)

    identity_hash = record.get("record_identity_hash")
    if not isinstance(identity_hash, str) or not identity_hash:
        errors.append("record_identity_hash_missing")
    elif identity_hash != _record_identity_hash(record):
        errors.append("record_identity_hash_mismatch")
    elif identity_hash in seen_hashes:
        errors.append("duplicate_record_identity")
    else:
        seen_hashes.add(identity_hash)

    source_log = record.get("source_log")
    if (
        not isinstance(source_log, str)
        or record.get("source_log_sha256") != _sha256_text(source_log)
    ):
        errors.append("source_log_sha256_mismatch")
    candidate_count = record.get("candidate_count")
    oracle_index = record.get("oracle_index")
    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count <= 0
    ):
        errors.append("candidate_count_invalid")
    if (
        isinstance(oracle_index, bool)
        or not isinstance(oracle_index, int)
        or not isinstance(candidate_count, int)
        or not 0 <= oracle_index < candidate_count
    ):
        errors.append("oracle_index_invalid")
    if record.get("records_without_feasible_candidate") is not True:
        errors.append("feasible_candidate_record_included")
    if record.get("seed") in FORMAL_SEEDS:
        errors.append("formal_seed_in_split_manifest")
    if record.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_record_included")


def _assignment(record: dict[str, Any]) -> dict[str, Any]:
    identity_hash = record["record_identity_hash"]
    split_hash = _sha256_text(identity_hash + SPLIT_SALT)
    split_score = int(split_hash, 16) / float(1 << 256)
    split = "validation" if split_score < 0.2 else "training"
    return {
        "record_identity_hash": identity_hash,
        "group_id": _group_id(record),
        "split": split,
        "split_hash": split_hash,
    }


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": passed,
        "enabled": enabled,
        "errors": sorted(set(errors)),
        "ready_for_future_preflight": bool(enabled and passed),
    }
    for flag in FORBIDDEN_FINAL_FLAGS:
        decision[flag] = False
    return decision


def _dataset(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "dataset_sha256": DATASET_SHA,
        "validator_output_sha256": VALIDATOR_SHA,
        "records_scope": "records_without_feasible_candidate_only",
        "formal_eval_artifact_included": False,
        "split_feature_sources": ["record_identity_hash"],
        "records": records or _records(),
    }


def _records() -> list[dict[str, Any]]:
    records = []
    for index in range(15):
        source_log = f"log_{index:02d}"
        record = {
            "source_log": source_log,
            "source_log_sha256": _sha256_text(source_log),
            "run_id": f"run_{index % 3}",
            "record_index": index,
            "candidate_count": 6,
            "oracle_index": index % 6,
            "records_without_feasible_candidate": True,
            "seed": 21 + index,
            "formal_eval_artifact_included": False,
            "selected_index": (index + 1) % 6,
            "candidate_rank": index % 6,
            "closed_loop_outcome": {"ignored": index},
            "learned_weights": [0.25, 0.75],
        }
        record["record_identity_hash"] = _record_identity_hash(record)
        records.append(record)
    return records


def _record_identity_hash(record: dict[str, Any]) -> str:
    return _sha256_text(
        "|".join(str(record.get(field)) for field in GROUP_KEY_FIELDS)
    )


def _group_id(record: dict[str, Any]) -> str:
    return "|".join(str(record[field]) for field in GROUP_KEY_FIELDS)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _preflight_inputs(tmp_path: Path, split: dict[str, Any]) -> dict[str, Path]:
    return {
        "validated_dataset_summary_json": _write_json(
            tmp_path / "validated_dataset.json",
            {
                "sha256": DATASET_SHA,
                "records": 15,
                "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
                "validator_passed": True,
                "training_sufficiency_claim": False,
                "deployable_checkpoint_claim": False,
            },
        ),
        "training_split_manifest_json": _write_json(tmp_path / "split.json", split),
        "train_only_scale_manifest_json": _write_json(
            tmp_path / "scales.json",
            {
                "fit_groups": split["training_groups"],
                "fit_seeds": [21, 22],
                "formal_eval_artifact_included": False,
                "atom_schema_version": "dp_camp_v10_14d",
                "atom_names": [
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
                ],
                "atom_scales": {
                    "jerk_early": 1.0,
                    "jerk_late": 1.0,
                    "jerk_full": 1.0,
                    "rms_acceleration": 1.0,
                    "speed_limit_margin_0_0": 1.0,
                    "speed_limit_margin_0_5": 1.0,
                    "speed_limit_margin_1_0": 1.0,
                    "lane_deviation": 1.0,
                    "clearance": 1.0,
                    "progress_shortfall": 1.0,
                    "planned_red_light_cost": 1.0,
                    "planned_lateral_acceleration_cost": 1.0,
                    "red_stopping_margin_cost": 1.0,
                    "dp_prior_jerk_excess_cost": 1.0,
                },
            },
        ),
        "fallback_master_config_json": _write_json(
            tmp_path / "master.json",
            {
                "fallback_only": True,
                "feasible_branch_records_allowed": False,
                "all_infeasible_records_added_to_feasible_training": False,
                "all_infeasible_records_relabelled_feasible": False,
                "hard_feasibility_relaxation_authorized": False,
                "feasible_ranking_master_change_authorized": False,
                "score_expression": "score_k(w)=a_k^T w",
                "atoms_fixed_nonnegative": True,
                "fallback_label_is_deployed_atom": False,
                "margins_nonnegative": True,
                "simplex_cvar_l2_convex": True,
            },
        ),
        "training_command_plan_json": _write_json(
            tmp_path / "command.json",
            {
                "training_command_authorization": False,
                "replay_execution_authorized": False,
                "candidate_generation_authorized": False,
                "camp_training_authorized": False,
                "camp_retraining_authorized": False,
                "Full36_authorized": False,
                "formal_seeds_11_12_13_authorized": False,
                "dp_modification_authorized": False,
                "reference_blend_authorized": False,
                "guidance_authorized": False,
                "postprocess_postselection_authorized": False,
                "closed_loop_outcome_online_input_authorized": False,
                "selector_promotion_authorized": False,
                "atom_promotion_authorized": False,
                "deployable_checkpoint_claim_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
                "fallback_risk_training_authorized_now": False,
                "feasible_ranking_master_change_authorized": False,
                "hard_feasibility_relaxation_authorized": False,
                "all_infeasible_records_added_to_feasible_training": False,
                "production_selector_change_authorized": False,
                "online_selector_change_authorized": False,
                "post_training_nonpromotion_plan_required": True,
                "development_holdout_acceptance_gate_required": True,
            },
        ),
    }


def test_default_off_split_builder_does_not_read_dataset() -> None:
    report = build_reference_split_manifest(object(), enabled=False)

    assert report["final_decision"]["status"] == (
        "dp_native_fallback_risk_training_split_manifest_default_off_disabled"
    )
    assert report["final_decision"]["passed"] is True
    assert report["analysis"]["dataset_read"] is False
    assert report["record_assignments"] == []


def test_clean_synthetic_manifest_is_preflight_compatible(tmp_path: Path) -> None:
    report = build_reference_split_manifest(_dataset(), enabled=True)
    split = {
        "group_key_fields": report["group_key_fields"],
        "training_groups": report["training_groups"],
        "validation_groups": report["validation_groups"],
        "seeds": [21, 22],
        "formal_eval_artifact_included": False,
    }

    preflight = validate_training_sufficiency_preflight(
        enabled=True,
        **_preflight_inputs(tmp_path, split),
    )

    assert report["final_decision"]["passed"] is True
    assert validate_split_manifest_report(report) == []
    assert preflight["final_decision"]["status"] == COMPLETE_STATUS
    assert preflight["final_decision"]["training_authorized"] is False
    assert preflight["final_decision"]["fallback_dataset_training_sufficiency_claim"] is False


def test_split_assignments_are_stable_and_ignore_nonidentity_features() -> None:
    records = _records()
    report_a = build_reference_split_manifest(_dataset(records), enabled=True)
    changed = list(reversed([dict(record) for record in records]))
    for index, record in enumerate(changed):
        record["selected_index"] = index % 6
        record["candidate_rank"] = 5 - (index % 6)
        record["closed_loop_outcome"] = {"changed": index}
        record["learned_weights"] = [index, index + 1]
    report_b = build_reference_split_manifest(_dataset(changed), enabled=True)

    assignments_a = {
        item["record_identity_hash"]: item["split"]
        for item in report_a["record_assignments"]
    }
    assignments_b = {
        item["record_identity_hash"]: item["split"]
        for item in report_b["record_assignments"]
    }

    assert report_a["final_decision"]["passed"] is True
    assert report_b["final_decision"]["passed"] is True
    assert assignments_a == assignments_b


def test_rejects_forbidden_split_feature_sources() -> None:
    dataset = _dataset()
    dataset["split_feature_sources"] = [
        "record_identity_hash",
        "selected_index",
        "candidate_rank",
        "closed_loop_outcome",
        "learned_weights",
    ]

    errors = build_reference_split_manifest(dataset, enabled=True)["final_decision"]["errors"]

    for needle in [
        "selected_index_used_as_split_feature",
        "candidate_rank_used_as_split_feature",
        "closed_loop_outcome_used_as_split_feature",
        "learned_weights_used_as_split_feature",
    ]:
        assert needle in errors


def test_rejects_scope_identity_collision_and_formal_leakage() -> None:
    records = _records()
    records[0].pop("record_identity_hash")
    records[1]["source_log"] = records[2]["source_log"]
    records[1]["run_id"] = records[2]["run_id"]
    records[1]["record_index"] = records[2]["record_index"]
    records[3]["records_without_feasible_candidate"] = False
    records[4]["seed"] = 11
    records[5]["formal_eval_artifact_included"] = True

    errors = build_reference_split_manifest(
        _dataset(records),
        enabled=True,
    )["final_decision"]["errors"]

    for needle in [
        "record_identity_hash_missing",
        "group_key_collision",
        "record_identity_hash_mismatch",
        "feasible_candidate_record_included",
        "formal_seed_in_split_manifest",
        "formal_eval_artifact_record_included",
    ]:
        assert needle in errors


def test_contract_rejects_tampered_split_overlap_and_decision_leaks() -> None:
    report = build_reference_split_manifest(_dataset(), enabled=True)
    report["validation_groups"].append(report["training_groups"][0])
    report["record_assignments"].append(dict(report["record_assignments"][0]))
    report["final_decision"]["training_authorized"] = True
    report["final_decision"]["fallback_dataset_training_sufficiency_claim"] = True
    report["final_decision"]["deployable_checkpoint_claim_authorized"] = True
    report["final_decision"]["safety_benefit_claim_authorized"] = True
    report["final_decision"]["camp_over_dp_top1_claim_authorized"] = True

    errors = validate_split_manifest_report(report)

    for needle in [
        "split_train_validation_overlap",
        "duplicate_record_assignment",
        "record_counts_accepted_mismatch",
        "training_authorized_leak",
        "fallback_dataset_training_sufficiency_claim_leak",
        "deployable_checkpoint_claim_authorized_leak",
        "safety_benefit_claim_authorized_leak",
        "camp_over_dp_top1_claim_authorized_leak",
    ]:
        assert needle in errors


def test_manifest_pins_deterministic_policy_and_forbids_random_inputs() -> None:
    report = build_reference_split_manifest(_dataset(), enabled=True)

    assert report["split_policy"] == SPLIT_POLICY
    assert report["split_salt"] == SPLIT_SALT
    assert "random_seed" not in report
    assert "python_hash" not in report
    assert "wall_clock" not in report
    assert report["analysis"]["replay_executed"] is False
    assert report["analysis"]["candidate_generation_executed"] is False
    assert report["analysis"]["camp_training_executed"] is False
    assert report["analysis"]["diffusion_planner_modified"] is False


def test_preflight_rejects_scale_and_fallback_master_boundary_leaks(tmp_path: Path) -> None:
    report = build_reference_split_manifest(_dataset(), enabled=True)
    split = {
        "group_key_fields": report["group_key_fields"],
        "training_groups": report["training_groups"],
        "validation_groups": report["validation_groups"],
        "seeds": [21, 22],
        "formal_eval_artifact_included": False,
    }
    inputs = _preflight_inputs(tmp_path, split)
    scales = json.loads(inputs["train_only_scale_manifest_json"].read_text(encoding="utf-8"))
    master = json.loads(inputs["fallback_master_config_json"].read_text(encoding="utf-8"))

    scales["fit_groups"] = split["training_groups"] + split["validation_groups"][:1]
    scales["fit_seeds"] = [11]
    scales["formal_eval_artifact_included"] = True
    scales["atom_scales"]["jerk_early"] = 0.0
    master["fallback_only"] = False
    master["feasible_branch_records_allowed"] = True
    master["all_infeasible_records_added_to_feasible_training"] = True
    master["score_expression"] = "score_k(w)=nonlinear(a_k,w)"
    master["atoms_fixed_nonnegative"] = False
    master["simplex_cvar_l2_convex"] = False
    inputs["train_only_scale_manifest_json"].write_text(
        json.dumps(scales, sort_keys=True),
        encoding="utf-8",
    )
    inputs["fallback_master_config_json"].write_text(
        json.dumps(master, sort_keys=True),
        encoding="utf-8",
    )

    preflight = validate_training_sufficiency_preflight(enabled=True, **inputs)
    errors = set(preflight["final_decision"]["errors"])

    for needle in [
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
        "scale_fit_formal_seed_leak",
        "scale_fit_formal_eval_leak",
        "atom_scale_jerk_early_not_strictly_positive",
        "fallback_master_not_isolated",
        "feasible_branch_records_allowed_leak",
        "all_infeasible_records_added_to_feasible_training_leak",
        "score_expression_not_affine",
        "atoms_not_fixed_nonnegative",
        "convex_master_boundary_missing",
    ]:
        assert needle in errors


def test_current_head_f8f409b_split_manifest_unit_tests_revalidation_is_pinned() -> None:
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_split_manifest_unit_tests_head_f8f409b_revalidated",
        "unit_tests_base_head=f8f409b6b08fab9c0423278d5a7a52595e461379",
        "camp_origin_main_at_unit_tests=f8f409b6b08fab9c0423278d5a7a52595e461379",
        "github_refs_heads_main_at_unit_tests=f8f409b6b08fab9c0423278d5a7a52595e461379",
        "autodl_CAMP_HEAD_at_unit_tests=f8f409b6b08fab9c0423278d5a7a52595e461379",
        "autodl_CAMP_origin_main_at_unit_tests=f8f409b6b08fab9c0423278d5a7a52595e461379",
        "autodl_DP_HEAD_at_unit_tests=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_plan_status=fallback_risk_training_split_manifest_unit_tests_plan_head_84f24a1_revalidated",
        "head_f8f409b_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_f8f409b_validated_fallback_records=15",
        "head_f8f409b_validator_output_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "head_f8f409b_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_f8f409b_default_off_builder_requires_enable_flag=True",
        "head_f8f409b_disabled_mode_does_not_read_dataset=True",
        "head_f8f409b_clean_synthetic_manifest_preflight_compatible=True",
        "head_f8f409b_stable_split_ignores_nonidentity_features=True",
        "head_f8f409b_forbidden_split_feature_sources_rejected=True",
        "head_f8f409b_scope_identity_collision_and_formal_leakage_rejected=True",
        "head_f8f409b_split_overlap_and_decision_leaks_rejected=True",
        "head_f8f409b_deterministic_policy_and_no_random_inputs_pinned=True",
        "head_f8f409b_manifest_not_generated=True",
        "head_f8f409b_training_not_executed=True",
        "head_f8f409b_candidate_generation_not_executed=True",
        "head_f8f409b_dp_not_modified=True",
        "head_f8f409b_selector_or_atom_not_promoted=True",
        "head_f8f409b_local_split_manifest_contract_pytest=9 passed",
        "head_f8f409b_split_manifest_unit_tests_pinned=True",
        "head_f8f409b_training_split_manifest_builder_authorized=False",
        "this_split_manifest_unit_tests_gate_authorizes_builder_training_replay_dp_or_claims=False",
    ]:
        assert needle in audit


def test_current_head_cde90c0_split_manifest_unit_tests_revalidation_is_pinned() -> None:
    combined = (
        UNIT_TESTS_DOC.read_text(encoding="utf-8")
        + AUDIT_DOC.read_text(encoding="utf-8")
    )
    status = "status=fallback_risk_training_split_manifest_unit_tests_head_cde90c0_revalidated"

    assert status in combined

    for needle in [
        status,
        "unit_tests_base_head=cde90c05bb4baad5caf018fdba647da97f44fcee",
        "camp_origin_main_at_unit_tests=cde90c05bb4baad5caf018fdba647da97f44fcee",
        "github_refs_heads_main_at_unit_tests=cde90c05bb4baad5caf018fdba647da97f44fcee",
        "autodl_CAMP_HEAD_at_unit_tests=cde90c05bb4baad5caf018fdba647da97f44fcee",
        "autodl_CAMP_origin_main_at_unit_tests=cde90c05bb4baad5caf018fdba647da97f44fcee",
        "autodl_DP_HEAD_at_unit_tests=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_plan_status=fallback_risk_training_split_manifest_unit_tests_plan_head_8c6ab32_revalidated",
        "head_cde90c0_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_cde90c0_validated_fallback_records=15",
        "head_cde90c0_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_cde90c0_default_off_builder_requires_enable_flag=True",
        "head_cde90c0_disabled_mode_does_not_read_dataset=True",
        "head_cde90c0_clean_synthetic_manifest_preflight_compatible=True",
        "head_cde90c0_stable_split_ignores_nonidentity_features=True",
        "head_cde90c0_forbidden_split_feature_sources_rejected=True",
        "head_cde90c0_scope_identity_collision_and_formal_leakage_rejected=True",
        "head_cde90c0_split_overlap_and_decision_leaks_rejected=True",
        "head_cde90c0_deterministic_policy_and_no_random_inputs_pinned=True",
        "head_cde90c0_manifest_not_generated=True",
        "head_cde90c0_training_not_executed=True",
        "head_cde90c0_candidate_generation_not_executed=True",
        "head_cde90c0_dp_not_modified=True",
        "head_cde90c0_selector_or_atom_not_promoted=True",
        "head_cde90c0_local_split_manifest_contract_pytest=10 passed",
        "head_cde90c0_local_unit_tests_plan_pytest=12 passed",
        "head_cde90c0_local_static_contract_review_pytest=11 passed",
        "head_cde90c0_local_target_pytest=33 passed",
        "head_cde90c0_autodl_split_manifest_contract_pytest=10 passed",
        "head_cde90c0_autodl_unit_tests_plan_pytest=12 passed",
        "head_cde90c0_autodl_static_contract_review_pytest=11 passed",
        "head_cde90c0_autodl_target_pytest=33 passed",
        "head_cde90c0_split_manifest_unit_tests_pinned=True",
        "head_cde90c0_training_split_manifest_builder_authorized=False",
        "this_split_manifest_unit_tests_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_cde90c0_camp_training_authorized=False",
        "head_cde90c0_camp_retraining_authorized=False",
        "head_cde90c0_formal_seeds_11_12_13_authorized=False",
        "head_cde90c0_safety_benefit_claim_authorized=False",
        "head_cde90c0_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization_only",
    ]:
        assert needle in combined


def test_current_head_6540f09_split_manifest_unit_tests_revalidation_is_pinned() -> None:
    unit_tests_doc = UNIT_TESTS_DOC.read_text(encoding="utf-8")
    audit_tail = AUDIT_DOC.read_text(encoding="utf-8")[-22000:]
    combined = unit_tests_doc + audit_tail
    status = "status=fallback_risk_training_split_manifest_unit_tests_head_6540f09_revalidated"

    assert status in unit_tests_doc
    assert status in combined

    for needle in [
        status,
        "unit_tests_base_head=6540f0997d8273f423ba1ce78f0ebcc85dc893c9",
        "camp_origin_main_at_unit_tests=6540f0997d8273f423ba1ce78f0ebcc85dc893c9",
        "github_refs_heads_main_at_unit_tests=6540f0997d8273f423ba1ce78f0ebcc85dc893c9",
        "autodl_CAMP_HEAD_at_unit_tests=6540f0997d8273f423ba1ce78f0ebcc85dc893c9",
        "autodl_CAMP_origin_main_at_unit_tests=6540f0997d8273f423ba1ce78f0ebcc85dc893c9",
        "autodl_DP_HEAD_at_unit_tests=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_plan_status=fallback_risk_training_split_manifest_unit_tests_plan_head_350b666_revalidated",
        "head_6540f09_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_6540f09_validated_fallback_records=15",
        "head_6540f09_validator_output_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "head_6540f09_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_6540f09_default_off_builder_requires_enable_flag=True",
        "head_6540f09_disabled_mode_does_not_read_dataset=True",
        "head_6540f09_clean_synthetic_manifest_preflight_compatible=True",
        "head_6540f09_stable_split_ignores_nonidentity_features=True",
        "head_6540f09_forbidden_split_feature_sources_rejected=True",
        "head_6540f09_scope_identity_collision_and_formal_leakage_rejected=True",
        "head_6540f09_split_overlap_and_decision_leaks_rejected=True",
        "head_6540f09_deterministic_policy_and_no_random_inputs_pinned=True",
        "head_6540f09_manifest_not_generated=True",
        "head_6540f09_training_not_executed=True",
        "head_6540f09_candidate_generation_not_executed=True",
        "head_6540f09_dp_not_modified=True",
        "head_6540f09_selector_or_atom_not_promoted=True",
        "head_6540f09_autodl_temp_worktree=/root/autodl-tmp/camp_core_split_manifest_unit_tests_6540f09_verify_20260627T010000Z",
        "head_6540f09_autodl_split_manifest_contract_pytest=11 passed",
        "head_6540f09_autodl_unit_tests_plan_pytest=12 passed",
        "head_6540f09_autodl_static_contract_review_pytest=11 passed",
        "head_6540f09_autodl_target_pytest=34 passed",
        "head_6540f09_autodl_git_diff_check_exit=0",
        "head_6540f09_split_manifest_unit_tests_pinned=True",
        "head_6540f09_training_split_manifest_builder_authorized=False",
        "this_split_manifest_unit_tests_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_6540f09_camp_training_authorized=False",
        "head_6540f09_camp_retraining_authorized=False",
        "head_6540f09_formal_seeds_11_12_13_authorized=False",
        "head_6540f09_safety_benefit_claim_authorized=False",
        "head_6540f09_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization_only",
    ]:
        assert needle in combined


def test_current_head_b9a8b07_split_manifest_unit_tests_revalidation_is_pinned() -> None:
    unit_tests_doc = UNIT_TESTS_DOC.read_text(encoding="utf-8")
    audit_tail = AUDIT_DOC.read_text(encoding="utf-8")[-22000:]
    combined = unit_tests_doc + audit_tail
    status = "status=fallback_risk_training_split_manifest_unit_tests_head_b9a8b07_revalidated"

    assert status in audit_tail

    for needle in [
        status,
        "unit_tests_base_head=b9a8b07eb972c55ea9c7cff739076fe2783e5d25",
        "camp_origin_main_at_unit_tests=b9a8b07eb972c55ea9c7cff739076fe2783e5d25",
        "github_refs_heads_main_at_unit_tests=b9a8b07eb972c55ea9c7cff739076fe2783e5d25",
        "autodl_CAMP_HEAD_at_unit_tests=b9a8b07eb972c55ea9c7cff739076fe2783e5d25",
        "autodl_CAMP_origin_main_at_unit_tests=b9a8b07eb972c55ea9c7cff739076fe2783e5d25",
        "autodl_DP_HEAD_at_unit_tests=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_plan_status=fallback_risk_training_split_manifest_unit_tests_plan_head_9c0a160_revalidated",
        "head_b9a8b07_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_b9a8b07_validated_fallback_records=15",
        "head_b9a8b07_validator_output_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "head_b9a8b07_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_b9a8b07_default_off_builder_requires_enable_flag=True",
        "head_b9a8b07_disabled_mode_does_not_read_dataset=True",
        "head_b9a8b07_clean_synthetic_manifest_preflight_compatible=True",
        "head_b9a8b07_stable_split_ignores_nonidentity_features=True",
        "head_b9a8b07_forbidden_split_feature_sources_rejected=True",
        "head_b9a8b07_scope_identity_collision_and_formal_leakage_rejected=True",
        "head_b9a8b07_split_overlap_and_decision_leaks_rejected=True",
        "head_b9a8b07_deterministic_policy_and_no_random_inputs_pinned=True",
        "head_b9a8b07_scale_and_fallback_master_boundary_leaks_rejected=True",
        "head_b9a8b07_score_k(w)=a_k^T w",
        "head_b9a8b07_fixed_candidate_affine_reranking_boundary_pinned=True",
        "head_b9a8b07_trajectory_generation_or_modification_rejected=True",
        "head_b9a8b07_manifest_not_generated=True",
        "head_b9a8b07_training_not_executed=True",
        "head_b9a8b07_candidate_generation_not_executed=True",
        "head_b9a8b07_dp_not_modified=True",
        "head_b9a8b07_selector_or_atom_not_promoted=True",
        "head_b9a8b07_local_split_manifest_contract_pytest=13 passed",
        "head_b9a8b07_local_unit_tests_plan_pytest=13 passed",
        "head_b9a8b07_local_static_contract_review_pytest=12 passed",
        "head_b9a8b07_local_target_pytest=38 passed",
        "head_b9a8b07_autodl_split_manifest_contract_pytest=13 passed",
        "head_b9a8b07_autodl_unit_tests_plan_pytest=13 passed",
        "head_b9a8b07_autodl_static_contract_review_pytest=12 passed",
        "head_b9a8b07_autodl_target_pytest=38 passed",
        "head_b9a8b07_split_manifest_unit_tests_pinned=True",
        "head_b9a8b07_training_split_manifest_builder_authorized=False",
        "this_split_manifest_unit_tests_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_b9a8b07_camp_training_authorized=False",
        "head_b9a8b07_camp_retraining_authorized=False",
        "head_b9a8b07_formal_seeds_11_12_13_authorized=False",
        "head_b9a8b07_safety_benefit_claim_authorized=False",
        "head_b9a8b07_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization_only",
    ]:
        assert needle in combined


def test_audit_tail_records_split_manifest_builder_authorization_next_gate() -> None:
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-220:])

    assert (
        "status=fallback_risk_training_split_manifest_unit_tests_head_f8f409b_revalidated"
        in audit
    )
    assert (
        "status=fallback_risk_training_split_manifest_unit_tests_current_head_2a49147_autodl_sync_verified"
        in audit
    )
    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_authorization_current_head_eedbc1f_autodl_sync_verified"
        in audit
    )
    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_current_head_099b935_revalidated"
        in audit
    )
    assert "head_f8f409b_local_split_manifest_contract_pytest=9 passed" in audit
    assert (
        "source_revalidation_status=fallback_risk_training_split_manifest_unit_tests_current_head_9668754_revalidated"
        in audit
    )
    assert (
        "source_authorization_sync_status=fallback_risk_training_split_manifest_builder_implementation_authorization_current_head_eedbc1f_autodl_sync_verified"
        in audit
    )
    assert "current_head=099b935c7ab84cdd35ebafc097764bc7cf96354c" in audit
    assert "f8f409b_is_ancestor_of_current_head=True" in audit
    assert "training_execution_authorized_now=False" in audit
    assert (
        "this_split_manifest_unit_tests_gate_authorizes_builder_training_replay_dp_or_claims=False"
        in audit
    )
    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_autodl_sync_verified"
        in audit
    )
    assert (
        "this_builder_implementation_gate_authorizes_fixed_artifact_training_replay_dp_or_claims=False"
        in audit
    )
    assert (
        "status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_current_head_67db07f_revalidated"
        in audit
    )
    assert "head_67db07f_local_extended_target_pytest=39 passed" in audit
    assert "this_post_static_gate_authorizes_fixed_artifact_builder_run=False" in audit
    assert (
        "status=fallback_risk_training_split_manifest_unit_tests_head_6540f09_revalidated"
        in audit
    )
    assert "head_6540f09_local_split_manifest_contract_pytest=11 passed" in audit
    assert (
        "prior_split_manifest_unit_tests_plan_status=fallback_risk_training_split_manifest_unit_tests_plan_head_350b666_revalidated"
        in audit
    )
    assert (
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization_only"
        in audit
    )
