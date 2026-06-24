from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK as ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as ATTRIBUTION_READY_STATUS,
    SCREEN_REJECT_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_design import (
    ATTRIBUTION_JSON,
    ATTRIBUTION_MD,
    AUTHORIZED_NEXT_WORK,
    GATE_NAME,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FAILURE_MODES,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
## 2026-06-23 - failure attribution

status={ATTRIBUTION_READY_STATUS}
training_execution_authorized=False
dp_modification_authorized=False

Next admissible gate:

`{GATE_NAME}`.

This next gate may design a remediation plan only.
"""


def _attribution_payload(
    *,
    modes: tuple[str, ...] = REQUIRED_FAILURE_MODES,
    blocked_action: bool = False,
    authorized_next_work: str = ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    status: str = ATTRIBUTION_READY_STATUS,
    passed: bool = True,
    comfort_rows: int = 0,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "atom_promotion_authorized": False,
        "online_selector_promotion_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "source_summary": {
            "status": SCREEN_REJECT_STATUS,
            "snapshots": 57,
            "generated_candidate_rows": 276,
            "lower_union_red_comfort_admissible_rows": comfort_rows,
        },
        "read_only_attribution": {
            "primary_failure_modes": list(modes),
            "zero_candidate_reasons": {"red_stop_distance_window": 36},
            "comfort_blocker_counts": {
                "route_topology_comfort_blocked_command_jerk": 64
            },
            "recommended_design_focus": [
                "red-stop distance-window coverage",
                "comfort-preserving candidate construction",
                "latency-bounded candidate expansion",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "attribution"
    root.mkdir()
    audit.write_text(
        audit_text if audit_text is not None else _audit_text(),
        encoding="utf-8",
    )
    (root / ATTRIBUTION_JSON).write_text(
        json.dumps(payload or _attribution_payload(), sort_keys=True),
        encoding="utf-8",
    )
    (root / ATTRIBUTION_MD).write_text(
        "# Failure Attribution\n\n## Boundaries\n\n- read-only analysis only\n",
        encoding="utf-8",
    )
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return build_report(
        attribution_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_remediation_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    design = report["remediation_design"]
    axes = {item["name"] for item in design["remediation_axes"]}
    rejected = {item["name"] for item in design["rejected_non_fixes"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert set(design["source_failure_modes"]) == set(REQUIRED_FAILURE_MODES)
    assert "red_stop_distance_window_coverage_partition" in axes
    assert "comfort_first_longitudinal_retiming" in axes
    assert "comfort_blocker_split_diagnostics" in axes
    assert "latency_bounded_candidate_budget" in axes
    assert "comfort_gate_relaxation" in rejected
    assert "dp_side_fix" in rejected


def test_remediation_design_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["static_contract_review_authorized"] is False


def test_remediation_design_rejects_missing_audit_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text=_audit_text().replace(GATE_NAME, "other"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_this_design_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_remediation_design_rejects_missing_failure_mode(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_attribution_payload(modes=REQUIRED_FAILURE_MODES[:-1]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "attribution_failure_mode_latency_budget_exceeded"
        in report["final_decision"]["failed_checks"]
    )


def test_remediation_design_rejects_blocked_action_leak(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_attribution_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "attribution_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_remediation_design_rejects_comfort_support_present(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_attribution_payload(comfort_rows=2))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "attribution_no_comfort_admissible_lower_red_rows" in report[
        "final_decision"
    ]["failed_checks"]


def test_remediation_design_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Remediation Design Plan" in markdown
    assert "Static contract review authorized" in markdown
    assert "red_stop_distance_window_zero_candidate_partition" in markdown
    assert "comfort_first_longitudinal_retiming" in markdown
    assert "implementation edits are not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights, DP code, DP configs, and DP invocation must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "hinge/signed-split" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "classical Benders" in markdown


def test_remediation_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--attribution_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Design Plan"
    )
