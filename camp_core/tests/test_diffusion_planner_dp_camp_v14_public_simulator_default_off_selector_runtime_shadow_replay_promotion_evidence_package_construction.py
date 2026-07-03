import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "construct_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package.py"
)
CAMP_HEAD = "602e7bbee6119372009a88430af078aa3b1a3338"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_promotion_evidence_package_construction",
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


def _source_files(tmp_path: Path, module) -> dict[str, Path]:
    root = tmp_path / "source_artifacts"
    files = {
        "runtime_promotion_decision_plan": root / "runtime_promotion_decision_plan.json",
        "runtime_result_review": root / "runtime_result_review.json",
        "shadow_vs_top1_delta_review": root / "shadow_vs_top1_delta_review.json",
        "runtime_manifest": root / "runtime_manifest.json",
        "training_artifact_static_review": root / "training_artifact_static_review.json",
        "training_summary": root / "training_summary.json",
        "offline_weights_npy": root / "offline_weights_dp_static.npy",
        "atom_scales_json": root / "atom_scales_dp_static.json",
        "runtime_shadow_execution_sha256s": root / "runtime_shadow_execution_SHA256SUMS",
    }
    for name, path in files.items():
        if path.suffix == ".json":
            _write_json(path, {"name": name, "score_expression": module.SCORE_EXPRESSION})
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{name}\n".encode("utf-8"))
    return files


def _static_review_payload(
    module,
    files: dict[str, Path],
    preflight_json: Path,
    preflight_md: Path,
    preflight_sha256s: Path,
    *,
    source_passed: bool = True,
    selector_promotion_authorized: bool = False,
) -> dict:
    blocked = {name: False for name in module.BLOCKED_ACTIONS}
    decision_blocked = dict(blocked)
    decision_blocked["selector_promotion_authorized"] = selector_promotion_authorized
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "runtime_promotion_evidence_package_preflight_json": str(preflight_json.resolve()),
            "runtime_promotion_evidence_package_preflight_md": str(preflight_md.resolve()),
            "runtime_promotion_evidence_package_preflight_sha256s": str(preflight_sha256s.resolve()),
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "artifact_manifest_review": [
            {
                "name": name,
                "path": str(path.resolve()),
                "exists": True,
                "sha256": module._sha256(path),
                "observed_sha256": module._sha256(path),
                "hash_matches": True,
            }
            for name, path in files.items()
        ],
        "blocked_actions": blocked,
        "review_checks": [{"name": "all", "passed": True}],
        "final_decision": {
            "passed": source_passed,
            "status": (
                module.SOURCE_STATIC_REVIEW_STATUS
                if source_passed
                else "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected"
            ),
            "failed_checks": [] if source_passed else ["source_failure"],
            "authorized_next_work": (
                module.SOURCE_AUTHORIZED_NEXT_WORK if source_passed else None
            ),
            "evidence_package_construction_authorized": source_passed,
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
    source_passed: bool = True,
    selector_promotion_authorized: bool = False,
) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Runtime Promotion Evidence-Package Static Review Authorized Rerun",
                f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_passed=True",
                "default_off_shadow_selector_runtime_promotion_evidence_package_construction_authorized=True",
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
                f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
                f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK if not wrong_eof else 'wrong_gate'}",
                "",
            ]
        ),
    )
    files = _source_files(tmp_path, module)
    preflight_json = _write_json(
        tmp_path / "preflight" / "runtime_promotion_evidence_package_preflight.json",
        {"passed": True, "score_expression": module.SCORE_EXPRESSION},
    )
    preflight_md = _write(
        tmp_path / "preflight" / "runtime_promotion_evidence_package_preflight.md",
        "# V14 Runtime Promotion Evidence-Package Preflight\n\nread-only\n",
    )
    preflight_sha256s = _write(
        tmp_path / "preflight" / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(preflight_json)}  {preflight_json.name}",
                f"{module._sha256(preflight_md)}  {preflight_md.name}",
                "",
            ]
        ),
    )
    static_review_json = _write_json(
        tmp_path / "static_review" / "runtime_promotion_evidence_package_static_review.json",
        _static_review_payload(
            module,
            files,
            preflight_json,
            preflight_md,
            preflight_sha256s,
            source_passed=source_passed,
            selector_promotion_authorized=selector_promotion_authorized,
        ),
    )
    static_review_md = _write(
        tmp_path / "static_review" / "runtime_promotion_evidence_package_static_review.md",
        "# V14 Runtime Promotion Evidence-Package Static Review\n\nread-only\n",
    )
    static_review_sha256s = _write(
        tmp_path / "static_review" / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(static_review_json)}  {static_review_json.name}",
                f"{module._sha256(static_review_md)}  {static_review_md.name}",
                "",
            ]
        ),
    )
    return {
        "runtime_promotion_evidence_package_static_review_json": static_review_json,
        "runtime_promotion_evidence_package_static_review_md": static_review_md,
        "runtime_promotion_evidence_package_static_review_sha256s": static_review_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "construction",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_promotion_evidence_package_construction_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["constructed_package_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["package_manifest"]) == 15
    assert (kwargs["output_dir"] / "evidence_package" / "evidence_manifest.json").is_file()
    assert (kwargs["output_dir"] / "evidence_package" / "README.md").is_file()
    assert (kwargs["output_dir"] / "evidence_package" / "SHA256SUMS").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_construction.json").is_file()
    assert all(entry["hash_matches"] for entry in report["package_manifest"])


def test_runtime_promotion_evidence_package_construction_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "construction_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_construction_authorization_missing"
    assert report["package_manifest"] == []


def test_runtime_promotion_evidence_package_construction_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "audit_latest_boundary_matches_construction_gate"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_evidence_package_construction_rejects_failed_static_review(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, source_passed=False)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_passed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_static_review_contract_failure"


def test_runtime_promotion_evidence_package_construction_rejects_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False
