from __future__ import annotations

import hashlib
import json
from pathlib import Path

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness import (
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "9cdf56c10bfc872f4fd02e17d5313a7984c81c95"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(hash_label: str, *, guidance_enabled: bool = False) -> dict:
    schema_version, atom_names = atom_schema_for_dimension(14)
    assert schema_version == ATOM_SCHEMA_VERSION
    return {
        "num_candidates": 8,
        "atoms": [[float(candidate + atom + 1) / 100.0 for atom in range(14)] for candidate in range(8)],
        "atom_names": list(atom_names),
        "atom_schema_version": schema_version,
        "feasible_mask": [True] * 8,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 2,
        "candidate_reference_blend_steps": None,
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
        "candidate_closed_loop_outcomes": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 8,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": guidance_enabled,
            "changes_diffusion_planner_weights": False,
        },
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": False,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "executed_index": 0,
            "shadow_selected_index": 2,
            "failed_closed_reason": None,
            "artifact_contract_ready": True,
            "candidate_tensor_hash": {
                "sha256": _sha(hash_label),
                "shape": [8, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "dp_candidate_rewards": [
            {"total": float(index), "progress": float(index) / 10.0}
            for index in range(8)
        ],
    }


def _write_logs(root: Path, *, prefix: str, overlap_with: str | None = None) -> None:
    rows_a = [
        _record(f"{overlap_with or prefix}-a-{index}")
        for index in range(3)
    ]
    rows_b = [
        _record(f"{overlap_with or prefix}-b-{index}")
        for index in range(3)
    ]
    _write(
        root
        / "sample_normal"
        / "seed_301"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static_shadow"
        / "camp_selection_log.json",
        json.dumps(rows_a),
    )
    _write(
        root
        / "sample_tl"
        / "seed_302"
        / "npc_0"
        / "spawn_0p3"
        / "tl_off"
        / "static_shadow"
        / "camp_selection_log.json",
        json.dumps(rows_b),
    )


def _write_execution_audit(path: Path, *, guidance_violation: int = 0) -> Path:
    data = {
        "schema_version": "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_v1",
        "final_decision": {
            "passed": guidance_violation == 0,
            "status": "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_passed",
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "result_review_and_training_readiness_authorized_next": True,
            "training_performed_by_this_audit": False,
            "candidate_generation_performed_by_this_audit": False,
            "replay_execution_performed_by_this_audit": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "execution": {
            "selection_log_count": 2,
            "expected_records": 6,
        },
        "records": {
            "record_count": 6,
            "feasible_records": 6,
            "used_fallback_records": 0,
            "shadow_differs_from_dp_top1_records": 6,
            "violation_counts": {
                "default_off_contract": 0,
                "executed_index": 0,
                "postselection": 0,
                "reference_blend": 0,
                "guidance": guidance_violation,
                "closed_loop_outcomes": 0,
                "atom_schema": 0,
                "affine_score": 0,
                "selection_score_mask": 0,
                "shape": 0,
            },
        },
    }
    return _write(path, json.dumps(data))


def _write_audit_md(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "camp_training_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "",
            ]
        ),
    )


def _write_current_audit_md(path: Path, *, current_work: str) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={current_work}",
                "training_execution_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "",
            ]
        ),
    )


def _selection_logs(root: Path) -> list[str]:
    return [str(path) for path in sorted(root.rglob("camp_selection_log.json"))]


def _eval_hashes() -> list[str]:
    return [_sha(f"eval-a-{index}") for index in range(3)] + [
        _sha(f"eval-b-{index}") for index in range(3)
    ]


def _write_nonoverlap_artifacts(
    root: Path,
    *,
    split_overlap: bool = False,
    formal_seed: bool = False,
    candidate_overlap: bool = False,
    path_overlap: bool = False,
    record_overlap: bool = False,
) -> dict[str, Path]:
    training_root = root / "previous"
    holdout_root = training_root if split_overlap else root / "evaluation"
    training_candidate_hashes = (
        [_eval_hashes()[0]]
        if candidate_overlap
        else [_sha(f"previous-a-{index}") for index in range(3)]
    )
    evaluation_path_signatures = ["eval_path_a", "eval_path_b"]
    training_path_signatures = (
        ["eval_path_a"] if path_overlap else ["previous_path_a", "previous_path_b"]
    )
    evaluation_record_identities = [f"eval_record_{index}" for index in range(6)]
    training_record_identities = (
        ["eval_record_0"]
        if record_overlap
        else [f"previous_record_{index}" for index in range(6)]
    )
    split = {
        "training": {
            "selection_log_roots": [str(training_root)],
            "seeds": [301],
        },
        "holdout": {
            "selection_log_roots": [str(holdout_root)],
            "seeds": [11 if formal_seed else 302],
        },
    }
    candidate_registry = {
        "training": {"values": training_candidate_hashes},
        "evaluation": {"values": _eval_hashes()},
    }
    path_registry = {
        "training": {"values": training_path_signatures},
        "evaluation": {"values": evaluation_path_signatures},
    }
    record_registry = {
        "training": {"values": training_record_identities},
        "evaluation": {"values": evaluation_record_identities},
    }
    return {
        "split_manifest_json": _write(root / "split_manifest.json", json.dumps(split)),
        "candidate_tensor_hash_registry_json": _write(
            root / "candidate_tensor_hash_registry.json",
            json.dumps(candidate_registry),
        ),
        "path_signature_registry_json": _write(
            root / "path_signature_registry.json",
            json.dumps(path_registry),
        ),
        "record_identity_hash_registry_json": _write(
            root / "record_identity_hash_registry.json",
            json.dumps(record_registry),
        ),
    }


