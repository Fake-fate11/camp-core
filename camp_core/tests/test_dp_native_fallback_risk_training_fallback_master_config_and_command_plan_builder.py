from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_fallback_master_config_and_command_plan import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    build_master_command_report,
    main,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
    validate_training_sufficiency_preflight,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
SPLIT_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_split_manifest_v1"
SCALE_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_train_only_scale_manifest_v1"
VALIDATED_DATASET_SHA = "1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf"


def _group(source_log: str, run_id: str, record_index: int) -> str:
    return f"{source_log}|{run_id}|{record_index}"


def _record(source_log: str, run_id: str, record_index: int, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_log": source_log,
        "run_id": run_id,
        "record_index": record_index,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
    }
    payload.update(overrides)
    return payload


def _dataset(records: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "records": records,
        "final_decision": {
            "status": "dp_native_fallback_risk_training_data_builder_complete",
            "passed": True,
            "errors": [],
            "training_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
        },
    }
    payload.update(overrides)
    return payload


def _split(
    *,
    training_groups: list[str],
    validation_groups: list[str],
    seeds: list[int] | None = None,
    formal_eval_artifact_included: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": SPLIT_MANIFEST_SCHEMA_VERSION,
        "group_key_fields": ["source_log", "run_id", "record_index"],
        "training_groups": training_groups,
        "validation_groups": validation_groups,
        "seeds": seeds or [21, 22],
        "formal_eval_artifact_included": formal_eval_artifact_included,
        "final_decision": {
            "status": "dp_native_fallback_risk_training_split_manifest_builder_complete",
            "passed": True,
            "errors": [],
            "training_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _scale(
    *,
    dataset_sha: str,
    split_sha: str,
    training_groups: list[str],
    validation_groups: list[str],
    seeds: list[int] | None = None,
    atom_schema_version: str = APPROVED_ATOM_SCHEMA,
    atom_scales: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCALE_MANIFEST_SCHEMA_VERSION,
        "source_dataset_sha256": dataset_sha,
        "source_split_manifest_sha256": split_sha,
        "fit_groups": training_groups,
        "excluded_validation_groups": validation_groups,
        "fit_seeds": seeds or [21, 22],
        "formal_eval_artifact_included": False,
        "atom_schema_version": atom_schema_version,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atom_scales": atom_scales or {name: 1.0 for name in APPROVED_ATOM_NAMES},
        "final_decision": {
            "status": "dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete",
            "passed": True,
            "errors": [],
            "training_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> tuple[Path, str]:
    path = tmp_path / name
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_inputs(tmp_path: Path) -> tuple[Path, str, Path, str, Path, str, dict[str, Any], dict[str, Any]]:
    train = [_group("log_a", "run_0", 0), _group("log_a", "run_0", 1)]
    validation = [_group("log_b", "run_1", 0)]
    dataset_path, dataset_sha = _write_json(
        tmp_path,
        "dataset.json",
        _dataset(
            [
                _record("log_a", "run_0", 0),
                _record("log_a", "run_0", 1),
                _record("log_b", "run_1", 0),
            ]
        ),
    )
    split = _split(training_groups=train, validation_groups=validation)
    split_path, split_sha = _write_json(tmp_path, "split.json", split)
    scales = _scale(
        dataset_sha=dataset_sha,
        split_sha=split_sha,
        training_groups=train,
        validation_groups=validation,
    )
    scale_path, scale_sha = _write_json(tmp_path, "scales.json", scales)
    return dataset_path, dataset_sha, split_path, split_sha, scale_path, scale_sha, split, scales


def _preflight_dataset_summary(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path,
        "validated_dataset_summary.json",
        {
            "sha256": VALIDATED_DATASET_SHA,
            "records": 15,
            "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
            "validator_passed": True,
            "training_sufficiency_claim": False,
            "deployable_checkpoint_claim": False,
        },
    )[0]


def test_master_command_builder_is_default_off_and_does_not_read_or_write_inputs(tmp_path: Path) -> None:
    output_master = tmp_path / "out" / "master.json"
    output_command = tmp_path / "out" / "command.json"
    output_md = tmp_path / "out" / "summary.md"

    exit_code = main(
        [
            "--dataset_json",
            str(tmp_path / "missing_dataset.json"),
            "--expected_dataset_sha256",
            "a" * 64,
            "--training_split_manifest_json",
            str(tmp_path / "missing_split.json"),
            "--expected_split_manifest_sha256",
            "b" * 64,
            "--train_only_scale_manifest_json",
            str(tmp_path / "missing_scales.json"),
            "--expected_scale_manifest_sha256",
            "c" * 64,
            "--output_master_config_json",
            str(output_master),
            "--output_training_command_plan_json",
            str(output_command),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert output_md.is_file()
    assert not output_master.exists()
    assert not output_command.exists()
    report = build_master_command_report(
        dataset_json=tmp_path / "missing_dataset.json",
        expected_dataset_sha256="a" * 64,
        training_split_manifest_json=tmp_path / "missing_split.json",
        expected_split_manifest_sha256="b" * 64,
        train_only_scale_manifest_json=tmp_path / "missing_scales.json",
        expected_scale_manifest_sha256="c" * 64,
        enabled=False,
    )
    assert report["source_hashes"] == {}
    assert report["final_decision"]["status"] == DISABLED_STATUS


def test_master_command_builder_writes_preflight_compatible_manifests(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, scale_path, scale_sha, split, _ = _clean_inputs(tmp_path)
    output_master = tmp_path / "out" / "master.json"
    output_command = tmp_path / "out" / "command.json"
    output_md = tmp_path / "out" / "summary.md"

    exit_code = main(
        [
            "--dataset_json",
            str(dataset_path),
            "--expected_dataset_sha256",
            dataset_sha,
            "--training_split_manifest_json",
            str(split_path),
            "--expected_split_manifest_sha256",
            split_sha,
            "--train_only_scale_manifest_json",
            str(scale_path),
            "--expected_scale_manifest_sha256",
            scale_sha,
            "--enable_default_off_fallback_risk_training_master_command_builder",
            "--output_master_config_json",
            str(output_master),
            "--output_training_command_plan_json",
            str(output_command),
            "--output_md",
            str(output_md),
        ]
    )
    report = build_master_command_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        train_only_scale_manifest_json=scale_path,
        expected_scale_manifest_sha256=scale_sha,
        enabled=True,
    )
    preflight = validate_training_sufficiency_preflight(
        validated_dataset_summary_json=_preflight_dataset_summary(tmp_path),
        training_split_manifest_json=split_path,
        train_only_scale_manifest_json=scale_path,
        fallback_master_config_json=output_master,
        training_command_plan_json=output_command,
        enabled=True,
    )

    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert output_master.is_file()
    assert output_command.is_file()
    assert json.loads(output_master.read_text(encoding="utf-8"))["score_expression"] == "score_k(w)=a_k^T w"
    command = json.loads(output_command.read_text(encoding="utf-8"))
    assert command["training_command_authorization"] is False
    assert command["camp_training_authorized"] is False
    assert split["training_groups"]
    assert preflight["final_decision"]["status"] == PREFLIGHT_COMPLETE_STATUS
    assert "training_execution_authorized=False" in output_md.read_text(encoding="utf-8")


def test_master_command_builder_rejects_sha_split_and_scale_scope_errors(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, scale_path, scale_sha, split, scales = _clean_inputs(tmp_path)
    split["training_groups"].append(split["validation_groups"][0])
    scales["fit_groups"] = split["validation_groups"]
    dataset = json.loads(dataset_path.read_text())
    dataset["records"].append(_record("log_extra", "run_x", 9))
    dataset_path, _ = _write_json(tmp_path, "bad_dataset.json", dataset)
    split_path, _ = _write_json(tmp_path, "bad_split.json", split)
    scale_path, _ = _write_json(tmp_path, "bad_scales.json", scales)

    report = build_master_command_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        train_only_scale_manifest_json=scale_path,
        expected_scale_manifest_sha256=scale_sha,
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "dataset_sha256_mismatch",
        "split_manifest_sha256_mismatch",
        "scale_manifest_sha256_mismatch",
        "training_validation_overlap",
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
    ]:
        assert needle in errors


def test_master_command_builder_rejects_formal_leaks_and_bad_scale_atoms(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, scale_path, scale_sha, split, scales = _clean_inputs(tmp_path)
    split["seeds"] = [11]
    split["formal_eval_artifact_included"] = True
    scales["fit_seeds"] = [12]
    scales["formal_eval_artifact_included"] = True
    scales["atom_schema_version"] = "wrong"
    scales["atom_scales"]["jerk_early"] = 0.0
    split_path, split_sha = _write_json(tmp_path, "bad_split.json", split)
    scales["source_split_manifest_sha256"] = split_sha
    scale_path, scale_sha = _write_json(tmp_path, "bad_scales.json", scales)

    errors = build_master_command_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        train_only_scale_manifest_json=scale_path,
        expected_scale_manifest_sha256=scale_sha,
        enabled=True,
    )["final_decision"]["errors"]

    for needle in [
        "formal_seed_in_split",
        "formal_eval_artifact_included",
        "scale_fit_formal_seed_leak",
        "scale_fit_formal_eval_leak",
        "scale_atom_schema_mismatch",
        "atom_scale_jerk_early_not_strictly_positive",
    ]:
        assert needle in errors


def test_master_command_builder_rejects_dataset_decision_training_and_claim_leaks(tmp_path: Path) -> None:
    train = [_group("log_a", "run_0", 0)]
    validation = [_group("log_b", "run_1", 0)]
    dataset = _dataset(
        [_record("log_a", "run_0", 0), _record("log_b", "run_1", 0)],
        training_sufficiency_claim=True,
        deployable_checkpoint_claim=True,
    )
    dataset["final_decision"]["camp_training_authorized"] = True
    dataset_path, dataset_sha = _write_json(tmp_path, "dataset.json", dataset)
    split_path, split_sha = _write_json(
        tmp_path,
        "split.json",
        _split(training_groups=train, validation_groups=validation),
    )
    scale_path, scale_sha = _write_json(
        tmp_path,
        "scales.json",
        _scale(
            dataset_sha=dataset_sha,
            split_sha=split_sha,
            training_groups=train,
            validation_groups=validation,
        ),
    )

    errors = build_master_command_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        train_only_scale_manifest_json=scale_path,
        expected_scale_manifest_sha256=scale_sha,
        enabled=True,
    )["final_decision"]["errors"]

    assert "dataset_final_decision_camp_training_authorized_not_false" in errors
    assert "training_sufficiency_claim_leak" in errors
    assert "deployable_checkpoint_claim_leak" in errors


def test_master_command_builder_outputs_keep_training_dp_and_promotion_false(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, scale_path, scale_sha, _, _ = _clean_inputs(tmp_path)

    report = build_master_command_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        train_only_scale_manifest_json=scale_path,
        expected_scale_manifest_sha256=scale_sha,
        enabled=True,
    )
    master = report["fallback_master_config"]
    command = report["training_command_plan"]
    decision = report["final_decision"]

    assert master["fallback_only"] is True
    assert master["feasible_branch_records_allowed"] is False
    assert master["all_infeasible_records_added_to_feasible_training"] is False
    assert master["hard_feasibility_relaxation_authorized"] is False
    assert master["fallback_label_is_deployed_atom"] is False
    assert command["training_execution_authorized"] is False
    assert command["dp_modification_authorized"] is False
    assert command["selector_promotion_authorized"] is False
    assert command["atom_promotion_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["fallback_risk_training_authorized_now"] is False
