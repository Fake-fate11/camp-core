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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result.py"
)
CURRENT_HEAD = "c" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_paired_evaluation_execution_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["paired_evaluation_executed_by_this_gate"] is False
    assert decision["paired_evaluation_execution_reviewed_by_this_gate"] is True
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["actual_safetycost_evidence_gap_closure_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_execution_summary"]["paired_record_count"] == 4
    assert report["source_execution_summary"]["selection_score_better_records"] == 3
    assert report["evidence_gap_summary"]["next_evidence_need"] == "paired shadow-selected run-level closed-loop outcome summaries"
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_paired_evaluation_execution_result_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_paired_evaluation_execution_result_review_authorization_missing"
    )


def test_paired_evaluation_execution_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_paired_evaluation_execution_result_review_rejects_source_claim_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"safety_benefit_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_execution_decision_safety_benefit_claim_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_paired_evaluation_execution_result_review_rejects_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_execution_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_execution_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_execution_md_sha" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_EXECUTION_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_passed=True",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_authorized=True",
            "paired_evaluation_executed_by_current_gate=True",
            "paired_evaluation_execution_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "source_execution_artifact"
    evaluation = artifact / "evaluation"
    source_json = _write_json(
        evaluation / module.SOURCE_EXECUTION_JSON_NAME,
        _source_execution_report(module, source_decision_updates=source_decision_updates),
    )
    source_md = _write(evaluation / module.SOURCE_EXECUTION_MD_NAME, "# execution\n")
    source_sha = _write_sha256s(evaluation / "SHA256SUMS", [source_json, source_md])
    _write(artifact / "HEADS", f"CAMP_HEAD={'b' * 40}\nCAMP_ORIGIN_MAIN={'b' * 40}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(artifact / "COMMAND", "python execute.py\n")
    _write(artifact / "stdout", "{}\n")
    _write(artifact / "stderr", "")
    _write(artifact / "run.exit", "0\n")
    _write_root_sha256s(artifact, [source_json, source_md, source_sha])

    return {
        "source_execution_artifact_dir": artifact,
        "source_execution_json": source_json,
        "source_execution_md": source_md,
        "source_execution_sha256s": source_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": 4,
        "expected_shadow_diff_records": 3,
        "enabled": True,
    }


def _source_execution_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_EXECUTION_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "paired_evaluation_executed_by_this_gate": True,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "final_decision": decision,
        "paired_record_summary": {
            "record_count": 4,
            "executed_top1_records": 4,
            "shadow_selected_index_differs_from_executed_index_records": 3,
            "formal_seed_records": 0,
            "full36_path_records": 0,
            "non_affine_score_records": 0,
            "non_simplex_weight_records": 0,
        },
        "paired_run_key_index": {
            "paired_run_key_count": 4,
            "unique_paired_run_key_count": 4,
            "duplicate_paired_run_key_count": 0,
        },
        "candidate_tensor_identity_table": {
            "identity_match_records": 4,
            "candidate_tensor_mutation_records": 0,
        },
        "shadow_vs_top1_metric_delta_table": {
            "selection_score_delta": {
                "records": 4,
                "better_records": 3,
                "worse_records": 0,
                "uncomparable_records": 0,
            },
            "raw_affine_score_delta": {"records": 4},
        },
        "safetycost_v1_confidence_interval_table": {
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "unavailable_reason": "locked runtime selection logs do not contain shadow-selected run-level closed-loop outcomes",
            "safetycost_v1_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "paired_execution_no_go_report": {"failed_count": 0},
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(path: Path, paths: list[Path]) -> Path:
    return _write(path, "\n".join(f"{_sha256(item)}  {item.name}" for item in paths) + "\n")


def _write_root_sha256s(root: Path, evaluation_paths: list[Path]) -> Path:
    paths = [
        root / "HEADS",
        root / "COMMAND",
        root / "stdout",
        root / "stderr",
        root / "run.exit",
        *evaluation_paths,
    ]
    lines = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        lines.append(f"{_sha256(path)}  ./{rel}")
    return _write(root / "SHA256SUMS", "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
