import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_vs_top1_delta.py"
)
CURRENT_CAMP_HEAD = "b003fc98d5ad6d58aa29f68fd5aa4451e251e22f"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_vs_top1_delta", SCRIPT_PATH)
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


def _selector(shadow_index: int) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "enabled": True,
        "default_off": True,
        "source_scope": "public_simulator_fixed_dp_candidate_tensor",
        "selection_effect": False,
        "online_selector_change": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
        "executed_index": 0,
        "executed_output_policy": "dp_top1",
        "shadow_selected_index": shadow_index,
        "artifact_contract_ready": True,
    }


def _record(*, shadow_index: int, selection_scores: list[float], scores: list[float]) -> dict:
    return {
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": shadow_index,
        "num_candidates": 3,
        "feasible_mask": [score != float("inf") for score in selection_scores],
        "selection_scores": selection_scores,
        "scores": scores,
        "atom_names": ["jerk_early", "lane_deviation"],
        "selection_normalized_atoms": [
            [0.50, 0.20],
            [0.40, 0.10],
            [0.30, 0.00],
        ],
        "default_off_shadow_selector": _selector(shadow_index),
    }


def _source_result(module, *, record_count: int) -> dict:
    return {
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_RESULT_REVIEW_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.EXPECTED_CURRENT_NEXT_WORK,
        },
        "heads": {
            "current_camp_head": CURRENT_CAMP_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
        },
        "execution": {
            "selection_log_count": 1,
        },
        "records": {
            "record_count": record_count,
            "executed_top1_records": record_count,
            "shadow_selected_index_differs_from_executed_index_records": 2,
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False, worse_shadow: bool = False) -> dict:
    output = tmp_path / "execution_output" / "route_a" / "seed_1" / "tl_off"
    if worse_shadow:
        records = [
            _record(shadow_index=2, selection_scores=[0.10, 0.20, 0.30], scores=[0.10, 0.20, 0.30]),
            _record(shadow_index=0, selection_scores=[0.10, 0.20, 0.30], scores=[0.10, 0.20, 0.30]),
        ]
    else:
        records = [
            _record(shadow_index=2, selection_scores=[0.50, 0.20, 0.10], scores=[0.50, 0.20, 0.10]),
            _record(shadow_index=0, selection_scores=[0.10, 0.20, 0.30], scores=[0.10, 0.20, 0.30]),
            _record(
                shadow_index=1,
                selection_scores=[float("inf"), 0.40, 0.50],
                scores=[0.20, 0.40, 0.50],
            ),
        ]
    _write_json(output / "camp_selection_log.json", records)
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.EXPECTED_CURRENT_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    source_json = _write_json(
        tmp_path / "source" / "result_review_report.json",
        _source_result(module, record_count=len(records)),
    )
    source_md = _write(tmp_path / "source" / "result_review_report.md", "# source\n")
    return {
        "execution_output_dir": tmp_path / "execution_output",
        "source_result_review_json": source_json,
        "source_result_review_md": source_md,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "delta_review",
        "current_camp_head": CURRENT_CAMP_HEAD,
        "current_camp_origin_main": CURRENT_CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_log_count": 1,
        "expected_records": len(records),
        "expected_records_per_log": len(records),
        "expected_num_candidates": 3,
    }


def test_shadow_vs_top1_delta_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    records = report["records"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["static_objective_delta_supported"] is True
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert records["selection_score_comparison"]["better_records"] == 2
    assert records["selection_score_comparison"]["worse_records"] == 0
    assert records["selection_score_comparison"]["tie_records"] == 1
    assert records["selection_score_comparison_among_shadow_diff_records"]["better_records"] == 2
    assert (kwargs["output_dir"] / "shadow_vs_top1_delta_review_report.json").is_file()
    assert (kwargs["output_dir"] / "shadow_vs_top1_delta_review_report.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_shadow_vs_top1_delta_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_shadow_vs_top1_delta_review_rejects_worse_shadow_score(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, worse_shadow=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "selection_score_worse_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "static_objective_delta_failure"
    assert report["final_decision"]["selector_promotion_authorized"] is False
