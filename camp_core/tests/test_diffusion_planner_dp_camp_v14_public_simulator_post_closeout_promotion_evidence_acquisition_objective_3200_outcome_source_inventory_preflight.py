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
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory.py"
)
CURRENT_HEAD = "6" * 40
SOURCE_HEAD = "7" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_source_inventory_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_source_inventory_preflight_passes_with_existing_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    inventory = report["inventory_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_source_inventory_preflight_passed"] is True
    assert decision["objective_3200_outcome_acquisition_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert inventory["runtime_record_count"] == 3200
    assert inventory["existing_delta_count"] == 32
    assert inventory["candidate_closed_loop_outcome_records"] == 0
    assert inventory["missing_candidate_closed_loop_outcome_records"] == 3200
    assert inventory["existing_artifacts_satisfy_objective"] is False
    assert inventory["requires_acquisition_plan"] is True
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_source_inventory_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_inventory_preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_source_inventory_preflight_authorization_missing"
    )


def test_objective_3200_source_inventory_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_objective_3200_source_inventory_preflight_rejects_static_review_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_review_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_static_review_camp_over_dp_top1_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_objective_3200_source_inventory_preflight_rejects_claim_supported_review(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, result_claim_supported=True)

    report = module.build_report(**fixture)

    assert "source_result_review_safety_claim_supported" in report["final_decision"]["failed_checks"]
    assert "source_result_review_camp_over_dp_supported" in report["final_decision"]["failed_checks"]


def test_objective_3200_source_inventory_preflight_rejects_unexpected_source_availability(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, candidate_records=3200, missing_records=0)

    report = module.build_report(**fixture)

    assert "inventory_candidate_closed_loop_outcome_records" in report["final_decision"]["failed_checks"]
    assert "inventory_missing_candidate_closed_loop_outcome_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    static_review_updates: dict[str, Any] | None = None,
    result_claim_supported: bool = False,
    candidate_records: int = 0,
    missing_records: int = 3200,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_source_inventory_preflight_static_review_passed=True",
            "objective_3200_outcome_source_inventory_preflight_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    static_artifact = tmp_path / "source_static_review"
    _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    static_json = _write_json(
        static_artifact / "review" / "static_review.json",
        _static_review_report(module, static_review_updates=static_review_updates),
    )
    static_sha = _write(static_artifact / "review" / "SHA256SUMS", "fixture\n")
    continuation_json = _write_json(
        tmp_path / "continuation_plan.json",
        _continuation_plan_report(module, candidate_records=candidate_records, missing_records=missing_records),
    )
    materialization_json = _write_json(
        tmp_path / "materialization.json",
        _materialization_report(module, candidate_records=candidate_records, missing_records=missing_records),
    )
    result_review_json = _write_json(
        tmp_path / "result_review.json",
        _result_review_report(module, claim_supported=result_claim_supported),
    )
    closeout_json = _write_json(tmp_path / "closeout.json", _closeout_report(module))

    return {
        "source_static_review_artifact_dir": static_artifact,
        "source_static_review_json": static_json,
        "source_static_review_sha256s": static_sha,
        "source_continuation_plan_json": continuation_json,
        "source_materialization_json": materialization_json,
        "source_result_review_json": result_review_json,
        "source_closeout_json": closeout_json,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _static_review_report(
    module,
    *,
    static_review_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "replay_execution_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
    }
    if static_review_updates:
        decision.update(static_review_updates)
    return {"schema_version": module.SOURCE_REVIEW_SCHEMA, "final_decision": decision}


def _continuation_plan_report(
    module,
    *,
    candidate_records: int,
    missing_records: int,
) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "objective_3200_gap_present": candidate_records < module.PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        },
        "objective_gap_summary": {
            "objective_required_records": module.PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_record_count": module.PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_selection_log_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_top1_summary_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_shadow_summary_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_paired_run_key_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_delta_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
        },
    }


def _materialization_report(
    module,
    *,
    candidate_records: int,
    missing_records: int,
) -> dict[str, Any]:
    return {
        "runtime_source_summary": {
            "record_count": module.PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "selection_log_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
        },
        "materialization_summary": {
            "top1_summary_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "shadow_summary_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "paired_run_key_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "delta_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET,
        },
    }


def _result_review_report(module, *, claim_supported: bool) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "safety_benefit_claim_supported": claim_supported,
            "camp_over_dp_top1_claim_supported": claim_supported,
        },
        "source_execution_summary": {"delta_count": module.PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET},
    }


def _closeout_report(module) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "status": module.PLAN_MODULE.SOURCE_CLOSEOUT_STATUS,
            "authorized_next_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        }
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
