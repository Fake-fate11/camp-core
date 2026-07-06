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
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization.py"
)
SOURCE_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_delta_materialization_execution_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["delta_materialization_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["actual_safetycost_delta_materialization_executed_by_this_gate"] is True
    assert decision["candidate_index_replay_executed_by_this_gate"] is False
    assert decision["outcome_acquisition_executed_by_this_gate"] is False
    assert decision["actual_safetycost_v1_available"] is True
    assert decision["actual_safetycost_v1_claim_rule_evaluable"] is True
    assert decision["same_as_top1_records"] == 1
    assert decision["non_top1_shadow_selected_records"] == 3
    assert decision["delta_better_records"] == 2
    assert decision["delta_tie_records"] == 1
    assert decision["delta_worse_records"] == 1
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["no_go_report"]["failed_count"] == 0
    assert len(report["paired_safetycost_v1_rows"]) == 4
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / module.DELTA_TABLE_JSONL_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_actual_safetycost_delta_materialization_execution_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_actual_safetycost_delta_materialization_execution_authorization_missing"
    )


def test_candidate_index_actual_safetycost_delta_materialization_execution_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_delta_materialization_execution_rejects_tensor_mutation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, mutate_tensor=True)

    report = module.build_report(**fixture)

    assert "delta_candidate_tensor_mutation_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["selector_promotion_authorized"] is False


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    mutate_tensor: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review_passed=True",
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "online_selector_change_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_artifact = _write_source_static_review_artifact(tmp_path / "source_static_review", module)
    candidate_root = _write_candidate_output_root(
        tmp_path / "candidate_index_runtime",
        mutate_tensor=mutate_tensor,
    )
    candidate_artifact = _write_candidate_execution_artifact(
        tmp_path / "candidate_index_execution",
        module,
        candidate_root=candidate_root,
    )
    return {
        "source_preflight_static_review_artifact_dir": source_artifact["artifact"],
        "source_preflight_static_review_json": source_artifact["json"],
        "source_preflight_static_review_md": source_artifact["md"],
        "source_preflight_static_review_sha256s": source_artifact["sha256s"],
        "candidate_index_execution_artifact_dir": candidate_artifact["artifact"],
        "candidate_index_execution_json": candidate_artifact["json"],
        "candidate_index_execution_md": candidate_artifact["md"],
        "candidate_index_execution_sha256s": candidate_artifact["sha256s"],
        "candidate_index_output_root": candidate_root,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": 4,
        "expected_selection_log_count": 2,
        "expected_num_candidates": 2,
        "enabled": True,
    }


