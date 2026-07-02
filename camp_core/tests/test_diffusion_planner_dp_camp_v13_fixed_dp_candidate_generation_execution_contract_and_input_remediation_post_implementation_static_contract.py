from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract import (
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


CAMP_HEAD = "7f074a2ff4330338f411b94b622799d26acec29e"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_"
    "implementation_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _implementation(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_complete": True,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source_static_review": {
            "path": str(path.parent / "static_contract_review.json"),
            "schema_version": "source_static_review_v1",
            "status": "passed",
            "passed": True,
        },
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
                "/tmp/valid_set_list.json",
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


def _runner_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                GUARD_ENV_VAR,
                "EXECUTION_GATE_WORK",
                "VALID_DP_EXPORT_ENTRYPOINT",
                "_audit_authorization_value",
                "_audit_false_flags",
                "execute_requires_guard_env_var",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_complete",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_authorized_next",
                "fixed DP candidate reranking only",
                SCORE_EXPRESSION,
                "",
            ]
        ),
    )


def _preflight_script(path: Path, *, stale_source_contract: bool = False) -> Path:
    lines = [
        "contract_and_input_",
        "remediation_post_implementation_static_contract_review_v1",
        "remediation_implementation_v1",
        "--input_contract_json",
        "INPUT_CONTRACT_SCHEMA_VERSION",
        "INPUT_CONTRACT_READY_STATUS",
        "input_contract_valid_set_list_exists",
        "input_contract_fixed_dp_checkpoint_exists",
        "input_contract_fixed_dp_args_json_exists",
        "_base_dp_command(source_runner_planned_command, input_contract)",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed",
    ]
    if stale_source_contract:
        lines = [
            line
            for line in lines
            if line
            != "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed"
        ]
        lines.append("runner_contract_remediation_post_implementation_static_contract_review_passed")
    return _write(path, "\n".join(lines) + "\n")


def _materializer_script(path: Path, *, missing_zero_overlap: bool = False) -> Path:
    lines = [
        "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialization_v1",
        "fresh_nonformal_fixed_dp_npz",
        "valid_set_list.json",
        "FORBIDDEN_SOURCE_PATTERNS",
        "candidate_tensor_hash",
        "path_signature",
        "record_identity",
        "split_manifest_root",
        "closed_loop_outcome_read",
        "dp_modification",
        "fixed_dp_candidate_generation_executed",
        "candidate_generation_by_camp",
    ]
    if missing_zero_overlap:
        lines.remove("split_manifest_root")
    return _write(path, "\n".join(lines) + "\n")


def _runner_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_runner_accepts_execution_gate_audit_without_requiring_source_execution_auth",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_complete",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_authorized_next",
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
                "_input_contract",
                "--input_contract_json",
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed",
                "",
            ]
        ),
    )


def _materializer_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_materializer_writes_fixed_dp_input_contract_without_execution",
                "test_materializer_rejects_empty_source_list",
                "test_materializer_rejects_full36_formal_seed_and_closed_loop_sources",
                "test_materializer_rejects_unapproved_manifest_source",
                "test_materializer_main_writes_valid_set_list_and_report",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_authorized_next=True",
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
    stale_source_contract: bool = False,
    missing_zero_overlap: bool = False,
) -> dict[str, Any]:
    artifact_dir = tmp_path / "artifact"
    return build_report(
        implementation_json=_implementation(
            artifact_dir / "implementation.json",
            mutation=mutation,
        ),
        implementation_artifact_dir=artifact_dir,
        runner_script=_runner_script(tmp_path / "runner.py"),
        preflight_script=_preflight_script(
            tmp_path / "preflight.py",
            stale_source_contract=stale_source_contract,
        ),
        input_materializer_script=_materializer_script(
            tmp_path / "materializer.py",
            missing_zero_overlap=missing_zero_overlap,
        ),
        runner_test=_runner_test(tmp_path / "test_runner.py"),
        preflight_test=_preflight_test(tmp_path / "test_preflight.py"),
        input_materializer_test=_materializer_test(tmp_path / "test_materializer.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_contract_input_post_review_authorizes_execution_preflight_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["runner_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed"
        ]
        is True
    )
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["fixed_dp_export_entrypoint"] == VALID_DP_EXPORT_ENTRYPOINT
    assert review["guard_env_var"] == GUARD_ENV_VAR


def test_contract_input_post_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_contract_input_post_review_rejects_source_execution_leak(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_contract_input_post_review_rejects_stale_preflight_source_contract(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, stale_source_contract=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "preflight_script_contains_fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_impl"
        in report["final_decision"]["failed_checks"]
    )


def test_contract_input_post_review_rejects_missing_materializer_zero_overlap_key(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_zero_overlap=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "materializer_script_contains_split_manifest_root" in report["final_decision"][
        "failed_checks"
    ]


def test_contract_input_post_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Fixed-DP Execution Contract/Input Remediation Post-Implementation Static Review" in markdown
    assert "execution_preflight_authorized_next: `True`" in markdown
    assert "fixed_dp_generation_execution_authorized: `False`" in markdown
    assert "fixed_dp_generation_executed: `False`" in markdown
    assert "training_preflight_authorized: `False`" in markdown


def test_contract_input_post_review_main_writes_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact"
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--implementation_json",
            str(_implementation(artifact_dir / "implementation.json")),
            "--implementation_artifact_dir",
            str(artifact_dir),
            "--runner_script",
            str(_runner_script(tmp_path / "runner.py")),
            "--preflight_script",
            str(_preflight_script(tmp_path / "preflight.py")),
            "--input_materializer_script",
            str(_materializer_script(tmp_path / "materializer.py")),
            "--runner_test",
            str(_runner_test(tmp_path / "test_runner.py")),
            "--preflight_test",
            str(_preflight_test(tmp_path / "test_preflight.py")),
            "--input_materializer_test",
            str(_materializer_test(tmp_path / "test_materializer.py")),
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
        "# Fixed-DP Execution Contract/Input Remediation Post-Implementation Static Review"
    )
