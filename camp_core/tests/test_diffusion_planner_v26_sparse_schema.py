import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_camp_training_math import (
    estimate_v26_sparse_train_positive_q95_scales,
    paper_bradley_terry_sparse_pool_objective,
)
from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_ATOM_STATUS_VOCABULARY,
    V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES,
    V26_GLOBAL_ATOM_INDEX,
    V26_GLOBAL_ATOM_NAMES,
    V26_TRAINABLE_ATOM_NAMES,
    V26_UNRESOLVED_ATOM_NAMES,
    evaluate_v26_complete_pool_eligibility,
    validate_v26_sparse_pool_artifact,
)


def _artifact(
    observed_names=V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES,
    *,
    city="boston",
    anchor_id="fixture",
    candidate_count=8,
):
    observed_names = tuple(
        name for name in V26_GLOBAL_ATOM_NAMES if name in set(observed_names)
    )
    candidate = np.column_stack(
        [
            np.full(candidate_count, V26_GLOBAL_ATOM_INDEX[name] + 1.0)
            for name in observed_names
        ]
    )
    expert = np.zeros_like(candidate)
    return {
        "identity": {
            "city": city,
            "partition": "train_iid",
            "anchor_id": anchor_id,
            "candidate_pool_sha256": f"pool_{anchor_id}",
        },
        "K": candidate_count,
        "T": 80,
        "dt_seconds": 0.1,
        "candidate0_row": 0,
        "bank_atom_names": list(V26_GLOBAL_ATOM_NAMES),
        "observed_atom_names": list(observed_names),
        "observed_global_atom_indices": [
            V26_GLOBAL_ATOM_INDEX[name] for name in observed_names
        ],
        "candidate_atoms_raw": candidate,
        "expert_atoms_raw": expert,
        "atom_states": [
            {
                "name": name,
                "status": "observed" if name in observed_names else "typed_missing",
            }
            for name in V26_GLOBAL_ATOM_NAMES
        ],
    }


def _global_parameters():
    scales = {name: None for name in V26_GLOBAL_ATOM_NAMES}
    for name in V26_TRAINABLE_ATOM_NAMES:
        scales[name] = float(V26_GLOBAL_ATOM_INDEX[name] + 1)
    weights = {name: 0.0 for name in V26_GLOBAL_ATOM_NAMES}
    for name in V26_TRAINABLE_ATOM_NAMES:
        weights[name] = 1.0 / len(V26_TRAINABLE_ATOM_NAMES)
    return scales, weights


def test_global_bank_status_and_sparse_column_identity_are_frozen() -> None:
    artifact = _artifact()
    validated = validate_v26_sparse_pool_artifact(artifact)

    assert len(V26_GLOBAL_ATOM_NAMES) == 15
    assert V26_ATOM_STATUS_VOCABULARY == (
        "observed",
        "not_applicable",
        "typed_missing",
    )
    assert validated["candidate_atoms_raw"].shape == (8, 7)
    assert validated["observed_global_atom_indices"] == (0, 9, 10, 11, 12, 13, 14)

    misbound = copy.deepcopy(artifact)
    misbound["observed_global_atom_indices"][0] = 3
    with pytest.raises(ValueError, match="one-to-one"):
        validate_v26_sparse_pool_artifact(misbound)


def test_k16_sparse_schema_and_pairwise_bt_retain_all_rows() -> None:
    artifact = _artifact(candidate_count=16)
    validated = validate_v26_sparse_pool_artifact(artifact)
    scales, weights = _global_parameters()

    objective = paper_bradley_terry_sparse_pool_objective(
        artifact,
        expert_future_brackets_8s=True,
        global_atom_scales=scales,
        global_nonnegative_weights=weights,
    )

    assert validated["candidate_atoms_raw"].shape == (16, 7)
    assert objective["pairwise_logits"].shape == (16,)


def test_complete_pool_requires_only_identity_expert_s1_and_comfort() -> None:
    artifact = _artifact()
    eligibility = evaluate_v26_complete_pool_eligibility(
        artifact, expert_future_brackets_8s=True
    )

    assert eligibility["eligible"] is True
    assert eligibility["unresolved_atoms_are_eligibility_gates"] is False
    assert eligibility["endpoint_local_authoritative_atom_states"] == {
        "ttc_deficit_0_95s": "typed_missing",
        "dynamic_clearance_buffer_deficit": "typed_missing",
        "overspeed_integral_m2_per_s": "typed_missing",
        "full_footprint_road_exit_severity_s": "typed_missing",
        "reverse_progress_severity_m": "typed_missing",
        "red_light_crossing_exposure_fraction": "typed_missing",
        "red_stopping_margin_m2_s": "typed_missing",
        "route_progress_shortfall_m": "typed_missing",
    }

    no_s1 = _artifact(V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES[1:])
    rejected = evaluate_v26_complete_pool_eligibility(
        no_s1, expert_future_brackets_8s=True
    )
    assert rejected["eligible"] is False
    assert "predicted_obb_collision_exposure_fraction" in rejected["reasons"][0]


