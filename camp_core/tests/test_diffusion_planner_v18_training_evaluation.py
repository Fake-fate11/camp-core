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
    assert module.EXPECTED_SOURCE_COUNT == 10_000
    assert module.EXPECTED_MATERIALIZED_COUNT == 9_458
    assert module.EXPECTED_CANONICAL_MANIFEST_ENTRIES == 9_460
    assert module.EXPECTED_SOURCE_SPLIT_COUNTS == {
        "train": 6_000,
        "calibration": 2_000,
        "holdout": 2_000,
    }
    assert module.EXPECTED_MATERIALIZED_SPLIT_COUNTS == {
        "train": 5_631,
        "calibration": 1_896,
        "holdout": 1_931,
    }
    assert module.EXPECTED_SOURCE_INCOMPLETE_COUNT == 243
    assert module.EXPECTED_ALL_K_INFEASIBLE_COUNT == 299
    assert module.EXPECTED_TRAIN_COUNT == 5_631
    assert module.EXPECTED_CALIBRATION_COUNT == 1_896
    assert module.EXPECTED_HOLDOUT_COUNT == 1_931
    assert module.EXPECTED_EXCLUDED_HOLDOUT_COUNT == 69
    assert module.LEARNING_CURVE_TRAIN_COUNTS == (564, 1_408, 2_816, 5_631)
    assert module.CORRECTED_SCHEMA_DIMS == (9, 10, 12, 13, 14)
    assert module.TRAIN_SCHEMA_VERSION == (
        "dp_camp_v18_nuplan_causal_10k_static_14d_train_calibrate_v1"
    )
    assert module.EVAL_SCHEMA_VERSION == (
        "dp_camp_v18_nuplan_causal_10k_one_shot_paired_eval_v1"
    )
    assert module.CLAIM_SCOPE == "causal_10k_offline_fixed_candidate_comparison_only"
    assert module.BOUNDED_OFFLINE_SAFETY_PROTOCOL_SHA256 == (
        "54022f480b53d1a036af82f81b4d9124b333bda1971a07122523e9e692a6f94b"
    )
    assert module.EXPECTED_CANDIDATE_ROOT_SHA256 == (
        "3febcd4de182598e69d3420900c996eb37dc3f54d0a8a4a1f221d6ab3c648515"
    )
    assert module.EXPECTED_CANONICAL_ROOT_SHA256 == (
        "79c9570bf04088ff05aea30a1e251738742e3648742044be724b662ff5329a3c"
    )
    assert module.EXPECTED_EQUIVALENCE_REVIEW_ROOT_SHA256 == (
        "aacbab7f5b64bdec369435309a3530b4cec6d704c031be6c8d8322b2a4ff6446"
    )
    assert module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256 == (
        "b09a81f94776a59ad6ac8fe93ec27f610d4b74859efa1b10f7f4d0160596a058"
    )
    assert module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256 == (
        "de5a90b7ac5e4295b58f11f48ddbb519646130129644c7cbc8d7b559051b29ea"
    )
    assert module.PRE_HOLDOUT_CLAIM_STATUS == (
        "pending_no_performance_claim_before_one_shot_result_review"
    )
    assert module.SAFETY_CLAIM_SCOPE == (
        "no_complete_scene_closed_loop_or_real_world_safety_claim"
    )
    assert module.LEGACY9D_STATUS == "unavailable"
    assert module.CORRECTED_SCHEMA_NAMES == (
        "camp_legacy_v1_9d",
        "dp_camp_v7_10d",
        "dp_camp_v8_12d",
        "dp_camp_v9_13d",
        "dp_camp_v10_14d",
    )
    assert module.COMPARISON_FAMILY == (
        "fixed_dp_deterministic_map_baseline",
        "uniform14d",
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
        "mini_trained14d",
        "feasible_best_of_k_oracle",
    )


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
                "canonical_output_npz": f"{split}/{index}.npz",
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
        mini_selector_freeze=tmp_path / "mini_selector_freeze",
        mini_selector_review=tmp_path / "mini_selector_review",
        output_dir=tmp_path / "freeze",
        current_status=tmp_path / "status.md",
        v18_audit=tmp_path / "audit.md",
    )


