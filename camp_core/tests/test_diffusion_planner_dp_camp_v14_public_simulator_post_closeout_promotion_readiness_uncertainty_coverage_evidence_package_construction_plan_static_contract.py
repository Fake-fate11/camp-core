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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction.py"
)
PLAN_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan.py"
)
ARTIFACT_HEAD = "7" * 40
CURRENT_HEAD = "8" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_contract",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_passes(
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
    assert decision["uncertainty_coverage_evidence_package_construction_plan_static_review_passed"] is True
    assert decision["uncertainty_coverage_evidence_package_construction_authorized"] is True
    assert decision["evidence_package_constructed_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["package_plan_summary"]["package_plan_item_count"] == 5
    assert report["package_plan_summary"]["all_no_construction"] is True
    assert report["package_plan_summary"]["all_no_execution"] is True
    assert report["package_plan_summary"]["all_no_claim"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_requires_enable(
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
        == "explicit_uncertainty_coverage_evidence_package_construction_plan_static_review_authorization_missing"
    )


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_rejects_source_leak(
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
    assert "source_plan_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_rejects_plan_item_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        package_plan_updates={"claim_boundary_register": {"authorizes_claim": True}},
    )

    report = module.build_report(**fixture)

    assert "source_package_plan_no_claim" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_evidence_package_construction_plan_static_review_contract_failure"
    )


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_rejects_source_surface_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["plan_script_py"] = _write(tmp_path / "bad_plan.py", "missing surface tokens\n")

    report = module.build_report(**fixture)

    assert "plan_script_schema_token" in report["final_decision"]["failed_checks"]
    assert "plan_script_static_review_next" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_evidence_package_construction_plan_static_review_contract_failure"
    )


def test_uncertainty_coverage_evidence_package_construction_plan_static_contract_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_package_construction_plan_artifact_dir",
            str(fixture["evidence_package_construction_plan_artifact_dir"]),
            "--evidence_package_construction_plan_json",
            str(fixture["evidence_package_construction_plan_json"]),
            "--evidence_package_construction_plan_md",
            str(fixture["evidence_package_construction_plan_md"]),
            "--evidence_package_construction_plan_sha256s",
            str(fixture["evidence_package_construction_plan_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review",
        ]
    )

    assert exit_code == 0
    assert (output_dir / module.REVIEW_JSON_NAME).is_file()
    assert (output_dir / module.REVIEW_MD_NAME).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    package_plan_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "plan_artifact"
    plan_dir = artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_package_construction_plan_ready=True",
            "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized=True",
            "evidence_package_constructed_by_this_gate=False",
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
        plan_dir / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_payload(
            module,
            decision_updates=source_decision_updates,
            package_plan_updates=package_plan_updates,
        ),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# Package Construction Plan\n")
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    command = _write(artifact / "COMMAND", "plan command\n")
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
        [command, heads, stdout, stderr, run_exit, plan_json, plan_md],
        relative_to=artifact,
    )

    return {
        "evidence_package_construction_plan_artifact_dir": artifact,
        "evidence_package_construction_plan_json": plan_json,
        "evidence_package_construction_plan_md": plan_md,
        "evidence_package_construction_plan_sha256s": plan_sha256s,
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
    package_plan_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_current_work": module.SOURCE_PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_package_construction_plan_ready": True,
        "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized": True,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
        "recommendation": "static_review_uncertainty_coverage_evidence_package_construction_plan_only",
        "immediate_action": "evidence_package_construction_plan_static_review_only",
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)

    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "label": "unit",
            "plan_only": True,
            "read_only": True,
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "score_expression": module.SCORE_EXPRESSION,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_review_summary": {
            "schema_version": "source_review",
            "status": "passed",
            "passed": True,
            "authorized_next_work": module.SOURCE_PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
            "review_check_count": module.EXPECTED_SOURCE_REVIEW_CHECK_COUNT,
        },
        "source_materialization_summary": {
            "schema_version": "source_materialization",
            "status": "passed",
            "passed": True,
            "materialized_manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "materialization_check_count": module.EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT,
        },
        "manifest_summary": {
            "manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "manifest_names": list(module.SOURCE_PLAN_MODULE.EXPECTED_MANIFESTS),
            "all_materialized": True,
            "all_no_execution": True,
            "all_no_claim": True,
        },
        "evidence_package_construction_plan": _package_plan(module, updates=package_plan_updates),
        "blocked_actions": {action: False for action in module.BLOCKED_ACTIONS},
        "plan_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_PLAN_CHECK_COUNT)
        ],
        "final_decision": decision,
    }


def _package_plan(
    module,
    *,
    updates: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    items = []
    for name in module.PACKAGE_PLAN_ITEMS:
        item = {
            "item_name": name,
            "label": "unit",
            "purpose": f"purpose for {name}",
            "source_static_review_status": module.SOURCE_PLAN_MODULE.SOURCE_STATIC_REVIEW_STATUS,
            "source_materialization_status": module.SOURCE_PLAN_MODULE.SOURCE_MATERIALIZATION_STATUS,
            "source_manifests_dir": "/tmp/manifests",
            "required_manifest_names": list(module.SOURCE_PLAN_MODULE.EXPECTED_MANIFESTS),
            "package_constructed_by_this_gate": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        }
        if updates and name in updates:
            item.update(updates[name])
        items.append(item)
    return items


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
    for file in files:
        key = file.relative_to(relative_to).as_posix() if relative_to else file.name
        rows.append(f"{_sha256(file)}  {key}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
