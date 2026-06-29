from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "8827ed93917c24007f632f1ddc57447f7d949fb5"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result_readiness(path: Path, *, missing: str | None = None) -> Path:
    lines = [
        "SCHEMA_VERSION = 'dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_v2'",
        "FORMAL_SEEDS = {11, 12, 13}",
        "parser.add_argument('--split_manifest_json')",
        "parser.add_argument('--candidate_tensor_hash_registry_json')",
        "parser.add_argument('--path_signature_registry_json')",
        "parser.add_argument('--record_identity_hash_registry_json')",
        "previous_training_summary_json = None",
        "max_previous_overlap_rate = 0.0",
        "def _compare_candidate_tensor_hashes(): pass",
        "'split_manifest_training_holdout_root_intersection_zero'",
        "'split_manifest_formal_seed_records_zero'",
        "'candidate_tensor_hash_registry_intersection_zero'",
        "'path_signature_registry_intersection_zero'",
        "'record_identity_hash_registry_intersection_zero'",
        "'candidate_tensor_hash_registry_eval_values_complete'",
        "'record_identity_hash_registry_eval_values_complete'",
    ]
    if missing is not None:
        lines = [line for line in lines if missing not in line]
    return _write(path, "\n".join(lines) + "\n")


def _result_readiness_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "def test_result_readiness_rejects_split_manifest_overlap(): pass",
                "def test_result_readiness_rejects_formal_seed_in_split_manifest(): pass",
                "def test_result_readiness_rejects_candidate_tensor_registry_overlap(): pass",
                "def test_result_readiness_rejects_path_signature_registry_overlap(): pass",
                "def test_result_readiness_rejects_record_identity_registry_overlap(): pass",
                "",
            ]
        ),
    )


def _implementation_json(
    path: Path,
    *,
    result_readiness_py: Path,
    result_readiness_test_py: Path,
    mutation: Any | None = None,
) -> Path:
    payload = {
        "schema_version": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_implementation_v1"
        ),
        "status": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_implementation_complete"
        ),
        "source_hashes": {
            "result_readiness_script_sha256": _sha256(result_readiness_py),
            "result_readiness_test_sha256": _sha256(result_readiness_test_py),
        },
        "verification": {
            "target_pytest_passed": True,
            "target_pytest_count": 35,
        },
        "implemented_contracts": {
            "split_manifest_json_required_by_result_readiness": True,
            "candidate_tensor_hash_registry_json_required_by_result_readiness": True,
            "path_signature_registry_json_required_by_result_readiness": True,
            "record_identity_hash_registry_json_required_by_result_readiness": True,
            "train_holdout_split_intersection_must_be_zero": True,
            "candidate_tensor_train_eval_intersection_must_be_zero": True,
            "path_signature_train_eval_intersection_must_be_zero": True,
            "record_identity_train_eval_intersection_must_be_zero": True,
            "formal_seeds_11_12_13_rejected": True,
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "final_decision": {
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "training_executed": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write(path, json.dumps(payload))


def _audit(path: Path, *, next_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "## Current V13 Static DP-Reward Eval Plus Prior Non-Overlap Data Remediation Implementation After 8827ed93",
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_implementation_complete",
                "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_post_implementation_static_contract_review_authorized=True",
                "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )


def _report(tmp_path: Path, *, missing_source: str | None = None) -> dict[str, Any]:
    result_py = _result_readiness(tmp_path / "result_readiness.py", missing=missing_source)
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")
    implementation = _implementation_json(
        tmp_path / "implementation.json",
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
    )
    return build_report(
        implementation_json=implementation,
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_post_implementation_static_contract_review_authorizes_result_review_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["result_review_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False


def test_nonoverlap_post_implementation_static_contract_review_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    result_py = _result_readiness(tmp_path / "result_readiness.py")
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")
    report = build_report(
        implementation_json=_implementation_json(
            tmp_path / "implementation.json",
            result_readiness_py=result_py,
            result_readiness_test_py=result_test,
        ),
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
        v13_audit_md=_audit(tmp_path / "audit.md", next_work="old_gate"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work_target" in report["final_decision"]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_rejects_missing_cli_arg(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_source="record_identity_hash_registry_json")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "result_readiness_has_record_identity_hash_registry_json" in report[
        "final_decision"
    ]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_rejects_missing_zero_intersection_check(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_source="path_signature_registry_intersection_zero")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "result_readiness_has_path_signature_registry_intersection_zero" in report[
        "final_decision"
    ]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_rejects_source_hash_drift(
    tmp_path: Path,
) -> None:
    result_py = _result_readiness(tmp_path / "result_readiness.py")
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")
    implementation = _implementation_json(
        tmp_path / "implementation.json",
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
    )
    result_py.write_text(result_py.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
    report = build_report(
        implementation_json=implementation,
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "result_readiness_source_hash_matches_implementation" in report[
        "final_decision"
    ]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    result_py = _result_readiness(tmp_path / "result_readiness.py")
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")
    report = build_report(
        implementation_json=_implementation_json(
            tmp_path / "implementation.json",
            result_readiness_py=result_py,
            result_readiness_test_py=result_test,
        ),
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_rejects_training_auth(
    tmp_path: Path,
) -> None:
    result_py = _result_readiness(tmp_path / "result_readiness.py")
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")

    def authorize_training(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_executed"] = True

    report = build_report(
        implementation_json=_implementation_json(
            tmp_path / "implementation.json",
            result_readiness_py=result_py,
            result_readiness_test_py=result_test,
            mutation=authorize_training,
        ),
        result_readiness_py=result_py,
        result_readiness_test_py=result_test,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_executed" in report["final_decision"]["failed_checks"]


def test_nonoverlap_post_implementation_static_contract_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    result_py = _result_readiness(tmp_path / "result_readiness.py")
    result_test = _result_readiness_test(tmp_path / "test_result_readiness.py")
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"

    exit_code = main(
        [
            "--implementation_json",
            str(
                _implementation_json(
                    tmp_path / "implementation.json",
                    result_readiness_py=result_py,
                    result_readiness_test_py=result_test,
                )
            ),
            "--result_readiness_py",
            str(result_py),
            "--result_readiness_test_py",
            str(result_test),
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
    assert "read-only" in output_md.read_text(encoding="utf-8")
