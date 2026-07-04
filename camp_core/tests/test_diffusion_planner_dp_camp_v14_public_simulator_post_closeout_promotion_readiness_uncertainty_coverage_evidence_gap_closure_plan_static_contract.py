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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure.py"
)
PLAN_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan.py"
)
ARTIFACT_HEAD = "c" * 40
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_contract",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["uncertainty_coverage_evidence_manifest_materialization_plan_authorized"] is True
    assert decision["direct_promotion_recommendation"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_plan_summary"]["plan_check_count"] == 143
    assert report["source_plan_summary"]["plan_item_count"] == 5
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_requires_enable(
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
        == "explicit_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorization_missing"
    )


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_direct_script_help(
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
    assert "evidence_gap_closure_plan_artifact_dir" in result.stdout
    assert "No module named 'scripts'" not in result.stderr


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_accepts_import_path_rerun_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        current_status=module.REJECT_STATUS,
        next_work=module.AUDITED_IMPORT_PATH_RERUN_NEXT_WORK,
        import_path_rerun=True,
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "audit_latest_status_is_source_plan_ready" not in report["final_decision"]["failed_checks"]
    assert "audit_latest_eof_authorizes_static_review" not in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_status_is_source_plan_ready" not in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" not in report["final_decision"]["failed_checks"]


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_rejects_source_leak(
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


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_rejects_gap_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_gap=True)

    report = module.build_report(**fixture)

    assert "source_plan_gap_names" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_evidence_gap_closure_plan_contract_failure"


def test_uncertainty_coverage_evidence_gap_closure_plan_static_contract_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_gap_closure_plan_artifact_dir",
            str(fixture["evidence_gap_closure_plan_artifact_dir"]),
            "--evidence_gap_closure_plan_json",
            str(fixture["evidence_gap_closure_plan_json"]),
            "--evidence_gap_closure_plan_md",
            str(fixture["evidence_gap_closure_plan_md"]),
            "--evidence_gap_closure_plan_sha256s",
            str(fixture["evidence_gap_closure_plan_sha256s"]),
            "--evidence_gap_closure_plan_script_py",
            str(fixture["evidence_gap_closure_plan_script_py"]),
            "--evidence_gap_closure_plan_test_py",
            str(fixture["evidence_gap_closure_plan_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    current_status: str | None = None,
    next_work: str | None = None,
    import_path_rerun: bool = False,
    source_decision_updates: dict[str, Any] | None = None,
    drop_gap: bool = False,
) -> dict[str, Any]:
    artifact = tmp_path / "closure_plan_artifact"
    plan_dir = artifact / "plan"
    docs = tmp_path / "docs"
    current_status_value = current_status or module.SOURCE_PLAN_STATUS
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_lines = [
        f"current_v14_status={current_status_value}",
        f"next_work_target={current_next}",
        "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_ready=True",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized=True",
    ]
    if import_path_rerun:
        doc_lines.extend(
            [
                "uncertainty_coverage_evidence_gap_closure_plan_static_review_import_path_fixed=True",
                "uncertainty_coverage_evidence_gap_closure_plan_static_review_passed=False",
                "uncertainty_coverage_evidence_manifest_materialization_plan_authorized=False",
            ]
        )
    doc_lines.extend(
        [
            "direct_promotion_recommendation=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    doc_text = "\n".join(doc_lines)
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    plan_json = _write_json(
        plan_dir / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_payload(module, decision_updates=source_decision_updates, drop_gap=drop_gap),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# Evidence-Gap Closure Plan\n")
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    command = _write(artifact / "COMMAND", "closure plan command\n")
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
        [command, heads, stdout, stderr, run_exit, plan_json, plan_md, plan_sha256s],
        relative_to=artifact,
    )
    return {
        "evidence_gap_closure_plan_artifact_dir": artifact,
        "evidence_gap_closure_plan_json": plan_json,
        "evidence_gap_closure_plan_md": plan_md,
        "evidence_gap_closure_plan_sha256s": plan_sha256s,
        "evidence_gap_closure_plan_script_py": PLAN_SCRIPT_PATH,
        "evidence_gap_closure_plan_test_py": PLAN_TEST_PATH,
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
    drop_gap: bool = False,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_ready": True,
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    gaps = list(module.EXPECTED_EVIDENCE_GAPS)
    if drop_gap:
        gaps.pop()
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
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
        "source_static_review_summary": {
            "static_review_check_count": module.EXPECTED_SOURCE["source_static_review_check_count"],
            "source_evidence_gap_count": module.EXPECTED_SOURCE["source_review_gap_count"],
        },
        "evidence_gap_closure_plan": [
            {"source_gap": gap, "authorizes_execution": False, "authorizes_claim": False}
            for gap in gaps
        ],
        "blocked_actions": {action: False for action in module.BLOCKED_ACTIONS},
        "plan_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_SOURCE["plan_check_count"])
        ],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_sha256sums(paths_file: Path, paths: list[Path], *, relative_to: Path | None = None) -> Path:
    paths_file.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        key = path.relative_to(relative_to).as_posix() if relative_to else path.name
        rows.append(f"{_sha256(path)}  {key}")
    paths_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return paths_file


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
