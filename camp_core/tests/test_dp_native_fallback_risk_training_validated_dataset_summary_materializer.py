from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_validated_dataset_summary import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    build_validated_dataset_summary_report,
    main,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    validate_training_sufficiency_preflight,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
VALIDATED_DATASET_SHA = "1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf"
VALIDATOR_STATUS = "dp_native_fallback_risk_training_data_validator_complete"
FORBIDDEN_FALSES = {
    "training_authorized": False,
    "camp_training_authorized": False,
    "camp_retraining_authorized": False,
    "candidate_generation_authorized": False,
    "dp_modification_authorized": False,
    "selector_promotion_authorized": False,
    "atom_promotion_authorized": False,
    "safety_benefit_claim_authorized": False,
    "camp_over_dp_top1_claim_authorized": False,
    "fallback_risk_training_authorized_now": False,
}


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[Path, str]:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _record(index: int) -> dict[str, Any]:
    return {
        "source_log": "log_a",
        "run_id": "run_0",
        "record_index": index,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
    }


def _dataset(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "records": [_record(index) for index in range(15)],
        "final_decision": {
            "status": "dp_native_fallback_risk_training_data_builder_complete",
            "passed": True,
            "errors": [],
            **FORBIDDEN_FALSES,
        },
    }
    payload.update(overrides)
    return payload


def _validator(dataset_sha: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "dp_native_fallback_risk_training_data_validator_report_v1",
        "source_hashes": {"dataset_json": dataset_sha},
        "record_counts": {"records_checked": 15, "failed_records": 0},
        "final_decision": {
            "status": VALIDATOR_STATUS,
            "passed": True,
            "errors": [],
            "validator_output_written": True,
            **FORBIDDEN_FALSES,
        },
    }
    payload.update(overrides)
    return payload


def _clean_inputs(tmp_path: Path) -> tuple[Path, str, Path, str]:
    dataset_path, dataset_sha = _write_json(tmp_path / "dataset.json", _dataset())
    validator_path, validator_sha = _write_json(
        tmp_path / "validator.json",
        _validator(dataset_sha),
    )
    return dataset_path, dataset_sha, validator_path, validator_sha


def _preflight_payload_paths(tmp_path: Path, summary_json: Path) -> dict[str, Path]:
    train = ["log_a|run_0|0", "log_a|run_0|1"]
    validation = ["log_b|run_1|0"]
    atom_scales = {name: 1.0 for name in APPROVED_ATOM_NAMES}
    return {
        "validated_dataset_summary_json": summary_json,
        "training_split_manifest_json": _write_json(
            tmp_path / "split.json",
            {
                "group_key_fields": ["source_log", "run_id", "record_index"],
                "training_groups": train,
                "validation_groups": validation,
                "seeds": [21, 22],
                "formal_eval_artifact_included": False,
            },
        )[0],
        "train_only_scale_manifest_json": _write_json(
            tmp_path / "scales.json",
            {
                "fit_groups": train,
                "fit_seeds": [21, 22],
                "formal_eval_artifact_included": False,
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "atom_scales": atom_scales,
            },
        )[0],
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
        )[0],
        "training_command_plan_json": _write_json(
            tmp_path / "command.json",
            {
                "training_command_authorization": False,
                "post_training_nonpromotion_plan_required": True,
                "development_holdout_acceptance_gate_required": True,
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
        )[0],
    }


def test_materializer_is_default_off_and_does_not_read_or_write_summary(tmp_path: Path) -> None:
    output_summary = tmp_path / "out" / "summary.json"
    output_md = tmp_path / "out" / "summary.md"

    exit_code = main(
        [
            "--dataset_json",
            str(tmp_path / "missing_dataset.json"),
            "--expected_dataset_sha256",
            "a" * 64,
            "--validator_output_json",
            str(tmp_path / "missing_validator.json"),
            "--expected_validator_output_sha256",
            "b" * 64,
            "--output_summary_json",
            str(output_summary),
            "--output_md",
            str(output_md),
        ]
    )
    report = build_validated_dataset_summary_report(
        dataset_json=tmp_path / "missing_dataset.json",
        expected_dataset_sha256="a" * 64,
        validator_output_json=tmp_path / "missing_validator.json",
        expected_validator_output_sha256="b" * 64,
        enabled=False,
    )

    assert exit_code == 0
    assert output_md.is_file()
    assert not output_summary.exists()
    assert report["source_hashes"] == {}
    assert report["final_decision"]["status"] == DISABLED_STATUS


