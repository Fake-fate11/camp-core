from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_remediation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    CONTRACT_REMEDIATIONS,
    FIXED_DP_HEAD,
    INPUT_REMEDIATIONS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FAILED_CHECKS,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_REJECT_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "1c1ab98a6e0dc83f9b282d7de7a53147bc194886"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_rejected_runner_contract_authorization_"
    "mismatch_and_missing_inputs"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _execution_rejection(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_REJECT_STATUS,
        "passed": False,
        "failed_checks": list(REQUIRED_FAILED_CHECKS),
        "authorized_next_work": None,
        "fixed_dp_candidate_generation_executed": False,
        "dp_modification_authorized": False,
        "training_preflight_authorized_next": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
    }
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "runner_contract": {
            "runner_script": RUNNER_SCRIPT,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _artifact_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _write(path / "exit.txt", "1")
    _write(path / "stdout.txt", "{}\n")
    _write(path / "stderr.txt", "")
    return path


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fixed_dp_candidate_generation_execution_rejected=True",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_plan_authorized_next=True",
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
    create_checkpoint: bool = True,
    create_valid_set_list: bool = False,
    create_candidate_output: bool = False,
) -> dict[str, Any]:
    checkpoint = tmp_path / "fixed_dp" / "diffusion_planner.pth"
    args_json = tmp_path / "fixed_dp" / "diffusion_planner.param.json"
    valid_set_list = tmp_path / "inputs" / "valid_set_list.json"
    candidate_output = tmp_path / "candidate_output"
    if create_checkpoint:
        _write(checkpoint, "fixed checkpoint placeholder")
        _write_json(args_json, {"device": "cuda"})
    if create_valid_set_list:
        _write_json(valid_set_list, {"files": []})
    if create_candidate_output:
        candidate_output.mkdir(parents=True)
    artifact_dir = _artifact_dir(tmp_path / "execution_rejection_artifact")
    return build_report(
        execution_rejection_json=_execution_rejection(
            artifact_dir / "runner_execution.json", mutation=mutation
        ),
        execution_rejection_artifact_dir=artifact_dir,
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        dp_repo=tmp_path,
        camp_repo=tmp_path,
        fixed_dp_checkpoint=checkpoint,
        fixed_dp_args_json=args_json,
        required_valid_set_list=valid_set_list,
        candidate_output_dir=candidate_output,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_execution_contract_and_input_remediation_plan_authorizes_static_review_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["remediation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_execution_contract_and_input_remediation_plan_ready"] is True
    assert decision["fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["fixed_dp_execution_started_by_this_gate"] is False
    assert plan["contract_remediations"] == list(CONTRACT_REMEDIATIONS)
    assert plan["input_remediations"] == list(INPUT_REMEDIATIONS)
    assert plan["required_zero_overlap_keys"] == list(ZERO_OVERLAP_KEYS)
    assert plan["candidate_generation_by_camp_allowed"] is False
    assert plan["training_authorized"] is False


def test_execution_contract_and_input_remediation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_execution_contract_and_input_remediation_plan_rejects_missing_failed_check(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["failed_checks"] = ["source_authorized_next_work"]

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_failed_check_audit_authorizes_implementation" in report["final_decision"][
        "failed_checks"
    ]


def test_execution_contract_and_input_remediation_plan_rejects_missing_checkpoint(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, create_checkpoint=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "fixed_dp_checkpoint_exists" in report["final_decision"]["failed_checks"]
    assert "fixed_dp_args_json_exists" in report["final_decision"]["failed_checks"]


def test_execution_contract_and_input_remediation_plan_rejects_existing_candidate_output(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, create_candidate_output=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_output_dir_not_created" in report["final_decision"]["failed_checks"]


def test_execution_contract_and_input_remediation_plan_rejects_premature_valid_set_list(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, create_valid_set_list=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "required_valid_set_list_missing_before_remediation" in report["final_decision"][
        "failed_checks"
    ]


def test_execution_contract_and_input_remediation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    checkpoint = _write(tmp_path / "fixed_dp" / "diffusion_planner.pth", "fixed")
    args_json = _write_json(tmp_path / "fixed_dp" / "diffusion_planner.param.json", {"device": "cuda"})
    artifact_dir = _artifact_dir(tmp_path / "execution_rejection_artifact")
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"

    exit_code = main(
        [
            "--execution_rejection_json",
            str(_execution_rejection(artifact_dir / "runner_execution.json")),
            "--execution_rejection_artifact_dir",
            str(artifact_dir),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--dp_repo",
            str(tmp_path),
            "--camp_repo",
            str(tmp_path),
            "--fixed_dp_checkpoint",
            str(checkpoint),
            "--fixed_dp_args_json",
            str(args_json),
            "--required_valid_set_list",
            str(tmp_path / "inputs" / "valid_set_list.json"),
            "--candidate_output_dir",
            str(tmp_path / "candidate_output"),
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
    assert "fixed_dp_execution_started_by_this_gate: `False`" in output_md.read_text(
        encoding="utf-8"
    )
