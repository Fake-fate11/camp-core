from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook.py"
)
PLAN_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_plan_static_review_passes(
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
    assert decision["evaluation_runbook_execution_preflight_authorized"] is True
    assert decision["evaluation_runbook_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_plan_summary"]["runbook_step_count"] == 7
    assert report["source_plan_summary"]["artifact_count"] == 9
    assert report["source_plan_summary"]["metrics_count"] == 6
    assert report["source_plan_summary"]["decision_criteria_count"] == 6
    assert report["source_plan_summary"]["no_go_count"] == 8
    assert report["source_plan_summary"]["forbidden_action_count"] == 10
    assert report["source_plan_summary"]["future_review_count"] == 4
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_plan_static_review_accepts_uppercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, dp_key="DP_HEAD")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "artifact_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_plan_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_runbook_plan_static_review_authorization_missing"
    )


def test_promotion_readiness_evaluation_runbook_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["runbook_plan_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_plan_md_plan_sha" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "runbook_plan_artifact_sha256_mismatch"
    )


def test_promotion_readiness_evaluation_runbook_plan_static_review_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_plan_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_plan_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_readiness_evaluation_runbook_plan_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_plan_artifact_dir",
            str(fixture["runbook_plan_artifact_dir"]),
            "--runbook_plan_json",
            str(fixture["runbook_plan_json"]),
            "--runbook_plan_md",
            str(fixture["runbook_plan_md"]),
            "--runbook_plan_sha256s",
            str(fixture["runbook_plan_sha256s"]),
            "--plan_script_py",
            str(fixture["plan_script_py"]),
            "--plan_test_py",
            str(fixture["plan_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_plan_decision_updates: dict[str, Any] | None = None,
    dp_key: str = "dp_head",
) -> dict[str, Any]:
    artifact = tmp_path / "runbook_plan_artifact"
    plan_dir = artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_plan_ready=True",
            "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_authorized=True",
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

    plan_json = _write_json(
        plan_dir / module.PLAN_JSON_NAME,
        _source_plan_payload(module, decision_updates=source_plan_decision_updates),
    )
    plan_md = _write(plan_dir / module.PLAN_MD_NAME, "# Runbook Plan\n")
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    command = _write(artifact / "COMMAND", "runbook plan command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"{dp_key}={module.FIXED_DP_HEAD}",
                "source_runbook_preflight_static_review_artifact=/tmp/preflight_static_review",
                "source_runbook_preflight_artifact=/tmp/preflight",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, plan_json, plan_md, plan_sha256s, run_exit, stderr, stdout],
        relative_to=artifact,
    )

    return {
        "runbook_plan_artifact_dir": artifact,
        "runbook_plan_json": plan_json,
        "runbook_plan_md": plan_md,
        "runbook_plan_sha256s": plan_sha256s,
        "plan_script_py": PLAN_SCRIPT_PATH,
        "plan_test_py": PLAN_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
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
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
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
            for name in module.EXPECTED_RUNBOOK_STEPS
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

