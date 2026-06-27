from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_K = 8
FORBIDDEN_FORMAL_SEEDS = frozenset((11, 12, 13))


@dataclass(frozen=True)
class _Artifacts:
    weights: np.ndarray
    expected_hash: str
    actual_hash: str
    available: bool = True


class _ExplodingArtifacts:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"disabled shadow selector read artifact field {name!r}")


def _sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return hashlib.sha256(array.view(np.uint8)).hexdigest()


def _base_candidates(k: int = EXPECTED_K) -> np.ndarray:
    values = np.arange(k * 3 * 2, dtype=np.float64).reshape(k, 3, 2)
    return values / 10.0


def _base_atoms(k: int = EXPECTED_K) -> np.ndarray:
    atoms = np.full((k, 3), 4.0, dtype=np.float64)
    atoms[:, 0] = np.linspace(1.0, 8.0, k)
    atoms[:, 1] = np.linspace(8.0, 1.0, k)
    atoms[:, 2] = 0.5
    atoms[3] = np.array([0.1, 0.2, 0.3], dtype=np.float64)
    return atoms


def _base_artifacts(weights: np.ndarray | None = None) -> _Artifacts:
    if weights is None:
        weights = np.array([0.5, 0.25, 0.25], dtype=np.float64)
    digest = _sha256_array(weights)
    return _Artifacts(weights=weights, expected_hash=digest, actual_hash=digest)


def _fail_closed(
    candidates: np.ndarray,
    reason: str,
    *,
    candidate_hash_before: str,
) -> dict[str, Any]:
    return {
        "executed_index": 0,
        "executed_trajectory": candidates[0].copy(),
        "shadow_selected_index": None,
        "scores": None,
        "failed_closed_reason": reason,
        "candidate_hash_before": candidate_hash_before,
        "candidate_hash_after": _sha256_array(candidates),
    }


def _shadow_select(
    candidates: np.ndarray,
    normalized_atoms: np.ndarray | None,
    artifacts: _Artifacts | _ExplodingArtifacts,
    *,
    enabled: bool,
    formal_seed: int | None = None,
) -> dict[str, Any]:
    candidate_array = np.asarray(candidates, dtype=np.float64)
    candidate_hash_before = _sha256_array(candidate_array)
    if not enabled:
        return _fail_closed(
            candidate_array,
            "disabled",
            candidate_hash_before=candidate_hash_before,
        )

    if formal_seed in FORBIDDEN_FORMAL_SEEDS:
        return _fail_closed(
            candidate_array,
            "formal_seed_forbidden",
            candidate_hash_before=candidate_hash_before,
        )

    atom_array = np.asarray(normalized_atoms, dtype=np.float64)
    if candidate_array.shape[0] != EXPECTED_K or atom_array.shape[0] != EXPECTED_K:
        return _fail_closed(
            candidate_array,
            "candidate_count_drift",
            candidate_hash_before=candidate_hash_before,
        )
    if not artifacts.available:
        return _fail_closed(
            candidate_array,
            "artifact_missing",
            candidate_hash_before=candidate_hash_before,
        )
    if artifacts.expected_hash != artifacts.actual_hash:
        return _fail_closed(
            candidate_array,
            "artifact_hash_mismatch",
            candidate_hash_before=candidate_hash_before,
        )

    weights = np.asarray(artifacts.weights, dtype=np.float64)
    if weights.shape != (atom_array.shape[1],):
        return _fail_closed(
            candidate_array,
            "weight_dimension_mismatch",
            candidate_hash_before=candidate_hash_before,
        )
    if (
        not np.all(np.isfinite(atom_array))
        or not np.all(np.isfinite(weights))
        or np.any(atom_array < 0.0)
        or np.any(weights < 0.0)
        or not np.isclose(float(weights.sum()), 1.0)
    ):
        return _fail_closed(
            candidate_array,
            "invalid_affine_inputs",
            candidate_hash_before=candidate_hash_before,
        )

    scores = atom_array @ weights
    if not np.all(np.isfinite(scores)):
        return _fail_closed(
            candidate_array,
            "nonfinite_scores",
            candidate_hash_before=candidate_hash_before,
        )
    return {
        "executed_index": 0,
        "executed_trajectory": candidate_array[0].copy(),
        "shadow_selected_index": int(np.argmin(scores)),
        "scores": scores.copy(),
        "failed_closed_reason": None,
        "candidate_hash_before": candidate_hash_before,
        "candidate_hash_after": _sha256_array(candidate_array),
    }


def test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads() -> None:
    candidates = _base_candidates()

    result = _shadow_select(
        candidates,
        normalized_atoms=None,
        artifacts=_ExplodingArtifacts(),
        enabled=False,
    )

    assert result["failed_closed_reason"] == "disabled"
    assert result["executed_index"] == 0
    assert result["shadow_selected_index"] is None
    np.testing.assert_allclose(result["executed_trajectory"], candidates[0])
    assert result["candidate_hash_before"] == result["candidate_hash_after"]


