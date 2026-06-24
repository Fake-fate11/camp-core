from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_implementation_plan import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_STATIC_CONTRACTS,
    STATIC_REVIEW_JSON,
    STATIC_REVIEW_MD,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_static_contract import (
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


def _audit_text() -> str:
    return f"""
## 2026-06-23 - static contract review

status={STATIC_REVIEW_READY_STATUS}
authorized_next_work={STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_modification_authorized=False

Next admissible gate:

`{STATIC_REVIEW_AUTHORIZED_NEXT_WORK}`.
"""


def _static_review_payload(
    *,
    contract_names: tuple[str, ...] = REQUIRED_STATIC_CONTRACTS,
    blocked_action: bool = False,
    status: str = STATIC_REVIEW_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_plan_authorized": True,
        "implementation_code_edit_authorized": False,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    return {
        "final_decision": decision,
        "static_contract_review": {
            "all_contracts_pass": True,
            "contracts": [
                {"name": name, "status": "pass", "evidence": "ok"}
                for name in contract_names
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "static_review"
    root.mkdir()
    audit.write_text(
        audit_text if audit_text is not None else _audit_text(),
        encoding="utf-8",
    )
    (root / STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _static_review_payload(), sort_keys=True),
        encoding="utf-8",
    )
    (root / STATIC_REVIEW_MD).write_text(
        (
            markdown_text
            if markdown_text is not None
            else "# Static Review\n\n## Next Gate\n\nimplementation plan only\n"
        ),
        encoding="utf-8",
    )
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        payload=payload,
        markdown_text=markdown_text,
    )
    return build_report(
        static_review_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    component_names = {item["name"] for item in plan["components"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_ready"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["next_gate_allowed_files"] == list(ALLOWED_NEXT_FILES)
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["allowed_next_files"] == list(ALLOWED_NEXT_FILES)
    assert plan["planned_policy"] == PLANNED_POLICY
    assert "red_stop_distance_window_coverage_partition" in component_names
    assert "comfort_first_lane_projected_retiming" in component_names
    assert "comfort_blocker_split_diagnostics" in component_names
    assert "latency_bounded_candidate_budget" in component_names
    assert "contract_unit_tests" in component_names


def test_implementation_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["next_gate_allowed_files"] == []


def test_implementation_plan_rejects_missing_audit_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        audit_text=_audit_text().replace(
            STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
            "not_allowed",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_implementation_plan_rejects_failed_static_review(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(status="bad", passed=False),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_status_complete" in failed
    assert "static_review_passed" in failed


def test_implementation_plan_rejects_missing_contract(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(contract_names=REQUIRED_STATIC_CONTRACTS[:-1]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_contract_execution_block_contract" in report[
        "final_decision"
    ]["failed_checks"]


def test_implementation_plan_rejects_blocked_action_leak(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_implementation_plan_rejects_missing_next_gate_markdown(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, markdown_text="# Static Review\n")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_markdown_records_next_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_implementation_plan_markdown_records_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Implementation Plan" in markdown
    for path in ALLOWED_NEXT_FILES:
        assert path in markdown
    assert PLANNED_POLICY in markdown
    assert "implementation edits are not authorized now" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights, DP code, DP configs, and DP invocation must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "hinge/signed-split" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "classical Benders" in markdown


def test_implementation_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--static_review_root",
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
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Implementation Plan"
    )
