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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition.py"
)
CURRENT_HEAD = "8" * 40
SOURCE_HEAD = "9" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_outcome_acquisition_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    gap = report["objective_gap_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_plan_ready"] is True
    assert decision["objective_3200_outcome_acquisition_plan_static_review_authorized"] is True
    assert decision["direct_replay_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert gap["objective_required_records"] == 3200
    assert gap["candidate_closed_loop_outcome_records"] == 0
    assert gap["missing_candidate_closed_loop_outcome_records"] == 3200
    assert gap["existing_artifacts_satisfy_objective"] is False
    assert [item["step"] for item in report["acquisition_plan"]] == [
        "build_fixed_dp_row_manifest",
        "bind_shadow_selected_candidate_per_record",
        "execute_or_locate_shadow_selected_fixed_dp_candidate_outcomes",
        "enforce_strict_pairing_with_dp_top1",
        "fail_closed_on_forbidden_sources",
        "authorize_next_static_review_only",
    ]
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_outcome_acquisition_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "acquisition_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_outcome_acquisition_plan_authorization_missing"
    )


def test_objective_3200_outcome_acquisition_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_objective_3200_outcome_acquisition_plan_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_preflight_camp_over_dp_top1_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_objective_3200_outcome_acquisition_plan_rejects_already_satisfied_objective(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        candidate_records=3200,
        missing_records=0,
        existing_artifacts_satisfy=True,
        requires_acquisition_plan=False,
    )

    report = module.build_report(**fixture)

    assert "source_preflight_existing_artifacts_satisfy_objective" in report[
        "final_decision"
    ]["failed_checks"]
    assert "source_preflight_requires_acquisition_plan" in report["final_decision"]["failed_checks"]
    assert "candidate_closed_loop_outcome_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    candidate_records: int = 0,
    missing_records: int = 3200,
    existing_artifacts_satisfy: bool = False,
    requires_acquisition_plan: bool = True,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_source_inventory_preflight_passed=True",
            "objective_3200_outcome_acquisition_plan_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "source_inventory_preflight"
    _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    source_json = _write_json(
        artifact / "preflight" / "source_inventory_preflight.json",
        _source_preflight_report(
            module,
            source_decision_updates=source_decision_updates,
            candidate_records=candidate_records,
            missing_records=missing_records,
            existing_artifacts_satisfy=existing_artifacts_satisfy,
            requires_acquisition_plan=requires_acquisition_plan,
        ),
    )
    source_md = _write(artifact / "preflight" / "source_inventory_preflight.md", "# source\n")
    source_sha = _write(artifact / "preflight" / "SHA256SUMS", "fixture\n")

    return {
        "source_inventory_preflight_artifact_dir": artifact,
        "source_inventory_preflight_json": source_json,
        "source_inventory_preflight_md": source_md,
        "source_inventory_preflight_sha256s": source_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
    candidate_records: int,
    missing_records: int,
    existing_artifacts_satisfy: bool,
    requires_acquisition_plan: bool,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "existing_artifacts_satisfy_objective": existing_artifacts_satisfy,
        "per_record_outcome_source_available": candidate_records >= module.OBJECTIVE_REQUIRED_RECORDS,
        "requires_acquisition_plan": requires_acquisition_plan,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
    }
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "analysis": {
            "read_only": True,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "inventory_summary": {
            "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_selection_log_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_top1_summary_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_shadow_summary_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_paired_run_key_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "existing_delta_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
            "per_record_outcome_source_available": candidate_records >= module.OBJECTIVE_REQUIRED_RECORDS,
            "existing_artifacts_satisfy_objective": existing_artifacts_satisfy,
            "requires_acquisition_plan": requires_acquisition_plan,
        },
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
