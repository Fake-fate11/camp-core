from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_member_source_generation_post_implementation_static_contract import (
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
CAMP_HEAD = "385ae216a706f83e4fc84efb247a597cab3dcb66"
BUILDER_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_camp_v13_default_off_member_source_generation.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_default_off_member_source_generation_builder.py"
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


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": "dp_camp_v13_default_off_member_source_generation_builder_complete",
        "passed": True,
        "failed_checks": [],
        "authorized_current_work": (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
            "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
            "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
            "failure_remediation_default_off_member_source_generation_implementation_only"
        ),
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "implementation_complete": True,
        "post_implementation_static_contract_review_authorized_next": True,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "training_executed": False,
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
    zero_counts = {
        "candidate_tensor_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }
    report = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_builder_v1",
        "final_decision": decision,
        "selection_summary": {
            "candidate_member_count": 2,
            "selected_member_count": 1,
            "rejected_member_count": 1,
            "rejected_reasons": {"candidate_tensor_hash_overlap": 1},
            "manifest_written": True,
            "zero_intersection_counts": zero_counts,
        },
    }
    manifest = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_manifest_v1",
        "members": [{"member_id": "fresh-a"}],
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "fixed_dp_candidate_generation_executed": False,
        "training_executed": False,
    }
    preflight_inputs = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_zero_overlap_preflight_inputs_v1",
        "zero_intersection_counts": zero_counts,
    }
    files = {
        "HEADS": f"camp_head={CAMP_HEAD}\ncamp_origin_main={CAMP_HEAD}\ndp_head={FIXED_DP_HEAD}\n",
        "COMMAND.sh": "#!/usr/bin/env bash\ntrue\n",
        "stdout.log": json.dumps(decision, sort_keys=True),
        "stderr.log": "",
        "run.exit": "0\n",
        "SHA256SUMS": "0" * 64 + "  HEADS\n",
        "SHA256SUMS.check.exit": "0\n",
        "default_off_member_source_generation_builder_report.md": "# report\n",
    }
    if mutation is not None:
        mutation(report, manifest, preflight_inputs, files)
    for name, text in files.items():
        _write(root / name, text)
    _write_json(root / "default_off_member_source_generation_builder_report.json", report)
    _write_json(
        root / "generated_outputs" / "default_off_member_source_generation_manifest.json",
        manifest,
    )
    _write_json(
        root / "generated_outputs" / "zero_overlap_preflight_inputs.json",
        preflight_inputs,
    )
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_default_off_member_source_generation_implementation_complete",
        "default_off_member_source_generation_post_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in [
        "fixed_dp_candidate_generation_authorized_next",
        "fresh_member_source_materialization_execution_authorized_next",
        "fresh_evaluation_split_evaluation_execution_authorized_next",
        "fresh_evaluation_split_evaluation_result_review_authorized_next",
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
        builder_script_py=BUILDER_SCRIPT,
        builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_post_static_review_authorizes_fixed_dp_candidate_generation_plan_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["fixed_dp_candidate_generation_plan_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["artifact_summary"]["selected_member_count"] == 1
    assert report["artifact_summary"]["zero_intersection_counts"] == {
        "candidate_tensor_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }


def test_post_static_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_artifact_failure(tmp_path: Path) -> None:
    def fail_artifact(
        report: dict[str, Any],
        manifest: dict[str, Any],
        preflight_inputs: dict[str, Any],
        files: dict[str, str],
    ) -> None:
        files["run.exit"] = "1\n"

    report = build_report(
        builder_script_py=BUILDER_SCRIPT,
        builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=fail_artifact),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_artifact_exit_zero" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_nonzero_selected_overlap(tmp_path: Path) -> None:
    def overlap(
        report: dict[str, Any],
        manifest: dict[str, Any],
        preflight_inputs: dict[str, Any],
        files: dict[str, str],
    ) -> None:
        report["selection_summary"]["zero_intersection_counts"][
            "candidate_tensor_hash_intersection_count"
        ] = 1

    report = build_report(
        builder_script_py=BUILDER_SCRIPT,
        builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=overlap),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "zero_candidate_tensor_hash_intersection_count" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_builder_contract_removal(tmp_path: Path) -> None:
    script = tmp_path / "builder.py"
    script.write_text(
        BUILDER_SCRIPT.read_text(encoding="utf-8").replace(
            "--enable_default_off_member_source_generation_builder",
            "--removed",
        ),
        encoding="utf-8",
    )

    report = build_report(
        builder_script_py=script,
        builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "builder_contains_enable_default_off_member_source_generation_builder"
        in report["final_decision"]["failed_checks"]
    )


def test_post_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "Fixed-DP candidate generation plan authorized next: `True`" in markdown
    assert "Fixed-DP candidate generation execution authorized next: `False`" in markdown
    assert "Training authorized next: `False`" in markdown
    assert "read-only" in markdown
    assert "safety/CAMP-over-DP claims" in markdown


def test_post_static_review_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"

    exit_code = main(
        [
            "--builder_script_py",
            str(BUILDER_SCRIPT),
            "--builder_test_py",
            str(BUILDER_TEST),
            "--implementation_artifact_dir",
            str(_artifact(tmp_path / "artifact")),
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
        "# Default-Off Member-Source Generation Post-Implementation Static Contract Review"
    )
