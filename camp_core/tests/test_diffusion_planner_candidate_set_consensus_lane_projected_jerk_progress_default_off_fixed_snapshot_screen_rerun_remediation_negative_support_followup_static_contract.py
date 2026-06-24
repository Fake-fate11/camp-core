from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_design import (
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DESIGN_JSON,
    DESIGN_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_COMPONENTS,
    REQUIRED_STATIC_CONTRACTS,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
Next admissible gate:

`{DESIGN_AUTHORIZED_NEXT_WORK}`.

Required static contracts:
"""


def _design_payload(
    *,
    missing_contract: str | None = None,
    blocked_action: bool = False,
    status: str = DESIGN_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = DESIGN_AUTHORIZED_NEXT_WORK,
) -> dict[str, object]:
    contracts = [item for item in REQUIRED_STATIC_CONTRACTS if item != missing_contract]
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "static_contract_review_authorized": True,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    return {
        "analysis": {
            "math_boundary": (
                "preserve score_k(w)=a_k^T w and simplex/CVaR/L2 while "
                "keeping DP fixed"
            )
        },
        "design_plan": {
            "components": [
                {
                    "name": name,
                    "purpose": "current-tick design",
                    "evidence_driver": (
                        "fail_closed dp_red_light dp_lane_crossing "
                        "hard-progress-feasible current-tick"
                    ),
                    "contract": (
                        "current-tick fail_closed dp_red_light dp_lane_crossing "
                        "hard-progress-feasible"
                    ),
                }
                for name in REQUIRED_COMPONENTS
            ],
            "required_static_contracts": contracts,
            "forbidden_actions": [
                "production implementation edits are not authorized",
                "candidate generation is not authorized",
                "CAMP retraining is not authorized",
                "safety-benefit claims are not authorized",
                "DP weights remain fixed",
            ],
        },
        "final_decision": decision,
    }


def _write_inputs(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    audit_text: str | None = None,
    markdown_text: str | None = None,
) -> tuple[Path, Path]:
    root = tmp_path / "design"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / DESIGN_JSON).write_text(
        json.dumps(payload or _design_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / DESIGN_MD).write_text(
        markdown_text
        if markdown_text is not None
        else "# Design\n\n## Next Gate\n\nstatic review\n\n## Boundaries\n\nnone\n",
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
        design_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_negative_support_static_contract_review_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized"] is True
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["all_contracts_pass"] is True


def test_negative_support_static_contract_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_negative_support_static_contract_review_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    missing = "affine_score_and_convex_master_boundary_preserved"
    report = _build(tmp_path, payload=_design_payload(missing_contract=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"design_contract_{missing}" in report["final_decision"]["failed_checks"]
    assert f"static_contract_{missing}" in report["final_decision"]["failed_checks"]


def test_negative_support_static_contract_review_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_no_blocked_actions" in report["final_decision"]["failed_checks"]
    assert "boundary_no_execution" in report["final_decision"]["failed_checks"]


def test_negative_support_static_contract_review_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_static_contract_review_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Static Contract Review" in markdown
    for contract in REQUIRED_STATIC_CONTRACTS:
        assert contract in markdown
    assert "implementation planning only may follow" in markdown
    assert "no production implementation edit is authorized" in markdown
    assert "formal seeds" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_negative_support_static_contract_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_review.json"
    output_md = tmp_path / "out" / "static_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--design_root",
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
    assert "Static Contract Review" in markdown
