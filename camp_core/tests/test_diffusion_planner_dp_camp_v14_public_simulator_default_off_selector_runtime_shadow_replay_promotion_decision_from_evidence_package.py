from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_from_evidence_package.py"
)
CAMP_HEAD = "6ad6d3966f8071d66a61b80421333dd97f5046e7"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_promotion_decision_from_evidence_package",
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


def _entries(tmp_path: Path, module, *, drift_name: str | None = None) -> list[dict]:
    entries = []
    for name in module.EXPECTED_ENTRY_NAMES:
        package = tmp_path / "evidence_package" / "evidence" / name / f"{name}.txt"
        _write(package, f"package {name}\n")
        sha = module._sha256(package)
        entry = {
            "name": name,
            "package_path": str(package.resolve()),
            "package_sha256": sha,
            "package_exists": True,
            "hash_matches": True,
        }
        entries.append(entry)
    if drift_name:
        drift = next(entry for entry in entries if entry["name"] == drift_name)
        Path(drift["package_path"]).write_text("drift\n", encoding="utf-8")
    return entries


def _static_review_payload(module, *, selector_promotion_authorized: bool = False) -> dict:
    decision_blocked = {name: False for name in module.BLOCKED_ACTIONS}
    decision_blocked["selector_promotion_authorized"] = selector_promotion_authorized
    return {
        "schema_version": module.STATIC_REVIEW_SCHEMA,
        "analysis": {
            "construction_static_review_only": True,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
        },
        "evidence_package_summary": {
            "entry_count": module.EXPECTED_PACKAGE_ENTRY_COUNT,
            "score_expression": module.SCORE_EXPRESSION,
            "source_static_review_passed": True,
        },
        "final_decision": {
            "status": module.SOURCE_STATIC_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "promotion_decision_planning_authorized": True,
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
    drift_name: str | None = None,
) -> dict:
    next_work = "wrong_gate" if wrong_eof else module.AUTHORIZED_CURRENT_WORK
    docs = tmp_path / "docs"
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_passed=True",
                "default_off_shadow_selector_runtime_promotion_decision_plan_from_evidence_package_authorized=True",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    entries = _entries(tmp_path, module, drift_name=drift_name)
    package_dir = tmp_path / "evidence_package"
    evidence_manifest = _write_json(
        package_dir / "evidence_manifest.json",
        {
            "schema_version": module.EVIDENCE_PACKAGE_SCHEMA,
            "score_expression": module.SCORE_EXPRESSION,
            "source_static_review_passed": True,
            "entries": entries,
            "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        },
    )
    package_sha256s = _write(
        package_dir / "SHA256SUMS",
        f"{module._sha256(evidence_manifest)}  {evidence_manifest.name}\n",
    )
    static_review_json = _write_json(
        tmp_path / "review" / "runtime_promotion_evidence_package_construction_static_review.json",
        _static_review_payload(
            module,
            selector_promotion_authorized=selector_promotion_authorized,
        ),
    )
    static_review_sha256s = _write(
        tmp_path / "review" / "SHA256SUMS",
        f"{module._sha256(static_review_json)}  {static_review_json.name}\n",
    )
    return {
        "construction_static_review_json": static_review_json,
        "construction_static_review_sha256s": static_review_sha256s,
        "evidence_manifest_json": evidence_manifest,
        "evidence_package_sha256s": package_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_promotion_decision_from_evidence_package_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["recommendation"] == "do_not_promote_from_current_evidence_package_alone"
    assert decision["immediate_action"] == "record_no_promotion_closeout_only"
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["evidence_package_summary"]["entry_count"] == 15
    assert (kwargs["output_dir"] / "runtime_promotion_decision_from_evidence_package_plan.json").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_decision_from_evidence_package_plan.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_promotion_decision_from_evidence_package_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "planning_from_evidence_package_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_evidence_package_decision_planning_authorization_missing"
    )


def test_runtime_promotion_decision_from_evidence_package_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_decision_from_evidence_package_rejects_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "source_static_review_decision_selector_promotion_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_runtime_promotion_decision_from_evidence_package_rejects_package_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, drift_name="runtime_manifest")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "evidence_entry_runtime_manifest_package_sha_matches_manifest"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "evidence_package_contract_failure"
