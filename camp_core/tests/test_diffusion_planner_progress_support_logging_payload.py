from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_progress_support_logging_payload,
)


ROOT = Path(__file__).resolve().parents[2]
REPLAY_SCRIPT = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [5.0, 0.0],
            [10.0, 0.0],
        ],
        dtype=np.float64,
    )


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [4.0, 0.0]],
            [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0], [1.5, 0.0], [2.0, 0.0]],
            [[0.0, 0.0], [1.0, 0.0], [0.5, 0.0], [1.5, 0.0], [1.0, 0.0]],
        ],
        dtype=np.float64,
    )


def test_progress_support_payload_schema_shapes_and_metadata() -> None:
    payload = build_progress_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        dt_s=0.1,
    )

    assert payload["schema_version"] == PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["classical_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]
    assert payload["candidate_count"] == 3
    assert payload["horizons"] == {"support_steps": 5, "dt_s": 0.1}
    assert set(payload["field_shapes"]) == set(PROGRESS_SUPPORT_FIELD_NAMES)
    assert payload["field_shapes"]["candidate_route_progress_s_profile_m"] == [3, 5]
    assert payload["field_shapes"]["candidate_plan_arc_length_profile_m"] == [3, 5]
    assert payload["field_shapes"]["candidate_speed_profile_mps"] == [3, 4]
    assert payload["field_shapes"]["candidate_route_remaining_m"] == [3]
    assert payload["field_shapes"]["candidate_goal_alignment_progress_m"] == [3]
    assert all(payload["finite_checks"].values())
    assert payload["progress_support_atom_names"] == list(PROGRESS_SUPPORT_ATOM_NAMES)
    assert np.asarray(payload["progress_support_atoms"]).shape == (
        3,
        len(PROGRESS_SUPPORT_ATOM_NAMES),
    )


def test_progress_support_atoms_are_nonnegative_fixed_candidate_coefficients() -> None:
    payload = build_progress_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        dt_s=0.1,
    )
    atoms = np.asarray(payload["progress_support_atoms"], dtype=np.float64)
    atom_index = {
        name: idx for idx, name in enumerate(payload["progress_support_atom_names"])
    }

    assert np.all(atoms >= 0.0)
    np.testing.assert_allclose(atoms[0], np.zeros(atoms.shape[1]))
    assert atoms[1, atom_index["route_progress_deficit_envelope_v1"]] > 0.0
    assert atoms[1, atom_index["plan_arc_support_deficit_v1"]] > 0.0
    assert atoms[1, atom_index["tail_speed_support_deficit_v1"]] > 0.0
    assert atoms[1, atom_index["route_remaining_excess_vs_top1_v1"]] > 0.0
    assert atoms[1, atom_index["goal_alignment_progress_deficit_v1"]] > 0.0
    assert atoms[1, atom_index["low_speed_progress_conflict_v1"]] > 0.0
    assert atoms[2, atom_index["route_progress_regression_envelope_v1"]] > 0.0


def test_progress_support_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_progress_support_logging_payload)

    assert list(signature.parameters) == [
        "candidates",
        "route_centerline_ego",
        "support_steps",
        "dt_s",
    ]
    assert "outcome" not in str(signature).lower()


def test_progress_support_payload_validates_inputs() -> None:
    with pytest.raises(ValueError, match="candidates must have shape"):
        build_progress_support_logging_payload(
            candidates=np.zeros((5, 2), dtype=np.float64),
            route_centerline_ego=_route(),
            support_steps=5,
        )
    with pytest.raises(ValueError, match="route_centerline_ego"):
        build_progress_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=np.zeros((1, 2), dtype=np.float64),
            support_steps=5,
        )
    with pytest.raises(ValueError, match="dt_s"):
        build_progress_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=5,
            dt_s=0.0,
        )


def test_replay_wiring_is_default_off_and_selection_neutral() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_progress_support_logging" in source
    assert "action=\"store_true\"" in source
    assert "\"progress_support_logging\": progress_support_logging_payload" in source
    assert "\"selection_effect\": False" in source
    assert "\"future_outcome_leakage\": False" in source
    assert "\"closed_loop_outcome_fields_read\": False" in source
    assert "\"camp_progress_support_logging\"" in source
    assert "build_progress_support_logging_payload(" in source
