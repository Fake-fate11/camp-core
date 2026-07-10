from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.integrations import (
    run_diffusion_planner_dp_camp_v18_training_evaluation as module,
)


def test_frozen_training_and_evaluation_constants() -> None:
    assert module.TRAINING_SEED == 3408
    assert module.TIE_SEED == 3409
    assert module.BOOTSTRAP_SEED == 3410
    assert module.SCALE_PERCENTILE == 95.0
    assert module.MARGIN_SCALE == 0.1
    assert module.MARGIN_CLIP == 2.0
    assert module.CVAR_ALPHA == 0.9
    assert module.L2_REG == 1e-4
    assert module.MAX_ITER == 20
    assert module.TOLERANCE == 1e-6
    assert module.SOLVER == "CLARABEL"
    assert module.MISS_THRESHOLD_M == 2.0
    assert module.ADE_TIE_TOLERANCE_M == 1e-9
    assert module.BOOTSTRAP_REPLICATES == 10_000
    assert module.FORBIDDEN_SEEDS == (11, 12, 13)
    assert module.BASELINE_SEMANTICS == "fixed_dp_deterministic_map_baseline"
    assert module.NATIVE_RANKED_TOP1 is False


def test_candidate_errors_use_xy_ade_and_final_xy_fde() -> None:
    candidates = np.zeros((2, 3, 4), dtype=np.float64)
    candidates[0, :, 0] = [1.0, 2.0, 3.0]
    candidates[1, :, 1] = [2.0, 2.0, 2.0]
    expert = np.zeros((3, 3), dtype=np.float64)

    ade, fde = module.candidate_ade_fde(candidates, expert)

    np.testing.assert_allclose(ade, [2.0, 2.0])
    np.testing.assert_allclose(fde, [3.0, 2.0])


def test_oracle_is_ade_primary_fde_secondary_then_seeded_priority() -> None:
    priority = module.tie_priority(4)
    ade = np.array(
        [
            [1.0, 1.0 + 5e-10, 2.0, 3.0],
            [1.0, 1.0, 4.0, 5.0],
        ],
        dtype=np.float64,
    )
    fde = np.array(
        [
            [3.0, 2.0, 1.0, 1.0],
            [2.0, 2.0, 1.0, 1.0],
        ],
        dtype=np.float64,
    )
    feasible = np.ones((2, 4), dtype=bool)

    oracle = module.oracle_indices(ade, fde, feasible, priority=priority)

    assert oracle[0] == 1
    assert oracle[1] == min((0, 1), key=lambda index: priority[index])


def test_oracle_and_selector_fail_closed_for_all_k_infeasible() -> None:
    feasible = np.zeros((1, 3), dtype=bool)
    with pytest.raises(ValueError, match="finite feasible candidate"):
        module.oracle_indices(
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            feasible,
            priority=module.tie_priority(3),
        )
    with pytest.raises(ValueError, match="finite feasible candidate"):
        module.select_indices(
            np.zeros((1, 3, 2)),
            np.array([0.5, 0.5]),
            feasible,
            priority=module.tie_priority(3),
        )


def test_train_atom_scales_use_only_feasible_train_rows() -> None:
    atoms = np.array(
        [
            [[1.0, 10.0], [1000.0, 1000.0]],
            [[3.0, 30.0], [5.0, 50.0]],
        ],
        dtype=np.float64,
    )
    feasible = np.array([[True, False], [True, True]], dtype=bool)

    scales = module.train_atom_scales(atoms, feasible, percentile=50.0)

    np.testing.assert_allclose(scales, [3.0, 30.0])


def test_select_indices_is_affine_masked_and_seed_tie_deterministic() -> None:
    atoms = np.array(
        [
            [[1.0, 1.0], [1.0, 1.0], [0.0, 0.0]],
            [[5.0, 0.0], [0.0, 5.0], [9.0, 9.0]],
        ],
        dtype=np.float64,
    )
    feasible = np.array([[True, True, False], [True, True, False]])
    weights = np.array([0.5, 0.5])
    priority = module.tie_priority(3)

    selected, scores = module.select_indices(
        atoms, weights, feasible, priority=priority
    )

    assert selected[0] == min((0, 1), key=lambda index: priority[index])
    assert selected[1] == min((0, 1), key=lambda index: priority[index])
    assert np.isinf(scores[:, 2]).all()


def test_ade_margins_are_nonnegative_and_clipped() -> None:
    ade = np.array([[1.0, 2.0, 50.0]], dtype=np.float64)
    oracle = np.array([0], dtype=np.int64)
    feasible = np.ones((1, 3), dtype=bool)

    margins = module.ade_margins(
        ade,
        oracle,
        feasible,
        margin_scale=0.1,
        margin_clip=2.0,
    )

    np.testing.assert_allclose(margins, [[0.0, 0.1, 2.0]])


