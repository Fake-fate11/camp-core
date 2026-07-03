from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_no_promotion_closeout import (  # noqa: E501
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    FIXED_DP_HEAD,
    READY_STATUS,
    SCORE_EXPRESSION,
    SOURCE_RECORD_AUTHORIZED_CURRENT_WORK,
    SOURCE_RECORD_AUTHORIZED_NEXT_WORK,
    SOURCE_RECORD_READY_STATUS,
    SOURCE_RECORD_SCHEMA,
    build_report,
    main,
)


CAMP_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def test_no_promotion_closeout_review_passes(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)

    report = _build(tmp_path, fixture)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["no_promotion_closeout_complete"] is True
    assert (
        report["final_decision"][
            "future_promotion_requires_new_eof_and_explicit_authorization"
        ]
        is True
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False
    assert report["final_decision"]["deployment_authorized"] is False
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False
    assert not report["final_decision"]["failed_checks"]
    assert report["source_summary"]["status"] == SOURCE_RECORD_READY_STATUS


def test_no_promotion_closeout_review_requires_explicit_enable(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)

    report = _build(tmp_path, fixture, enabled=False)

    assert report["final_decision"]["passed"] is False
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_no_promotion_closeout_review_authorization_missing"
    )
    assert "no_promotion_closeout_review_enabled" in report["final_decision"]["failed_checks"]


def test_no_promotion_closeout_review_rejects_promotion_leak(tmp_path: Path) -> None:
    record = _source_record()
    record["final_decision"]["selector_promotion_authorized"] = True
    fixture = _write_fixture(tmp_path, record=record)

    report = _build(tmp_path, fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "boundary_contract_failure"
    assert "source_decision_selector_promotion_authorized" in report["final_decision"][
        "failed_checks"
    ]


def test_no_promotion_closeout_review_rejects_latest_eof_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, next_work="wrong_next_gate")

    report = _build(tmp_path, fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]


