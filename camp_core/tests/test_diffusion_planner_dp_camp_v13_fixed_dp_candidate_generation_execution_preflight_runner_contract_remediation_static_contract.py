from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_remediation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_IMPLEMENTATION_TARGETS,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_PLAN_SCRIPT_SNIPPETS,
    REQUIRED_PLAN_TEST_SNIPPETS,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
    plan_script_to_review_script,
)


CAMP_HEAD = "197cf9cd0a71e432219ede1445aa4e51c04e4b21"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_runner_contract_remediation_plan_ready"
)
REQUIRED_CONTRACT_CHANGES = [
    "replace_runner_implementation_only_execute_rejection_with_execution_gate_check",
    "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
    "preserve_zero_overlap_registry_requirements",
    "require_guard_env_var_for_any_future_execution",
    "keep_affine_score_contract",
    "keep_nonexecution_gates_default_off",
]


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
        "runner_contract_remediation_plan_ready": True,
        "runner_contract_remediation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "runner_contract_remediation_plan": {
            "remediation_scope": "CAMP-owned runner contract and command validation only",
            "execution_authorized_by_this_gate": False,
            "fixed_dp_candidate_generation_authorized_by_this_gate": False,
            "training_authorized_by_this_gate": False,
            "dp_repo_modification_allowed": False,
            "dp_config_weight_checkpoint_change_allowed": False,
            "future_static_review_script": plan_script_to_review_script(),
            "future_implementation_targets": list(FUTURE_IMPLEMENTATION_TARGETS),
            "required_contract_changes": list(REQUIRED_CONTRACT_CHANGES),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _plan_script(path: Path, *, omit: str | None = None) -> Path:
    snippets = [snippet for snippet in REQUIRED_PLAN_SCRIPT_SNIPPETS if snippet != omit]
    return _write(path, "\n".join(snippets) + "\n")


def _plan_test(path: Path, *, omit: str | None = None) -> Path:
    snippets = [snippet for snippet in REQUIRED_PLAN_TEST_SNIPPETS if snippet != omit]
    return _write(path, "\n".join(snippets) + "\n")


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "runner_contract_remediation_plan_ready=True",
        "runner_contract_remediation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(
    tmp_path: Path,
    *,
    plan_mutation: Any | None = None,
    audit_target: str = AUTHORIZED_CURRENT_WORK,
    script_omit: str | None = None,
    test_omit: str | None = None,
) -> dict[str, Any]:
    artifact_dir = tmp_path / "plan_artifact"
    artifact_dir.mkdir(parents=True)
    return build_report(
        plan_json=_plan(artifact_dir / "runner_contract_remediation_plan.json", mutation=plan_mutation),
        plan_artifact_dir=artifact_dir,
        plan_script=_plan_script(tmp_path / "plan.py", omit=script_omit),
        plan_test=_plan_test(tmp_path / "test_plan.py", omit=test_omit),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_static_contract_review_authorizes_implementation_plan_only(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    contract = report["plan_static_contract"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_current_work"] == AUTHORIZED_CURRENT_WORK
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runner_contract_remediation_static_contract_review_passed"] is True
    assert decision["runner_contract_remediation_implementation_plan_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert contract["future_implementation_targets"] == list(FUTURE_IMPLEMENTATION_TARGETS)
    assert contract["required_contract_changes"] == REQUIRED_CONTRACT_CHANGES


def test_static_contract_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_source_execution_auth_leak(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _build(tmp_path, plan_mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_missing_implementation_target(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract_remediation_plan"]["future_implementation_targets"] = [
            FUTURE_IMPLEMENTATION_TARGETS[0]
        ]

    report = _build(tmp_path, plan_mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        check.startswith("plan_targets_scripts_integrations_preflight_diffusion_planner")
        for check in report["final_decision"]["failed_checks"]
    )


def test_static_contract_review_rejects_missing_required_contract_change(tmp_path: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["runner_contract_remediation_plan"]["required_contract_changes"] = [
            change for change in REQUIRED_CONTRACT_CHANGES if change != "keep_affine_score_contract"
        ]

    report = _build(tmp_path, plan_mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_requires_keep_affine_score_contract" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_plan_script_or_test_drift(tmp_path: Path) -> None:
    script_report = _build(
        tmp_path / "script",
        script_omit="replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
    )
    test_report = _build(
        tmp_path / "test",
        test_omit="test_runner_contract_remediation_plan_rejects_execution_auth_leak",
    )

    assert script_report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        check.startswith("plan_script_contains_replace_planner_generate_placeholder")
        for check in script_report["final_decision"]["failed_checks"]
    )
    assert test_report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "plan_test_contains_test_runner_contract_remediation_plan_rejects_execution_auth_leak"
        in test_report["final_decision"]["failed_checks"]
    )


def test_static_contract_review_main_writes_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "plan_artifact"
    artifact_dir.mkdir()
    output_json = tmp_path / "static_contract_review.json"
    output_md = tmp_path / "static_contract_review.md"

    exit_code = main(
        [
            "--plan_json",
            str(_plan(artifact_dir / "runner_contract_remediation_plan.json")),
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
    markdown = output_md.read_text(encoding="utf-8")
    assert "Runner Contract Remediation Static Contract Review" in markdown
    assert AUTHORIZED_NEXT_WORK in markdown
