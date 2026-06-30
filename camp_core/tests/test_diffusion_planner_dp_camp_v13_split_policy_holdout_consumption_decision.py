from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.decide_diffusion_planner_dp_camp_v13_split_policy_holdout_consumption import (
    CURRENT_SOURCE_RESULT_REVIEW_STATUS,
    DEFAULT_NEXT_WORK_TARGET,
    FIXED_DP_HEAD,
    GATE_NAME,
    PASS_STATUS,
    RESULT_READINESS_STATUS,
    RESULT_REVIEW_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "e8de599b1442c8fd28802741c93fb39b801fc918"


def _write(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _result_readiness(*, overlap: int = 0, guidance: int = 0) -> dict:
    return {
        "heads": {
            "current_camp_head": "24f645cbb8e95bab3868ff1d7151d274ab08c6da",
            "current_camp_origin_main": "24f645cbb8e95bab3868ff1d7151d274ab08c6da",
            "current_dp_head": FIXED_DP_HEAD,
            "required_dp_head": FIXED_DP_HEAD,
        },
        "source_paths": {"split_manifest_json": "/fixed/split_manifest.json"},
        "source_hashes": {"split_manifest_json_sha256": "a" * 64},
        "clean_contract": {
            "passed": True,
            "records": 3200,
            "failed_records": 0,
            "future_training_input_contract_satisfied": True,
        },
        "training_readiness": {
            "selection_log_count": 32,
            "records_total": 3200,
            "usable_feasible_records": 2642,
            "multi_feasible_records": 2589,
            "all_infeasible_records": 558,
            "route_records": {
                "nishi_lane_change": 800,
                "nishi_release": 800,
                "sample_normal": 800,
                "sample_tl": 800,
            },
            "route_tl_records": {
                "nishi_lane_change|tl_off": 400,
                "nishi_lane_change|tl_on": 400,
            },
            "seed_records": {"1300": 1600, "1301": 1600},
            "formal_seed_records": 0,
            "reference_blend_enabled_records": 0,
            "guidance_enabled_records": guidance,
            "postselection_records": 0,
            "closed_loop_outcome_records": 0,
            "camp_candidate_generation_effect_records": 0,
            "dp_modification_records": 0,
            "shadow_differs_from_dp_top1_records": 3017,
        },
        "candidate_tensor_overlap": {
            "eval_hashes_in_previous_count": overlap,
            "eval_hashes_in_previous_rate": 0.0 if overlap == 0 else 0.1,
        },
        "final_decision": {
            "passed": True,
            "status": RESULT_READINESS_STATUS,
        },
    }


def _registry_manifest(*, candidate_overlap: int = 0) -> dict:
    return {
        "training_log_count": 224,
        "evaluation_log_count": 32,
        "training_candidate_hash_count": 22400,
        "evaluation_candidate_hash_count": 3200,
        "evaluation_record_identity_count": 3200,
        "candidate_hash_intersection_count": candidate_overlap,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
    }


def _audit_text(
    *,
    holdout_signal: bool = True,
    current_status: str = RESULT_REVIEW_STATUS,
    next_work_target: str = "none_result_review_passed_no_promotion_or_safety_claim_authorized",
) -> str:
    return "\n".join(
        [
            f"current_v13_status={current_status}",
            "static_dp_reward_training_artifact_shadow_replay_evaluation_result_review_passed=True",
            "static_dp_reward_training_artifact_shadow_replay_evaluation_result_review_training_preflight_clean_data_available=True",
            "static_dp_reward_training_artifact_shadow_replay_evaluation_holdout_consumption_requires_split_policy_decision="
            + ("True" if holdout_signal else "False"),
            "training_execution_authorized_by_current_boundary=False",
            "replay_execution_authorized_by_current_boundary=False",
            "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
            f"next_work_target={next_work_target}",
            "",
        ]
    )


def _fixture(
    tmp_path: Path,
    *,
    overlap: int = 0,
    holdout_signal: bool = True,
    current_status: str = RESULT_REVIEW_STATUS,
    next_work_target: str = "none_result_review_passed_no_promotion_or_safety_claim_authorized",
) -> dict[str, Path]:
    return {
        "result": _write(tmp_path / "result_readiness.json", _result_readiness(overlap=overlap)),
        "registry": _write(tmp_path / "registry_manifest.json", _registry_manifest(candidate_overlap=overlap)),
        "audit": _write(
            tmp_path / "audit.md",
            _audit_text(
                holdout_signal=holdout_signal,
                current_status=current_status,
                next_work_target=next_work_target,
            ),
        ),
    }


def test_split_policy_preserves_current_holdout_by_default(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    report = build_report(
        result_readiness_json=paths["result"],
        registry_manifest_json=paths["registry"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["status"] == PASS_STATUS
    assert report["policy_decision"]["decision"] == "preserve_current_holdout"
    assert report["policy_decision"]["current_holdout_preserved"] is True
    assert report["policy_decision"]["current_holdout_consumed"] is False
    assert report["policy_decision"]["training_from_current_holdout_authorized"] is False
    assert report["policy_decision"]["next_work_target"] == DEFAULT_NEXT_WORK_TARGET


def test_split_policy_accepts_current_source_result_review_and_explicit_gate(tmp_path: Path) -> None:
    paths = _fixture(
        tmp_path,
        current_status=CURRENT_SOURCE_RESULT_REVIEW_STATUS,
        next_work_target=GATE_NAME,
    )

    report = build_report(
        result_readiness_json=paths["result"],
        registry_manifest_json=paths["registry"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["passed"] is True
    assert report["policy_decision"]["decision"] == "preserve_current_holdout"
    assert report["policy_decision"]["current_holdout_preserved"] is True
    assert report["final_decision"]["authorized_next_work"] == DEFAULT_NEXT_WORK_TARGET


def test_split_policy_rejects_overlap(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, overlap=1)
    report = build_report(
        result_readiness_json=paths["result"],
        registry_manifest_json=paths["registry"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["passed"] is False
    assert "candidate_hash_intersection_zero" in report["final_decision"]["failed_checks"]
    assert "candidate_tensor_eval_hashes_in_previous_zero" in report["final_decision"]["failed_checks"]


def test_split_policy_rejects_missing_holdout_signal(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, holdout_signal=False)
    report = build_report(
        result_readiness_json=paths["result"],
        registry_manifest_json=paths["registry"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["passed"] is False
    assert "audit_holdout_consumption_requires_split_policy" in report["final_decision"]["failed_checks"]


def test_split_policy_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    output_json = tmp_path / "out" / "split_policy.json"
    output_md = tmp_path / "out" / "split_policy.md"

    rc = main(
        [
            "--result_readiness_json",
            str(paths["result"]),
            "--registry_manifest_json",
            str(paths["registry"]),
            "--v13_audit_md",
            str(paths["audit"]),
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

    assert rc == 0
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == PASS_STATUS
    assert "V13 Split Policy" in output_md.read_text(encoding="utf-8")
