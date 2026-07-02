from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_remediation_post_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    PASS_STATUS,
    REJECT_STATUS,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    VALID_DP_EXPORT_ENTRYPOINT,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "4a5d6e1a50fcf520dac308b229b83075cc585903"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_runner_contract_remediation_"
    "runner_implementation_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _runner_implementation(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "runner_contract_remediation_implementation_complete": True,
        "runner_contract_remediation_post_implementation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "runner_contract": {
            "runner_script": RUNNER_SCRIPT,
            "guard_env_var": GUARD_ENV_VAR,
            "fixed_dp_export_entrypoint": VALID_DP_EXPORT_ENTRYPOINT,
            "required_dp_export_args": [
                "--valid_set_list",
                "--resume_model_path",
                "--args_json_path",
                "--save_predictions_dir",
            ],
            "required_fixed_dp_head": FIXED_DP_HEAD,
            "forbid_full36": True,
            "forbidden_formal_seeds": ["11", "12", "13"],
            "write_zero_overlap_registries": True,
            "planned_command": [
                "python3",
                "-m",
                "torch.distributed.run",
                "--nnodes",
                "1",
                "--nproc-per-node",
                "1",
                "--standalone",
                VALID_DP_EXPORT_ENTRYPOINT,
                "--valid_set_list",
                "/tmp/valid_set_list.txt",
                "--resume_model_path",
                "/tmp/best_model.pth",
                "--args_json_path",
                "/tmp/args.json",
                "--save_predictions_dir",
                "/tmp/candidate_output",
            ],
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


def _runner_script(path: Path, *, stale_hard_reject: bool = False) -> Path:
    lines = [
        GUARD_ENV_VAR,
        "EXECUTION_GATE_WORK",
        "execute_requires_authorized_execution_gate",
        "execute_requires_guard_env_var",
        "argparse.REMAINDER",
        "VALID_DP_EXPORT_ENTRYPOINT",
        "--save_predictions_dir",
        "fixed DP candidate reranking only",
        SCORE_EXPRESSION,
        "FORBIDDEN_COMMAND_SNIPPETS",
    ]
    if stale_hard_reject:
        lines.append("runner_is_default_off_for_this_gate")
    return _write(path, "\n".join(lines) + "\n")


def _preflight_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "execution_preflight_runner_contract_remediation_",
                "post_implementation_static_contract_review_v1",
                "remediation_runner_implementation_v1",
                "EXECUTION_NEXT_WORK",
                "_without_option_value",
                "base_dp_command_strips_save_predictions_dir",
                VALID_DP_EXPORT_ENTRYPOINT,
                "--authorized_current_work",
                "--authorized_next_work",
                "",
            ]
        ),
    )


def _runner_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_runner_rejects_execute_in_implementation_gate",
                "execute_requires_authorized_execution_gate",
                VALID_DP_EXPORT_ENTRYPOINT,
                "--save_predictions_dir",
                "planned_command_forbids_guidance",
                "",
            ]
        ),
    )


def _preflight_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_execution_preflight_authorizes_fixed_dp_execution_only",
                "EXECUTION_NEXT_WORK",
                VALID_DP_EXPORT_ENTRYPOINT,
                "base_dp_command",
                "--save_predictions_dir",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "runner_contract_remediation_post_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    mutation: Any | None = None,
    stale_hard_reject: bool = False,
) -> dict[str, Any]:
    artifact_dir = tmp_path / "artifact"
    return build_report(
        runner_implementation_json=_runner_implementation(
            artifact_dir / "runner_implementation.json",
            mutation=mutation,
        ),
        runner_implementation_artifact_dir=artifact_dir,
        runner_script=_runner_script(tmp_path / "runner.py", stale_hard_reject=stale_hard_reject),
        preflight_script=_preflight_script(tmp_path / "preflight.py"),
        runner_test=_runner_test(tmp_path / "test_runner.py"),
        preflight_test=_preflight_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_runner_contract_post_review_authorizes_execution_preflight_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["runner_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runner_contract_remediation_post_implementation_static_contract_review_passed"] is True
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["fixed_dp_export_entrypoint"] == VALID_DP_EXPORT_ENTRYPOINT
    assert review["guard_env_var"] == GUARD_ENV_VAR


def test_runner_contract_post_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_runner_contract_post_review_rejects_source_execution_leak(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_runner_contract_post_review_rejects_stale_execute_hard_reject(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, stale_hard_reject=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_script_forbids_runner_is_default_off_for_this_gate" in report[
        "final_decision"
    ]["failed_checks"]


def test_runner_contract_post_review_rejects_planner_generate_placeholder(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract"]["planned_command"][8] = "planner_generate.py"

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_command_uses_valid_predictor" in report["final_decision"]["failed_checks"]
    assert "planned_command_does_not_use_planner_generate_placeholder" in report[
        "final_decision"
    ]["failed_checks"]


def test_runner_contract_post_review_rejects_missing_preflight_execution_gate(
    tmp_path: Path,
) -> None:
    def missing_preflight(path: Path) -> Path:
        return _write(path, "runner_contract_remediation_post_implementation_static_contract_review_v1\n")

    artifact_dir = tmp_path / "artifact"
    report = build_report(
        runner_implementation_json=_runner_implementation(
            artifact_dir / "runner_implementation.json"
        ),
        runner_implementation_artifact_dir=artifact_dir,
        runner_script=_runner_script(tmp_path / "runner.py"),
        preflight_script=missing_preflight(tmp_path / "preflight.py"),
        runner_test=_runner_test(tmp_path / "test_runner.py"),
        preflight_test=_preflight_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_script_contains_EXECUTION_NEXT_WORK" in report["final_decision"][
        "failed_checks"
    ]


def test_runner_contract_post_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Runner-Contract Remediation Post-Implementation Static Contract Review" in markdown
    assert "execution_preflight_authorized_next: `True`" in markdown
    assert "fixed_dp_generation_execution_authorized: `False`" in markdown
    assert "fixed_dp_generation_executed: `False`" in markdown
    assert "training_preflight_authorized: `False`" in markdown


def test_runner_contract_post_review_main_writes_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact"
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--runner_implementation_json",
            str(_runner_implementation(artifact_dir / "runner_implementation.json")),
            "--runner_implementation_artifact_dir",
            str(artifact_dir),
            "--runner_script",
            str(_runner_script(tmp_path / "runner.py")),
            "--preflight_script",
            str(_preflight_script(tmp_path / "preflight.py")),
            "--runner_test",
            str(_runner_test(tmp_path / "test_runner.py")),
            "--preflight_test",
            str(_preflight_test(tmp_path / "test_preflight.py")),
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Runner-Contract Remediation Post-Implementation Static Contract Review"
    )
