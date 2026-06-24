from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_dp_native_candidate_reranking_after_materialized_generator_rejection import (
    AUTHORIZED_NEXT_WORK,
    EXPECTED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


SOURCE_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_"
    "comfort_failure_diagnostic_remediation_followup_materially_different_generator_"
    "guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_"
    "fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_snapshot_"
    "screen_rerun_failure_attribution_remediation_design_plan_only"
)


def _failure_attribution_payload(
    *,
    passed: bool = True,
    hard_rows: int = 0,
    comfort_rows: int = 0,
    materialized_rows: int = 73,
    dp_head: str = EXPECTED_DP_HEAD,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_materially_different_generator_guarded_"
                "fixed_snapshot_screen_rerun_failure_attribution_remediation_"
                "guarded_fixed_snapshot_screen_rerun_failure_attribution_"
                "remediation_guarded_fixed_snapshot_screen_rerun_failure_"
                "attribution_remediation_guarded_fixed_snapshot_screen_rerun_"
                "failure_attribution_complete"
            ),
            "passed": passed,
            "authorized_next_work": SOURCE_NEXT_WORK,
            "remediation_design_plan_authorized": passed,
        },
        "head_audit": {
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "source_summary": {
            "status": "route_topology_candidate_support_insufficient",
            "snapshots": 57,
            "snapshots_with_generated_candidates": 21,
            "generated_candidate_rows": 73,
            "lower_union_red_rows": 73,
            "hard_feasible_rows": hard_rows,
            "comfort_admissible_rows": comfort_rows,
            "hard_support_rate": 0.0,
            "comfort_support_rate": 0.0,
        },
        "materialization_summary": {
            "materialized_rows": materialized_rows,
            "report_only_rows": materialized_rows,
            "uses_outcome_labels_rows": 0,
            "score_mutation_rows": 0,
            "selector_mutation_rows": 0,
        },
        "read_only_attribution": {
            "primary_blocker_family": (
                "route_topology_hard_constraint_failure_after_v4_materialization"
            ),
            "secondary_blocker_family": "zero_comfort_support_after_hard_constraint_failure",
            "training_ready": False,
            "replay_evidence_ready": False,
            "positive_support_evidence": False,
        },
        "blocked_actions": {
            "candidate_generation_execution_authorized": blocked_action,
            "safety_benefit_claim_authorized": False,
        },
    }


def _audit_text(*, omit: str | None = None) -> str:
    lines = {
        "materialized_generator_rejected": (
            "Reject this guarded material v4 route/topology candidate construction family"
        ),
        "dp_fixed_tail": f"DP remained fixed at `{EXPECTED_DP_HEAD}`",
        "selector_equivalence_exact": (
            "selector_equivalence.exact_field_mismatches=0 for selected_index"
        ),
        "selector_equivalence_numeric": (
            "selector_equivalence.numeric_field_mismatches=0 for scores"
        ),
        "candidate_tensor_available": "The fixed candidate tensor exists before",
        "candidate_tensor_dp_native_boundary": (
            "already generated DP candidate tensor before selection"
        ),
        "fixed_dp_candidate_pool_opportunity": (
            "fixed DP candidate pool contains hard-guarded lower-SafetyCost alternatives"
        ),
    }
    return "\n".join(value for key, value in lines.items() if key != omit)


def test_dp_native_reranking_design_plan_ready() -> None:
    report = build_report(
        failure_attribution=_failure_attribution_payload(),
        audit_text=_audit_text(),
        failure_attribution_json="/tmp/source.json",
        audit_md="/tmp/audit.md",
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_artifact_evidence_audit_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["trajectory_rewrite_authorized"] is False
    assert decision["candidate_tensor_mutation_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["design_plan"]["route"] == "dp_native_candidate_reranking_only"
    assert report["design_plan"]["source_materialized_generator_rejected"] is True
    assert report["design_plan"]["uses_existing_dp_native_evidence_only"] is True


def test_dp_native_reranking_design_plan_rejects_source_positive_support() -> None:
    report = build_report(
        failure_attribution=_failure_attribution_payload(hard_rows=1),
        audit_text=_audit_text(),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "hard_support_zero" in failed
    assert "plan_source_materialized_generator_rejected" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_dp_native_reranking_design_plan_rejects_missing_audit_anchor() -> None:
    report = build_report(
        failure_attribution=_failure_attribution_payload(),
        audit_text=_audit_text(omit="selector_equivalence_exact"),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_anchor_selector_equivalence_exact" in failed
    assert "audit_required_anchors_present" in failed


def test_dp_native_reranking_design_plan_rejects_dp_head_change() -> None:
    report = build_report(
        failure_attribution=_failure_attribution_payload(dp_head="not-fixed"),
        audit_text=_audit_text(),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in failed


def test_dp_native_reranking_design_plan_markdown_boundary() -> None:
    markdown = render_markdown(
        build_report(
            failure_attribution=_failure_attribution_payload(),
            audit_text=_audit_text(),
        )
    )

    assert "DP-Native Candidate Reranking Design Plan" in markdown
    assert "Candidate generation authorized: `False`" in markdown
    assert "Trajectory rewrite authorized: `False`" in markdown
    assert "Candidate tensor mutation authorized: `False`" in markdown
    assert "selected output is an index k from the original DP candidate tensor" in markdown
    assert "generate candidates, rewrite trajectories, run replay" in markdown


def test_dp_native_reranking_design_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "failure_attribution.json"
    audit_md = tmp_path / "audit.md"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(
        json.dumps(_failure_attribution_payload()),
        encoding="utf-8",
    )
    audit_md.write_text(_audit_text(), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "dp-native-reranking-plan",
            "--failure_attribution_json",
            str(source_json),
            "--audit_md",
            str(audit_md),
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
    assert "DP-Native Candidate Reranking Design Plan" in output_md.read_text(
        encoding="utf-8"
    )
