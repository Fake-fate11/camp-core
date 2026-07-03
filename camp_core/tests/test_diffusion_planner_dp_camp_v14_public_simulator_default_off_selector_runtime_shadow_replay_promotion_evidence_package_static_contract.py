import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package_static_contract.py"
)
PREFLIGHT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package.py"
)
PREFLIGHT_TEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package_preflight.py"
)
CAMP_HEAD = "602e7bbee6119372009a88430af078aa3b1a3338"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_promotion_evidence_package_static_review",
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


def _preflight_payload(
    module,
    files: dict[str, Path],
    *,
    selector_promotion_authorized: bool = False,
    selection_score_worse_records: int = 0,
) -> dict:
    source_hashes = {name: module._sha256(path) for name, path in files.items()}
    blocked = {name: False for name in module.BLOCKED_ACTIONS}
    decision_blocked = dict(blocked)
    decision_blocked["selector_promotion_authorized"] = selector_promotion_authorized
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA_VERSION,
        "analysis": {
            "preflight_only": True,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_hashes": source_hashes,
        "artifact_manifest": [
            {
                "name": name,
                "path": str(path.resolve()),
                "sha256": source_hashes[name],
                "role": name,
            }
            for name, path in files.items()
        ],
        "source_summary": {
            "promotion_plan_status": "ready",
            "runtime_result_review_status": "passed",
            "shadow_vs_top1_delta_status": "passed",
            "runtime_manifest_schema_version": module.SOURCE_RUNTIME_MANIFEST_SCHEMA,
            "training_review_status": "passed",
            "selection_log_count": 1,
            "validation_summary_count": 1,
            "replay_summary_count": 1,
            "records": 3,
            "executed_top1_records": 3,
            "shadow_selected_index_nonzero_records": 2,
            "feasible_records": 3,
            "used_fallback_records": 0,
            "selection_score_better_records": 2 - selection_score_worse_records,
            "selection_score_tie_records": 1,
            "selection_score_worse_records": selection_score_worse_records,
            "selection_score_uncomparable_records": 0,
            "training_records": 3,
            "dropped_records_without_feasible_candidate": 0,
            "num_candidates": 8,
            "num_atoms": 9,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "static_integration_contract": {
            "default_off": True,
            "fail_closed": True,
            "executed_output_policy": "dp_top1",
            "score_expression": module.SCORE_EXPRESSION,
            "simplex_master_convex": True,
            "cvar_master_convex": True,
            "l2_master_convex": True,
        },
        "blocked_actions": blocked,
        "preflight_checks": [{"name": "all", "passed": True}],
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_PREFLIGHT_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "runtime_promotion_evidence_package_preflight_ready": True,
            "evidence_package_static_review_authorized": True,
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
    selection_score_worse_records: int = 0,
) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Runtime Promotion Evidence-Package Preflight",
                f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_promotion_evidence_package_preflight_ready=True",
                "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_authorized=True",
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
                f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
                f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK}",
                "",
            ]
        ),
    )
    files = _source_files(tmp_path, module)
    preflight_json = _write_json(
        tmp_path / "preflight" / "runtime_promotion_evidence_package_preflight.json",
        _preflight_payload(
            module,
            files,
            selector_promotion_authorized=selector_promotion_authorized,
            selection_score_worse_records=selection_score_worse_records,
        ),
    )
    preflight_md = _write(
        tmp_path / "preflight" / "runtime_promotion_evidence_package_preflight.md",
        "# V14 Runtime Promotion Evidence-Package Preflight\n\nread-only\n",
    )
    sha256sums = _write(
        tmp_path / "preflight" / "SHA256SUMS",
        "\n".join(
            [
                f"{module._sha256(preflight_json)}  {preflight_json.name}",
                f"{module._sha256(preflight_md)}  {preflight_md.name}",
                "",
            ]
        ),
    )
    return {
        "runtime_promotion_evidence_package_preflight_json": preflight_json,
        "runtime_promotion_evidence_package_preflight_md": preflight_md,
        "runtime_promotion_evidence_package_preflight_sha256s": sha256sums,
        "preflight_script_py": PREFLIGHT_SCRIPT_PATH,
        "preflight_test_py": PREFLIGHT_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "static_review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
        "expected_counts": {
            "selection_log_count": 1,
            "validation_summary_count": 1,
            "replay_summary_count": 1,
            "records": 3,
            "executed_top1_records": 3,
            "shadow_selected_index_nonzero_records": 2,
            "feasible_records": 3,
            "used_fallback_records": 0,
            "selection_score_better_records": 2,
            "selection_score_tie_records": 1,
            "selection_score_worse_records": 0,
            "selection_score_uncomparable_records": 0,
            "training_records": 3,
            "dropped_records_without_feasible_candidate": 0,
            "num_candidates": 8,
            "num_atoms": 9,
        },
        "source_files": files,
    }


def test_runtime_promotion_evidence_package_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs.pop("source_files")

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_construction_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_preflight_summary"]["records"] == 3
    assert len(report["artifact_manifest_review"]) == 9
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_static_review.json").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_static_review.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_promotion_evidence_package_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs.pop("source_files")
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_static_review_authorization_missing"
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_runtime_promotion_evidence_package_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)
    kwargs.pop("source_files")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_boundary_matches_static_review_gate" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_evidence_package_static_review_rejects_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)
    kwargs.pop("source_files")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "source_preflight_decision_selector_promotion_authorized"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "source_preflight_contract_failure"


def test_runtime_promotion_evidence_package_static_review_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    source_files = kwargs.pop("source_files")
    source_files["runtime_manifest"].write_text("drift\n", encoding="utf-8")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "artifact_runtime_manifest_hash_matches_file" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_hash_mismatch"
