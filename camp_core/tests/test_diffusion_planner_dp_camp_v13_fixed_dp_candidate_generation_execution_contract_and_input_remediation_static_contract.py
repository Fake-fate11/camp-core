from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_CONTRACT_REMEDIATIONS,
    REQUIRED_INPUT_REMEDIATIONS,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "bb07f1808589e38ca4a5171f56b9ea92ec84bb8b"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _plan(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_plan_ready": True,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "remediation_plan": {
            "implementation_performed_by_this_gate": False,
            "fixed_dp_execution_started_by_this_gate": False,
            "future_runner_script": RUNNER_SCRIPT,
            "future_preflight_script": "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution.py",
            "contract_remediations": list(REQUIRED_CONTRACT_REMEDIATIONS),
            "input_remediations": list(REQUIRED_INPUT_REMEDIATIONS),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "candidate_generation_by_camp_allowed": False,
            "training_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "CONTRACT_REMEDIATIONS",
                "INPUT_REMEDIATIONS",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_authorized_next",
                "required_valid_set_list_missing_before_remediation",
                "candidate_generation_by_camp_allowed",
                "score_expression",
                "",
            ]
        ),
    )


def _plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_execution_contract_and_input_remediation_plan_authorizes_static_review_only",
                "test_execution_contract_and_input_remediation_plan_rejects_missing_failed_check",
                "test_execution_contract_and_input_remediation_plan_rejects_premature_valid_set_list",
                "AUTHORIZED_NEXT_WORK",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_authorized_next=True",
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
    artifact_dir = tmp_path / "plan_artifact"
    artifact_dir.mkdir(parents=True)
    return build_report(
        plan_json=_plan(artifact_dir / "remediation_plan.json", mutation=mutation),
        plan_artifact_dir=artifact_dir,
        plan_script=_plan_script(tmp_path / "plan.py"),
        plan_test=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_execution_contract_input_static_review_authorizes_implementation_plan_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_passed"
    ] is True
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next"
    ] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["implementation_performed_by_source_plan"] is False
    assert review["fixed_dp_execution_started_by_source_plan"] is False
    assert review["contract_remediations"] == list(REQUIRED_CONTRACT_REMEDIATIONS)
    assert review["input_remediations"] == list(REQUIRED_INPUT_REMEDIATIONS)


def test_execution_contract_input_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_execution_contract_input_static_review_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_static_review_rejects_missing_contract_remediation(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["remediation_plan"]["contract_remediations"] = [
            item
            for item in REQUIRED_CONTRACT_REMEDIATIONS
            if item != "refresh_runbook_current_camp_head_after_audit_commit"
        ]

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_contract_remediation_refresh_runbook_current_camp_head_after_audit_commit" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_static_review_rejects_missing_input_remediation(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["remediation_plan"]["input_remediations"] = [
            item
            for item in REQUIRED_INPUT_REMEDIATIONS
            if item != "require_nonempty_valid_set_list_before_execution"
        ]

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_input_remediation_require_nonempty_valid_set_list_before_execution" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_static_review_main_writes_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "plan_artifact"
    artifact_dir.mkdir()
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--plan_json",
            str(_plan(artifact_dir / "remediation_plan.json")),
            "--plan_artifact_dir",
            str(artifact_dir),
            "--plan_script",
            str(_plan_script(tmp_path / "plan.py")),
            "--plan_test",
            str(_plan_test(tmp_path / "test_plan.py")),
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
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert "fixed_dp_generation_executed: `False`" in output_md.read_text(encoding="utf-8")
