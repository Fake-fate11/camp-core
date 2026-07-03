from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "record_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_no_promotion_closeout.py"
)
CAMP_HEAD = "7117f5b87b0f2dfe6c338ccf3afc233c8f09604a"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_no_promotion_closeout_record",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _source_plan_payload(
    module,
    *,
    selector_promotion_authorized: bool = False,
) -> dict:
    decision_blocked = {name: False for name in module.BLOCKED_ACTIONS}
    decision_blocked["selector_promotion_authorized"] = selector_promotion_authorized
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "planning_only": True,
            "promotion_executed": False,
            "deployment_executed": False,
        },
        "promotion_decision_plan": {
            "recommendation": "do_not_promote_from_current_evidence_package_alone",
            "immediate_action": "record_no_promotion_closeout_only",
            "required_evidence_before_any_future_promotion": [
                "explicit_human_authorization_for_actual_promotion_gate",
            ],
            "no_go_conditions": [
                "safety_or_camp_over_dp_top1_claim_from_static_evidence_only",
            ],
        },
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "promotion_decision_from_evidence_package_plan_ready": True,
            "recommendation": "do_not_promote_from_current_evidence_package_alone",
            "immediate_action": "record_no_promotion_closeout_only",
            "promotion_executed_by_this_gate": False,
            "deployment_executed_by_this_gate": False,
            "training_executed_by_this_gate": False,
            "replay_executed_by_this_gate": False,
            "candidate_generation_executed_by_this_gate": False,
            "dp_modified_by_this_gate": False,
            "score_expression": module.SCORE_EXPRESSION,
            **decision_blocked,
        },
    }


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_eof: bool = False,
    selector_promotion_authorized: bool = False,
    drift_plan_md: bool = False,
) -> dict:
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    docs = tmp_path / "docs"
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_promotion_decision_from_evidence_package_plan_ready=True",
                "default_off_shadow_selector_runtime_promotion_no_promotion_closeout_authorized=True",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    plan_json = _write_json(
        tmp_path / "plan" / "runtime_promotion_decision_from_evidence_package_plan.json",
        _source_plan_payload(
            module,
            selector_promotion_authorized=selector_promotion_authorized,
        ),
    )
    plan_md = _write(
        tmp_path / "plan" / "runtime_promotion_decision_from_evidence_package_plan.md",
        "# plan\n",
    )
    plan_sha256s = _write(
        tmp_path / "plan" / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(plan_json)}  {plan_json.name}",
                f"{module._sha256(plan_md)}  {plan_md.name}",
                "",
            ]
        ),
    )
    if drift_plan_md:
        plan_md.write_text("# drift\n", encoding="utf-8")
    return {
        "promotion_decision_plan_json": plan_json,
        "promotion_decision_plan_md": plan_md,
        "promotion_decision_plan_sha256s": plan_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "record",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_no_promotion_closeout_record_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["no_promotion_closeout_recorded"] is True
    assert decision["promotion_recommended"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["no_promotion_closeout_record"]["final_selector_state"] == "default_off_shadow_only_not_promoted"
    assert (kwargs["output_dir"] / "runtime_no_promotion_closeout_record.json").is_file()
    assert (kwargs["output_dir"] / "runtime_no_promotion_closeout_record.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_no_promotion_closeout_record_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "no_promotion_closeout_record_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_no_promotion_closeout_record_authorization_missing"
    )


def test_no_promotion_closeout_record_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_no_promotion_closeout_record_rejects_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "source_plan_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_no_promotion_closeout_record_rejects_source_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, drift_plan_md=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "plan_sha256s_md_hash" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_plan_sha256s_mismatch"
