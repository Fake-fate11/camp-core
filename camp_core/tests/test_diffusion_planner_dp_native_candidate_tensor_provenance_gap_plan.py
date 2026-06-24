from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_dp_native_candidate_tensor_provenance_gap import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REQUIRED_GAPS = [
    "candidate_tensor_hash_missing",
    "full_candidate_coordinate_tensor_artifact_missing",
    "raw_dp_pre_camp_candidate_set_immutability_not_proven",
    "reference_blend_selection_effect_requires_provenance_separation",
    "full_candidate_tensor_mutation_absence_not_proven",
]


def _evidence_audit(
    *,
    complete: bool = True,
    ready: bool = False,
    gaps: list[str] | None = None,
    blocked: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": "dp_native_candidate_reranking_fixed_artifact_evidence_audit_complete",
            "passed": complete,
            "evidence_audit_complete": complete,
            "dp_native_reranking_evidence_ready": ready,
            "candidate_tensor_provenance_gap": bool(gaps if gaps is not None else REQUIRED_GAPS),
            "authorized_next_work": (
                "dp_native_candidate_tensor_provenance_gap_design_plan_only"
            ),
            "evidence_gaps": gaps if gaps is not None else list(REQUIRED_GAPS),
            "candidate_generation_execution_authorized": blocked,
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        }
    }


def test_provenance_gap_plan_ready() -> None:
    report = build_report(
        evidence_audit=_evidence_audit(),
        evidence_audit_json="/tmp/evidence.json",
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["provenance_gap_design_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_authorized_now"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["required_provenance_stages"][0].startswith("dp_sampler_output")
    assert "candidate_tensor_sha256" in plan["required_payload_fields"]
    assert "pre_post_tensor_hash_equal" in plan["required_payload_fields"]


def test_provenance_gap_plan_rejects_completed_ready_source() -> None:
    report = build_report(evidence_audit=_evidence_audit(ready=True, gaps=[]))

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_not_ready" in failed
    assert "source_has_provenance_gap" in failed


def test_provenance_gap_plan_rejects_missing_required_gap() -> None:
    report = build_report(
        evidence_audit=_evidence_audit(gaps=["candidate_tensor_hash_missing"])
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_gap_full_candidate_coordinate_tensor_artifact_missing" in failed
    assert "source_gap_reference_blend_selection_effect_requires_provenance_separation" in failed


def test_provenance_gap_plan_rejects_blocked_authorization() -> None:
    report = build_report(evidence_audit=_evidence_audit(blocked=True))

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_authorizations" in failed


def test_provenance_gap_plan_markdown_boundary() -> None:
    markdown = render_markdown(build_report(evidence_audit=_evidence_audit()))

    assert "DP-Native Candidate Tensor Provenance Gap Design Plan" in markdown
    assert "Implementation authorized now: `False`" in markdown
    assert "Replay authorized: `False`" in markdown
    assert "candidate_tensor_sha256" in markdown
    assert "pre_post_tensor_hash_equal" in markdown


def test_provenance_gap_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_json = tmp_path / "evidence.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    evidence_json.write_text(json.dumps(_evidence_audit()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "provenance-gap-plan",
            "--evidence_audit_json",
            str(evidence_json),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Tensor Provenance Gap Design Plan" in output_md.read_text(
        encoding="utf-8"
    )
