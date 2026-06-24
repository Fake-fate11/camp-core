from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.analyze_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _candidate_row(*, descriptor: bool = True) -> dict[str, object]:
    meta: dict[str, object] = {}
    if descriptor:
        meta["remediation_descriptor_payload"] = {
            "descriptor_family": target.PLANNED_POLICY,
            "current_tick_features_only": True,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "nonnegative_descriptor_channels": True,
            "hinge_signed_split_channels": True,
            "affine_score_compatible": True,
            "score_contract": "score_k(w)=a_k^T w",
            "convex_master_contract": "simplex/CVaR/L2 unchanged",
        }
    return {"candidate_meta": meta}


def _screen_payload(
    *,
    status: str = target.SCREEN_REJECT_STATUS,
    policy: str = target.PLANNED_POLICY,
    profile: str = target.REMEDIATION_PROFILE,
    comfort_rows: int = 0,
    blocked_authorization: bool = False,
    descriptor_coverage: bool = True,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "next_step": "attribute material generator fixed-snapshot failure",
        "source_authorization_conflicts": [],
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_authorization:
        decision["training_execution_authorized"] = True

    second_candidate = _candidate_row(descriptor=descriptor_coverage)
    return {
        "analysis": {
            "future_outcome_leakage": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
        },
        "config": {
            "generator_policy": policy,
            "default_off_remediation_profile": profile,
        },
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 27,
            "generated_candidate_rows": 306,
            "lower_union_red_rows": 306,
            "lower_union_red_hard_feasible_rows": 18,
            "lower_union_red_progress_feasible_rows": 18,
            "lower_union_red_comfort_admissible_rows": comfort_rows,
        },
        "support_gate": {
            "snapshots": 57,
            "min_snapshot_support_rate": 0.25,
            "hard_feasible_snapshot_support_rate": 0.18518518518518517,
            "hard_feasible_snapshot_support_pass": False,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "comfort_admissible_snapshot_support_pass": False,
        },
        "failure_class_counts": {
            "route_topology_comfort_blocked_command_jerk": 9,
            "route_topology_comfort_blocked_command_lateral": 12,
            "route_topology_comfort_blocked_progress_loss": 6,
            "route_topology_comfort_blocked_rollout_jerk": 12,
            "route_topology_comfort_blocked_rollout_lateral": 5,
            "route_topology_comfort_blocked_smoothness_loss": 3,
            "route_topology_dp_kinematic": 238,
            "route_topology_dp_road_border": 227,
            "route_topology_lane_invalid": 260,
            "route_topology_red_timing_invalid": 216,
        },
        "hard_reason_counts": {
            "dp_kinematic": 238,
            "dp_lane_crossing": 260,
            "dp_red_light": 216,
            "dp_road_border": 227,
        },
        "rows": [
            {"candidate_rows": [_candidate_row(), second_candidate]},
        ],
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
    (root / target.CANDIDATE_LOG).write_text("screen completed\n", encoding="utf-8")
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
) -> dict[str, object]:
    return target.build_report(
        screen_root=_write_screen_root(tmp_path, payload=payload),
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head or target.EXPECTED_DP_HEAD,
        label="unit",
    )


def test_material_generator_fixed_snapshot_failure_attribution_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_failure_attribution_complete"] is True
    assert decision["remediation_design_plan_authorized"] is True
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert attribution["primary_blocker_family"] == (
        "hard_support_below_threshold_plus_zero_comfort_support"
    )
    assert attribution["descriptor_coverage_rate"] == 1.0
    assert attribution["training_ready"] is False
    assert attribution["positive_support_evidence"] is False
    assert attribution["replay_evidence_ready"] is False


def test_material_generator_fixed_snapshot_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(blocked_authorization=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_positive_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(status="support_ready"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_status_is_support_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_wrong_policy(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(policy="lane_centerline_red_stop"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_policy_is_material_support" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_wrong_profile(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(profile="off"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_profile_is_material_support" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_comfort_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(comfort_rows=1))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_comfort_support_zero" in report["final_decision"]["failed_checks"]


def test_material_generator_fixed_snapshot_failure_attribution_rejects_descriptor_gap(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_screen_payload(descriptor_coverage=False))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "attribution_descriptor_coverage_complete" in report["final_decision"][
        "failed_checks"
    ]


def test_material_generator_fixed_snapshot_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_screen_root(tmp_path)
    output_json = tmp_path / "out" / "failure_attribution.json"
    output_md = tmp_path / "out" / "failure_attribution.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "attribute",
            "--screen_root",
            str(root),
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

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == target.READY_STATUS
    assert target.AUTHORIZED_NEXT_WORK in markdown
    assert "read-only attribution only" in markdown
