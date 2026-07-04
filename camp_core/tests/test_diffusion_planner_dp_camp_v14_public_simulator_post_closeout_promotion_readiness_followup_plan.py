from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_followup.py"
)
ARTIFACT_HEAD = "b" * 40
CURRENT_HEAD = "c" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_followup_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_readiness_followup_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["followup_plan_static_review_authorized"] is True
    assert decision["direct_promotion_recommendation"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["name"] for item in report["followup_plan"]] == list(module.EXPECTED_FOLLOWUP_ITEMS)
    assert {item["authorizes_promotion"] for item in report["followup_plan"]} == {False}
    assert (
        fixture["output_dir"] / "post_closeout_promotion_readiness_followup_plan.json"
    ).is_file()
    assert (
        fixture["output_dir"] / "post_closeout_promotion_readiness_followup_plan.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_readiness_followup_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "followup_plan_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_followup_plan_authorization_missing"


def test_post_closeout_promotion_readiness_followup_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_followup_plan" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_followup_plan" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_readiness_followup_plan_rejects_source_promotion_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_result_review_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_post_closeout_promotion_readiness_followup_plan_cli_writes_outputs(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--result_review_artifact_dir",
            str(fixture["result_review_artifact_dir"]),
            "--result_review_json",
            str(fixture["result_review_json"]),
            "--result_review_md",
            str(fixture["result_review_md"]),
            "--result_review_sha256s",
            str(fixture["result_review_sha256s"]),
            "--v14_audit_md",
            str(fixture["v14_audit_md"]),
            "--current_status_md",
            str(fixture["current_status_md"]),
            "--output_dir",
            str(output_dir),
            "--current_camp_head",
            CURRENT_HEAD,
            "--current_camp_origin_main",
            CURRENT_HEAD,
            "--current_dp_head",
            module.FIXED_DP_HEAD,
            "--enable_v14_post_closeout_promotion_readiness_followup_plan",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "post_closeout_promotion_readiness_followup_plan.json").is_file()
    assert (output_dir / "post_closeout_promotion_readiness_followup_plan.md").is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    eof_status: str | None = None,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "result_review_artifact"
    result_dir = artifact / "result_review"
    docs = tmp_path / "docs"
    current_status_value = eof_status or module.SOURCE_RESULT_REVIEW_STATUS
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={current_status_value}",
            f"next_work_target={current_next}",
            f"v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_artifact={artifact.resolve()}",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed=True",
            "direct_promotion_recommendation=False",
            "promotion_decision_plan_authorized_next=False",
            "followup_requires_explicit_user_decision=True",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "dp_modification_authorized_by_current_boundary=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "shadow_vs_top1_delta_review=present",
            "no_promotion_closeout=present",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    result_json = _write_json(
        result_dir / module.SOURCE_RESULT_JSON_NAME,
        _source_result_review_payload(module, decision_updates=source_decision_updates),
    )
    result_md = _write(result_dir / module.SOURCE_RESULT_MD_NAME, "# Result Review\n")
    result_sha256s = _write_sha256sums(result_dir / "SHA256SUMS", [result_json, result_md])
    command = _write(artifact / "COMMAND", "result review command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"dp_head={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, stdout, stderr, run_exit, result_json, result_md, result_sha256s],
        relative_to=artifact,
    )
    return {
        "result_review_artifact_dir": artifact,
        "result_review_json": result_json,
        "result_review_md": result_md,
        "result_review_sha256s": result_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_result_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_RESULT_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.SOURCE_RESULT_REVIEW_STATUS.replace("_passed", "_only"),
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "followup_requires_explicit_user_decision": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_RESULT_REVIEW_SCHEMA,
        "analysis": {
            "result_review_only": True,
            "read_only": True,
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_static_review_summary": {
            "review_check_count": module.EXPECTED_SOURCE_COUNTS["source_static_review_check_count"],
        },
        "source_execution_summary": {
            "check_count": module.EXPECTED_SOURCE_COUNTS["source_execution_check_count"],
            "metrics_manifest_count": module.EXPECTED_SOURCE_COUNTS["source_metrics_manifest_count"],
            "no_go_summary_count": module.EXPECTED_SOURCE_COUNTS["source_no_go_summary_count"],
            "evidence_matrix_count": module.EXPECTED_SOURCE_COUNTS["source_evidence_matrix_count"],
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "result_review_checks": [
            {"name": f"fixture_check_{index}", "passed": True}
            for index in range(module.EXPECTED_SOURCE_COUNTS["result_review_check_count"])
        ],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256sums(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    rows = []
    for item in files:
        key = item.relative_to(relative_to).as_posix() if relative_to else item.name
        rows.append(f"{_sha256(item)}  {key}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
