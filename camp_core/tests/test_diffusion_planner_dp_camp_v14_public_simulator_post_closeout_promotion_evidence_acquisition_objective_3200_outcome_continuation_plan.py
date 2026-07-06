from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation.py"
)
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_outcome_continuation_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    gap = report["objective_gap_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_continuation_plan_ready"] is True
    assert decision["objective_3200_outcome_source_inventory_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert gap["objective_required_records"] == 3200
    assert gap["runtime_record_count"] == 3200
    assert gap["existing_delta_count"] == 32
    assert gap["candidate_closed_loop_outcome_records"] == 0
    assert gap["missing_candidate_closed_loop_outcome_records"] == 3200
    assert gap["objective_3200_gap_present"] is True
    assert gap["closeout_does_not_satisfy_objective"] is True
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_outcome_continuation_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "continuation_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_outcome_continuation_authorization_missing"
    )


def test_objective_3200_outcome_continuation_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_objective_3200_outcome_continuation_plan_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, closeout_claim_authorized=True)

    report = module.build_report(**fixture)

    assert "closeout_no_safety_claim" in report["final_decision"]["failed_checks"]
    assert "closeout_no_camp_over_dp_claim" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_objective_3200_outcome_continuation_plan_rejects_absent_objective_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, candidate_records=3200, missing_records=0)

    report = module.build_report(**fixture)

    assert "candidate_closed_loop_outcome_records" in report["final_decision"]["failed_checks"]
    assert "missing_candidate_closed_loop_outcome_records" in report["final_decision"]["failed_checks"]
    assert "objective_3200_gap_present" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    closeout_claim_authorized: bool = False,
    candidate_records: int = 0,
    missing_records: int = 3200,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_CLOSEOUT_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    closeout_artifact = _write_source_artifact(
        tmp_path / "source_closeout",
        "closeout",
        "closeout.json",
        _closeout_report(module, claim_authorized=closeout_claim_authorized),
        module,
    )
    materialization_artifact = _write_source_artifact(
        tmp_path / "source_materialization",
        "materialization",
        "materialization.json",
        _materialization_report(
            module,
            candidate_records=candidate_records,
            missing_records=missing_records,
        ),
        module,
    )
    result_review_artifact = _write_source_artifact(
        tmp_path / "source_result_review",
        "review",
        "result_review.json",
        _result_review_report(module),
        module,
    )

    return {
        "source_closeout_artifact_dir": closeout_artifact["artifact"],
        "source_closeout_json": closeout_artifact["json"],
        "source_closeout_md": closeout_artifact["md"],
        "source_closeout_sha256s": closeout_artifact["sha256s"],
        "source_materialization_artifact_dir": materialization_artifact["artifact"],
        "source_materialization_json": materialization_artifact["json"],
        "source_materialization_sha256s": materialization_artifact["sha256s"],
        "source_result_review_artifact_dir": result_review_artifact["artifact"],
        "source_result_review_json": result_review_artifact["json"],
        "source_result_review_sha256s": result_review_artifact["sha256s"],
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_artifact(
    artifact: Path,
    subdir_name: str,
    json_name: str,
    payload: dict[str, Any],
    module,
) -> dict[str, Path]:
    subdir = artifact / subdir_name
    report_json = _write_json(subdir / json_name, payload)
    report_md = _write(subdir / f"{Path(json_name).stem}.md", "# report\n")
    report_sha256s = _write(subdir / "SHA256SUMS", "fixture sha256s\n")
    _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={CURRENT_HEAD}",
                f"CAMP_ORIGIN_MAIN={CURRENT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    return {
        "artifact": artifact,
        "json": report_json,
        "md": report_md,
        "sha256s": report_sha256s,
    }


def _closeout_report(module, *, claim_authorized: bool) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_CLOSEOUT_STATUS,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": claim_authorized,
            "camp_over_dp_top1_claim_authorized": claim_authorized,
            "no_further_action_recommended": True,
        },
        "closeout_summary": {
            "delta_mean": 0.9501537269208384,
            "better_records": 1,
            "worse_records": 31,
        },
    }


def _materialization_report(
    module,
    *,
    candidate_records: int,
    missing_records: int,
) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "status": "source_materialization_passed",
        },
        "runtime_source_summary": {
            "record_count": module.OBJECTIVE_REQUIRED_RECORDS,
            "selection_log_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
        },
        "materialization_summary": {
            "top1_summary_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "shadow_summary_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "paired_run_key_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "delta_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "delta_summary": {"mean": 0.9501537269208384},
            "delta_bootstrap_ci95": {
                "ci95_low": 0.7157895850136042,
                "ci95_high": 1.171673912524327,
            },
        },
    }


def _result_review_report(module) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "status": "source_result_review_passed",
            "safety_benefit_claim_supported": False,
            "camp_over_dp_top1_claim_supported": False,
        },
        "source_execution_summary": {
            "delta_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "delta_mean": 0.9501537269208384,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
