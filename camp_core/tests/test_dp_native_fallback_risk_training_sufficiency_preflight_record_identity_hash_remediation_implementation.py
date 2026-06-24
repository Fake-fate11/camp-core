from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS,
    EXPECTED_VALIDATED_DATASET_SHA256,
    REJECT_STATUS,
    validate_training_sufficiency_preflight,
)


DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_implementation.md"
)
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_sufficiency_preflight.py"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
OLD_EXPECTED_DATASET_SHA = (
    "0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2"
)
NEW_EXPECTED_DATASET_SHA = (
    "8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9"
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path, *, dataset_sha: str) -> dict[str, Path]:
    train = ["log_a|run_0|0", "log_a|run_0|1"]
    validation = ["log_b|run_1|0"]
    atom_scales = {name: 1.0 for name in APPROVED_ATOM_NAMES}
    return {
        "validated_dataset_summary_json": _write_json(
            tmp_path / f"validated_dataset_{dataset_sha[:8]}.json",
            {
                "schema_version": "dp_native_fallback_risk_validated_dataset_summary_v1",
                "sha256": dataset_sha,
                "records": 15,
                "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
                "validator_passed": True,
                "training_sufficiency_claim": False,
                "deployable_checkpoint_claim": False,
            },
        ),
        "training_split_manifest_json": _write_json(
            tmp_path / "split.json",
            {
                "group_key_fields": ["source_log", "run_id", "record_index"],
                "training_groups": train,
                "validation_groups": validation,
                "seeds": [21, 22],
                "formal_eval_artifact_included": False,
            },
        ),
        "train_only_scale_manifest_json": _write_json(
            tmp_path / "scales.json",
            {
                "fit_groups": train,
                "fit_seeds": [21, 22],
                "formal_eval_artifact_included": False,
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "atom_scales": atom_scales,
            },
        ),
        "fallback_master_config_json": _write_json(
            tmp_path / "master.json",
            {
                "fallback_only": True,
                "feasible_branch_records_allowed": False,
                "all_infeasible_records_added_to_feasible_training": False,
                "all_infeasible_records_relabelled_feasible": False,
                "hard_feasibility_relaxation_authorized": False,
                "feasible_ranking_master_change_authorized": False,
                "score_expression": "score_k(w)=a_k^T w",
                "atoms_fixed_nonnegative": True,
                "fallback_label_is_deployed_atom": False,
                "margins_nonnegative": True,
                "simplex_cvar_l2_convex": True,
            },
        ),
        "training_command_plan_json": _write_json(
            tmp_path / "command.json",
            {
                "training_command_authorization": False,
                "post_training_nonpromotion_plan_required": True,
                "development_holdout_acceptance_gate_required": True,
                "replay_execution_authorized": False,
                "candidate_generation_authorized": False,
                "camp_training_authorized": False,
                "camp_retraining_authorized": False,
                "Full36_authorized": False,
                "formal_seeds_11_12_13_authorized": False,
                "dp_modification_authorized": False,
                "reference_blend_authorized": False,
                "guidance_authorized": False,
                "postprocess_postselection_authorized": False,
                "closed_loop_outcome_online_input_authorized": False,
                "selector_promotion_authorized": False,
                "atom_promotion_authorized": False,
                "deployable_checkpoint_claim_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
                "fallback_risk_training_authorized_now": False,
                "feasible_ranking_master_change_authorized": False,
                "hard_feasibility_relaxation_authorized": False,
                "all_infeasible_records_added_to_feasible_training": False,
                "production_selector_change_authorized": False,
                "online_selector_change_authorized": False,
            },
        ),
    }


def test_preflight_expected_dataset_sha_is_record_identity_remediated_artifact() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert EXPECTED_VALIDATED_DATASET_SHA256 == NEW_EXPECTED_DATASET_SHA
    assert NEW_EXPECTED_DATASET_SHA in source
    assert OLD_EXPECTED_DATASET_SHA not in source


def test_preflight_rejects_previous_fixed_artifact_dataset_sha(tmp_path: Path) -> None:
    report = validate_training_sufficiency_preflight(
        **_inputs(tmp_path, dataset_sha=OLD_EXPECTED_DATASET_SHA),
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["errors"] == ["validated_dataset_sha_mismatch"]
    assert report["final_decision"]["training_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized_now"] is False


def test_preflight_accepts_record_identity_dataset_without_authorizing_training(tmp_path: Path) -> None:
    report = validate_training_sufficiency_preflight(
        **_inputs(tmp_path, dataset_sha=NEW_EXPECTED_DATASET_SHA),
        enabled=True,
    )
    decision = report["final_decision"]

    assert decision["status"] == COMPLETE_STATUS
    assert decision["errors"] == []
    assert decision["ready_for_future_training_authorization"] is True
    assert decision["training_authorized"] is False
    assert decision["fallback_risk_training_authorized_now"] is False
    assert decision["camp_retraining_authorized_now"] is False
    assert decision["candidate_generation_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False


def test_remediation_audit_records_rejection_implementation_and_next_gate() -> None:
    text = DOC.read_text(encoding="utf-8")
    tail = "\n".join(ITERATION_AUDIT.read_text(encoding="utf-8").splitlines()[-190:])

    for needle in [
        "pre_remediation_commit=4c685823947767be9e2d5ef16fb96bf84f1a3035",
        "preflight_exit=1",
        "preflight_json_sha256=aa08865177199ce5da13f83be4d51c120146f78ace27c08b2f45d0204ddd81ef",
        "errors=['validated_dataset_sha_mismatch']",
        f"old_expected_validated_dataset_sha256={OLD_EXPECTED_DATASET_SHA}",
        f"new_expected_validated_dataset_sha256={NEW_EXPECTED_DATASET_SHA}",
        "scope=expected_dataset_sha_only",
        "local_preflight_remediation_pytest=4 passed",
        "local_preflight_and_affected_pytest=34 passed",
        "local_related_target_pytest=99 passed",
        "autodl_preflight_remediation_pytest=4 passed",
        "autodl_preflight_and_affected_pytest=34 passed",
        "autodl_related_target_pytest=99 passed",
        "status=fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_implemented",
        "old_expected_validated_dataset_sha_rejected=True",
        "new_expected_validated_dataset_sha_accepted_by_unit_contract=True",
        "training_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan_only`"
    )
