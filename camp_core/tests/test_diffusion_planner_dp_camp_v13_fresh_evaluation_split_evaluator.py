from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.evaluate_diffusion_planner_dp_camp_v13_fresh_evaluation_split import (
    ATOM_SCHEMA_VERSION,
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    MEMBER_SOURCE_SCHEMA,
    NONOVERLAP_REPORT_SCHEMA,
    READY_STATUS,
    REJECT_STATUS,
    RUNTIME_MANIFEST_SCHEMA,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "54434a96b1a69bcea10bdec369d247d8c7fb7185"
ATOM_NAMES = [
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
]


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _record(*, selected_index: int = 0, selection_effect: bool = False) -> dict[str, Any]:
    weights = [1.0 / 14.0] * 14
    atoms = [
        [float(candidate + atom + 1) / 100.0 for atom in range(14)]
        for candidate in range(8)
    ]
    scores = [sum(atom * weight for atom, weight in zip(row, weights)) for row in atoms]
    shadow_selected_index = 2
    return {
        "atoms": atoms,
        "normalized_atoms": atoms,
        "selection_normalized_atoms": atoms,
        "weights": weights,
        "selection_weights": weights,
        "scores": scores,
        "selection_scores": scores,
        "selected_index": selected_index,
        "executed_index": 0,
        "shadow_selected_index": shadow_selected_index,
        "num_candidates": 8,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": ATOM_NAMES,
        "feasible_mask": [True] * 8,
        "used_fallback": False,
        "candidate_closed_loop_outcomes": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 8,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "default_off_shadow_selector": {
            "schema_version": RUNTIME_MANIFEST_SCHEMA,
            "enabled": True,
            "default_off": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "selection_effect": selection_effect,
            "online_selector_change": False,
            "artifact_contract_ready": True,
            "failed_closed_reason": None,
            "executed_index": 0,
            "shadow_selected_index": shadow_selected_index,
            "candidate_tensor_hash": {
                "sha256": "a" * 64,
                "shape": [8, 16, 3],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
    }


def _logs(root: Path, *, selected_index: int = 0, selection_effect: bool = False) -> Path:
    for route in ("sample_normal", "nishi_release"):
        log = root / route / "seed_201" / "npc_0" / "spawn_0p3" / "tl_off" / "static_shadow" / "camp_selection_log.json"
        _write_json(
            log,
            [
                _record(selected_index=selected_index, selection_effect=selection_effect)
                for _ in range(3)
            ],
        )
    return root


def _member_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": MEMBER_SOURCE_SCHEMA,
            "selected_member_count": 2,
            "members": [
                {"relative_path": "sample_normal/seed_201/camp_selection_log.json"},
                {"relative_path": "nishi_release/seed_201/camp_selection_log.json"},
            ],
        },
    )


def _nonoverlap(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": NONOVERLAP_REPORT_SCHEMA,
            "zero_intersection_counts": {
                "candidate_tensor_hash_intersection_count": 0,
                "path_signature_intersection_count": 0,
                "record_identity_intersection_count": 0,
                "split_manifest_root_intersection_count": 0,
            },
        },
    )


def _runtime_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": RUNTIME_MANIFEST_SCHEMA,
            "default_off": True,
            "selection_effect": False,
            "executed_output_policy": "dp_top1",
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "current_dp_head": FIXED_DP_HEAD,
        },
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_execution_preflight_passed",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _inputs(tmp_path: Path, *, selected_index: int = 0, selection_effect: bool = False, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Path]:
    return {
        "evaluation_output_dir": _logs(
            tmp_path / "logs",
            selected_index=selected_index,
            selection_effect=selection_effect,
        ),
        "member_source_manifest_json": _member_manifest(tmp_path / "member_source.json"),
        "member_source_nonoverlap_report_json": _nonoverlap(tmp_path / "nonoverlap.json"),
        "runtime_manifest_json": _runtime_manifest(tmp_path / "runtime_manifest.json"),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_selection_log_count=2,
        expected_records=6,
        enabled=True,
    )


def test_fresh_evaluation_split_evaluator_is_disabled_by_default(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        evaluation_output_dir=missing,
        member_source_manifest_json=missing,
        member_source_nonoverlap_report_json=missing,
        runtime_manifest_json=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["fresh_evaluation_split_evaluation_executed"] is False
    assert report["evaluation_checks"] == []


def test_fresh_evaluation_split_evaluator_accepts_default_off_shadow_logs(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_evaluation_executed"] is True
    assert decision["fresh_evaluation_split_evaluation_result_review_authorized_next"] is True
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["clean_contract"]["passed"] is True
    assert report["evaluation"]["selection_log_count"] == 2
    assert report["evaluation"]["record_count"] == 6
    assert report["evaluation"]["shadow_differs_from_dp_top1_records"] == 6
    assert report["evaluation"]["executed_index_violations"] == 0
    assert report["evaluation"]["max_affine_score_error"] <= 1.0e-12


def test_fresh_evaluation_split_evaluator_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_evaluator_rejects_selection_effect_or_executed_change(tmp_path: Path) -> None:
    report = _report(tmp_path, selected_index=1, selection_effect=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "clean_contract_passed" in report["final_decision"]["failed_checks"]
    assert "evaluation_executed_index_violations_zero" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_evaluator_main_writes_outputs(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    output_json = tmp_path / "out" / "fresh_evaluation_split_evaluation_report.json"
    output_md = tmp_path / "out" / "fresh_evaluation_split_evaluation_report.md"

    exit_code = main(
        [
            "--evaluation_output_dir",
            str(inputs["evaluation_output_dir"]),
            "--member_source_manifest_json",
            str(inputs["member_source_manifest_json"]),
            "--member_source_nonoverlap_report_json",
            str(inputs["member_source_nonoverlap_report_json"]),
            "--runtime_manifest_json",
            str(inputs["runtime_manifest_json"]),
            "--v13_audit_md",
            str(inputs["v13_audit_md"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_selection_log_count",
            "2",
            "--expected_records",
            "6",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_fresh_evaluation_split_evaluation",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["evaluation"]["record_count"] == 6
    assert "Executed output remains DP Top-1" in output_md.read_text(encoding="utf-8")