def test_training_inputs_accept_causal_10k_top_level_equivalence_review(
    tmp_path, monkeypatch
) -> None:
    args = _training_args(tmp_path)
    args.expected_canonical_root_sha256 = module.EXPECTED_CANONICAL_ROOT_SHA256
    args.expected_candidate_root_sha256 = module.EXPECTED_CANDIDATE_ROOT_SHA256
    args.expected_equivalence_review_root_sha256 = (
        module.EXPECTED_EQUIVALENCE_REVIEW_ROOT_SHA256
    )
    monkeypatch.setattr(module, "_verify_sha_list", lambda *_args: 9_460)
    monkeypatch.setattr(
        module,
        "_verified_candidate_source",
        lambda *_args: ([None] * 10_000, [None] * 10_000, None, None),
    )
    monkeypatch.setattr(
        module,
        "_verify_artifact_root",
        lambda *_args: {
            "status": "passed",
            "equivalence_verified": True,
            "native_ranked_top1": False,
            "records_reviewed": 10_000,
        },
    )
    monkeypatch.setattr(
        module,
        "_verify_mini_selector_inputs",
        lambda _args: {
            "freeze_path": str(args.mini_selector_freeze),
            "freeze_root_sha256": module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256,
            "review_path": str(args.mini_selector_review),
            "review_root_sha256": module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256,
        },
    )

    result = module._verify_training_inputs(args)

    assert result == {
        "canonical_manifest_entries": 9_460,
        "candidate_record_count": 10_000,
        "candidate_source_count": 10_000,
        "equivalence_verified": True,
        "mini_trained14d": {
            "freeze_path": str(args.mini_selector_freeze),
            "freeze_root_sha256": module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256,
            "review_path": str(args.mini_selector_review),
            "review_root_sha256": module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256,
        },
    }


def test_training_inputs_reject_nonfrozen_causal_10k_root(tmp_path) -> None:
    args = _training_args(tmp_path)

    with pytest.raises(ValueError, match="frozen causal-10k roots"):
        module._verify_training_inputs(args)


def test_training_inputs_reject_nested_mini_equivalence_schema(
    tmp_path, monkeypatch
) -> None:
    args = _training_args(tmp_path)
    args.expected_canonical_root_sha256 = module.EXPECTED_CANONICAL_ROOT_SHA256
    args.expected_candidate_root_sha256 = module.EXPECTED_CANDIDATE_ROOT_SHA256
    args.expected_equivalence_review_root_sha256 = (
        module.EXPECTED_EQUIVALENCE_REVIEW_ROOT_SHA256
    )
    monkeypatch.setattr(
        module,
        "_verify_sha_list",
        lambda *_args: module.EXPECTED_CANONICAL_MANIFEST_ENTRIES,
    )
    monkeypatch.setattr(
        module,
        "_verified_candidate_source",
        lambda *_args: ([None] * 10_000, [None] * 10_000, None, None),
    )
    monkeypatch.setattr(
        module,
        "_verify_artifact_root",
        lambda *_args: {
            "status": "passed",
            "review": {
                "equivalence_verified": True,
                "native_ranked_top1": False,
                "record_count": 10_000,
            },
        },
    )
    monkeypatch.setattr(module, "_verify_mini_selector_inputs", lambda _args: {})

    with pytest.raises(ValueError, match="equivalence review failed"):
        module._verify_training_inputs(args)


