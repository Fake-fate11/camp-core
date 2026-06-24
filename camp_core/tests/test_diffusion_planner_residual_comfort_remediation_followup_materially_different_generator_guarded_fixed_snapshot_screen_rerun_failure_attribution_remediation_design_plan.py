from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_design"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.FAILURE_ATTRIBUTION_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK}
primary_blocker_family={target.PRIMARY_BLOCKER_FAMILY}
positive_support_evidence=False
training_ready=False
replay_evidence_ready=False
This is negative support evidence, not training-ready evidence.
formal seeds 11/12/13 remain frozen
"""


def _attribution_payload(
    *,
    status: str = target.FAILURE_ATTRIBUTION_READY_STATUS,
    authorized_next_work: str = target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    primary: str = target.PRIMARY_BLOCKER_FAMILY,
    blocked_action: bool = False,
    positive_support: bool = False,
    training_ready: bool = False,
    descriptor_coverage: float = 1.0,
    comfort_blockers: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["training_execution_authorized"] = True

    return {
        "final_decision": decision,
        "blocked_actions": {key: False for key in target.BLOCKED_ACTIONS},
        "read_only_attribution": {
            "primary_blocker_family": primary,
            "candidate_row_count": 306,
            "descriptor_row_count": 306,
            "descriptor_coverage_rate": descriptor_coverage,
            "candidate_coverage_rate": 0.47368421052631576,
            "hard_support_gap": 0.06481481481481483,
            "comfort_support_gap": 0.25,
            "positive_support_evidence": positive_support,
            "training_ready": training_ready,
            "replay_evidence_ready": False,
            "hard_blocker_ranking": [
                {"name": "dp_lane_crossing", "count": 260},
                {"name": "dp_kinematic", "count": 238},
                {"name": "dp_road_border", "count": 227},
                {"name": "dp_red_light", "count": 216},
            ],
            "comfort_blocker_ranking": comfort_blockers
            or [
                {
                    "name": "route_topology_comfort_blocked_command_lateral",
                    "count": 12,
                },
                {
                    "name": "route_topology_comfort_blocked_rollout_jerk",
                    "count": 12,
                },
                {
                    "name": "route_topology_comfort_blocked_command_jerk",
                    "count": 9,
                },
                {
                    "name": "route_topology_comfort_blocked_progress_loss",
                    "count": 6,
                },
                {
                    "name": "route_topology_comfort_blocked_rollout_lateral",
                    "count": 5,
                },
                {
                    "name": "route_topology_comfort_blocked_smoothness_loss",
                    "count": 3,
                },
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Failure Attribution\n",
) -> tuple[Path, Path]:
    root = tmp_path / "failure_attribution"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.ATTRIBUTION_JSON).write_text(
        json.dumps(payload or _attribution_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.ATTRIBUTION_MD).write_text(markdown, encoding="utf-8")
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
        failure_attribution_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_material_generator_failure_remediation_design_plan_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["remediation_design_plan"]
    tracks = {item["name"] for item in plan["remediation_tracks"]}
    descriptors = {item["name"] for item in plan["descriptor_atom_contract"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["remediation_design_plan_ready"] is True
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["target_failure"]["residual_family"] == target.RESIDUAL_FAMILY
    assert "lane_red_hard_feasibility_precheck" in tracks
    assert "jerk_limited_stop_and_creep_profiles" in tracks
    assert "lateral_heading_continuity_projection" in tracks
    assert "progress_retention_without_gate_relaxation" in tracks
    assert "positive_support_before_training_gate" in tracks
    assert "hard_feasibility_margin_hinges" in descriptors
    assert "command_jerk_hinge" in descriptors
    assert "rollout_jerk_hinge" in descriptors
    assert "lateral_error_signed_split" in descriptors
    assert "progress_loss_hinge" in descriptors
    assert "train_on_negative_support" in rejected
    assert "comfort_budget_relaxation" in rejected
    assert "formal_seed_probe" in rejected
    assert "dp_side_change" in rejected


def test_material_generator_failure_remediation_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_material_generator_failure_remediation_design_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_this_design_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_failure_remediation_design_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_failure_remediation_design_rejects_wrong_primary(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(primary="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_primary_blocker" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_failure_remediation_design_rejects_positive_support(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(positive_support=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_no_positive_support" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_failure_remediation_design_rejects_training_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(training_ready=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_training_not_ready" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_failure_remediation_design_rejects_descriptor_gap(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(descriptor_coverage=0.5))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_descriptor_coverage_complete" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_generator_failure_remediation_design_rejects_missing_comfort_blocker(
    tmp_path: Path,
) -> None:
    payload = _attribution_payload(
        comfort_blockers=[
            {"name": "route_topology_comfort_blocked_command_lateral", "count": 12},
            {"name": "route_topology_comfort_blocked_rollout_jerk", "count": 12},
        ]
    )
    report = _build(tmp_path, payload=payload)

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "failure_attribution_has_route_topology_comfort_blocked_rollout_lateral"
        in report["final_decision"]["failed_checks"]
    )


def test_material_generator_failure_remediation_design_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_no_blocked_authorizations" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_generator_failure_remediation_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "remediation_design_plan.json"
    output_md = tmp_path / "out" / "remediation_design_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "design",
            "--failure_attribution_root",
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
    assert "Material Generator Failure Remediation Design Plan" in markdown
    assert "lane_red_hard_feasibility_precheck" in markdown
    assert "lateral_error_signed_split" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