def test_materializer_writes_preflight_compatible_summary(tmp_path: Path) -> None:
    dataset_path, dataset_sha, validator_path, validator_sha = _clean_inputs(tmp_path)
    output_summary = tmp_path / "out" / "validated_dataset_summary.json"
    output_md = tmp_path / "out" / "summary.md"

    exit_code = main(
        [
            "--dataset_json",
            str(dataset_path),
            "--expected_dataset_sha256",
            dataset_sha,
            "--validator_output_json",
            str(validator_path),
            "--expected_validator_output_sha256",
            validator_sha,
            "--enable_default_off_fallback_risk_training_validated_dataset_summary_materializer",
            "--output_summary_json",
            str(output_summary),
            "--output_md",
            str(output_md),
        ]
    )
    report = build_validated_dataset_summary_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_json=validator_path,
        expected_validator_output_sha256=validator_sha,
        enabled=True,
    )
    summary = json.loads(output_summary.read_text(encoding="utf-8"))
    preflight = validate_training_sufficiency_preflight(
        **_preflight_payload_paths(tmp_path, output_summary),
        enabled=True,
    )

    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert summary["sha256"] == dataset_sha
    assert summary["records"] == 15
    assert summary["validator_status"] == VALIDATOR_STATUS
    assert summary["validator_passed"] is True
    assert summary["training_sufficiency_claim"] is False
    assert summary["deployable_checkpoint_claim"] is False
    assert summary["source_validator_output_sha256"] == validator_sha
    assert preflight["final_decision"]["errors"] == ["validated_dataset_sha_mismatch"]
    assert "training_sufficiency_preflight_executed=False" in output_md.read_text(encoding="utf-8")


def test_materializer_rejects_sha_validator_status_and_record_count_mismatches(tmp_path: Path) -> None:
    dataset_path, dataset_sha, validator_path, validator_sha = _clean_inputs(tmp_path)
    validator = json.loads(validator_path.read_text(encoding="utf-8"))
    validator["source_hashes"]["dataset_json"] = "0" * 64
    validator["record_counts"]["records_checked"] = 14
    validator["record_counts"]["failed_records"] = 1
    validator["final_decision"]["status"] = "wrong"
    validator["final_decision"]["passed"] = False
    validator_path, _ = _write_json(tmp_path / "bad_validator.json", validator)

    errors = build_validated_dataset_summary_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_json=validator_path,
        expected_validator_output_sha256=validator_sha,
        enabled=True,
    )["final_decision"]["errors"]

    for needle in [
        "validator_output_sha256_mismatch",
        "validator_dataset_sha256_mismatch",
        "validator_records_checked_mismatch",
        "validator_failed_records_nonzero",
        "validator_status_not_complete",
        "validator_not_passed",
    ]:
        assert needle in errors


def test_materializer_rejects_training_dp_promotion_and_claim_leaks(tmp_path: Path) -> None:
    dataset_path, dataset_sha = _write_json(
        tmp_path / "dataset.json",
        _dataset(training_sufficiency_claim=True, deployable_checkpoint_claim=True),
    )
    validator = _validator(dataset_sha, training_sufficiency_claim=True)
    validator["final_decision"]["camp_training_authorized"] = True
    validator["final_decision"]["camp_retraining_authorized"] = True
    validator["final_decision"]["candidate_generation_authorized"] = True
    validator["final_decision"]["dp_modification_authorized"] = True
    validator["final_decision"]["selector_promotion_authorized"] = True
    validator["final_decision"]["atom_promotion_authorized"] = True
    validator["final_decision"]["safety_benefit_claim_authorized"] = True
    validator_path, validator_sha = _write_json(tmp_path / "validator.json", validator)

    errors = build_validated_dataset_summary_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_json=validator_path,
        expected_validator_output_sha256=validator_sha,
        enabled=True,
    )["final_decision"]["errors"]

    for needle in [
        "training_sufficiency_claim_leak",
        "deployable_checkpoint_claim_leak",
        "validator_training_sufficiency_claim_leak",
        "validator_final_decision_camp_training_authorized_not_false",
        "validator_final_decision_camp_retraining_authorized_not_false",
        "validator_final_decision_candidate_generation_authorized_not_false",
        "validator_final_decision_dp_modification_authorized_not_false",
        "validator_final_decision_selector_promotion_authorized_not_false",
        "validator_final_decision_atom_promotion_authorized_not_false",
        "validator_final_decision_safety_benefit_claim_authorized_not_false",
    ]:
        assert needle in errors


def test_materializer_rejects_dataset_record_count_and_final_decision_leaks(tmp_path: Path) -> None:
    dataset = _dataset()
    dataset["records"] = dataset["records"][:14]
    dataset["final_decision"]["passed"] = False
    dataset["final_decision"]["camp_training_authorized"] = True
    dataset_path, dataset_sha = _write_json(tmp_path / "dataset.json", dataset)
    validator_path, validator_sha = _write_json(tmp_path / "validator.json", _validator(dataset_sha))

    errors = build_validated_dataset_summary_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        validator_output_json=validator_path,
        expected_validator_output_sha256=validator_sha,
        enabled=True,
    )["final_decision"]["errors"]

    assert "dataset_record_count_mismatch" in errors
    assert "dataset_final_decision_not_passed" in errors
    assert "dataset_final_decision_camp_training_authorized_not_false" in errors
    assert "dataset_validator_record_count_mismatch" in errors
