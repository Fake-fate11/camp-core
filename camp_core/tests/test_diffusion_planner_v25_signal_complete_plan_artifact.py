from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact


ROOT = Path(__file__).resolve().parents[2]


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAP_PRODUCER = _module(
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_maps.py",
    "v25_signal_map_producer_for_plan",
)
PLAN_PRODUCER = _module(
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_plan.py",
    "v25_signal_plan_producer",
)
PLAN_REVIEWER = _module(
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_plan.py",
    "v25_signal_plan_reviewer",
)


@pytest.mark.parametrize(
    ("split", "units", "arm_runs"),
    (("calibration", 100, 100), ("fresh_b2", 500, 1500)),
)
def test_plan_artifact_binds_map_root_and_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    split: str,
    units: int,
    arm_runs: int,
) -> None:
    monkeypatch.setattr(MAP_PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(MAP_PRODUCER, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(PLAN_PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PLAN_PRODUCER, "_git_head", lambda: "a" * 40)
    maps = tmp_path / f"{split}_maps"
    map_root = MAP_PRODUCER.build(split=split, output_dir=maps)
    plan_artifact = tmp_path / f"{split}_plan"
    plan_root = PLAN_PRODUCER.build(
        split=split,
        map_artifact=maps,
        map_root_sha256=map_root,
        output_dir=plan_artifact,
    )
    report = PLAN_REVIEWER.review(plan_artifact, plan_root)
    assert report["status"] == "passed_independent_signal_complete_plan_review"
    assert report["map_root_sha256"] == map_root
    assert report["execution_unit_count"] == units
    assert report["planned_arm_run_count"] == arm_runs
    assert report["all_family_tier_cells_nonzero"] is True
    assert report["fresh_b2_opened"] is False


def test_resealed_plan_online_phase_program_mutation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MAP_PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(MAP_PRODUCER, "_git_head", lambda: "b" * 40)
    monkeypatch.setattr(PLAN_PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PLAN_PRODUCER, "_git_head", lambda: "b" * 40)
    maps = tmp_path / "maps"
    map_root = MAP_PRODUCER.build(split="calibration", output_dir=maps)
    artifact = tmp_path / "plan"
    PLAN_PRODUCER.build(
        split="calibration",
        map_artifact=maps,
        map_root_sha256=map_root,
        output_dir=artifact,
    )
    plan_path = artifact / "execution_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    red = next(
        row for row in plan["identities"] if row["scenario_family"] == "red_light_phase_timing"
    )
    red["future_phase_program_present"] = True
    plan_path.write_bytes(
        (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    report_path = artifact / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    import hashlib

    report["plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    report_path.write_bytes(
        (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    mutated_root = seal_artifact(artifact, label="mutated signal-complete plan")
    with pytest.raises(ValueError, match="reconstruction"):
        PLAN_REVIEWER.review(artifact, mutated_root)
