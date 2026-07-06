from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition.py"
)
CURRENT_HEAD = "a" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_outcome_acquisition_execution_passes_when_per_record_outcomes_exist(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, with_candidate_outcomes=True)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)
    decision = report["final_decision"]
    acquisition = report["objective_3200_outcome_acquisition_summary"]

    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_satisfied"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert acquisition["runtime_record_count"] == 4
    assert acquisition["candidate_closed_loop_outcome_records"] == 4
    assert acquisition["missing_candidate_closed_loop_outcome_records"] == 0
    assert acquisition["paired_record_key_count"] == 4
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_outcome_acquisition_execution_fails_closed_without_outcomes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, with_candidate_outcomes=False)

    report = module.build_report(**fixture)
    decision = report["final_decision"]

    assert decision["passed"] is False
    assert decision["failure_class"] == "objective_3200_outcome_acquisition_execution_source_missing"
    assert decision["recommended_next_work"] == module.FAILED_NEXT_WORK
    assert "candidate_outcome_record_count" in decision["failed_checks"]
    assert "candidate_missing_outcome_record_count" in decision["failed_checks"]
    assert decision["candidate_closed_loop_outcome_records"] == 0
    assert decision["missing_candidate_closed_loop_outcome_records"] == 4
    assert decision["safety_benefit_claim_authorized"] is False


def test_objective_3200_outcome_acquisition_execution_requires_current_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, with_candidate_outcomes=True, next_work="other_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]


def _fixture(
    tmp_path: Path,
    module,
    *,
    with_candidate_outcomes: bool,
    next_work: str | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_artifact = tmp_path / "source_preflight_static_review"
    source_review_dir = source_artifact / "review"
    source_json = _write_json(
        source_review_dir / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        _source_static_review_report(module),
    )
    source_md = _write(source_review_dir / module.SOURCE_STATIC_REVIEW_MD_NAME, "# source static review\n")
    source_sha = _write_sha256s(source_review_dir / "SHA256SUMS", [(source_json, source_json.name), (source_md, source_md.name)])
    _write(
        source_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={CURRENT_HEAD}",
                f"CAMP_ORIGIN_MAIN={CURRENT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(source_artifact / "COMMAND", "source static review\n")
    _write(source_artifact / "stdout", "{}\n")
    _write(source_artifact / "stderr", "")
    _write(source_artifact / "run.exit", "0\n")
    _write_sha256s(
        source_artifact / "SHA256SUMS",
        [
            (source_json, f"review/{source_json.name}"),
            (source_md, f"review/{source_md.name}"),
            (source_sha, "review/SHA256SUMS"),
            (source_artifact / "HEADS", "HEADS"),
            (source_artifact / "run.exit", "run.exit"),
        ],
    )

    runtime = _write_selection_logs(tmp_path / "runtime", with_outcomes=False, module=module)
    candidate = _write_selection_logs(tmp_path / "candidate", with_outcomes=with_candidate_outcomes, module=module)

    return {
        "source_preflight_static_review_artifact_dir": source_artifact,
        "source_preflight_static_review_json": source_json,
        "source_preflight_static_review_md": source_md,
        "source_preflight_static_review_sha256s": source_sha,
        "runtime_execution_dir": runtime,
        "candidate_outcome_source_root": candidate,
        "candidate_outcome_source_artifact_dir": tmp_path / "candidate_artifact",
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
        "objective_required_records": 4,
        "runtime_record_count": 4,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": 4,
        "failed_checks": [],
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "outcome_acquisition_executed": False,
            "dp_modification": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_preflight_summary": {
            "objective_required_records": 4,
            "runtime_record_count": 4,
            "candidate_closed_loop_outcome_records": 0,
            "missing_candidate_closed_loop_outcome_records": 4,
        },
        "final_decision": decision,
    }


def _write_selection_logs(root: Path, *, with_outcomes: bool, module) -> Path:
    for route, seed in [("route_a", 1), ("route_b", 2)]:
        run_dir = root / route / f"seed_{seed}" / "tl_off" / "runtime"
        rows = [_row(index, with_outcomes=with_outcomes, module=module) for index in range(2)]
        _write_json(run_dir / "camp_selection_log.json", rows)
        _write_json(run_dir / "camp_validation_summary.json", {"benchmark": {"route": route, "seed": seed}})
    return root


def _row(index: int, *, with_outcomes: bool, module) -> dict[str, Any]:
    tensor_hash = "b" * 64
    return {
        "selection_step": index,
        "sample_index": index,
        "candidate_closed_loop_outcomes": [{"safetycost_v1": 1.0 + index}] if with_outcomes else None,
        "weights": [0.5, 0.5],
        "default_off_shadow_selector": {
            "score_expression": module.SCORE_EXPRESSION,
            "candidate_tensor_hash": {"sha256": tensor_hash},
        },
        "camp_candidate_tensor_provenance": {
            "pre_camp_scoring_tensor": {"sha256": tensor_hash},
            "post_camp_selector_tensor": {"sha256": tensor_hash},
            "pre_post_tensor_hash_equal": True,
            "candidate_tensor_mutation_effect": False,
            "reference_blend_present": False,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(path: Path, paths: list[tuple[Path, str]]) -> Path:
    lines = [f"{_sha256(item)}  {name}" for item, name in paths]
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
