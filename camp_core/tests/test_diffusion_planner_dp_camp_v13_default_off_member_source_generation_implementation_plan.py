from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_member_source_generation_implementation_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_GENERATOR_SCRIPT,
    LATEST_AUDIT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FUTURE_BEHAVIOR,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    build_report,
    main,
)


CAMP_HEAD = "4dc8d5ff709b56bc96de22dcc05aaea399c4271f"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_review(path: Path, *, mutation: Any | None = None) -> Path:
    decision: dict[str, Any] = {
        "atom_promotion_authorized": False,
        "authorized_current_work": (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
            "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
            "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
            "failure_remediation_default_off_member_source_generation_static_contract_review_only"
        ),
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_generation_by_camp_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "closed_loop_outcome_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "deployment_authorized": False,
        "dp_modification_authorized": False,
        "failed_checks": [],
        "fixed_dp_candidate_generation_authorized_next": False,
        "guidance_authorized": False,
        "implementation_plan_authorized_next": True,
        "passed": True,
        "postprocess_or_postselection_authorized": False,
        "reference_blend_authorized": False,
        "replay_execution_authorized_next": False,
        "safety_benefit_claim_authorized": False,
        "score_expression": "score_k(w)=a_k^T w",
        "selector_promotion_authorized": False,
        "status": (
            "dp_camp_v13_default_off_member_source_generation_"
            "static_contract_review_passed"
        ),
        "training_execution_authorized_next": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
    }
    payload = {
        "schema_version": (
            "dp_camp_v13_default_off_member_source_generation_"
            "static_contract_review_v1"
        ),
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _source_script(path: Path, *, include_contracts: bool = True) -> Path:
    snippets = [
        'fixed_dp_candidate_generation_authorized_next": False',
        'candidate_generation_by_camp_authorized": False',
        'training_execution_authorized_next": False',
        'dp_modification_authorized": False',
        'score_expression": SCORE_EXPRESSION',
    ]
    text = "\n".join(snippets if include_contracts else snippets[:-1])
    return _write(path, text + "\n")


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "implementation_plan_authorized_next",
                "fixed_dp_candidate_generation_authorized_next",
                "candidate_generation_by_camp_authorized",
                "training_execution_authorized_next",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "default_off_member_source_generation_implementation_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        static_contract_review_json=_source_review(tmp_path / "review.json"),
        static_contract_review_script=_source_script(tmp_path / "review.py"),
        static_contract_review_test=_source_test(tmp_path / "test_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_default_off_member_source_generation_implementation_plan_passes(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_ready"] is True
    assert decision["implementation_static_contract_review_authorized_next"] is True
    assert decision["implementation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["future_generator_script"] == FUTURE_GENERATOR_SCRIPT
    assert sorted(plan["required_future_behavior"]) == sorted(REQUIRED_FUTURE_BEHAVIOR)
    assert (
        plan["acceptance_summary"]["default_off_execution"]
        == "selected_index=0 and executed_index=0 for every record"
    )


def test_default_off_member_source_generation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_default_off_member_source_generation_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_authorized_next"] = True

    report = build_report(
        static_contract_review_json=_source_review(tmp_path / "review.json", mutation=leak),
        static_contract_review_script=_source_script(tmp_path / "review.py"),
        static_contract_review_test=_source_test(tmp_path / "test_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_fixed_dp_candidate_generation_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_default_off_member_source_generation_implementation_plan_rejects_missing_source_contract(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_contract_review_json=_source_review(tmp_path / "review.json"),
        static_contract_review_script=_source_script(
            tmp_path / "review.py",
            include_contracts=False,
        ),
        static_contract_review_test=_source_test(tmp_path / "test_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        name.startswith("source_script_contains_score_expression")
        for name in report["final_decision"]["failed_checks"]
    )


def test_default_off_member_source_generation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"

    exit_code = main(
        [
            "--static_contract_review_json",
            str(_source_review(tmp_path / "review.json")),
            "--static_contract_review_script",
            str(_source_script(tmp_path / "review.py")),
            "--static_contract_review_test",
            str(_source_test(tmp_path / "test_review.py")),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Implementation Plan" in output_md.read_text(encoding="utf-8")
    assert all(flag in SOURCE_FALSE_FLAGS for flag in SOURCE_FALSE_FLAGS)
