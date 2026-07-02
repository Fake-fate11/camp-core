from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_IMPLEMENTATION_TARGET,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    SOURCE_FAILURE_CLASS,
    SOURCE_REJECT_STATUS,
    SOURCE_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "9c9734f0a83179377a777ad7dc0750842cbe0286"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _preflight(path: Path, dp_repo: Path, *, mutation: Any | None = None) -> Path:
    missing = dp_repo / "tools" / "camp_fixed_candidate_generation.py"
    decision = {
        "status": SOURCE_REJECT_STATUS,
        "passed": False,
        "failed_checks": ["dp_entrypoint_exists"],
        "failure_class": SOURCE_FAILURE_CLASS,
        "recommended_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_execution_preflight_passed": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "execution_preflight": {
            "candidate_output_dir": str(path.parent / "candidate_output"),
            "dp_entrypoint_exists": False,
            "dp_entrypoint_path": str(missing),
            "dp_repo": str(dp_repo),
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _source_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "dp_entrypoint_exists",
                "missing_fixed_dp_candidate_generation_entrypoint",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "",
            ]
        ),
    )


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_execution_preflight_rejects_missing_dp_entrypoint",
                "dp_entrypoint_exists",
                "missing_fixed_dp_candidate_generation_entrypoint",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_execution_preflight_rejected_missing_fixed_dp_entrypoint",
        "fixed_dp_candidate_generation_execution_preflight_rejected=True",
        "fixed_dp_candidate_generation_execution_preflight_failure_class=missing_fixed_dp_candidate_generation_entrypoint",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(tmp_path: Path, *, missing_entrypoint: bool = True) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    if not missing_entrypoint:
        _write(dp_repo / "tools" / "camp_fixed_candidate_generation.py", "print('unexpected')\n")
    return camp_repo, dp_repo


def _build(tmp_path: Path, *, missing_entrypoint: bool = True) -> dict[str, Any]:
    camp_repo, dp_repo = _repos(tmp_path, missing_entrypoint=missing_entrypoint)
    return build_report(
        preflight_json=_preflight(tmp_path / "preflight.json", dp_repo),
        preflight_artifact_dir=tmp_path,
        preflight_script=_source_script(tmp_path / "preflight.py"),
        preflight_test=_source_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )


def test_entrypoint_contract_remediation_plan_authorizes_static_review_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["entrypoint_contract_remediation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["entrypoint_contract_remediation_plan_ready"] is True
    assert decision["entrypoint_contract_remediation_static_contract_review_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert plan["remediation_scope"] == "CAMP-owned entrypoint contract only"
    assert plan["dp_repo_modification_allowed"] is False
    assert plan["dp_config_weight_checkpoint_change_allowed"] is False
    assert plan["future_implementation_target"] == FUTURE_IMPLEMENTATION_TARGET
    assert plan["execution_authorized_by_this_gate"] is False
    assert "candidate_tensor_hash" in plan["required_zero_overlap_keys"]
    assert "replace_dp_repo_tools_entrypoint_with_camp_owned_adapter" in plan[
        "required_contract_changes"
    ]


def test_entrypoint_contract_remediation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    camp_repo, dp_repo = _repos(tmp_path)
    report = build_report(
        preflight_json=_preflight(tmp_path / "preflight.json", dp_repo),
        preflight_artifact_dir=tmp_path,
        preflight_script=_source_script(tmp_path / "preflight.py"),
        preflight_test=_source_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_entrypoint_contract_remediation_plan_rejects_nonmatching_failure(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["failure_class"] = "other"

    camp_repo, dp_repo = _repos(tmp_path)
    report = build_report(
        preflight_json=_preflight(tmp_path / "preflight.json", dp_repo, mutation=mutate),
        preflight_artifact_dir=tmp_path,
        preflight_script=_source_script(tmp_path / "preflight.py"),
        preflight_test=_source_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_failure_class" in report["final_decision"]["failed_checks"]


def test_entrypoint_contract_remediation_plan_rejects_execution_auth_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    camp_repo, dp_repo = _repos(tmp_path)
    report = build_report(
        preflight_json=_preflight(tmp_path / "preflight.json", dp_repo, mutation=mutate),
        preflight_artifact_dir=tmp_path,
        preflight_script=_source_script(tmp_path / "preflight.py"),
        preflight_test=_source_test(tmp_path / "test_preflight.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_entrypoint_contract_remediation_plan_rejects_if_entrypoint_now_exists(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, missing_entrypoint=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "actual_dp_entrypoint_still_missing" in report["final_decision"]["failed_checks"]


def test_entrypoint_contract_remediation_plan_main_writes_outputs(tmp_path: Path) -> None:
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    exit_code = main(
        [
            "--preflight_json",
            str(_preflight(tmp_path / "preflight.json", dp_repo)),
            "--preflight_artifact_dir",
            str(tmp_path),
            "--preflight_script",
            str(_source_script(tmp_path / "preflight.py")),
            "--preflight_test",
            str(_source_test(tmp_path / "test_preflight.py")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--dp_repo",
            str(dp_repo),
            "--camp_repo",
            str(camp_repo),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert FUTURE_IMPLEMENTATION_TARGET in output_md.read_text(encoding="utf-8")
