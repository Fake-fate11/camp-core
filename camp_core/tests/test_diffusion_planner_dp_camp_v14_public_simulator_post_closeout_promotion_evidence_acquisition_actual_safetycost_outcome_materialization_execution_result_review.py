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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution_result.py"
)
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actual_safetycost_outcome_materialization_result_review_passes_and_recommends_no_claim_closeout(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.NO_PROMOTION_CLOSEOUT_WORK
    assert decision["safety_benefit_claim_supported"] is False
    assert decision["camp_over_dp_top1_claim_supported"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["no_promotion_closeout_recommended"] is True
    assert report["actual_safetycost_claim_rule_summary"]["delta_mean"] == 0.5
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_actual_safetycost_outcome_materialization_result_review_only_plans_claim_boundary_when_supported(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, supported=True)

    report = module.build_report(**fixture)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == module.CLAIM_REVIEW_PLAN_WORK
    assert decision["safety_benefit_claim_supported"] is True
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["no_promotion_closeout_recommended"] is False


def test_actual_safetycost_outcome_materialization_result_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_actual_safetycost_result_review_authorization_missing"
    )


def test_actual_safetycost_outcome_materialization_result_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_actual_safetycost_outcome_materialization_result_review_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, claim_leak=True)

    report = module.build_report(**fixture)

    assert "source_execution_decision_safety_benefit_claim_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_actual_safetycost_outcome_materialization_result_review_accepts_lowercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, lowercase_heads=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["heads"]["source_artifact_dp_head"] == module.FIXED_DP_HEAD


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    supported: bool = False,
    next_work: str | None = None,
    claim_leak: bool = False,
    lowercase_heads: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_EXECUTION_STATUS}",
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

    source_artifact = tmp_path / "source_execution"
    materialization_dir = source_artifact / "materialization"
    source_json = _write_json(
        materialization_dir / module.SOURCE_EXECUTION_JSON_NAME,
        _source_execution_report(module, supported=supported, claim_leak=claim_leak),
    )
    source_md = _write(materialization_dir / module.SOURCE_EXECUTION_MD_NAME, "# source execution\n")
    source_sha = _write_sha256s(materialization_dir / "SHA256SUMS", [source_json, source_md])
    head_key = "dp_head" if lowercase_heads else "DP_HEAD"
    _write(
        source_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={CURRENT_HEAD}",
                f"CAMP_ORIGIN_MAIN={CURRENT_HEAD}",
                f"{head_key}={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(source_artifact / "COMMAND", "materialization execution\n")
    _write(source_artifact / "stdout", "{}\n")
    _write(source_artifact / "stderr", "")
    _write(source_artifact / "run.exit", "0\n")
    _write_sha256s(
        source_artifact / "SHA256SUMS",
        [
            source_json,
            source_md,
            source_sha,
            source_artifact / "HEADS",
            source_artifact / "COMMAND",
            source_artifact / "stdout",
            source_artifact / "stderr",
            source_artifact / "run.exit",
        ],
        root=source_artifact,
    )

    return {
        "source_execution_artifact_dir": source_artifact,
        "source_execution_json": source_json,
        "source_execution_md": source_md,
        "source_execution_sha256s": source_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_summary_count": 2,
        "expected_runtime_record_count": 4,
        "expected_selection_log_count": 2,
        "enabled": True,
    }


def _source_execution_report(module, *, supported: bool, claim_leak: bool) -> dict[str, Any]:
    mean = -0.5 if supported else 0.5
    ci_low = -0.9 if supported else 0.1
    ci_high = -0.1 if supported else 0.8
    better = 2 if supported else 0
    worse = 0 if supported else 2
    decision = {
        "passed": True,
        "status": module.SOURCE_EXECUTION_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": True,
        "actual_safetycost_v1_available": True,
        "actual_safetycost_v1_claim_rule_evaluable": True,
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "safetycost_v1_claim_authorized": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    if claim_leak:
        decision["safety_benefit_claim_authorized"] = True
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "final_decision": decision,
        "runtime_source_summary": {
            "selection_log_count": 2,
            "record_count": 4,
            "candidate_tensor_mutation_records": 0,
            "closed_loop_outcomes_training_or_online_input": False,
            "full36_path_records": 0,
            "formal_seed_records": 0,
        },
        "materialization_summary": {
            "top1_summary_count": 2,
            "shadow_summary_count": 2,
            "paired_run_key_count": 2,
            "delta_count": 2,
            "duplicate_run_key_count": 0,
            "unpaired_run_key_count": 0,
            "invalid_summary_count": 0,
            "actual_safetycost_v1_available": True,
            "actual_safetycost_v1_claim_rule_evaluable": True,
            "safetycost_v1_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "delta_summary": {
                "count": 2,
                "mean": mean,
                "min": mean - 0.1,
                "max": mean + 0.1,
                "better_records": better,
                "worse_records": worse,
                "tie_records": 0,
            },
            "delta_bootstrap_ci95": {
                "mean": mean,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "resamples": 10000,
            },
            "no_go_report": {"failed_count": 0, "failures": []},
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256s(path: Path, files: list[Path], root: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.name if root is None else file.relative_to(root).as_posix()
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
