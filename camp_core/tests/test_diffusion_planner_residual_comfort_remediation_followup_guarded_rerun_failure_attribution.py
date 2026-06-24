from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.analyze_diffusion_planner_residual_comfort_remediation_"
    "followup_guarded_rerun_failure_attribution"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _screen_payload(
    *,
    status: str = "route_topology_candidate_support_insufficient",
    comfort_rows: int = 0,
    blocked_authorization: bool = False,
    profile: str = target.REMEDIATION_PROFILE,
    effective_profile: str = target.REMEDIATION_PROFILE,
    command_jerk_budget: float = 0.05,
    rollout_lateral_budget: float = 1.0,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "next_step": "inspect failure classes",
        "source_authorization_conflicts": [],
        "offline_selector_screen_authorized": False,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "camp_retraining_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_authorization:
        decision["camp_retraining_authorized"] = True
    return {
        "analysis": {
            "candidate_generation_executed": True,
            "future_outcome_leakage": False,
            "closed_loop_replay": False,
            "selection_effect": False,
            "training": False,
            "uses_outcome_labels": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
        },
        "config": {
            "generator_policy": target.PLANNED_POLICY,
            "default_off_remediation_profile": profile,
            "max_remediation_candidates": 12,
        },
        "effective_comfort_budgets": {
            "default_off_remediation_profile": effective_profile,
            "command_jerk_worse_budget_mps3": command_jerk_budget,
            "rollout_lateral_worse_budget_mps2": rollout_lateral_budget,
        },
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 27,
            "generated_candidate_rows": 270,
            "lower_union_red_rows": 270,
            "lower_union_red_hard_feasible_rows": 58,
            "lower_union_red_progress_feasible_rows": 58,
            "lower_union_red_comfort_admissible_rows": comfort_rows,
        },
        "support_gate": {
            "min_snapshot_support_rate": 0.25,
            "hard_feasible_snapshot_support_pass": True,
            "hard_feasible_snapshot_support_rate": 0.2962962962962963,
            "comfort_admissible_snapshot_support_pass": False,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "failure_class_counts": {
            "route_topology_comfort_blocked_command_jerk": 54,
            "route_topology_comfort_blocked_command_lateral": 49,
            "route_topology_comfort_blocked_progress_loss": 37,
            "route_topology_comfort_blocked_rollout_distance": 12,
            "route_topology_comfort_blocked_rollout_jerk": 54,
            "route_topology_comfort_blocked_rollout_lateral": 34,
            "route_topology_comfort_blocked_smoothness_loss": 4,
            "route_topology_dp_kinematic": 200,
            "route_topology_dp_road_border": 120,
            "route_topology_lane_invalid": 121,
            "route_topology_red_timing_invalid": 69,
        },
        "hard_reason_counts": {
            "dp_kinematic": 200,
            "dp_lane_crossing": 121,
            "dp_red_light": 69,
            "dp_road_border": 120,
        },
        "final_decision": decision,
    }


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / target.SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_screen_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    markdown: str = "# Screen\n\n## Verdict\n\nsupport insufficient\n",
    err_text: str = "",
    exit_code: str = "0\n",
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    (root / target.SCREEN_JSON).write_text(
        json.dumps(payload or _screen_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.SCREEN_MD).write_text(markdown, encoding="utf-8")
    (root / target.CANDIDATE_LOG).write_text("JSON: screen\n", encoding="utf-8")
    (root / target.CANDIDATE_ERR).write_text(err_text, encoding="utf-8")
    (root / target.EXIT_CODE).write_text(exit_code, encoding="utf-8")
    (root / target.HEADS).write_text(
        "\n".join(
            [
                f"CAMP_HEAD={CAMP_COMMIT}",
                f"CAMP_ORIGIN_MAIN={CAMP_COMMIT}",
                f"DP_HEAD={target.EXPECTED_DP_HEAD}",
                "SNAPSHOT_COUNT=57",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (
            target.SCREEN_JSON,
            target.SCREEN_MD,
            target.CANDIDATE_LOG,
            target.CANDIDATE_ERR,
            target.EXIT_CODE,
            target.HEADS,
        ),
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    dp_head: str | None = None,
    err_text: str = "",
) -> dict:
    root = _write_screen_root(tmp_path, payload=payload, err_text=err_text)
    return target.build_report(
        screen_root=root,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head or target.EXPECTED_DP_HEAD,
        label="unit",
    )


def test_followup_guarded_rerun_failure_attribution_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_failure_attribution_complete"] is True
    assert decision["materially_different_generator_design_plan_authorized"] is True
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert attribution["primary_blocker_family"] == (
        "comfort_support_zero_after_hard_support_pass"
    )
    assert attribution["training_ready"] is False
    assert attribution["comfort_support_gap"] > 0


def test_followup_guarded_rerun_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_guarded_rerun_failure_attribution_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(blocked_authorization=True),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_guarded_rerun_failure_attribution_rejects_non_negative_screen(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(status="route_topology_candidate_support_ready"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_status_is_support_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_guarded_rerun_failure_attribution_rejects_missing_profile(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(profile="off"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_followup_support_profile" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_guarded_rerun_failure_attribution_rejects_budget_drift(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(command_jerk_budget=0.0))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_command_jerk_budget_relaxed" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_guarded_rerun_failure_attribution_rejects_comfort_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(comfort_rows=1))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_zero_comfort_support_after_followup" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_guarded_rerun_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_screen_root(tmp_path)
    output_json = tmp_path / "out" / "failure_attribution.json"
    output_md = tmp_path / "out" / "failure_attribution.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "attribution",
            "--screen_root",
            str(root),
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
    assert "Failure Attribution" in markdown
