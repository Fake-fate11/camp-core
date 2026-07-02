from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_remediation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    PASS_STATUS,
    PREFLIGHT_SCRIPT,
    REJECT_STATUS,
    REQUIRED_CONTRACT_CHANGES,
    REQUIRED_FUTURE_REVIEW_REQUIREMENTS,
    REQUIRED_PREFLIGHT_REQUIREMENTS,
    REQUIRED_RUNNER_REQUIREMENTS,
    RUNNER_SCRIPT,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "474430607555c4e1479e8005ce97ed56a10831af"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_runner_contract_remediation_"
    "implementation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _implementation_plan(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "runner_contract_remediation_implementation_plan_ready": True,
        "runner_contract_remediation_implementation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "runner_contract_remediation_implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "future_implementation_targets": [RUNNER_SCRIPT, PREFLIGHT_SCRIPT],
            "runner_owner_repo": "CAMP",
            "dp_repo_modification_allowed": False,
            "fixed_dp_candidate_generation_execution_authorized_by_this_gate": False,
            "training_authorized_by_this_gate": False,
            "required_contract_changes": list(REQUIRED_CONTRACT_CHANGES),
            "runner_implementation_requirements": list(REQUIRED_RUNNER_REQUIREMENTS),
            "preflight_implementation_requirements": list(REQUIRED_PREFLIGHT_REQUIREMENTS),
            "future_static_review_requirements": list(REQUIRED_FUTURE_REVIEW_REQUIREMENTS),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
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
                "RUNNER_IMPLEMENTATION_REQUIREMENTS",
                "PREFLIGHT_IMPLEMENTATION_REQUIREMENTS",
                "FUTURE_STATIC_REVIEW_REQUIREMENTS",
                "runner_contract_remediation_implementation_static_contract_review_authorized_next",
                "runner_contract_remediation_implementation_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "",
            ]
        ),
    )


def _plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_runner_contract_remediation_implementation_plan_authorizes_static_review_only",
                "test_runner_contract_remediation_implementation_plan_rejects_source_action_leak",
                "AUTHORIZED_NEXT_WORK",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "runner_contract_remediation_implementation_static_contract_review_authorized_next=True",
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
    artifact_dir = tmp_path / "implementation_plan_artifact"
    artifact_dir.mkdir(parents=True)
    return build_report(
        implementation_plan_json=_implementation_plan(
            artifact_dir / "implementation_plan.json", mutation=mutation
        ),
        implementation_plan_artifact_dir=artifact_dir,
        implementation_plan_script=_plan_script(tmp_path / "implementation_plan.py"),
        implementation_plan_test=_plan_test(tmp_path / "test_implementation_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_runner_contract_remediation_implementation_static_review_authorizes_implementation_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["implementation_static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runner_contract_remediation_implementation_static_contract_review_passed"] is True
    assert decision["runner_contract_remediation_implementation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["implementation_performed_by_source_plan"] is False
    assert review["future_implementation_targets"] == [RUNNER_SCRIPT, PREFLIGHT_SCRIPT]


def test_runner_contract_remediation_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_runner_contract_remediation_implementation_static_review_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_runner_contract_remediation_implementation_static_review_rejects_missing_target(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract_remediation_implementation_plan"]["future_implementation_targets"] = [
            RUNNER_SCRIPT
        ]

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        check.startswith("plan_targets_scripts_integrations_preflight_diffusion_planner")
        for check in report["final_decision"]["failed_checks"]
    )


def test_runner_contract_remediation_implementation_static_review_rejects_missing_runner_requirement(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract_remediation_implementation_plan"][
            "runner_implementation_requirements"
        ].remove("preserve_affine_score_and_nonnegative_simplex_boundaries")

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_requires_preserve_affine_score_and_nonnegative_simplex_boundaries" in report[
        "final_decision"
    ]["failed_checks"]


def test_runner_contract_remediation_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "implementation_plan_artifact"
    artifact_dir.mkdir()
    output_json = tmp_path / "implementation_static_review.json"
    output_md = tmp_path / "implementation_static_review.md"

    exit_code = main(
        [
            "--implementation_plan_json",
            str(_implementation_plan(artifact_dir / "implementation_plan.json")),
            "--implementation_plan_artifact_dir",
            str(artifact_dir),
            "--implementation_plan_script",
            str(_plan_script(tmp_path / "implementation_plan.py")),
            "--implementation_plan_test",
            str(_plan_test(tmp_path / "test_implementation_plan.py")),
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
    assert AUTHORIZED_NEXT_WORK in output_md.read_text(encoding="utf-8")
