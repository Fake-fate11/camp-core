from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_post_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "3b189f1e8458f50a173c7305058ee622b9b0997b"
IMPLEMENTATION_HEAD = "efebbf47c8354b190edb73a78cf64420d390d34c"
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
MATERIALIZER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materializer.py"
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
                "",
            ]
        ),
        "COMMAND.sh": "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "/root/autodl-tmp/dp312_venv/bin/python -m py_compile scripts/integrations/build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source.py",
                "/root/autodl-tmp/dp312_venv/bin/python -m pytest -q camp_core/tests/test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder.py camp_core/tests/test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materializer.py camp_core/tests/test_diffusion_planner_v13_iteration_audit.py",
                "",
            ]
        ),
        "run.exit": "0\n",
        "stdout.txt": ".............................. [100%]\n317 passed in 4.31s\n",
        "stderr.txt": "",
        "SHA256SUMS": "0" * 64 + "  HEADS.txt\n",
        "sha256sums.check.exit": "0\n",
        "sha256sums.check.stdout": "HEADS.txt: OK\n",
        "sha256sums.check.stderr": "",
    }
    if mutation is not None:
        mutation(files)
    for name, text in files.items():
        _write(root / name, text)
    return root


def _audit(
    path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    training_leak: bool = False,
) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_implementation_complete=True",
        "fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_post_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        value = training_leak and flag == "training_execution_authorized_by_current_boundary"
        lines.append(f"{flag}={value}")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=BUILDER_TEST,
        member_source_materializer_test_py=MATERIALIZER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_executed_index_post_implementation_static_contract_passes(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_member_source_rematerialization_plan_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert review["legacy_non_default_off_selection_logs_rejected"] is True
    assert review["required_builder_terms_missing"] == []
    assert review["required_builder_test_terms_missing"] == []
    assert review["required_materializer_test_terms_missing"] == []
    assert report["implementation_artifact_summary"]["dp_head"] == FIXED_DP_HEAD
    assert report["implementation_artifact_summary"]["stdout_contains_317_passed"] is True


def test_executed_index_post_implementation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_executed_index_post_implementation_static_contract_rejects_artifact_failure(
    tmp_path: Path,
) -> None:
    def fail_artifact(files: dict[str, str]) -> None:
        files["run.exit"] = "1\n"

    report = build_report(
        member_source_builder_script_py=BUILDER_SCRIPT,
        member_source_builder_test_py=BUILDER_TEST,
        member_source_materializer_test_py=MATERIALIZER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact", mutation=fail_artifact),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_artifact_exit_zero" in report["final_decision"]["failed_checks"]


def test_executed_index_post_implementation_static_contract_rejects_contract_drift(
    tmp_path: Path,
) -> None:
    script = tmp_path / "builder.py"
    script.write_text(
        BUILDER_SCRIPT.read_text(encoding="utf-8").replace(
            "default_off_contract_executed_index_not_dp_top1",
            "removed_default_off_contract",
        ),
        encoding="utf-8",
    )

    report = build_report(
        member_source_builder_script_py=script,
        member_source_builder_test_py=BUILDER_TEST,
        member_source_materializer_test_py=MATERIALIZER_TEST,
        implementation_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "builder_contains_default_off_contract_executed_index_not_dp_top1"
        in report["final_decision"]["failed_checks"]
    )


def test_executed_index_post_implementation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"

    exit_code = main(
        [
            "--member_source_builder_script_py",
            str(BUILDER_SCRIPT),
            "--member_source_builder_test_py",
            str(BUILDER_TEST),
            "--member_source_materializer_test_py",
            str(MATERIALIZER_TEST),
            "--implementation_artifact_dir",
            str(_artifact(tmp_path / "artifact")),
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
    assert "fresh member-source rematerialization" in output_md.read_text(
        encoding="utf-8"
    )
