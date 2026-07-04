from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_contract.py"
)
REVIEW_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage.py"
)
REVIEW_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review.py"
)
ARTIFACT_HEAD = "d" * 40
CURRENT_HEAD = "e" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_review_static_contract",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_uncertainty_coverage_review_static_contract_passes(
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
    assert decision["uncertainty_coverage_evidence_gap_closure_plan_authorized"] is True
    assert decision["direct_promotion_recommendation"] is False
    assert decision["promotion_decision_plan_authorized_next"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_review_summary"]["review_check_count"] == 227
    assert report["source_review_summary"]["review_item_count"] == 7
    assert report["source_review_summary"]["evidence_gap_count"] == 5
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_uncertainty_coverage_review_static_contract_requires_enable(
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
        == "explicit_uncertainty_coverage_review_static_review_authorization_missing"
    )


def test_promotion_readiness_uncertainty_coverage_review_static_contract_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_uncertainty_coverage_review_static_contract_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_review_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_review_decision_deployment_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["deployment_authorized"] is False


def test_promotion_readiness_uncertainty_coverage_review_static_contract_rejects_gap_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_evidence_gap=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_review_evidence_gap_names" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_uncertainty_coverage_review_contract_failure"


def test_promotion_readiness_uncertainty_coverage_review_static_contract_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--review_artifact_dir",
            str(fixture["review_artifact_dir"]),
            "--review_json",
            str(fixture["review_json"]),
            "--review_md",
            str(fixture["review_md"]),
            "--review_sha256s",
            str(fixture["review_sha256s"]),
            "--review_script_py",
            str(fixture["review_script_py"]),
            "--review_test_py",
            str(fixture["review_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_review_decision_updates: dict[str, Any] | None = None,
    drop_evidence_gap: bool = False,
) -> dict[str, Any]:
    artifact = tmp_path / "review_artifact"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_uncertainty_coverage_review_passed=True",
            "uncertainty_coverage_review_static_review_authorized=True",
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

    review_json = _write_json(
        artifact / "review" / module.SOURCE_REVIEW_JSON_NAME,
        _source_review_payload(
            module,
            decision_updates=source_review_decision_updates,
            drop_evidence_gap=drop_evidence_gap,
        ),
    )
    review_md = _write(artifact / "review" / module.SOURCE_REVIEW_MD_NAME, "# Review\n")
    review_sha256s = _write_sha256sums(artifact / "review" / "SHA256SUMS", [review_json, review_md])
    command = _write(artifact / "COMMAND", "review command\n")
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
        [command, heads, stdout, stderr, run_exit, review_json, review_md, review_sha256s],
        relative_to=artifact,
    )

    return {
        "review_artifact_dir": artifact,
        "review_json": review_json,
        "review_md": review_md,
        "review_sha256s": review_sha256s,
        "review_script_py": REVIEW_SCRIPT_PATH,
        "review_test_py": REVIEW_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
    drop_evidence_gap: bool = False,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.SOURCE_REVIEW_STATUS.replace("_passed", "_only"),
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_review_static_review_authorized": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.FALSE_EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    gap_names = list(module.EXPECTED_EVIDENCE_GAPS)
    if drop_evidence_gap:
        gap_names = gap_names[:-1]
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "uncertainty_coverage_review_only": True,
            "read_only": True,
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "uncertainty_coverage_review": [
            {
                "name": name,
                "status": "reviewed",
                "finding": "fixture",
                "authorizes_execution": False,
                "authorizes_claim": False,
            }
            for name in module.EXPECTED_REVIEW_ITEMS
        ],
        "evidence_gap_matrix": [
            {
                "name": name,
                "available_from_current_artifacts": False,
                "blocks_promotion_or_claim": True,
            }
            for name in gap_names
        ],
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [
            {"name": f"fixture_review_check_{index}", "passed": True}
            for index in range(227)
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
