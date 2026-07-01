from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    MANIFEST_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_generation_report,
    main,
)


CAMP_HEAD = "485e41bf2ca1727edae65d688ef812333c488e36"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


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
        "status": "dp_camp_v13_fixed_dp_candidate_generation_implementation_static_contract_review_passed",
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_implementation_static_contract_review_passed": True,
        "fixed_dp_candidate_generation_implementation_authorized_next": True,
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
        "schema_version": (
            "dp_camp_v13_fixed_dp_candidate_generation_implementation_static_contract_review_v1"
        ),
        "review_contract": {
            "future_generator_script": (
                "scripts/integrations/build_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation.py"
            ),
            "target_min_candidate_members": 1024,
            "target_candidates_per_member": 8,
            "required_zero_overlap_keys": [
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


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_implementation_static_contract_review_passed",
        "fixed_dp_candidate_generation_implementation_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, enabled: bool = True) -> dict[str, Any]:
    return build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=enabled,
    )


def test_fixed_dp_candidate_generation_builder_writes_guarded_runbook(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    builder = report["generation_builder"]
    manifest_path = Path(report["output_paths"]["manifest"])
    runbook_path = Path(report["output_paths"]["runbook"])

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_implementation_complete"] is True
    assert decision["post_implementation_static_contract_review_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert builder["manifest_written"] is True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["fixed_dp_candidate_generation_executed"] is False
    assert manifest["candidate_generation_by_camp"] is False
    runbook = runbook_path.read_text(encoding="utf-8")
    assert GUARD_ENV_VAR in runbook
    assert "DP HEAD mismatch" in runbook
    assert "--forbid_formal_seeds 11 12 13" in runbook
    assert "--write_zero_overlap_registries" in runbook
    assert "camp_retraining" not in runbook.lower()


def test_fixed_dp_candidate_generation_builder_default_disabled(tmp_path: Path) -> None:
    report = _build(tmp_path, enabled=False)

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert "builder_enabled" in report["final_decision"]["failed_checks"]
    assert report["generation_builder"]["manifest_written"] is False


def test_fixed_dp_candidate_generation_builder_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_fixed_dp_candidate_generation_builder_rejects_generation_execution_auth(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = build_generation_report(
        implementation_static_contract_review_json=_review(
            tmp_path / "review.json",
            mutation=leak,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_fixed_dp_candidate_generation_builder_rejects_dp_head_mismatch(
    tmp_path: Path,
) -> None:
    report = build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="bad",
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fixed_dp_candidate_generation_builder_rejects_small_target(tmp_path: Path) -> None:
    report = build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        target_min_candidate_members=128,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "target_members_at_least_1000" in report["final_decision"]["failed_checks"]


def test_fixed_dp_candidate_generation_builder_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(_review(tmp_path / "review.json")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--output_dir",
            str(tmp_path / "out"),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_fixed_dp_candidate_generation_builder",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Fixed-DP Candidate Generation Builder"
    )
