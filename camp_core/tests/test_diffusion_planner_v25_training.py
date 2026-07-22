from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import (
    RAW_FEATURE_COUNT,
    fit_train_context_scaler,
)
from camp_core.integrations.diffusion_planner_v25_training import (
    MODEL_REGISTRY,
    train_v25_selector_suite,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    DEFAULT_LABEL_SEVERITY,
)
from camp_core.outer_master.parametric_cvxpy_master import V25ParametricMasterConfig
from scripts.integrations.review_diffusion_planner_v25_camp_training import (
    _active_atom_view,
    _array_sha as independently_review_array_sha,
    _context_scaler as independently_review_context_scaler,
    _exact_parameter_arrays,
    _solver_evidence_contract,
    _weighted_quantile as independently_review_weighted_quantile,
)


FROZEN_CONFIG_SHA256 = (
    "939a4cf4275daa205cad0aaf5aef25cfb65e5f9cc412e389191cae14d5044422"
)


def _training_inputs() -> tuple[np.ndarray, ...]:
    records = 5
    atoms = np.zeros((records, 8, 14), dtype=np.float64)
    atoms[:, 1, 0] = np.linspace(0.3, 0.7, records)
    atoms[:, 2, 1] = np.linspace(0.7, 0.3, records)
    atoms[:, 3:, :2] = 1.0
    contexts = np.linspace(
        0.0, 2.0, records * RAW_FEATURE_COUNT, dtype=np.float64
    ).reshape(records, RAW_FEATURE_COUNT)
    context_source = np.ones((records, RAW_FEATURE_COUNT), dtype=np.bool_)
    context_source[:, -1] = False
    oracle = np.zeros(records, dtype=np.int64)
    margins = np.zeros((records, 8), dtype=np.float64)
    margins[:, 1:] = 0.1
    source = np.ones((records, 8), dtype=np.bool_)
    weights = np.asarray([0.4, 0.25, 0.15, 0.1, 0.1], dtype=np.float64)
    return atoms, contexts, context_source, oracle, margins, source, weights


def _clusters() -> tuple[str, ...]:
    return ("corridor-a", "corridor-a", "corridor-b", "corridor-c", "corridor-c")


def _empirical_cdf_boundary_fixture() -> tuple[np.ndarray, ...]:
    values = np.arange(129, dtype=np.float64)
    weights = np.concatenate(
        (
            np.asarray([0.05], dtype=np.float64),
            np.full(128, 0.95 / 128.0, dtype=np.float64),
        )
    )
    raw = np.repeat(values[:, None], RAW_FEATURE_COUNT, axis=1)
    source = np.ones(raw.shape, dtype=np.bool_)
    return values, weights, raw, source


def test_training_reviewer_reproduces_frozen_empirical_cdf_boundary() -> None:
    values, weights, raw, source = _empirical_cdf_boundary_fixture()
    cumulative = np.cumsum(weights)
    assert float(cumulative[-1]) == 1.000000000000002
    assert float(np.sum(weights)) == 1.0

    producer = fit_train_context_scaler(
        raw,
        source_complete=source,
        record_weights=weights,
    )
    reviewed_q05, reviewed_q95 = independently_review_context_scaler(
        raw, source, weights
    )

    assert independently_review_weighted_quantile(values, weights, 0.05) == values[1]
    assert np.array_equal(reviewed_q05, producer.q05)
    assert np.array_equal(reviewed_q95, producer.q95)


def test_training_reviewer_weighted_quantile_handles_nonboundary_sample() -> None:
    values = np.asarray([0.0, 1.0, 2.0], dtype=np.float64)
    weights = np.asarray([0.2, 0.3, 0.5], dtype=np.float64)
    assert independently_review_weighted_quantile(values, weights, 0.5) == 1.0


