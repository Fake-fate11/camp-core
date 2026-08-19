import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_ATOM_STATUS_VOCABULARY,
    V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES,
    V26_GLOBAL_ATOM_INDEX,
    V26_GLOBAL_ATOM_NAMES,
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
