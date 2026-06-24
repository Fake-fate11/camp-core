from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_static_contract"
)
target = importlib.import_module(MODULE)
plan = target._plan

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.PLAN_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.PLAN_AUTHORIZED_NEXT_WORK}
target_residual_family={target.RESIDUAL_FAMILY}
static_contract_review_authorized=True
training_execution_authorized=False
dp_modification_authorized=False
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
    report = plan.build_report(
        failure_attribution_root=Path("missing"),
        audit_path=Path("missing"),
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=target.EXPECTED_DP_HEAD,
        label="fixture",
    )
    decision = report["final_decision"]
    decision["status"] = status
    decision["passed"] = True
    decision["failed_checks"] = []
    decision["authorized_next_work"] = authorized_next_work
    decision["static_contract_review_authorized"] = True
    if blocked_action:
        decision["training_execution_authorized"] = True
    design = report["materially_different_generator_design_plan"]
    design["target_failure"]["residual_family"] = target.RESIDUAL_FAMILY
    design["target_failure"]["primary_blocker_family"] = plan.PRIMARY_BLOCKER_FAMILY
    if missing_track is not None:
        design["generator_tracks"] = [
            item for item in design["generator_tracks"] if item["name"] != missing_track
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
    return report


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Follow-Up Materially Different Generator Design Plan\n",
) -> tuple[Path, Path]:
    root = tmp_path / "plan"
    root.mkdir()
    audit = tmp_path / "audit.md"
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
) -> dict:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return target.build_report(
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_static_contract_review_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    contract = report["static_contract"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized"] is True
    assert decision["materially_different_generator_implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert contract["current_tick_input_contract"] is True
    assert contract["finite_default_off_append_contract"] is True
    assert contract["material_difference_contract"] is True
    assert contract["descriptor_legality_contract"] is True
    assert contract["affine_convex_master_contract"] is True
    assert contract["positive_support_before_training_contract"] is True


def test_static_contract_review_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_static_contract_review_rejects_missing_audit(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_rejects_wrong_plan_status(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_plan_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_status_ready" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_wrong_next_work(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_plan_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_authorizes_this_review" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_rejects_missing_track(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(
            missing_track="lateral_heading_continuity_projection"
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_has_track_lateral_heading_continuity_projection" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_missing_descriptor(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(missing_descriptor="lateral_error_signed_split"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_has_descriptor_lateral_error_signed_split" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_review_rejects_missing_rejected_non_fix(
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


def test_static_contract_review_rejects_blocked_action(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "design_plan_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_cli_writes_outputs(
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
            "unit",
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
    assert "implementation plan authorized" in markdown.lower()
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
