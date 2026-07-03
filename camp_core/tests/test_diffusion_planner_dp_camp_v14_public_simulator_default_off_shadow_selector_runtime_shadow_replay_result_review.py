import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result.py"
)
CURRENT_CAMP_HEAD = "9e86ec1fb2bb9f22df578712b8003414694131f1"
EXECUTION_CAMP_HEAD = "dbd5b539a0117c47ea0809e923940619ec41214a"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_runtime_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload) -> Path:
    return _write(path, json.dumps(payload))


def _source_audit(module, *, executed_top1_records: int = 3200) -> dict:
    violation_counts = {
        "affine_score": 0,
        "atom_schema": 0,
        "closed_loop_outcomes": 0,
        "default_off_contract": 0,
        "executed_top1": 0 if executed_top1_records == 3200 else 1,
        "guidance": 0,
        "postselection": 0,
        "reference_blend": 0,
        "selected_executed_mismatch": 0,
        "selection_score_mask": 0,
        "shape": 0,
    }
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_audit_v1",
        "final_decision": {
            "passed": True,
            "status": module.EXECUTION_AUDIT_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "replay_execution_performed_by_this_audit": False,
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "heads": {
            "execution_camp_head": EXECUTION_CAMP_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
        },
        "execution": {
            "runbook_exit": "0",
            "selection_log_count": 32,
            "validation_summary_count": 32,
            "replay_summary_count": 32,
            "formal_seed_path_count": 0,
            "stderr_lines": 0,
        },
        "records": {
            "record_count": 3200,
            "log_record_counts_min": 100,
            "log_record_counts_max": 100,
            "default_off_selector_records": 3200,
            "artifact_contract_ready_records": 3200,
            "executed_top1_records": executed_top1_records,
            "selected_index_matches_executed_index_records": 3200,
            "shadow_selected_index_nonzero_records": 2832,
            "shadow_selected_index_differs_from_executed_index_records": 2832,
            "feasible_records": 2914,
            "used_fallback_records": 286,
            "masked_selection_score_inf_count": 2517,
            "max_affine_score_error": 4.0e-16,
            "violation_counts": violation_counts,
        },
        "source_hashes": {
            "execution_stdout": "0" * 64,
            "execution_stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False, executed_top1_records: int = 3200) -> dict:
    artifact = tmp_path / "execution_artifact"
    output = tmp_path / "execution_output"
    artifact.mkdir()
    output.mkdir()
    _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={EXECUTION_CAMP_HEAD}",
                f"CAMP_ORIGIN_MAIN={EXECUTION_CAMP_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(artifact / "audit.exit", "0\n")
    _write(artifact / "SHA256SUMS", "0" * 64 + "  logs/stdout.log\n")
    audit_json = _write_json(
        artifact / "report" / "runtime_shadow_replay_execution_audit.json",
        _source_audit(module, executed_top1_records=executed_top1_records),
    )
    audit_md = _write(
        artifact / "report" / "runtime_shadow_replay_execution_audit.md",
        "# execution audit\n",
    )
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.AUTHORIZED_CURRENT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={next_work}",
                f"{module.EXECUTION_CAMP_HEAD_AUDIT_KEY}={EXECUTION_CAMP_HEAD}",
                f"{module.EXECUTION_CAMP_ORIGIN_AUDIT_KEY}={EXECUTION_CAMP_HEAD}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join([module.EXPECTED_CURRENT_STATUS, module.AUTHORIZED_CURRENT_WORK, ""]),
    )
    return {
        "execution_artifact_dir": artifact,
        "execution_output_dir": output,
        "execution_audit_json": audit_json,
        "execution_audit_md": audit_md,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "review",
        "current_camp_head": CURRENT_CAMP_HEAD,
        "current_camp_origin_main": CURRENT_CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
    }


def test_runtime_shadow_replay_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["promotion_decision_plan_authorized_next"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["records"]["executed_top1_records"] == 3200
    assert (kwargs["output_dir"] / "result_review_report.json").is_file()
    assert (kwargs["output_dir"] / "result_review_report.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_shadow_replay_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_shadow_replay_result_review_rejects_source_violation(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, executed_top1_records=3199)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "executed_top1_all_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False