def test_mini_selector_inputs_verify_frozen_freeze_and_review(
    tmp_path, monkeypatch
) -> None:
    args = _training_args(tmp_path)
    observed = {}

    def fake_sha_list(root, manifest, expected_root):
        observed["freeze"] = (root, manifest, expected_root)
        return 7

    def fake_review(root, expected_root, expected_freeze_root):
        observed["review"] = (root, expected_root, expected_freeze_root)
        return {"status": "passed"}

    monkeypatch.setattr(module, "_verify_sha_list", fake_sha_list)
    monkeypatch.setattr(module, "verify_freeze_review", fake_review)

    result = module._verify_mini_selector_inputs(args)

    assert observed["freeze"] == (
        args.mini_selector_freeze,
        args.mini_selector_freeze / "SHA256SUMS",
        module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256,
    )
    assert observed["review"] == (
        args.mini_selector_review,
        module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256,
        module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256,
    )
    assert result["freeze_root_sha256"] == (
        module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256
    )
    assert result["review_root_sha256"] == (
        module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256
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
        solver_name="CLARABEL",
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
    monkeypatch.setattr(module, "LEARNING_CURVE_TRAIN_COUNTS", (1, 2))
    monkeypatch.setattr(module, "LATENCY_REPETITIONS_PER_RECORD", 2)
    monkeypatch.setattr(
        module,
        "_verify_training_inputs",
        lambda _args: {"mini_trained14d": {"paths_verified": True}},
    )
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {
            "next_work_target": module.TRAIN_CALIBRATE_EXECUTION_TARGET
        },
    )
    monkeypatch.setattr(
        module,
        "load_materialized_split",
        lambda _canonical, _candidate, split, **_kwargs: (
            train if split == "train" else calibration
        ),
    )
    monkeypatch.setattr(
        module,
        "_load_primary_frozen_selector",
        lambda root, expected: {
            "weights": np.full(14, 1.0 / 14.0),
            "scales": np.ones(14),
        },
    )
    observed = []

    def fake_master(atoms, oracle, margins, feasible, *, config, features=None):
        observed.append((atoms.shape, config, features))
        return _accepted_master_result(atoms, oracle, margins, feasible, config)

    monkeypatch.setattr(module, "solve_robust_margin_cutting_plane", fake_master)

    summary = module.run_train_calibrate(_training_args(tmp_path))

    assert [shape for shape, _config, _features in observed] == [
        (2, 8, 9),
        (2, 8, 10),
        (2, 8, 12),
        (2, 8, 13),
        (2, 8, 14),
        (1, 8, 14),
    ]
    for _shape, config, features in observed:
        assert features is None
        assert config.mode == "static"
        assert config.risk_type == "cvar"
        assert config.alpha == 0.9
        assert config.l2_reg == 1e-4
        assert config.max_iter == 20
        assert config.tolerance == 1e-6
        assert config.solver == "CLARABEL"
        assert config.solver_options == module.CLARABEL_SOLVER_OPTIONS
    assert summary["holdout_label_reads"] == 0
    assert summary["train_records"] == 2
    assert summary["calibration_records"] == 1
    assert summary["solver_status"] == "optimal"
    assert summary["solver_name"] == "CLARABEL"
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
    assert protocol["solver_options"] == dict(module.CLARABEL_SOLVER_OPTIONS)
    assert protocol["native_ranked_top1"] is False
    assert protocol["comparison_family_sha256"] == module._sha256(
        tmp_path / "freeze" / "comparison_family.json"
    )
    comparison = json.loads(
        (tmp_path / "freeze" / "comparison_family.json").read_text(
            encoding="utf-8"
        )
    )
    assert tuple(comparison["model_order"]) == (
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
    )
    assert comparison["legacy9d"]["status"] == module.LEGACY9D_STATUS
    assert comparison["mini_trained14d"]["paths_verified"] is True
    assert comparison["mini_trained14d"]["calibration_metrics"]["records"] == 1
    assert comparison["uniform14d"]["scales_sha256"] == module._sha256(
        tmp_path / "freeze" / "atom_scales.json"
    )
    calibration_summary = json.loads(
        (tmp_path / "freeze" / "calibration_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(calibration_summary["metrics"]) == {
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
        "uniform14d",
        "mini_trained14d",
    }
    assert all(
        set(metrics["selector_latency_ms"])
        == {"mean", "p50", "p95", "p99", "max"}
        for metrics in calibration_summary["metrics"].values()
    )
    assert [row["train_records"] for row in comparison["learning_curve"]] == [
        1,
        2,
    ]
    for name in comparison["models"]:
        assert (tmp_path / "freeze" / "models" / f"{name}_weights.npy").is_file()
        assert (tmp_path / "freeze" / "models" / f"{name}_scales.json").is_file()


def test_train_calibrate_rejects_stale_eof_before_loading(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(module, "_verify_training_inputs", lambda _args: {})
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {"next_work_target": "stale_gate"},
    )
    monkeypatch.setattr(
        module,
        "load_materialized_split",
        lambda *_args, **_kwargs: pytest.fail("data loaded before EOF gate"),
    )

    with pytest.raises(RuntimeError, match="live v18 EOF"):
        module.run_train_calibrate(_training_args(tmp_path))


def test_train_calibrate_preflight_is_label_safe_and_execution_free(
    tmp_path, monkeypatch
) -> None:
    train = _split_data("train", 2)
    calibration = _split_data("calibration", 1)
    source_holdout = _split_data("holdout", 1)
    holdout = module.SplitData(
        split=source_holdout.split,
        rows=source_holdout.rows,
        atoms=source_holdout.atoms,
        feasible_mask=source_holdout.feasible_mask,
        candidates=source_holdout.candidates,
        labels=None,
    )
    args = _training_args(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_TRAIN_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_CALIBRATION_COUNT", 1)
    monkeypatch.setattr(module, "EXPECTED_HOLDOUT_COUNT", 1)
    monkeypatch.setattr(module, "EXPECTED_EXCLUDED_HOLDOUT_COUNT", 0)
    monkeypatch.setattr(module, "_verify_training_inputs", lambda _args: {})
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {
            "next_work_target": module.TRAIN_CALIBRATE_PREFLIGHT_TARGET
        },
    )
    observed = []

    def load_split(_canonical, _candidate, split, *, labels_required):
        observed.append((split, labels_required))
        return {"train": train, "calibration": calibration, "holdout": holdout}[
            split
        ]

    monkeypatch.setattr(module, "load_materialized_split", load_split)
    monkeypatch.setattr(
        module,
        "_materialized_identity_sets",
        lambda _root: (
            {
                "train": {module._identity(row) for row in train.rows},
                "calibration": {
                    module._identity(row) for row in calibration.rows
                },
                "holdout": {module._identity(row) for row in holdout.rows},
            },
            0,
        ),
    )
    monkeypatch.setattr(module, "_free_bytes_for_path", lambda _path: 11 << 30)
    monkeypatch.setattr(module, "_active_peer_gate_processes", lambda: [])
    monkeypatch.setattr(module, "_installed_solvers", lambda: ("CLARABEL",))

    report = module.run_train_calibrate_preflight(args)

    assert observed == [
        ("train", True),
        ("calibration", True),
        ("holdout", False),
    ]
    assert report["status"] == "passed"
    assert report["holdout_label_reads"] == 0
    assert report["training_executed"] is False
    assert report["model_calls"] == 0
    assert report["free_bytes"] == 11 << 30
    assert not args.output_dir.exists()
    assert not args.output_dir.with_name(args.output_dir.name + ".tmp").exists()

    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {"next_work_target": "stale_gate"},
    )
    with pytest.raises(RuntimeError, match="live v18 EOF"):
        module.run_train_calibrate_preflight(args)

    args.output_dir.mkdir()
    with pytest.raises(FileExistsError):
        module.run_train_calibrate_preflight(args)


