from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    EXECUTION_NEXT_WORK,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    READY_STATUS,
    REJECT_STATUS,
    REMEDIATION_NEXT_WORK,
    RUNNER_READY_STATUS,
    RUNNER_SCHEMA_VERSION,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "c21764469718734aac25e80d4cd08cadbf0547a9"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _runner_script(camp_repo: Path, *, hard_reject_execute: bool = False) -> Path:
    text = "\n".join(
        [
            "def execute_fixed_dp_command(command, dp_repo):",
            "    return None",
            (
                "runner_is_default_off_for_this_gate = True"
                if hard_reject_execute
                else "fixed_dp_candidate_generation_execution_gate_supported = True"
            ),
            "",
        ]
    )
    return _write(camp_repo / RUNNER_SCRIPT, text)


def _static_review(path: Path) -> Path:
    return _write_json(path, {"schema_version": "source_static_review_v1"})


def _input_contract(path: Path) -> Path:
    valid_set_list = _write_json(path.parent / "valid_set_list.json", {"files": ["/tmp/source.npz"]})
    checkpoint = _write(path.parent / "diffusion_planner.pth", "checkpoint")
    args_json = _write_json(path.parent / "diffusion_planner.args.json", {"model": "fixed_dp"})
    payload = {
        "schema_version": "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialization_v1",
        "input_contract": {
            "valid_set_list": str(valid_set_list),
            "valid_set_files": ["/tmp/source.npz"],
            "fixed_dp_checkpoint": str(checkpoint),
            "fixed_dp_args_json": str(args_json),
            "closed_loop_outcome_read": False,
            "dp_modification": False,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        },
        "final_decision": {
            "status": "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialized",
            "passed": True,
            "failed_checks": [],
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
        },
    }
    return _write_json(path, payload)


