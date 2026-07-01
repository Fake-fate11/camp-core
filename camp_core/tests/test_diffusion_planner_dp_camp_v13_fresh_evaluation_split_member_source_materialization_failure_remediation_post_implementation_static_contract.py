from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_failure_remediation_post_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_MATERIALIZER_SCRIPT,
    EXPECTED_MATERIALIZER_TEST,
    FIXED_DP_HEAD,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_ARTIFACT_FILES,
    REQUIRED_SCRIPT_TERMS,
    REQUIRED_TEST_TERMS,
    SCHEMA_VERSION,
    SOURCE_IMPLEMENTATION_SCHEMA_VERSION,
    SOURCE_IMPLEMENTATION_STATUS,
    build_report,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "5f30c17a0bc758972b871fc1ea35b9559b9e4221"
IMPLEMENTATION_HEAD = "93ef4da053523eac00eeaa34ffa651544327e0f0"
MATERIALIZER_SCRIPT = REPO_ROOT / EXPECTED_MATERIALIZER_SCRIPT
MATERIALIZER_TEST = REPO_ROOT / EXPECTED_MATERIALIZER_TEST
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_implementation_"
    "complete"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": SOURCE_IMPLEMENTATION_SCHEMA_VERSION,
        "status": SOURCE_IMPLEMENTATION_STATUS,
        "passed": True,
        "script": EXPECTED_MATERIALIZER_SCRIPT,
        "test": EXPECTED_MATERIALIZER_TEST,
        "camp_head": IMPLEMENTATION_HEAD,
        "camp_origin_main": IMPLEMENTATION_HEAD,
        "dp_head": FIXED_DP_HEAD,
        "required_dp_head": FIXED_DP_HEAD,
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "py_compile_passed": True,
        "target_tests_passed": True,
        "implementation_only": True,
        "input_materialization_executed": False,
        "candidate_member_source_manifest_written": False,
        "training_split_manifest_roots_written": False,
        "validation_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
        "nonnegative_simplex_weights_only": True,
        "master_problem_remains_convex": True,
    }
    files = {
        "HEADS": "\n".join(
            [
                f"camp_head={IMPLEMENTATION_HEAD}",
                f"camp_origin_main={IMPLEMENTATION_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                "",
            ]
        ),
        "COMMAND": "py_compile plus target pytest\n",
        "run.exit": "0\n",
        "stdout.log": "294 passed\n",
        "stderr.log": "",
        "missing_input_materializer_implementation_report.md": "# ok\n",
        "SHA256SUMS": "0" * 64 + "  HEADS\n",
        "SHA256SUMS.check.exit": "0\n",
        "SHA256SUMS.check.stdout": "HEADS: OK\n",
        "SHA256SUMS.check.stderr": "",
    }
    if mutation is not None:
        mutation(files, report)
    for name in REQUIRED_ARTIFACT_FILES:
        if name == "missing_input_materializer_implementation_report.json":
            _write_json(root / name, report)
        else:
            _write(root / name, files.get(name, ""))
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "missing_input_materializer_implemented=True",
        "input_materialization_executed=False",
        "candidate_member_source_manifest_written=False",
        "training_split_manifest_roots_written=False",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK, dp_head: str = FIXED_DP_HEAD) -> dict[str, Any]:
    return build_report(
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        materializer_script_py=MATERIALIZER_SCRIPT,
        materializer_test_py=MATERIALIZER_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=dp_head,
    )


def test_post_implementation_static_review_authorizes_input_materialization_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["input_materialization_execution_authorized_next"] is True
    assert decision["candidate_member_source_manifest_materialization_authorized_next"] is True
    assert decision["training_split_manifest_roots_materialization_authorized_next"] is True
    assert decision["validation_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["candidate_operation"] == "fixed DP candidate reranking only"
    assert decision["score_expression"] == "score_k(w)=a_k^T w"
    assert report["artifact_summary"]["source_dp_head"] == FIXED_DP_HEAD
    assert report["artifact_summary"]["source_input_materialization_executed"] is False


def test_post_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_artifact_failure(
    tmp_path: Path,
) -> None:
    def fail_artifact(files: dict[str, str], report: dict[str, Any]) -> None:
        files["run.exit"] = "1\n"
        report["passed"] = False

    report = build_report(
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=fail_artifact),
        materializer_script_py=MATERIALIZER_SCRIPT,
        materializer_test_py=MATERIALIZER_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_run_exit_zero" in report["final_decision"]["failed_checks"]
    assert "source_passed" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_source_execution_leak(
    tmp_path: Path,
) -> None:
    def leak(files: dict[str, str], report: dict[str, Any]) -> None:
        report["input_materialization_executed"] = True
        report["training_execution_authorized_next"] = True

    report = build_report(
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=leak),
        materializer_script_py=MATERIALIZER_SCRIPT,
        materializer_test_py=MATERIALIZER_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocks_input_materialization_executed" in report["final_decision"]["failed_checks"]
    assert "source_blocks_training_execution_authorized_next" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_materializer_contract_removal(
    tmp_path: Path,
) -> None:
    missing = "--enable_v13_fresh_evaluation_split_member_source_missing_input_materializer"
    script = tmp_path / "materializer.py"
    script.write_text(
        MATERIALIZER_SCRIPT.read_text(encoding="utf-8").replace(missing, "--removed"),
        encoding="utf-8",
    )
    report = build_report(
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        materializer_script_py=script,
        materializer_test_py=MATERIALIZER_TEST,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"materializer_contains_{missing.strip('-')}" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_missing_test_contract(
    tmp_path: Path,
) -> None:
    missing = REQUIRED_TEST_TERMS[0]
    test_file = tmp_path / "test_materializer.py"
    test_file.write_text(
        MATERIALIZER_TEST.read_text(encoding="utf-8").replace(missing, "removed_test"),
        encoding="utf-8",
    )
    report = build_report(
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        materializer_script_py=MATERIALIZER_SCRIPT,
        materializer_test_py=test_file,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"test_contains_{missing}" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_main_writes_reports(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--implementation_artifact_dir",
            str(_artifact(tmp_path / "artifact")),
            "--materializer_script_py",
            str(MATERIALIZER_SCRIPT),
            "--materializer_test_py",
            str(MATERIALIZER_TEST),
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
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["status"] == PASS_STATUS
    assert "input_materialization_execution_authorized_next: True" in output_md.read_text(
        encoding="utf-8"
    )
