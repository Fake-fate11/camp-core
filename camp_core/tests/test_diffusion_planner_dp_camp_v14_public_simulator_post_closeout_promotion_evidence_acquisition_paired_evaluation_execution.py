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
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_paired_evaluation.py"
)
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_passes(
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
    assert decision["paired_evaluation_executed_by_this_gate"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["actual_safetycost_v1_claim_rule_evaluable"] is False
    assert report["paired_run_key_index"]["unique_paired_run_key_count"] == 4
    assert report["candidate_tensor_identity_table"]["identity_match_records"] == 4
    assert report["shadow_vs_top1_metric_delta_table"]["selection_score_delta"]["better_records"] == 4
    assert report["paired_execution_no_go_report"]["failed_count"] == 0
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_paired_evaluation_execution_authorization_missing"


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_rejects_tensor_mutation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, mutate_tensor=True)

    report = module.build_report(**fixture)

    assert "candidate_tensor_identity_records" in report["final_decision"]["failed_checks"]
    assert "candidate_tensor_mutation_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_rejects_non_affine_scores(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, non_affine=True)

    report = module.build_report(**fixture)

    assert "non_affine_score_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "paired_static_objective_contract_failure"


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    mutate_tensor: bool = False,
    non_affine: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_passed=True",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_authorized=True",
            "paired_evaluation_executed_by_current_gate=False",
            "paired_evaluation_execution_authorized=True",
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
        "SafetyCost_v1\nci95_high(DeltaSafetyCost_v1) < 0\n",
    )

    static_artifact = tmp_path / "static_review_artifact"
    static_review_dir = static_artifact / "review"
    static_json = _write_json(
        static_review_dir / module.SOURCE_PREFLIGHT_STATIC_REVIEW_JSON_NAME,
        _source_static_review_report(module),
    )
    static_md = _write(static_review_dir / "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review.md", "# static\n")
    static_sha = _write_sha256s(static_review_dir / "SHA256SUMS", [static_json, static_md])
    _write_sha256s(static_artifact / "SHA256SUMS", [static_json, static_md, static_sha])

    preflight_artifact = tmp_path / "preflight_artifact"
    preflight_dir = preflight_artifact / "preflight"
    preflight_json = _write_json(
        preflight_dir / module.SOURCE_PREFLIGHT_JSON_NAME,
        _source_preflight_report(module),
    )
    preflight_md = _write(preflight_dir / "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight.md", "# preflight\n")
    preflight_sha = _write_sha256s(preflight_dir / "SHA256SUMS", [preflight_json, preflight_md])
    _write_sha256s(preflight_artifact / "SHA256SUMS", [preflight_json, preflight_md, preflight_sha])

    runtime_result_json = _write_json(tmp_path / "runtime_result_review.json", _runtime_result_review())
    shadow_delta_json = _write_json(tmp_path / "shadow_delta_review.json", _shadow_delta_review())
    runtime_execution_dir = _write_runtime_logs(tmp_path / "runtime_execution", mutate_tensor=mutate_tensor, non_affine=non_affine)

    return {
        "runtime_execution_dir": runtime_execution_dir,
        "source_preflight_static_review_artifact_dir": static_artifact,
        "source_preflight_static_review_json": static_json,
        "source_preflight_static_review_md": static_md,
        "source_preflight_static_review_sha256s": static_sha,
        "source_preflight_artifact_dir": preflight_artifact,
        "source_preflight_json": preflight_json,
        "source_preflight_md": preflight_md,
        "source_preflight_sha256s": preflight_sha,
        "runtime_result_review_json": runtime_result_json,
        "shadow_delta_review_json": shadow_delta_json,
        "safety_score_doc": safety_score_doc,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_selection_log_count": 2,
        "expected_record_count": 4,
        "expected_records_per_log": 2,
        "expected_num_candidates": 3,
        "enabled": True,
    }


def _source_static_review_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "paired_evaluation_execution_authorized": True,
        "paired_evaluation_executed_by_this_gate": False,
        "failed_checks": [],
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    return {"schema_version": "source_static_review", "final_decision": decision}


