from __future__ import annotations

import json

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.validate_dp_native_training_data_contract import (
    PROVENANCE_SCHEMA_VERSION,
    main,
    validate_logs,
    validate_record,
)


def _sha(value: str) -> str:
    return value * 64


def _valid_record() -> dict[str, object]:
    version, names = atom_schema_for_dimension(9)
    return {
        "selected_index": 1,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": [
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.1, 0.4, 0.3, 0.6, 0.5, 0.8, 0.7, 1.0],
        ],
        "feasible_mask": [True, True],
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 2,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "camp_candidate_tensor_provenance": {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "candidate_count": 2,
            "post_selector_candidate_count": 2,
            "selected_index": 1,
            "pre_camp_scoring_tensor": {
                "sha256": _sha("a"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
            "post_camp_selector_tensor": {
                "sha256": _sha("a"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "candidate_closed_loop_outcomes": [
            {"candidate_index": 0, "value": 0.0, "feasible": True},
            {"candidate_index": 1, "value": 1.0, "feasible": True},
        ],
    }


def _valid_default_off_shadow_record() -> dict[str, object]:
    record = _valid_record()
    record["selected_index"] = 0
    record["executed_index"] = 0
    record["shadow_selected_index"] = 1
    record["camp_candidate_tensor_provenance"] = None
    record["default_off_shadow_selector"] = {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "enabled": True,
        "default_off": True,
        "artifact_contract_ready": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "score_expression": "score_k(w)=a_k^T w",
        "selection_effect": False,
        "online_selector_change": False,
        "failed_closed_reason": None,
        "executed_index": 0,
        "shadow_selected_index": 1,
        "candidate_tensor_hash": {
            "sha256": _sha("b"),
            "shape": [2, 80, 4],
            "dtype": "float32",
            "hash_input": "contiguous_candidate_tensor_bytes",
            "nan_policy": "preserve_tensor_bytes",
        },
    }
    return record


def test_valid_record_satisfies_clean_dp_native_contract() -> None:
    assert validate_record(_valid_record()) == []


def test_valid_default_off_shadow_record_satisfies_clean_dp_native_contract() -> None:
    assert validate_record(_valid_default_off_shadow_record()) == []


def test_validator_rejects_missing_provenance() -> None:
    record = _valid_record()
    record.pop("camp_candidate_tensor_provenance")

    assert validate_record(record) == ["camp_candidate_tensor_provenance_missing"]


def test_validator_rejects_candidate_generation_route_changes() -> None:
    record = _valid_record()
    contract = record["candidate_generation_contract"]
    assert isinstance(contract, dict)
    contract["noise_strategy"] = "antithetic"
    contract["guidance_enabled"] = True
    contract["reference_blend_steps"] = 4

    errors = validate_record(record)

    assert "candidate_generation_contract_noise_strategy_not_iid" in errors
    assert "candidate_generation_contract_guidance_enabled" in errors
    assert "candidate_generation_contract_reference_blend_enabled" in errors


def test_validator_rejects_tensor_mutation_and_outcome_leakage() -> None:
    record = _valid_record()
    payload = record["camp_candidate_tensor_provenance"]
    assert isinstance(payload, dict)
    payload["payload_valid"] = False
    payload["pre_post_tensor_hash_equal"] = False
    payload["no_coordinate_heading_speed_rewrite_by_camp"] = False
    payload["outcome_label_input"] = True

    errors = validate_record(record)

    assert "provenance_payload_valid_not_true" in errors
    assert "provenance_pre_post_tensor_hash_equal_not_true" in errors
    assert "provenance_no_coordinate_heading_speed_rewrite_by_camp_not_true" in errors
    assert "provenance_outcome_label_input_not_false" in errors


def test_validator_rejects_default_off_shadow_selector_contract_drift() -> None:
    record = _valid_default_off_shadow_record()
    record["selected_index"] = 1
    payload = record["default_off_shadow_selector"]
    assert isinstance(payload, dict)
    payload["selection_effect"] = True
    payload["executed_index"] = 1
    tensor_hash = payload["candidate_tensor_hash"]
    assert isinstance(tensor_hash, dict)
    tensor_hash["sha256"] = "not-a-sha"
    tensor_hash["shape"] = [3, 80, 4]

    errors = validate_record(record)

    assert "default_off_shadow_selector_selection_effect_mismatch" in errors
    assert "default_off_shadow_selector_executed_index_mismatch" in errors
    assert "default_off_shadow_selector_selected_index_not_dp_top1" in errors
    assert "default_off_shadow_selector_tensor_sha256_missing_or_invalid" in errors
    assert "default_off_shadow_selector_tensor_shape_invalid" in errors


def test_validator_rejects_count_and_schema_mismatches() -> None:
    record = _valid_record()
    record["atom_schema_version"] = "wrong"
    record["feasible_mask"] = [True]
    payload = record["camp_candidate_tensor_provenance"]
    assert isinstance(payload, dict)
    payload["candidate_count"] = 3
    payload["selected_index"] = 0

    errors = validate_record(record)

    assert "atom_schema_version_mismatch" in errors
    assert "feasible_mask_candidate_count_mismatch" in errors
    assert "provenance_candidate_count_mismatch" in errors
    assert "provenance_selected_index_mismatch" in errors


def test_validate_logs_reports_read_only_contract(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([_valid_record()]), encoding="utf-8")

    report = validate_logs([log_path])

    assert report["passed"] is True
    assert report["records"] == 1
    assert report["failed_records"] == []
    assert report["read_only"] is True
    assert report["replay_executed"] is False
    assert report["candidate_generation_executed"] is False
    assert report["training_execution_authorized"] is False
    assert report["future_training_input_contract_satisfied"] is True


def test_validate_logs_reports_failed_records(tmp_path) -> None:
    record = _valid_record()
    record["selected_index"] = 3
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    report = validate_logs([tmp_path])

    assert report["passed"] is False
    assert report["records"] == 1
    assert report["failed_records"][0]["record_index"] == 0
    assert "selected_index_out_of_range" in report["failed_records"][0]["errors"]


def test_validator_cli_writes_read_only_reports(tmp_path, capsys) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    log_path.write_text(json.dumps([_valid_record()]), encoding="utf-8")

    exit_code = main(
        [
            "--selection_log",
            str(log_path),
            "--output_json",
            str(json_path),
            "--output_md",
            str(md_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(json_path.read_text(encoding="utf-8"))["passed"] is True
    markdown = md_path.read_text(encoding="utf-8")
    assert "Replay executed: `False`" in markdown
    assert "Training execution authorized: `False`" in markdown
    assert '"passed": true' in capsys.readouterr().out