def test_training_reviewer_keeps_exact_parameter_drift_rejection() -> None:
    values, weights, raw, source = _empirical_cdf_boundary_fixture()
    producer = fit_train_context_scaler(
        raw,
        source_complete=source,
        record_weights=weights,
    )
    scales = np.arange(1.0, 15.0, dtype=np.float64)
    assert _exact_parameter_arrays(
        producer.q05,
        producer.q95,
        scales,
        producer.q05,
        producer.q95,
        scales,
    )

    adjacent_record = producer.q05.copy()
    adjacent_record[19] = values[0]
    assert not _exact_parameter_arrays(
        adjacent_record,
        producer.q95,
        scales,
        producer.q05,
        producer.q95,
        scales,
    )

    threshold_mutation = producer.q05.copy()
    threshold_mutation[19] = np.nextafter(threshold_mutation[19], np.inf)
    assert not _exact_parameter_arrays(
        threshold_mutation,
        producer.q95,
        scales,
        producer.q05,
        producer.q95,
        scales,
    )


def test_training_reviewer_preserves_producer_active_atom_layout() -> None:
    rng = np.random.default_rng(25001)
    for trial in range(99):
        atoms = rng.random((1, 8, 14), dtype=np.float64)
        weights = rng.random(14)
        weights /= weights.sum()
        atoms[:, 1, :] = atoms[:, 0, :]
        atom_index = trial % 14
        atoms[:, 1, atom_index] = np.nextafter(
            atoms[:, 1, atom_index],
            np.inf if trial % 2 else 0.0,
        )

    producer_layout = _active_atom_view(atoms, 14)
    contiguous_slice = atoms[:, :, :14]
    row_weights = np.broadcast_to(weights, (1, 14))
    producer_scores = np.einsum("nkr,nr->nk", producer_layout, row_weights)
    sliced_scores = np.einsum("nkr,nr->nk", contiguous_slice, row_weights)

    assert producer_layout.strides == (64, 8, 64)
    assert contiguous_slice.strides == (896, 112, 8)
    assert int(np.argmin(producer_scores, axis=1)[0]) == 0
    assert int(np.argmin(sliced_scores, axis=1)[0]) == 1


def _valid_solver_report(cuts: np.ndarray) -> dict[str, object]:
    total = int(np.sum(cuts))
    counts = np.sum(cuts, axis=1)
    history = {
        "iteration": 1,
        "master_objective": 0.5,
        "exact_cvar": 0.4,
        "mean_violation": 0.3,
        "max_violation": 0.6,
        "max_master_gap": 8.0e-7,
        "new_cuts": 0,
        "total_cuts": total,
        "solver_status": "optimal",
        "solver_name": "CLARABEL",
    }
    return {
        "iterations": 1,
        "final_master_gap": 8.0e-7,
        "master_learning_curve": [history],
        "total_cuts": total,
        "cuts_per_scene_min_median_max": [
            int(np.min(counts)),
            float(np.median(counts)),
            int(np.max(counts)),
        ],
        "cut_index_sha256": independently_review_array_sha(cuts),
        "solver_status": "optimal",
        "solver_name": "CLARABEL",
    }


def test_training_reviewer_uses_frozen_solver_gap_evidence_contract() -> None:
    cuts = np.zeros((3, 8), dtype=np.bool_)
    cuts[:, 0] = True
    report = _valid_solver_report(cuts)
    assert _solver_evidence_contract(report, cuts, tolerance=1e-6)

    outside_tolerance = json.loads(json.dumps(report))
    outside_tolerance["final_master_gap"] = 1.1e-6
    outside_tolerance["master_learning_curve"][-1]["max_master_gap"] = 1.1e-6
    assert not _solver_evidence_contract(outside_tolerance, cuts, tolerance=1e-6)

    drifted_history = json.loads(json.dumps(report))
    drifted_history["master_learning_curve"][-1]["total_cuts"] += 1
    assert not _solver_evidence_contract(drifted_history, cuts, tolerance=1e-6)

    drifted_cut = cuts.copy()
    drifted_cut[0, 1] = True
    assert not _solver_evidence_contract(report, drifted_cut, tolerance=1e-6)


