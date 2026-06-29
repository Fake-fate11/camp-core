from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.review_diffusion_planner_dp_camp_v13_current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_training_readiness import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.validate_dp_native_training_data_contract import (
    PROVENANCE_SCHEMA_VERSION,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "91ae66fc6fd4a5b7dad111ebc613a4318934a8fc"


def _sha(value: str) -> str:
    return value * 64


def _record(
    *,
    selected_index: int = 0,
    executed_index: int = 0,
    shadow_selected_index: int = 1,
    feasible_mask: list[bool] | None = None,
    include_rewards: bool = True,
    closed_loop_outcomes=None,
    legacy_provenance: bool = True,
) -> dict:
    version, names = atom_schema_for_dimension(14)
    candidate_count = 8
    if feasible_mask is None:
        feasible_mask = [True for _ in range(candidate_count)]
    record = {
        "selected_index": selected_index,
        "executed_index": executed_index,
        "shadow_selected_index": shadow_selected_index,
        "num_candidates": candidate_count,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": [
            [float(index + column + 1) / 20.0 for column in range(14)]
            for index in range(candidate_count)
        ],
        "normalized_atoms": [
            [float(index + column + 1) / 20.0 for column in range(14)]
            for index in range(candidate_count)
        ],
        "scores": [float(index) for index in range(candidate_count)],
        "selection_scores": [float(index) for index in range(candidate_count)],
        "feasible_mask": feasible_mask,
        "candidate_closed_loop_outcomes": closed_loop_outcomes,
        "candidate_reference_blend_steps": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": candidate_count,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "artifact_contract_ready": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "selection_effect": False,
            "online_selector_change": False,
            "failed_closed_reason": None,
            "executed_index": executed_index,
            "shadow_selected_index": shadow_selected_index,
            "candidate_tensor_hash": {
                "sha256": _sha("b"),
                "shape": [candidate_count, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "camp_candidate_tensor_provenance": None,
    }
    if legacy_provenance:
        record["camp_candidate_tensor_provenance"] = {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "candidate_count": candidate_count,
            "post_selector_candidate_count": candidate_count,
            "selected_index": selected_index,
            "pre_camp_scoring_tensor": {
                "sha256": _sha("a"),
                "shape": [candidate_count, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
            "post_camp_selector_tensor": {
                "sha256": _sha("a"),
                "shape": [candidate_count, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        }
    if include_rewards:
        record["dp_candidate_rewards"] = [
            {"total": float(8 - index), "progress": 0.1 * index}
            for index in range(candidate_count)
        ]
    return record


def _write_log(root: Path, route: str, seed: int, tl: str, records: list[dict]) -> Path:
    path = (
        root
        / route
        / f"seed_{seed}"
        / "npc_0"
        / "spawn_0p3"
        / f"tl_{tl}"
        / "static_shadow"
    )
    path.mkdir(parents=True, exist_ok=True)
    log_path = path / "camp_selection_log.json"
    log_path.write_text(json.dumps(records), encoding="utf-8")
    (path / "camp_validation_summary.json").write_text("{}", encoding="utf-8")
    return log_path


def _audit_text(*, wrong_scope: bool = False, remediation_scope: bool = False) -> str:
    next_work = (
        "old_scope"
        if wrong_scope
        else (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
            "nonformal_shadow_replay_batch_default_off_shadow_training_data_"
            "contract_remediation_only"
        )
        if remediation_scope
        else (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
            "nonformal_shadow_replay_batch_result_review_and_training_readiness_"
            "preflight_only"
        )
    )
    status = (
        "current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_training_readiness_contract_remediation_required"
        if remediation_scope
        else "current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_passed"
    )
    return "\n".join(
        [
            f"current_v13_status={status}",
            f"next_work_target={next_work}",
            "training_execution_authorized_by_current_boundary=False",
            "dp_modification_authorized_by_current_boundary=False",
        ]
    )


def _static_audit(
    *,
    replay_root: Path,
    execution_root: Path,
    records: int = 4,
    logs: int = 2,
) -> dict:
    checks = {
        "runbook_exit_zero": True,
        "selection_log_count_32": True,
        "validation_log_count_32": True,
        "records_total_3200": True,
        "summary_shadow_records_3200": True,
        "executed_indices_dp_top1": True,
        "selected_indices_dp_top1": True,
        "missing_shadow_payload_zero": True,
        "failed_shadow_records_zero": True,
        "reference_blend_disabled_all_records": True,
        "guidance_disabled_all_records": True,
        "candidate_closed_loop_outcomes_absent": True,
        "score_expression_affine_all_records": True,
        "candidate_operation_fixed_all_records": True,
        "executed_policy_dp_top1_all_records": True,
        "selection_effect_false_all_records": True,
    }
    blocked = {
        "training_executed": False,
        "candidate_generation_by_camp_executed": False,
        "trajectory_generation_by_camp_executed": False,
        "trajectory_modification_by_camp_executed": False,
        "dp_modified": False,
        "formal_seeds_executed": False,
        "selector_promoted": False,
        "atom_promoted": False,
        "deployed": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    return {
        "schema_version": "dp_camp_v13_current_source_large_shadow_replay_batch_execution_static_audit_v1",
        "status": "passed",
        "passed": True,
        "execution_artifact_dir": str(execution_root.resolve()),
        "replay_output_dir": str(replay_root.resolve()),
        "selection_log_count": logs,
        "validation_log_count": logs,
        "records_total": records,
        "summary_shadow_records": records,
        "executed_indices": {"0": records},
        "selected_indices": {"0": records},
        "shadow_selected_index_counts": {"0": 2, "1": 2},
        "nonzero_shadow_selection_count_records": 2,
        "route_records": {"sample_normal": 2, "sample_tl": 2},
        "route_tl_records": {"sample_normal|tl_on": 2, "sample_tl|tl_off": 2},
        "failed_checks": [],
        "checks": checks,
        "blocked_claims": blocked,
    }


def _fixture(
    tmp_path: Path,
    *,
    wrong_scope: bool = False,
    remediation_scope: bool = False,
) -> dict[str, Path]:
    replay_root = tmp_path / "replay"
    execution_root = tmp_path / "execution"
    execution_root.mkdir()
    _write_log(
        replay_root,
        "sample_normal",
        301,
        "on",
        [_record(shadow_selected_index=0), _record(shadow_selected_index=1)],
    )
    _write_log(
        replay_root,
        "sample_tl",
        302,
        "off",
        [
            _record(feasible_mask=[False] * 8, shadow_selected_index=0),
            _record(shadow_selected_index=1),
        ],
    )
    (execution_root / "static_batch_audit.json").write_text(
        json.dumps(_static_audit(replay_root=replay_root, execution_root=execution_root)),
        encoding="utf-8",
    )
    (execution_root / "replay_output_hash_manifest.txt").write_text(
        "manifest\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.md"
    audit.write_text(
        _audit_text(wrong_scope=wrong_scope, remediation_scope=remediation_scope),
        encoding="utf-8",
    )
    return {
        "replay_root": replay_root,
        "execution_root": execution_root,
        "audit": audit,
    }


def _report(tmp_path: Path, **overrides):
    paths = _fixture(
        tmp_path,
        wrong_scope=overrides.pop("wrong_scope", False),
        remediation_scope=overrides.pop("remediation_scope", False),
    )
    params = {
        "replay_output_dir": paths["replay_root"],
        "execution_artifact_dir": paths["execution_root"],
        "v13_audit_md": paths["audit"],
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "expected_selection_log_count": 2,
        "expected_validation_log_count": 2,
        "expected_records": 4,
        "min_routes": 2,
        "min_seeds": 2,
        "min_route_tl_buckets": 2,
        "min_usable_feasible_records": 2,
        "min_multi_feasible_records": 2,
    }
    params.update(overrides)
    return build_report(**params)


def test_training_readiness_passes_fixed_shadow_batch_fixture(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    readiness = report["training_readiness"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_dp_reward_training_execution_authorized_next"] is True
    assert decision["training_executed"] is False
    assert readiness["records_total"] == 4
    assert readiness["usable_feasible_records"] == 3
    assert readiness["records_dropped_without_feasible_candidate_by_static_training"] == 1
    assert readiness["nonzero_shadow_selection_count"] == 2
    assert readiness["closed_loop_outcome_records"] == 0
    assert readiness["candidate_count_values"] == {"8": 4}
    assert readiness["atom_schema_versions"] == {"dp_camp_v10_14d": 4}


def test_training_readiness_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_scope_allows_review" in report["final_decision"][
        "failed_checks"
    ]
    assert report["final_decision"]["authorized_next_work"] is None


def test_training_readiness_accepts_current_remediation_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, remediation_scope=True)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK


def test_training_readiness_rejects_label_contract_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    bad_log = next(paths["replay_root"].rglob("camp_selection_log.json"))
    records = json.loads(bad_log.read_text(encoding="utf-8"))
    records[0].pop("dp_candidate_rewards")
    bad_log.write_text(json.dumps(records), encoding="utf-8")

    report = build_report(
        replay_output_dir=paths["replay_root"],
        execution_artifact_dir=paths["execution_root"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_selection_log_count=2,
        expected_validation_log_count=2,
        expected_records=4,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=2,
        min_multi_feasible_records=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "label_failed_records_zero" in report["final_decision"]["failed_checks"]
    assert report["training_readiness"]["label_failed_record_count"] == 1


def test_training_readiness_accepts_default_off_contract_after_remediation(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    for log_path in paths["replay_root"].rglob("camp_selection_log.json"):
        records = json.loads(log_path.read_text(encoding="utf-8"))
        for record in records:
            record["camp_candidate_tensor_provenance"] = None
        log_path.write_text(json.dumps(records), encoding="utf-8")

    report = build_report(
        replay_output_dir=paths["replay_root"],
        execution_artifact_dir=paths["execution_root"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_selection_log_count=2,
        expected_validation_log_count=2,
        expected_records=4,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=2,
        min_multi_feasible_records=2,
    )

    decision = report["final_decision"]
    readiness = report["training_readiness"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_dp_reward_training_execution_authorized_next"] is True
    assert readiness["legacy_provenance_missing_records"] == 4
    assert readiness["default_off_shadow_selector_valid_records"] == 4
    assert readiness["contract_error_counts"] == {}


def test_training_readiness_cli_writes_reports(tmp_path: Path, capsys) -> None:
    paths = _fixture(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--replay_output_dir",
            str(paths["replay_root"]),
            "--execution_artifact_dir",
            str(paths["execution_root"]),
            "--v13_audit_md",
            str(paths["audit"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_selection_log_count",
            "2",
            "--expected_validation_log_count",
            "2",
            "--expected_records",
            "4",
            "--min_routes",
            "2",
            "--min_seeds",
            "2",
            "--min_route_tl_buckets",
            "2",
            "--min_usable_feasible_records",
            "2",
            "--min_multi_feasible_records",
            "2",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "read-only training-readiness review" in output_md.read_text(
        encoding="utf-8"
    )
    assert '"passed": true' in capsys.readouterr().out
