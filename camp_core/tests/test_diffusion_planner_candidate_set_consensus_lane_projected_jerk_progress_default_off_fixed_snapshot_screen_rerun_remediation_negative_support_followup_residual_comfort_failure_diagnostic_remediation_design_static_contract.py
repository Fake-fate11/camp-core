from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design import (
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    PRIMARY_BLOCKER_FAMILY,
    READY_STATUS as DESIGN_READY_STATUS,
    RESIDUAL_FAILURE_FAMILY,
    TOP_COMFORT_BLOCKER,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DESIGN_JSON,
    DESIGN_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_REJECTED_NON_FIXES,
    REQUIRED_TRACKS,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={DESIGN_READY_STATUS}
authorized_next_work={DESIGN_AUTHORIZED_NEXT_WORK}
top_comfort_blocker={TOP_COMFORT_BLOCKER}
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _design_payload(
    *,
    status: str = DESIGN_READY_STATUS,
    authorized_next_work: str = DESIGN_AUTHORIZED_NEXT_WORK,
    missing_track: str | None = None,
    missing_rejected: str | None = None,
    blocked_action: bool = False,
    wrong_top_blocker: bool = False,
    missing_requirement: str | None = None,
) -> dict[str, object]:
    tracks = [name for name in REQUIRED_TRACKS if name != missing_track]
    rejected = [name for name in REQUIRED_REJECTED_NON_FIXES if name != missing_rejected]
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "static_contract_review_authorized": True,
        "remediation_design_static_contract_review_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    requirements = [
        "prove all features are finite, current-tick, and candidate-local",
        "prove diagnostic payloads cannot alter candidates, scores, selected index, fallback, online selector, or deployed atom schema",
        "prove any future command-jerk descriptor is nonnegative or legal hinge/signed-split",
        "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
        "prove candidate generation, fixed-snapshot screen rerun, replay, Full36, and formal seeds remain unauthorized",
        "prove CAMP retraining and training execution remain unauthorized until positive support and training contracts exist",
        "prove DP code, weights, configs, and invocation remain fixed at the pinned commit",
        "prove no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is introduced",
    ]
    if missing_requirement:
        requirements = [
            item for item in requirements if missing_requirement not in item
        ]
    return {
        "analysis": {
            "math_boundary": (
                "preserve score_k(w)=a_k^T w and simplex/CVaR/L2 while "
                "keeping DP fixed"
            )
        },
        "final_decision": decision,
        "remediation_design_plan": {
            "target_failure": {
                "primary_blocker_family": PRIMARY_BLOCKER_FAMILY,
                "residual_failure_family": RESIDUAL_FAILURE_FAMILY,
                "top_comfort_blocker": "wrong" if wrong_top_blocker else TOP_COMFORT_BLOCKER,
                "hard_progress_survivor_rows": 58,
                "comfort_admissible_rows": 0,
            },
            "design_position": (
                "uses current-tick finite candidate features without "
                "mutating candidates"
            ),
            "remediation_tracks": [
                {
                    "name": name,
                    "purpose": "current-tick finite candidate features",
                    "evidence_driver": TOP_COMFORT_BLOCKER,
                    "contract": (
                        "no mutation of candidates, scores, selected index, "
                        "fallback, online selector, or deployed atom schema"
                    ),
                }
                for name in tracks
            ],
            "static_review_requirements": requirements,
            "rejected_non_fixes": [
                {"name": name, "reason": "not allowed"} for name in rejected
            ],
            "blocked_boundaries": [
                "implementation edits are not authorized in this gate",
                "candidate generation execution is not authorized",
                "fixed-snapshot candidate generation and screen rerun are not authorized",
                "formal seeds 11/12/13 remain frozen and unused",
                "Full36 is not authorized",
                "atom promotion, CAMP retraining, and online selector changes are not authorized",
                "DP weights, DP code, DP config, and DP invocation must remain fixed",
                "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
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
        else (
            "# Residual Comfort Failure Remediation Design Plan\n\n"
            "## Forbidden Work\n\nnone\n\n## Math Boundary\n\nfixed\n"
        ),
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
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_design_static_contract_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["remediation_design_static_contract_review_complete"] is True
    assert decision["remediation_implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["all_contracts_pass"] is True


def test_residual_comfort_remediation_design_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_design_static_contract_rejects_missing_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_static_contract_rejects_missing_track(
    tmp_path: Path,
) -> None:
    missing = "command_jerk_hinge_descriptor_family"
    report = _build(tmp_path, payload=_design_payload(missing_track=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"design_track_{missing}" in report["final_decision"]["failed_checks"]
    assert "static_contract_required_tracks_present" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_static_contract_rejects_missing_nonfix(
    tmp_path: Path,
) -> None:
    missing = "online_selector_workaround"
    report = _build(tmp_path, payload=_design_payload(missing_rejected=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"design_rejected_non_fix_{missing}" in report["final_decision"][
        "failed_checks"
    ]
    assert "static_contract_rejected_non_fixes_present" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_static_contract_rejects_wrong_blocker(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(wrong_top_blocker=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_top_comfort_blocker" in report["final_decision"]["failed_checks"]
    assert "static_contract_failure_target_preserved" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_design_static_contract_rejects_missing_math(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(missing_requirement="score_k(w)=a_k^T w"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_contract_atom_math_contract" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_static_contract_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Static Contract Review" in markdown
    assert "implementation planning only may follow" in markdown
    assert "implementation code edits" in markdown
    assert "formal seeds" in markdown
    assert "CAMP retraining" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "DP modification" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_remediation_design_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_contract_review.json"
    output_md = tmp_path / "out" / "static_contract_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--design_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["analysis"]["label"] == "cli"
    assert report["final_decision"]["status"] == READY_STATUS
    assert markdown.startswith(
        "# Residual Comfort Remediation Design Static Contract Review"
    )
