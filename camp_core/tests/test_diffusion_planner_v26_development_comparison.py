from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "camp_core") not in sys.path:
    sys.path.insert(0, str(ROOT / "camp_core"))

from camp_core.integrations import (  # noqa: E402
    diffusion_planner_v26_development_comparison as comparison,
)
from camp_core.integrations import (  # noqa: E402
    diffusion_planner_v26_development_comparison_inventory as inventory,
)
from camp_core.integrations import diffusion_planner_v26_integration_boundary as boundary  # noqa: E402
from camp_core.integrations.diffusion_planner_v26_native_runner import (  # noqa: E402
    _validate_selector_runtime_contract,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _write_adaptation_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "adaptation"
    root.mkdir()
    theta = np.full((14, 53), 1.0 / 14.0, dtype=np.float64)
    scales = np.ones(14, dtype=np.float64)
    parameters = root / "adapted_selector_parameters.npz"
    np.savez_compressed(
        parameters,
        schema_version=np.asarray(boundary.V26_ADAPTED_WEIGHTS_SCHEMA_VERSION),
        context_feature_names=np.asarray(
            [
                "ego_speed_mps", "ego_longitudinal_acceleration_mps2", "ego_lateral_acceleration_mps2",
                "ego_yaw_rate_radps", "route_curvature_mean_abs_radpm", "route_curvature_max_abs_radpm",
                "route_lane_width_min_m", "route_lane_width_p50_m", "route_speed_limit_min_mps",
                "route_speed_limit_current_mps", "traffic_phase_red", "traffic_phase_yellow",
                "traffic_phase_green", "traffic_phase_unknown", "traffic_signal_distance_m",
                "traffic_signal_phase_remaining_s", "neighbor_count", "neighbor_min_distance_m",
                "neighbor_min_ttc_s", "neighbor_closing_speed_mps", "neighbor_lateral_gap_min_m",
                "candidate_consensus_rms_median_m", "candidate_consensus_rms_mad_m",
                "candidate_endpoint_xy_std_m", "candidate_progress_std_m", "candidate_source_valid_fraction",
            ]
        ),
        context_q05=np.zeros(26, dtype=np.float64),
        context_q95=np.ones(26, dtype=np.float64),
        training_scales_14d=scales,
        static14d_theta=theta,
        scene14d_theta=theta,
        static14d_runtime_weights=theta[:, 0],
    )
    static = root / "adapted_static14d_runtime_weights.npy"
    np.save(static, theta[:, 0])
    reports = root / "adapted_model_reports.json"
    report_value = {
        name: {
            "mode": mode,
            "active_atom_indices": list(range(14)),
            "theta_sha256": comparison._theta_sha256(theta),
            "outcome_or_fresh_consumed": False,
        }
        for name, mode in (("CAMP-Static14D", "static"), ("CAMP-Scene14D", "scene"))
    }
    reports.write_text(json.dumps(report_value), encoding="utf-8")
    scale_path = root / "adapted_runtime_atom_scales.json"
    scale_path.write_text(
        json.dumps(
            {
                "schema_version": "camp_dp_v26_adapted_runtime_atom_scales_v1",
                "atom_count": 14,
                "scales": scales.tolist(),
                "scale_source": "reviewed_training_only_saved_pools",
                "outcome_or_fresh_consumed": False,
            }
        ),
        encoding="utf-8",
    )

    def binding(path: Path) -> dict[str, str]:
        return {
            "relative_path": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    receipt = {
        "schema_version": "camp_dp_v26_selector_adaptation_receipt_v1",
        "evidence_role": "development_train_only_selector_adaptation",
        "terminal": {"status": "complete"},
        "weight_roles": {
            "reference": boundary.V25_ZERO_SHOT_REFERENCE_READ_ONLY,
            "adapted": boundary.V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
        },
        "manifest": {
            "adaptation_scope": "camp_selector_adaptation_layer_only",
            "frozen_dp": {"head": inventory.FROZEN_FIXED_DP_HEAD},
            "training_label_contract": "causal_policy_distillation_no_outcome",
            "reference": {"compatibility_role": boundary.V25_ZERO_SHOT_REFERENCE_READ_ONLY},
        },
        "adapted_assets": {
            "parameters": binding(parameters),
            "model_reports": binding(reports),
            "runtime_atom_scales": binding(scale_path),
            "static14d_runtime_weights": binding(static),
        },
    }
    receipt_path = root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt_path


def _comparison_inventory(assets: comparison.V26AdaptedSelectorAssets) -> dict[str, object]:
    candidates = []
    for index in range(3):
        candidates.append(
            {
                "schema_version": inventory.SOURCE_CANDIDATE_SCHEMA_VERSION,
                "family_id": "family-a",
                "route_id": f"route-{index}",
                "route_identity_sha256": _sha(10 + index),
                "provisional_corridor_id": _sha(20 + index),
                "physical_route_identity_sha256": _sha(30 + index),
                "source_map_sha256": _sha(40),
                "derived_geometry_sha256": _sha(50 + index),
                "source_artifact_sha256": _sha(60),
                "source_projection_sha256": _sha(70),
                "source_inventory_sha256": _sha(80),
                "source_event_identity_sha256": _sha(90),
                "event_manifest_sha256": _sha(100),
                "risk_stratum_sha256": _sha(110),
                "geometry_stratum": "short_le_100m",
                "source_stratum": {
                    "traffic_light": False,
                    "branch_intersection": False,
                    "tight_corridor": True,
                    "short_progress_opportunity": True,
                },
                "route_lanelet_ids": [1000 + index],
                "boundary_ids": [2000 + index],
                "minimum_source_corridor_width_m": 4.0,
                "source_arc_length_m": 80.0,
                "route_length_m": 90.0,
                "route_spec": {
                    "map_path": "/maps/source.osm",
                    "lanelet_ids": [1000 + index],
                    "start_pose": [float(index) * 100.0, 0.0, 0.0],
                    "goal_pose": [float(index) * 100.0 + 90.0, 0.0, 0.0],
                    "route_length_m": 90.0,
                },
                "identity_only_route_sha256": _sha(120 + index),
                "signal_authority_mode": boundary.V26_CERTIFIED_NO_SIGNAL_MODE,
                "signal_adapter_id": boundary.V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
                "eligibility": {
                    "schema_version": inventory.ELIGIBILITY_SCHEMA_VERSION,
                    "status": "passed_v26_native_source_preflight",
                    "failure_class": None,
                    "failure_reason": None,
                    "exact_route_connectivity": True,
                    "source_signal_adapter_bound": True,
                    "model_dp_gpu_latent_candidate_calls": inventory._zero_calls(),
                },
                "_centerline_samples_m": [[float(index) * 100.0, 0.0], [float(index) * 100.0 + 90.0, 0.0]],
                "_centerline_headings_rad": [0.0, 0.0],
            }
        )
    source = {
        "zero_model_calls": inventory._zero_calls(),
        "training_identities": [
            {
                "route_id": "training-route",
                "corridor_id": "training-corridor",
                "source_map_sha256": _sha(41),
                "derived_geometry_sha256": _sha(51),
                "source_event_identity_sha256": _sha(91),
                "physical_route_identity_sha256": _sha(31),
            }
        ],
        "candidates": candidates,
        "families": [{"family_id": "family-a"}],
    }
    adapted = {
        "artifact_role": boundary.V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
        "adaptation_receipt_sha256": assets.adaptation_receipt_sha256,
        "assets": json.loads(assets.receipt_path.read_text(encoding="utf-8"))["adapted_assets"],
    }
    return inventory.build_development_comparison_inventory(
        source_collection=source,
        camp_head="a" * 40,
        fixed_dp_checkpoint={"path": "/fixed/checkpoint", "sha256": _sha(200)},
        adapted_selector=adapted,
        reference_selector={"artifact_role": boundary.V25_ZERO_SHOT_REFERENCE_READ_ONLY},
        final_training_population_sha256=_sha(201),
        revision_plan_sha256=_sha(202),
    )


def _base_probe() -> dict[str, object]:
    return {
        "source_path": "/config/base.json",
        "source_sha256": _sha(300),
        "fixed_dp": {
            "head": inventory.FROZEN_FIXED_DP_HEAD,
            "checkpoint": {"path": "/fixed/checkpoint", "sha256": _sha(200)},
            "args_json": {"path": "/fixed/args.json", "sha256": _sha(301)},
            "native_source_sha256": {"replay.py": _sha(302)},
        },
        "spawn_config": {"seed": 1},
        "seed_template": {"scenario": 1},
    }


def test_adapted_assets_bind_b32_schema_and_scene_runtime_without_v25_high_level_consumer(
    tmp_path: Path,
) -> None:
    assets = comparison.load_v26_adapted_selector_assets(_write_adaptation_fixture(tmp_path))
    assert assets.static14d_weights.shape == (14,)
    scene = assets.scene14d_weights(
        {
            "schema_version": "camp_dp_v25_causal_context_raw_v2",
            "raw_context": {
                name: 0.5 for name in comparison.RAW_FEATURE_NAMES
            },
            "source_complete": {name: True for name in comparison.RAW_FEATURE_NAMES},
            "source_receipt": {},
        }
    )
    assert len(scene["weights"]) == 14
    assert scene["runtime_projection"] is False
    source = Path(comparison.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("v25_industrial", "v25_fair", "summarize_run_v2"):
        assert forbidden not in source


def test_manifest_freezes_three_arms_per_cluster_and_exact_b32_identity(tmp_path: Path) -> None:
    assets = comparison.load_v26_adapted_selector_assets(_write_adaptation_fixture(tmp_path))
    manifest = comparison.build_development_comparison_manifest(
        inventory=_comparison_inventory(assets),
        inventory_file_sha256=_sha(400),
        camp_head="a" * 40,
        base_probe=_base_probe(),
        adapted_assets=assets,
    )
    assert manifest["denominator"] == {
        "planned_clusters": 2,
        "planned_arm_units": 6,
        "complete_arm_units": 0,
        "typed_failure_arm_units": 0,
        "unattempted_arm_units": 6,
    }
    assert manifest["execution_topology"]["cross_arm_pool_equality_claim"] is False
    assert [row["arm_id"] for row in manifest["unit_plan"][:3]] == list(comparison.COMPARISON_ARMS)
    assert len({row["planned_state_id_sha256"] for row in manifest["unit_plan"]}) == 6
    assert manifest["adapted_selector"]["adaptation_receipt_sha256"] == assets.adaptation_receipt_sha256


def test_native_selector_subsets_and_runtime_unit_enforce_b8_row0_and_postpool_zero() -> None:
    assert _validate_selector_runtime_contract(
        selector_arms=("pool_matched_candidate0", "Static14D"), operational_arm="Static14D"
    ) == ("pool_matched_candidate0", "Static14D")
    with pytest.raises(ValueError, match="selector-arm contract"):
        _validate_selector_runtime_contract(
            selector_arms=("Static14D",), operational_arm="Static14D"
        )
    runner = __import__("scripts.integrations.run_diffusion_planner_v26_development_comparison", fromlist=["x"])
    rows = [_sha(500 + index) for index in range(8)]
    unit = {
        "unit_index": 0,
        "cluster_index": 0,
        "cluster_id_sha256": _sha(600),
        "planned_state_id_sha256": _sha(601),
        "arm_id": comparison.STATIC14D_ARM,
        "runtime_operational_arm": "Static14D",
    }
    cluster = {
        "cluster_index": 0,
        "cluster_id_sha256": _sha(600),
        "route": {
            "route_id": "route", "corridor_id": "corridor", "family_id": "family",
            "source_event_identity_sha256": _sha(602), "physical_route_identity_sha256": _sha(603),
        },
    }
    raw = {
        "status": "ok",
        "candidate_row_sha256": rows,
        "candidate_tensor_sha256_before": _sha(604),
        "candidate_tensor_sha256_after": _sha(604),
        "selector_arms": ["pool_matched_candidate0", "Static14D"],
        "operational_arm": "Static14D",
        "primary_pool_model_call_count": 1,
        "zero_call_receipt": {
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        "selected_index": 2,
        "selected_trajectory_sha256": rows[2],
        "default_output_sha256": rows[0],
        "real_selector_receipts": {
            "Static14D": {"status": "ok", "selected_index": 2, "selected_row_sha256": rows[2]}
        },
        "same_ego_batch_metadata": {"same_ego_batch_size": 8, "nonlatent_rows_identical": True, "tensor_metadata": {"x": {}}},
        "source_input_sha256": _sha(605), "input_sha256": _sha(606),
        "latent_seed": 1, "latent_shape": [8, 321, 81, 4], "latent_dtype": "float32",
        "latent_tensor_sha256": _sha(607), "latent_row_sha256": rows,
        "candidate_shape": [8, 80, 4], "candidate_dtype": "float32", "candidate_finite": True,
        "latency_ms": {"total_planning": 1.0},
    }
    result = runner._runtime_unit(raw=raw, callback=SimpleNamespace(model_call_count=1), unit=unit, cluster=cluster)
    assert result["selection"]["selected_index"] == 2
    assert result["candidate_pool"]["candidate0_row"] == 0
    assert result["forward_calls"]["post_pool_model_forward_count"] == 0
    assert result["endpoint_vector"]["weighted_total_score"] is None


def test_static14_runtime_subset_does_not_materialize_or_call_9d_or_scene_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from camp_core.integrations import diffusion_planner_v26_native_runner as native

    callback = native.V26NativeSameEgoB8Callback.__new__(native.V26NativeSameEgoB8Callback)
    callback.selector_arms = ("pool_matched_candidate0", "Static14D")
    callback.selector_assets = SimpleNamespace(
        atom_scales=np.ones(14, dtype=np.float64),
        static14d_weights=np.full(14, 1.0 / 14.0, dtype=np.float64),
        static14d_weights_sha256=_sha(650),
    )
    callback.simplex_nonnegative_atol = boundary.FROZEN_SIMPLEX_TOLERANCE

    def materialize(**kwargs: object) -> dict[str, object]:
        phase = kwargs["phase_receipt"]
        phase.update(
            {
                "projection": {"status": "not_available", "elapsed_ns": None},
                "obb_build": {"status": "not_available", "elapsed_ns": None},
                "candidate_tick_obstacle_feasibility": {"status": "not_available", "elapsed_ns": None},
                "atom_arithmetic": {"status": "not_available", "elapsed_ns": None},
            }
        )
        return {
            "source_valid_mask": np.ones(8, dtype=np.bool_),
            "physical_feasible_mask": np.ones(8, dtype=np.bool_),
            "atom_matrix": np.zeros((8, 14), dtype=np.float64),
            "atom_source_valid_mask": np.ones((8, 14), dtype=np.bool_),
            "atom_applicable_mask": np.ones((8, 14), dtype=np.bool_),
            "candidate_reasons": [[] for _ in range(8)],
            "canonical_eligible": True,
            "exclusion_reason": None,
        }

    monkeypatch.setattr(native, "materialize_canonical_14d", materialize)
    callback._select_candidate = lambda **_kwargs: {
        "status": "ok", "failure_reason": None, "selected_index": 1,
        "scores": np.arange(8, dtype=np.float64),
        "physical_feasible_mask": np.ones(8, dtype=np.bool_),
        "source_valid_mask": np.ones(8, dtype=np.bool_),
    }
    candidates = np.arange(8 * 80 * 4, dtype=np.float32).reshape(8, 80, 4)
    result = callback._evaluate_pool(
        candidates=candidates,
        neighbors=np.zeros((8, 32, 80, 4), dtype=np.float32),
        causal={},
        neighbor_valid=np.zeros(32, dtype=np.bool_),
        signals=np.zeros(8, dtype=np.bool_),
        red_cost=np.zeros(8, dtype=np.float64),
        causal_signal_atom_input={},
    )
    assert tuple(result["arms"]) == ("pool_matched_candidate0", "Static14D")
    assert result["arms"]["Static14D"]["selected_index"] == 1
    assert result["summary"]["context"] is None


def test_adapted_boundary_and_endpoint_legacy_isolation_reject_v25_consumer() -> None:
    signal = boundary.resolve_v26_signal_adapter(
        {
            "signal_authority_mode": boundary.V26_CERTIFIED_NO_SIGNAL_MODE,
            "routes": [{"sha256": _sha(700)}],
            "map": {"sha256": _sha(701)},
            "certified_no_signal_authority": {
                "schema_version": boundary.V26_CERTIFIED_NO_SIGNAL_SCHEMA_VERSION,
                "route_sha256": _sha(700), "map_sha256": _sha(701), "route_lanelet_ids": [1],
                "route_geometry_sha256": _sha(702), "source_chain_sha256": _sha(703),
                "certification_sha256": _sha(704), "traffic_light_regulatory_element_ids": [],
            },
        }
    )
    value = boundary.build_v26_adapted_comparison_integration_boundary(
        signal=signal,
        reference_manifest_sha256=_sha(705),
        adaptation_receipt_sha256=_sha(706),
        adapted_asset_manifest_sha256=_sha(707),
    )
    assert value["evaluation_schema"] == boundary.V26_DEVELOPMENT_COMPARISON_EVALUATION_SCHEMA
    bad = copy.deepcopy(value)
    bad["consumer_ids"][-1] = "v25_industrial_bounded_closed_loop"
    with pytest.raises(ValueError, match="rejects V25 high-level"):
        boundary.validate_v26_integration_boundary(bad)
    endpoint = comparison.industrial_v3_endpoint_vector(planning_latency_ms=2.0)
    assert comparison.validate_industrial_v3_endpoint_vector(endpoint) == endpoint
    assert endpoint["legacy_safetycost"]["consumed"] is False


def test_atomic_failure_ledger_preserves_full_cluster_and_arm_denominator(tmp_path: Path) -> None:
    assets = comparison.load_v26_adapted_selector_assets(_write_adaptation_fixture(tmp_path))
    manifest = comparison.build_development_comparison_manifest(
        inventory=_comparison_inventory(assets),
        inventory_file_sha256=_sha(800),
        camp_head="a" * 40,
        base_probe=_base_probe(),
        adapted_assets=assets,
    )
    runner = __import__("scripts.integrations.run_diffusion_planner_v26_development_comparison", fromlist=["x"])
    ledger = runner._Ledger(output_dir=tmp_path / "comparison", manifest=manifest)
    ledger.record(
        runner._failure_unit(
            unit=manifest["unit_plan"][0],
            cluster=manifest["clusters"][0],
            failure_class="PreModelSourceFailure",
            failure_reason="fixture",
        )
    )
    receipt_path = ledger.finalize(terminal_error="fixture")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["denominator"] == {
        "planned_clusters": 2,
        "complete_clusters": 0,
        "typed_failure_clusters": 1,
        "unattempted_clusters": 1,
        "planned_arm_units": 6,
        "complete_arm_units": 0,
        "typed_failure_arm_units": 1,
        "unattempted_arm_units": 5,
    }
    assert (tmp_path / "comparison" / "units" / "000.json").is_file()
