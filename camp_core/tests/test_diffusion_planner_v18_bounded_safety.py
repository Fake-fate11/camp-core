from __future__ import annotations

import argparse
import json

import numpy as np
import pytest

from scripts.integrations import (
    run_diffusion_planner_dp_camp_v18_bounded_safety as module,
)
from scripts.integrations import (
    run_diffusion_planner_dp_camp_v18_training_evaluation as base,
)


def _straight_candidates(count: int = 1, *, acceleration: float = 0.0) -> np.ndarray:
    time_s = np.arange(80, dtype=np.float64) * 0.1
    candidates = np.zeros((count, 80, 4), dtype=np.float64)
    candidates[:, :, 0] = time_s + 0.5 * acceleration * time_s**2
    candidates[:, :, 2] = 1.0
    return candidates


def _components(**overrides):
    values = {
        "atom_matrix": np.zeros((1, 14), dtype=np.float64),
        "candidates": _straight_candidates(),
        "lane_feasible_mask": np.array([True]),
        "obb_collision_free_mask": np.array([True]),
        "physical_feasible_mask": np.array([True]),
        "route_progress": np.array([10.0]),
        "progress_reference": 10.0,
        "minimum_obb_clearance": np.full((1, 80), 3.0),
        "planned_red_light_cost": np.array([0.0]),
    }
    values.update(overrides)
    return module.candidate_safety_components(**values)


def test_compliant_candidate_scores_100_without_learned_weights() -> None:
    components = _components()

    assert components["bounded_offline_safety_score"][0] == pytest.approx(100.0)
    assert components["clearance_score"][0] == 1.0
    assert components["speed_score"][0] == 1.0
    assert components["progress_score"][0] == 1.0
    assert components["comfort_score"][0] == 1.0


@pytest.mark.parametrize(
    "override",
    [
        {"obb_collision_free_mask": np.array([False])},
        {"lane_feasible_mask": np.array([False])},
        {"planned_red_light_cost": np.array([1.1e-12])},
        {"route_progress": np.array([1.9])},
    ],
)
def test_each_hard_multiplier_zeros_score(override) -> None:
    assert _components(**override)["bounded_offline_safety_score"][0] == 0.0


def test_soft_components_use_frozen_clearance_speed_and_progress_scales() -> None:
    atoms = np.zeros((1, 14), dtype=np.float64)
    atoms[0, 4] = 7.9 * 2.23**2

    components = _components(
        atom_matrix=atoms,
        route_progress=np.array([5.0]),
        minimum_obb_clearance=np.full((1, 80), 1.5),
    )

    assert components["clearance_score"][0] == pytest.approx(0.5)
    assert components["speed_score"][0] == pytest.approx(0.0)
    assert components["progress_score"][0] == pytest.approx(0.5)
    assert components["bounded_offline_safety_score"][0] == pytest.approx(43.75)


def test_official_comfort_bounds_reject_excess_longitudinal_acceleration() -> None:
    assert module.trajectory_comfort_pass(_straight_candidates())[0]
    assert not module.trajectory_comfort_pass(
        _straight_candidates(acceleration=3.0)
    )[0]


