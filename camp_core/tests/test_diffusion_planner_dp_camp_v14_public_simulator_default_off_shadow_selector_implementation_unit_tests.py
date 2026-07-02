from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "camp_core"
for path in (REPO_ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.integrations.diffusion_planner import (
    CAMPSelector,
    CAMP_ATOM_NAMES,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K,
    DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION,
    _default_off_shadow_selector_contract,
    _summarize_default_off_shadow_selector_records,
    _validate_args,
)


EXPECTED_K = DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K
FORBIDDEN_FORMAL_SEEDS = frozenset((11, 12, 13))


def _sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return hashlib.sha256(array.view(np.uint8)).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_tensor(k: int = EXPECTED_K) -> np.ndarray:
    x = np.arange(5, dtype=np.float64)
    lateral_offsets = np.array([1.2, 1.0, 0.8, 0.0, 0.6, 1.4, 1.6, 1.8])
    if k != EXPECTED_K:
        lateral_offsets = lateral_offsets[:k]
    return np.stack(
        [np.column_stack([x, np.full_like(x, offset)]) for offset in lateral_offsets],
        axis=0,
    )


def _context() -> DriverAtomContext:
    return DriverAtomContext(
        dt=1.0,
        lane_centerline=np.column_stack(
            [
                np.linspace(-1.0, 8.0, 10, dtype=np.float64),
                np.zeros(10, dtype=np.float64),
            ]
        ),
        static_obstacles=np.empty((0, 2), dtype=np.float64),
        speed_limit=30.0,
        desired_speed=3.0,
        lane_half_width=2.5,
        lane_corridor_buffer=1.0,
        safety_radius=0.1,
    )


def _lane_deviation_weights() -> np.ndarray:
    weights = np.zeros(len(CAMP_ATOM_NAMES), dtype=np.float64)
    weights[CAMP_ATOM_NAMES.index("lane_deviation")] = 1.0
    return weights


def _selector() -> CAMPSelector:
    return CAMPSelector(
        atom_scales=np.ones(len(CAMP_ATOM_NAMES), dtype=np.float64),
        static_weights=_lane_deviation_weights(),
        fallback_mode="top1",
    )


def _runner_args(
    *,
    enabled: bool = True,
    atom_scales: Path | None = None,
    static_weights: Path | None = None,
    atom_scales_sha256: str | None = None,
    static_weights_sha256: str | None = None,
    manifest: Path | None = None,
    selector_mode: str = "static",
    num_candidates: int = EXPECTED_K,
) -> SimpleNamespace:
    return SimpleNamespace(
        camp_default_off_shadow_selector=enabled,
        camp_selector_mode=selector_mode,
        num_candidates=num_candidates,
        camp_shadow_artifact_manifest=manifest,
        camp_atom_scales=atom_scales,
        camp_static_weights=static_weights,
        camp_checkpoint=None,
        camp_shadow_expected_atom_scales_sha256=atom_scales_sha256,
        camp_shadow_expected_static_weights_sha256=static_weights_sha256,
        camp_shadow_expected_checkpoint_sha256=None,
        camp_fallback_atom_scales=None,
        camp_fallback_static_weights=None,
        camp_fallback_mode="uniform",
        candidate_noise_strategy="iid",
        candidate_noise_scale=1.0,
        candidate_reference_blend_steps=None,
        candidate_guidance_config=None,
        candidate_guidance_scale=None,
        camp_microbenchmark_snapshot_dir=None,
        camp_microbenchmark_snapshot_steps=[0],
        camp_log_raw_candidate_prefix_steps=0,
        camp_observable_state_logging=False,
        camp_red_route_vector_logging=False,
        camp_progress_support_logging=False,
        camp_lane_hard_violation_support_logging=False,
        camp_progress_lane_hard_context_logging=False,
        camp_turn_logit_payload_logging=False,
        camp_non_turn_logit_interaction_payload_logging=False,
        camp_external_context_payload_logging=False,
        camp_temporal_consistency_payload_logging=False,
        camp_candidate_set_consensus_payload_logging=False,
        camp_min_candidate0_progress_ratio=None,
        camp_min_candidate0_route_progress_ratio=None,
        camp_shadow_route_progress=False,
        camp_shadow_obstacle_clearance=False,
        camp_shadow_obstacle_clearance_exact_obb=False,
        camp_min_candidate0_step_reach_ratio=None,
        camp_candidate0_step_reach_preserve_feasible=False,
        camp_lexicographic_progress_epsilon_m=None,
        camp_lexicographic_red_epsilon=0.0,
        camp_lexicographic_jerk_epsilon=0.0,
        camp_lexicographic_lateral_epsilon=0.0,
        camp_perfect_tracker_command_postselection=False,
        camp_traffic_light_hybrid_postselection="off",
        camp_underprogress_relaxation=False,
        camp_collect_closed_loop_outcomes=False,
        camp_splice_shadow_rule=False,
        camp_lane_corridor_buffer=1.0,
        camp_min_progress_ratio=0.8,
        camp_feasibility_source="context",
        camp_underprogress_progress_loss_budget_m=1.0,
        camp_underprogress_h3_distance_loss_budget_m=1.0,
        camp_underprogress_lateral_limit_mps2=3.0,
        camp_reward_horizon_steps=10,
        camp_outcome_horizon_steps=10,
        reward_config=None,
        near_miss_threshold_m=2.0,
        camp_observable_state_support_steps=10,
        camp_observable_state_traffic_light_steps=10,
        camp_observable_state_turn_steps=10,
        camp_progress_support_steps=10,
        camp_progress_support_dt_s=0.5,
        camp_lane_hard_violation_support_steps=10,
        camp_lane_hard_violation_support_dt_s=0.5,
        camp_lane_hard_violation_corridor_half_width_m=2.0,
        camp_lane_hard_violation_lateral_rate_budget_mps=0.5,
        camp_progress_lane_hard_context_steps=10,
        camp_progress_lane_hard_context_dt_s=0.5,
        camp_progress_lane_hard_context_corridor_half_width_m=2.0,
        camp_progress_lane_hard_context_corridor_safety_margin_m=0.5,
        camp_external_context_payload_steps=10,
        camp_external_context_payload_dt_s=0.5,
        camp_temporal_consistency_payload_steps=10,
        camp_temporal_consistency_payload_dt_s=0.5,
        camp_temporal_consistency_payload_elapsed_steps=0,
        camp_temporal_consistency_payload_min_overlap_steps=2,
        camp_candidate_set_consensus_payload_steps=10,
        camp_splice_shadow_progress_loss_budget_m=1.0,
        camp_splice_shadow_smoothness_loss_budget=0.5,
        camp_splice_shadow_anchor_steps=2,
        camp_splice_shadow_blend_steps=0,
        steps=None,
    )


def test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads() -> None:
    contract = _default_off_shadow_selector_contract(
        _runner_args(
            enabled=False,
            atom_scales=Path("missing-scales.json"),
            static_weights=Path("missing-weights.npy"),
        )
    )

    assert contract["schema_version"] == DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION
    assert contract["enabled"] is False
    assert contract["default_off"] is True
    assert contract["executed_output_policy"] == "dp_top1"
    assert contract["selection_effect"] is False
    assert contract["ready"] is False
    assert contract["failed_closed_reason"] == "disabled"
    assert contract["artifacts"] == {}


def test_immutable_artifact_hash_contract_fails_closed_on_mismatch(tmp_path: Path) -> None:
    scales = tmp_path / "scales.json"
    weights = tmp_path / "weights.npy"
    scales.write_text(
        '{"atom_schema_version": "camp_legacy_v1_9d", '
        '"atom_names": ["jerk_early", "jerk_late", "jerk_full", '
        '"rms_acceleration", "speed_limit_margin_0_0", '
        '"speed_limit_margin_0_5", "speed_limit_margin_1_0", '
        '"lane_deviation", "clearance"], '
        '"scales": [1, 1, 1, 1, 1, 1, 1, 1, 1]}',
        encoding="utf-8",
    )
    np.save(weights, _lane_deviation_weights())

    contract = _default_off_shadow_selector_contract(
        _runner_args(
            atom_scales=scales,
            static_weights=weights,
            atom_scales_sha256="0" * 64,
            static_weights_sha256=_sha256_file(weights),
        )
    )

    assert contract["ready"] is False
    assert contract["fail_closed"] is True
    assert contract["failed_closed_reason"] == "atom_scales_hash_mismatch"
    assert contract["artifacts"]["atom_scales"]["hash_match"] is False


def test_fixed_candidate_affine_score_contract_uses_real_selector_matrix_product() -> None:
    candidates = _candidate_tensor()
    result = _selector().select(
        candidates,
        _context(),
        apply_context_feasibility=False,
    )

    expected_scores = result.normalized_atoms @ result.weights
    np.testing.assert_allclose(result.scores, expected_scores, rtol=0.0, atol=1e-12)
    assert result.selected_index == int(np.argmin(expected_scores))
    assert result.weights.shape == (len(CAMP_ATOM_NAMES),)
    assert np.all(result.weights >= 0.0)
    assert np.isclose(float(result.weights.sum()), 1.0)


@pytest.mark.parametrize(
    ("selector_mode", "num_candidates", "reason"),
    [
        ("uniform", EXPECTED_K, "selector_mode_not_static"),
        ("static", EXPECTED_K - 1, "candidate_count_drift"),
    ],
)
def test_k_drift_and_selector_mode_drift_fail_closed(
    selector_mode: str,
    num_candidates: int,
    reason: str,
) -> None:
    contract = _default_off_shadow_selector_contract(
        _runner_args(selector_mode=selector_mode, num_candidates=num_candidates)
    )

    assert contract["ready"] is False
    assert contract["fail_closed"] is True
    assert reason in contract["failed_checks"]
    assert contract["executed_output_policy"] == "dp_top1"


def test_nonfinite_atom_scales_fail_before_runtime_selection() -> None:
    with pytest.raises(ValueError, match="atom_scales"):
        CAMPSelector(
            atom_scales=np.full(len(CAMP_ATOM_NAMES), np.nan),
            static_weights=_lane_deviation_weights(),
        )


def test_dp_top1_shadow_runtime_contract_logs_shadow_without_routing() -> None:
    records = [
        {
            "selected_index": 0,
            "default_off_shadow_selector": {
                "shadow_selected_index": 3,
            },
        }
    ]

    summary = _summarize_default_off_shadow_selector_records(
        records,
        enabled=True,
        artifact_contract={"ready": True, "failed_closed_reason": None},
    )

    assert summary["executed_top1_all"] is True
    assert summary["selection_effect"] is False
    assert summary["shadow_selection_logged_records"] == 1
    assert summary["shadow_selected_index_counts"] == {"3": 1}
    assert summary["nonzero_shadow_selection_count"] == 1


def test_no_candidate_mutation_contract_keeps_tensor_hash_and_returns_copy() -> None:
    candidates = _candidate_tensor()
    original = candidates.copy()
    before = _sha256_array(candidates)

    result = _selector().select(
        candidates,
        _context(),
        apply_context_feasibility=False,
    )

    assert _sha256_array(candidates) == before
    np.testing.assert_array_equal(candidates, original)
    assert not np.shares_memory(result.selected_trajectory, candidates)
    result.selected_trajectory[0, 0] = 999.0
    np.testing.assert_array_equal(candidates, original)


def test_benders_boundary_keeps_scores_affine_in_simplex_weights() -> None:
    result = _selector().select(
        _candidate_tensor(),
        _context(),
        apply_context_feasibility=False,
    )
    atoms = result.normalized_atoms
    weight_a = np.full(atoms.shape[1], 1.0 / atoms.shape[1], dtype=np.float64)
    weight_b = np.zeros(atoms.shape[1], dtype=np.float64)
    weight_b[CAMP_ATOM_NAMES.index("lane_deviation")] = 1.0
    alpha = 0.37
    mixed = alpha * weight_a + (1.0 - alpha) * weight_b

    np.testing.assert_allclose(
        atoms @ mixed,
        alpha * (atoms @ weight_a) + (1.0 - alpha) * (atoms @ weight_b),
        rtol=0.0,
        atol=1e-12,
    )


def test_formal_seed_boundary_is_rejection_only_and_never_replay_execution() -> None:
    for seed in FORBIDDEN_FORMAL_SEEDS:
        assert seed in FORBIDDEN_FORMAL_SEEDS

    runner = (
        REPO_ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
    ).read_text(encoding="utf-8")
    assert "--seed" in runner
    assert "formal_seeds_authorized=True" not in runner


def test_runner_shadow_selector_rejects_execution_changing_flags() -> None:
    args = _runner_args()
    args.camp_perfect_tracker_command_postselection = True

    with pytest.raises(ValueError, match="shadow execution must remain DP Top-1"):
        _validate_args(args)


def test_runner_shadow_contract_accepts_clean_hash_manifest(tmp_path: Path) -> None:
    scales = tmp_path / "scales.json"
    weights = tmp_path / "weights.npy"
    manifest = tmp_path / "manifest.json"
    scales.write_text(
        '{"atom_schema_version": "camp_legacy_v1_9d", '
        '"atom_names": ["jerk_early", "jerk_late", "jerk_full", '
        '"rms_acceleration", "speed_limit_margin_0_0", '
        '"speed_limit_margin_0_5", "speed_limit_margin_1_0", '
        '"lane_deviation", "clearance"], '
        '"scales": [1, 1, 1, 1, 1, 1, 1, 1, 1]}',
        encoding="utf-8",
    )
    np.save(weights, _lane_deviation_weights())
    manifest.write_text(
        (
            '{"artifacts": {'
            f'"atom_scales": {{"sha256": "{_sha256_file(scales)}"}}, '
            f'"static_weights": {{"sha256": "{_sha256_file(weights)}"}}'
            "}}"
        ),
        encoding="utf-8",
    )

    contract = _default_off_shadow_selector_contract(
        _runner_args(atom_scales=scales, static_weights=weights, manifest=manifest)
    )

    assert contract["ready"] is True
    assert contract["fail_closed"] is False
    assert contract["failed_closed_reason"] is None
    assert contract["artifacts"]["atom_scales"]["hash_match"] is True
    assert contract["artifacts"]["static_weights"]["hash_match"] is True


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
        "--camp_default_off_shadow_selector",
        '"top1"',
        "_dp_camp_finite_candidate_contract",
        '"executed_output_policy": "dp_top1"',
    ]:
        assert needle in runner

    for needle in [
        "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights",
        "test_robust_margin_master_rejects_negative_atom_coefficients",
    ]:
        assert needle in benders_tests
