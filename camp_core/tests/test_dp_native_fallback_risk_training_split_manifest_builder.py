from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_split_manifest import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    SPLIT_MANIFEST_SCHEMA_VERSION,
    build_split_manifest_report,
    main,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
    validate_training_sufficiency_preflight,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
VALIDATOR_SHA = "572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b"
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex(char: str) -> str:
    return char * 64


def _record(index: int, *, source_log: str | None = None) -> dict[str, Any]:
    source = source_log or f"/synthetic/source_{index:02d}/camp_selection_log.json"
    record = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_log": source,
        "source_log_sha256": _hex(chr(ord("a") + index % 6)),
        "run_id": f"run_{index % 3}",
        "record_index": index,
        "candidate_count": 6,
        "selected_index": (index + 1) % 6,
        "oracle_index": index % 6,
        "oracle_policy": ["red", "lane", "quality"],
        "costs": [],
        "margins": [0.0 for _ in range(6)],
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }
    record["record_identity_hash"] = _record_identity_hash(record)
    return record


def _record_identity_hash(record: dict[str, Any]) -> str:
    identity = {
        "source_log": record.get("source_log"),
        "source_log_sha256": record.get("source_log_sha256"),
        "run_id": record.get("run_id"),
        "record_index": record.get("record_index"),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dataset(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    records = records or [_record(index) for index in range(15)]
    source_hashes = {
        record["source_log"]: record["source_log_sha256"] for record in records
    }
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_hashes": source_hashes,
        "record_counts": {
            "records_total": len(records),
            "records_without_feasible_candidate": len(records),
            "records_with_feasible_candidate": 0,
            "records_built": len(records),
            "failed_records": 0,
        },
        "records": records,
        "failed_records": [],
        "final_decision": {
            "status": "dp_native_fallback_risk_training_data_builder_complete",
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": False,
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
        },
    }


def _write_dataset(tmp_path: Path, payload: dict[str, Any]) -> tuple[Path, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, _sha256_file(path)


def _build(tmp_path: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    dataset_path, dataset_sha = _write_dataset(tmp_path, payload or _dataset())
    return build_split_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=True,
    )


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _preflight_inputs(tmp_path: Path, split: dict[str, Any]) -> dict[str, Path]:
    return {
        "validated_dataset_summary_json": _write(
            tmp_path / "validated_dataset.json",
            {
                "sha256": split["dataset_sha256"],
                "records": 15,
                "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
                "validator_passed": True,
                "training_sufficiency_claim": False,
                "deployable_checkpoint_claim": False,
            },
        ),
        "training_split_manifest_json": _write(tmp_path / "split.json", split),
        "train_only_scale_manifest_json": _write(
            tmp_path / "scales.json",
            {
                "fit_groups": split["training_groups"],
                "fit_seeds": [21, 22],
                "formal_eval_artifact_included": False,
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "atom_scales": {name: 1.0 for name in APPROVED_ATOM_NAMES},
            },
        ),
        "fallback_master_config_json": _write(
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
        "training_command_plan_json": _write(
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


def test_split_builder_is_default_off_and_does_not_read_missing_dataset(tmp_path: Path) -> None:
    report = build_split_manifest_report(
        dataset_json=tmp_path / "missing.json",
        expected_dataset_sha256=_hex("a"),
        validator_output_sha256=VALIDATOR_SHA,
        enabled=False,
    )

    assert report["schema_version"] == SPLIT_MANIFEST_SCHEMA_VERSION
    assert report["source_hashes"] == {}
    assert report["record_assignments"] == []
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True


def test_split_builder_enabled_writes_preflight_compatible_manifest(tmp_path: Path) -> None:
    dataset_path, dataset_sha = _write_dataset(tmp_path, _dataset())
    output_json = tmp_path / "out" / "split.json"
    output_md = tmp_path / "out" / "split.md"

    report = build_split_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=True,
    )
    exit_code = main(
        [
            "--dataset_json",
            str(dataset_path),
            "--expected_dataset_sha256",
            dataset_sha,
            "--validator_output_sha256",
            VALIDATOR_SHA,
            "--enable_default_off_fallback_risk_training_split_manifest_builder",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )
    written = json.loads(output_json.read_text(encoding="utf-8"))
    preflight = validate_training_sufficiency_preflight(
        enabled=True,
        **_preflight_inputs(tmp_path, written),
    )

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["dataset_sha256"] == dataset_sha
    assert report["validator_output_sha256"] == VALIDATOR_SHA
    assert report["record_counts"]["accepted_records"] == 15
    assert report["record_counts"]["training_records"] >= 1
    assert report["record_counts"]["validation_records"] >= 1
    assert exit_code == 0
    assert written["final_decision"]["status"] == COMPLETE_STATUS
    assert preflight["final_decision"]["status"] != PREFLIGHT_COMPLETE_STATUS
    assert preflight["final_decision"]["errors"] == ["validated_dataset_sha_mismatch"]
    assert "training_authorized=False" in output_md.read_text(encoding="utf-8")


def test_split_builder_rejects_dataset_sha_validator_sha_and_top_level_errors(
    tmp_path: Path,
) -> None:
    payload = _dataset()
    payload["schema_version"] = "wrong"
    payload["record_counts"]["records_built"] = 14
    payload["final_decision"]["passed"] = False
    dataset_path, _dataset_sha = _write_dataset(tmp_path, payload)

    report = build_split_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=_hex("0"),
        validator_output_sha256="not-a-sha",
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "dataset_sha256_mismatch",
        "validator_output_sha256_invalid",
        "dataset_schema_version_mismatch",
        "records_built_count_mismatch",
        "final_decision_not_passed",
    ]:
        assert needle in errors


def test_split_builder_rejects_identity_collision_and_formal_leaks(tmp_path: Path) -> None:
    records = [_record(index) for index in range(15)]
    records[1]["source_log"] = records[2]["source_log"]
    records[1]["source_log_sha256"] = records[2]["source_log_sha256"]
    records[1]["run_id"] = records[2]["run_id"]
    records[1]["record_index"] = records[2]["record_index"]
    records[3]["source_log_sha256"] = _hex("f")
    records[4]["oracle_index"] = 99
    records[5]["seed"] = 11
    records[6]["formal_eval_artifact_included"] = True
    records[7]["selected_index_used_as_feature"] = True
    records[8]["candidate_rank_used_as_feature"] = True
    records[9].pop("record_identity_hash")

    payload = _dataset(records)
    payload["source_hashes"][records[3]["source_log"]] = _hex("a")
    errors = _build(tmp_path, payload)["final_decision"]["errors"]

    for needle in [
        "record_1:record_identity_hash_mismatch",
        "record_2:group_key_collision",
        "record_2:duplicate_record_identity",
        "record_3:source_log_sha256_mismatch",
        "record_3:record_identity_hash_mismatch",
        "record_4:oracle_index_invalid",
        "record_5:formal_seed_in_split_manifest",
        "record_6:formal_eval_artifact_record_included",
        "record_7:selected_index_used_as_feature_leak",
        "record_8:candidate_rank_used_as_feature_leak",
        "record_9:record_identity_hash_missing",
    ]:
        assert needle in errors


def test_split_builder_assignments_are_order_stable_and_ignore_selected_index(
    tmp_path: Path,
) -> None:
    records = [_record(index) for index in range(15)]
    report_a = _build(tmp_path / "a", _dataset(records))
    changed = list(reversed([copy.deepcopy(record) for record in records]))
    for index, record in enumerate(changed):
        record["selected_index"] = index % 6
    report_b = _build(tmp_path / "b", _dataset(changed))

    assignments_a = {
        item["record_identity_hash"]: item["split"]
        for item in report_a["record_assignments"]
    }
    assignments_b = {
        item["record_identity_hash"]: item["split"]
        for item in report_b["record_assignments"]
    }

    assert report_a["final_decision"]["status"] == COMPLETE_STATUS
    assert report_b["final_decision"]["status"] == COMPLETE_STATUS
    assert assignments_a == assignments_b


def test_split_builder_final_decision_keeps_training_and_claims_false(tmp_path: Path) -> None:
    report = _build(tmp_path, _dataset())
    decision = report["final_decision"]

    assert decision["training_authorized"] is False
    assert decision["fallback_dataset_training_sufficiency_claim"] is False
    assert decision["camp_retraining_authorized_now"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False


def test_split_builder_accepts_missing_legacy_final_decision_forbidden_flag(
    tmp_path: Path,
) -> None:
    payload = _dataset()
    payload["final_decision"].pop("fallback_risk_training_authorized_now")

    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["final_decision"]["fallback_risk_training_authorized_now"] is False


def test_split_builder_rejects_explicit_true_or_nonfalse_forbidden_flags(
    tmp_path: Path,
) -> None:
    true_payload = _dataset()
    true_payload["final_decision"]["fallback_risk_training_authorized_now"] = True
    nonfalse_payload = _dataset()
    nonfalse_payload["final_decision"]["candidate_generation_authorized"] = "false"

    true_errors = _build(tmp_path / "true", true_payload)["final_decision"]["errors"]
    nonfalse_errors = _build(tmp_path / "nonfalse", nonfalse_payload)["final_decision"][
        "errors"
    ]

    assert "final_decision_fallback_risk_training_authorized_now_not_false" in true_errors
    assert "final_decision_candidate_generation_authorized_not_false" in nonfalse_errors


def test_audit_records_split_manifest_builder_static_contract_and_current_next_gate() -> None:
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-160:])

    assert "status=fallback_risk_training_split_manifest_builder_implementation_current_head_revalidated" in audit
    assert "local_target_pytest=9 passed" in audit
    assert "training_execution_authorized_now=False" in audit
    assert "status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_passed" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_audit_only`"
    )
