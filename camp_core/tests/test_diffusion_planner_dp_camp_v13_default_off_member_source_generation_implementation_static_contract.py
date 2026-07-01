from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_member_source_generation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_FUTURE_GENERATOR_SCRIPT,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_FUTURE_BEHAVIOR,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "35bec304ba8a41d7769b8eec3e60228040d7ed2f"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_implementation_plan_v1",
        "implementation_plan": {
            "acceptance_summary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "default_off_execution": "selected_index=0 and executed_index=0 for every record",
                "fixed_dp_head": FIXED_DP_HEAD,
                "score_expression": "score_k(w)=a_k^T w",
                "shadow_only_field": "shadow_selected_index may be recorded without execution effect",
            },
            "future_generator_script": EXPECTED_FUTURE_GENERATOR_SCRIPT,
            "future_generator_test": (
                "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
                "default_off_member_source_generation_builder.py"
            ),
            "future_outputs": [
                "default_off_member_source_generation_manifest.json",
                "candidate_tensor_hash_registry.json",
                "path_signature_registry.json",
                "record_identity_registry.json",
                "split_manifest_root_registry.json",
                "zero_overlap_preflight_inputs.json",
                "SHA256SUMS",
            ],
            "implementation_performed_by_this_gate": False,
            "required_future_behavior": list(REQUIRED_FUTURE_BEHAVIOR),
        },
        "final_decision": {
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "candidate_generation_by_camp_authorized": False,
            "closed_loop_outcome_authorized": False,
            "data_preparation_authorized_next": False,
            "deployable_checkpoint_claim_authorized": False,
            "deployment_authorized": False,
            "dp_modification_authorized": False,
            "failed_checks": [],
            "fixed_dp_candidate_generation_authorized_next": False,
            "guidance_authorized": False,
            "implementation_authorized_next": False,
            "implementation_static_contract_review_authorized_next": True,
            "passed": True,
            "postprocess_or_postselection_authorized": False,
            "reference_blend_authorized": False,
            "replay_execution_authorized_next": False,
            "safety_benefit_claim_authorized": False,
            "score_expression": "score_k(w)=a_k^T w",
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "status": "dp_camp_v13_default_off_member_source_generation_implementation_plan_ready",
            "training_execution_authorized_next": False,
            "training_preflight_authorized_next": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    _write_json(root / "default_off_member_source_generation_implementation_plan.json", payload)
    return root


def _source_script(path: Path, *, include_contracts: bool = True) -> Path:
    snippets = [
        "implementation_static_contract_review_authorized_next",
        'implementation_authorized_next": False',
        'fixed_dp_candidate_generation_authorized_next": False',
        'training_execution_authorized_next": False',
        "future_generator_script",
    ]
    text = "\n".join(snippets if include_contracts else snippets[:-1])
    return _write(path, text + "\n")


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "implementation_static_contract_review_authorized_next",
                "implementation_authorized_next",
                "fixed_dp_candidate_generation_authorized_next",
                "future_generator_script",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "default_off_member_source_generation_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        implementation_plan_artifact_dir=_artifact(tmp_path / "artifact"),
        implementation_plan_script=_source_script(tmp_path / "plan.py"),
        implementation_plan_test=_source_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_default_off_member_source_generation_implementation_static_review_passes(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    contract = report["contract_summary"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert contract["future_generator_script"] == EXPECTED_FUTURE_GENERATOR_SCRIPT


def test_default_off_member_source_generation_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_default_off_member_source_generation_implementation_static_review_rejects_action_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_authorized_next"] = True

    report = build_report(
        implementation_plan_artifact_dir=_artifact(tmp_path / "artifact", mutation=leak),
        implementation_plan_script=_source_script(tmp_path / "plan.py"),
        implementation_plan_test=_source_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_fixed_dp_candidate_generation_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_default_off_member_source_generation_implementation_static_review_rejects_missing_behavior(
    tmp_path: Path,
) -> None:
    def remove_behavior(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["required_future_behavior"] = list(
            REQUIRED_FUTURE_BEHAVIOR[:-1]
        )

    report = build_report(
        implementation_plan_artifact_dir=_artifact(
            tmp_path / "artifact",
            mutation=remove_behavior,
        ),
        implementation_plan_script=_source_script(tmp_path / "plan.py"),
        implementation_plan_test=_source_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "required_future_behavior" in report["final_decision"]["failed_checks"]


def test_default_off_member_source_generation_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--implementation_plan_artifact_dir",
            str(_artifact(tmp_path / "artifact")),
            "--implementation_plan_script",
            str(_source_script(tmp_path / "plan.py")),
            "--implementation_plan_test",
            str(_source_test(tmp_path / "test_plan.py")),
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
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Static Contract Review" in output_md.read_text(encoding="utf-8")
