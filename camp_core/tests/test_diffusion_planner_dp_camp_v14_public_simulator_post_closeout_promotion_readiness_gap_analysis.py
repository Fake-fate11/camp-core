from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis.py"
)
CAMP_HEAD = "c" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_gap_analysis",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_readiness_gap_analysis_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["recommendation"] == "do_not_promote_or_deploy_from_current_evidence_package"
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_summaries"]["evidence_manifest_json"]["entry_count"] == 15
    assert {gap["category"] for gap in report["evidence_gaps"]} == {
        "active_selector_promotion",
        "deployment_fail_closed",
        "safety_claim",
        "camp_over_dp_top1_claim",
        "evaluation_coverage",
        "governance_authorization",
    }
    assert (fixture["output_dir"] / "post_closeout_promotion_readiness_gap_analysis.json").is_file()
    assert (fixture["output_dir"] / "post_closeout_promotion_readiness_gap_analysis.md").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_readiness_gap_analysis_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "gap_analysis_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_post_closeout_gap_analysis_authorization_missing"
    )


def test_post_closeout_promotion_readiness_gap_analysis_rejects_eof_mismatch(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_next_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_closeout_promotion_readiness_gap_analysis_rejects_promotion_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        promotion_plan_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "boundary_contract_failure"
    assert (
        "promotion_decision_plan_json_decision_selector_promotion_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_post_closeout_promotion_readiness_gap_analysis_rejects_source_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["result_review_json"].write_text("{}", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "source_artifact_sha256_mismatch"
    assert "result_review_json_listed_in_result_review_sha256s" in report["final_decision"][
        "failed_checks"
    ]


def test_post_closeout_promotion_readiness_gap_analysis_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_package_artifact_dir",
            str(fixture["evidence_package_artifact_dir"]),
            "--result_review_artifact_dir",
            str(fixture["result_review_artifact_dir"]),
            "--delta_review_artifact_dir",
            str(fixture["delta_review_artifact_dir"]),
            "--promotion_plan_artifact_dir",
            str(fixture["promotion_plan_artifact_dir"]),
            "--closeout_review_artifact_dir",
            str(fixture["closeout_review_artifact_dir"]),
            "--evidence_manifest_json",
            str(fixture["evidence_manifest_json"]),
            "--evidence_construction_json",
            str(fixture["evidence_construction_json"]),
            "--result_review_json",
            str(fixture["result_review_json"]),
            "--shadow_vs_top1_delta_review_json",
            str(fixture["shadow_vs_top1_delta_review_json"]),
            "--promotion_decision_plan_json",
            str(fixture["promotion_decision_plan_json"]),
            "--no_promotion_closeout_review_json",
            str(fixture["no_promotion_closeout_review_json"]),
            "--evidence_package_sha256s",
            str(fixture["evidence_package_sha256s"]),
            "--evidence_construction_sha256s",
            str(fixture["evidence_construction_sha256s"]),
            "--result_review_sha256s",
            str(fixture["result_review_sha256s"]),
            "--shadow_vs_top1_delta_review_sha256s",
            str(fixture["shadow_vs_top1_delta_review_sha256s"]),
            "--promotion_decision_plan_sha256s",
            str(fixture["promotion_decision_plan_sha256s"]),
            "--no_promotion_closeout_review_sha256s",
            str(fixture["no_promotion_closeout_review_sha256s"]),
            "--v14_audit_md",
            str(fixture["v14_audit_md"]),
            "--current_status_md",
            str(fixture["current_status_md"]),
            "--output_dir",
            str(output_dir),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            module.FIXED_DP_HEAD,
            "--enable_v14_post_closeout_promotion_readiness_gap_analysis",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "post_closeout_promotion_readiness_gap_analysis.json").is_file()
    assert (output_dir / "post_closeout_promotion_readiness_gap_analysis.md").is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    promotion_plan_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    next_target = next_work or module.SOURCE_CLOSED_NEXT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.CLOSEOUT_REVIEW_STATUS}",
            "default_off_shadow_selector_runtime_no_promotion_closeout_complete=True",
            "future_promotion_requires_new_eof_and_explicit_authorization=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    evidence_package_dir = _artifact_dir(tmp_path, module, "evidence_package")
    result_review_dir = _artifact_dir(tmp_path, module, "result_review")
    delta_review_dir = _artifact_dir(tmp_path, module, "delta_review")
    promotion_plan_dir = _artifact_dir(tmp_path, module, "promotion_plan")
    closeout_review_dir = _artifact_dir(tmp_path, module, "closeout_review")

    evidence_manifest = _write_json(
        evidence_package_dir / "construction" / "evidence_package" / "evidence_manifest.json",
        _evidence_manifest(tmp_path, module),
    )
    evidence_construction = _write_json(
        evidence_package_dir / "construction" / "runtime_promotion_evidence_package_construction.json",
        _source_payload(
            module,
            schema=module.EVIDENCE_PACKAGE_SCHEMA,
            status=module.EVIDENCE_CONSTRUCTION_STATUS,
            authorized_next_work="construction_static_review_only",
            analysis={"construction_only": True},
        ),
    )
    result_review = _write_json(
        result_review_dir / "review" / "result_review_report.json",
        _source_payload(
            module,
            schema=module.RESULT_REVIEW_SCHEMA,
            status=module.RESULT_REVIEW_STATUS,
            authorized_next_work="promotion_decision_plan_only",
            blocked=False,
        ),
    )
    delta_review = _write_json(
        delta_review_dir / "review" / "shadow_vs_top1_delta_review_report.json",
        _source_payload(
            module,
            schema=module.DELTA_REVIEW_SCHEMA,
            status=module.DELTA_REVIEW_STATUS,
            authorized_next_work="promotion_decision_plan_only",
            blocked=False,
        ),
    )
    promotion_plan = _write_json(
        promotion_plan_dir / "plan" / "runtime_promotion_decision_from_evidence_package_plan.json",
        _source_payload(
            module,
            schema=module.PROMOTION_PLAN_SCHEMA,
            status=module.PROMOTION_PLAN_STATUS,
            authorized_next_work="no_promotion_closeout_only",
            decision_updates={
                "recommendation": "do_not_promote_from_current_evidence_package_alone",
                "immediate_action": "record_no_promotion_closeout_only",
                "promotion_decision_from_evidence_package_plan_ready": True,
                **(promotion_plan_decision_updates or {}),
            },
            analysis={"planning_only": True},
        ),
    )
    closeout_review = _write_json(
        closeout_review_dir / "review" / "runtime_no_promotion_closeout_review.json",
        _source_payload(
            module,
            schema=module.CLOSEOUT_REVIEW_SCHEMA,
            status=module.CLOSEOUT_REVIEW_STATUS,
            authorized_next_work=module.SOURCE_CLOSED_NEXT_WORK,
            decision_updates={
                "recommendation": "keep_default_off_no_promotion_from_current_evidence_package",
                "no_promotion_closeout_complete": True,
                "future_promotion_requires_new_eof_and_explicit_authorization": True,
            },
            analysis={"review_only": True},
        ),
    )

    evidence_package_sha256s = _write_sha256sums(
        evidence_package_dir / "construction" / "evidence_package",
        [evidence_manifest],
    )
    evidence_construction_sha256s = _write_sha256sums(
        evidence_package_dir / "construction",
        [evidence_construction],
    )
    result_review_sha256s = _write_sha256sums(result_review_dir / "review", [result_review])
    delta_review_sha256s = _write_sha256sums(delta_review_dir / "review", [delta_review])
    promotion_plan_sha256s = _write_sha256sums(promotion_plan_dir / "plan", [promotion_plan])
    closeout_review_sha256s = _write_sha256sums(closeout_review_dir / "review", [closeout_review])

    return {
        "evidence_package_artifact_dir": evidence_package_dir,
        "result_review_artifact_dir": result_review_dir,
        "delta_review_artifact_dir": delta_review_dir,
        "promotion_plan_artifact_dir": promotion_plan_dir,
        "closeout_review_artifact_dir": closeout_review_dir,
        "evidence_manifest_json": evidence_manifest,
        "evidence_construction_json": evidence_construction,
        "result_review_json": result_review,
        "shadow_vs_top1_delta_review_json": delta_review,
        "promotion_decision_plan_json": promotion_plan,
        "no_promotion_closeout_review_json": closeout_review,
        "evidence_package_sha256s": evidence_package_sha256s,
        "evidence_construction_sha256s": evidence_construction_sha256s,
        "result_review_sha256s": result_review_sha256s,
        "shadow_vs_top1_delta_review_sha256s": delta_review_sha256s,
        "promotion_decision_plan_sha256s": promotion_plan_sha256s,
        "no_promotion_closeout_review_sha256s": closeout_review_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _artifact_dir(tmp_path: Path, module, name: str) -> Path:
    root = tmp_path / "artifacts" / name
    layout = module.ARTIFACT_LAYOUTS[name]
    files: list[Path] = []
    for role, rel in layout.items():
        path = root / rel
        if role == "exit":
            _write(path, "0\n")
        elif role == "heads":
            _write(
                path,
                "\n".join(
                    [
                        f"camp_head={CAMP_HEAD}",
                        f"camp_origin_main={CAMP_HEAD}",
                        f"dp_head={module.FIXED_DP_HEAD}",
                    ]
                )
                + "\n",
            )
        else:
            _write(path, f"{name} {role}\n")
        files.append(path)
    _write_sha256sums(root, files, relative_to=root)
    return root


def _evidence_manifest(tmp_path: Path, module) -> dict[str, Any]:
    entries = []
    for name in module.EXPECTED_ENTRY_NAMES:
        package = tmp_path / "package_entries" / name / f"{name}.txt"
        _write(package, f"{name}\n")
        entries.append(
            {
                "name": name,
                "package_path": str(package.resolve()),
                "package_sha256": module._sha256(package),
                "package_exists": True,
                "hash_matches": True,
            }
        )
    return {
        "schema_version": module.EVIDENCE_PACKAGE_SCHEMA,
        "score_expression": module.SCORE_EXPRESSION,
        "source_static_review_passed": True,
        "entries": entries,
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
    }


def _source_payload(
    module,
    *,
    schema: str,
    status: str,
    authorized_next_work: str,
    blocked: bool = True,
    decision_updates: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_next_work": authorized_next_work,
        "score_expression": module.SCORE_EXPRESSION,
        **{name: False for name in module.BLOCKED_ACTIONS},
        **{name: False for name in module.EXECUTION_FLAGS},
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": schema,
        "analysis": {
            "score_expression": module.SCORE_EXPRESSION,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            **(analysis or {}),
        },
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS}
        if blocked
        else {},
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256sums(
    directory: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    rows = []
    for path in files:
        rel = path.name if relative_to is None else "./" + path.relative_to(relative_to).as_posix()
        rows.append(f"{_sha256(path)}  {rel}")
    return _write(directory / "SHA256SUMS", "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
