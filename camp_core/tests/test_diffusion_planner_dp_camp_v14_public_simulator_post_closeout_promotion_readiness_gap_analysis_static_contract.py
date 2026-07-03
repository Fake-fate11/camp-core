from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_contract.py"
)
GAP_ANALYSIS_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis.py"
)
GAP_ANALYSIS_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis.py"
)
ARTIFACT_HEAD = "c" * 40
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_gap_analysis_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_gap_analysis_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["promotion_readiness_evaluation_preflight_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert sorted(report["gap_categories"]) == sorted(module.EXPECTED_GAP_CATEGORIES)
    assert sorted(report["readiness_surfaces"]) == sorted(module.EXPECTED_DECISION_SURFACES)
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_gap_analysis_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_gap_analysis_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_gap_analysis_static_review_requires_enable(
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
        == "explicit_gap_analysis_static_review_authorization_missing"
    )


def test_post_closeout_gap_analysis_static_review_accepts_uppercase_heads(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, uppercase_heads=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "artifact_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_post_closeout_gap_analysis_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_gap_analysis_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["gap_analysis_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "artifact_plan_md_plan_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "gap_analysis_artifact_sha256_mismatch"


def test_post_closeout_gap_analysis_static_review_rejects_promotion_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert (
        "source_gap_analysis_decision_selector_promotion_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_post_closeout_gap_analysis_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--gap_analysis_artifact_dir",
            str(fixture["gap_analysis_artifact_dir"]),
            "--gap_analysis_json",
            str(fixture["gap_analysis_json"]),
            "--gap_analysis_md",
            str(fixture["gap_analysis_md"]),
            "--gap_analysis_sha256s",
            str(fixture["gap_analysis_sha256s"]),
            "--gap_analysis_script_py",
            str(fixture["gap_analysis_script_py"]),
            "--gap_analysis_test_py",
            str(fixture["gap_analysis_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_gap_analysis_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir / "post_closeout_promotion_readiness_gap_analysis_static_review.json"
    ).is_file()
    assert (
        output_dir / "post_closeout_promotion_readiness_gap_analysis_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    uppercase_heads: bool = False,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact_dir = tmp_path / "artifact"
    plan_dir = artifact_dir / "plan"
    source_dirs = {
        key: tmp_path / "sources" / key
        for key in module.EXPECTED_SOURCE_ARTIFACT_DIR_KEYS
    }
    for path in source_dirs.values():
        path.mkdir(parents=True)
    previous_failed = tmp_path / "sources" / "previous_failed"
    previous_failed.mkdir(parents=True)

    docs = tmp_path / "docs"
    current_next = next_work or module.SOURCE_AUTHORIZED_NEXT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_gap_analysis_passed=True",
            "post_closeout_promotion_readiness_gap_analysis_static_review_authorized=True",
            "default_off_shadow_selector_runtime_no_promotion_closeout_complete=True",
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

    gap_json = _write_json(
        plan_dir / module.GAP_JSON_NAME,
        _gap_analysis_payload(
            module,
            source_dirs=source_dirs,
            decision_updates=decision_updates,
        ),
    )
    gap_md = _write(plan_dir / module.GAP_MD_NAME, "# Gap Analysis\n\nread-only\n")
    gap_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [gap_json, gap_md])

    command = _write(artifact_dir / "COMMAND", "plan command\n")
    heads = _write_heads(
        artifact_dir / "HEADS",
        module,
        uppercase=uppercase_heads,
        source_dirs=source_dirs,
        previous_failed=previous_failed,
    )
    stdout = _write(artifact_dir / "stdout.txt", "ok\n")
    stderr = _write(artifact_dir / "stderr.txt", "")
    run_exit = _write(artifact_dir / "run.exit", "0\n")
    _write_sha256sums(
        artifact_dir / "SHA256SUMS",
        [command, heads, gap_json, gap_md, run_exit, stderr, stdout],
        relative_to=artifact_dir,
    )

    return {
        "gap_analysis_artifact_dir": artifact_dir,
        "gap_analysis_json": gap_json,
        "gap_analysis_md": gap_md,
        "gap_analysis_sha256s": gap_sha256s,
        "gap_analysis_script_py": GAP_ANALYSIS_SCRIPT_PATH,
        "gap_analysis_test_py": GAP_ANALYSIS_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _gap_analysis_payload(
    module,
    *,
    source_dirs: dict[str, Path],
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": (
            "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
            "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
            "post_closeout_promotion_readiness_gap_analysis_plan_only"
        ),
        "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
        "post_closeout_promotion_readiness_gap_analysis_ready": True,
        "recommendation": "do_not_promote_or_deploy_from_current_evidence_package",
        "immediate_action": "static_review_this_gap_analysis_only",
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_GAP_ANALYSIS_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "artifact_dirs": {
                key: str(path.resolve()) for key, path in source_dirs.items()
            },
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
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "gap_analysis_checks": [{"name": "all", "passed": True}],
        "evidence_gaps": [
            {
                "category": category,
                "gap_status": "open",
                "current_evidence_limit": f"limit {category}",
                "required_future_evidence": [f"future {category}"],
            }
            for category in module.EXPECTED_GAP_CATEGORIES
        ],
        "promotion_readiness_matrix": [
            {
                "decision_surface": "promotion_readiness",
                "current_state": "not_ready_for_active_promotion",
                "next_allowed_gate": module.SOURCE_AUTHORIZED_NEXT_WORK,
                "promotion_authorized": False,
            },
            {
                "decision_surface": "deployment_readiness",
                "current_state": "not_ready_for_deployment",
                "next_allowed_gate": module.SOURCE_AUTHORIZED_NEXT_WORK,
                "deployment_authorized": False,
            },
            {
                "decision_surface": "safety_or_superiority_claim",
                "current_state": "not_ready_for_claim",
                "next_allowed_gate": module.SOURCE_AUTHORIZED_NEXT_WORK,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
        ],
        "final_decision": decision,
    }


def _write_heads(
    path: Path,
    module,
    *,
    uppercase: bool,
    source_dirs: dict[str, Path],
    previous_failed: Path,
) -> Path:
    rows = {
        "camp_head": ARTIFACT_HEAD,
        "camp_origin_main": ARTIFACT_HEAD,
        "dp_head": module.FIXED_DP_HEAD,
        "previous_failed_gap_analysis_artifact": str(previous_failed.resolve()),
        "source_evidence_package_artifact": str(source_dirs["evidence_package"].resolve()),
        "source_result_review_artifact": str(source_dirs["result_review"].resolve()),
        "source_shadow_vs_top1_delta_review_artifact": str(source_dirs["delta_review"].resolve()),
        "source_promotion_decision_plan_artifact": str(source_dirs["promotion_plan"].resolve()),
        "source_no_promotion_closeout_review_artifact": str(source_dirs["closeout_review"].resolve()),
    }
    if uppercase:
        rows = {key.upper(): value for key, value in rows.items()}
    return _write(path, "\n".join(f"{key}={value}" for key, value in rows.items()) + "\n")


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
