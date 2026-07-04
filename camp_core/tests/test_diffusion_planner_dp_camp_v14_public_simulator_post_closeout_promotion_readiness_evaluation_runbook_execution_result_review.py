from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result.py"
)
STATIC_HEAD = "f" * 40
EXECUTION_HEAD = "e" * 40
CURRENT_HEAD = "a" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_execution_result_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["direct_promotion_recommendation"] is False
    assert decision["promotion_decision_plan_authorized_next"] is False
    assert decision["followup_requires_explicit_user_decision"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_static_review_summary"]["review_check_count"] == 136
    assert report["source_execution_summary"]["check_count"] == 216
    assert report["source_execution_summary"]["metrics_manifest_count"] == 6
    assert report["source_execution_summary"]["no_go_summary_count"] == 8
    assert report["source_execution_summary"]["evidence_matrix_count"] == 6
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_execution_result_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_runbook_execution_result_review_authorization_missing"
    )


def test_promotion_readiness_evaluation_runbook_execution_result_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_result_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_result_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_execution_result_review_rejects_static_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_review_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_readiness_evaluation_runbook_execution_result_review_rejects_no_go_trigger(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, no_go_triggered=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_execution_no_go_triggered" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["direct_promotion_recommendation"] is False


def test_promotion_readiness_evaluation_runbook_execution_result_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_execution_static_review_artifact_dir",
            str(fixture["runbook_execution_static_review_artifact_dir"]),
            "--runbook_execution_static_review_json",
            str(fixture["runbook_execution_static_review_json"]),
            "--runbook_execution_static_review_md",
            str(fixture["runbook_execution_static_review_md"]),
            "--runbook_execution_static_review_sha256s",
            str(fixture["runbook_execution_static_review_sha256s"]),
            "--source_runbook_execution_artifact_dir",
            str(fixture["source_runbook_execution_artifact_dir"]),
            "--source_runbook_execution_json",
            str(fixture["source_runbook_execution_json"]),
            "--source_runbook_execution_md",
            str(fixture["source_runbook_execution_md"]),
            "--source_runbook_execution_sha256s",
            str(fixture["source_runbook_execution_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    eof_status: str | None = None,
    next_work: str | None = None,
    static_review_decision_updates: dict[str, Any] | None = None,
    execution_decision_updates: dict[str, Any] | None = None,
    no_go_triggered: bool = False,
) -> dict[str, Any]:
    static_artifact = tmp_path / "runbook_execution_static_review_artifact"
    execution_artifact = tmp_path / "runbook_execution_artifact"
    docs = tmp_path / "docs"
    current_status_value = eof_status or module.SOURCE_STATIC_REVIEW_STATUS
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={current_status_value}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_authorized=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "dp_modification_authorized_by_current_boundary=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    execution_json = _write_json(
        execution_artifact / "execution" / module.EXECUTION_JSON_NAME,
        _source_execution_payload(
            module,
            decision_updates=execution_decision_updates,
            no_go_triggered=no_go_triggered,
        ),
    )
    execution_md = _write(execution_artifact / "execution" / module.EXECUTION_MD_NAME, "# Runbook Execution\n")
    execution_sha256s = _write_sha256sums(
        execution_artifact / "execution" / "SHA256SUMS",
        [execution_json, execution_md],
    )
    execution_command = _write(execution_artifact / "COMMAND", "runbook execution command\n")
    execution_heads = _write(
        execution_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={EXECUTION_HEAD}",
                f"camp_origin_main={EXECUTION_HEAD}",
                f"dp_head={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    execution_stdout = _write(execution_artifact / "stdout.txt", "ok\n")
    execution_stderr = _write(execution_artifact / "stderr.txt", "")
    execution_exit = _write(execution_artifact / "run.exit", "0\n")
    _write_sha256sums(
        execution_artifact / "SHA256SUMS",
        [
            execution_command,
            execution_heads,
            execution_stdout,
            execution_stderr,
            execution_exit,
            execution_json,
            execution_md,
            execution_sha256s,
        ],
        relative_to=execution_artifact,
    )

    static_json = _write_json(
        static_artifact / "review" / module.STATIC_REVIEW_JSON_NAME,
        _source_static_review_payload(
            module,
            execution_artifact,
            decision_updates=static_review_decision_updates,
        ),
    )
    static_md = _write(static_artifact / "review" / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_sha256s = _write_sha256sums(
        static_artifact / "review" / "SHA256SUMS",
        [static_json, static_md],
    )
    static_command = _write(static_artifact / "COMMAND", "static review command\n")
    static_heads = _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={STATIC_HEAD}",
                f"camp_origin_main={STATIC_HEAD}",
                f"dp_head={module.FIXED_DP_HEAD}",
                f"source_runbook_execution_artifact={execution_artifact.resolve()}",
                f"source_runbook_execution_json={execution_json.resolve()}",
                f"source_runbook_execution_md={execution_md.resolve()}",
                f"source_runbook_execution_sha256s={execution_sha256s.resolve()}",
                "",
            ]
        ),
    )
    static_stdout = _write(static_artifact / "stdout.txt", "ok\n")
    static_stderr = _write(static_artifact / "stderr.txt", "")
    static_exit = _write(static_artifact / "run.exit", "0\n")
    _write_sha256sums(
        static_artifact / "SHA256SUMS",
        [static_command, static_heads, static_stdout, static_stderr, static_exit, static_json, static_md, static_sha256s],
        relative_to=static_artifact,
    )

    return {
        "runbook_execution_static_review_artifact_dir": static_artifact,
        "runbook_execution_static_review_json": static_json,
        "runbook_execution_static_review_md": static_md,
        "runbook_execution_static_review_sha256s": static_sha256s,
        "source_runbook_execution_artifact_dir": execution_artifact,
        "source_runbook_execution_json": execution_json,
        "source_runbook_execution_md": execution_md,
        "source_runbook_execution_sha256s": execution_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_static_review_payload(
    module,
    execution_artifact: Path,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.SOURCE_STATIC_REVIEW_STATUS.replace("_passed", "_only"),
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed": True,
        "evaluation_runbook_execution_result_review_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
        "evaluation_runbook_executed_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "current_camp_head": STATIC_HEAD,
            "current_camp_origin_main": STATIC_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "runbook_execution_artifact_dir": str(execution_artifact.resolve()),
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_execution_summary": {
            "schema_version": module.SOURCE_EXECUTION_SCHEMA,
            "status": module.SOURCE_EXECUTION_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_STATIC_REVIEW_STATUS.replace("_passed", "_only"),
            "check_count": 216,
            "metrics_manifest_count": 6,
            "no_go_summary_count": 8,
            "evidence_matrix_count": 6,
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [{"name": f"fixture_check_{index}", "passed": True} for index in range(136)],
        "final_decision": decision,
    }


def _source_execution_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
    no_go_triggered: bool = False,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_EXECUTION_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.SOURCE_STATIC_REVIEW_STATUS.replace("_passed", "_only"),
        "post_closeout_promotion_readiness_evaluation_runbook_execution_passed": True,
        "evaluation_runbook_execution_static_review_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
        "evaluation_runbook_executed_by_this_gate": True,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    no_go = []
    for index, name in enumerate(module.EXPECTED_NO_GO):
        no_go.append({"name": name, "triggered": no_go_triggered and index == 0})
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "analysis": {
            "execution_only": True,
            "read_only": True,
            "materializes_nonclaim_evidence_matrix": True,
            "current_camp_head": EXECUTION_HEAD,
            "current_camp_origin_main": EXECUTION_HEAD,
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
        "metrics_manifest": [
            {"name": name, "status": "materialized_nonclaim"}
            for name in module.EXPECTED_METRICS
        ],
        "no_go_summary": no_go,
        "evidence_matrix": [
            {"name": name, "source": "fixture", "claim": "none"}
            for name in module.EXPECTED_METRICS
        ],
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "execution_checks": [{"name": f"fixture_check_{index}", "passed": True} for index in range(216)],
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
