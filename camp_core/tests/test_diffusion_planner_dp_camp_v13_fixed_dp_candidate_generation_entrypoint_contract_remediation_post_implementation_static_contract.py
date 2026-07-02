from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_post_implementation_static_contract import (
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
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "64dbeef4b37f7ca79857918c152c7b6b3f55ac7e"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_runner_implementation_ready"
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
        "entrypoint_contract_remediation_implementation_complete": True,
        "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next": True,
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
            "planned_command": [
                "python",
                "planner_generate.py",
                "--output_dir",
                "/tmp/fixed_dp_candidates",
                "--fixed_dp_head",
                FIXED_DP_HEAD,
                "--candidate_operation",
                "fixed DP candidate reranking only",
                "--score_expression",
                SCORE_EXPRESSION,
                "--forbid_full36",
                "--forbid_formal_seeds",
                "11",
                "12",
                "13",
                "--write_zero_overlap_registries",
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
                "execute_fixed_dp_command",
                "runner_is_default_off_for_this_gate",
                "--forbid_full36",
                "--forbid_formal_seeds",
                "--write_zero_overlap_registries",
                "fixed DP candidate reranking only",
                SCORE_EXPRESSION,
                "FORBIDDEN_COMMAND_SNIPPETS",
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
                "test_runner_rejects_forbidden_command_snippet",
                "fixed_dp_candidate_generation_executed",
                "candidate_generation_by_camp_authorized",
                "training_preflight_authorized_next",
                "GUARD_ENV_VAR",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next=True",
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
) -> dict[str, Any]:
    artifact_dir = tmp_path / "artifact"
    return build_report(
        runner_implementation_json=_runner_implementation(
            artifact_dir / "entrypoint_contract_remediation_runner_implementation.json",
            mutation=mutation,
        ),
        runner_implementation_artifact_dir=artifact_dir,
        runner_script=_runner_script(tmp_path / "runner.py"),
        runner_test=_runner_test(tmp_path / "test_runner.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_post_implementation_static_review_authorizes_execution_preflight_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    runner = report["runner_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["entrypoint_contract_remediation_post_implementation_static_contract_review_passed"] is True
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert runner["guard_env_var"] == GUARD_ENV_VAR
    assert runner["runner_script"] == RUNNER_SCRIPT


def test_post_implementation_static_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_execution_leak(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_post_implementation_static_review_rejects_missing_guard(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract"]["guard_env_var"] = "UNGUARDED"

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_contract_guard_env" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_missing_zero_overlap_key(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract"]["required_zero_overlap_keys"].remove("record_identity")

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_contract_requires_zero_overlap_record_identity" in report[
        "final_decision"
    ]["failed_checks"]


def test_post_implementation_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Entrypoint Remediation Runner Post-Implementation Static Contract Review" in markdown
    assert "execution_preflight_authorized_next: `True`" in markdown
    assert "fixed_dp_generation_execution_authorized: `False`" in markdown
    assert "fixed_dp_generation_executed: `False`" in markdown
    assert "training_preflight_authorized: `False`" in markdown


def test_post_implementation_static_review_main_writes_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact"
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--runner_implementation_json",
            str(
                _runner_implementation(
                    artifact_dir / "entrypoint_contract_remediation_runner_implementation.json"
                )
            ),
            "--runner_implementation_artifact_dir",
            str(artifact_dir),
            "--runner_script",
            str(_runner_script(tmp_path / "runner.py")),
            "--runner_test",
            str(_runner_test(tmp_path / "test_runner.py")),
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
        "# Entrypoint Remediation Runner Post-Implementation Static Contract Review"
    )
