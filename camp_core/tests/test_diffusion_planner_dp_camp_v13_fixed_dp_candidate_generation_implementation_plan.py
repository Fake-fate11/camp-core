from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_implementation_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_GENERATOR_SCRIPT,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FUTURE_BEHAVIOR,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "8452d64a4d9db2bcd4b47fdbcd21ff9817d728dd"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_review(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": "dp_camp_v13_fixed_dp_candidate_generation_static_contract_review_passed",
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_static_contract_review_passed": True,
        "fixed_dp_candidate_generation_implementation_plan_authorized_next": True,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
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
    payload = {
        "schema_version": "dp_camp_v13_fixed_dp_candidate_generation_static_contract_review_v1",
        "source_plan": {
            "target_min_candidate_members": 1024,
            "target_candidates_per_member": 8,
            "zero_overlap_required_against_training_registries": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _artifact_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "HEADS", f"camp_head={CAMP_HEAD}\ndp_head={FIXED_DP_HEAD}\n")
    return root


def _source_script(path: Path, *, include_score: bool = True) -> Path:
    snippets = [
        "fixed_dp_candidate_generation_implementation_plan_authorized_next",
        'fixed_dp_candidate_generation_execution_authorized_next": False',
        'candidate_generation_by_camp_authorized": False',
        'training_preflight_authorized_next": False',
        'training_execution_authorized_next": False',
        'dp_modification_authorized": False',
    ]
    if include_score:
        snippets.append('score_expression": SCORE_EXPRESSION')
    return _write(path, "\n".join(snippets) + "\n")


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "fixed_dp_candidate_generation_implementation_plan_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "training_preflight_authorized_next",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_static_contract_review_passed",
        "fixed_dp_candidate_generation_implementation_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        static_review_json=_source_review(tmp_path / "static_review.json"),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fixed_dp_candidate_generation_implementation_plan_authorizes_static_review_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_implementation_plan_ready"] is True
    assert (
        decision["fixed_dp_candidate_generation_implementation_static_contract_review_authorized_next"]
        is True
    )
    assert decision["fixed_dp_candidate_generation_implementation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["future_generator_script"] == FUTURE_GENERATOR_SCRIPT
    assert sorted(plan["required_future_behavior"]) == sorted(REQUIRED_FUTURE_BEHAVIOR)
    assert plan["target_min_candidate_members"] == 1024
    assert plan["required_zero_overlap_keys"] == [
        "candidate_tensor_hash",
        "path_signature",
        "record_identity",
        "split_manifest_root",
    ]


def test_fixed_dp_candidate_generation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fixed_dp_candidate_generation_implementation_plan_rejects_execution_auth_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = build_report(
        static_review_json=_source_review(tmp_path / "static_review.json", mutation=leak),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_fixed_dp_candidate_generation_implementation_plan_accepts_legacy_missing_optional_flags(
    tmp_path: Path,
) -> None:
    def legacy(payload: dict[str, Any]) -> None:
        for flag in [
            "reference_blend_authorized",
            "guidance_authorized",
            "postprocess_or_postselection_authorized",
            "closed_loop_outcome_authorized",
            "deployable_checkpoint_claim_authorized",
        ]:
            payload["final_decision"].pop(flag)

    report = build_report(
        static_review_json=_source_review(tmp_path / "static_review.json", mutation=legacy),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == READY_STATUS


def test_fixed_dp_candidate_generation_implementation_plan_rejects_optional_boundary_true(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["guidance_authorized"] = True

    report = build_report(
        static_review_json=_source_review(tmp_path / "static_review.json", mutation=leak),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_does_not_authorize_guidance_authorized" in report["final_decision"][
        "failed_checks"
    ]


def test_fixed_dp_candidate_generation_implementation_plan_rejects_missing_source_contract(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_review_json=_source_review(tmp_path / "static_review.json"),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py", include_score=False),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
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


def test_fixed_dp_candidate_generation_implementation_plan_rejects_small_source_target(
    tmp_path: Path,
) -> None:
    def small(payload: dict[str, Any]) -> None:
        payload["source_plan"]["target_min_candidate_members"] = 128

    report = build_report(
        static_review_json=_source_review(tmp_path / "static_review.json", mutation=small),
        static_review_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        static_review_script=_source_script(tmp_path / "static_review.py"),
        static_review_test=_source_test(tmp_path / "test_static_review.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_target_members_at_least_1000" in report["final_decision"]["failed_checks"]


def test_fixed_dp_candidate_generation_implementation_plan_markdown_boundary(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Fixed-DP Candidate Generation Implementation Plan" in markdown
    assert "Implementation performed by this gate: `False`" in markdown
    assert "Fixed-DP generation execution authorized next: `False`" in markdown
    assert "CAMP candidate generation authorized: `False`" in markdown
    assert "Training preflight authorized next: `False`" in markdown


def test_fixed_dp_candidate_generation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"

    exit_code = main(
        [
            "--static_review_json",
            str(_source_review(tmp_path / "static_review.json")),
            "--static_review_artifact_dir",
            str(_artifact_dir(tmp_path / "artifact")),
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
    assert payload["implementation_plan"]["future_generator_script"] == FUTURE_GENERATOR_SCRIPT
    assert "Implementation Plan" in output_md.read_text(encoding="utf-8")
    assert all(flag in SOURCE_FALSE_FLAGS for flag in SOURCE_FALSE_FLAGS)
