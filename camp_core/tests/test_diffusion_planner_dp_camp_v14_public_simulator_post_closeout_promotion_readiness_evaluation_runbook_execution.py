from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook.py"
)
SOURCE_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_execution_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evaluation_runbook_executed_by_this_gate"] is True
    assert decision["evaluation_runbook_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["metrics_manifest"]) == 6
    assert len(report["evidence_matrix"]) == 6
    assert {item["triggered"] for item in report["no_go_summary"]} == {False}
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_execution_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "runbook_execution_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_runbook_execution_authorization_missing"
    )


def test_promotion_readiness_evaluation_runbook_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_runbook_execution" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_runbook_execution" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_execution_rejects_source_static_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_static_review_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_decision_deployment_authorized" in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_execution_cli_writes_outputs(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_execution_preflight_static_review_artifact_dir",
            str(fixture["runbook_execution_preflight_static_review_artifact_dir"]),
            "--runbook_execution_preflight_static_review_json",
            str(fixture["runbook_execution_preflight_static_review_json"]),
            "--runbook_execution_preflight_static_review_md",
            str(fixture["runbook_execution_preflight_static_review_md"]),
            "--runbook_execution_preflight_static_review_sha256s",
            str(fixture["runbook_execution_preflight_static_review_sha256s"]),
            "--source_runbook_execution_preflight_artifact_dir",
            str(fixture["source_runbook_execution_preflight_artifact_dir"]),
            "--source_runbook_execution_preflight_json",
            str(fixture["source_runbook_execution_preflight_json"]),
            "--source_runbook_execution_preflight_md",
            str(fixture["source_runbook_execution_preflight_md"]),
            "--source_runbook_execution_preflight_sha256s",
            str(fixture["source_runbook_execution_preflight_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_static_review_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_plan_json = _write_json(
        tmp_path / "source_plan" / "plan" / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_payload(module),
    )
    static_artifact = tmp_path / "execution_preflight_static_review_artifact"
    preflight_artifact = tmp_path / "execution_preflight_artifact"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=True",
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

    static_json = _write_json(
        static_artifact / "review" / module.STATIC_REVIEW_JSON_NAME,
        _source_static_review_payload(
            module,
            decision_updates=source_static_review_decision_updates,
        ),
    )
    static_md = _write(static_artifact / "review" / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_sha256s = _write_sha256sums(static_artifact / "review" / "SHA256SUMS", [static_json, static_md])
    static_command = _write(static_artifact / "COMMAND", "static review command\n")
    static_heads = _write(
        static_artifact / "HEADS",
        f"camp_head={SOURCE_HEAD}\ncamp_origin_main={SOURCE_HEAD}\ndp_head={module.FIXED_DP_HEAD}\n",
    )
    static_stdout = _write(static_artifact / "stdout.txt", "ok\n")
    static_stderr = _write(static_artifact / "stderr.txt", "")
    static_exit = _write(static_artifact / "run.exit", "0\n")
    _write_sha256sums(
        static_artifact / "SHA256SUMS",
        [static_heads, static_command, static_stdout, static_stderr, static_exit, static_json, static_md, static_sha256s],
        relative_to=static_artifact,
    )

    preflight_json = _write_json(
        preflight_artifact / "preflight" / module.PREFLIGHT_JSON_NAME,
        _source_preflight_payload(module, source_plan_json),
    )
    preflight_md = _write(preflight_artifact / "preflight" / module.PREFLIGHT_MD_NAME, "# Preflight\n")
    preflight_sha256s = _write_sha256sums(preflight_artifact / "preflight" / "SHA256SUMS", [preflight_json, preflight_md])
    preflight_command = _write(preflight_artifact / "COMMAND", "preflight command\n")
    preflight_heads = _write(
        preflight_artifact / "HEADS",
        f"camp_head={SOURCE_HEAD}\ncamp_origin_main={SOURCE_HEAD}\ndp_head={module.FIXED_DP_HEAD}\n",
    )
    preflight_stdout = _write(preflight_artifact / "stdout.txt", "ok\n")
    preflight_stderr = _write(preflight_artifact / "stderr.txt", "")
    preflight_exit = _write(preflight_artifact / "run.exit", "0\n")
    _write_sha256sums(
        preflight_artifact / "SHA256SUMS",
        [preflight_heads, preflight_command, preflight_stdout, preflight_stderr, preflight_exit, preflight_json, preflight_md, preflight_sha256s],
        relative_to=preflight_artifact,
    )

    return {
        "runbook_execution_preflight_static_review_artifact_dir": static_artifact,
        "runbook_execution_preflight_static_review_json": static_json,
        "runbook_execution_preflight_static_review_md": static_md,
        "runbook_execution_preflight_static_review_sha256s": static_sha256s,
        "source_runbook_execution_preflight_artifact_dir": preflight_artifact,
        "source_runbook_execution_preflight_json": preflight_json,
        "source_runbook_execution_preflight_md": preflight_md,
        "source_runbook_execution_preflight_sha256s": preflight_sha256s,
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
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "evaluation_runbook_execution_authorized": True,
        "score_expression": module.SCORE_EXPRESSION,
        "evaluation_runbook_executed_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.SOURCE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "current_camp_head": SOURCE_HEAD,
            "current_camp_origin_main": SOURCE_HEAD,
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
            "evaluation_runbook_execution": False,
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [{"name": "fixture_check", "passed": True}],
        "final_decision": decision,
    }


def _source_preflight_payload(module, source_plan_json: Path) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK,
        "evaluation_runbook_execution_preflight_static_review_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.SOURCE_EXECUTION_FLAGS:
        decision[flag] = False
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
        "analysis": {
            "preflight_only": True,
            "read_only": True,
            "current_camp_head": SOURCE_HEAD,
            "current_camp_origin_main": SOURCE_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_runbook_plan_json": str(source_plan_json),
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "preflight_checks": [{"name": "fixture_check", "passed": True}],
        "runbook_execution_preflight": [
            {"name": name, "status": "ready_for_static_review_only"}
            for name in [
                "source_artifact_inventory",
                "fixed_dp_candidate_tensor_boundary",
                "split_seed_zero_overlap_boundary",
                "default_off_shadow_selector_no_output_effect_boundary",
                "metric_uncertainty_and_no_claim_boundary",
                "execution_command_dry_run_boundary",
                "claim_promotion_deployment_stop_boundary",
            ]
        ],
        "final_decision": decision,
    }


def _source_plan_payload(module) -> dict[str, Any]:
    return {
        "schema_version": "source_plan",
        "runbook_plan": [
            {"name": name, "status": "planned_read_only_no_execution"}
            for name in module.EXPECTED_RUNBOOK_STEPS
        ],
        "metrics_plan": [
            {"name": name, "status": "planned_nonclaim"}
            for name in module.EXPECTED_METRICS
        ],
        "no_go_conditions": [
            {"name": name, "required_state": "not_triggered"}
            for name in module.EXPECTED_NO_GO
        ],
        "forbidden_actions": [{"name": f"forbidden_{index}", "status": "forbidden"} for index in range(10)],
        "final_decision": {
            "status": "source_plan_ready",
            "passed": True,
            "authorized_next_work": "source_plan_static_review_only",
        },
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
