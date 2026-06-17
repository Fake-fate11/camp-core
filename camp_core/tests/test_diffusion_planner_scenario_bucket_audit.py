from __future__ import annotations

import json

import pytest

from scripts.integrations.audit_diffusion_planner_scenario_buckets import (
    audit_comparison,
    main,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (
    _apply_safety_cost_v1,
)


def _row(
    *,
    variant: str,
    run_key: str,
    route_name: str,
    buckets: list[str],
    jerk: float,
    lateral: float,
    completion: float = 1.0,
    contract: bool = True,
) -> dict[str, object]:
    row: dict[str, object] = {
        "variant": variant,
        "run_key": run_key,
        "route_name": route_name,
        "seed": 1,
        "scenario_buckets": buckets,
        "route_completion_rate": completion,
        "obb_collision_rate": 0.0,
        "near_miss_rate": 0.0,
        "lane_violation_rate": 0.0,
        "red_light_violation_rate": 0.0,
        "planned_red_light_violation_rate": 0.0,
        "mean_jerk_magnitude_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "p95_selection_latency_ms": 80.0,
        "finite_candidate_contract_verified": contract,
    }
    _apply_safety_cost_v1(row)
    return row


def _comparison() -> dict[str, object]:
    rows = []
    for run_key, route_name, buckets in (
        ("normal-1", "sample_normal", ["overall", "normal"]),
        ("red-turn-1", "sample_red_turn", ["overall", "traffic_light", "red_light_turn"]),
    ):
        rows.append(
            _row(
                variant="top1",
                run_key=run_key,
                route_name=route_name,
                buckets=buckets,
                jerk=20.0,
                lateral=2.0,
                contract=False,
            )
        )
        rows.append(
            _row(
                variant="camp",
                run_key=run_key,
                route_name=route_name,
                buckets=buckets,
                jerk=10.0,
                lateral=1.0,
            )
        )
    return {"baseline": "top1", "runs": rows}


def test_bucket_audit_reports_explicit_coverage_gaps() -> None:
    report = audit_comparison(_comparison())

    by_bucket = {bucket["bucket"]: bucket for bucket in report["buckets"]}

    assert by_bucket["overall"]["n_run_keys"] == 2
    assert by_bucket["normal"]["n_run_keys"] == 1
    assert by_bucket["red_light_turn"]["strictly_paired"]
    assert report["coverage_gaps"]["missing_required_buckets"] == [
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    assert report["next_step"] == "add_or_verify_scenario_manifest_labels"


def test_bucket_audit_recomputes_bucket_safety_gate() -> None:
    report = audit_comparison(_comparison())
    by_bucket = {bucket["bucket"]: bucket for bucket in report["buckets"]}
    gate = by_bucket["red_light_turn"]["safety_gate_assessments"][0]

    assert gate["hard_gate_passed"]
    assert gate["safety_cost_claim_passed"]
    assert gate["checks"]["safety_cost_significantly_lower"]["delta"][
        "ci95_high"
    ] < 0.0


def test_bucket_audit_cli_fails_on_missing_required_bucket(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comparison_path = tmp_path / "comparison.json"
    output_json = tmp_path / "bucket_audit.json"
    output_md = tmp_path / "bucket_audit.md"
    comparison_path.write_text(json.dumps(_comparison()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_diffusion_planner_scenario_buckets.py",
            "--comparison_json",
            str(comparison_path),
            "--output_json",
            str(output_json),
            "--output_markdown",
            str(output_md),
            "--fail_on_missing_required",
        ],
    )

    with pytest.raises(SystemExit, match="Missing required scenario bucket"):
        main()
    assert output_json.is_file()
    assert output_md.is_file()
