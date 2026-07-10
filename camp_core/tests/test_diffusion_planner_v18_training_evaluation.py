from __future__ import annotations

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
