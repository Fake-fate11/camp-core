from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_execution_preflight_passes(
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
    assert decision["evaluation_runbook_execution_preflight_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["evaluation_runbook_execution_authorized"] is False
    assert len(report["runbook_execution_preflight"]) == 7
    assert len(report["artifact_manifest_requirements"]) == 7
    assert report["source_runbook_plan_summary"]["runbook_step_count"] == 7
    assert report["source_runbook_plan_summary"]["artifact_count"] == 9
    assert report["source_runbook_plan_summary"]["metrics_count"] == 6
    assert report["source_runbook_plan_summary"]["decision_criteria_count"] == 6
    assert report["source_runbook_plan_summary"]["forbidden_action_count"] == 10
    assert report["source_runbook_plan_summary"]["future_review_count"] == 4
    assert all(item["triggered"] is False for item in report["no_go_status"])
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_execution_preflight_accepts_uppercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, static_dp_key="DP_HEAD", source_dp_key="DP_HEAD")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "static_review_heads_dp_fixed" not in report["final_decision"]["failed_checks"]
    assert "source_plan_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_execution_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "runbook_execution_preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_runbook_execution_preflight_authorization_missing"
    )


def test_promotion_readiness_evaluation_runbook_execution_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_runbook_execution_preflight" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_runbook_execution_preflight" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_execution_preflight_rejects_source_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_runbook_plan_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "source_plan_md_plan_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_sha256_mismatch"


def test_promotion_readiness_evaluation_runbook_execution_preflight_rejects_source_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_review_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert (
        "source_static_review_decision_deployment_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["deployment_authorized"] is False


def test_promotion_readiness_evaluation_runbook_execution_preflight_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_plan_static_review_artifact_dir",
            str(fixture["runbook_plan_static_review_artifact_dir"]),
            "--runbook_plan_static_review_json",
            str(fixture["runbook_plan_static_review_json"]),
            "--runbook_plan_static_review_md",
            str(fixture["runbook_plan_static_review_md"]),
            "--runbook_plan_static_review_sha256s",
            str(fixture["runbook_plan_static_review_sha256s"]),
            "--source_runbook_plan_artifact_dir",
            str(fixture["source_runbook_plan_artifact_dir"]),
            "--source_runbook_plan_json",
            str(fixture["source_runbook_plan_json"]),
            "--source_runbook_plan_md",
            str(fixture["source_runbook_plan_md"]),
            "--source_runbook_plan_sha256s",
            str(fixture["source_runbook_plan_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    static_review_decision_updates: dict[str, Any] | None = None,
    source_plan_decision_updates: dict[str, Any] | None = None,
    static_dp_key: str = "dp_head",
    source_dp_key: str = "dp_head",
) -> dict[str, Any]:
    static_artifact = tmp_path / "static_review_artifact"
    review_dir = static_artifact / "review"
    plan_artifact = tmp_path / "runbook_plan_artifact"
    plan_dir = plan_artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_authorized=True",
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

    source_plan_json = _write_json(
        plan_dir / module.PLAN_JSON_NAME,
        _source_plan_payload(module, decision_updates=source_plan_decision_updates),
    )
    source_plan_md = _write(plan_dir / module.PLAN_MD_NAME, "# Runbook Plan\n")
    source_plan_sha256s = _write_sha256sums(
        plan_dir / "SHA256SUMS",
        [source_plan_json, source_plan_md],
    )
    plan_command = _write(plan_artifact / "COMMAND", "runbook plan command\n")
    plan_heads = _write(
        plan_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"{source_dp_key}={module.FIXED_DP_HEAD}",
                "source_runbook_preflight_static_review_artifact=/tmp/preflight_static_review",
                "source_runbook_preflight_artifact=/tmp/preflight",
                "",
            ]
        ),
    )
    plan_stdout = _write(plan_artifact / "stdout.txt", "ok\n")
    plan_stderr = _write(plan_artifact / "stderr.txt", "")
    plan_run_exit = _write(plan_artifact / "run.exit", "0\n")
    _write_sha256sums(
        plan_artifact / "SHA256SUMS",
        [
            plan_command,
            plan_heads,
            source_plan_json,
            source_plan_md,
            source_plan_sha256s,
            plan_run_exit,
            plan_stderr,
            plan_stdout,
        ],
        relative_to=plan_artifact,
    )

    static_review_json = _write_json(
        review_dir / module.STATIC_REVIEW_JSON_NAME,
        _static_review_payload(
            module,
            source_plan_artifact=plan_artifact,
            decision_updates=static_review_decision_updates,
        ),
    )
    static_review_md = _write(review_dir / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_review_sha256s = _write_sha256sums(
        review_dir / "SHA256SUMS",
        [static_review_json, static_review_md],
    )
    static_command = _write(static_artifact / "COMMAND", "static review command\n")
    static_heads = _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"{static_dp_key}={module.FIXED_DP_HEAD}",
                f"source_runbook_plan_artifact={plan_artifact.resolve()}",
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
            static_review_json,
            static_review_md,
            static_review_sha256s,
            static_run_exit,
            static_stderr,
            static_stdout,
        ],
        relative_to=static_artifact,
    )

    return {
        "runbook_plan_static_review_artifact_dir": static_artifact,
        "runbook_plan_static_review_json": static_review_json,
        "runbook_plan_static_review_md": static_review_md,
        "runbook_plan_static_review_sha256s": static_review_sha256s,
        "source_runbook_plan_artifact_dir": plan_artifact,
        "source_runbook_plan_json": source_plan_json,
        "source_runbook_plan_md": source_plan_md,
        "source_runbook_plan_sha256s": source_plan_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _static_review_payload(
    module,
    *,
    source_plan_artifact: Path,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "evaluation_runbook_execution_preflight_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "runbook_plan_artifact_dir": str(source_plan_artifact.resolve()),
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
        "review_checks": [{"name": "all", "passed": True}],
        "final_decision": decision,
    }


def _source_plan_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        "evaluation_runbook_plan_static_review_authorized": True,
        "evaluation_runbook_execution_authorized": False,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "runbook_preflight_static_review_artifact_dir": "/tmp/preflight_static_review",
            "source_runbook_preflight_artifact_dir": "/tmp/preflight",
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
        "plan_checks": [{"name": "all", "passed": True}],
        "runbook_plan": [
            {"name": name, "scope": "fixture"}
            for name in module.EXPECTED_RUNBOOK_PREFLIGHT_STEPS
        ],
        "planned_artifacts": [f"artifact_{index}" for index in range(9)],
        "metrics_plan": [f"metric_{index}" for index in range(6)],
        "decision_criteria_plan": [f"criterion_{index}" for index in range(6)],
        "no_go_conditions": [f"no_go_{index}" for index in range(8)],
        "forbidden_actions": [f"forbidden_{index}" for index in range(10)],
        "future_review_requirements": [f"review_{index}" for index in range(4)],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256sums(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    rows = []
    for item in files:
        name = item.name if relative_to is None else "./" + item.relative_to(relative_to).as_posix()
        rows.append(f"{_sha256(item)}  {name}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

