from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "dbfbdf53aa1d4f31da94fb73df62e7143afdd99d"
PLAN_SCRIPT = (
    REPO_ROOT / "scripts" / "integrations" / "plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation.py"
)
PLAN_TEST = (
    REPO_ROOT / "camp_core" / "tests" / "test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_plan.py"
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


def _plan(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": "dp_camp_v13_fixed_dp_candidate_generation_plan_ready",
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_static_contract_review_authorized_next": True,
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
    }
    payload = {
        "schema_version": "dp_camp_v13_fixed_dp_candidate_generation_plan_v1",
        "final_decision": decision,
        "fixed_dp_candidate_generation_plan": {
            "target_min_candidate_members": 1024,
            "target_candidates_per_member": 8,
            "target_candidate_members_range": "hundreds_to_thousands",
            "candidate_source": "fixed Diffusion Planner candidate tensor only",
            "allowed_execution_engine": "Diffusion-Planner at fixed commit",
            "required_dp_head": FIXED_DP_HEAD,
            "execution_authorized_by_this_gate": False,
            "zero_overlap_required_against_training_registries": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _artifact_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "HEADS", f"camp_head={CAMP_HEAD}\ndp_head={FIXED_DP_HEAD}\n")
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_plan_ready",
        "fixed_dp_candidate_generation_static_contract_review_authorized_next=True",
    ]
    for flag in [
        "fixed_dp_candidate_generation_authorized_next",
        "fixed_dp_candidate_generation_execution_authorized_next",
        "fresh_member_source_materialization_execution_authorized_next",
        "fresh_evaluation_split_evaluation_execution_authorized_next",
        "data_preparation_authorized_next",
        "training_preflight_authorized_next",
        "training_execution_authorized_by_current_boundary",
        "runtime_shadow_selector_execution_authorized",
        "replay_execution_authorized_by_current_boundary",
        "fixed_dp_candidate_generation_authorized_by_current_boundary",
        "candidate_generation_by_camp_authorized_by_current_boundary",
        "trajectory_generation_by_camp_authorized_by_current_boundary",
        "trajectory_modification_by_camp_authorized_by_current_boundary",
        "dp_modification_authorized_by_current_boundary",
        "formal_seed_11_12_13_execution_authorized",
        "reference_blend_authorized",
        "guidance_authorized",
        "postprocess_or_postselection_authorized",
        "closed_loop_outcome_authorized",
        "online_selector_change_authorized",
        "executed_trajectory_change_authorized",
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "deployable_checkpoint_claim_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ]:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        plan_json=_plan(tmp_path / "plan.json"),
        plan_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        plan_script_py=PLAN_SCRIPT,
        plan_test_py=PLAN_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_static_contract_review_authorizes_implementation_plan_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_static_contract_review_passed"] is True
    assert decision["fixed_dp_candidate_generation_implementation_plan_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["source_plan"]["target_min_candidate_members"] == 1024
    assert report["source_plan"]["target_candidates_per_member"] == 8


def test_static_contract_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_generation_execution_auth(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = build_report(
        plan_json=_plan(tmp_path / "plan.json", mutation=leak),
        plan_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        plan_script_py=PLAN_SCRIPT,
        plan_test_py=PLAN_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_small_plan_target(tmp_path: Path) -> None:
    def small(payload: dict[str, Any]) -> None:
        payload["fixed_dp_candidate_generation_plan"]["target_min_candidate_members"] = 128

    report = build_report(
        plan_json=_plan(tmp_path / "plan.json", mutation=small),
        plan_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        plan_script_py=PLAN_SCRIPT,
        plan_test_py=PLAN_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_target_members_at_least_1000" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_missing_zero_overlap_key(tmp_path: Path) -> None:
    def missing(payload: dict[str, Any]) -> None:
        payload["fixed_dp_candidate_generation_plan"][
            "zero_overlap_required_against_training_registries"
        ].remove("record_identity")

    report = build_report(
        plan_json=_plan(tmp_path / "plan.json", mutation=missing),
        plan_artifact_dir=_artifact_dir(tmp_path / "artifact"),
        plan_script_py=PLAN_SCRIPT,
        plan_test_py=PLAN_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_requires_zero_overlap_record_identity" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Fixed-DP Candidate Generation Static Contract Review" in markdown
    assert "Fixed-DP generation execution authorized next: `False`" in markdown
    assert "CAMP candidate generation authorized: `False`" in markdown
    assert "Training authorized next: `False`" in markdown
    assert "static-only" in markdown


def test_static_contract_review_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--plan_json",
            str(_plan(tmp_path / "plan.json")),
            "--plan_artifact_dir",
            str(_artifact_dir(tmp_path / "artifact")),
            "--plan_script_py",
            str(PLAN_SCRIPT),
            "--plan_test_py",
            str(PLAN_TEST),
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
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Fixed-DP Candidate Generation Static Contract Review"
    )
