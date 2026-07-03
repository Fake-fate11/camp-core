from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_contract.py"
)
CONSTRUCTION_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "construct_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package.py"
)
CONSTRUCTION_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package_construction.py"
)
CAMP_HEAD = "602e7bbee6119372009a88430af078aa3b1a3338"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_promotion_evidence_package_construction_static_review",
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


def _entry_names(module) -> list[str]:
    return sorted(
        module.EXPECTED_SOURCE_ARTIFACT_NAMES
        + module.EXPECTED_STATIC_REVIEW_NAMES
        + module.EXPECTED_PREFLIGHT_NAMES
    )


def _package_entries(tmp_path: Path, module, *, drift_package_name: str | None = None) -> list[dict]:
    entries = []
    for name in _entry_names(module):
        source = tmp_path / "sources" / name / f"{name}.txt"
        package = tmp_path / "construction" / "evidence_package" / "evidence" / name / f"{name}.txt"
        _write(source, f"source {name}\n")
        _write(package, f"source {name}\n")
        source_sha = module._sha256(source)
        package_sha = module._sha256(package)
        entry = {
            "name": name,
            "role": "source_artifact",
            "source_path": str(source.resolve()),
            "package_path": str(package.resolve()),
            "source_sha256": source_sha,
            "package_sha256": package_sha,
            "source_exists": True,
            "package_exists": True,
            "hash_matches": True,
        }
        entries.append(entry)
    if drift_package_name:
        drift = next(entry for entry in entries if entry["name"] == drift_package_name)
        Path(drift["package_path"]).write_text("drift\n", encoding="utf-8")
    return entries


def _construction_payload(
    module,
    entries: list[dict],
    *,
    selector_promotion_authorized: bool = False,
    source_passed: bool = True,
) -> dict:
    blocked = {name: False for name in module.BLOCKED_ACTIONS}
    decision_blocked = dict(blocked)
    decision_blocked["selector_promotion_authorized"] = selector_promotion_authorized
    return {
        "schema_version": module.SOURCE_CONSTRUCTION_SCHEMA,
        "analysis": {
            "construction_only": True,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "package_manifest": entries,
        "blocked_actions": blocked,
        "construction_checks": [{"name": "all", "passed": True}],
        "final_decision": {
            "passed": source_passed,
            "status": (
                module.SOURCE_CONSTRUCTION_STATUS
                if source_passed
                else "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_rejected"
            ),
            "failed_checks": [] if source_passed else ["source_failure"],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK if source_passed else None,
            "constructed_package_static_review_authorized": source_passed,
            "score_expression": module.SCORE_EXPRESSION,
            "training_executed_by_this_gate": False,
            "replay_executed_by_this_gate": False,
            "candidate_generation_executed_by_this_gate": False,
            "dp_modified_by_this_gate": False,
            "promotion_executed_by_this_gate": False,
            "deployment_executed_by_this_gate": False,
            **decision_blocked,
        },
    }


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_eof: bool = False,
    selector_promotion_authorized: bool = False,
    source_passed: bool = True,
    drift_package_name: str | None = None,
) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Runtime Promotion Evidence-Package Construction",
                f"current_v14_status={module.SOURCE_CONSTRUCTION_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_promotion_evidence_package_constructed=True",
                "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_authorized=True",
                "default_off_shadow_selector_runtime_execution_authorized=False",
                "dp_modification_authorized_by_current_boundary=False",
                "selector_promotion_authorized=False",
                "deployment_authorized=False",
                "safety_benefit_claim_authorized=False",
                "camp_over_dp_top1_claim_authorized=False",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_CONSTRUCTION_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    entries = _package_entries(tmp_path, module, drift_package_name=drift_package_name)
    package_dir = tmp_path / "construction" / "evidence_package"
    evidence_manifest = _write_json(
        package_dir / "evidence_manifest.json",
        {
            "schema_version": module.SOURCE_CONSTRUCTION_SCHEMA,
            "score_expression": module.SCORE_EXPRESSION,
            "source_static_review_status": "passed",
            "source_static_review_passed": True,
            "entries": entries,
            "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        },
    )
    evidence_readme = _write(
        package_dir / "README.md",
        "# V14 Runtime Promotion Evidence Package\n\nread-only\n",
    )
    package_sha256s = _write(
        package_dir / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(evidence_manifest)}  {evidence_manifest.name}",
                f"{module._sha256(evidence_readme)}  {evidence_readme.name}",
                "",
            ]
        ),
    )
    construction_json = _write_json(
        tmp_path / "construction" / "runtime_promotion_evidence_package_construction.json",
        _construction_payload(
            module,
            entries,
            selector_promotion_authorized=selector_promotion_authorized,
            source_passed=source_passed,
        ),
    )
    construction_md = _write(
        tmp_path / "construction" / "runtime_promotion_evidence_package_construction.md",
        "# V14 Runtime Promotion Evidence-Package Construction\n\nread-only\n",
    )
    construction_sha256s = _write(
        tmp_path / "construction" / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(construction_json)}  {construction_json.name}",
                f"{module._sha256(construction_md)}  {construction_md.name}",
                f"{module._sha256(evidence_manifest)}  evidence_package/{evidence_manifest.name}",
                f"{module._sha256(evidence_readme)}  evidence_package/{evidence_readme.name}",
                "",
            ]
        ),
    )
    return {
        "runtime_promotion_evidence_package_construction_json": construction_json,
        "runtime_promotion_evidence_package_construction_md": construction_md,
        "runtime_promotion_evidence_package_construction_sha256s": construction_sha256s,
        "evidence_manifest_json": evidence_manifest,
        "evidence_package_readme_md": evidence_readme,
        "evidence_package_sha256s": package_sha256s,
        "construction_script_py": CONSTRUCTION_SCRIPT_PATH,
        "construction_test_py": CONSTRUCTION_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "static_review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_promotion_evidence_package_construction_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["promotion_decision_planning_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["evidence_package_summary"]["entry_count"] == 15
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_construction_static_review.json").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_construction_static_review.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_promotion_evidence_package_construction_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "construction_static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_construction_static_review_authorization_missing"
    )


def test_runtime_promotion_evidence_package_construction_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "audit_latest_boundary_matches_construction_static_review_gate"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_evidence_package_construction_static_review_rejects_source_failure(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, source_passed=False)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "source_construction_passed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_construction_contract_failure"


def test_runtime_promotion_evidence_package_construction_static_review_rejects_package_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, drift_package_name="runtime_manifest")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "evidence_entry_runtime_manifest_package_sha_matches_manifest"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "evidence_package_contract_failure"


def test_runtime_promotion_evidence_package_construction_static_review_rejects_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "source_construction_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False
