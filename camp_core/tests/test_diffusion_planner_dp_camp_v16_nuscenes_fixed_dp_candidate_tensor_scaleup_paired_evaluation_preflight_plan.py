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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight.py"
)
HEAD = "f01925cfdcceb8d7288899c0970b82f16cc61592"
SOURCE_ROOT_SHA = "1063073e0b1f7088b142241f71a238711635865409ed5166e389b46299521429"
SOURCE_CAMP_HEAD = "7aec1e3b9ec3cd209a142b48986ed74b0386b31a"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_"
    "f01925cfdc_20260709T165918CST"
)
PLAN_JSON_SHA = "9cb923edd93be16170c02a190cffdfa76178e84be4555c19fcb0d9f8b37d393f"
PLAN_MD_SHA = "6ee00584c749a162efccb7459f2c68e292a8b9977cbecbdddefb4c2ef6cd7609"
PLAN_SHA256SUMS_SHA = "24247d7924a7ac388adf7893cc70510b9fa6496aee9b394f34747ead8b12f4e2"
PLAN_ROOT_SHA256SUMS_SHA = "bdbf5f9165a6f1acddd0ea5a9684d8059e9dc8a84641baac5d7f85c1306f3282"
PLAN_HEADS_SHA = "f2cbb5de7ff3aab3acf52cf7650a82a385cb11aef6ec6bec42673a0507b88ba4"
PLAN_COMMAND_SHA = "9d38485313240c4e6e8f07a236af389a54b1787c914e48ae31a48ea3254834c9"
PLAN_STDOUT_SHA = "8400b31e98c94e5681311234f48b3a783b98f9a3b6c8ce3fa2679c88e40a72e8"
PLAN_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PLAN_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_paired_eval_preflight_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_paired_eval_preflight_plan_passes_reviewed_training(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["paired_evaluation_preflight_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["paired_evaluation_preflight_plan_only"] is True
    assert decision["evaluation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert plan["primary_eval_splits"] == ["calibration", "holdout"]
    assert plan["reporting_only_splits"] == ["train"]
    assert plan["paired_rows_by_split"] == {
        "calibration": 2156,
        "holdout": 1581,
        "primary_eval_total": 3737,
        "train_reporting_only": 6263,
    }
    assert plan["comparison"]["camp_selection"] == "camp_selected_fixed_dp_candidate"
    assert plan["comparison"]["baseline"] == "dp_top1"
    assert plan["comparison"]["candidate_source"] == "fixed_dp_candidate_tensor"
    assert plan["scaleup_evidence_only"] is True
    assert plan["claims"]["performance_claim_allowed"] is False
    assert plan["claims"]["safety_claim_allowed"] is False
    assert plan["claims"]["camp_over_dp_claim_allowed"] is False
    assert plan["pass_fail_conditions"]["no_train_leakage_into_primary_eval"] is True
    assert plan["pass_fail_conditions"]["k"] == 8
    assert plan["pass_fail_conditions"]["candidate_count"] == 8
    assert plan["pass_fail_conditions"]["dp_head_fixed"] == module.FIXED_DP_HEAD
    assert plan["pass_fail_conditions"]["candidate_tensor_hashes_present"] is True
    assert plan["pass_fail_conditions"]["no_candidate_mutation"] is True
    assert plan["pass_fail_conditions"]["affine_simplex_checks_pass"] is True
    assert set(plan["metrics_planned"]) == {
        "paired_rows_by_split",
        "better_tie_worse",
        "mean_delta",
        "ci95",
        "dp_top1_metric",
        "camp_selected_metric",
        "non_top1_selection_rate",
        "oracle_gap_closed",
        "selector_latency_mean_median_p95_p99_max",
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_paired_eval_preflight_plan_rejects_train_leakage(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, train_leakage=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "calibration_not_used_for_training" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_paired_eval_preflight_plan_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert PLAN_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_train_reporting_only_rows=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_calibration_rows=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_holdout_rows=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_primary_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_primary_eval_splits=[calibration,holdout]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_reporting_only_splits=[train]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_comparison=camp_selected_fixed_dp_candidate_vs_dp_top1" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_scaleup_evidence_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_camp_over_dp_claimed=False" in text
        assert "selector_latency_mean_median_p95_p99_max" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_camp_head={HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_source_camp_head={SOURCE_CAMP_HEAD}" in text
        assert SOURCE_ROOT_SHA in text
        assert PLAN_JSON_SHA in text
        assert PLAN_MD_SHA in text
        assert PLAN_SHA256SUMS_SHA in text
        assert PLAN_ROOT_SHA256SUMS_SHA in text
        assert PLAN_HEADS_SHA in text
        assert PLAN_COMMAND_SHA in text
        assert PLAN_STDOUT_SHA in text
        assert PLAN_STDERR_SHA in text
        assert PLAN_RUN_EXIT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in status
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status


def _write_fixture(tmp_path: Path, module, *, train_leakage: bool = False) -> dict:
    artifact = tmp_path / "source_review"
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
    source = _source_payload(module, train_leakage=train_leakage)
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write(artifact / module.SOURCE_MD_NAME, "# Scale-up training result review\n")
    for name, text in {
        "HEADS": f"CAMP_HEAD={SOURCE_CAMP_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_CAMP_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "scale-up training result review\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    _rewrite_manifest(artifact, module.REQUIRED_SOURCE_FILES)
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


def _source_payload(module, *, train_leakage: bool) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "source_artifact": {
            "path": "/root/autodl-tmp/source_training",
            "root_sha256": "70875a2691fcd45f6337c48db563b9623e9606adbc35c5fd1df9f7e68029f28e",
        },
        "heads": {
            "camp_head": SOURCE_CAMP_HEAD,
            "camp_origin_main": SOURCE_CAMP_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "b9a43b733712d38252a43415050ced20ade5edae",
        },
        "training_result_review": {
            "train_records": 6263,
            "calibration_records": 2156,
            "holdout_records": 1581,
            "calibration_records_used_for_training": 1 if train_leakage else 0,
            "holdout_records_used_for_training": 0,
            "scene_zero_overlap": True,
            "sample_zero_overlap": True,
            "train_k_values": [8],
            "train_candidate_count_values": [8],
            "source_dp_head": module.FIXED_DP_HEAD,
            "candidate_tensor_mutated_count": 0,
            "closed_loop_outcomes_used_for_training": False,
            "train_closed_loop_outcome_count": 0,
            "atom_count": 9,
            "atom_schema_version": "camp_legacy_v1_9d",
            "atom_schema_canonical": True,
            "approved_atoms_only": True,
            "weights": [1.0 / 9.0] * 9,
            "weights_sum": 1.0,
            "weights_min": 1.0 / 9.0,
            "weights_max": 1.0 / 9.0,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "score_expression": module.SCORE_EXPRESSION,
            "offline_training_wall_clock_seconds": 1.335207,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "result_review_only": True,
            "training_executed_by_review": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rewrite_manifest(path: Path, files: tuple[str, ...]) -> None:
    rows = []
    for name in files:
        if name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            continue
        rows.append(f"{_sha256(path / name)}  {name}\n")
    (path / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")
    (path / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  SHA256SUMS\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
