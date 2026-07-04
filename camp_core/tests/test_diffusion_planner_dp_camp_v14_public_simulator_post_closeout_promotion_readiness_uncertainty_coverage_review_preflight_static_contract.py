from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_contract.py"
)
PREFLIGHT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review.py"
)
PREFLIGHT_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passes(
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
    assert decision["uncertainty_coverage_review_authorized"] is True
    assert decision["direct_promotion_recommendation"] is False
    assert decision["promotion_decision_plan_authorized_next"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_preflight_summary"]["check_count"] == 190
    assert report["source_preflight_summary"]["review_preflight_item_count"] == 7
    assert report["source_preflight_summary"]["artifact_manifest_requirement_count"] == 7
    assert report["source_preflight_summary"]["future_review_requirement_count"] == 5
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_requires_enable(
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
        == "explicit_preflight_static_review_authorization_missing"
    )


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_accepts_audited_rerun_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, failed_rerun_eof=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "audit_latest_eof_authorizes_static_review" not in report["final_decision"]["failed_checks"]
    assert "audit_preflight_static_review_authorized" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        preflight_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert (
        "source_preflight_decision_selector_promotion_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["preflight_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "artifact_preflight_md_preflight_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "preflight_artifact_sha256_mismatch"


def test_promotion_readiness_uncertainty_coverage_review_preflight_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--preflight_artifact_dir",
            str(fixture["preflight_artifact_dir"]),
            "--preflight_json",
            str(fixture["preflight_json"]),
            "--preflight_md",
            str(fixture["preflight_md"]),
            "--preflight_sha256s",
            str(fixture["preflight_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    failed_rerun_eof: bool = False,
    preflight_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "preflight_artifact"
    preflight_dir = artifact / "preflight"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready=True",
            "uncertainty_coverage_review_preflight_static_review_authorized=True",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "dp_modification_authorized_by_current_boundary=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    if failed_rerun_eof:
        doc_text += "\n".join(
            [
                f"current_v14_status={module.FAILED_ATTEMPT_STATUS}",
                f"next_work_target={module.AUTHORIZED_RERUN_DECISION_WORK}",
                f"{module.FAILED_ATTEMPT_PREFIX}_failure_class=v14_eof_contract_mismatch",
                f"{module.FAILED_ATTEMPT_PREFIX}_checks=audit_preflight_static_review_authorized",
                "",
            ]
        )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    preflight_json = _write_json(
        preflight_dir / module.PREFLIGHT_JSON_NAME,
        _preflight_payload(module, decision_updates=preflight_decision_updates),
    )
    preflight_md = _write(preflight_dir / module.PREFLIGHT_MD_NAME, "# Preflight\n")
    preflight_sha256s = _write_sha256sums(
        preflight_dir / "SHA256SUMS",
        [preflight_json, preflight_md],
    )
    command = _write(artifact / "COMMAND", "preflight command\n")
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
        [command, heads, preflight_json, preflight_md, preflight_sha256s, run_exit, stderr, stdout],
        relative_to=artifact,
    )

    return {
        "preflight_artifact_dir": artifact,
        "preflight_json": preflight_json,
        "preflight_md": preflight_md,
        "preflight_sha256s": preflight_sha256s,
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


def _preflight_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_review_preflight_static_review_authorized": True,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
        "analysis": {
            "preflight_only": True,
            "read_only": True,
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
        "preflight_checks": [
            {"name": f"check_{index}", "passed": True}
            for index in range(module.EXPECTED_SOURCE["preflight_check_count"])
        ],
        "artifact_manifest_requirements": [
            {"name": f"artifact_{index}", "status": "ready"}
            for index in range(module.EXPECTED_SOURCE["artifact_manifest_requirement_count"])
        ],
        "uncertainty_coverage_review_preflight": [
            {"name": f"preflight_{index}"}
            for index in range(module.EXPECTED_SOURCE["review_preflight_item_count"])
        ],
        "no_go_status": [
            {"name": f"no_go_{index}", "triggered": False}
            for index in range(module.EXPECTED_SOURCE["no_go_count"])
        ],
        "future_review_requirements": [
            {"name": f"review_{index}"}
            for index in range(module.EXPECTED_SOURCE["future_review_requirement_count"])
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

