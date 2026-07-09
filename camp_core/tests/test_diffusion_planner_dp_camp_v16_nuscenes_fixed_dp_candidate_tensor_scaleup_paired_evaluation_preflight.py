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
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation.py"
)
HEAD = "303a47be3edba6b238f9a2a25ad239369fb7c64b"
PLAN_HEAD = "f01925cfdcceb8d7288899c0970b82f16cc61592"
STATIC_REVIEW_HEAD = "16dc79401936187938abb9996c627151c16bfa1d"
TRAINING_HEAD = "b9a43b733712d38252a43415050ced20ade5edae"
PLAN_ROOT_SHA = "24247d7924a7ac388adf7893cc70510b9fa6496aee9b394f34747ead8b12f4e2"
STATIC_REVIEW_ROOT_SHA = "82182c771919e5dffcff57a546b04931553507a80ec6565bd398d9f6d6747512"
TRAINING_ROOT_SHA = "70875a2691fcd45f6337c48db563b9623e9606adbc35c5fd1df9f7e68029f28e"
SPLIT_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
PREFLIGHT_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_"
    "303a47be3e_20260709T173841CST"
)
PREFLIGHT_JSON_SHA = "443c797192942aefc72143db3c835899d7dad23493e46e0953aa433d3320d927"
PREFLIGHT_MD_SHA = "eb36938d7343200eb5e8754cff172fb80cbfd02e0cb0cec55ea83de020662c3a"
PREFLIGHT_SHA256SUMS_SHA = "620c55ade0d5dba9e6a1c816ebb16178f27729189971308697fda3c9c2e42514"
PREFLIGHT_ROOT_SHA256SUMS_SHA = "7ce9da499bece17ce8d21d02497c2492969311e0ec8ea570b6ad7af34d373ed6"
PREFLIGHT_HEADS_SHA = "fd2a283679575a90ca6ec8406159e81700366a9792d2d39059fff7e921c36afa"
PREFLIGHT_COMMAND_SHA = "e84dacc87866f85d47b82d5a6c831afdc6a38d02c74541094f1411e0850dde00"
PREFLIGHT_STDOUT_SHA = "60156c9218dfd72eea14dd9abb0557ca8bdc3c31a56b7a5b9eede2f48de2225f"
PREFLIGHT_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PREFLIGHT_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_paired_eval_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_paired_eval_preflight_passes_without_eval(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["scaleup_paired_evaluation_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["preflight_only"] is True
    assert decision["evaluation_command_constructed"] is True
    assert decision["evaluation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert preflight["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert preflight["source_static_review_root_sha256"] == STATIC_REVIEW_ROOT_SHA
    assert preflight["source_training_root_sha256"] == TRAINING_ROOT_SHA
    assert preflight["primary_eval_rows"] == 3737
    assert preflight["paired_rows_by_split"] == {
        "calibration": 2156,
        "holdout": 1581,
        "primary_eval_total": 3737,
        "train_reporting_only": 6263,
    }
    assert preflight["primary_eval_splits"] == ["calibration", "holdout"]
    assert preflight["reporting_only_splits"] == ["train"]
    assert preflight["scene_zero_overlap"] is True
    assert preflight["sample_zero_overlap"] is True
    assert preflight["k_values"] == [8]
    assert preflight["candidate_count_values"] == [8]
    assert preflight["missing_candidate_tensor_sha256"] == 0
    assert preflight["candidate_tensor_mutated_count"] == 0
    assert preflight["dp_head"] == module.FIXED_DP_HEAD
    assert preflight["score_expression"] == module.SCORE_EXPRESSION
    assert preflight["approved_atoms_only"] is True
    assert preflight["weights_nonnegative"] is True
    assert preflight["weights_sum_to_one"] is True
    assert set(preflight["metrics_planned"]) >= set(module.REQUIRED_METRICS)
    assert preflight["evaluation_output_root_absent_or_reserved"] is True
    assert "execute_diffusion_planner_dp_camp_v16" in " ".join(preflight["evaluation_command_template"])
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_paired_eval_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["evaluation_output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "evaluation_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_paired_eval_preflight_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert PREFLIGHT_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_train_reporting_only_rows=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_calibration_rows=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_holdout_rows=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_primary_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_missing_candidate_tensor_sha256=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_evaluation_command_constructed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_performance_claimed=False" in text
        assert "selector_latency_mean_median_p95_p99_max" in text
        assert PLAN_ROOT_SHA in text
        assert STATIC_REVIEW_ROOT_SHA in text
        assert TRAINING_ROOT_SHA in text
        assert PREFLIGHT_JSON_SHA in text
        assert PREFLIGHT_MD_SHA in text
        assert PREFLIGHT_SHA256SUMS_SHA in text
        assert PREFLIGHT_ROOT_SHA256SUMS_SHA in text
        assert PREFLIGHT_HEADS_SHA in text
        assert PREFLIGHT_COMMAND_SHA in text
        assert PREFLIGHT_STDOUT_SHA in text
        assert PREFLIGHT_STDERR_SHA in text
        assert PREFLIGHT_RUN_EXIT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in audit
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit


def _write_fixture(tmp_path: Path, module) -> dict:
    plan_artifact = tmp_path / "paired_eval_plan"
    review_artifact = tmp_path / "paired_eval_plan_static_review"
    training_artifact = tmp_path / "training_execution"
    split_artifact = tmp_path / "split_execution"
    for path in (plan_artifact, review_artifact, training_artifact, split_artifact):
        path.mkdir()
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
    records_by_split = _records_by_split(module)
    for name, rows in {
        "train_records.jsonl": records_by_split["train"],
        "calibration_records.jsonl": records_by_split["calibration"],
        "holdout_records.jsonl": records_by_split["holdout"],
    }.items():
        _write(split_artifact / name, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    _write_plan_artifact(plan_artifact, module)
    _write_static_review_artifact(review_artifact, module)
    _write_training_artifact(training_artifact, split_artifact, module)
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_artifact / module.PLAN_MODULE.PLAN_JSON_NAME,
        "source_plan_sha256s": plan_artifact / "SHA256SUMS",
        "source_plan_root_sha256s": plan_artifact / "ROOT_SHA256SUMS",
        "source_static_review_artifact_dir": review_artifact,
        "source_static_review_json": review_artifact / module.SOURCE_REVIEW_JSON_NAME,
        "source_static_review_sha256s": review_artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": review_artifact / "ROOT_SHA256SUMS",
        "source_training_artifact_dir": training_artifact,
        "source_training_json": training_artifact / module.TRAINING_JSON_NAME,
        "source_training_sha256s": training_artifact / "SHA256SUMS",
        "source_training_root_sha256s": training_artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "evaluation_output_root": tmp_path / "paired_eval_execution",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "expected_training_root_sha256": TRAINING_ROOT_SHA,
        "python_executable": "python",
        "enabled": True,
    }


def _write_plan_artifact(artifact: Path, module) -> None:
    _write_json(artifact / module.PLAN_MODULE.PLAN_JSON_NAME, _plan_payload(module))
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Plan\n")
    _write_common_files(artifact, PLAN_HEAD, module.FIXED_DP_HEAD)
    _write_manifest(artifact, PLAN_ROOT_SHA)


def _write_static_review_artifact(artifact: Path, module) -> None:
    _write_json(artifact / module.SOURCE_REVIEW_JSON_NAME, _static_review_payload(module))
    _write(artifact / module.SOURCE_REVIEW_MD_NAME, "# Static review\n")
    _write_common_files(artifact, STATIC_REVIEW_HEAD, module.FIXED_DP_HEAD)
    _write_manifest(artifact, STATIC_REVIEW_ROOT_SHA)


def _write_training_artifact(artifact: Path, split_artifact: Path, module) -> None:
    _write_json(artifact / module.TRAINING_JSON_NAME, _training_payload(module, split_artifact))
    _write(artifact / module.TRAINING_MD_NAME, "# Training execution\n")
    _write_common_files(artifact, TRAINING_HEAD, module.FIXED_DP_HEAD)
    for name in ("static_camp_weights_model.json", "scaleup_training_config.json", "scaleup_training_timing.json"):
        _write(artifact / name, "{}\n")
    for name in ("scaleup_training_timing.md", "scaleup_training.log", "training_log.jsonl"):
        _write(artifact / name, "\n")
    _write_manifest(artifact, TRAINING_ROOT_SHA)


def _plan_payload(module) -> dict:
    return {
        "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
        "authorized_next_work": module.SOURCE_CURRENT_WORK,
        "heads": {"camp_head": PLAN_HEAD, "dp_head": module.FIXED_DP_HEAD},
        "paired_evaluation_preflight_plan": _paired_plan(module),
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.SOURCE_CURRENT_WORK,
            "paired_evaluation_preflight_plan_only": True,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _static_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "heads": {"camp_head": STATIC_REVIEW_HEAD, "source_camp_head": PLAN_HEAD, "dp_head": module.FIXED_DP_HEAD},
        "plan_static_review": {
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            **_paired_plan(module),
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_review_only": True,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _training_payload(module, split_artifact: Path) -> dict:
    return {
        "schema_version": module.TRAINING_SCHEMA_VERSION,
        "status": module.TRAINING_READY_STATUS,
        "heads": {"camp_head": TRAINING_HEAD, "dp_head": module.FIXED_DP_HEAD},
        "source_artifacts": {
            "split_execution": {
                "path": str(split_artifact),
                "root_sha256": SPLIT_ROOT_SHA,
                "sha256s_verified": True,
                "failed_sha256s": [],
            }
        },
        "scaleup_training_execution": {
            "train_records": 6263,
            "calibration_records": 2156,
            "holdout_records": 1581,
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
            "record_summary": {
                "scene_zero_overlap": True,
                "sample_zero_overlap": True,
                "train_k_values": [8],
                "train_candidate_count_values": [8],
                "train_dp_head_values": [module.FIXED_DP_HEAD],
                "train_candidate_tensor_mutated_count": 0,
                "train_closed_loop_outcome_count": 0,
            },
            "score_expression": module.SCORE_EXPRESSION,
        },
        "static_camp_model": {
            "approved_atoms_only": True,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": {
            "passed": True,
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


def _paired_plan(module) -> dict:
    return {
        "primary_eval_splits": ["calibration", "holdout"],
        "reporting_only_splits": ["train"],
        "paired_rows_by_split": {
            "calibration": 2156,
            "holdout": 1581,
            "primary_eval_total": 3737,
            "train_reporting_only": 6263,
        },
        "comparison": {
            "camp_selection": "camp_selected_fixed_dp_candidate",
            "baseline": "dp_top1",
            "candidate_source": "fixed_dp_candidate_tensor",
        },
        "metrics_planned": list(module.REQUIRED_METRICS),
        "scaleup_evidence_only": True,
        "claims": {
            "performance_claim_allowed": False,
            "safety_claim_allowed": False,
            "camp_over_dp_claim_allowed": False,
        },
        "pass_fail_conditions": {
            "no_train_leakage_into_primary_eval": True,
            "k": 8,
            "candidate_count": 8,
            "dp_head_fixed": module.FIXED_DP_HEAD,
            "candidate_tensor_hashes_present": True,
            "no_candidate_mutation": True,
            "affine_simplex_checks_pass": True,
        },
    }


def _records_by_split(module) -> dict[str, list[dict]]:
    return {
        "train": [_record(module, "train", i) for i in range(6263)],
        "calibration": [_record(module, "calibration", i) for i in range(2156)],
        "holdout": [_record(module, "holdout", i) for i in range(1581)],
    }


def _record(module, split: str, index: int) -> dict:
    return {
        "split": split,
        "scene_id": f"{split}_scene_{index}",
        "sample_id": f"{split}_sample_{index}",
        "K": 8,
        "candidate_count": 8,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "candidate_tensor_sha256": f"{split}_{index:04x}",
        "candidate_tensor_unchanged_by_camp": True,
    }


def _write_common_files(artifact: Path, camp_head: str, dp_head: str) -> None:
    _write(artifact / "HEADS", f"CAMP_HEAD={camp_head}\nCAMP_ORIGIN_MAIN={camp_head}\nDP_HEAD={dp_head}\n")
    _write(artifact / "COMMAND", "command\n")
    _write(artifact / "stdout.txt", "{}\n")
    _write(artifact / "stderr.txt", "")
    _write(artifact / "run.exit", "0\n")


def _write_manifest(artifact: Path, root_sha: str) -> None:
    rows = []
    for path in sorted(artifact.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.name}\n")
    _write(artifact / "SHA256SUMS", "".join(rows))
    _write(artifact / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