def test_no_promotion_closeout_review_rejects_source_hash_drift(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path)
    fixture["record_md"].write_text("drifted\n", encoding="utf-8")

    report = _build(tmp_path, fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["failure_class"] == "source_closeout_hash_mismatch"
    assert "record_sha256s_md" in report["final_decision"]["failed_checks"]
    assert "artifact_sha256s_md" in report["final_decision"]["failed_checks"]


def test_no_promotion_closeout_review_cli_writes_outputs(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)
    output_dir = tmp_path / "cli_out"

    exit_code = main(
        [
            "--closeout_artifact_dir",
            str(fixture["artifact_dir"]),
            "--closeout_record_json",
            str(fixture["record_json"]),
            "--closeout_record_md",
            str(fixture["record_md"]),
            "--closeout_record_sha256s",
            str(fixture["record_sha256s"]),
            "--v14_audit_md",
            str(fixture["audit_md"]),
            "--current_status_md",
            str(fixture["status_md"]),
            "--output_dir",
            str(output_dir),
            "--current_camp_head",
            CURRENT_HEAD,
            "--current_camp_origin_main",
            CURRENT_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v14_runtime_no_promotion_closeout_review",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "runtime_no_promotion_closeout_review.json").is_file()
    assert (output_dir / "runtime_no_promotion_closeout_review.md").is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _build(
    tmp_path: Path,
    fixture: dict[str, Path],
    *,
    enabled: bool = True,
) -> dict[str, Any]:
    return build_report(
        closeout_artifact_dir=fixture["artifact_dir"],
        closeout_record_json=fixture["record_json"],
        closeout_record_md=fixture["record_md"],
        closeout_record_sha256s=fixture["record_sha256s"],
        v14_audit_md=fixture["audit_md"],
        current_status_md=fixture["status_md"],
        output_dir=tmp_path / "out",
        current_camp_head=CURRENT_HEAD,
        current_camp_origin_main=CURRENT_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=enabled,
    )


def _write_fixture(
    tmp_path: Path,
    *,
    record: dict[str, Any] | None = None,
    next_work: str = SOURCE_RECORD_AUTHORIZED_NEXT_WORK,
) -> dict[str, Path]:
    artifact_dir = tmp_path / "artifact"
    record_dir = artifact_dir / "record"
    record_dir.mkdir(parents=True)
    record_json = record_dir / "runtime_no_promotion_closeout_record.json"
    record_md = record_dir / "runtime_no_promotion_closeout_record.md"
    record_sha256s = record_dir / "SHA256SUMS"
    record_json.write_text(
        json.dumps(record or _source_record(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    record_md.write_text("# closeout record\n", encoding="utf-8")
    record_sha256s.write_text(
        "\n".join(
            [
                f"{_sha256(record_json)}  {record_json.name}",
                f"{_sha256(record_md)}  {record_md.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "HEADS").write_text(
        "\n".join(
            [
                f"camp_head={CAMP_HEAD}",
                f"camp_origin_main={CAMP_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                "source_promotion_decision_from_evidence_package_plan_artifact=/tmp/plan",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "COMMAND").write_text("record command\n", encoding="utf-8")
    (artifact_dir / "stdout.txt").write_text("{}\n", encoding="utf-8")
    (artifact_dir / "stderr.txt").write_text("", encoding="utf-8")
    (artifact_dir / "run.exit").write_text("0\n", encoding="utf-8")
    (artifact_dir / "SHA256SUMS").write_text(
        "\n".join(
            [
                f"{_sha256(artifact_dir / 'COMMAND')}  ./COMMAND",
                f"{_sha256(artifact_dir / 'HEADS')}  ./HEADS",
                f"{_sha256(record_json)}  ./record/{record_json.name}",
                f"{_sha256(record_md)}  ./record/{record_md.name}",
                f"{_sha256(record_sha256s)}  ./record/SHA256SUMS",
                f"{_sha256(artifact_dir / 'run.exit')}  ./run.exit",
                f"{_sha256(artifact_dir / 'stderr.txt')}  ./stderr.txt",
                f"{_sha256(artifact_dir / 'stdout.txt')}  ./stdout.txt",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    audit_md = tmp_path / "audit.md"
    status_md = tmp_path / "status.md"
    text = "\n".join(
        [
            "no-promotion closeout review",
            f"current_v14_status={SOURCE_RECORD_READY_STATUS}",
            "default_off_shadow_selector_runtime_no_promotion_closeout_recorded=True",
            "default_off_shadow_selector_runtime_no_promotion_closeout_review_authorized=True",
            f"next_work_target={next_work}",
            "",
        ]
    )
    audit_md.write_text(text, encoding="utf-8")
    status_md.write_text(text, encoding="utf-8")
    return {
        "artifact_dir": artifact_dir,
        "record_json": record_json,
        "record_md": record_md,
        "record_sha256s": record_sha256s,
        "audit_md": audit_md,
        "status_md": status_md,
    }


def _source_record() -> dict[str, Any]:
    final_decision: dict[str, Any] = {
        "authorized_current_work": SOURCE_RECORD_AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": SOURCE_RECORD_AUTHORIZED_NEXT_WORK,
        "failed_checks": [],
        "failure_class": None,
        "no_promotion_closeout_record_ready": True,
        "no_promotion_closeout_recorded": True,
        "no_promotion_closeout_review_authorized": True,
        "passed": True,
        "promotion_recommended": False,
        "recommendation": "do_not_promote_from_current_evidence_package_alone",
        "score_expression": SCORE_EXPRESSION,
        "status": SOURCE_RECORD_READY_STATUS,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        final_decision[name] = False
    return {
        "analysis": {
            "candidate_generation": False,
            "current_camp_head": CAMP_HEAD,
            "current_camp_origin_main": CAMP_HEAD,
            "current_dp_head": FIXED_DP_HEAD,
            "deployment_executed": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "record_only": True,
            "replay_execution": False,
            "safety_or_camp_over_dp_claim": False,
            "training_execution": False,
        },
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": final_decision,
        "no_promotion_closeout_record": {
            "evidence_class": "static_default_off_shadow_evidence_not_deployment_or_safety_proof",
            "final_selector_state": "default_off_shadow_only_not_promoted",
            "promotion_recommended": False,
            "record_decision": "close_current_evidence_package_without_promotion",
        },
        "record_checks": [{"name": "ok", "passed": True}],
        "schema_version": SOURCE_RECORD_SCHEMA,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