def test_immutable_artifact_hash_contract_fails_closed_on_mismatch() -> None:
    candidates = _base_candidates()
    atoms = _base_atoms()
    artifacts = _base_artifacts()
    mismatched = _Artifacts(
        weights=artifacts.weights,
        expected_hash=artifacts.expected_hash,
        actual_hash="0" * 64,
    )

    result = _shadow_select(candidates, atoms, mismatched, enabled=True)

    assert result["failed_closed_reason"] == "artifact_hash_mismatch"
    assert result["shadow_selected_index"] is None
    np.testing.assert_allclose(result["executed_trajectory"], candidates[0])


def test_fixed_candidate_affine_score_contract_uses_k8_matrix_product() -> None:
    candidates = _base_candidates()
    atoms = _base_atoms()
    artifacts = _base_artifacts()

    result = _shadow_select(candidates, atoms, artifacts, enabled=True)

    expected_scores = atoms @ artifacts.weights
    np.testing.assert_allclose(result["scores"], expected_scores, rtol=0.0, atol=1e-12)
    assert result["shadow_selected_index"] == int(np.argmin(expected_scores))
    assert result["shadow_selected_index"] == 3
    assert result["executed_index"] == 0
    np.testing.assert_allclose(result["executed_trajectory"], candidates[0])


@pytest.mark.parametrize(
    ("candidates", "atoms", "reason"),
    [
        (_base_candidates(7), _base_atoms(7), "candidate_count_drift"),
        (_base_candidates(), np.full((EXPECTED_K, 3), np.inf), "invalid_affine_inputs"),
    ],
)
def test_k_drift_and_nonfinite_scores_fail_closed(
    candidates: np.ndarray,
    atoms: np.ndarray,
    reason: str,
) -> None:
    result = _shadow_select(candidates, atoms, _base_artifacts(), enabled=True)

    assert result["failed_closed_reason"] == reason
    assert result["shadow_selected_index"] is None
    assert result["executed_index"] == 0


def test_dp_top1_shadow_runtime_contract_never_routes_shadow_argmin() -> None:
    candidates = _base_candidates()
    atoms = _base_atoms()

    result = _shadow_select(candidates, atoms, _base_artifacts(), enabled=True)

    assert result["shadow_selected_index"] == 3
    assert result["executed_index"] == 0
    np.testing.assert_allclose(result["executed_trajectory"], candidates[0])
    assert not np.array_equal(candidates[0], candidates[result["shadow_selected_index"]])


def test_no_candidate_mutation_contract_keeps_tensor_hash_and_shape() -> None:
    candidates = _base_candidates()
    original = candidates.copy()

    result = _shadow_select(candidates, _base_atoms(), _base_artifacts(), enabled=True)

    assert result["candidate_hash_before"] == result["candidate_hash_after"]
    assert candidates.shape == (EXPECTED_K, 3, 2)
    np.testing.assert_array_equal(candidates, original)


def test_benders_boundary_keeps_scores_affine_in_simplex_weights() -> None:
    atoms = _base_atoms()
    weight_a = np.array([0.5, 0.25, 0.25], dtype=np.float64)
    weight_b = np.array([0.2, 0.7, 0.1], dtype=np.float64)
    alpha = 0.37
    mixed = alpha * weight_a + (1.0 - alpha) * weight_b

    np.testing.assert_allclose(
        atoms @ mixed,
        alpha * (atoms @ weight_a) + (1.0 - alpha) * (atoms @ weight_b),
        rtol=0.0,
        atol=1e-12,
    )


def test_formal_seed_boundary_rejects_frozen_seeds_without_selection() -> None:
    candidates = _base_candidates()

    for seed in sorted(FORBIDDEN_FORMAL_SEEDS):
        result = _shadow_select(
            candidates,
            _base_atoms(),
            _base_artifacts(),
            enabled=True,
            formal_seed=seed,
        )

        assert result["failed_closed_reason"] == "formal_seed_forbidden"
        assert result["shadow_selected_index"] is None
        np.testing.assert_allclose(result["executed_trajectory"], candidates[0])


def test_current_static_source_surfaces_preserve_rerank_boundary() -> None:
    integration = (
        REPO_ROOT / "camp_core" / "camp_core" / "integrations" / "diffusion_planner.py"
    ).read_text(encoding="utf-8")
    runner = (
        REPO_ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
    ).read_text(encoding="utf-8")
    benders_tests = (
        REPO_ROOT / "camp_core" / "tests" / "test_diffusion_planner_benders_atom_contract.py"
    ).read_text(encoding="utf-8")

    for needle in [
        "class CAMPSelector",
        "scores = normalized @ weights",
        "selected_index = int(np.argmin(selection_scores))",
        "selected_trajectory=candidates[selected_index].copy()",
    ]:
        assert needle in integration

    for needle in [
        "--camp_selector_mode",
        '"top1"',
        "_dp_camp_finite_candidate_contract",
    ]:
        assert needle in runner

    for needle in [
        "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights",
        "test_robust_margin_master_rejects_negative_atom_coefficients",
    ]:
        assert needle in benders_tests