def test_cluster_bootstrap_is_deterministic_for_scene_and_log() -> None:
    deltas = {
        "ade": np.array([-1.0, 0.0, 1.0, 2.0]),
        "fde": np.array([-2.0, 0.0, 2.0, 4.0]),
        "miss": np.array([-1.0, 0.0, 0.0, 1.0]),
    }
    logs = np.array(["a", "a", "b", "c"])
    scenes = np.array(["s0", "s1", "s2", "s3"])

    first = module.paired_cluster_bootstrap(
        deltas,
        log_ids=logs,
        scene_ids=scenes,
        replicates=500,
        seed=module.BOOTSTRAP_SEED,
    )
    second = module.paired_cluster_bootstrap(
        deltas,
        log_ids=logs,
        scene_ids=scenes,
        replicates=500,
        seed=module.BOOTSTRAP_SEED,
    )

    assert first == second
    assert set(first) == {"log_cluster", "scene_cluster"}
    for cluster in first.values():
        assert set(cluster) == {"ade", "fde", "miss"}
        assert all(len(interval) == 2 for interval in cluster.values())


def _split_data(split: str, count: int, *, atom_offset: float = 0.0):
    atoms = np.zeros((count, 8, 14), dtype=np.float64)
    candidates = np.zeros((count, 8, 80, 4), dtype=np.float64)
    labels = np.zeros((count, 80, 3), dtype=np.float64)
    for record_index in range(count):
        for candidate_index in range(8):
            atoms[record_index, candidate_index] = (
                atom_offset + record_index + candidate_index + 1.0
            )
            candidates[record_index, candidate_index, :, 0] = candidate_index
    return module.SplitData(
        split=split,
        rows=tuple(
            {
                "split": split,
                "log_token": f"{split}_log_{index // 2}",
                "scene_token": f"{split}_scene_{index}",
                "decision_token": f"{split}_decision_{index}",
            }
            for index in range(count)
        ),
        atoms=atoms,
        feasible_mask=np.ones((count, 8), dtype=bool),
        candidates=candidates,
        labels=labels,
    )


def _training_args(tmp_path) -> argparse.Namespace:
    return argparse.Namespace(
        canonical_root=tmp_path / "canonical",
        canonical_sha256s=tmp_path / "canonical.sha256s",
        expected_canonical_root_sha256="a" * 64,
        candidate_root=tmp_path / "candidates",
        expected_candidate_root_sha256="b" * 64,
        equivalence_review=tmp_path / "equivalence_review",
        expected_equivalence_review_root_sha256="c" * 64,
        output_dir=tmp_path / "freeze",
        current_status=tmp_path / "status.md",
        v18_audit=tmp_path / "audit.md",
    )


def _accepted_master_result(atoms, oracle, margins, feasible, config):
    weights = np.full(atoms.shape[2], 1.0 / atoms.shape[2])
    _, violations, _ = module.candidate_ranking_violations(
        atoms, weights, oracle, margins, feasible
    )
    return SimpleNamespace(
        static_weights=weights,
        theta=None,
        train_weights=np.broadcast_to(weights, (atoms.shape[0], atoms.shape[2])),
        train_violations=violations,
        final_master_gap=0.0,
        history=[{"iteration": 1, "new_cuts": 0, "max_master_gap": 0.0}],
        converged=True,
        cuts_per_scene=[1] * atoms.shape[0],
        solver_status="optimal",
    )


def _write_materialized_record(tmp_path, split: str, *, include_label: bool):
    canonical_root = tmp_path / "canonical"
    candidate_root = tmp_path / "candidates"
    relative = f"{split}/log/scene.npz"
    candidate_path = candidate_root / relative
    candidate_path.parent.mkdir(parents=True)
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    np.savez(candidate_path, candidate_tensor=candidates)
    canonical_path = canonical_root / relative
    canonical_path.parent.mkdir(parents=True)
    values = {
        "atom_matrix": np.ones((8, 14), dtype=np.float64),
        "atom_names": np.asarray(module.DP_CAMP_ATOM_NAMES_V10),
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "schema_version": np.array("dp_camp_v10_14d"),
        "source_candidate_npz": np.array(relative),
        "source_candidate_npz_sha256": np.array(module._sha256(candidate_path)),
        "baseline_index": np.array(0),
        "baseline_semantics": np.array(module.BASELINE_SEMANTICS),
        "native_ranked_top1": np.array(False),
        "feasibility_scope": np.array(module.FEASIBILITY_SCOPE),
        "closed_loop_safety_claim": np.array(False),
    }
    if include_label:
        values["expert_ego_future_xyh"] = np.zeros((80, 3), dtype=np.float64)
    np.savez(canonical_path, **values)
    row = {
        "split": split,
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "canonical_output_npz": relative,
        "canonical_output_npz_sha256": module._sha256(canonical_path),
    }
    (canonical_root / "records.jsonl").write_text(
        json.dumps(row) + "\n", encoding="utf-8"
    )
    return canonical_root, candidate_root


