from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_contract.py"
)
PREFLIGHT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.py"
)
PREFLIGHT_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passes(
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
    assert decision["evaluation_runbook_execution_authorized"] is True
    assert decision["evaluation_runbook_executed_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_preflight_summary"]["runbook_execution_preflight_step_count"] == 7
    assert report["source_preflight_summary"]["artifact_manifest_requirement_count"] == 7
    assert report["source_preflight_summary"]["no_go_status_count"] == 8
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_accepts_uppercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, dp_key="DP_HEAD")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "artifact_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_accepts_prior_source_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["current_camp_head"] = CURRENT_HEAD
    fixture["current_camp_origin_main"] = CURRENT_HEAD

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "artifact_heads_camp_matches_source_analysis" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_requires_enable(
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
        == "explicit_runbook_execution_preflight_static_review_authorization_missing"
    )


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["runbook_execution_preflight_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_preflight_md_preflight_sha" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "runbook_execution_preflight_artifact_sha256_mismatch"
    )


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_preflight_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_preflight_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_readiness_evaluation_runbook_execution_preflight_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--runbook_execution_preflight_artifact_dir",
            str(fixture["runbook_execution_preflight_artifact_dir"]),
            "--runbook_execution_preflight_json",
            str(fixture["runbook_execution_preflight_json"]),
            "--runbook_execution_preflight_md",
            str(fixture["runbook_execution_preflight_md"]),
            "--runbook_execution_preflight_sha256s",
            str(fixture["runbook_execution_preflight_sha256s"]),
            "--preflight_script_py",
            str(fixture["preflight_script_py"]),
            "--preflight_test_py",
            str(fixture["preflight_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_preflight_decision_updates: dict[str, Any] | None = None,
    dp_key: str = "dp_head",
) -> dict[str, Any]:
    artifact = tmp_path / "runbook_execution_preflight_artifact"
    preflight_dir = artifact / "preflight"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready=True",
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_authorized=True",
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

    preflight_json = _write_json(
        preflight_dir / module.PREFLIGHT_JSON_NAME,
        _source_preflight_payload(module, decision_updates=source_preflight_decision_updates),
    )
    preflight_md = _write(preflight_dir / module.PREFLIGHT_MD_NAME, "# Runbook Execution Preflight\n")
    preflight_sha256s = _write_sha256sums(
        preflight_dir / "SHA256SUMS",
        [preflight_json, preflight_md],
    )
    command = _write(artifact / "COMMAND", "runbook execution preflight command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"{dp_key}={module.FIXED_DP_HEAD}",
                "source_runbook_plan_static_review_artifact=/tmp/static_review",
                "source_runbook_plan_artifact=/tmp/plan",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, preflight_json, preflight_md, preflight_sha256s, run_exit, stderr, stdout],
        relative_to=artifact,
    )

    return {
        "runbook_execution_preflight_artifact_dir": artifact,
        "runbook_execution_preflight_json": preflight_json,
        "runbook_execution_preflight_md": preflight_md,
        "runbook_execution_preflight_sha256s": preflight_sha256s,
        "preflight_script_py": PREFLIGHT_SCRIPT_PATH,
        "preflight_test_py": PREFLIGHT_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
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
        "authorized_current_work": module.SOURCE_PREFLIGHT_STATUS.replace("_ready", "_only"),
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready": True,
        "evaluation_runbook_execution_preflight_static_review_authorized": True,
        "score_expression": module.SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
        "evaluation_runbook_executed_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
        "analysis": {
            "label": "fixture",
            "preflight_only": True,
            "read_only": True,
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "runbook_plan_static_review_artifact_dir": "/tmp/static_review",
            "source_runbook_plan_artifact_dir": "/tmp/plan",
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
        "source_static_review_summary": {
            "schema_version": "static_review",
            "status": "passed",
            "passed": True,
            "authorized_next_work": module.SOURCE_PREFLIGHT_STATUS.replace("_ready", "_only"),
            "review_check_count": 145,
        },
        "source_runbook_plan_summary": {
            "schema_version": "plan",
            "status": "ready",
            "passed": True,
            "authorized_next_work": "static_review_only",
            "plan_check_count": 186,
            "runbook_step_count": 7,
            "artifact_count": 9,
            "metrics_count": 6,
            "decision_criteria_count": 6,
            "no_go_condition_count": 8,
            "forbidden_action_count": 10,
            "future_review_count": 4,
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "preflight_checks": [{"name": "fixture_check", "passed": True}],
        "runbook_execution_preflight": [
            {"name": name, "status": "ready_for_static_review_only"}
            for name in module.EXPECTED_PREFLIGHT_STEPS
        ],
        "artifact_manifest_requirements": [
            {"name": name, "status": "required"}
            for name in module.EXPECTED_MANIFEST_REQUIREMENTS
        ],
        "no_go_status": [
            {"name": name, "triggered": False}
            for name in module.EXPECTED_NO_GO
        ],
        "future_review_requirements": [
            {"name": name, "status": "required"}
            for name in module.EXPECTED_FUTURE_REQUIREMENTS
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
