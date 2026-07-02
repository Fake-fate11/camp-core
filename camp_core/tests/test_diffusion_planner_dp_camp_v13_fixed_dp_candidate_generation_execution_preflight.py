from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BUILDER_READY_STATUS,
    BUILDER_SCHEMA_VERSION,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    MANIFEST_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    REMEDIATION_NEXT_WORK,
    SCHEMA_VERSION,
    SOURCE_READY_STATUS,
    SOURCE_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "c21764469718734aac25e80d4cd08cadbf0547a9"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _builder_artifact(
    root: Path,
    *,
    dp_entrypoint: str = "tools/camp_fixed_candidate_generation.py",
    mutation: Any | None = None,
) -> Path:
    generated = root / "generated"
    manifest = generated / "fixed_dp_candidate_generation_manifest.json"
    runbook = generated / "run_fixed_dp_candidate_generation.sh"
    _write_json(
        manifest,
        {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "candidate_generation_by_camp": False,
            "dp_entrypoint": dp_entrypoint,
            "dp_modification": False,
            "fixed_dp_candidate_generation_executed": False,
            "required_dp_head": FIXED_DP_HEAD,
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
            "target_candidates_per_member": 8,
            "target_min_candidate_members": 1024,
        },
    )
    _write(
        runbook,
        "\n".join(
            [
                f"if [ \"${{{GUARD_ENV_VAR}:-}}\" != \"1\" ]; then",
                "  exit 40",
                "fi",
                "echo 'DP HEAD mismatch' >&2",
                "--forbid_formal_seeds 11 12 13",
                "--write_zero_overlap_registries",
                "",
            ]
        ),
    )
    decision = {
        "status": BUILDER_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "fixed_dp_candidate_generation_executed": False,
    }
    payload = {
        "schema_version": BUILDER_SCHEMA_VERSION,
        "generation_builder": {
            "manifest_written": True,
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
            "runbook_guard_env_var": GUARD_ENV_VAR,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload, manifest, runbook)
    return _write_json(root / "builder.json", payload)


def _post_review(path: Path, builder_json: Path, *, mutation: Any | None = None) -> Path:
    manifest = builder_json.parent / "generated" / "fixed_dp_candidate_generation_manifest.json"
    runbook = builder_json.parent / "generated" / "run_fixed_dp_candidate_generation.sh"
    decision = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_post_implementation_static_contract_review_passed": True,
        "fixed_dp_candidate_generation_execution_preflight_authorized_next": True,
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
        "artifact_summary": {
            "builder_artifact_dir": str(builder_json.parent),
            "builder_json": str(builder_json),
            "manifest_path": str(manifest),
            "runbook_path": str(runbook),
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_post_implementation_static_contract_review_passed",
        "fixed_dp_candidate_generation_execution_preflight_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(tmp_path: Path, *, entrypoint: bool = True) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    if entrypoint:
        _write(dp_repo / "tools" / "camp_fixed_candidate_generation.py", "print('fixed dp')\n")
    return camp_repo, dp_repo


def _report(tmp_path: Path, *, entrypoint: bool = True) -> dict[str, Any]:
    builder_json = _builder_artifact(tmp_path / "builder")
    post_review = _post_review(tmp_path / "post_review.json", builder_json)
    camp_repo, dp_repo = _repos(tmp_path, entrypoint=entrypoint)
    return build_report(
        post_review_json=post_review,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )


def test_execution_preflight_disabled_has_no_next_work(tmp_path: Path) -> None:
    report = build_report(
        post_review_json=tmp_path / "missing.json",
        v13_audit_md=tmp_path / "missing.md",
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=tmp_path / "dp",
        camp_repo=tmp_path / "camp",
        enabled=False,
    )

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["fixed_dp_candidate_generation_executed"] is False


def test_execution_preflight_authorizes_fixed_dp_execution_only(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    preflight = report["execution_preflight"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_execution_preflight_passed"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    command = preflight["planned_command"]
    assert GUARD_ENV_VAR in " ".join(command)
    assert "--forbid_full36" in command
    assert "--forbid_formal_seeds" in command
    assert "--write_zero_overlap_registries" in command
    assert "fixed DP candidate reranking only" in command
    assert SCORE_EXPRESSION in command


def test_execution_preflight_rejects_missing_dp_entrypoint(tmp_path: Path) -> None:
    report = _report(tmp_path, entrypoint=False)
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert "dp_entrypoint_exists" in decision["failed_checks"]
    assert decision["authorized_next_work"] is None
    assert decision["recommended_next_work"] == REMEDIATION_NEXT_WORK
    assert decision["failure_class"] == "missing_fixed_dp_candidate_generation_entrypoint"
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False


def test_execution_preflight_rejects_wrong_audit_target(tmp_path: Path) -> None:
    builder_json = _builder_artifact(tmp_path / "builder")
    post_review = _post_review(tmp_path / "post_review.json", builder_json)
    camp_repo, dp_repo = _repos(tmp_path)

    report = build_report(
        post_review_json=post_review,
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] is False


def test_execution_preflight_rejects_source_execution_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    builder_json = _builder_artifact(tmp_path / "builder")
    post_review = _post_review(tmp_path / "post_review.json", builder_json, mutation=leak)
    camp_repo, dp_repo = _repos(tmp_path)

    report = build_report(
        post_review_json=post_review,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        candidate_output_dir=tmp_path / "candidate_output",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_execution_preflight_main_writes_reports_and_runbook(tmp_path: Path) -> None:
    builder_json = _builder_artifact(tmp_path / "builder")
    post_review = _post_review(tmp_path / "post_review.json", builder_json)
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    output_runbook = tmp_path / "run.sh"

    exit_code = main(
        [
            "--post_review_json",
            str(post_review),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--candidate_output_dir",
            str(tmp_path / "candidate_output"),
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
            "--output_runbook",
            str(output_runbook),
            "--enable_fixed_dp_candidate_generation_execution_preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    runbook = output_runbook.read_text(encoding="utf-8")
    assert GUARD_ENV_VAR in runbook
    assert "DP HEAD mismatch" in runbook
    assert "Candidate output dir already exists" in runbook
