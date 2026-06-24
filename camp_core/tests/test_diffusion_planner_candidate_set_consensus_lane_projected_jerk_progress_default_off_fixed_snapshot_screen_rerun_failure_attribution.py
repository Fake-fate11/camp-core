from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SCREEN_JSON,
    SCREEN_REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _screen_payload(
    *,
    status: str = SCREEN_REJECT_STATUS,
    comfort_rows: int = 0,
    generated_rows: int = 276,
    authorization_leak: bool = False,
) -> dict[str, object]:
    decision = {
        "status": status,
        "offline_selector_screen_authorized": False,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "source_authorization_conflicts": [],
    }
    if authorization_leak:
        decision["camp_retraining_authorized"] = True
    rows = []
    for idx in range(57):
        if idx < 36:
            rows.append(
                {
                    "generated_count": 0,
                    "candidate_construction_diagnostics": {
                        "failure_reason": "red_stop_distance_window"
                    },
                }
            )
        else:
            rows.append({"generated_count": 6, "candidate_rows": [{}] * 6})
    return {
        "analysis": {
            "selection_effect": False,
            "future_outcome_leakage": False,
            "training": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
        },
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 21,
            "generated_candidate_rows": generated_rows,
            "lower_union_red_rows": generated_rows,
            "lower_union_red_hard_feasible_rows": 67,
            "lower_union_red_progress_feasible_rows": 64,
            "lower_union_red_comfort_admissible_rows": comfort_rows,
        },
        "support_gate": {
            "hard_feasible_snapshot_support_rate": 0.38,
            "hard_feasible_snapshot_support_pass": True,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "comfort_admissible_snapshot_support_pass": False,
        },
        "latency_ms": {
            "candidate_build": {"p95": 35.8},
            "total": {"p95": 100.9},
        },
        "failure_class_counts": {
            "route_topology_dp_kinematic": 197,
            "route_topology_comfort_blocked_command_jerk": 64,
            "route_topology_comfort_blocked_rollout_jerk": 60,
            "route_topology_comfort_blocked_progress_loss": 58,
        },
        "rows": rows,
        "final_decision": decision,
    }


def _write_screen_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    files = {
        SCREEN_JSON: json.dumps(payload or _screen_payload(), sort_keys=True),
        "default_off_fixed_snapshot_screen.md": "# screen\n",
        "CANDIDATE_SCREEN.log": "JSON: screen\n",
        "CANDIDATE_SCREEN.err": "",
        "CAMP_HEAD.txt": "abc\n",
        "CAMP_ORIGIN_MAIN.txt": "abc\n",
        "DP_HEAD.txt": f"{EXPECTED_DP_HEAD}\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    _write_sha256sums(root, tuple(files))
    return root


def _build(tmp_path: Path, **kwargs) -> dict:
    return build_report(
        screen_root=_write_screen_root(tmp_path, **kwargs),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_failure_attribution_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    source = report["source_summary"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert source["snapshots"] == 57
    assert source["generated_candidate_rows"] == 276
    assert source["lower_union_red_comfort_admissible_rows"] == 0
    assert attribution["zero_candidate_reasons"] == {"red_stop_distance_window": 36}
    assert "comfort_admissible_support_absent" in attribution["primary_failure_modes"]
    assert "latency_budget_exceeded" in attribution["primary_failure_modes"]


def test_failure_attribution_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_screen_root(tmp_path)
    (root / SCREEN_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        screen_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_artifact_sha256sums_ok" in report["final_decision"][
        "failed_checks"
    ]


def test_failure_attribution_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        screen_root=_write_screen_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_failure_attribution_rejects_non_rejected_screen(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(status="route_topology_candidate_design_ready"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_status_is_support_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_failure_attribution_rejects_missing_comfort_failure(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_screen_payload(comfort_rows=4))

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_no_comfort_admissible_rows" in failed
    assert "attribution_primary_modes_present" not in failed


def test_failure_attribution_rejects_authorization_leak(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_screen_payload(authorization_leak=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_failure_attribution_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "# Default-Off Fixed-Snapshot Screen Rerun Failure Attribution" in markdown
    assert "read-only analysis only" in markdown
    assert "CAMP retraining" in markdown
    assert "red_stop_distance_window_zero_candidate_partition" in markdown


def test_failure_attribution_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    screen_root = _write_screen_root(tmp_path)
    output_json = tmp_path / "out" / "analysis.json"
    output_md = tmp_path / "out" / "analysis.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analysis",
            "--screen_root",
            str(screen_root),
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
        "# Default-Off Fixed-Snapshot Screen Rerun Failure Attribution"
    )