def _source_preflight_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "authorized_next_work": module.SOURCE_STATUS,
        "paired_evaluation_executed_by_this_gate": False,
        "failed_checks": [],
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    return {
        "schema_version": "source_preflight",
        "final_decision": decision,
        "future_outputs": [{"name": "paired_run_key_index"}],
        "required_input_manifests": [{"name": "fixed_dp_candidate_tensor_manifest"}],
    }


def _runtime_result_review() -> dict[str, Any]:
    return {
        "final_decision": {"passed": True, "status": "runtime_result_review_passed"},
        "records": {"record_count": 4, "executed_top1_records": 4},
        "execution": {"selection_log_count": 2},
    }


def _shadow_delta_review() -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "status": "shadow_delta_review_passed",
            "static_objective_delta_supported": True,
        },
        "records": {"record_count": 4},
    }


def _write_runtime_logs(root: Path, *, mutate_tensor: bool, non_affine: bool) -> Path:
    for scenario, seed in [("sample_normal", 1), ("sample_tl", 2)]:
        log_dir = root / scenario / f"seed_{seed}" / "tl_off" / "runtime_default_off_shadow_replay"
        rows = [_selection_row(step, mutate_tensor=mutate_tensor, non_affine=non_affine) for step in range(2)]
        _write_json(log_dir / "camp_selection_log.json", rows)
    return root


def _selection_row(step: int, *, mutate_tensor: bool, non_affine: bool) -> dict[str, Any]:
    weights = [0.5, 0.5]
    atoms = [[2.0, 0.0], [0.0, 0.0], [3.0, 1.0]]
    scores = [1.0, 0.0, 2.0]
    if non_affine:
        scores = [1.5, 0.0, 2.0]
    tensor_hash = "1" * 64
    post_hash = "2" * 64 if mutate_tensor else tensor_hash
    selector_hash = {
        "sha256": tensor_hash,
        "shape": [3, 80, 4],
        "dtype": "float32",
    }
    return {
        "selection_step": step,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 1,
        "num_candidates": 3,
        "used_fallback": False,
        "candidate_reference_blend_steps": 0,
        "feasible_mask": [True, True, True],
        "atom_names": ["a", "b"],
        "selection_weights": weights,
        "weights": weights,
        "selection_normalized_atoms": atoms,
        "normalized_atoms": atoms,
        "selection_scores": scores,
        "scores": scores,
        "candidate_red_stopping_margin_cost": [1.0, 0.5, 2.0],
        "candidate_full_horizon_planned_red_light_cost": [0.0, 0.0, 1.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 1.0],
        "candidate_dp_prior_deviation_cost": [1.0, 0.5, 2.0],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5, 2.0],
        "candidate_dp_prior_acceleration_excess_cost": [1.0, 0.5, 2.0],
        "candidate_horizon_lateral_acceleration_cost": [1.0, 0.5, 2.0],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [1.0, 0.5, 2.0],
        "candidate_horizon_yaw_rate_cost": [1.0, 0.5, 2.0],
        "candidate_dp_prior_yaw_rate_excess_cost": [1.0, 0.5, 2.0],
        "candidate_route_progress": [2.0, 3.0, 1.0],
        "candidate_step_reach": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_first_step_reach_m": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_tail_average_speed_mps": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [3.0, 2.0, 5.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 0.5, 3.0],
        "latency_ms_camp_selection": 5.0,
        "candidate_closed_loop_outcomes": None,
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "source_scope": "public_simulator_fixed_dp_candidate_tensor",
            "selection_effect": False,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "executed_output_policy": "dp_top1",
            "shadow_selected_index": 1,
            "artifact_contract_ready": True,
            "candidate_tensor_hash": selector_hash,
        },
        "camp_candidate_tensor_provenance": {
            "enabled": True,
            "payload_valid": True,
            "candidate_tensor_mutation_effect": mutate_tensor,
            "pre_post_tensor_hash_equal": not mutate_tensor,
            "reference_blend_present": False,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "dp_modification_authorized": False,
            "candidate_generation_authorized": False,
            "pre_camp_scoring_tensor": {"sha256": tensor_hash, "shape": [3, 80, 4], "dtype": "float32"},
            "post_camp_selector_tensor": {"sha256": post_hash, "shape": [3, 80, 4], "dtype": "float32"},
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(path: Path, paths: list[Path]) -> Path:
    lines = [f"{_sha256(item)}  {item.name}" for item in paths]
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
