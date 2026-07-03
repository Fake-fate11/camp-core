from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_evaluation.py"
)
ARTIFACT_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_evaluation_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promotion_readiness_evaluation_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evaluation_plan_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["decision_surfaces"]) == 3
    assert len(report["evidence_requirements"]) == 7
    assert len(report["no_go_conditions"]) == 7
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_plan.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_evaluation_plan.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_promotion_readiness_evaluation_plan_accepts_uppercase_source_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_preflight_dp_key="DP_HEAD")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert "source_preflight_heads_dp_fixed" not in report["final_decision"]["failed_checks"]


def test_promotion_readiness_evaluation_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "evaluation_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_evaluation_plan_authorization_missing"
    )


def test_promotion_readiness_evaluation_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_eof_authorizes_evaluation_plan" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_evaluation_plan" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_promotion_readiness_evaluation_plan_rejects_source_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_preflight_md"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_preflight_md_preflight_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_sha256_mismatch"


def test_promotion_readiness_evaluation_plan_rejects_source_static_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        static_review_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert (
        "source_static_review_decision_deployment_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["deployment_authorized"] is False


def test_promotion_readiness_evaluation_plan_rejects_source_preflight_failure(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_preflight_decision_updates={"passed": False, "failed_checks": ["preflight"]},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_preflight_passed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_preflight_contract_failure"


def test_promotion_readiness_evaluation_plan_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--preflight_static_review_artifact_dir",
            str(fixture["preflight_static_review_artifact_dir"]),
            "--preflight_static_review_json",
            str(fixture["preflight_static_review_json"]),
            "--preflight_static_review_md",
            str(fixture["preflight_static_review_md"]),
            "--preflight_static_review_sha256s",
            str(fixture["preflight_static_review_sha256s"]),
            "--source_preflight_artifact_dir",
            str(fixture["source_preflight_artifact_dir"]),
            "--source_preflight_json",
            str(fixture["source_preflight_json"]),
            "--source_preflight_md",
            str(fixture["source_preflight_md"]),
            "--source_preflight_sha256s",
            str(fixture["source_preflight_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_evaluation_plan",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "post_closeout_promotion_readiness_evaluation_plan.json").is_file()
    assert (output_dir / "post_closeout_promotion_readiness_evaluation_plan.md").is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    static_review_decision_updates: dict[str, Any] | None = None,
    source_preflight_decision_updates: dict[str, Any] | None = None,
    source_preflight_dp_key: str = "dp_head",
) -> dict[str, Any]:
    static_artifact = tmp_path / "static_review_artifact"
    review_dir = static_artifact / "review"
    preflight_artifact = tmp_path / "preflight_artifact"
    preflight_dir = preflight_artifact / "preflight"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_readiness_evaluation_preflight_static_review_passed=True",
            "post_closeout_promotion_readiness_evaluation_plan_authorized=True",
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
    preflight_md = _write(preflight_dir / module.PREFLIGHT_MD_NAME, "# Preflight\n")
    preflight_sha256s = _write_sha256sums(
        preflight_dir / "SHA256SUMS",
        [preflight_json, preflight_md],
    )
    preflight_command = _write(preflight_artifact / "COMMAND", "preflight command\n")
    preflight_heads = _write(
        preflight_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"{source_preflight_dp_key}={module.FIXED_DP_HEAD}",
                "source_preflight_plan_static_review_artifact=/tmp/preflight_plan_static_review",
                "source_preflight_plan_artifact=/tmp/preflight_plan",
                "",
            ]
        ),
    )
    preflight_stdout = _write(preflight_artifact / "stdout.txt", "ok\n")
    preflight_stderr = _write(preflight_artifact / "stderr.txt", "")
    preflight_run_exit = _write(preflight_artifact / "run.exit", "0\n")
    _write_sha256sums(
        preflight_artifact / "SHA256SUMS",
        [
            preflight_command,
            preflight_heads,
            preflight_json,
            preflight_md,
            preflight_sha256s,
            preflight_run_exit,
            preflight_stderr,
            preflight_stdout,
        ],
        relative_to=preflight_artifact,
    )

    static_review_json = _write_json(
        review_dir / module.STATIC_REVIEW_JSON_NAME,
        _static_review_payload(
            module,
            source_preflight_artifact=preflight_artifact,
            decision_updates=static_review_decision_updates,
        ),
    )
    static_review_md = _write(review_dir / module.STATIC_REVIEW_MD_NAME, "# Static Review\n")
    static_review_sha256s = _write_sha256sums(
        review_dir / "SHA256SUMS",
        [static_review_json, static_review_md],
    )
    static_command = _write(static_artifact / "COMMAND", "static review command\n")
    static_heads = _write(
        static_artifact / "HEADS",
        "\n".join(
            [
                f"camp_head={ARTIFACT_HEAD}",
                f"camp_origin_main={ARTIFACT_HEAD}",
                f"dp_head={module.FIXED_DP_HEAD}",
                f"source_preflight_artifact={preflight_artifact.resolve()}",
                "",
            ]
        ),
    )
    static_stdout = _write(static_artifact / "stdout.txt", "ok\n")
    static_stderr = _write(static_artifact / "stderr.txt", "")
    static_run_exit = _write(static_artifact / "run.exit", "0\n")
    _write_sha256sums(
        static_artifact / "SHA256SUMS",
        [
            static_command,
            static_heads,
            static_review_json,
            static_review_md,
            static_review_sha256s,
            static_run_exit,
            static_stderr,
            static_stdout,
        ],
        relative_to=static_artifact,
    )

    return {
        "preflight_static_review_artifact_dir": static_artifact,
        "preflight_static_review_json": static_review_json,
        "preflight_static_review_md": static_review_md,
        "preflight_static_review_sha256s": static_review_sha256s,
        "source_preflight_artifact_dir": preflight_artifact,
        "source_preflight_json": preflight_json,
        "source_preflight_md": preflight_md,
        "source_preflight_sha256s": preflight_sha256s,
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
    source_preflight_artifact: Path,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "promotion_readiness_evaluation_plan_authorized": True,
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
            "preflight_artifact_dir": str(source_preflight_artifact.resolve()),
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
        "review_checks": [{"name": "all", "passed": True}],
        "final_decision": decision,
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
        "authorized_next_work": module.SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK,
        "preflight_static_review_authorized": True,
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
            "preflight_plan_static_review_artifact_dir": "/tmp/preflight_plan_static_review",
            "source_preflight_plan_artifact_dir": "/tmp/preflight_plan",
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
        "preflight_checks": [{"name": "all", "passed": True}],
        "evaluation_preflight": [{"name": f"preflight_{index}"} for index in range(5)],
        "no_go_status": [{"name": f"no_go_{index}", "triggered": False} for index in range(7)],
        "future_review_requirements": [{"name": f"review_{index}"} for index in range(4)],
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
