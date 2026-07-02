from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    INPUT_MATERIALIZER_REQUIREMENTS,
    INPUT_MATERIALIZER_SCRIPT,
    INPUT_MATERIALIZER_TEST,
    PREFLIGHT_REQUIREMENTS,
    PREFLIGHT_SCRIPT,
    READY_STATUS,
    REJECT_STATUS,
    RUNNER_REQUIREMENTS,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_PASS_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "890421f1280b67a18936699e00d13e7aa9c5cc4a"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_static_contract_"
    "review_passed"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _static_review(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_PASS_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_passed": True,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source_static_review": {
            "status": SOURCE_PASS_STATUS,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(
    tmp_path: Path,
    *,
    mutation: Any | None = None,
    target: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Any]:
    artifact_dir = tmp_path / "static_review_artifact"
    artifact_dir.mkdir(parents=True)
    return build_report(
        static_review_json=_static_review(artifact_dir / "static_contract_review.json", mutation=mutation),
        static_review_artifact_dir=artifact_dir,
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_execution_contract_input_remediation_implementation_plan_authorizes_static_review_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_ready"
    ] is True
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract_review_authorized_next"
    ] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["data_preparation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["fixed_dp_execution_started_by_this_gate"] is False
    assert RUNNER_SCRIPT in plan["implementation_targets"]
    assert PREFLIGHT_SCRIPT in plan["implementation_targets"]
    assert INPUT_MATERIALIZER_SCRIPT in plan["implementation_targets"]
    assert INPUT_MATERIALIZER_TEST in plan["test_targets"]
    assert plan["runner_requirements"] == list(RUNNER_REQUIREMENTS)
    assert plan["preflight_requirements"] == list(PREFLIGHT_REQUIREMENTS)
    assert plan["input_materializer_requirements"] == list(INPUT_MATERIALIZER_REQUIREMENTS)
    assert plan["required_zero_overlap_keys"] == list(ZERO_OVERLAP_KEYS)


def test_execution_contract_input_remediation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_execution_contract_input_remediation_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_remediation_implementation_plan_rejects_missing_static_review_auth(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"][
            "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next"
        ] = False

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_authorizes_implementation_plan" in report["final_decision"]["failed_checks"]


def test_execution_contract_input_remediation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "static_review_artifact"
    artifact_dir.mkdir()
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_review_json",
            str(_static_review(artifact_dir / "static_contract_review.json")),
            "--static_review_artifact_dir",
            str(artifact_dir),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "training_preflight_authorized: `False`" in output_md.read_text(encoding="utf-8")