def _runner_implementation(
    path: Path,
    static_review: Path,
    *,
    mutation: Any | None = None,
) -> Path:
    planned_command = [
        "python",
        "-m",
        "torch.distributed.run",
        "--nnodes",
        "1",
        "--nproc-per-node",
        "1",
        "--standalone",
        "diffusion_planner/valid_predictor.py",
        "--valid_set_list",
        "/tmp/valid_set_list.txt",
        "--resume_model_path",
        "/tmp/best_model.pth",
        "--args_json_path",
        "/tmp/args.json",
        "--save_predictions_dir",
        str(path.parent / "candidate_output_not_created"),
    ]
    payload = {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "source_static_review": {
            "path": str(static_review),
            "schema_version": "source_static_review_v1",
            "status": "passed",
            "passed": True,
        },
        "runner_contract": {
            "runner_script": RUNNER_SCRIPT,
            "guard_env_var": GUARD_ENV_VAR,
            "planned_command": planned_command,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "required_fixed_dp_head": FIXED_DP_HEAD,
            "forbid_full36": True,
            "forbidden_formal_seeds": ["11", "12", "13"],
            "write_zero_overlap_registries": True,
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "dp_modification": False,
        },
        "final_decision": {
            "status": RUNNER_READY_STATUS,
            "passed": True,
            "failed_checks": [],
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _source_decision() -> dict[str, Any]:
    return {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed": True,
        "fixed_dp_candidate_generation_execution_preflight_authorized_next": True,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _post_review(path: Path, runner_json: Path, *, mutation: Any | None = None) -> Path:
    decision = _source_decision()
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source_runner_implementation": {
            "path": str(runner_json),
            "artifact_dir": str(runner_json.parent),
            "schema_version": RUNNER_SCHEMA_VERSION,
            "status": RUNNER_READY_STATUS,
            "passed": True,
        },
        "runner_contract_review": {
            "runner_script": RUNNER_SCRIPT,
            "guard_env_var": GUARD_ENV_VAR,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "dp_modification": False,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed=True",
        "fixed_dp_candidate_generation_execution_preflight_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(
    tmp_path: Path,
    *,
    command_entrypoint: bool = True,
    hard_reject_execute: bool = False,
) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    _runner_script(camp_repo, hard_reject_execute=hard_reject_execute)
    if command_entrypoint:
        _write(dp_repo / "diffusion_planner" / "valid_predictor.py", "print('fixed dp candidate export')\n")
    return camp_repo, dp_repo


def _report(
    tmp_path: Path,
    *,
    command_entrypoint: bool = True,
    hard_reject_execute: bool = False,
) -> dict[str, Any]:
    static_review = _static_review(tmp_path / "runner" / "static_review.json")
    input_contract = _input_contract(tmp_path / "inputs" / "input_contract.json")
    runner_json = _runner_implementation(tmp_path / "runner" / "runner.json", static_review)
    post_review = _post_review(tmp_path / "post_review.json", runner_json)
    camp_repo, dp_repo = _repos(
        tmp_path,
        command_entrypoint=command_entrypoint,
        hard_reject_execute=hard_reject_execute,
    )
    return build_report(
        post_review_json=post_review,
        input_contract_json=input_contract,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )


def test_execution_preflight_disabled_has_no_next_work(tmp_path: Path) -> None:
    report = build_report(
        post_review_json=tmp_path / "missing.json",
        input_contract_json=tmp_path / "missing_input_contract.json",
        v13_audit_md=tmp_path / "missing.md",
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=tmp_path / "dp",
        camp_repo=tmp_path / "camp",
        enabled=False,
    )

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["fixed_dp_candidate_generation_executed"] is False


def test_execution_preflight_authorizes_fixed_dp_execution_only(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    preflight = report["execution_preflight"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_execution_preflight_passed"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert preflight["base_dp_command"] == [
        "python",
        "-m",
        "torch.distributed.run",
        "--nnodes",
        "1",
        "--nproc-per-node",
        "1",
        "--standalone",
        "diffusion_planner/valid_predictor.py",
        "--valid_set_list",
        str(tmp_path / "inputs" / "valid_set_list.json"),
        "--resume_model_path",
        str(tmp_path / "inputs" / "diffusion_planner.pth"),
        "--args_json_path",
        str(tmp_path / "inputs" / "diffusion_planner.args.json"),
    ]
    assert preflight["base_dp_command_entrypoint_exists"] is True
    command = preflight["planned_command"]
    assert GUARD_ENV_VAR in " ".join(command)
    assert RUNNER_SCRIPT in " ".join(command).replace("\\", "/")
    assert "--execute" in command
    assert "--dp_command" in command
    assert FIXED_DP_HEAD in command
    assert AUTHORIZED_NEXT_WORK in command
    assert EXECUTION_NEXT_WORK in command
    source_command = preflight["source_runner_planned_command"]
    assert "diffusion_planner/valid_predictor.py" in source_command
    assert "--save_predictions_dir" in source_command
    assert "--save_predictions_dir" not in preflight["base_dp_command"]


def test_execution_preflight_rejects_missing_dp_command_entrypoint(tmp_path: Path) -> None:
    report = _report(tmp_path, command_entrypoint=False)
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert "base_dp_command_entrypoint_exists" in decision["failed_checks"]
    assert decision["authorized_next_work"] is None
    assert decision["recommended_next_work"] == REMEDIATION_NEXT_WORK
    assert decision["failure_class"] == "missing_fixed_dp_candidate_generation_command"
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False


def test_execution_preflight_rejects_runner_that_still_hard_rejects_execute(tmp_path: Path) -> None:
    report = _report(tmp_path, hard_reject_execute=True)
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert "runner_script_does_not_hard_reject_execute" in decision["failed_checks"]
    assert decision["failure_class"] == "runner_execution_contract_not_authorized"
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False


def test_execution_preflight_rejects_wrong_audit_target(tmp_path: Path) -> None:
    static_review = _static_review(tmp_path / "runner" / "static_review.json")
    input_contract = _input_contract(tmp_path / "inputs" / "input_contract.json")
    runner_json = _runner_implementation(tmp_path / "runner" / "runner.json", static_review)
    post_review = _post_review(tmp_path / "post_review.json", runner_json)
    camp_repo, dp_repo = _repos(tmp_path)

    report = build_report(
        post_review_json=post_review,
        input_contract_json=input_contract,
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] is False


def test_execution_preflight_rejects_source_execution_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    static_review = _static_review(tmp_path / "runner" / "static_review.json")
    input_contract = _input_contract(tmp_path / "inputs" / "input_contract.json")
    runner_json = _runner_implementation(tmp_path / "runner" / "runner.json", static_review)
    post_review = _post_review(tmp_path / "post_review.json", runner_json, mutation=leak)
    camp_repo, dp_repo = _repos(tmp_path)

    report = build_report(
        post_review_json=post_review,
        input_contract_json=input_contract,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_preflight_main_writes_reports_and_runbook(tmp_path: Path) -> None:
    static_review = _static_review(tmp_path / "runner" / "static_review.json")
    input_contract = _input_contract(tmp_path / "inputs" / "input_contract.json")
    runner_json = _runner_implementation(tmp_path / "runner" / "runner.json", static_review)
    post_review = _post_review(tmp_path / "post_review.json", runner_json)
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    output_runbook = tmp_path / "run.sh"

    exit_code = main(
        [
            "--post_review_json",
            str(post_review),
            "--input_contract_json",
            str(input_contract),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--candidate_output_dir",
            str(tmp_path / "candidate_output"),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--dp_repo",
            str(dp_repo),
            "--camp_repo",
            str(camp_repo),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_runbook",
            str(output_runbook),
            "--enable_fixed_dp_candidate_generation_execution_preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    runbook = output_runbook.read_text(encoding="utf-8")
    assert GUARD_ENV_VAR in runbook
    assert "DP HEAD mismatch" in runbook
    assert "Candidate output dir already exists" in runbook
    assert "--dp_command" in runbook
