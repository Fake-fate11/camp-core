from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_TESTS,
    STATIC_REVIEW_JSON,
    STATIC_REVIEW_MD,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_static_contract import (
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
    REQUIRED_STATIC_CONTRACTS,
)


def _audit_text() -> str:
    return f"""
status={STATIC_REVIEW_READY_STATUS}

Next admissible gate:

`{STATIC_REVIEW_AUTHORIZED_NEXT_WORK}`.
"""


def _static_review_payload(
    *,
    missing_contract: str | None = None,
    blocked_action: bool = False,
    status: str = STATIC_REVIEW_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
) -> dict[str, object]:
    contracts = [item for item in REQUIRED_STATIC_CONTRACTS if item != missing_contract]
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_plan_authorized": True,
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
            "all_contracts_pass": missing_contract is None,
            "contracts": [
                {
                    "name": name,
                    "status": "pass",
                    "evidence": "contract present",
                }
                for name in contracts
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    audit_text: str | None = None,
    markdown_text: str | None = None,
) -> tuple[Path, Path]:
    root = tmp_path / "static_review"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _static_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / STATIC_REVIEW_MD).write_text(
        markdown_text
        if markdown_text is not None
        else "# Static Review\n\n## Contracts\n\nall pass\n",
        encoding="utf-8",
    )
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    audit_text: str | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, payload=payload, audit_text=audit_text)
    return build_report(
        static_review_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_negative_support_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    component_names = {component["name"] for component in plan["components"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_ready"] is True
    assert decision["next_gate_allowed_files"] == list(ALLOWED_NEXT_FILES)
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["planned_policy"] == PLANNED_POLICY
    assert "coverage_first_fail_closed_partition" in component_names
    assert "hard_feasibility_support_floor_candidates" in component_names
    assert "comfort_after_hard_progress_candidates" in component_names
    assert set(REQUIRED_TESTS).issubset(set(plan["required_tests"]))


def test_negative_support_implementation_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_negative_support_implementation_plan_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    missing = "affine_score_and_convex_master_boundary_preserved"
    report = _build(tmp_path, payload=_static_review_payload(missing_contract=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_all_contracts_pass" in report["final_decision"][
        "failed_checks"
    ]
    assert f"static_review_contract_{missing}" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_implementation_plan_rejects_blocked_action_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_implementation_plan_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_implementation_plan_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Negative-Support Follow-Up Implementation Plan" in markdown
    assert PLANNED_POLICY in markdown
    for path in ALLOWED_NEXT_FILES:
        assert path in markdown
    for test_name in REQUIRED_TESTS:
        assert test_name in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_negative_support_implementation_plan_cli_writes_outputs(
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
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Negative-Support Follow-Up Implementation Plan" in markdown
