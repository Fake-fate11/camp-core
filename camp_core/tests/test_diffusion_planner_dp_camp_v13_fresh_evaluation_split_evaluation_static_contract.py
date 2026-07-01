from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "0fe0037ad54773432dcefb05ba03bed5e2ec4cda"
PREFLIGHT_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v13_fresh_evaluation_split.py"
)
PREFLIGHT_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_preflight.py"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "dp_camp_v13_fresh_evaluation_split_preflight_v1",
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "preflight_result": {
            "all_required_intersections_zero": True,
            "selected_member_count": 32,
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "final_decision": {
            "status": "dp_camp_v13_fresh_evaluation_split_preflight_passed",
            "passed": True,
            "failed_checks": [],
            "failure_class": None,
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "fresh_evaluation_split_evaluation_authorized_next": True,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(report)
    _write(
        root / "HEADS",
        "\n".join(
            [
                f"camp_head={CAMP_HEAD}",
                f"camp_origin_main={CAMP_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(root / "COMMAND", "python preflight\n")
    _write(root / "run.exit", "0\n")
    _write(root / "stdout.txt", "{}\n")
    _write(root / "stderr.txt", "")
    _write_json(root / "fresh_evaluation_split_preflight_report.json", report)
    _write(root / "fresh_evaluation_split_preflight_report.md", "# ok\n")
    _write(root / "SHA256SUMS.artifact", "0" * 64 + "  HEADS\n")
    _write(root / "SHA256SUMS_artifact.check.exit", "0\n")
    _write(root / "SHA256SUMS_artifact.check.stdout", "HEADS: OK\n")
    _write(root / "SHA256SUMS_artifact.check.stderr", "")
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation_fresh_evaluation_split_preflight_passed",
        "fresh_evaluation_split_evaluation_static_contract_review_authorized_next=True",
        "all_required_intersections_zero=True",
        "data_preparation_authorized_next=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_or_postselection_authorized=False",
        "closed_loop_outcome_authorized=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK, mutation: Any | None = None) -> dict[str, Any]:
    return build_report(
        preflight_artifact_dir=_artifact(tmp_path / "artifact", mutation=mutation),
        preflight_script_py=PREFLIGHT_SCRIPT,
        preflight_test_py=PREFLIGHT_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_evaluation_static_contract_review_passes(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_evaluation_plan_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["preflight_result"]["all_required_intersections_zero"] is True


def test_fresh_evaluation_split_evaluation_static_contract_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="wrong_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fresh_evaluation_split_evaluation_static_contract_review_rejects_training_leak(tmp_path: Path) -> None:
    def mutate(report: dict[str, Any]) -> None:
        report["final_decision"]["training_execution_authorized_next"] = True

    report = _build(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_training_execution_false" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_evaluation_static_contract_review_main_writes_report(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
    artifact = _artifact(tmp_path / "artifact")
    audit = _audit(tmp_path / "audit.md")

    exit_code = main(
        [
            "--preflight_artifact_dir",
            str(artifact),
            "--preflight_script_py",
            str(PREFLIGHT_SCRIPT),
            "--preflight_test_py",
            str(PREFLIGHT_TEST),
            "--v13_audit_md",
            str(audit),
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
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert "read-only" in output_md.read_text(encoding="utf-8")
