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
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization.py"
)
CURRENT_HEAD = "c" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actual_safetycost_outcome_materialization_execution_passes_with_shadow_summaries(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_shadow_summaries=True)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["actual_safetycost_outcome_materialization_executed_by_this_gate"] is True
    assert decision["actual_safetycost_v1_available"] is True
    assert decision["actual_safetycost_v1_claim_rule_evaluable"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["materialization_summary"]["delta_count"] == 2
    assert report["materialization_summary"]["no_go_report"]["failed_count"] == 0
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_actual_safetycost_outcome_materialization_execution_fails_without_shadow_summaries(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_shadow_summaries=False)

    report = module.build_report(**fixture)

    decision = report["final_decision"]
    assert decision["passed"] is False
    assert decision["failure_class"] == "actual_safetycost_outcome_source_missing"
    assert "shadow_selected_summary_root_provided" in decision["failed_checks"]
    assert "materialization_shadow_summary_count" in decision["failed_checks"]
    assert decision["recommended_next_work"] == module.FAILED_NEXT_WORK
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["safety_benefit_claim_authorized"] is False


def test_actual_safetycost_outcome_materialization_execution_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_shadow_summaries=True)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_actual_safetycost_outcome_materialization_execution_authorization_missing"
    )


def test_actual_safetycost_outcome_materialization_execution_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_shadow_summaries=True, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_actual_safetycost_outcome_materialization_execution_accepts_shadow_execution_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        with_shadow_summaries=True,
        status=module.SHADOW_SELECTED_EXECUTION_STATUS,
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK


def test_actual_safetycost_outcome_materialization_execution_rejects_tensor_mutation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_shadow_summaries=True, mutate_tensor=True)

    report = module.build_report(**fixture)

    assert "paired_execution_candidate_tensor_mutation_records" in report["final_decision"]["failed_checks"]
    assert "runtime_candidate_tensor_mutation_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    with_shadow_summaries: bool,
    status: str | None = None,
    next_work: str | None = None,
    mutate_tensor: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={status or module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "actual_safetycost_outcome_materialization_execution_authorized=True",
            "actual_safetycost_outcome_materialization_executed_by_current_gate=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_artifact = tmp_path / "source_static_review"
    source_review_dir = source_artifact / "review"
    source_json = _write_json(
        source_review_dir / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        _source_static_review_report(module),
    )
    source_md = _write(source_review_dir / module.SOURCE_STATIC_REVIEW_MD_NAME, "# source static\n")
    source_sha = _write_sha256s(source_review_dir / "SHA256SUMS", [source_json, source_md])
    _write(source_artifact / "HEADS", f"DP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(source_artifact / "COMMAND", "source static review\n")
    _write(source_artifact / "stdout", "{}\n")
    _write(source_artifact / "stderr", "")
    _write(source_artifact / "run.exit", "0\n")
    _write_sha256s(
        source_artifact / "SHA256SUMS",
        [source_json, source_md, source_sha, source_artifact / "HEADS", source_artifact / "run.exit"],
    )

    paired_artifact = tmp_path / "paired_execution"
    paired_dir = paired_artifact / "evaluation"
    paired_json = _write_json(
        paired_dir / "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution.json",
        _paired_execution_report(mutate_tensor=mutate_tensor),
    )
    paired_sha = _write_sha256s(paired_dir / "SHA256SUMS", [paired_json])
    _write(paired_artifact / "HEADS", f"DP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(paired_artifact / "COMMAND", "paired execution\n")
    _write(paired_artifact / "stdout", "{}\n")
    _write(paired_artifact / "stderr", "")
    _write(paired_artifact / "run.exit", "0\n")
    _write_sha256s(
        paired_artifact / "SHA256SUMS",
        [paired_json, paired_sha, paired_artifact / "HEADS", paired_artifact / "run.exit"],
    )

    runtime = _write_runtime(tmp_path / "runtime", mutate_tensor=mutate_tensor)
    shadow_root = _write_shadow_summaries(tmp_path / "shadow") if with_shadow_summaries else None

    return {
        "source_preflight_static_review_artifact_dir": source_artifact,
        "source_preflight_static_review_json": source_json,
        "source_preflight_static_review_md": source_md,
        "source_preflight_static_review_sha256s": source_sha,
        "paired_execution_artifact_dir": paired_artifact,
        "paired_execution_json": paired_json,
        "paired_execution_sha256s": paired_sha,
        "runtime_execution_dir": runtime,
        "shadow_selected_summary_root": shadow_root,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": 4,
        "expected_selection_log_count": 2,
        "enabled": True,
    }


def _source_static_review_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "actual_safetycost_outcome_materialization_execution_authorized": True,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "failed_checks": [],
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    return {"schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA, "final_decision": decision}


def _paired_execution_report(*, mutate_tensor: bool) -> dict[str, Any]:
    return {
        "final_decision": {
            "passed": True,
            "actual_safetycost_v1_available": False,
        },
        "paired_record_summary": {"record_count": 4},
        "candidate_tensor_identity_table": {"candidate_tensor_mutation_records": 1 if mutate_tensor else 0},
    }


def _write_runtime(root: Path, *, mutate_tensor: bool) -> Path:
    for route, seed in [("route_a", 1), ("route_b", 2)]:
        run_dir = root / route / f"seed_{seed}" / "tl_off" / "runtime_default_off_shadow_replay"
        rows = [
            {
                "selection_step": index,
                "candidate_closed_loop_outcomes": None,
                "camp_candidate_tensor_provenance": {
                    "candidate_tensor_mutation_effect": mutate_tensor,
                },
            }
            for index in range(2)
        ]
        _write_json(run_dir / "camp_selection_log.json", rows)
        _write_json(run_dir / "camp_validation_summary.json", _summary(route, seed, cost_offset=0.0))
    return root


def _write_shadow_summaries(root: Path) -> Path:
    for route, seed in [("route_a", 1), ("route_b", 2)]:
        run_dir = root / route / f"seed_{seed}" / "tl_off" / "runtime_shadow_selected"
        _write_json(run_dir / "camp_validation_summary.json", _summary(route, seed, cost_offset=-0.2))
    return root


def _summary(route: str, seed: int, *, cost_offset: float) -> dict[str, Any]:
    return {
        "advance_mode": "perfect",
        "benchmark": {
            "route": f"/tmp/{route}.pkl",
            "seed": seed,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": False,
            "advance_mode": "perfect",
        },
        "obb_collision_rate": 0.0,
        "near_miss_rate": 0.0,
        "lane_violation_rate": 0.0,
        "red_light_violation_rate": 0.0,
        "planned_red_light_violation_rate": 0.0,
        "mean_jerk_magnitude_mps3": 2.0 + cost_offset,
        "mean_lateral_acceleration_mps2": 0.5,
        "route_completion_rate": 1.0,
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