def test_materialized_identity_sets_reject_log_or_scene_overlap(
    tmp_path, monkeypatch
) -> None:
    rows = [
        {
            "split": "train",
            "log_token": "shared_log",
            "scene_token": "train_scene",
            "decision_token": "train_decision",
            "canonical_output_npz": "train.npz",
        },
        {
            "split": "calibration",
            "log_token": "shared_log",
            "scene_token": "calibration_scene",
            "decision_token": "calibration_decision",
            "canonical_output_npz": "calibration.npz",
        },
    ]
    monkeypatch.setattr(module, "_canonical_rows", lambda _root: rows)

    with pytest.raises(ValueError, match="log/scene split overlap"):
        module._materialized_identity_sets(tmp_path)


def test_active_peer_detector_ignores_shell_wrapper(tmp_path) -> None:
    script_name = module.Path(module.__file__).name
    shell = tmp_path / "1001"
    shell.mkdir()
    (shell / "comm").write_text("bash\n", encoding="utf-8")
    (shell / "cmdline").write_bytes(
        f"bash\0-c\0python {script_name} --mode train-calibrate\0".encode()
    )
    python = tmp_path / "1002"
    python.mkdir()
    (python / "comm").write_text("python3\n", encoding="utf-8")
    (python / "cmdline").write_bytes(
        f"python3\0/runner/{script_name}\0--mode\0train-calibrate\0".encode()
    )

    peers = module._active_peer_gate_processes(tmp_path)

    assert len(peers) == 1
    assert peers[0].startswith("python3 ")


def test_fit_static_selector_uses_dimension_specific_convex_master(
    monkeypatch,
) -> None:
    train = _split_data("train", 2)
    ade, fde = module._split_errors(train)
    priority = module.tie_priority(8)
    observed = {}

    def fake_master(atoms, oracle, margins, feasible, *, config, features=None):
        observed["shape"] = atoms.shape
        observed["lower_bounds"] = config.static_weight_lower_bounds
        observed["features"] = features
        return _accepted_master_result(atoms, oracle, margins, feasible, config)

    monkeypatch.setattr(module, "solve_robust_margin_cutting_plane", fake_master)

    fitted = module._fit_static_selector(
        train.atoms[:, :, :9], train.feasible_mask, ade, fde, priority=priority
    )

    assert observed == {
        "shape": (2, 8, 9),
        "lower_bounds": (0.0,) * 9,
        "features": None,
    }
    assert fitted["weights"].shape == (9,)
    assert fitted["scales"].shape == (9,)
    assert fitted["solver"]["status"] == "optimal"
    assert fitted["solver"]["final_new_cuts"] == 0


