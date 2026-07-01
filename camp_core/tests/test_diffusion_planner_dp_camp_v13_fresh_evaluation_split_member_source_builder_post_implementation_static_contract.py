from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "7f6f4725d8c4d13694ac31c1fda7befd44a8aac4"
IMPLEMENTATION_HEAD = "7ba3868a51fe5c2bd33f6df10dc117d85ad480bc"
BUILDER_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder.py"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "HEADS.txt": "\n".join(
            [
                f"camp_head={IMPLEMENTATION_HEAD}",
                f"camp_origin_main={IMPLEMENTATION_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                f"required_dp_head={FIXED_DP_HEAD}",
                f"artifact={root}",
                "",
            ]
        ),
        "COMMAND.sh": "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "PY=/root/autodl-tmp/dp312_venv/bin/python",
                '"$PY" -m py_compile scripts/integrations/build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source.py',
                '"$PY" -m pytest camp_core/tests/test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder.py -q',
                "",
            ]
        ),
        "run.exit": "0\n",
        "stdout.txt": ".......... [100%]\n301 passed in 3.71s\n",
        "stderr.txt": "",
        "SHA256SUMS.txt": "0" * 64 + "  HEADS.txt\n",
        "SHA256SUMS.check.exit": "0\n",
        "SHA256SUMS.check.stdout.txt": "HEADS.txt: OK\n",
        "SHA256SUMS.check.stderr.txt": "",
    }
    if mutation is not None:
        mutation(files)
    for name, text in files.items():
        _write(root / name, text)
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation_implementation_complete",
                f"next_work_target={target}",
                "fresh_evaluation_split_member_source_remediation_post_implementation_static_contract_review_authorized_next=True",
                "fresh_member_selection_execution_authorized_next=False",
                "fresh_evaluation_split_evaluation_authorized_next=False",
                "data_preparation_authorized_next=False",
                "training_preflight_authorized_next=False",
                "training_execution_authorized_by_current_boundary=False",
                "runtime_shadow_selector_execution_authorized=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_modification_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "reference_blend_authorized=False",
                "guidance_authorized=False",
                "postprocess_or_postselection_authorized=False",
                "closed_loop_outcome_authorized=False",
                "online_selector_change_authorized=False",
                "executed_trajectory_change_authorized=False",
                "selector_promotion_authorized=False",
                "atom_promotion_authorized=False",
                "deployment_authorized=False",
                "deployable_checkpoint_claim_authorized=False",
                "safety_benefit_claim_authorized=False",
                "camp_over_dp_top1_claim_authorized=False",
                "",
            ]
        ),
    )


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_post_static_review_authorizes_validation_preflight_only(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["validation_preflight_authorized_next"] is True
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["fresh_evaluation_split_evaluation_authorized_next"] is False
    assert decision["data_preparation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["implementation_artifact_summary"]["dp_head"] == FIXED_DP_HEAD
    assert report["implementation_artifact_summary"]["stdout_contains_301_passed"] is True


def test_post_static_review_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_artifact_failure(tmp_path: Path) -> None:
    def fail_artifact(files: dict[str, str]) -> None:
        files["run.exit"] = "1\n"

    report = build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=fail_artifact),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_artifact_exit_zero" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_dp_head_drift(tmp_path: Path) -> None:
    report = build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_builder_contract_removal(tmp_path: Path) -> None:
    script = tmp_path / "builder.py"
    script.write_text(
        BUILDER_SCRIPT.read_text(encoding="utf-8").replace(
            "--enable_v13_fresh_evaluation_split_member_source_builder",
            "--removed",
        ),
        encoding="utf-8",
    )
    report = build_report(
        member_source_builder_script_py=script,
        member_source_builder_test_py=BUILDER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "builder_contains_enable_v13_fresh_evaluation_split_member_source_builder"
        in report["final_decision"]["failed_checks"]
    )


def test_post_static_review_rejects_missing_test_contract(tmp_path: Path) -> None:
    test_file = tmp_path / "test_builder.py"
    test_file.write_text(
        BUILDER_TEST.read_text(encoding="utf-8").replace(
            "test_member_source_builder_rejects_rejected_source_reuse",
            "test_removed",
        ),
        encoding="utf-8",
    )
    report = build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=test_file,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "test_contains_test_member_source_builder_rejects_rejected_source_reuse"
        in report["final_decision"]["failed_checks"]
    )


def test_post_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "Validation preflight authorized next: `True`" in markdown
    assert "Fresh member selection authorized next: `False`" in markdown
    assert "Training authorized next: `False`" in markdown
    assert "read-only" in markdown
    assert "safety/CAMP-over-DP claims" in markdown


def test_post_static_review_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"
    artifact = _artifact(tmp_path / "artifact")
    audit = _audit(tmp_path / "audit.md")

    exit_code = main(
        [
            "--member_source_builder_script_py",
            str(BUILDER_SCRIPT),
            "--member_source_builder_test_py",
            str(BUILDER_TEST),
            "--implementation_artifact_dir",
            str(artifact),
            "--v13_audit_md",
            str(audit),
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
    assert "read-only" in output_md.read_text(encoding="utf-8")


def test_post_static_review_script_has_cli_entrypoint() -> None:
    source = (
        REPO_ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder_post_implementation_static_contract.py"
    ).read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source
