from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_failure_remediation import (
    ABSENCE_SCAN_SCHEMA_VERSION,
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FAILED_CHECKS,
    SCHEMA_VERSION,
    SOURCE_REJECT_STATUS,
    SOURCE_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "506018adfeb440a0d739d72833ec914853ccf5a1"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_rejected_missing_candidate_member_"
    "source_manifest"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "candidate_member_source_manifest_missing=True",
        "training_split_manifest_root_registry_missing=True",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _materialization_payload(*, mutation: Any | None = None) -> dict[str, Any]:
    decision = {
        "status": SOURCE_REJECT_STATUS,
        "passed": False,
        "authorized_next_work": None,
        "materialization_complete": False,
        "member_source_manifest_written": False,
        "failed_checks": list(REQUIRED_FAILED_CHECKS),
        "validation_preflight_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_executed": False,
        "trajectory_generation_by_camp_executed": False,
        "trajectory_modification_by_camp_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "final_decision": decision,
        "source_summaries": {
            "candidate_member_source_manifest": {
                "schema_version": None,
                "candidate_member_count": 0,
            },
            "training_registries": {
                "label": "training",
                "candidate_tensor_hash_count": 28580,
                "path_signature_count": 352,
                "record_identity_hash_count": 35200,
                "split_manifest_root_count": 0,
            },
            "recovered_prior_registry": {
                "label": "recovered_prior",
                "candidate_tensor_hash_count": 31060,
                "path_signature_count": 384,
                "record_identity_hash_count": 38400,
                "split_manifest_root_count": 528,
            },
            "rejected_overlap_source_registry": {
                "label": "rejected_overlap_source",
                "candidate_tensor_hash_count": 28600,
                "path_signature_count": 372,
                "record_identity_hash_count": 35220,
                "split_manifest_root_count": 611,
            },
        },
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _absence_payload(*, structures_found: int = 0) -> dict[str, Any]:
    return {
        "schema_version": ABSENCE_SCAN_SCHEMA_VERSION,
        "scan_root": "/root/autodl-tmp",
        "max_json_size_bytes": 20000000,
        "candidate_member_source_manifest_structures_found": structures_found,
        "matches": [],
    }


def _script_text() -> str:
    return "\n".join(
        [
            "candidate_member_source_manifest_json",
            "training_split_manifest_root_registry_json",
            "fresh_member_source_candidates_after_filters_nonempty",
            "reject_split_root_only_acceptance",
            "exclude_formal_seeds_11_12_13_and_full36",
            "exclude_every_member_from_the_rejected_overlap_source",
            "SCORE_EXPRESSION",
            "score_k(w)=a_k^T w",
        ]
    )


def _inputs(
    tmp_path: Path,
    *,
    materialization_mutation: Any | None = None,
    absence_structures_found: int = 0,
    audit_target: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Any]:
    rejection = _write_json(
        tmp_path / "materialization_report.json",
        _materialization_payload(mutation=materialization_mutation),
    )
    absence = _write_json(
        tmp_path / "candidate_member_source_manifest_absence_scan.json",
        _absence_payload(structures_found=absence_structures_found),
    )
    return {
        "materialization_rejection_json": rejection,
        "expected_materialization_rejection_sha256": _sha256(rejection),
        "candidate_member_source_manifest_absence_scan_json": absence,
        "expected_absence_scan_sha256": _sha256(absence),
        "materializer_script_py": _write(tmp_path / "materializer.py", _script_text()),
        "builder_script_py": _write(tmp_path / "builder.py", _script_text()),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=audit_target),
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_materialization_failure_remediation_plan_ready_without_executing() -> None:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        report = _report(Path(tmp))

    decision = report["final_decision"]
    plan = report["remediation_plan"]
    summary = report["materialization_rejection_summary"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_failure_remediation_plan_ready"] is True
    assert decision["materialization_failure_remediation_implementation_plan_authorized_next"] is True
    assert decision["materialization_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert summary["candidate_member_source_manifest_structures_found"] == 0
    assert summary["candidate_member_count"] == 0
    assert summary["training_split_manifest_root_count"] == 0
    assert plan["failure_attribution"]["candidate_member_source_manifest_missing"] is True
    assert plan["failure_attribution"]["training_split_manifest_root_registry_missing"] is True
    assert plan["failure_attribution"]["rejected_materialization_is_not_holdout"] is True
    assert plan["training_split_root_registry_contract"]["nonempty_registry_required"] is True
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["master_problem_remains_convex"] is True


def test_materialization_failure_remediation_plan_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, audit_target="stale_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["training_execution_authorized_next"] is False


def test_materialization_failure_remediation_plan_rejects_action_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_execution_authorized_next"] = True

    report = _report(tmp_path, materialization_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_training_execution_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_failure_remediation_plan_rejects_sha_mismatch(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    inputs["expected_materialization_rejection_sha256"] = "0" * 64

    report = build_report(
        **inputs,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "materialization_rejection_sha256" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_plan_rejects_nonzero_absence_scan(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, absence_structures_found=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "absence_scan_structures_found_zero" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_plan_main_writes_outputs(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    output_json = tmp_path / "out" / "failure_remediation_plan.json"
    output_md = tmp_path / "out" / "failure_remediation_plan.md"

    exit_code = main(
        [
            "--materialization_rejection_json",
            str(inputs["materialization_rejection_json"]),
            "--expected_materialization_rejection_sha256",
            inputs["expected_materialization_rejection_sha256"],
            "--candidate_member_source_manifest_absence_scan_json",
            str(inputs["candidate_member_source_manifest_absence_scan_json"]),
            "--expected_absence_scan_sha256",
            inputs["expected_absence_scan_sha256"],
            "--materializer_script_py",
            str(inputs["materializer_script_py"]),
            "--builder_script_py",
            str(inputs["builder_script_py"]),
            "--v13_audit_md",
            str(inputs["v13_audit_md"]),
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
    assert "Required Remediation" in output_md.read_text(encoding="utf-8")