def test_saved_simplex_projection_must_preserve_master_gap() -> None:
    atoms = np.array([[[10_000_000.0, 0.0], [0.0, 0.0]]])
    feasible = np.ones((1, 2), dtype=bool)
    oracle = np.array([0], dtype=np.int64)
    margins = np.array([[0.0, 2e-6]])
    raw = np.array([-1e-13, 1.0 + 1e-13])
    _, recorded, _ = module.candidate_ranking_violations(
        atoms, raw, oracle, margins, feasible
    )
    result = SimpleNamespace(
        solver_name="CLARABEL",
        solver_status="optimal",
        converged=True,
        final_master_gap=5e-7,
        history=[{"new_cuts": 0}],
        static_weights=raw,
        train_violations=recorded,
    )

    with pytest.raises(RuntimeError, match="projected master gap"):
        module._accepted_weights_and_violations(
            result, atoms, oracle, margins, feasible
        )


def test_comparison_family_fits_prefixes_and_nested_14d_curve(
    monkeypatch,
) -> None:
    train = _split_data("train", 4)
    calibration = _split_data("calibration", 2)
    monkeypatch.setattr(module, "LEARNING_CURVE_TRAIN_COUNTS", (1, 2, 4))
    calls = []

    def fake_fit(atoms, feasible, ade, fde, *, priority):
        calls.append((atoms.shape[2], atoms.shape[0]))
        dimension = atoms.shape[2]
        return {
            "weights": np.full(dimension, 1.0 / dimension),
            "scales": np.ones(dimension),
            "train_metrics": {"records": atoms.shape[0]},
            "solver": {"status": "optimal", "final_new_cuts": 0},
        }

    monkeypatch.setattr(module, "_fit_static_selector", fake_fit)

    result = module._fit_comparison_family(
        train, calibration, priority=module.tie_priority(8)
    )

    assert calls == [
        (9, 4),
        (10, 4),
        (12, 4),
        (13, 4),
        (14, 4),
        (14, 1),
        (14, 2),
    ]
    assert tuple(result["models"]) == (
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
    )
    assert [row["train_records"] for row in result["learning_curve"]] == [1, 2, 4]
    assert result["legacy9d"]["status"] == module.LEGACY9D_STATUS


@pytest.mark.parametrize(
    ("solver_name", "solver_status", "converged", "gap", "new_cuts", "match"),
    [
        ("SCS", "optimal", True, 0.0, 0, "CLARABEL solver"),
        ("CLARABEL", "optimal_inaccurate", True, 0.0, 0, "exact optimal"),
        ("CLARABEL", "optimal", False, 0.0, 0, "converged"),
        ("CLARABEL", "optimal", True, 1e-4, 0, "master gap"),
        ("CLARABEL", "optimal", True, float("nan"), 0, "master gap"),
        ("CLARABEL", "optimal", True, float("-inf"), 0, "master gap"),
        ("CLARABEL", "optimal", True, 0.0, 1, "new cuts"),
    ],
)
def test_train_calibrate_fail_closed_before_checkpoint_promotion(
    tmp_path,
    monkeypatch,
    solver_name,
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
    monkeypatch.setattr(module, "LEARNING_CURVE_TRAIN_COUNTS", (1,))
    monkeypatch.setattr(
        module,
        "_verify_training_inputs",
        lambda _args: {"mini_trained14d": {"paths_verified": True}},
    )
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {
            "next_work_target": module.TRAIN_CALIBRATE_EXECUTION_TARGET
        },
    )
    monkeypatch.setattr(
        module,
        "load_materialized_split",
        lambda _canonical, _candidate, split, **_kwargs: (
            train if split == "train" else calibration
        ),
    )
    monkeypatch.setattr(
        module,
        "load_frozen_selector",
        lambda *_args: {
            "weights": np.full(14, 1.0 / 14.0),
            "scales": np.ones(14),
        },
    )

    def fake_master(atoms, oracle, margins, feasible, *, config, features=None):
        result = _accepted_master_result(atoms, oracle, margins, feasible, config)
        result.solver_name = solver_name
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
    assert not args.output_dir.with_name(args.output_dir.name + ".tmp").exists()


def _evaluation_args(tmp_path) -> argparse.Namespace:
    args = _training_args(tmp_path)
    args.freeze_root = tmp_path / "freeze"
    args.expected_freeze_root_sha256 = "d" * 64
    args.freeze_review = tmp_path / "freeze_review"
    args.expected_freeze_review_root_sha256 = "e" * 64
    args.output_dir = tmp_path / "paired_eval"
    return args


