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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result.py"
)
HEAD = "c17643fb7cdfb4d970dbf024b6b20d8b659f9e11"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT_SHA = "60c051980a20206f75b113bb68a597aacb99782896b9d108b56546c2d97aa0b6"
MEAN_DELTA = -0.01762098077036227
CI95_LOW = -0.021974139797953596
CI95_HIGH = -0.01326782174277094
NON_TOP1_SELECTION_RATE = 0.903933636606904
ORACLE_GAP_CLOSED = 0.9619006786247026
REVIEW_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_passed"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_c17643fb7c_20260709T194159CST"
)
REVIEW_ROOT_SHA = "727ef240fb7803b5e479b5a1e5e86cf2ec0ca79e67d4f0894b44042743723f21"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_only"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_paired_eval_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_paired_eval_result_review_accepts_descriptive_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["paired_evaluation_result_review"]
    metrics = review["primary_metrics"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["primary_eval_rows"] == 3737
    assert review["calibration_rows"] == 2156
    assert review["holdout_rows"] == 1581
    assert review["train_reporting_only_rows"] == 6263
    assert review["train_rows_in_primary_eval"] == 0
    assert review["k_values"] == [8]
    assert review["candidate_count_values"] == [8]
    assert review["dp_head_values"] == [DP_HEAD]
    assert review["candidate_tensor_missing_hash_count"] == 0
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["selected_index_out_of_range_count"] == 0
    assert review["score_expression"] == module.SCORE_EXPRESSION
    assert review["weights_nonnegative"] is True
    assert review["weights_sum_to_one"] is True
    assert review["approved_atoms_only"] is True
    assert metrics["better_tie_worse"] == {"better": 3365, "tie": 359, "worse": 13}
    assert metrics["mean_delta"] == MEAN_DELTA
    assert metrics["ci95"]["high"] == CI95_HIGH
    assert metrics["ci95"]["high"] < 0.0
    assert metrics["non_top1_selection_rate"] == NON_TOP1_SELECTION_RATE
    assert metrics["oracle_gap_closed"] == ORACLE_GAP_CLOSED
    assert review["latency_summary"]["count"] == 3737
    assert review["descriptive_paired_metrics_only"] is True
    assert review["recommended_next_gate"] == module.AUTHORIZED_NEXT_WORK
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_paired_eval_result_review_rejects_nonnegative_ci_high(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    metrics = json.loads(fixture["source_split_metrics_json"].read_text(encoding="utf-8"))
    metrics["primary"]["ci95"]["high"] = 0.1
    fixture["source_split_metrics_json"].write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "ci95_high_negative" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_paired_eval_result_review_is_recorded_in_status_docs() -> None:
    current = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    current_v16 = current.split("## Current V15 Status", maxsplit=1)[0]

    for text in (current_v16, audit):
        assert f"current_v16_status={REVIEW_STATUS}" in text
        assert f"current_v16_artifact={REVIEW_ARTIFACT}" in text
        assert f"next_work_target={NEXT_WORK_TARGET}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_check_count=75" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_source_execution_root_sha256=60c051980a20206f75b113bb68a597aacb99782896b9d108b56546c2d97aa0b6" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_descriptive_paired_metrics_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_camp_over_dp_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_deployment_executed=False" in text

    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


def _write_fixture(tmp_path: Path, module) -> dict:
    artifact = tmp_path / "source_scaleup_paired_eval_execution"
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
    rows = [_row(index) for index in range(3737)]
    source = _source_payload(module)
    split_metrics = _split_metrics_payload()
    latency = _latency_payload()
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write(artifact / module.SOURCE_MD_NAME, "# Scale-up paired eval execution\n")
    _write(artifact / module.SOURCE_ROWS_JSONL_NAME, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    _write_json(artifact / module.SOURCE_SPLIT_METRICS_JSON_NAME, split_metrics)
    _write_json(artifact / module.SOURCE_LATENCY_JSON_NAME, latency)
    _write_json(artifact / module.SOURCE_TIMING_JSON_NAME, {"selector_latency_ms": latency})
    _write(artifact / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(artifact / "COMMAND", "scale-up paired eval execution\n")
    _write(artifact / "stdout.txt", "{}\n")
    _write(artifact / "stderr.txt", "")
    _write(artifact / "run.exit", "0\n")
    _write_manifest(artifact, SOURCE_ROOT_SHA)
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
        "source_rows_jsonl": artifact / module.SOURCE_ROWS_JSONL_NAME,
        "source_split_metrics_json": artifact / module.SOURCE_SPLIT_METRICS_JSON_NAME,
        "source_latency_json": artifact / module.SOURCE_LATENCY_JSON_NAME,
        "source_sha256s": artifact / "SHA256SUMS",
        "source_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module) -> dict:
    metrics = _split_metrics_payload()["primary"]
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "scaleup_paired_evaluation_execution": {
            "paired_rows_by_split": {
                "calibration": 2156,
                "holdout": 1581,
                "primary_eval_total": 3737,
                "train_reporting_only": 6263,
            },
            "primary_eval_splits": ["calibration", "holdout"],
            "reporting_only_splits": ["train"],
            "score_expression": module.SCORE_EXPRESSION,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "approved_atoms_only": True,
            "candidate_tensor_mutated_count": 0,
            "selected_index_out_of_range_count": 0,
            "scaleup_evidence_only": True,
        },
        "split_metrics": {"primary": metrics},
        "selector_latency_ms": _latency_payload(),
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "paired_evaluation_executed": True,
            "training_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
            "scaleup_evidence_only": True,
        },
    }


def _split_metrics_payload() -> dict:
    return {
        "primary": {
            "row_count": 3737,
            "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
            "mean_delta": MEAN_DELTA,
            "ci95": {"low": CI95_LOW, "high": CI95_HIGH},
            "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
            "oracle_gap_closed": ORACLE_GAP_CLOSED,
            "performance_claim": False,
        }
    }


def _latency_payload() -> dict:
    return {
        "count": 3737,
        "mean": 0.026566584903327164,
        "median": 0.026017194613814354,
        "p95": 0.029518036171793938,
        "p99": 0.03343797288835049,
        "max": 0.34069595858454704,
    }


def _row(index: int) -> dict:
    split = "calibration" if index < 2156 else "holdout"
    if index < 3365:
        outcome = "better"
        delta = (MEAN_DELTA * 3737.0 - 13e-6) / 3365.0
        selected_index = 1
    elif index < 3365 + 359:
        outcome = "tie"
        delta = 0.0
        selected_index = 0
    else:
        outcome = "worse"
        delta = 1e-6
        selected_index = 1
    return {
        "split": split,
        "scene_id": f"{split}_scene_{index}",
        "sample_id": f"{split}_sample_{index}",
        "k": 8,
        "candidate_count": 8,
        "fixed_dp_head": DP_HEAD,
        "candidate_tensor_sha256": f"{split}_{index:04x}",
        "candidate_tensor_sha256_present": True,
        "candidate_tensor_unchanged_by_camp": True,
        "selected_index": selected_index,
        "selected_index_in_range": True,
        "dp_top1_index": 0,
        "outcome": outcome,
        "delta": delta,
        "non_top1_selection": selected_index != 0,
        "score_expression": "score_k(w)=a_k^T w",
        "performance_claim": False,
        "safety_claim": False,
        "camp_over_dp_claim": False,
    }


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