def _report(tmp_path: Path, *, overlap_previous: bool = False, guidance_violation: int = 0) -> dict:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous", overlap_with="eval" if overlap_previous else None)
    artifacts = _write_nonoverlap_artifacts(tmp_path)
    execution_audit = _write_execution_audit(
        tmp_path / "execution_audit.json",
        guidance_violation=guidance_violation,
    )
    audit_md = _write_audit_md(tmp_path / "audit.md")
    return build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )


def test_result_readiness_accepts_fixed_default_off_eval_logs(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["clean_contract"]["passed"] is True
    assert report["training_readiness"]["records_total"] == 6
    assert report["training_readiness"]["usable_feasible_records"] == 6
    assert report["candidate_tensor_overlap"]["eval_hashes_in_previous_count"] == 0
    assert report["split_manifest"]["root_intersection_count"] == 0
    assert report["split_manifest"]["formal_seed_count"] == 0
    assert report["candidate_tensor_hash_registry"]["intersection_count"] == 0
    assert report["path_signature_registry"]["intersection_count"] == 0
    assert report["record_identity_hash_registry"]["intersection_count"] == 0
    assert decision["static_dp_reward_training_execution_authorized_next"] is False
    assert decision["safety_benefit_claim_authorized"] is False


def test_result_readiness_accepts_parameterized_current_gate(tmp_path: Path) -> None:
    current_work = "dp_camp_v13_result_review_only"
    next_work = "dp_camp_v13_training_preflight_only"
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    payload = json.loads(execution_audit.read_text(encoding="utf-8"))
    payload["final_decision"]["authorized_next_work"] = current_work
    execution_audit.write_text(json.dumps(payload), encoding="utf-8")
    audit_md = _write_current_audit_md(tmp_path / "audit.md", current_work=current_work)

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
        authorized_current_work=current_work,
        authorized_next_work=next_work,
        training_blocked_audit_key="training_execution_authorized_by_current_boundary",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == next_work


def test_result_readiness_rejects_execution_audit_violation(tmp_path: Path) -> None:
    report = _report(tmp_path, guidance_violation=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "execution_audit_passed" in report["final_decision"]["failed_checks"]
    assert (
        "execution_audit_violation_zero:guidance"
        in report["final_decision"]["failed_checks"]
    )


def test_result_readiness_rejects_previous_candidate_tensor_overlap(tmp_path: Path) -> None:
    report = _report(tmp_path, overlap_previous=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_tensor_overlap_rate_within_limit" in report["final_decision"]["failed_checks"]
    assert report["candidate_tensor_overlap"]["eval_hashes_in_previous_count"] == 6


def test_result_readiness_rejects_training_summary_selection_log_overlap(
    tmp_path: Path,
) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous", overlap_with="eval")
    artifacts = _write_nonoverlap_artifacts(tmp_path)
    summary = _write(
        tmp_path / "training_summary.json",
        json.dumps({"selection_logs": _selection_logs(previous)}),
    )
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_summary_json=summary,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_tensor_overlap_rate_within_limit" in report["final_decision"]["failed_checks"]
    assert report["candidate_tensor_overlap"]["previous_hash_count"] == 6
    assert report["candidate_tensor_overlap"]["eval_hashes_in_previous_count"] == 6


def test_result_readiness_rejects_split_manifest_overlap(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path, split_overlap=True)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "split_manifest_training_holdout_root_intersection_zero"
        in report["final_decision"]["failed_checks"]
    )


def test_result_readiness_rejects_formal_seed_in_split_manifest(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path, formal_seed=True)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "split_manifest_formal_seed_records_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_result_readiness_rejects_candidate_tensor_registry_overlap(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path, candidate_overlap=True)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_tensor_hash_registry_intersection_zero" in report[
        "final_decision"
    ]["failed_checks"]


def test_result_readiness_rejects_path_signature_registry_overlap(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path, path_overlap=True)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "path_signature_registry_intersection_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_result_readiness_rejects_record_identity_registry_overlap(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path, record_overlap=True)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")

    report = build_report(
        evaluation_output_dir=evaluation,
        execution_audit_json=execution_audit,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        previous_training_output_dir=previous,
        **artifacts,
        expected_selection_log_count=2,
        expected_records=6,
        min_routes=2,
        min_seeds=2,
        min_route_tl_buckets=2,
        min_usable_feasible_records=1,
        min_multi_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "record_identity_hash_registry_intersection_zero" in report[
        "final_decision"
    ]["failed_checks"]


def test_result_readiness_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation"
    previous = tmp_path / "previous"
    _write_logs(evaluation, prefix="eval")
    _write_logs(previous, prefix="previous")
    artifacts = _write_nonoverlap_artifacts(tmp_path)
    execution_audit = _write_execution_audit(tmp_path / "execution_audit.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "readiness.json"
    output_md = tmp_path / "out" / "readiness.md"

    exit_code = main(
        [
            "--evaluation_output_dir",
            str(evaluation),
            "--execution_audit_json",
            str(execution_audit),
            "--v13_audit_md",
            str(audit_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--previous_training_output_dir",
            str(previous),
            "--split_manifest_json",
            str(artifacts["split_manifest_json"]),
            "--candidate_tensor_hash_registry_json",
            str(artifacts["candidate_tensor_hash_registry_json"]),
            "--path_signature_registry_json",
            str(artifacts["path_signature_registry_json"]),
            "--record_identity_hash_registry_json",
            str(artifacts["record_identity_hash_registry_json"]),
            "--expected_selection_log_count",
            "2",
            "--expected_records",
            "6",
            "--min_routes",
            "2",
            "--min_seeds",
            "2",
            "--min_route_tl_buckets",
            "2",
            "--min_usable_feasible_records",
            "1",
            "--min_multi_feasible_records",
            "1",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert "read-only result review" in output_md.read_text(encoding="utf-8")
