from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_design import (
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
    REQUIRED_FAILURE_MODES,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DESIGN_JSON,
    DESIGN_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_REJECTED_NON_FIXES,
    REQUIRED_REMEDIATION_AXES,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
## 2026-06-23 - remediation design plan

status={DESIGN_READY_STATUS}
authorized_next_work={DESIGN_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_modification_authorized=False

Next admissible gate:

`{DESIGN_AUTHORIZED_NEXT_WORK}`.
"""


def _design_payload(
    *,
    enabled_by_default: bool = False,
    axes: tuple[str, ...] = REQUIRED_REMEDIATION_AXES,
    failure_modes: tuple[str, ...] = REQUIRED_FAILURE_MODES,
    requirements: list[str] | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": DESIGN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": DESIGN_AUTHORIZED_NEXT_WORK,
        "static_contract_review_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["implementation_code_edit_authorized"] = True
    return {
        "final_decision": decision,
        "remediation_design": {
            "source_failure_modes": list(failure_modes),
            "remediation_axes": [
                {"name": name, "covers_failure_mode": REQUIRED_FAILURE_MODES[0]}
                for name in axes
            ],
            "rejected_non_fixes": [
                {"name": name, "reason": "rejected"} for name in REQUIRED_REJECTED_NON_FIXES
            ],
            "default_off_contract": {
                "enabled_by_default": enabled_by_default,
                "candidate0_preserved": True,
                "selection_effect_when_disabled": False,
                "future_outcome_leakage_allowed": False,
                "dp_code_or_weight_change_allowed": False,
                "formal_seed_use_allowed": False,
                "training_allowed": False,
            },
            "static_review_requirements": requirements
            if requirements is not None
            else [
                "prove all proposed inputs are finite current-tick candidate, lane, route, and traffic-light features",
                "prove no DP code, weights, configs, or invocation contract are modified",
                "prove any future atom proposal is nonnegative or legally hinge/signed-split while preserving score_k(w)=a_k^T w and convex simplex/CVaR/L2 master structure",
            ],
            "blocked_boundaries": [
                "implementation edits are not authorized",
                "candidate generation execution is not authorized",
                "fixed-snapshot screen rerun is not authorized",
                "replay, Full36, and formal seeds 11/12/13 remain frozen",
                "CAMP retraining and training execution are not authorized",
                "atom promotion and online selector promotion are not authorized",
                "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
                "DP weights, DP code, DP configs, and DP invocation must remain fixed",
            ],
        },
    }


def _markdown_text() -> str:
    return """
# Design

## Remediation Axes

- red-stop partition without using future outcomes

## Static Review Requirements

- finite current-tick features
"""


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "design"
    root.mkdir()
    audit.write_text(
        audit_text if audit_text is not None else _audit_text(),
        encoding="utf-8",
    )
    (root / DESIGN_JSON).write_text(
        json.dumps(payload or _design_payload(), sort_keys=True),
        encoding="utf-8",
    )
    (root / DESIGN_MD).write_text(
        markdown_text if markdown_text is not None else _markdown_text(),
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
        design_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_static_contract_review_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert [item["name"] for item in review["contracts"]] == [
        "source_failure_mode_coverage_contract",
        "default_off_selection_neutral_contract",
        "current_tick_feature_contract",
        "dp_black_box_fixed_contract",
        "rejected_non_fix_contract",
        "math_boundary_contract",
        "execution_block_contract",
    ]


def test_static_contract_review_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_static_contract_review_rejects_missing_audit_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        audit_text=_audit_text().replace(DESIGN_AUTHORIZED_NEXT_WORK, "not_allowed"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_rejects_default_on(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_design_payload(enabled_by_default=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_default_off_selection_neutral_contract_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_missing_axis(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(axes=REQUIRED_REMEDIATION_AXES[:-1]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_source_failure_mode_coverage_contract_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_missing_current_tick_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(requirements=["prove no DP code is modified"]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_current_tick_feature_contract_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_blocked_action_leak(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_design_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_static_contract_review_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Static Contract Review" in markdown
    assert "source_failure_mode_coverage_contract" in markdown
    assert "default_off_selection_neutral_contract" in markdown
    assert "current_tick_feature_contract" in markdown
    assert "implementation edits are not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights, DP code, DP configs, and DP invocation must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "classical Benders" in markdown


def test_static_contract_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
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
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Static Contract Review"
    )
