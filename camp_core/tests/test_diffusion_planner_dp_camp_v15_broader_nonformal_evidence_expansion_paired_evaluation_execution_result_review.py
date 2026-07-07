from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result.py"
)
HEAD = "08feecf836b4083efa296726fcc45754fe23da91"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_execution_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_paired_evaluation_execution_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_paired_evaluation_execution"] is True
    assert decision["source_paired_evaluation_executed"] is True
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_supported"] is False
    assert decision["closeout_record_authorized"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_paired_evaluation_execution_result_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_review" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_result_review_rejects_performance_claim(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, decision_updates={"performance_claimed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_performance_not_claimed" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_result_review_rejects_train_rows(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, split_updates={"train": {"row_count": 1}})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_train_rows_excluded" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    decision_updates: dict | None = None,
    split_updates: dict | None = None,
) -> dict:
    execution = module.EXECUTION_MODULE
    artifact = tmp_path / "source_execution"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")
    payload = _source_execution_payload(module, decision_updates=decision_updates, split_updates=split_updates)
    files = {
        execution.EXECUTION_JSON_NAME: payload,
        execution.SPLIT_METRICS_JSON_NAME: payload["split_metrics"],
        execution.SCENARIO_BUCKET_METRICS_JSON_NAME: payload["scenario_bucket_metrics"],
        execution.ONLINE_LATENCY_JSON_NAME: payload["online_selector_latency"],
        execution.FALLBACK_LATENCY_JSON_NAME: payload["fallback_latency"],
        execution.TIMING_JSON_NAME: payload["timing"],
    }
    for name, value in files.items():
        _write_json(artifact / name, value)
    (artifact / execution.EXECUTION_MD_NAME).write_text("# Paired Execution\n", encoding="utf-8")
    (artifact / execution.PAIRED_ROWS_JSONL_NAME).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in _paired_rows()),
        encoding="utf-8",
    )
    (artifact / execution.TIMING_MD_NAME).write_text("# Timing\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run paired execution\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    sha_path = artifact / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                execution.EXECUTION_JSON_NAME,
                execution.EXECUTION_MD_NAME,
                execution.PAIRED_ROWS_JSONL_NAME,
                execution.SPLIT_METRICS_JSON_NAME,
                execution.SCENARIO_BUCKET_METRICS_JSON_NAME,
                execution.ONLINE_LATENCY_JSON_NAME,
                execution.FALLBACK_LATENCY_JSON_NAME,
                execution.TIMING_JSON_NAME,
                execution.TIMING_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_execution_artifact_dir": artifact,
        "source_execution_json": artifact / execution.EXECUTION_JSON_NAME,
        "source_execution_md": artifact / execution.EXECUTION_MD_NAME,
        "source_rows_jsonl": artifact / execution.PAIRED_ROWS_JSONL_NAME,
        "source_split_metrics": artifact / execution.SPLIT_METRICS_JSON_NAME,
        "source_scenario_bucket_metrics": artifact / execution.SCENARIO_BUCKET_METRICS_JSON_NAME,
        "source_online_latency_json": artifact / execution.ONLINE_LATENCY_JSON_NAME,
        "source_fallback_latency_json": artifact / execution.FALLBACK_LATENCY_JSON_NAME,
        "source_timing_json": artifact / execution.TIMING_JSON_NAME,
        "source_timing_md": artifact / execution.TIMING_MD_NAME,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_execution_payload(
    module,
    *,
    decision_updates: dict | None = None,
    split_updates: dict | None = None,
) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "paired_evaluation_execution_executed": True,
        "source_training_executed": True,
        "training_executed": False,
        "paired_evaluation_executed": True,
        "online_selector_latency_executed": True,
        "fallback_latency_executed": True,
        "performance_claimed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if decision_updates:
        decision.update(decision_updates)
    split_metrics = {
        "calibration": {"row_count": 1, "better": 0, "tie": 1, "worse": 0, "performance_claim": False},
        "holdout": {"row_count": 1, "better": 0, "tie": 1, "worse": 0, "performance_claim": False},
        "train": {"row_count": 0, "better": 0, "tie": 0, "worse": 0, "performance_claim": False},
    }
    if split_updates:
        for key, value in split_updates.items():
            split_metrics[key].update(value)
    online_latency = {"count": 2, "mean": 0.1, "median": 0.1, "p95": 0.1, "p99": 0.1, "max": 0.1}
    fallback_latency = {"count": 2, "mean": 0.01, "median": 0.01, "p95": 0.01, "p99": 0.01, "max": 0.01}
    return {
        "schema_version": module.EXECUTION_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
        "paired_evaluation": {
            "row_count": 2,
            "evaluation_splits": ["calibration", "holdout"],
            "performance_claim": False,
        },
        "split_metrics": split_metrics,
        "scenario_bucket_metrics": {"normal": {"row_count": 2, "performance_claim": False}},
        "online_selector_latency": online_latency,
        "fallback_latency": fallback_latency,
        "timing": {
            "online_selector_latency": online_latency,
            "fallback_latency": fallback_latency,
            "instrumentation_changes_selector_behavior": False,
        },
    }


def _paired_rows() -> list[dict]:
    return [
        {
            "record_id": "row-calibration",
            "split": "calibration",
            "outcome": "tie",
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
            "dp_modified": False,
            "performance_claim": False,
        },
        {
            "record_id": "row-holdout",
            "split": "holdout",
            "outcome": "tie",
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
            "dp_modified": False,
            "performance_claim": False,
        },
    ]


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
