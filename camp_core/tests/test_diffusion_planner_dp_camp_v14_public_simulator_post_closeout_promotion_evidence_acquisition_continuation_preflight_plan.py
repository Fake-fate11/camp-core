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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_continuation_preflight.py"
)
ARTIFACT_HEAD = "a" * 40
CURRENT_HEAD = "2" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_continuation_preflight_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_passes(
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
    assert decision["post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_ready"] is True
    assert decision["post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_review_authorized"] is True
    assert decision["post_closeout_promotion_evidence_acquisition_chain_opened_for_planning_only"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["item_name"] for item in report["paired_evaluation_protocol"]] == list(
        module.EXPECTED_PROTOCOL_ITEMS
    )
    assert [item["name"] for item in report["metrics_plan"]] == list(module.EXPECTED_METRICS)
    assert (
        report["pass_fail_criteria"]["primary_claim_rule"]
        == "hard_gate_passed == true and ci95_high(DeltaSafetyCost_v1) < 0"
    )
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "preflight_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_post_closeout_promotion_evidence_acquisition_authorization_missing"
    )


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_is_no_further_action_boundary" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_is_no_further_action_boundary" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        closeout_summary_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "closeout_camp_over_dp" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_review_md_root_sha" in report["final_decision"]["failed_checks"]
    assert "source_review_md_review_sha" in report["final_decision"]["failed_checks"]


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_rejects_safety_score_doc_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["safety_score_doc"].write_text("# Different contract\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "safety_score_doc_contains_0" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    closeout_summary_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "source_static_review_artifact"
    review_dir = artifact / "review"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "promotion_readiness_evidence_chain_closed=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    safety_score_doc = _write(
        docs / "dp_camp_safety_score_v1.md",
        "\n".join(
            [
                "SafetyCost_v1",
                "ci95_high(DeltaSafetyCost_v1) < 0",
                "Formal seeds",
                "no paired run uses seeds `11`, `12`, or `13`",
                "must not be fed to an online selector",
                "",
            ]
        ),
    )
    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_review_payload(module, closeout_summary_updates=closeout_summary_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# Static Review\n")
    review_sha256s = _write_sha256sums(review_dir / "SHA256SUMS", [review_json, review_md])
    command = _write(artifact / "COMMAND", "static review command\n")
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
        [command, heads, stdout, stderr, run_exit, review_json, review_md, review_sha256s],
        relative_to=artifact,
    )
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": review_json,
        "source_static_review_md": review_md,
        "source_static_review_sha256s": review_sha256s,
        "safety_score_doc": safety_score_doc,
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
    closeout_summary_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "promotion_readiness_evidence_chain_no_promotion_closeout_record_static_review_passed": True,
        "promotion_readiness_evidence_chain_closed": True,
        "evidence_chain_closed_by_this_gate": False,
        "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
        "direct_promotion_recommendation": False,
        "recommendation": "stop_without_new_eof_authorization",
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    analysis = {
        "current_camp_head": ARTIFACT_HEAD,
        "current_camp_origin_main": ARTIFACT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for flag in module.ANALYSIS_FALSE_FLAGS:
        analysis[flag] = False
    closeout_summary = {
        "record_decision": "close_promotion_readiness_evidence_chain_without_promotion",
        "final_evidence_chain_state": "audit_evidence_chain_closed_no_promotion_no_deployment_no_claim",
        "promotion_recommended": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    if closeout_summary_updates:
        closeout_summary.update(closeout_summary_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": analysis,
        "source_record_summary": {
            "record_check_count": module.EXPECTED_SOURCE_RECORD_CHECK_COUNT,
            "failed_check_count": 0,
        },
        "closeout_record_summary": closeout_summary,
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_SOURCE_REVIEW_CHECK_COUNT)
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
