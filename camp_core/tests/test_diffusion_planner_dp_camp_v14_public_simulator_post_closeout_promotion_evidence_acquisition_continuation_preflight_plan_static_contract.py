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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_continuation_preflight.py"
)
PLAN_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_continuation_preflight_plan.py"
)
ARTIFACT_HEAD = "b" * 40
CURRENT_HEAD = "3" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_passes(
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
    assert decision["post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_review_passed"] is True
    assert decision["post_closeout_promotion_evidence_acquisition_paired_evaluation_preflight_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["protocol_summary"]["protocol_item_count"] == module.EXPECTED_PROTOCOL_ITEM_COUNT
    assert report["protocol_summary"]["metrics_count"] == module.EXPECTED_METRICS_COUNT
    assert report["protocol_summary"]["no_go_count"] == module.EXPECTED_NO_GO_COUNT
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_requires_enable(
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
        == "explicit_promotion_evidence_acquisition_preflight_plan_static_review_authorization_missing"
    )


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_plan_decision_camp_over_dp_top1_claim_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["preflight_plan_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_plan_md_root_sha" in report["final_decision"]["failed_checks"]
    assert "source_plan_md_plan_sha" in report["final_decision"]["failed_checks"]


def test_post_closeout_promotion_evidence_acquisition_preflight_plan_static_review_rejects_safety_score_doc_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["safety_score_doc"].write_text("# Different contract\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "safety_score_doc_claim_rule" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "preflight_plan_artifact"
    plan_dir = artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_ready=True",
            "post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_review_authorized=True",
            "post_closeout_promotion_evidence_acquisition_chain_opened_for_planning_only=True",
            "previous_no_promotion_closeout_preserved=True",
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
    plan_json = _write_json(
        plan_dir / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_payload(module, source_decision_updates=source_decision_updates),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# Plan\n")
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    command = _write(artifact / "COMMAND", "preflight plan command\n")
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
        [command, heads, stdout, stderr, run_exit, plan_json, plan_md, plan_sha256s],
        relative_to=artifact,
    )
    return {
        "preflight_plan_artifact_dir": artifact,
        "preflight_plan_json": plan_json,
        "preflight_plan_md": plan_md,
        "preflight_plan_sha256s": plan_sha256s,
        "plan_script_py": PLAN_SCRIPT_PATH,
        "plan_test_py": PLAN_TEST_PATH,
        "safety_score_doc": safety_score_doc,
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
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_ready": True,
        "post_closeout_promotion_evidence_acquisition_continuation_preflight_plan_static_review_authorized": True,
        "post_closeout_promotion_evidence_acquisition_chain_opened_for_planning_only": True,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_promotion_evidence_acquisition_continuation_preflight_plan_only",
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if source_decision_updates:
        decision.update(source_decision_updates)
    analysis = {
        "current_camp_head": ARTIFACT_HEAD,
        "current_camp_origin_main": ARTIFACT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for flag in module.ANALYSIS_FALSE_FLAGS:
        analysis[flag] = False
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": analysis,
        "closeout_record_summary": {
            "record_decision": "close_promotion_readiness_evidence_chain_without_promotion",
            "final_evidence_chain_state": "audit_evidence_chain_closed_no_promotion_no_deployment_no_claim",
            "promotion_recommended": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "paired_evaluation_protocol": [
            {"item_name": name, "requirement": "fixture"}
            for name in module.PLAN_MODULE.EXPECTED_PROTOCOL_ITEMS
        ],
        "metrics_plan": [
            {"name": name, "claim_scope": "fixture"}
            for name in module.PLAN_MODULE.EXPECTED_METRICS
        ],
        "no_go_register": [
            {"name": name, "status": "predeclared_reject_condition"}
            for name in module.PLAN_MODULE.EXPECTED_NO_GO
        ],
        "pass_fail_criteria": {
            "primary_claim_rule": "hard_gate_passed == true and ci95_high(DeltaSafetyCost_v1) < 0",
            "claim_authorized_by_this_gate": False,
            "reject_on_formal_seed_11_12_13": True,
            "reject_on_closed_loop_outcome_training_or_online_input": True,
        },
        "artifact_contract": {
            "required_root_files": ["HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", "SHA256SUMS"],
            "required_head_fields": ["CAMP_HEAD", "CAMP_ORIGIN_MAIN", "DP_HEAD"],
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "preflight_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_PLAN_CHECK_COUNT)
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
