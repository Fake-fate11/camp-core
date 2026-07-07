from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "record_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout.py"
)
HEAD = "587668a8d548a3f7448078f46fee93d3e22339da"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_no_promotion_no_claim_closeout_record_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["check_count"] == len(report["closeout_checks"])
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["closeout_recorded"] is True
    assert decision["no_further_action_recommended"] is True
    assert decision["performance_claimed"] is False
    assert decision["promotion_supported"] is False
    assert decision["full36_used"] is False
    assert decision["formal_seed_11_12_13_used"] is False
    assert decision["dp_modified"] is False
    assert decision["candidate_tensor_modified"] is False
    assert decision["trajectory_modified"] is False
    assert report["closeout_summary"]["closeout_classification"] == "no_promotion_no_claim"
    assert (fixture["output_dir"] / module.RECORD_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.RECORD_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v15_no_promotion_no_claim_closeout_record_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "closeout_record_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_closeout_record_authorization_missing"


def test_v15_no_promotion_no_claim_closeout_record_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v15_eof_contract_mismatch"


def test_v15_no_promotion_no_claim_closeout_record_rejects_performance_claim(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_decision_updates={"performance_claimed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_result_review_performance_not_claimed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["performance_claimed"] is False
    assert report["final_decision"]["promotion_supported"] is False


def test_v15_no_promotion_no_claim_closeout_record_rejects_missing_closeout_authorization(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"closeout_record_authorized": False, "authorized_next_work": "wrong_gate"},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_result_review_closeout_record_authorized" in report["final_decision"]["failed_checks"]
    assert "source_result_review_authorized_current_work" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v15_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    v15_audit = _write(docs / "diffusion_planner_v15_iteration_audit.md", doc_text)
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        doc_text + "\n# historical v14 tail\nnext_work_target=old_v14_tail\n",
    )

    source_artifact = tmp_path / "source_result_review"
    source_artifact.mkdir()
    source_json = _write_json(
        source_artifact / module.SOURCE_REVIEW_JSON_NAME,
        _source_result_review_report(module, decision_updates=source_decision_updates),
    )
    source_md = _write(source_artifact / module.SOURCE_REVIEW_MD_NAME, "# source result review\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run result review\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(source_artifact / name, content)
    source_sha = _write_sha256s(
        source_artifact / "SHA256SUMS",
        [
            source_artifact / "HEADS",
            source_artifact / "COMMAND",
            source_artifact / "stdout.txt",
            source_artifact / "stderr.txt",
            source_artifact / "run.exit",
            source_json,
            source_md,
        ],
    )
    return {
        "source_result_review_artifact_dir": source_artifact,
        "source_result_review_json": source_json,
        "source_result_review_md": source_md,
        "source_result_review_sha256s": source_sha,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_result_review_report(
    module,
    *,
    decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "reviewed_paired_evaluation_execution": True,
        "source_paired_evaluation_executed": True,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "online_selector_latency_executed": False,
        "fallback_latency_executed": False,
        "performance_claimed": False,
        "promotion_supported": False,
        "closeout_record_authorized": True,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "final_decision": decision,
        "result_review": {
            "paired_rows": 288,
            "calibration_rows": 144,
            "holdout_rows": 144,
            "train_rows": 0,
            "promotion_supported": False,
            "performance_claim": False,
            "closeout_classification": "no_promotion_no_claim",
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    return _write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_sha256s(path: Path, files: list[Path]) -> Path:
    return _write(path, "\n".join(f"{_sha256(file)}  {file.name}" for file in files) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
