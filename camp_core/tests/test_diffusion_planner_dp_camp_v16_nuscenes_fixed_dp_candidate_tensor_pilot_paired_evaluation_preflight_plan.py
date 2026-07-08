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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight.py"
)
HEAD = "b7391b4db11eb056e9f298ad3db7fedd2637b218"
SOURCE_ROOT_SHA = "40f42c459041fd34d5b817d17fbc7d35d6c855fac3cfced192943ba05d153e42"
SOURCE_CAMP_HEAD = "0ffbf63faa26f2b04d3ffe6ed3c976595cf73c09"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_paired_eval_preflight_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_paired_eval_preflight_plan_passes_reviewed_training(tmp_path: Path) -> None:
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
        "calibration": 14,
        "holdout": 147,
        "primary_eval_total": 161,
        "train_reporting_only": 863,
    }
    assert plan["comparison"]["camp_selection"] == "camp_selected_fixed_dp_candidate"
    assert plan["comparison"]["baseline"] == "dp_top1"
    assert plan["comparison"]["candidate_source"] == "fixed_dp_candidate_tensor"
    assert plan["pilot_eval_smoke_only"] is True
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
    assert plan["planned_outputs"] == {
        "command": "COMMAND",
        "heads": "HEADS",
        "plan_json": module.PLAN_JSON_NAME,
        "plan_md": module.PLAN_MD_NAME,
        "sha256s": "SHA256SUMS",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
    }
    assert set(plan["metrics_planned"]) >= {
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


def test_v16_pilot_paired_eval_preflight_plan_rejects_source_claim(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, performance_claimed=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_performance_claimed_false" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, *, performance_claimed: bool = False) -> dict:
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

    source = _source_payload(module, performance_claimed=performance_claimed)
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write(artifact / module.SOURCE_MD_NAME, "# Training result review\n")
    for name, text in {
        "HEADS": f"CAMP_HEAD={SOURCE_CAMP_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_CAMP_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "training result review\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    sha_names = list(module.REQUIRED_SOURCE_FILES)
    (artifact / "SHA256SUMS").write_text(
        "".join(
            f"{_sha256(artifact / name)}  {name}\n"
            for name in sha_names
            if name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ),
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


def _source_payload(module, *, performance_claimed: bool) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "source_artifact": {
            "path": "/root/autodl-tmp/source_training",
            "root_sha256": "92ebe656b28a61b27a5317cf48e41f38a0c1f5d7f333323e2fdaeeb8c8dcd493",
        },
        "heads": {
            "camp_head": SOURCE_CAMP_HEAD,
            "camp_origin_main": SOURCE_CAMP_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "2f0448ad80abb5b858595c904d4bd6c2de3930a0",
        },
        "training_result_review": {
            "train_records": 863,
            "calibration_records": 14,
            "holdout_records": 147,
            "calibration_records_used_for_training": 0,
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
            "offline_training_wall_clock_seconds": 0.535838,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "result_review_only": True,
            "training_executed_by_review": False,
            "paired_evaluation_executed": False,
            "performance_claimed": performance_claimed,
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