def test_nonfinite_candidate_fails_closed() -> None:
    candidates = _straight_candidates()
    candidates[0, 0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        _components(candidates=candidates)


def _holdout_data() -> base.SplitData:
    candidates = np.repeat(_straight_candidates(8)[None, ...], 2, axis=0)
    atoms = np.zeros((2, 8, 14), dtype=np.float64)
    feasible = np.ones((2, 8), dtype=bool)
    feasible[0, 0] = False
    rows = tuple(
        {
            "split": "holdout",
            "log_token": f"log-{index}",
            "scene_token": f"scene-{index}",
            "decision_token": f"decision-{index}",
            "canonical_output_npz": f"holdout/log-{index}/scene-{index}.npz",
            "canonical_output_npz_sha256": "0" * 64,
        }
        for index in range(2)
    )
    return base.SplitData(
        split="holdout",
        rows=rows,
        atoms=atoms,
        feasible_mask=feasible,
        candidates=candidates,
        labels=None,
    )


def _component_inputs() -> dict[str, np.ndarray]:
    collision = np.ones((2, 8), dtype=bool)
    collision[0, 0] = False
    physical = collision.copy()
    return {
        "lane_feasible_mask": np.ones((2, 8), dtype=bool),
        "obb_collision_free_mask": collision,
        "physical_feasible_mask": physical,
        "route_progress": np.full((2, 8), 10.0),
        "progress_reference": np.full(2, 10.0),
        "minimum_obb_clearance": np.full((2, 8, 80), 3.0),
        "planned_red_light_cost": np.zeros((2, 8)),
    }


def _paired_root(tmp_path) -> tuple[object, str]:
    root = tmp_path / "paired"
    root.mkdir()
    rows = [
        {
            "record_index": index,
            "split": "holdout",
            "log_token": f"log-{index}",
            "scene_token": f"scene-{index}",
            "decision_token": f"decision-{index}",
            "selected_index": selected,
            "baseline_index": 0,
        }
        for index, selected in enumerate((1, 0))
    ]
    (root / "records.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    (root / "summary.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "holdout_records": 2,
                "holdout_label_reads": 2,
                "raw_holdout_labels_persisted": False,
                "baseline_semantics": base.BASELINE_SEMANTICS,
                "native_ranked_top1": False,
                "closed_loop_safety_claim": False,
            }
        ),
        encoding="utf-8",
    )
    return root, base._write_root_manifest(root)


def _evaluation_args(tmp_path, paired_root, paired_sha) -> argparse.Namespace:
    return argparse.Namespace(
        canonical_root=tmp_path / "canonical",
        canonical_sha256s=tmp_path / "canonical.sha256s",
        expected_canonical_root_sha256="a" * 64,
        candidate_root=tmp_path / "candidates",
        expected_candidate_root_sha256="b" * 64,
        paired_eval_root=paired_root,
        expected_paired_eval_root_sha256=paired_sha,
        output_dir=tmp_path / "safety",
        current_status=tmp_path / "status.md",
        v18_audit=tmp_path / "audit.md",
    )


def test_evaluate_is_label_free_atomic_and_reports_paired_score(
    tmp_path, monkeypatch
) -> None:
    holdout = _holdout_data()
    paired_root, paired_sha = _paired_root(tmp_path)
    args = _evaluation_args(tmp_path, paired_root, paired_sha)
    monkeypatch.setattr(module, "EXPECTED_HOLDOUT_COUNT", 2)
    monkeypatch.setattr(module, "BOOTSTRAP_REPLICATES", 50)
    monkeypatch.setattr(module, "_verify_sources", lambda _args: None)
    monkeypatch.setattr(module, "load_materialized_split", lambda *_a, **_k: holdout)
    monkeypatch.setattr(
        module, "load_candidate_component_inputs", lambda *_a, **_k: _component_inputs()
    )
    monkeypatch.setattr(module, "read_v18_status_pointer", lambda *_a: {"ok": True})

    summary = module.run_evaluate(args)

    assert summary["holdout_label_reads"] == 0
    assert summary["raw_holdout_labels_persisted"] is False
    assert summary["camp"]["mean_bounded_offline_safety_score"] == 100.0
    assert summary["baseline"]["mean_bounded_offline_safety_score"] == 50.0
    assert summary["paired_delta_camp_minus_baseline"]["mean_score"] == 50.0
    assert summary["better_tie_worse"] == {"better": 1, "tie": 1, "worse": 0}
    assert set(summary["paired_ci95"]) == {"log_cluster", "scene_cluster"}
    protocol = json.loads((args.output_dir / "protocol.json").read_text())
    assert protocol["schema_version"] == "camp_dp_bounded_offline_safety_score_v1"
    assert protocol["learned_selector_weights_used"] is False
    records = [
        json.loads(line)
        for line in (args.output_dir / "records.jsonl").read_text().splitlines()
    ]
    assert len(records) == 2
    assert all("expert_future" not in json.dumps(row) for row in records)
    assert (args.output_dir / "ROOT_SHA256SUMS").is_file()


def test_existing_output_blocks_evaluate_before_source_access(
    tmp_path, monkeypatch
) -> None:
    paired_root, paired_sha = _paired_root(tmp_path)
    args = _evaluation_args(tmp_path, paired_root, paired_sha)
    args.output_dir.mkdir()
    touched = []
    monkeypatch.setattr(module, "_verify_sources", lambda _args: touched.append(1))

    with pytest.raises(FileExistsError):
        module.run_evaluate(args)

    assert touched == []
