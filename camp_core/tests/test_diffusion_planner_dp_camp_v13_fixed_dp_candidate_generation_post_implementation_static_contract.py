from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    GUARD_ENV_VAR,
    MANIFEST_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "7b9d96daa16815cc03caabb70c80bbd6abab18c9"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    generated = root / "generated"
    manifest = generated / "fixed_dp_candidate_generation_manifest.json"
    runbook = generated / "run_fixed_dp_candidate_generation.sh"
    _write_json(
        manifest,
        {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "dp_modification": False,
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
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
        "status": "dp_camp_v13_fixed_dp_candidate_generation_builder_complete",
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fixed_dp_candidate_generation_implementation_complete": True,
        "post_implementation_static_contract_review_authorized_next": True,
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
        "training_executed": False,
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
        "schema_version": "dp_camp_v13_fixed_dp_candidate_generation_builder_v1",
        "generation_builder": {
            "manifest_written": True,
            "runbook_guard_env_var": GUARD_ENV_VAR,
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
        },
        "output_paths": {
            "manifest": str(manifest),
            "runbook": str(runbook),
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload, manifest, runbook)
    return _write_json(root / "builder.json", payload)


def _source_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE",
                "DP HEAD mismatch",
                "--forbid_formal_seeds 11 12 13",
                "--write_zero_overlap_registries",
                'fixed_dp_candidate_generation_executed": False',
                "",
            ]
        ),
    )


def _source_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "fixed_dp_candidate_generation_executed",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "DP HEAD mismatch",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fixed_dp_candidate_generation_implementation_complete",
        "fixed_dp_candidate_generation_post_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        builder_json=_artifact(tmp_path / "artifact"),
        builder_artifact_dir=tmp_path / "artifact",
        builder_script=_source_script(tmp_path / "builder.py"),
        builder_test=_source_test(tmp_path / "test_builder.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_post_implementation_static_review_authorizes_execution_preflight_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    summary = report["artifact_summary"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_post_implementation_static_contract_review_passed"] is True
    assert decision["fixed_dp_candidate_generation_execution_preflight_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert summary["runbook_guard_env_var"] == GUARD_ENV_VAR


def test_post_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_execution_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any], manifest: Path, runbook: Path) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_execution_authorized_next"] = True

    report = build_report(
        builder_json=_artifact(tmp_path / "artifact", mutation=leak),
        builder_artifact_dir=tmp_path / "artifact",
        builder_script=_source_script(tmp_path / "builder.py"),
        builder_test=_source_test(tmp_path / "test_builder.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbids_fixed_dp_candidate_generation_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_post_implementation_static_review_rejects_missing_manifest(tmp_path: Path) -> None:
    def remove_manifest(payload: dict[str, Any], manifest: Path, runbook: Path) -> None:
        manifest.unlink()

    report = build_report(
        builder_json=_artifact(tmp_path / "artifact", mutation=remove_manifest),
        builder_artifact_dir=tmp_path / "artifact",
        builder_script=_source_script(tmp_path / "builder.py"),
        builder_test=_source_test(tmp_path / "test_builder.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "manifest_exists" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_runbook_guard_removed(tmp_path: Path) -> None:
    def remove_guard(payload: dict[str, Any], manifest: Path, runbook: Path) -> None:
        runbook.write_text("echo unsafe\n", encoding="utf-8")

    report = build_report(
        builder_json=_artifact(tmp_path / "artifact", mutation=remove_guard),
        builder_artifact_dir=tmp_path / "artifact",
        builder_script=_source_script(tmp_path / "builder.py"),
        builder_test=_source_test(tmp_path / "test_builder.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runbook_guard_env_present" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Fixed-DP Candidate Generation Post-Implementation Static Contract Review" in markdown
    assert "Execution preflight authorized next: `True`" in markdown
    assert "Fixed-DP generation execution authorized next: `False`" in markdown
    assert "Fixed-DP generation executed: `False`" in markdown
    assert "CAMP candidate generation authorized: `False`" in markdown


def test_post_implementation_static_review_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--builder_json",
            str(_artifact(tmp_path / "artifact")),
            "--builder_artifact_dir",
            str(tmp_path / "artifact"),
            "--builder_script",
            str(_source_script(tmp_path / "builder.py")),
            "--builder_test",
            str(_source_test(tmp_path / "test_builder.py")),
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
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Fixed-DP Candidate Generation Post-Implementation Static Contract Review"
    )
