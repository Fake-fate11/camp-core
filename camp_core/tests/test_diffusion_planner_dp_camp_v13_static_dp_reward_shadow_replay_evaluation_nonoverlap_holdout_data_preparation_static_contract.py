from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_holdout_data_preparation import (
    AUTHORIZED_CURRENT_WORK as PLAN_AUTHORIZED_CURRENT_WORK,
    FIXED_DP_HEAD,
    build_report as build_plan_report,
)
from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    TARGET_HOLDOUT_RECORDS,
    build_report,
    main,
)


CAMP_HEAD = "e03c127c0916cea5ef46d7eb5d5d92d834b4b096"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _result_readiness(path: Path) -> Path:
    return _write(
        path,
        json.dumps(
            {
                "schema_version": (
                    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                    "result_readiness_v2"
                ),
                "analysis": {
                    "candidate_operation": "fixed DP candidate reranking only",
                    "score_expression": "score_k(w)=a_k^T w",
                },
                "candidate_tensor_hash_registry": {"intersection_count": 2180},
                "candidate_tensor_overlap": {
                    "intersection_unique_hash_count": 2180,
                    "unique_intersection_rate": 0.68,
                },
                "path_signature_registry": {"intersection_count": 32},
                "record_identity_hash_registry": {"intersection_count": 3200},
                "split_manifest": {"formal_holdout_seeds": [], "formal_training_seeds": []},
                "source_paths": {
                    "previous_training_summary_json": "/tmp/training_summary.json",
                    "previous_training_output_dir": "/tmp/training",
                    "evaluation_output_dir": "/tmp/evaluation",
                    "split_manifest_json": "/tmp/split_manifest.json",
                    "candidate_tensor_hash_registry_json": "/tmp/candidate_registry.json",
                    "path_signature_registry_json": "/tmp/path_registry.json",
                    "record_identity_hash_registry_json": "/tmp/record_registry.json",
                },
                "training_readiness": {
                    "records_total": 3200,
                    "selection_log_count": 32,
                    "candidate_count_values": {"8": 3200},
                    "atom_count_values": {"14": 3200},
                },
                "final_decision": {
                    "status": (
                        "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                        "result_readiness_rejected"
                    ),
                    "passed": False,
                    "failed_checks": [
                        "candidate_tensor_hash_registry_intersection_zero",
                        "path_signature_registry_intersection_zero",
                        "record_identity_hash_registry_intersection_zero",
                        "candidate_tensor_overlap_rate_within_limit",
                    ],
                    "authorized_next_work": None,
                    "static_dp_reward_training_preflight_authorized_next": False,
                    "static_dp_reward_training_execution_authorized_next": False,
                    "replay_executed": False,
                    "training_executed": False,
                    "candidate_generation_executed": False,
                    "candidate_generation_by_camp_authorized": False,
                    "trajectory_generation_by_camp_authorized": False,
                    "trajectory_modification_by_camp_authorized": False,
                    "dp_modification_authorized": False,
                    "selector_promotion_authorized": False,
                    "atom_promotion_authorized": False,
                    "deployment_authorized": False,
                    "safety_benefit_claim_authorized": False,
                    "camp_over_dp_top1_claim_authorized": False,
                },
            }
        ),
    )


def _plan_audit(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_result_review_rejected_nonoverlap_registry_overlap_with_prior_training",
                f"next_work_target={PLAN_AUTHORIZED_CURRENT_WORK}",
                "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_modification_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "selector_promotion_authorized=False",
                "atom_promotion_authorized=False",
                "deployment_authorized=False",
                "safety_benefit_claim_authorized=False",
                "camp_over_dp_top1_claim_authorized=False",
                "",
            ]
        ),
    )


def _review_audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_plan_ready",
                f"next_work_target={current_work}",
                "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "safety_benefit_claim_authorized=False",
                "",
            ]
        ),
    )


def _script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "TARGET_HOLDOUT_RECORDS = 12800",
                "TARGET_HOLDOUT_SELECTION_LOGS = 128",
                "formal_seeds_11_12_13_excluded = True",
                "",
            ]
        ),
    )


def _test_file(path: Path) -> Path:
    return _write(path, "count_distribution=True\n")


def _plan_json(tmp_path: Path, *, mutation: Any | None = None) -> Path:
    plan = build_plan_report(
        result_readiness_json=_result_readiness(tmp_path / "result_readiness.json"),
        v13_audit_md=_plan_audit(tmp_path / "plan_audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )
    if mutation is not None:
        mutation(plan)
    return _write(tmp_path / "holdout_plan.json", json.dumps(plan))


def _report(tmp_path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        holdout_plan_json=_plan_json(tmp_path),
        holdout_plan_script_py=_script(tmp_path / "plan.py"),
        holdout_plan_test_py=_test_file(tmp_path / "test_plan.py"),
        v13_audit_md=_review_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_holdout_data_preparation_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    contract = report["contract_summary"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized_next"] is True
    assert decision["data_preparation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert contract["target_holdout_records"] == TARGET_HOLDOUT_RECORDS
    assert contract["train_eval_candidate_tensor_intersection_must_be_zero"] is True
    assert contract["candidate_generation_by_camp_forbidden"] is True
    assert contract["score_expression"] == "score_k(w)=a_k^T w"


def test_holdout_data_preparation_static_contract_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_holdout_data_preparation_static_contract_rejects_data_preparation_auth(
    tmp_path: Path,
) -> None:
    def authorize_data_preparation(plan: dict[str, Any]) -> None:
        plan["final_decision"]["data_preparation_authorized_next"] = True

    report = build_report(
        holdout_plan_json=_plan_json(tmp_path, mutation=authorize_data_preparation),
        holdout_plan_script_py=_script(tmp_path / "plan.py"),
        holdout_plan_test_py=_test_file(tmp_path / "test_plan.py"),
        v13_audit_md=_review_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_plan_does_not_authorize_data_preparation"
        in report["final_decision"]["failed_checks"]
    )


def test_holdout_data_preparation_static_contract_rejects_missing_zero_intersection(
    tmp_path: Path,
) -> None:
    def remove_contract(plan: dict[str, Any]) -> None:
        plan["holdout_data_preparation_plan"]["required_nonoverlap_contracts"][
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ] = False

    report = build_report(
        holdout_plan_json=_plan_json(tmp_path, mutation=remove_contract),
        holdout_plan_script_py=_script(tmp_path / "plan.py"),
        holdout_plan_test_py=_test_file(tmp_path / "test_plan.py"),
        v13_audit_md=_review_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "train_eval_candidate_tensor_intersection_must_be_zero"
        in report["final_decision"]["failed_checks"]
    )


def test_holdout_data_preparation_static_contract_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        holdout_plan_json=_plan_json(tmp_path),
        holdout_plan_script_py=_script(tmp_path / "plan.py"),
        holdout_plan_test_py=_test_file(tmp_path / "test_plan.py"),
        v13_audit_md=_review_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_holdout_data_preparation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--holdout_plan_json",
            str(_plan_json(tmp_path)),
            "--holdout_plan_script_py",
            str(_script(tmp_path / "plan.py")),
            "--holdout_plan_test_py",
            str(_test_file(tmp_path / "test_plan.py")),
            "--v13_audit_md",
            str(_review_audit(tmp_path / "audit.md")),
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
    assert payload["final_decision"]["data_preparation_authorized_next"] is False
    assert READY_STATUS in output_md.read_text(encoding="utf-8")