def test_training_config_freezes_train_only_scale_and_label_rules() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_training_v1.json"
    )
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == FROZEN_CONFIG_SHA256
    config = json.loads(payload)
    audit = config["train_only_atom_audit_contract"]
    labels = audit["causal_policy_distillation"]
    assert audit["scale_quantile"] == 0.95
    assert audit["minimum_positive_candidate_rows"] == 128
    assert audit["minimum_positive_semantic_blocks"] == 20
    assert labels["severity_14d"] == DEFAULT_LABEL_SEVERITY.tolist()
    assert labels["physical_penalty"] == 100.0
    assert labels["margin_multiplier"] == 0.1
    assert labels["margin_clip"] == 2.0
    assert labels["closed_loop_outcome_consumed"] is False
    assert labels["fresh_b2_consumed"] is False


def test_train_suite_uses_same_rows_labels_weights_and_keeps_9d_as_ablation() -> None:
    pytest.importorskip("cvxpy")
    suite = train_v25_selector_suite(
        *_training_inputs(),
        stability_cluster_ids=_clusters(),
        config=V25ParametricMasterConfig(
            alpha=0.5,
            max_iter=4,
            bt_iterations=8,
            bt_max_pairs=256,
            tolerance=1e-6,
        ),
    )
    assert tuple(suite) == tuple(MODEL_REGISTRY)
    for name, model in suite.items():
        report = model.report
        assert report["converged"] is True
        assert report["same_rows_labels_scales_and_block_weights"] is True
        assert report["selection_eligibility"] == "source_valid_candidate_set"
        assert report["physical_feasible_mask_consumed_by_training"] is False
        assert report["v24_rows_consumed_by_main_2x2"] is False
        assert (
            report["v24_without_raw_context_excluded_from_main_fair_comparison"]
            is True
        )
        assert (
            report["static14d_full_v24_augmented_role"]
            == "auxiliary_only_not_primary_method"
        )
        assert report["outcome_or_fresh_consumed"] is False
        assert report["runtime_projection"] is False
        assert report["softmax"] is False
        assert report["theta_column_interpretation_limited_by_redundant_context_lift"] is True
        assert report["leave_one_corridor_stability"]["cluster_count"] == 3
        assert (
            report["leave_one_corridor_stability"]["analysis_kind"]
            == "postfit_cluster_exclusion_descriptive"
        )
        assert report["leave_one_corridor_stability"]["model_refit_performed"] is False
        assert "not leave-cluster-out retraining" in report[
            "leave_one_corridor_stability"
        ]["interpretation"]
        assert report["cluster_ids_used_as_model_features"] is False
        np.testing.assert_allclose(model.theta.sum(axis=0), 1.0, atol=1e-8)
        assert np.all(model.theta >= -1e-9)
        assert np.all(model.result.train_weights >= -1e-9)
        assert model.selected_indices.shape == (5,)
        if name.endswith("14D"):
            assert report["final_primary_method"] is True
            assert report["paper_9d_subset_ablation"] is False
        else:
            assert report["final_primary_method"] is False
            assert report["paper_9d_subset_ablation"] is True
    np.testing.assert_allclose(
        suite["CAMP-Scene14D"].result.train_weights.sum(axis=1),
        np.ones(5),
        rtol=0.0,
        atol=1e-10,
    )


@pytest.mark.parametrize(
    ("position", "replacement", "message"),
    [
        (2, np.ones((5, RAW_FEATURE_COUNT), dtype=np.int64), "native bool"),
        (3, np.zeros(5, dtype=np.float64), "native integers"),
        (5, np.ones((5, 8), dtype=np.int64), "native bool"),
    ],
)
def test_train_suite_rejects_type_smuggling(
    position: int, replacement: np.ndarray, message: str
) -> None:
    values = list(_training_inputs())
    values[position] = replacement
    with pytest.raises(ValueError, match=message):
        train_v25_selector_suite(*values, stability_cluster_ids=_clusters())


def test_train_suite_requires_source_valid_oracle_and_nonempty_source() -> None:
    values = list(_training_inputs())
    values[5] = values[5].copy()
    values[5][0] = False
    with pytest.raises(ValueError, match="nonempty"):
        train_v25_selector_suite(*values, stability_cluster_ids=_clusters())

    values = list(_training_inputs())
    values[5] = values[5].copy()
    values[5][0, 0] = False
    with pytest.raises(ValueError, match="source-valid"):
        train_v25_selector_suite(*values, stability_cluster_ids=_clusters())
