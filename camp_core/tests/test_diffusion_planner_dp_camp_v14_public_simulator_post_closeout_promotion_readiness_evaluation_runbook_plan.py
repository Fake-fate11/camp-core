from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook.py"
)
STATIC_HEAD = "e" * 40
PREFLIGHT_HEAD = "d" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evaluation_runbook_plan_static_review_authorized"] is True
    assert decision["evaluation_runbook_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["runbook_plan"]) == 7
    assert len(report["planned_artifacts"]) == 9
    assert len(report["no_go_conditions"]) == 8
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_plan.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_plan.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_plan_accepts_uppercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, static_dp_key="DP_HEAD", preflight_dp_key="DP_HEAD")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "static_heads_dp_fixed" not in report["final_decision"]["failed_checks"]
    assert "preflight_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "runbook_plan_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_runbook_plan_authorization_missing"


def test_promotion_readiness_evaluation_runbook_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_runbook_plan" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_runbook_plan" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_plan_rejects_static_review_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["runbook_preflight_static_review_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "static_review_md_review_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_sha256_mismatch"


def test_promotion_readiness_evaluation_runbook_plan_rejects_static_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_static_review_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_readiness_evaluation_runbook_plan_rejects_preflight_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        preflight_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_preflight_decision_deployment_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["deployment_authorized"] is False


def test_promotion_readiness_evaluation_runbook_plan_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_preflight_static_review_artifact_dir",
            str(fixture["runbook_preflight_static_review_artifact_dir"]),
            "--runbook_preflight_static_review_json",
            str(fixture["runbook_preflight_static_review_json"]),
            "--runbook_preflight_static_review_md",
            str(fixture["runbook_preflight_static_review_md"]),
            "--runbook_preflight_static_review_sha256s",
            str(fixture["runbook_preflight_static_review_sha256s"]),
            "--source_runbook_preflight_artifact_dir",
            str(fixture["source_runbook_preflight_artifact_dir"]),
            "--source_runbook_preflight_json",
            str(fixture["source_runbook_preflight_json"]),
            "--source_runbook_preflight_md",
            str(fixture["source_runbook_preflight_md"]),
            "--source_runbook_preflight_sha256s",
            str(fixture["source_runbook_preflight_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_plan",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_plan.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_plan.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    static_decision_updates: dict[str, Any] | None = None,
    preflight_decision_updates: dict[str, Any] | None = None,
    static_dp_key: str = "dp_head",
    preflight_dp_key: str = "dp_head",
) -> dict[str, Any]:
    static_artifact = tmp_path / "static_review_artifact"
    static_dir = static_artifact / "review"
    preflight_artifact = tmp_path / "preflight_artifact"
    preflight_dir = preflight_artifact / "preflight"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed=True",
            "post_closeout_promotion_readiness_evaluation_runbook_plan_authorized=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
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

    preflight_json = _write_json(
        preflight_dir / module.PREFLIGHT_JSON_NAME,
        _source_preflight_payload(module, decision_updates=preflight_decision_updates),
    )
    preflight_md = _write(preflight_dir / module.PREFLIGHT_MD_NAME, "# Runbook Preflight\n")
    preflight_sha256s = _write_sha256sums(preflight_dir / "SHA256SUMS", [preflight_json, preflight_md])
    preflight_command = _write(preflight_artifact / "COMMAND", "preflight command\n")
    preflight_heads = _write(
        preflight_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={PREFLIGHT_HEAD}",
                f"camp_origin_main={PREFLIGHT_HEAD}",
                f"{preflight_dp_key}={module.FIXED_DP_HEAD}",
                "source_runbook_preflight_plan_static_review_artifact=/tmp/static_plan_review",
                "source_runbook_preflight_plan_artifact=/tmp/plan",
                "",
            ]
        ),
    )
    preflight_stdout = _write(preflight_artifact / "stdout.txt", "ok\n")
    preflight_stderr = _write(preflight_artifact / "stderr.txt", "")
    preflight_run_exit = _write(preflight_artifact / "run.exit", "0\n")
    _write_sha256sums(
        preflight_artifact / "SHA256SUMS",
        [
            preflight_command,
            preflight_heads,
            preflight_json,
            preflight_md,
            preflight_sha256s,
            preflight_run_exit,
            preflight_stderr,
            preflight_stdout,
        ],
        relative_to=preflight_artifact,
    )

    static_json = _write_json(
        static_dir / module.STATIC_REVIEW_JSON_NAME,
        _source_static_review_payload(
            module,
            source_preflight_artifact_dir=preflight_artifact,
            decision_updates=static_decision_updates,
        ),
    )
    static_md = _write(static_dir / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_sha256s = _write_sha256sums(static_dir / "SHA256SUMS", [static_json, static_md])
    static_command = _write(static_artifact / "COMMAND", "static review command\n")
    static_heads = _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={STATIC_HEAD}",
                f"camp_origin_main={STATIC_HEAD}",
                f"{static_dp_key}={module.FIXED_DP_HEAD}",
                f"source_runbook_preflight_artifact={preflight_artifact}",
                "",
            ]
        ),
    )
    static_stdout = _write(static_artifact / "stdout.txt", "ok\n")
    static_stderr = _write(static_artifact / "stderr.txt", "")
    static_run_exit = _write(static_artifact / "run.exit", "0\n")
    _write_sha256sums(
        static_artifact / "SHA256SUMS",
        [
            static_command,
            static_heads,
            static_json,
            static_md,
            static_sha256s,
            static_run_exit,
            static_stderr,
            static_stdout,
        ],
        relative_to=static_artifact,
    )

    return {
        "runbook_preflight_static_review_artifact_dir": static_artifact,
        "runbook_preflight_static_review_json": static_json,
        "runbook_preflight_static_review_md": static_md,
        "runbook_preflight_static_review_sha256s": static_sha256s,
        "source_runbook_preflight_artifact_dir": preflight_artifact,
        "source_runbook_preflight_json": preflight_json,
        "source_runbook_preflight_md": preflight_md,
        "source_runbook_preflight_sha256s": preflight_sha256s,
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
    source_preflight_artifact_dir: Path,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed": True,
        "evaluation_runbook_plan_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
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
            "runbook_preflight_artifact_dir": str(source_preflight_artifact_dir),
        },
        "source_preflight_summary": {
            "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
            "status": module.SOURCE_PREFLIGHT_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK,
            "check_count": 218,
            "runbook_preflight_step_count": 6,
            "artifact_manifest_requirement_count": 7,
            "no_go_status_count": 8,
            "future_review_requirement_count": 4,
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [{"name": "fixture_check", "passed": True}],
        "final_decision": decision,
    }


def _source_preflight_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK,
        "evaluation_runbook_preflight_static_review_authorized": True,
        "score_expression": module.SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
        "analysis": {
            "preflight_only": True,
            "read_only": True,
            "current_camp_head": PREFLIGHT_HEAD,
            "current_camp_origin_main": PREFLIGHT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "preflight_checks": [{"name": "fixture_check", "passed": True}],
        "runbook_preflight": [{"name": f"step_{index}", "status": "ready"} for index in range(6)],
        "artifact_manifest_requirements": [{"name": f"artifact_{index}", "status": "required"} for index in range(7)],
        "no_go_status": [{"name": f"no_go_{index}", "triggered": False} for index in range(8)],
        "future_review_requirements": [{"name": f"future_{index}", "status": "required"} for index in range(4)],
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