def test_sparse_bt_gathers_global_names_without_zero_fill_or_local_renormalization() -> None:
    artifact = _artifact()
    scales, weights = _global_parameters()
    result = paper_bradley_terry_sparse_pool_objective(
        artifact,
        expert_future_brackets_8s=True,
        global_atom_scales=scales,
        global_nonnegative_weights=weights,
    )

    assert result["active_atom_names"] == list(V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES)
    assert result["active_global_atom_indices"] == [0, 9, 10, 11, 12, 13, 14]
    assert result["candidate_atoms_raw"].shape == (8, 7)
    assert result["active_weight_mass"] == pytest.approx(7.0 / 15.0)
    assert result["global_trainable_weight_mass"] == pytest.approx(1.0)
    assert result["weight_policy"] == (
        "global_weights_gathered_without_pool_local_renormalization"
    )
    np.testing.assert_allclose(result["pairwise_logits"], -7.0 / 15.0)

    tied = copy.deepcopy(artifact)
    tied["expert_atoms_raw"] = np.asarray(tied["candidate_atoms_raw"]).copy()
    tied_result = paper_bradley_terry_sparse_pool_objective(
        tied,
        expert_future_brackets_8s=True,
        global_atom_scales=scales,
        global_nonnegative_weights=weights,
    )
    np.testing.assert_array_equal(tied_result["pairwise_logits"], 0.0)


def test_sparse_q95_aggregates_by_global_name_and_preserves_unidentified_rows() -> None:
    first = _artifact(
        (*V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES, "overspeed_integral_m2_per_s"),
        anchor_id="first",
    )
    second = _artifact(anchor_id="second", city="pittsburgh")
    result = estimate_v26_sparse_train_positive_q95_scales(
        (first, second),
        (True, True),
        np.ones(2, dtype=np.float64),
    )
    rows = {row["atom_name"]: row for row in result["atom_rows"]}

    assert [row["atom_name"] for row in result["atom_rows"]] == list(
        V26_GLOBAL_ATOM_NAMES
    )
    assert rows["overspeed_integral_m2_per_s"]["observed_pool_count"] == 1
    assert rows["overspeed_integral_m2_per_s"]["positive_q95"] == 4.0
    assert rows["full_footprint_road_exit_severity_s"]["status"] == (
        "scale_unidentified"
    )
    for name in V26_UNRESOLVED_ATOM_NAMES:
        assert rows[name]["status"] == "unresolved_excluded_from_training_score"
        assert rows[name]["positive_q95"] is None


def test_sparse_bt_omits_observed_scale_unidentified_columns_without_zero_fill() -> None:
    artifact = _artifact()
    scales = {name: 1.0 for name in V26_GLOBAL_ATOM_NAMES}
    weights = {name: 0.0 for name in V26_GLOBAL_ATOM_NAMES}
    unidentified = V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES[-1]
    scales[unidentified] = None
    active = [name for name in V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES if name != unidentified]
    for name in active:
        weights[name] = 1.0 / len(active)

    result = paper_bradley_terry_sparse_pool_objective(
        artifact,
        expert_future_brackets_8s=True,
        global_atom_scales=scales,
        global_nonnegative_weights=weights,
    )

    assert unidentified not in result["active_atom_names"]
    assert result["observed_scale_unidentified_atoms"] == [unidentified]
    assert result["candidate_atoms_raw"].shape == (8, len(active))


def test_repaired_atom_enters_global_training_parameters_only_when_observed() -> None:
    artifact = _artifact((*V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES, "ttc_deficit_0_95s"))
    scales, weights = _global_parameters()
    result = paper_bradley_terry_sparse_pool_objective(
        artifact,
        expert_future_brackets_8s=True,
        global_atom_scales=scales,
        global_nonnegative_weights=weights,
    )
    assert "ttc_deficit_0_95s" in result["active_atom_names"]
    assert result["active_global_atom_indices"] == [0, 1, 9, 10, 11, 12, 13, 14]