def _write_test_freeze(
    root,
    *,
    latency_repetitions=2,
    bootstrap_replicates=50,
    include_comparison=True,
):
    root.mkdir(parents=True)
    weights = np.full(14, 1.0 / 14.0)
    np.save(root / "static_weights.npy", weights)
    (root / "atom_scales.json").write_text(
        json.dumps({"scales": [1.0] * 14}), encoding="utf-8"
    )
    protocol = {
        "status": "frozen",
        "equivalence_verified": True,
        "native_ranked_top1": False,
        "baseline_semantics": module.BASELINE_SEMANTICS,
        "feasibility_scope": module.FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
        "holdout_label_reads": 0,
        "tie_seed": module.TIE_SEED,
        "tie_priority": module.tie_priority(8).tolist(),
        "bootstrap_seed": module.BOOTSTRAP_SEED,
        "bootstrap_replicates": bootstrap_replicates,
        "ci_level": 0.95,
        "miss_threshold_m": module.MISS_THRESHOLD_M,
        "ade_tie_tolerance_m": module.ADE_TIE_TOLERANCE_M,
        "score_tie_tolerance": module.SCORE_TIE_TOLERANCE,
        "non_regression_slack": 0.0,
        "latency_repetitions_per_record": latency_repetitions,
        "expected_holdout_records": 2,
        "raw_holdout_labels_persisted": False,
        "claim_scope": module.CLAIM_SCOPE,
        "solver": module.SOLVER,
        "solver_options": dict(module.CLARABEL_SOLVER_OPTIONS),
        "weights_sha256": module._sha256(root / "static_weights.npy"),
        "atom_scales_sha256": module._sha256(root / "atom_scales.json"),
    }
    if include_comparison:
        models = root / "models"
        models.mkdir()
        model_order = [
            "corrected9d",
            "corrected10d",
            "corrected12d",
            "corrected13d",
            "corrected14d",
        ]
        model_manifest = {}
        for name, dimension in zip(model_order, module.CORRECTED_SCHEMA_DIMS):
            model_weights = np.full(dimension, 1.0 / dimension)
            weights_path = models / f"{name}_weights.npy"
            scales_path = models / f"{name}_scales.json"
            np.save(weights_path, model_weights)
            scales_path.write_text(
                json.dumps({"scales": [1.0] * dimension}), encoding="utf-8"
            )
            model_manifest[name] = {
                "dimension": dimension,
                "weights": weights_path.relative_to(root).as_posix(),
                "weights_sha256": module._sha256(weights_path),
                "scales": scales_path.relative_to(root).as_posix(),
                "scales_sha256": module._sha256(scales_path),
            }
        uniform_path = root / "uniform14d_weights.npy"
        mini_weights_path = models / "mini_trained14d_weights.npy"
        mini_scales_path = models / "mini_trained14d_scales.json"
        np.save(uniform_path, weights)
        np.save(mini_weights_path, weights)
        mini_scales_path.write_text(
            json.dumps({"scales": [1.0] * 14}), encoding="utf-8"
        )
        comparison = {
            "status": "frozen",
            "comparison_family": list(module.COMPARISON_FAMILY),
            "model_order": model_order,
            "models": model_manifest,
            "uniform14d": {
                "weights": uniform_path.relative_to(root).as_posix(),
                "weights_sha256": module._sha256(uniform_path),
                "scales": "atom_scales.json",
                "scales_sha256": module._sha256(root / "atom_scales.json"),
            },
        "mini_trained14d": {
            "weights": mini_weights_path.relative_to(root).as_posix(),
            "weights_sha256": module._sha256(mini_weights_path),
            "scales": mini_scales_path.relative_to(root).as_posix(),
            "scales_sha256": module._sha256(mini_scales_path),
            "freeze_root_sha256": (
                module.EXPECTED_MINI_SELECTOR_FREEZE_ROOT_SHA256
            ),
            "review_root_sha256": (
                module.EXPECTED_MINI_SELECTOR_REVIEW_ROOT_SHA256
            ),
            },
            "legacy9d": {
                "status": module.LEGACY9D_STATUS,
                "reason": module.LEGACY9D_UNAVAILABLE_REASON,
            },
        }
        (root / "comparison_family.json").write_text(
            json.dumps(comparison), encoding="utf-8"
        )
        protocol["comparison_family_sha256"] = module._sha256(
            root / "comparison_family.json"
        )
    (root / "paired_eval_protocol.json").write_text(
        json.dumps(protocol), encoding="utf-8"
    )
    (root / "training_summary.json").write_text(
        json.dumps({"status": "passed", "holdout_label_reads": 0}),
        encoding="utf-8",
    )
    return module._write_root_manifest(root)


