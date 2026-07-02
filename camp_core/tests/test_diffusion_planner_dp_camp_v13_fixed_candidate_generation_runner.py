from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.run_diffusion_planner_dp_camp_v13_fixed_candidate_generation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_PASS_STATUS,
    SOURCE_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "63c1cf37d0bf8631f24e83f85b81ae9cccd70c5b"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_implementation_static_"
    "contract_review_passed"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _review(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_PASS_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "entrypoint_contract_remediation_implementation_static_contract_review_passed": True,
        "entrypoint_contract_remediation_implementation_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {"schema_version": SOURCE_SCHEMA_VERSION, "final_decision": decision}
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "entrypoint_contract_remediation_implementation_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(tmp_path: Path) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    return camp_repo, dp_repo


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    mutation: Any | None = None,
    execute: bool = False,
    command: list[str] | None = None,
) -> dict[str, Any]:
    camp_repo, dp_repo = _repos(tmp_path)
    return build_report(
        implementation_static_contract_review_json=_review(
            tmp_path / "review.json",
            mutation=mutation,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        output_dir=tmp_path / "candidate_output",
        dp_command=command or ["python", "planner_generate.py"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        execute=execute,
    )


def test_runner_implementation_is_default_off_and_authorizes_post_review_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    runner = report["runner_contract"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["entrypoint_contract_remediation_implementation_complete"] is True
    assert (
        decision[
            "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next"
        ]
        is True
    )
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert runner["guard_env_var"] == GUARD_ENV_VAR
    assert "--write_zero_overlap_registries" in runner["planned_command"]
    assert "fixed DP candidate reranking only" in runner["planned_command"]
    assert SCORE_EXPRESSION in runner["planned_command"]


def test_runner_rejects_execute_in_implementation_gate(tmp_path: Path) -> None:
    report = _report(tmp_path, execute=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_is_default_off_for_this_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_runner_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_runner_rejects_source_action_leak(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_preflight_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_training_preflight_authorized_next" in report["final_decision"][
        "failed_checks"
    ]


def test_runner_rejects_forbidden_command_snippet(tmp_path: Path) -> None:
    report = _report(tmp_path, command=["python", "planner_generate.py", "--guidance"])

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_command_forbids_guidance" in report["final_decision"]["failed_checks"]


def test_runner_main_writes_outputs(tmp_path: Path) -> None:
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "runner.json"
    output_md = tmp_path / "runner.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(_review(tmp_path / "review.json")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--dp_repo",
            str(dp_repo),
            "--camp_repo",
            str(camp_repo),
            "--output_dir",
            str(tmp_path / "candidate_output"),
            "--dp_command",
            "python",
            "planner_generate.py",
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert GUARD_ENV_VAR in output_md.read_text(encoding="utf-8")
