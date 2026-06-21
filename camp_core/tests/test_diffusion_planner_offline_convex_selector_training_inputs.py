from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_offline_convex_selector_training_inputs import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    analyze,
    main,
    render_markdown,
)


def _training_plan() -> dict:
    return {
        "final_decision": {
            "status": "offline_convex_selector_training_plan_ready",
            "passed": True,
            "authorized_next_work": "offline_convex_selector_training_input_manifest_gate",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
        }
    }


def _manifest(path: Path) -> Path:
    payload = {
        "run_keys": {},
        "routes": {},
        "filters": [
            {
                "name": "normal_filter",
                "match": {"traffic_lights": False, "max_npcs": 0},
                "buckets": ["normal"],
            },
            {
                "name": "traffic_filter",
                "match": {"traffic_lights": True},
                "buckets": ["traffic_light"],
            },
        ],
        "default_buckets": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _record(*, missing_outcome_field: bool = False) -> dict:
    outcome = {
        "feasible": True,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.5,
        "progress_m": 2.0,
    }
    if missing_outcome_field:
        outcome.pop("progress_m")
    return {
        "atoms": [[0.1, 0.2], [0.3, 0.4]],
        "feasible_mask": [True, True],
        "candidate_closed_loop_outcomes": [outcome, dict(outcome)],
    }


def _write_log(
    root: Path,
    *,
    seed: int = 1,
    traffic_lights: bool = False,
    max_npcs: int = 0,
    missing_outcome_field: bool = False,
) -> Path:
    root.mkdir(parents=True)
    log_path = root / "camp_selection_log.json"
    log_path.write_text(
        json.dumps([_record(missing_outcome_field=missing_outcome_field)]),
        encoding="utf-8",
    )
    summary = {
        "benchmark": {
            "route": "/routes/sample_route.pkl",
            "seed": seed,
            "steps": 1,
            "max_npcs": max_npcs,
            "spawn_probability": 0.0,
            "traffic_lights": traffic_lights,
            "advance_mode": "perfect",
        }
    }
    (root / "camp_validation_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return log_path


def test_training_input_manifest_ready(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "run")
    manifest = _manifest(tmp_path / "buckets.json")

    report = analyze(
        [log_path],
        training_plan=_training_plan(),
        scenario_bucket_manifest=manifest,
        required_buckets=("normal",),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert report["summary"]["logs"] == 1
    assert report["summary"]["records"] == 1
    assert report["summary"]["bucket_record_counts"]["normal"] == 1
    assert report["manifest"]["logs"][0]["sha256"]

    markdown = render_markdown(report)
    assert "Offline Convex Selector Training Input Manifest" in markdown
    assert "training execution authorized: `False`" in markdown


def test_training_input_manifest_blocks_formal_seed(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "run", seed=11)
    manifest = _manifest(tmp_path / "buckets.json")

    report = analyze(
        [log_path],
        training_plan=_training_plan(),
        scenario_bucket_manifest=manifest,
        required_buckets=("normal",),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["summary"]["formal_seed_logs"] == 1
    assert any("formal_seed_detected" in error for error in report["summary"]["errors"])


def test_training_input_manifest_blocks_missing_outcome_field(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "run", missing_outcome_field=True)
    manifest = _manifest(tmp_path / "buckets.json")

    report = analyze(
        [log_path],
        training_plan=_training_plan(),
        scenario_bucket_manifest=manifest,
        required_buckets=("normal",),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert any("missing=progress_m" in error for error in report["summary"]["errors"])


def test_training_input_manifest_blocks_missing_bucket(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "run")
    manifest = _manifest(tmp_path / "buckets.json")

    report = analyze(
        [log_path],
        training_plan=_training_plan(),
        scenario_bucket_manifest=manifest,
        required_buckets=("traffic_light",),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["summary"]["missing_required_buckets"] == ["traffic_light"]


def test_training_input_manifest_blocks_bad_plan(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path / "run")
    manifest = _manifest(tmp_path / "buckets.json")
    plan = _training_plan()
    plan["final_decision"]["status"] = "offline_convex_selector_training_plan_blocked"

    report = analyze(
        [log_path],
        training_plan=plan,
        scenario_bucket_manifest=manifest,
        required_buckets=("normal",),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert "training_plan_status_ready" in failed


def test_training_input_manifest_prefers_path_route_alias_for_buckets(
    tmp_path: Path,
) -> None:
    route_root = (
        tmp_path
        / "candidate_outcome_labels_static"
        / "route_alias"
        / "seed_1"
        / "npc_0"
        / "spawn_0p3"
        / "tl_off"
        / "static"
    )
    log_path = _write_log(route_root)
    manifest_payload = {
        "run_keys": {},
        "routes": {"route_alias": ["lane_change_or_merge"]},
        "filters": [],
        "default_buckets": [],
    }
    manifest = tmp_path / "alias_buckets.json"
    manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")

    report = analyze(
        [log_path],
        training_plan=_training_plan(),
        scenario_bucket_manifest=manifest,
        required_buckets=("lane_change_or_merge",),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["manifest"]["logs"][0]["scenario_row"]["route_name"] == "route_alias"
    assert report["summary"]["bucket_record_counts"]["lane_change_or_merge"] == 1


def test_training_input_manifest_cli_writes_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    log_path = _write_log(tmp_path / "run")
    manifest = _manifest(tmp_path / "buckets.json")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_training_plan()), encoding="utf-8")
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "audit",
            "--training_plan_json",
            str(plan_path),
            "--selection_log",
            str(log_path),
            "--scenario_bucket_manifest",
            str(manifest),
            "--required_bucket",
            "normal",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )
    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == READY_STATUS
    assert "Offline Convex Selector Training Input Manifest" in output_md.read_text(
        encoding="utf-8"
    )
