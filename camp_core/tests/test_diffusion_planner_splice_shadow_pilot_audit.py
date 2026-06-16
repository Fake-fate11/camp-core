from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_splice_shadow_pilot import (
    analyze,
    render_markdown,
)


def _record(
    *,
    step: int,
    reason: str | None,
    changed: bool = False,
    lower_union_red_count: int = 0,
    lower_union_red_hard_feasible_count: int = 0,
    admissible_count: int = 0,
    chosen_union_red: float | None = None,
    transform_count: int = 1,
    hard_feasible_count: int = 1,
) -> dict:
    record = {
        "num_candidates": 2,
        "selected_index": 1,
        "selection_step": step,
        "feasible_mask": [True, True],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 10.0],
        "candidate_full_horizon_planned_red_light_cost": [0.0, 10.0],
        "dp_candidate_rewards": [
            {"red_light": 0.0, "progress": 9.0, "smoothness": 0.3},
            {"red_light": -10.0, "progress": 10.0, "smoothness": 1.0},
        ],
        "latency_ms_splice_shadow_rule": 5.0 + step,
        "latency_ms_selection": 80.0 + step,
        "latency_ms_including_candidate_generation": 90.0 + step,
    }
    if reason is None:
        return record
    record["splice_shadow_rule"] = {
        "schema_version": "splice_shadow_rule_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "online_selector_change": False,
        "reason": reason,
        "changed": changed,
        "baseline_selected_index": 1,
        "donor_count": 1,
        "donor_indices": [0],
        "transform_count": transform_count,
        "hard_feasible_count": hard_feasible_count,
        "lower_union_red_count": lower_union_red_count,
        "lower_union_red_hard_feasible_count": lower_union_red_hard_feasible_count,
        "admissible_count": admissible_count,
        "chosen_donor_index": 0 if changed else None,
        "chosen_union_red": chosen_union_red,
        "chosen_progress_loss_m": 0.5 if changed else None,
        "chosen_smoothness_loss": 0.25 if changed else None,
        "budget": {"progress_loss_m": 1.0, "smoothness_loss": 0.5},
        "latency_ms": 5.0 + step,
        "full_red_latency_ms": 0.5,
    }
    return record


def _write_log(tmp_path: Path, records: list[dict]) -> Path:
    log_path = (
        tmp_path
        / "pilot"
        / "sample59_86"
        / "seed_2"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
        / "camp_selection_log.json"
    )
    log_path.parent.mkdir(parents=True)
    log_path.write_text(json.dumps(records), encoding="utf-8")
    return log_path


def test_analyze_splice_shadow_pilot_splits_changed_and_no_budget(tmp_path: Path) -> None:
    _write_log(
        tmp_path,
        [
            _record(
                step=10,
                reason="budget_admissible_lower_red_candidate",
                changed=True,
                lower_union_red_count=1,
                lower_union_red_hard_feasible_count=1,
                admissible_count=1,
                chosen_union_red=0.0,
            ),
            _record(
                step=11,
                reason="no_budget_admissible_lower_red_candidate",
                lower_union_red_count=0,
                hard_feasible_count=1,
            ),
            _record(
                step=12,
                reason="no_budget_admissible_lower_red_candidate",
                lower_union_red_count=1,
                lower_union_red_hard_feasible_count=1,
                admissible_count=0,
            ),
            _record(step=13, reason="no_transformed_candidates", transform_count=0),
            _record(step=14, reason=None),
        ],
    )

    report = analyze([tmp_path / "pilot"], label="unit")

    assert report["records"]["total"] == 5
    assert report["records"]["missing_splice_shadow"] == 1
    assert report["records"]["target_records"] == 3
    assert report["records"]["changed"] == 1
    assert report["records"]["no_budget"] == 2
    assert report["records"]["reason_counts"] == {
        "budget_admissible_lower_red_candidate": 1,
        "no_budget_admissible_lower_red_candidate": 2,
    }
    assert report["records"]["no_budget_class_counts"] == {
        "lower_red_hard_feasible_but_budget_empty": 1,
        "splice_removed_lower_red_advantage": 1,
    }
    changed = report["safety_opportunity"]["changed"]
    assert changed["zero_union_red_records"] == 1
    assert changed["union_red_reduction"]["mean"] == 10.0
    assert changed["progress_loss_m"]["max"] == 0.5
    assert report["latency"]["all_target_records"]["count"] == 3
    assert report["by_run"][0]["changed"] == 1
    assert report["by_run"][0]["no_budget"] == 2


def test_render_markdown_includes_no_budget_classes(tmp_path: Path) -> None:
    _write_log(
        tmp_path,
        [
            _record(
                step=1,
                reason="no_budget_admissible_lower_red_candidate",
                lower_union_red_count=0,
            )
        ],
    )
    report = analyze([tmp_path / "pilot"], label="markdown")

    markdown = render_markdown(report)

    assert "splice_removed_lower_red_advantage" in markdown
    assert "Decision Boundary" in markdown


def test_analyze_requires_union_red_vector(tmp_path: Path) -> None:
    bad = _record(
        step=1,
        reason="budget_admissible_lower_red_candidate",
        changed=True,
        chosen_union_red=0.0,
    )
    bad.pop("candidate_horizon_union_planned_red_light_cost")
    _write_log(tmp_path, [bad])

    with pytest.raises(ValueError, match="candidate_horizon_union"):
        analyze([tmp_path / "pilot"])
