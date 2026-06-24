from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_design_static_contract"
)
target = importlib.import_module(MODULE)
plan = target._plan

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _source_for_plan() -> dict[str, object]:
    return {
        "primary_blocker_family": plan.PRIMARY_BLOCKER_FAMILY,
        "candidate_row_count": 306,
        "descriptor_row_count": 306,
        "descriptor_coverage_rate": 1.0,
        "candidate_coverage_rate": 0.47368421052631576,
        "hard_support_gap": 0.06481481481481483,
        "comfort_support_gap": 0.25,
        "hard_blockers": [
            "dp_lane_crossing",
            "dp_kinematic",
            "dp_road_border",
            "dp_red_light",
        ],
        "comfort_blockers": [
            "route_topology_comfort_blocked_command_lateral",
            "route_topology_comfort_blocked_rollout_jerk",
            "route_topology_comfort_blocked_command_jerk",
            "route_topology_comfort_blocked_progress_loss",
            "route_topology_comfort_blocked_rollout_lateral",
            "route_topology_comfort_blocked_smoothness_loss",
        ],
    }


def _audit_text() -> str:
    return f"""
status={target.PLAN_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.PLAN_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_head={target.EXPECTED_DP_HEAD}
"""


def _plan_payload(
    *,
    status: str = target.PLAN_READY_STATUS,
    authorized_next_work: str = target.PLAN_AUTHORIZED_NEXT_WORK,
    blocked_action: bool = False,
    missing_track: str | None = None,
    missing_descriptor: str | None = None,
    missing_rejected: str | None = None,
) -> dict[str, object]:
    design = plan._remediation_design_plan(_source_for_plan())
    if missing_track is not None:
        design["remediation_tracks"] = [
            item for item in design["remediation_tracks"] if item["name"] != missing_track
        ]
    if missing_descriptor is not None:
        design["descriptor_atom_contract"] = [
            item
            for item in design["descriptor_atom_contract"]
            if item["name"] != missing_descriptor
        ]
    if missing_rejected is not None:
        design["rejected_non_fixes"] = [
            item
            for item in design["rejected_non_fixes"]
            if item["name"] != missing_rejected
        ]

    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "static_contract_review_authorized": True,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {"final_decision": decision, "remediation_design_plan": design}


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Material Generator Failure Remediation Design Plan\n\n## Math Boundary\n",
) -> tuple[Path, Path]:
    root = tmp_path / "plan"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.PLAN_JSON).write_text(
        json.dumps(payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.PLAN_MD).write_text(markdown, encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    dp_head: str = target.EXPECTED_DP_HEAD,
) -> dict[str, object]:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return target.build_report(
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_material_generator_remediation_design_static_contract_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    contract = report["static_contract"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_complete"] is True
    assert decision["implementation_plan_authorized"] is True
    assert decision["remediation_implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert contract["current_tick_input_contract"] is True
    assert contract["finite_default_off_append_contract"] is True
    assert contract["fixed_dp_black_box_contract"] is True
    assert contract["hard_plus_comfort_target_contract"] is True
    assert contract["descriptor_legality_contract"] is True
    assert contract["affine_convex_master_contract"] is True
    assert contract["positive_support_before_training_contract"] is True


def test_material_generator_remediation_design_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_material_generator_remediation_design_static_contract_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_remediation_design_static_contract_rejects_wrong_plan_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_status_ready" in report["final_decision"]["failed_checks"]


def test_material_generator_remediation_design_static_contract_rejects_wrong_next(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_authorizes_this_review" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_remediation_design_static_contract_rejects_missing_track(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(missing_track="lane_red_hard_feasibility_precheck"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_has_track_lane_red_hard_feasibility_precheck" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_generator_remediation_design_static_contract_rejects_missing_descriptor(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(missing_descriptor="hard_feasibility_margin_hinges"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_has_descriptor_hard_feasibility_margin_hinges" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_generator_remediation_design_static_contract_rejects_missing_rejected_non_fix(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(missing_rejected="comfort_budget_relaxation"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_rejects_comfort_budget_relaxation" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_generator_remediation_design_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_remediation_design_static_contract_cli_writes_outputs(
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
            "--plan_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            target.EXPECTED_DP_HEAD,
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    target.main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["final_decision"]["status"] == target.READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Static Contract Review" in markdown
    assert "Implementation plan authorized" in markdown
    assert "formal seeds 11/12/13 remain unauthorized" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
