from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_passes(
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
    assert decision["uncertainty_coverage_review_preflight_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["uncertainty_coverage_review_preflight"]) == 7
    assert len(report["artifact_manifest_requirements"]) == 7
    assert all(item["triggered"] is False for item in report["no_go_status"])
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_preflight_authorization_missing"
    )


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_preflight" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_preflight" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_rejects_source_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_review_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_static_review_decision_deployment_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["deployment_authorized"] is False


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_rejects_source_plan_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_preflight_plan_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "source_preflight_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_sha256_mismatch"


def test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--preflight_plan_static_review_artifact_dir",
            str(fixture["preflight_plan_static_review_artifact_dir"]),
            "--preflight_plan_static_review_json",
            str(fixture["preflight_plan_static_review_json"]),
            "--preflight_plan_static_review_md",
            str(fixture["preflight_plan_static_review_md"]),
            "--preflight_plan_static_review_sha256s",
            str(fixture["preflight_plan_static_review_sha256s"]),
            "--source_preflight_plan_artifact_dir",
            str(fixture["source_preflight_plan_artifact_dir"]),
            "--source_preflight_plan_json",
            str(fixture["source_preflight_plan_json"]),
            "--source_preflight_plan_md",
            str(fixture["source_preflight_plan_md"]),
            "--source_preflight_plan_sha256s",
            str(fixture["source_preflight_plan_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    static_review_decision_updates: dict[str, Any] | None = None,
    source_plan_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    static_artifact = tmp_path / "static_review_artifact"
    review_dir = static_artifact / "review"
    plan_artifact = tmp_path / "preflight_plan_artifact"
    plan_dir = plan_artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            f"v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_artifact={static_artifact.resolve()}",
            "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_passed=True",
            "uncertainty_coverage_review_preflight_authorized=True",
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
        plan_dir / module.PREFLIGHT_PLAN_JSON_NAME,
        _source_plan_payload(module, decision_updates=source_plan_decision_updates),
    )
    source_plan_md = _write(plan_dir / module.PREFLIGHT_PLAN_MD_NAME, "# Preflight Plan\n")
    source_plan_sha256s = _write_sha256sums(
        plan_dir / "SHA256SUMS",
        [source_plan_json, source_plan_md],
    )

    static_review_json = _write_json(
        review_dir / module.STATIC_REVIEW_JSON_NAME,
        _static_review_payload(module, decision_updates=static_review_decision_updates),
    )
    static_review_md = _write(review_dir / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_review_sha256s = _write_sha256sums(
        review_dir / "SHA256SUMS",
        [static_review_json, static_review_md],
    )

    command = _write(static_artifact / "COMMAND", "static review command\n")
    heads = _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"dp_head={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(static_artifact / "stdout.txt", "ok\n")
    stderr = _write(static_artifact / "stderr.txt", "")
    run_exit = _write(static_artifact / "run.exit", "0\n")
    _write_sha256sums(
        static_artifact / "SHA256SUMS",
        [
            command,
            heads,
            static_review_json,
            static_review_md,
            static_review_sha256s,
            run_exit,
            stderr,
            stdout,
        ],
        relative_to=static_artifact,
    )

    return {
        "preflight_plan_static_review_artifact_dir": static_artifact,
        "preflight_plan_static_review_json": static_review_json,
        "preflight_plan_static_review_md": static_review_md,
        "preflight_plan_static_review_sha256s": static_review_sha256s,
        "source_preflight_plan_artifact_dir": plan_artifact,
        "source_preflight_plan_json": source_plan_json,
        "source_preflight_plan_md": source_plan_md,
        "source_preflight_plan_sha256s": source_plan_sha256s,
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
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_review_preflight_authorized": True,
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
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [
            {"name": f"fixture_check_{index}", "passed": True}
            for index in range(module.EXPECTED_SOURCE["static_review_check_count"])
        ],
        "final_decision": decision,
    }


def _source_plan_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PREFLIGHT_PLAN_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.SOURCE_PREFLIGHT_PLAN_AUTHORIZED_NEXT_WORK,
        "uncertainty_coverage_review_preflight_plan_static_review_authorized": True,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PREFLIGHT_PLAN_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
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
            "review_check_count": module.EXPECTED_SOURCE["source_review_check_count"],
            "source_plan_check_count": module.EXPECTED_SOURCE["source_plan_check_count"],
            "source_plan_item_count": module.EXPECTED_SOURCE["source_plan_item_count"],
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "plan_checks": [
            {"name": f"fixture_check_{index}", "passed": True}
            for index in range(module.EXPECTED_SOURCE["preflight_plan_check_count"])
        ],
        "preflight_plan": [
            {
                "name": name,
                "authorizes_execution": False,
                "authorizes_claim": False,
            }
            for name in module.EXPECTED_PREFLIGHT_PLAN_ITEMS
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
