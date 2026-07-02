import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result.py"
)
CAMP_HEAD = "11515f4d63628b6e7c1a4c2cd00650a8d9e71c5f"
ARTIFACT_CAMP_HEAD = "72fdb3e4c880751948a47d25b0330e3818975162"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_result_review", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _record(module, *, shadow_index: int = 2, selection_effect: bool = False) -> dict:
    return {
        "num_candidates": module.DEFAULT_EXPECTED_NUM_CANDIDATES,
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "weights": [1.0 / 9.0] * 9,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": shadow_index,
        "candidate_reference_blend_steps": [0, 0, 0],
        "candidate_closed_loop_outcome_weights": [0.0] * 8,
        "candidate_closed_loop_outcomes": [[0.0] * 2 for _ in range(8)],
        "perfect_tracker_command_postselection": False,
        "traffic_light_hybrid_postselection": False,
        "underprogress_relaxation": False,
        "splice_shadow_rule": False,
        "used_fallback": shadow_index == 0,
        "camp_candidate_tensor_provenance": {
            "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
            "generated_by_camp": False,
            "modified_by_camp": False,
        },
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": selection_effect,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": module.SCORE_EXPRESSION,
            "executed_index": 0,
            "executed_output_policy": "dp_top1",
            "shadow_selected_index": shadow_index,
            "failed_closed_reason": None,
            "artifact_contract_ready": True,
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False, selection_effect: bool = False) -> dict:
    artifact = tmp_path / "execution_artifact"
    output = tmp_path / "execution_output"
    artifact.mkdir()
    output.mkdir()
    _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={ARTIFACT_CAMP_HEAD}",
                f"CAMP_ORIGIN_MAIN={ARTIFACT_CAMP_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(artifact / "exit.code", "0\n")
    _write(
        artifact / "SHA256SUMS",
        "\n".join(
            [
                "0" * 64 + "  stdout.log",
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  stderr.log",
                "",
            ]
        ),
    )
    for route in ("sample_normal", "sample_tl"):
        log_dir = output / route / "seed_1" / "tl_off" / "trained_default_off_shadow_replay"
        records = [
            _record(module, shadow_index=index % 3, selection_effect=selection_effect)
            for index in range(3)
        ]
        _write(log_dir / "camp_selection_log.json", json.dumps(records))
        _write(log_dir / "validation_summary.json", "{}\n")
        _write(log_dir / "replay_summary.json", "{}\n")

    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.AUTHORIZED_CURRENT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={next_work}",
                f"{module.EXECUTION_CAMP_HEAD_AUDIT_KEY}={ARTIFACT_CAMP_HEAD}",
                f"{module.EXECUTION_CAMP_ORIGIN_AUDIT_KEY}={ARTIFACT_CAMP_HEAD}",
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
        "evaluation_output_dir": output,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_selection_log_count": 2,
        "expected_records": 6,
        "expected_records_per_log": 3,
        "expected_validation_summary_count": 2,
        "expected_replay_summary_count": 2,
    }


def test_v14_trained_shadow_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    records = report["records"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["promotion_decision_plan_authorized_next"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert records["records_total"] == 6
    assert records["executed_top1_records"] == 6
    assert records["selection_effect_true_count"] == 0
    assert records["shadow_selected_index_nonzero_records"] == 4
    assert (kwargs["output_dir"] / "result_review_report.json").is_file()
    assert (kwargs["output_dir"] / "result_review_report.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_trained_shadow_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_v14_trained_shadow_result_review_rejects_selection_effect(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selection_effect=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "selection_effect_true_zero" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False
