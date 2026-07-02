from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_implementation_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_RUNNER_SCRIPT,
    READY_STATUS,
    REJECT_STATUS,
    RUNNER_CONTRACT_REQUIREMENTS,
    SCHEMA_VERSION,
    SOURCE_DECISION_FALSE_FLAGS,
    SOURCE_PASS_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "db59e2462923d5b80d59f05119a223dabf54e937"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_static_contract_review_passed"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _static_review(
    path: Path,
    dp_repo: Path,
    *,
    mutation: Any | None = None,
) -> Path:
    decision = {
        "status": SOURCE_PASS_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "entrypoint_contract_remediation_static_contract_review_passed": True,
        "entrypoint_contract_remediation_implementation_plan_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_DECISION_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source_plan_summary": {
            "missing_entrypoint_path": str(
                dp_repo / "tools" / "camp_fixed_candidate_generation.py"
            ),
            "future_implementation_target": FUTURE_RUNNER_SCRIPT,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        },
        "static_contract_review": {
            "required_contract_groups": [
                "camp_owned_entrypoint_adapter_contract",
                "fixed_dp_read_only_contract",
                "zero_overlap_registry_contract",
            ],
            "entrypoint_contract": {
                "remediation_scope": "CAMP-owned entrypoint contract only",
                "dp_repo_modification_allowed": False,
            },
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _source_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "entrypoint_contract_remediation_implementation_plan_authorized_next",
                "entrypoint_contract_remediation_implementation_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "FUTURE_IMPLEMENTATION_TARGET",
                "score_expression",
                "",
            ]
        ),
    )


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "entrypoint_contract_remediation_implementation_plan_authorized_next",
                "entrypoint_contract_remediation_implementation_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "AUTHORIZED_NEXT_WORK",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "entrypoint_contract_remediation_implementation_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(tmp_path: Path, *, missing_entrypoint: bool = True) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    if not missing_entrypoint:
        _write(dp_repo / "tools" / "camp_fixed_candidate_generation.py", "unexpected\n")
    return camp_repo, dp_repo


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    mutation: Any | None = None,
    missing_entrypoint: bool = True,
) -> dict[str, Any]:
    camp_repo, dp_repo = _repos(tmp_path, missing_entrypoint=missing_entrypoint)
    return build_report(
        static_review_json=_static_review(tmp_path / "static_review.json", dp_repo, mutation=mutation),
        static_review_artifact_dir=tmp_path,
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )


def test_entrypoint_remediation_implementation_plan_authorizes_static_review_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["entrypoint_contract_remediation_implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["entrypoint_contract_remediation_implementation_plan_ready"] is True
    assert (
        decision[
            "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next"
        ]
        is True
    )
    assert decision["entrypoint_contract_remediation_implementation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["future_runner_script"] == FUTURE_RUNNER_SCRIPT
    assert plan["runner_owner_repo"] == "CAMP"
    assert plan["missing_dp_repo_entrypoint_will_not_be_created"] is True
    assert sorted(plan["runner_contract_requirements"]) == sorted(RUNNER_CONTRACT_REQUIREMENTS)
    assert plan["required_zero_overlap_keys"] == list(ZERO_OVERLAP_KEYS)


def test_entrypoint_remediation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_entrypoint_remediation_implementation_plan_rejects_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_entrypoint_remediation_implementation_plan_rejects_missing_zero_overlap_key(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["source_plan_summary"]["required_zero_overlap_keys"].remove("record_identity")

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_requires_zero_overlap_record_identity" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_implementation_plan_rejects_if_dp_entrypoint_exists(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_entrypoint=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_missing_dp_entrypoint_still_missing" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_review_json",
            str(_static_review(tmp_path / "static_review.json", dp_repo)),
            "--static_review_artifact_dir",
            str(tmp_path),
            "--static_review_script",
            str(_source_script(tmp_path / "static_review.py")),
            "--static_review_test",
            str(_source_test(tmp_path / "test_static_review.py")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
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
        ]
    )

    assert camp_repo.exists()
    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert payload["entrypoint_contract_remediation_implementation_plan"][
        "future_runner_script"
    ] == FUTURE_RUNNER_SCRIPT
    assert FUTURE_RUNNER_SCRIPT in output_md.read_text(encoding="utf-8")
