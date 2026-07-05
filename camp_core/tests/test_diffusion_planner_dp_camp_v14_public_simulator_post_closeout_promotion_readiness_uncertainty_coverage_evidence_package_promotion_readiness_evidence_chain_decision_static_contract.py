from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_contract.py"
)
DECISION_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "decide_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain.py"
)
DECISION_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision.py"
)
ARTIFACT_HEAD = "d" * 40
CURRENT_HEAD = "6" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_passes(
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
    assert decision["promotion_readiness_evidence_chain_decision_static_review_passed"] is True
    assert decision["promotion_readiness_evidence_chain_no_promotion_closeout_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_decision_summary"]["decision_check_count"] == module.EXPECTED_DECISION_CHECK_COUNT
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_evidence_chain_decision_static_review_authorization_missing"


def test_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_decision_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_decision_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_rejects_decision_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_decision_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["decision_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_decision_md_root_sha" in report["final_decision"]["failed_checks"]
    assert "source_decision_md_decision_sha" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "decision_artifact"
    decision_dir = artifact / "decision"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_DECISION_STATUS}",
            f"next_work_target={current_next}",
            "promotion_readiness_evidence_chain_decision_recorded=True",
            "promotion_readiness_evidence_chain_decision_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    decision_json = _write_json(
        decision_dir / module.SOURCE_DECISION_JSON_NAME,
        _source_decision_payload(module, decision_updates=source_decision_updates),
    )
    decision_md = _write(decision_dir / module.SOURCE_DECISION_MD_NAME, "# Decision\n")
    decision_sha256s = _write_sha256sums(decision_dir / "SHA256SUMS", [decision_json, decision_md])
    command = _write(artifact / "COMMAND", "decision command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={ARTIFACT_HEAD}",
                f"CAMP_ORIGIN_MAIN={ARTIFACT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, stdout, stderr, run_exit, decision_json, decision_md, decision_sha256s],
        relative_to=artifact,
    )
    return {
        "decision_artifact_dir": artifact,
        "decision_json": decision_json,
        "decision_md": decision_md,
        "decision_sha256s": decision_sha256s,
        "decision_script_py": DECISION_SCRIPT_PATH,
        "decision_test_py": DECISION_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_decision_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_DECISION_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "promotion_readiness_evidence_chain_decision_recorded": True,
        "promotion_readiness_evidence_chain_decision_static_review_authorized": True,
        "recommendation": "do_not_promote_deploy_or_claim_from_current_evidence_chain",
        "direct_promotion_recommendation": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    analysis = {
        "record_only": True,
        "read_only": True,
        "current_camp_head": ARTIFACT_HEAD,
        "current_camp_origin_main": ARTIFACT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for flag in module.ANALYSIS_FALSE_FLAGS:
        analysis[flag] = False
    return {
        "schema_version": module.SOURCE_DECISION_SCHEMA,
        "analysis": analysis,
        "source_static_review_summary": {
            "review_check_count": module.EXPECTED_SOURCE_REVIEW_CHECK_COUNT,
            "failed_check_count": 0,
        },
        "source_decision_plan_summary": {
            "source_plan_check_count": module.EXPECTED_SOURCE_PLAN_CHECK_COUNT,
            "source_plan_failed_check_count": 0,
        },
        "evidence_chain_decision": [
            {
                "item_name": f"item_{index}",
                "promote_selector_now": False,
                "deploy_now": False,
                "claim_now": False,
            }
            for index in range(module.EXPECTED_DECISION_ITEM_COUNT)
        ],
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "decision_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_DECISION_CHECK_COUNT)
        ],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256sums(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for file in files:
        name = file.name if relative_to is None else file.relative_to(relative_to).as_posix()
        lines.append(f"{_sha256(file)}  {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
