from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    INPUT_MATERIALIZER_SCRIPT,
    INPUT_MATERIALIZER_TEST,
    PASS_STATUS,
    PREFLIGHT_SCRIPT,
    PREFLIGHT_TEST,
    REJECT_STATUS,
    REQUIRED_IMPLEMENTATION_TARGETS,
    REQUIRED_INPUT_MATERIALIZER_REQUIREMENTS,
    REQUIRED_PLAN_SCRIPT_SNIPPETS,
    REQUIRED_PLAN_TEST_SNIPPETS,
    REQUIRED_PREFLIGHT_REQUIREMENTS,
    REQUIRED_RUNNER_REQUIREMENTS,
    REQUIRED_TEST_TARGETS,
    RUNNER_SCRIPT,
    RUNNER_TEST,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "0387ec128f797035a3b96872f31c8d5e0f72e1e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_implementation_"
    "plan_ready"
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
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_ready": True,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in SOURCE_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "fixed_dp_execution_started_by_this_gate": False,
            "implementation_targets": list(REQUIRED_IMPLEMENTATION_TARGETS),
            "test_targets": list(REQUIRED_TEST_TARGETS),
            "runner_requirements": list(REQUIRED_RUNNER_REQUIREMENTS),
            "preflight_requirements": list(REQUIRED_PREFLIGHT_REQUIREMENTS),
            "input_materializer_requirements": list(REQUIRED_INPUT_MATERIALIZER_REQUIREMENTS),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "dp_repo_modification_allowed": False,
            "candidate_generation_by_camp_allowed": False,
            "training_authorized": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _plan_script(path: Path) -> Path:
    return _write(path, "\n".join([*REQUIRED_PLAN_SCRIPT_SNIPPETS, ""]))


def _plan_test(path: Path) -> Path:
    return _write(path, "\n".join([*REQUIRED_PLAN_TEST_SNIPPETS, ""]))


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract_review_authorized_next=True",
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


def test_execution_contract_input_remediation_implementation_static_review_authorizes_implementation_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract_review_passed"
    ] is True
    assert decision[
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_authorized_next"
    ] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert RUNNER_SCRIPT in review["implementation_targets"]
    assert PREFLIGHT_SCRIPT in review["implementation_targets"]
    assert INPUT_MATERIALIZER_SCRIPT in review["implementation_targets"]
    assert RUNNER_TEST in review["test_targets"]
    assert PREFLIGHT_TEST in review["test_targets"]
    assert INPUT_MATERIALIZER_TEST in review["test_targets"]


def test_execution_contract_input_remediation_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_execution_contract_input_remediation_implementation_static_review_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_remediation_implementation_static_review_rejects_missing_materializer_requirement(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["input_materializer_requirements"] = [
            item
            for item in REQUIRED_INPUT_MATERIALIZER_REQUIREMENTS
            if item != "reject_full36_and_formal_seeds_11_12_13"
        ]

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_input_materializer_requirement_reject_full36_and_formal_seeds_11_12_13" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_contract_input_remediation_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "implementation_plan_artifact"
    artifact_dir.mkdir()
    output_json = tmp_path / "static_contract_review.json"
    output_md = tmp_path / "static_contract_review.md"

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
    assert "training_preflight_authorized: `False`" in output_md.read_text(encoding="utf-8")
