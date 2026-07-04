from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization.py"
)
PLAN_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_passes(
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
    assert decision["evidence_manifest_materialization_authorized"] is True
    assert decision["evidence_manifest_materialized_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_plan_summary"]["plan_check_count"] == 139
    assert report["source_plan_summary"]["manifest_plan_item_count"] == 5
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_requires_enable(
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
        == "explicit_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorization_missing"
    )


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_direct_script_help(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "evidence_manifest_materialization_plan_artifact_dir" in result.stdout
    assert "No module named 'scripts'" not in result.stderr


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_rejects_source_leak(
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


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_rejects_manifest_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_manifest=True)

    report = module.build_report(**fixture)

    assert "source_manifest_names" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_evidence_manifest_materialization_plan_contract_failure"


def test_uncertainty_coverage_evidence_manifest_materialization_plan_static_contract_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_manifest_materialization_plan_artifact_dir",
            str(fixture["evidence_manifest_materialization_plan_artifact_dir"]),
            "--evidence_manifest_materialization_plan_json",
            str(fixture["evidence_manifest_materialization_plan_json"]),
            "--evidence_manifest_materialization_plan_md",
            str(fixture["evidence_manifest_materialization_plan_md"]),
            "--evidence_manifest_materialization_plan_sha256s",
            str(fixture["evidence_manifest_materialization_plan_sha256s"]),
            "--evidence_manifest_materialization_plan_script_py",
            str(fixture["evidence_manifest_materialization_plan_script_py"]),
            "--evidence_manifest_materialization_plan_test_py",
            str(fixture["evidence_manifest_materialization_plan_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    drop_manifest: bool = False,
) -> dict[str, Any]:
    artifact = tmp_path / "materialization_plan_artifact"
    plan_dir = artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_manifest_materialization_plan_ready=True",
            "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized=True",
            "evidence_manifest_materialization_authorized=False",
            "direct_promotion_recommendation=False",
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
            drop_manifest=drop_manifest,
        ),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# Materialization Plan\n")
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
    plan_script = _write(
        tmp_path / "plan_script.py",
        "\n".join(
            [
                module.SOURCE_PLAN_SCHEMA,
                module.AUTHORIZED_CURRENT_WORK,
                "enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan",
                "",
            ]
        ),
    )
    plan_test = _write(
        tmp_path / "test_plan.py",
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized\n"
        "rejects_existing_manifest_root\n",
    )
    return {
        "evidence_manifest_materialization_plan_artifact_dir": artifact,
        "evidence_manifest_materialization_plan_json": plan_json,
        "evidence_manifest_materialization_plan_md": plan_md,
        "evidence_manifest_materialization_plan_sha256s": plan_sha256s,
        "evidence_manifest_materialization_plan_script_py": plan_script,
        "evidence_manifest_materialization_plan_test_py": plan_test,
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
    drop_manifest: bool = False,
) -> dict[str, Any]:
    manifest_plan = [
        {
            "manifest_name": name,
            "source_gap": f"gap_for_{name}",
            "planned_path": f"/future/{name}.json",
            "required_inputs": ["source_review"],
            "acceptance_checks": ["read_only"],
            "materialized_by_this_gate": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
        }
        for name in module.EXPECTED_MANIFESTS
    ]
    if drop_manifest:
        manifest_plan = manifest_plan[:-1]
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_manifest_materialization_plan_ready": True,
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized": True,
        "evidence_manifest_materialization_authorized": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
        "recommendation": "static_review_evidence_manifest_materialization_plan_only",
        "immediate_action": "evidence_manifest_materialization_plan_static_review_only",
    }
    for action in module.PLAN_MODULE.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "uncertainty_coverage_evidence_manifest_materialization_plan_only": True,
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
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_static_review_summary": {
            "static_review_check_count": 157,
            "source_plan_check_count": 143,
            "source_plan_item_count": 5,
            "source_static_review_check_count": 134,
            "source_review_gap_count": 5,
        },
        "evidence_manifest_materialization_plan": manifest_plan,
        "blocked_actions": {action: False for action in module.PLAN_MODULE.BLOCKED_ACTIONS},
        "plan_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(139)
        ],
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
    for file_path in files:
        digest = _sha256(file_path)
        name = str(file_path.relative_to(relative_to)) if relative_to else file_path.name
        rows.append(f"{digest}  {name.replace(chr(92), '/')}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
