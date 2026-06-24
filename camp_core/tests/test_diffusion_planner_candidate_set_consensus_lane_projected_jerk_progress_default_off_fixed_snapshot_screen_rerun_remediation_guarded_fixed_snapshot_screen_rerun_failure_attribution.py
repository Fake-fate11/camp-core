from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    CAMP_HEAD,
    CAMP_ORIGIN_MAIN,
    CANDIDATE_ERR,
    CANDIDATE_LOG,
    DP_HEAD,
    EXPECTED_DP_HEAD,
    PLANNED_POLICY,
    READY_STATUS,
    REJECT_STATUS,
    SCREEN_JSON,
    SCREEN_MD,
    SHA256SUMS,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _screen_payload(
    *,
    status: str = "route_topology_candidate_support_insufficient",
    comfort_rows: int = 0,
    blocked_authorization: bool = False,
    source_conflicts: list[str] | None = None,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "next_step": "inspect failure classes",
        "source_authorization_conflicts": source_conflicts or [],
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
            "future_outcome_leakage": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
        },
        "config": {
            "generator_policy": PLANNED_POLICY,
            "max_remediation_candidates": 12,
        },
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 27,
            "generated_candidate_rows": 324,
            "lower_union_red_rows": 324,
            "lower_union_red_hard_feasible_rows": 37,
            "lower_union_red_progress_feasible_rows": 37,
            "lower_union_red_comfort_admissible_rows": comfort_rows,
        },
        "support_gate": {
            "min_snapshot_support_rate": 0.25,
            "hard_feasible_snapshot_support_pass": False,
            "hard_feasible_snapshot_support_rate": 0.14814814814814814,
            "comfort_admissible_snapshot_support_pass": False,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "failure_class_counts": {
            "route_topology_comfort_blocked_command_lateral": 37,
            "route_topology_comfort_blocked_progress_loss": 37,
            "route_topology_comfort_blocked_rollout_lateral": 36,
            "route_topology_dp_kinematic": 241,
            "route_topology_dp_road_border": 242,
            "route_topology_lane_invalid": 253,
            "route_topology_red_timing_invalid": 275,
        },
        "hard_reason_counts": {
            "dp_kinematic": 241,
            "dp_lane_crossing": 253,
            "dp_red_light": 275,
            "dp_road_border": 242,
        },
        "rows": [
            {
                "candidate_construction_diagnostics": {
                    "construction_status": "ready",
                    "red_stop_distance_partition": "standard_min_stop_distance",
                },
                "candidate_rows": [
                    {
                        "hard_feasible": True,
                        "progress_feasible": True,
                        "comfort_admissible": False,
                        "failure_classes": [
                            "route_topology_comfort_blocked_progress_loss",
                            "route_topology_comfort_blocked_command_lateral",
                        ],
                    }
                ],
            }
        ],
        "final_decision": decision,
    }


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_screen_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    markdown: str = "# Screen\n\n## Verdict\n\nsupport insufficient\n",
    err_text: str = "",
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    (root / SCREEN_JSON).write_text(
        json.dumps(payload or _screen_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / SCREEN_MD).write_text(markdown, encoding="utf-8")
    (root / CANDIDATE_LOG).write_text("JSON: screen\nMarkdown: screen\n", encoding="utf-8")
    (root / CANDIDATE_ERR).write_text(err_text, encoding="utf-8")
    (root / CAMP_HEAD).write_text(CAMP_COMMIT + "\n", encoding="utf-8")
    (root / CAMP_ORIGIN_MAIN).write_text(CAMP_COMMIT + "\n", encoding="utf-8")
    (root / DP_HEAD).write_text(EXPECTED_DP_HEAD + "\n", encoding="utf-8")
    _write_sha256sums(
        root,
        (
            SCREEN_JSON,
            SCREEN_MD,
            CANDIDATE_LOG,
            CANDIDATE_ERR,
            CAMP_HEAD,
            CAMP_ORIGIN_MAIN,
            DP_HEAD,
        ),
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
    err_text: str = "",
) -> dict:
    root = _write_screen_root(tmp_path, payload=payload, err_text=err_text)
    return build_report(
        screen_root=root,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_rerun_failure_attribution_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["positive_support_evidence"] is False
    assert attribution["primary_blocker_family"] == (
        "hard_support_below_threshold_and_comfort_support_zero"
    )
    assert attribution["training_ready"] is False
    assert attribution["hard_support_gap"] > 0
    assert attribution["comfort_support_gap"] > 0


def test_guarded_rerun_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_guarded_rerun_failure_attribution_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(blocked_authorization=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_rerun_failure_attribution_rejects_non_negative_screen(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(status="route_topology_candidate_support_ready"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_status_is_support_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_rerun_failure_attribution_rejects_candidate_stderr(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, err_text="warning\n")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_screen_err_empty" in report["final_decision"]["failed_checks"]


def test_guarded_rerun_failure_attribution_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Failure Attribution" in markdown
    assert "hard_support_below_threshold_and_comfort_support_zero" in markdown
    assert "no new screen rerun" in markdown
    assert "formal seeds" in markdown
    assert "CAMP retraining" in markdown
    assert "DP modification" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_guarded_rerun_failure_attribution_cli_writes_outputs(
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
    assert "Failure Attribution" in markdown
