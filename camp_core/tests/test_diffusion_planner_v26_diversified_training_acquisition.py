from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES
from camp_core.integrations.diffusion_planner_v26_development_profiling import (
    OPERATIONAL_ARM,
    PROFILE_ARMS,
)


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(index: int) -> str:
    return f"{index:064x}"


def _schedule() -> dict[str, object]:
    return {
        "family_id": "legacy_simple_cross",
        "route_id": "legacy_simple_cross/route-0000",
        "corridor_id": _sha(9),
        "source_artifact_sha256": _sha(10),
        "event_manifest_sha256": _sha(11),
        "route_record": {
            "identity_sha256": _sha(12),
            "source_map_sha256": _sha(13),
            "source_geometry_sha256": _sha(14),
            "lanelet_ids": [1, 2],
            "source_stratum": {
                "traffic_light": False,
                "branch_intersection": False,
                "tight_corridor": True,
                "short_progress_opportunity": False,
            },
            "route_spec": {
                "map_path": "/root/autodl-tmp/maps/simple.osm",
                "lanelet_ids": [1, 2],
                "start_pose": [0.0, 0.0, 0.0],
                "goal_pose": [1.0, 0.0, 0.0],
                "route_length_m": 20.0,
            },
        },
    }


def _raw() -> dict[str, object]:
    rows = [_sha(100 + index) for index in range(8)]
    atom_source = np.ones((8, 14), dtype=bool).tolist()
    arms = {}
    for arm_id in PROFILE_ARMS:
        selected = 0 if arm_id == OPERATIONAL_ARM else 1
        arms[arm_id] = {
            "status": "ok",
            "failure_reason": None,
            "selected_index": selected,
            "selected_row_sha256": rows[selected],
            "source_valid_mask": [True] * 8,
            "physical_feasible_mask": [True] * 8,
            "margin_best_vs_runner_up": None if arm_id == OPERATIONAL_ARM else 1.0,
            "exact_tie_set": [selected],
        }
    return {
        "status": "ok",
        "candidate_row_sha256": rows,
        "candidate_tensor_sha256_before": _sha(200),
        "candidate_tensor_sha256_after": _sha(200),
        "zero_call_receipt": {
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        "primary_pool_model_call_count": 1,
        "same_ego_batch_metadata": {
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": {"history": {"shape": [8, 3], "dtype": "torch.float32", "finite": True}},
        },
        "selected_index": 0,
        "selected_trajectory_sha256": rows[0],
        "state_sha256": _sha(201),
        "source_input_sha256": _sha(202),
        "input_sha256": _sha(203),
        "latent_seed": 24001,
        "latent_shape": [8, 321, 81, 4],
        "latent_dtype": "float32",
        "latent_tensor_sha256": _sha(204),
        "latent_row_sha256": [_sha(210 + index) for index in range(8)],
        "candidate_shape": [8, 80, 4],
        "candidate_dtype": "float32",
        "candidate_finite": True,
        "default_output_sha256": rows[0],
        "real_selector_receipts": arms,
        "integration_boundary": {"runner_id": "fixture"},
        "controlled_scene": {"status": "fixture"},
        "causal_signal_atom_input_sha256": _sha(205),
        "materialized_summary": {
            "atom_matrix": np.ones((8, 14), dtype=np.float64).tolist(),
            "atom_matrix_sha256": _sha(206),
            "atom_source_valid_mask": atom_source,
            "atom_applicable_mask": atom_source,
            "source_valid_mask": [True] * 8,
            "physical_feasible_mask": [True] * 8,
            "context": {
                "raw_context": {name: float(index) for index, name in enumerate(RAW_FEATURE_NAMES)},
                "source_complete": {name: True for name in RAW_FEATURE_NAMES},
            },
            "atom_materialization_phase_receipt": {"projection": {"status": "measured"}},
        },
    }


def test_completed_unit_retains_b8_masks_hashes_and_candidate0() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    unit = runner._completed_unit(
        _raw(),
        SimpleNamespace(model_call_count=1),
        unit_index=0,
        route_plan_sha256=_sha(1),
        schedule=_schedule(),
        scenario_seed=46001,
    )

    assert unit["forward_calls"]["primary_forward_count"] == 1
    assert unit["forward_calls"]["sequential_forward_count"] == 0
    assert unit["candidate_pool"]["candidate0"]["index"] == 0
    assert unit["action"]["simulator_selected_row_sha256"] == unit["candidate_pool"]["row_sha256"][0]
    assert np.asarray(unit["training_pool"]["atom_source_valid_mask"]).shape == (8, 14)


def test_signal_route_without_sidecar_is_pre_model_failure_and_no_signal_is_explicit() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    schedule = _schedule()
    traffic = dict(schedule)
    traffic_record = dict(schedule["route_record"])
    traffic_record["source_stratum"] = {**traffic_record["source_stratum"], "traffic_light": True}
    traffic["route_record"] = traffic_record
    configuration, failure = runner._signal_config(
        schedule=traffic, family={"sidecar": None}, route_sha256=_sha(2)
    )
    assert configuration is None
    assert failure == "signal_authority_unavailable_for_traffic_route"

    configuration, failure = runner._signal_config(
        schedule=schedule, family={"sidecar": None}, route_sha256=_sha(2)
    )
    assert failure is None
    assert configuration["signal_authority_mode"] == "certified_no_signal"
    assert configuration["certified_no_signal_authority"]["traffic_light_regulatory_element_ids"] == []


def test_parser_and_source_keep_the_v26_native_boundary() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    args = runner.parse_args(
        [
            "--output-dir", "out",
            "--worker-lock", "lock",
            "--route-plan", "plan.json",
            "--base-probe-config", "base.json",
            "--reference-weights", "weights",
            "--reference-weights-root", _sha(3),
            "--reference-weights-review", "review",
            "--reference-weights-review-root", _sha(4),
            "--fixed-dp-repo", "fixed-dp",
            "--expected-camp-head", "a" * 40,
        ]
    )
    assert args.device == "cuda"
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "run_v26_native_same_ego_b8_replay" in source
    assert "validate_diffusion_planner_v25_fair_nonholdout" not in source
    assert "run_diffusion_planner_v25_industrial_bounded_closed_loop" not in source
    assert "_build_no_signal_chain" not in source
