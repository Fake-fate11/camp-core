from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_COUNT
from camp_core.integrations.diffusion_planner_v25_training import (
    MODEL_REGISTRY,
    train_v25_selector_suite,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    DEFAULT_LABEL_SEVERITY,
)
from camp_core.outer_master.parametric_cvxpy_master import V25ParametricMasterConfig


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
        assert np.all(model.theta >= 0.0)
        assert np.all(model.result.train_weights >= 0.0)
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