def _write_source_static_review_artifact(artifact: Path, module) -> dict[str, Path]:
    review_dir = artifact / "review"
    review_json = _write_json(review_dir / module.SOURCE_STATIC_REVIEW_JSON_NAME, _source_review_report(module))
    review_md = _write(review_dir / module.SOURCE_STATIC_REVIEW_MD_NAME, "# source static review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    heads = _write_heads(artifact / "HEADS", module)
    command = _write(artifact / "COMMAND", "python review.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, review_json, review_md, review_sha],
        relative_to=artifact,
    )
    return {"artifact": artifact, "json": review_json, "md": review_md, "sha256s": review_sha}


def _write_candidate_execution_artifact(
    artifact: Path,
    module,
    *,
    candidate_root: Path,
) -> dict[str, Path]:
    report_dir = artifact / "report"
    execution_json = _write_json(
        report_dir / module.CANDIDATE_EXECUTION_JSON_NAME,
        _candidate_execution_report(module, candidate_root=candidate_root),
    )
    execution_md = _write(report_dir / module.CANDIDATE_EXECUTION_MD_NAME, "# candidate execution\n")
    execution_sha = _write_sha256s(report_dir / "SHA256SUMS", [execution_json, execution_md])
    heads = _write_heads(artifact / "HEADS", module)
    command = _write(artifact / "COMMAND", "python execute_candidate_index.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, execution_json, execution_md, execution_sha],
        relative_to=artifact,
    )
    return {"artifact": artifact, "json": execution_json, "md": execution_md, "sha256s": execution_sha}


def _write_candidate_output_root(root: Path, *, mutate_tensor: bool) -> Path:
    scenarios = [
        ("route_a", "seed_1", "tl_off"),
        ("route_b", "seed_2", "tl_on"),
    ]
    record_specs = [
        (1, 2.0, 1.0),
        (0, 1.0, 1.0),
        (1, 1.0, 3.0),
        (1, 4.0, 2.0),
    ]
    spec_index = 0
    for route, seed, tl_mode in scenarios:
        runtime = root / route / seed / tl_mode / "runtime_default_off_shadow_replay"
        records = []
        for step in range(2):
            shadow_index, top1_jerk, shadow_jerk = record_specs[spec_index]
            records.append(
                _selection_record(
                    step=step,
                    shadow_index=shadow_index,
                    top1_jerk=top1_jerk,
                    shadow_jerk=shadow_jerk,
                    mutate_tensor=mutate_tensor,
                )
            )
            spec_index += 1
        _write_json(runtime / "camp_selection_log.json", records)
    return root


def _selection_record(
    *,
    step: int,
    shadow_index: int,
    top1_jerk: float,
    shadow_jerk: float,
    mutate_tensor: bool,
) -> dict[str, Any]:
    return {
        "selection_step": step,
        "shadow_selected_index": shadow_index,
        "executed_index": shadow_index,
        "num_candidates": 2,
        "selection_weights": [0.5, 0.5],
        "default_off_shadow_selector": {"score_expression": "score_k(w)=a_k^T w"},
        "camp_candidate_tensor_provenance": {
            "candidate_tensor_mutation_effect": mutate_tensor,
            "pre_post_tensor_hash_equal": not mutate_tensor,
            "reference_blend_present": False,
            "outcome_label_input": False,
        },
        "candidate_index_replay_harness": {
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
        },
        "candidate_reference_blend_steps": 0,
        "candidate_closed_loop_outcome_weights": {
            "progress": 1.0,
            "collision": 100.0,
            "near_miss": 10.0,
            "lane_violation": 20.0,
            "red_light": 30.0,
            "mean_jerk": 1.0,
            "mean_lateral_acceleration": 1.0,
        },
        "candidate_closed_loop_outcomes": [
            _outcome(candidate_index=0, jerk=top1_jerk),
            _outcome(candidate_index=1, jerk=shadow_jerk),
        ],
    }


def _outcome(*, candidate_index: int, jerk: float) -> dict[str, Any]:
    return {
        "candidate_index": candidate_index,
        "horizon_steps": 30,
        "progress_m": 10.0,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": 0.0,
        "feasible": True,
        "value": 10.0 - jerk,
    }


def _source_review_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "actual_safetycost_delta_materialization_execution_authorized": True,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "objective_required_records": 4,
        "paired_record_key_count": 4,
        "candidate_closed_loop_outcome_records": 4,
        "missing_candidate_closed_loop_outcome_records": 0,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    return {"schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA, "final_decision": decision}


def _candidate_execution_report(module, *, candidate_root: Path) -> dict[str, Any]:
    return {
        "schema_version": module.CANDIDATE_EXECUTION_SCHEMA,
        "inputs": {"candidate_index_output_root": str(candidate_root)},
        "candidate_index_outcome_summary": {
            "root": str(candidate_root),
            "selection_log_count": 2,
            "record_count": 4,
            "candidate_closed_loop_outcome_records": 4,
            "missing_candidate_closed_loop_outcome_records": 0,
        },
        "strict_pairing_summary": {"paired_record_key_count": 4},
        "no_go_report": {"failed_count": 0, "failures": []},
        "final_decision": {
            "passed": True,
            "status": module.CANDIDATE_EXECUTION_STATUS,
            "candidate_index_replay_execution_executed_by_this_gate": True,
            "outcome_acquisition_executed_by_this_gate": True,
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "online_selector_change_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _write_heads(path: Path, module) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_sha256s(path: Path, files: list[Path], *, relative_to: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.relative_to(relative_to).as_posix() if relative_to else file.name
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