def test_materialized_loader_enforces_train_labels_and_holdout_sealing(
    tmp_path,
) -> None:
    holdout_root, candidate_root = _write_materialized_record(
        tmp_path / "holdout_case", "holdout", include_label=False
    )
    holdout = module.load_materialized_split(
        holdout_root, candidate_root, "holdout", labels_required=False
    )
    assert holdout.labels is None
    assert holdout.atoms.shape == (1, 8, 14)

    with pytest.raises(ValueError, match="required"):
        module.load_materialized_split(
            holdout_root, candidate_root, "holdout", labels_required=True
        )

    train_root, train_candidates = _write_materialized_record(
        tmp_path / "train_case", "train", include_label=True
    )
    train = module.load_materialized_split(
        train_root, train_candidates, "train", labels_required=True
    )
    assert train.labels.shape == (1, 80, 3)
    with pytest.raises(ValueError, match="forbidden"):
        module.load_materialized_split(
            train_root, train_candidates, "train", labels_required=False
        )


def test_train_calibrate_uses_train_only_scales_and_exact_master_contract(
    tmp_path, monkeypatch
) -> None:
    train = _split_data("train", 2)
    calibration = _split_data("calibration", 1, atom_offset=10_000.0)
    monkeypatch.setattr(module, "EXPECTED_TRAIN_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_CALIBRATION_COUNT", 1)
    monkeypatch.setattr(module, "_verify_training_inputs", lambda _args: {"ok": True})
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {"next_work_target": "implementation-test"},
    )
    monkeypatch.setattr(
        module,
        "load_materialized_split",
        lambda _canonical, _candidate, split, **_kwargs: (
            train if split == "train" else calibration
        ),
    )
    observed = {}

    def fake_master(atoms, oracle, margins, feasible, *, config, features=None):
        observed["config"] = config
        observed["features"] = features
        observed["records"] = atoms.shape[0]
        return _accepted_master_result(atoms, oracle, margins, feasible, config)

    monkeypatch.setattr(module, "solve_robust_margin_cutting_plane", fake_master)

    summary = module.run_train_calibrate(_training_args(tmp_path))

    assert observed["records"] == 2
    assert observed["features"] is None
    config = observed["config"]
    assert config.mode == "static"
    assert config.risk_type == "cvar"
    assert config.alpha == 0.9
    assert config.l2_reg == 1e-4
    assert config.max_iter == 20
    assert config.tolerance == 1e-6
    assert config.solver == "CLARABEL"
    assert summary["holdout_label_reads"] == 0
    assert summary["train_records"] == 2
    assert summary["calibration_records"] == 1
    assert summary["solver_status"] == "optimal"
    assert summary["native_ranked_top1"] is False
    assert summary["baseline_semantics"] == module.BASELINE_SEMANTICS
    assert (tmp_path / "freeze" / "ROOT_SHA256SUMS").is_file()
    scales = json.loads(
        (tmp_path / "freeze" / "atom_scales.json").read_text(encoding="utf-8")
    )["scales"]
    np.testing.assert_allclose(
        scales,
        module.train_atom_scales(train.atoms, train.feasible_mask),
    )
    protocol = json.loads(
        (tmp_path / "freeze" / "paired_eval_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["holdout_label_reads"] == 0
    assert protocol["bootstrap_seed"] == 3410
    assert protocol["bootstrap_replicates"] == 10_000
    assert protocol["miss_threshold_m"] == 2.0
    assert protocol["native_ranked_top1"] is False


@pytest.mark.parametrize(
    ("solver_status", "converged", "gap", "new_cuts", "match"),
    [
        ("optimal_inaccurate", True, 0.0, 0, "exact optimal"),
        ("optimal", False, 0.0, 0, "converged"),
        ("optimal", True, 1e-4, 0, "master gap"),
        ("optimal", True, 0.0, 1, "new cuts"),
    ],
)
def test_train_calibrate_fail_closed_before_checkpoint_promotion(
    tmp_path,
    monkeypatch,
    solver_status,
    converged,
    gap,
    new_cuts,
    match,
) -> None:
    train = _split_data("train", 1)
    calibration = _split_data("calibration", 1)
    monkeypatch.setattr(module, "EXPECTED_TRAIN_COUNT", 1)
    monkeypatch.setattr(module, "EXPECTED_CALIBRATION_COUNT", 1)
    monkeypatch.setattr(module, "_verify_training_inputs", lambda _args: {})
    monkeypatch.setattr(module, "read_v18_status_pointer", lambda *_args: {})
    monkeypatch.setattr(
        module,
        "load_materialized_split",
        lambda _canonical, _candidate, split, **_kwargs: (
            train if split == "train" else calibration
        ),
    )

    def fake_master(atoms, oracle, margins, feasible, *, config, features=None):
        result = _accepted_master_result(atoms, oracle, margins, feasible, config)
        result.solver_status = solver_status
        result.converged = converged
        result.final_master_gap = gap
        result.history[-1]["new_cuts"] = new_cuts
        return result

    monkeypatch.setattr(module, "solve_robust_margin_cutting_plane", fake_master)
    args = _training_args(tmp_path)

    with pytest.raises(RuntimeError, match=match):
        module.run_train_calibrate(args)

    assert not args.output_dir.exists()
