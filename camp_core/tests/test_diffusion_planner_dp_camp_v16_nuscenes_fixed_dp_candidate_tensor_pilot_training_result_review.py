from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result.py"
)
HEAD = "251cb54cb42ec41fc2c5d4aba3d59d8bc87c70f2"
SOURCE_ROOT_SHA = "92ebe656b28a61b27a5317cf48e41f38a0c1f5d7f333323e2fdaeeb8c8dcd493"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_"
    "0ffbf63faa_20260708T123012CST"
)
REVIEW_CAMP_HEAD = "0ffbf63faa26f2b04d3ffe6ed3c976595cf73c09"
SOURCE_CAMP_HEAD = "2f0448ad80abb5b858595c904d4bd6c2de3930a0"
REVIEW_JSON_SHA = "db09ad1d3cf01eddb5e40297e050b872e7090d0c106a9a79b98cff27353507d9"
REVIEW_MD_SHA = "db9cc64c2c71ee2e902d4b1d90a8e50484a69533c50af32764f83348772a4d87"
REVIEW_SHA256SUMS_SHA = "40f42c459041fd34d5b817d17fbc7d35d6c855fac3cfced192943ba05d153e42"
REVIEW_ROOT_SHA256SUMS_SHA = "cc473adda4e6f875187eb141f7df61937f423a1b18107a5163c159ac09d642fc"
REVIEW_HEADS_SHA = "b027f7e18aa94feeba881dbfeca00cad3d199ae7a518dc139f8c4ed22ee39082"
REVIEW_COMMAND_SHA = "115e40c1b9e057b194218d6d8911cde4e7bc50d6b7dcb9664133e89a24990344"
REVIEW_COMMAND_SHELL_SHA = "365263e83072725d8fcd12132b8e58001b59309cfe0c67ccc5b34736c97e2600"
REVIEW_STDOUT_SHA = "a273e4bbf5115d61983a64158394098ab48b02205438b20fdcbe58f8ae98393e"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_training_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_training_result_review_passes_train_only_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["training_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["training_executed_by_review"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["train_records"] == 863
    assert review["calibration_records_used_for_training"] == 0
    assert review["holdout_records_used_for_training"] == 0
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["train_k_values"] == [8]
    assert review["train_candidate_count_values"] == [8]
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["closed_loop_outcomes_used_for_training"] is False
    assert review["atom_schema_version"] == "camp_legacy_v1_9d"
    assert review["weights_nonnegative"] is True
    assert review["weights_sum_to_one"] is True
    assert review["approved_atoms_only"] is True
    assert review["score_expression"] == module.SCORE_EXPRESSION
    assert review["offline_training_wall_clock_seconds"] == 0.535838
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_training_result_review_rejects_weight_sum_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, weight_sum=0.9)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "weights_sum_to_one" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_check_count=64" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_closed_loop_outcomes_used_for_training=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_atom_schema_version=camp_legacy_v1_9d" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_offline_training_wall_clock_seconds=0.535838" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_camp_head={REVIEW_CAMP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_source_camp_head={SOURCE_CAMP_HEAD}" in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert REVIEW_HEADS_SHA in text
        assert REVIEW_COMMAND_SHA in text
        assert REVIEW_COMMAND_SHELL_SHA in text
        assert REVIEW_STDOUT_SHA in text
        assert REVIEW_STDERR_SHA in text
        assert REVIEW_RUN_EXIT_SHA in text
        assert SOURCE_ROOT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in status
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status


def _write_fixture(tmp_path: Path, module, *, weight_sum: float = 1.0) -> dict:
    artifact = tmp_path / "source_training"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source = _source_payload(module, weight_sum=weight_sum)
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write(artifact / module.SOURCE_MD_NAME, "# Training execution\n")
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "training execution\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
        "static_camp_weights_model.json": json.dumps(source["static_camp_model"], sort_keys=True) + "\n",
        "pilot_training_config.json": "{}\n",
        "pilot_training_timing.json": "{}\n",
        "pilot_training_timing.md": "# Timing\n",
        "training_log.jsonl": "{}\n",
        "training_stdout.txt": "ok\n",
        "training_stderr.txt": "",
    }.items():
        _write(artifact / name, text)
    sha_names = list(module.REQUIRED_SOURCE_FILES)
    (artifact / "SHA256SUMS").write_text(
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names if name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}),
        encoding="utf-8",
    )
    (artifact / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  SHA256SUMS\n", encoding="utf-8")
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
        "source_sha256s": artifact / "SHA256SUMS",
        "source_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, weight_sum: float) -> dict:
    weights = [weight_sum / 9.0] * 9
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "source_artifacts": {
            "split_execution": {"root_sha256": "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"},
            "split_result_review": {"root_sha256": "028e40a2bf2c9c4fc9300660371079656a931e1dce8d3e9fc8c0a51a84f3d1e2"},
            "training_preflight_plan": {"root_sha256": "bc0c5b63a26dd035fcfd74a74df6465df173597278aacc95f77dd5ad8d86f2aa"},
            "training_preflight_plan_static_review": {"root_sha256": "0a73622f95790703a8a1512c46ae8be93dbd99c1932fda912069ee870e5dd188"},
            "training_preflight": {"root_sha256": "12a143284bff4bb8f6b0c423b61db85bd047684b8ecd652072d9964e61a58d9a"},
        },
        "heads": {
            "camp_head": "2f0448ad80abb5b858595c904d4bd6c2de3930a0",
            "camp_origin_main": "2f0448ad80abb5b858595c904d4bd6c2de3930a0",
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "pilot_training_execution": {
            "train_records": 863,
            "calibration_records": 14,
            "holdout_records": 147,
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
            "record_summary": {
                "scene_zero_overlap": True,
                "sample_zero_overlap": True,
                "train_k_values": [8],
                "train_candidate_count_values": [8],
                "train_candidate_tensor_mutated_count": 0,
                "train_closed_loop_outcome_count": 0,
            },
            "atom_summary": {
                "atom_count": 9,
                "atom_schema_version": "camp_legacy_v1_9d",
                "canonical_schema": True,
                "missing_atoms": 0,
            },
            "score_expression": module.SCORE_EXPRESSION,
            "training_executed": True,
            "training_start": "2026-07-08T03:40:49.899324+00:00",
            "training_end": "2026-07-08T03:40:50.435165+00:00",
            "offline_training_wall_clock_seconds": 0.535838,
        },
        "static_camp_model": {
            "atom_count": 9,
            "atom_schema_version": "camp_legacy_v1_9d",
            "approved_atoms_only": True,
            "score_expression": module.SCORE_EXPRESSION,
            "weights": weights,
            "weights_max": max(weights),
            "weights_min": min(weights),
            "weights_nonnegative": True,
            "weights_sum": weight_sum,
            "weights_sum_to_one": weight_sum == 1.0,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "training_executed": True,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
            "closed_loop_outcomes_used_for_training": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