def test_paired_eval_preflight_does_not_read_holdout_labels(
    tmp_path, monkeypatch
) -> None:
    holdout = _split_data("holdout", 1)
    holdout = module.SplitData(
        split=holdout.split,
        rows=holdout.rows,
        atoms=holdout.atoms,
        feasible_mask=holdout.feasible_mask,
        candidates=holdout.candidates,
        labels=None,
    )
    args = _evaluation_args(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_HOLDOUT_COUNT", 1)
    monkeypatch.setattr(module, "EXPECTED_EXCLUDED_HOLDOUT_COUNT", 0)
    monkeypatch.setattr(
        module,
        "_verify_evaluation_inputs",
        lambda _args: {
            "source_by_identity": {
                (
                    holdout.rows[0]["log_token"],
                    holdout.rows[0]["scene_token"],
                    holdout.rows[0]["decision_token"],
                ): {"db_path": "db", "decision_token": "decision"}
            },
            "freeze": {},
        },
    )
    monkeypatch.setattr(
        module, "load_materialized_split", lambda *_args, **_kwargs: holdout
    )
    monkeypatch.setattr(module, "_canonical_rows", lambda _root: list(holdout.rows))
    monkeypatch.setattr(module, "read_v18_status_pointer", lambda *_args: {})
    label_calls = []
    monkeypatch.setattr(
        module,
        "load_nuplan_expert_ego_future",
        lambda *_args, **_kwargs: label_calls.append(_args),
    )

    report = module.run_paired_eval_preflight(args)

    assert report["status"] == "passed"
    assert report["holdout_records"] == 1
    assert report["holdout_label_reads"] == 0
    assert label_calls == []
    assert not args.output_dir.exists()
    assert not args.output_dir.with_name(args.output_dir.name + ".tmp").exists()

    monkeypatch.setattr(module, "EXPECTED_EXCLUDED_HOLDOUT_COUNT", 1)
    with pytest.raises(ValueError, match="excluded holdout"):
        module.run_paired_eval_preflight(args)


def test_paired_eval_reads_each_label_once_and_persists_only_derived_metrics(
    tmp_path, monkeypatch
) -> None:
    holdout = _split_data("holdout", 2)
    holdout = module.SplitData(
        split=holdout.split,
        rows=holdout.rows,
        atoms=holdout.atoms,
        feasible_mask=holdout.feasible_mask,
        candidates=holdout.candidates,
        labels=None,
    )
    args = _evaluation_args(tmp_path)
    args.expected_freeze_root_sha256 = _write_test_freeze(args.freeze_root)
    source_by_identity = {
        (row["log_token"], row["scene_token"], row["decision_token"]): {
            "db_path": f"db_{index}",
            "decision_token": row["decision_token"],
        }
        for index, row in enumerate(holdout.rows)
    }
    monkeypatch.setattr(module, "EXPECTED_HOLDOUT_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_EXCLUDED_HOLDOUT_COUNT", 0)
    monkeypatch.setattr(
        module,
        "_verify_evaluation_inputs",
        lambda _args: {
            "source_by_identity": source_by_identity,
            "freeze": {"status": "passed"},
            "selector": module.load_frozen_selector(
                args.freeze_root, args.expected_freeze_root_sha256
            ),
        },
    )
    monkeypatch.setattr(
        module, "load_materialized_split", lambda *_args, **_kwargs: holdout
    )
    monkeypatch.setattr(module, "_canonical_rows", lambda _root: list(holdout.rows))
    monkeypatch.setattr(module, "read_v18_status_pointer", lambda *_args: {})
    calls = []
    bootstrap_seeds = []
    real_bootstrap = module.paired_cluster_bootstrap

    def recording_bootstrap(*args, **kwargs):
        bootstrap_seeds.append(kwargs["seed"])
        return real_bootstrap(*args, **kwargs)

    monkeypatch.setattr(module, "paired_cluster_bootstrap", recording_bootstrap)

    def label_loader(db_path, decision_token, **_kwargs):
        calls.append((db_path, decision_token))
        return np.zeros((80, 3), dtype=np.float64)

    summary = module.run_paired_eval(args, label_loader=label_loader)

    assert len(calls) == 2
    assert len(set(calls)) == 2
    assert summary["holdout_label_reads"] == 2
    assert summary["raw_holdout_labels_persisted"] is False
    assert summary["fallback_count"] == 0
    assert summary["native_ranked_top1"] is False
    assert set(summary["paired_ci95"]) == {"log_cluster", "scene_cluster"}
    assert set(summary["selector_latency_ms"]) == {
        "mean",
        "p50",
        "p95",
        "p99",
        "max",
    }
    expected_selectors = {
        "uniform14d",
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
        "mini_trained14d",
    }
    assert summary["primary_selector"] == "corrected14d"
    assert set(summary["selector_results"]) == expected_selectors
    expected_child_seeds = [
        int(child.generate_state(1, dtype=np.uint64)[0])
        for child in np.random.SeedSequence(module.BOOTSTRAP_SEED).spawn(
            len(expected_selectors)
        )
    ]
    assert bootstrap_seeds == expected_child_seeds
    assert all(
        set(result["selector_latency_ms"])
        == {"mean", "p50", "p95", "p99", "max"}
        for result in summary["selector_results"].values()
    )
    assert summary["legacy9d"] == {
        "status": module.LEGACY9D_STATUS,
        "reason": module.LEGACY9D_UNAVAILABLE_REASON,
    }
    assert summary["feasible_best_of_k_oracle"]["mean_ade_m"] == 0.0
    assert summary["aggregate"]["non_top1_rate"] == 0.0
    rows = [
        json.loads(line)
        for line in (args.output_dir / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 2
    assert all("expert_future_sha256" in row for row in rows)
    assert all("candidate_ade_m" in row and "candidate_fde_m" in row for row in rows)
    assert all("expert_ego_future_xyh" not in row for row in rows)
    assert all(set(row["selector_indices"]) == expected_selectors for row in rows)
    assert (args.output_dir / "ROOT_SHA256SUMS").is_file()


def test_paired_eval_existing_output_or_staging_blocks_before_label_read(
    tmp_path, monkeypatch
) -> None:
    args = _evaluation_args(tmp_path)
    calls = []
    for existing in (
        args.output_dir,
        args.output_dir.with_name(args.output_dir.name + ".tmp"),
    ):
        if args.output_dir.exists():
            args.output_dir.rmdir()
        staging = args.output_dir.with_name(args.output_dir.name + ".tmp")
        if staging.exists():
            staging.rmdir()
        existing.mkdir(parents=True)
        with pytest.raises(FileExistsError):
            module.run_paired_eval(
                args,
                label_loader=lambda *_args, **_kwargs: calls.append(1),
            )
        existing.rmdir()
    assert calls == []


def test_frozen_selector_root_rejects_post_freeze_mutation(tmp_path) -> None:
    freeze = tmp_path / "freeze"
    root_sha = _write_test_freeze(freeze)
    loaded = module.load_frozen_selector(freeze, root_sha)
    assert set(loaded["selectors"]) == {
        "uniform14d",
        "corrected9d",
        "corrected10d",
        "corrected12d",
        "corrected13d",
        "corrected14d",
        "mini_trained14d",
    }

    with (freeze / "static_weights.npy").open("ab") as stream:
        stream.write(b"mutation")

    with pytest.raises(ValueError, match="SHA256"):
        module.load_frozen_selector(freeze, root_sha)


def test_primary_frozen_selector_accepts_mini_single_model_layout(tmp_path) -> None:
    freeze = tmp_path / "mini_freeze"
    root_sha = _write_test_freeze(freeze, include_comparison=False)

    loaded = module._load_primary_frozen_selector(freeze, root_sha)

    np.testing.assert_allclose(loaded["weights"], np.full(14, 1.0 / 14.0))
    np.testing.assert_allclose(loaded["scales"], np.ones(14))


def test_frozen_selector_requires_exact_legacy_reason(tmp_path) -> None:
    freeze = tmp_path / "freeze"
    _write_test_freeze(freeze)
    comparison_path = freeze / "comparison_family.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["legacy9d"]["reason"] = "wrong"
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")
    protocol_path = freeze / "paired_eval_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["comparison_family_sha256"] = module._sha256(comparison_path)
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    root_sha = module._write_root_manifest(freeze)

    with pytest.raises(ValueError, match="comparison-family"):
        module.load_frozen_selector(freeze, root_sha)


def _write_freeze_review(root, freeze_root_sha):
    root.mkdir(parents=True)
    (root / "summary.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "run_exit": 0,
                "stderr_empty": True,
                "review": {
                    "status": "passed",
                    "freeze_root_sha256": freeze_root_sha,
                    "holdout_label_reads": 0,
                    "native_ranked_top1": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return module._write_root_manifest(root)


def test_freeze_review_gate_requires_passed_matching_review_root(tmp_path) -> None:
    review = tmp_path / "review"
    review_root = _write_freeze_review(review, "f" * 64)

    verified = module.verify_freeze_review(review, review_root, "f" * 64)
    assert verified["status"] == "passed"

    with pytest.raises(ValueError, match="freeze result review"):
        module.verify_freeze_review(review, review_root, "0" * 64)
