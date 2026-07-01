from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_default_off_member_source_generation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    MANIFEST_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_generation_report,
    main,
)


CAMP_HEAD = "a207a80035c7f8b39bc1a99453d3c5429d9e5394"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _selection_log(
    root: Path,
    member_id: str,
    *,
    selected_index: int = 0,
    executed_index: int = 0,
    shadow_selected_index: int = 2,
) -> str:
    path = root / "logs" / member_id / "camp_selection_log.json"
    record = {
        "selected_index": selected_index,
        "executed_index": executed_index,
        "shadow_selected_index": shadow_selected_index,
        "num_candidates": 8,
        "default_off_shadow_selector": {
            "schema_version": DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION,
            "enabled": True,
            "default_off": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
            "selection_effect": False,
            "online_selector_change": False,
            "executed_index": executed_index,
            "shadow_selected_index": shadow_selected_index,
        },
    }
    _write_json(path, {"records": [record]})
    return str(path)


def _review(path: Path, *, mutation: Any | None = None) -> Path:
    false_flags = {
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    payload = {
        "schema_version": (
            "dp_camp_v13_default_off_member_source_generation_implementation_"
            "static_contract_review_v1"
        ),
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_member_source_generation_implementation_"
                "static_contract_review_passed"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "implementation_authorized_next": True,
            **false_flags,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "default_off_member_source_generation_implementation_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _registry(path: Path, values: list[str]) -> Path:
    return _write_json(path, {"values": values})


def _candidates(path: Path, *, mutation: Any | None = None) -> Path:
    root = path.parent
    payload = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_candidates_v1",
        "members": [
            {
                "member_id": "fresh-a",
                "route": "sample_normal",
                "seed": 333,
                "selection_log_json": _selection_log(root, "fresh-a"),
                "candidate_tensor_hashes": ["fresh_cand_a"],
                "path_signatures": ["fresh_path_a"],
                "record_identity_hashes": ["fresh_record_a"],
                "split_manifest_roots": ["fresh_split_a"],
            },
            {
                "member_id": "overlap-candidate",
                "route": "sample_tl",
                "seed": 334,
                "selection_log_json": _selection_log(root, "overlap-candidate"),
                "candidate_tensor_hashes": ["train_cand"],
                "path_signatures": ["fresh_path_b"],
                "record_identity_hashes": ["fresh_record_b"],
                "split_manifest_roots": ["fresh_split_b"],
            },
        ],
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _build(tmp_path: Path, *, enabled: bool = True) -> dict[str, Any]:
    return build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        candidate_member_source_manifest_json=_candidates(tmp_path / "candidates.json"),
        training_candidate_tensor_hash_registry_json=_registry(
            tmp_path / "train_candidate.json",
            ["train_cand"],
        ),
        training_path_signature_registry_json=_registry(tmp_path / "train_path.json", []),
        training_record_identity_registry_json=_registry(tmp_path / "train_record.json", []),
        training_split_manifest_root_registry_json=_registry(tmp_path / "train_split.json", []),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=enabled,
    )


def test_default_off_member_source_generation_builder_passes_and_writes_outputs(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    summary = report["selection_summary"]
    manifest_path = Path(report["output_paths"]["manifest"])

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["training_executed"] is False
    assert decision["dp_modification_authorized"] is False
    assert summary["selected_member_count"] == 1
    assert summary["rejected_reasons"]["candidate_tensor_hash_overlap"] == 1
    assert summary["zero_intersection_counts"]["candidate_tensor_hash_intersection_count"] == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["members"][0]["member_id"] == "fresh-a"
    assert manifest["fixed_dp_candidate_generation_executed"] is False


def test_default_off_member_source_generation_builder_is_default_disabled(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, enabled=False)

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert "builder_enabled" in report["final_decision"]["failed_checks"]
    assert report["selection_summary"]["manifest_written"] is False


def test_default_off_member_source_generation_builder_rejects_default_off_contract_break(
    tmp_path: Path,
) -> None:
    def selected_index_break(payload: dict[str, Any]) -> None:
        payload["members"][0]["selection_log_json"] = _selection_log(
            tmp_path,
            "bad-selected-index",
            selected_index=3,
        )
        payload["members"][1]["candidate_tensor_hashes"] = ["also_train_cand"]

    report = build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        candidate_member_source_manifest_json=_candidates(
            tmp_path / "candidates.json",
            mutation=selected_index_break,
        ),
        training_candidate_tensor_hash_registry_json=_registry(
            tmp_path / "train_candidate.json",
            ["also_train_cand"],
        ),
        training_path_signature_registry_json=_registry(tmp_path / "train_path.json", []),
        training_record_identity_registry_json=_registry(tmp_path / "train_record.json", []),
        training_split_manifest_root_registry_json=_registry(tmp_path / "train_split.json", []),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "selected_members_nonempty" in report["final_decision"]["failed_checks"]
    assert (
        report["selection_summary"]["rejected_reasons"][
            "default_off_selected_index_not_zero"
        ]
        == 1
    )


def test_default_off_member_source_generation_builder_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = build_generation_report(
        implementation_static_contract_review_json=_review(tmp_path / "review.json"),
        candidate_member_source_manifest_json=_candidates(tmp_path / "candidates.json"),
        training_candidate_tensor_hash_registry_json=_registry(
            tmp_path / "train_candidate.json",
            ["train_cand"],
        ),
        training_path_signature_registry_json=_registry(tmp_path / "train_path.json", []),
        training_record_identity_registry_json=_registry(tmp_path / "train_record.json", []),
        training_split_manifest_root_registry_json=_registry(tmp_path / "train_split.json", []),
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_default_off_member_source_generation_builder_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(_review(tmp_path / "review.json")),
            "--candidate_member_source_manifest_json",
            str(_candidates(tmp_path / "candidates.json")),
            "--training_candidate_tensor_hash_registry_json",
            str(_registry(tmp_path / "train_candidate.json", ["train_cand"])),
            "--training_path_signature_registry_json",
            str(_registry(tmp_path / "train_path.json", [])),
            "--training_record_identity_registry_json",
            str(_registry(tmp_path / "train_record.json", [])),
            "--training_split_manifest_root_registry_json",
            str(_registry(tmp_path / "train_split.json", [])),
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
            "--enable_default_off_member_source_generation_builder",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["selection_summary"]["selected_member_count"] == 1
    assert "Default-Off Member-Source Generation Builder" in output_md.read_text(
        encoding="utf-8"
    )
