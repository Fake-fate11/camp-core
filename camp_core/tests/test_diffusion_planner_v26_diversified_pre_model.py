from __future__ import annotations

import importlib


def _unit(index: int) -> dict[str, object]:
    return {
        "unit_index": index,
        "route": {
            "route_id": f"route-{index}",
            "family_id": f"family-{index % 6}",
            "corridor_id": f"corridor-{index % 155}",
        },
        "terminal": {"status": "qualified"},
    }


def test_full_pre_model_aggregate_requires_exact_design_and_zero_model_contract() -> None:
    qualifier = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_pre_model"
    )
    manifest = {"route_plan_sha256": "a" * 64}
    units = [_unit(index) for index in range(1786)]
    receipt = qualifier._aggregate(manifest=manifest, units=units, terminal_error=None)
    assert receipt["status"] == "passed"
    assert receipt["denominator"] == {
        "planned": 1786,
        "complete": 1786,
        "failed": 0,
        "unattempted": 0,
    }
    assert all(value == 0 for value in receipt["zero_model_totals"].values())

    units[0]["terminal"] = {"status": "failed"}
    assert qualifier._aggregate(manifest=manifest, units=units, terminal_error=None)["status"] == "failed"


def test_qualification_parser_requires_explicit_frozen_plan_and_reference_bindings() -> None:
    qualifier = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_pre_model"
    )
    args = qualifier.parse_args(
        [
            "--output-dir", "out",
            "--qualification-lock", "lock",
            "--route-plan", "plan.json",
            "--expected-route-plan-sha256", "a" * 64,
            "--base-probe-config", "base.json",
            "--reference-weights", "weights",
            "--reference-weights-root", "b" * 64,
            "--reference-weights-review", "review",
            "--reference-weights-review-root", "c" * 64,
            "--fixed-dp-repo", "fixed-dp",
            "--expected-camp-head", "d" * 40,
        ]
    )
    assert args.expected_route_plan_sha256 == "a" * 64
