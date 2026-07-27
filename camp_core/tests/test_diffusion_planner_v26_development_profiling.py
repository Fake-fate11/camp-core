from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from camp_core.integrations.diffusion_planner_v26_development_profiling import (
    ACTIVE_ATOM_INDICES_BY_ARM,
    ATOM_PHASE_NAMES,
    ATOM_SET_BY_ARM,
    EVIDENCE_ROLE,
    OPERATIONAL_ARM,
    PROFILE_ARMS,
    PROFILE_STATE_COUNT,
    build_development_profiling_manifest,
    build_development_profiling_receipt,
    validate_development_profiling_manifest,
    validate_development_profiling_receipt,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _manifest() -> dict[str, object]:
    return build_development_profiling_manifest(
        camp_head="a" * 40,
        probe_config_sha256=_sha(1),
        route_sha256=_sha(2),
        scenario_seed=17,
        spawn_config={"scenario_seed": 17},
        fixed_dp_head="b" * 40,
        checkpoint_path="/fixed/model.ckpt",
        checkpoint_sha256=_sha(3),
        args_path="/fixed/args.json",
        args_sha256=_sha(4),
        training_root_sha256=_sha(5),
        training_review_root_sha256=_sha(6),
        atom_scales_sha256=_sha(7),
        static9d_weights_sha256=_sha(8),
        scene9d_theta_sha256=_sha(9),
        static14d_weights_sha256=_sha(10),
        scene14d_theta_sha256=_sha(11),
        context_scaler_sha256=_sha(12),
    )


def _selector_arm(
    manifest: dict[str, object], arm_id: str, rows: list[str], selected: int
) -> dict[str, object]:
    if arm_id == OPERATIONAL_ARM:
        return {
            "arm_id": arm_id,
            "atom_set": ATOM_SET_BY_ARM[arm_id],
            "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
            "weights_sha256": None,
            "scoring_weights_sha256": None,
            "weight_parameter_sha256": None,
            "status": "ok",
            "failure_reason": None,
            "selected_index": 0,
            "selected_row_sha256": rows[0],
            "scores": None,
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "eligible_count": 8,
            "margin_best_vs_runner_up": None,
            "exact_tie_set": [0],
            "weight_input_source_complete": None,
        }
    parameter_key = {
        "Static9D": "static9d_weights_sha256",
        "Scene9D": "scene9d_theta_sha256",
        "Static14D": "static14d_weights_sha256",
        "Scene14D": "scene14d_theta_sha256",
    }[arm_id]
    parameter_sha = manifest["selector"][parameter_key]
    scores = [2.0 + float(index) for index in range(8)]
    scores[selected] = 0.0
    return {
        "arm_id": arm_id,
        "atom_set": ATOM_SET_BY_ARM[arm_id],
        "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
        "weights_sha256": parameter_sha if arm_id.startswith("Static") else _sha(400 + selected),
        "scoring_weights_sha256": _sha(420 + selected),
        "weight_parameter_sha256": parameter_sha,
        "status": "ok",
        "failure_reason": None,
        "selected_index": selected,
        "selected_row_sha256": rows[selected],
        "scores": scores,
        "physical_feasible_mask": [True] * 8,
        "source_valid_mask": [True] * 8,
        "eligible_count": 8,
        "margin_best_vs_runner_up": 2.0,
        "exact_tie_set": [selected],
        "weight_input_source_complete": (
            {"ego_speed_mps": True, "traffic_signal_phase_remaining_s": False}
            if arm_id.startswith("Scene")
            else None
        ),
    }


def _completed_unit(manifest: dict[str, object], unit_index: int) -> dict[str, object]:
    rows = [_sha(1000 + unit_index * 20 + index) for index in range(8)]
    selected = {
        OPERATIONAL_ARM: 0,
        "Static9D": 1,
        "Scene9D": 3,
        "Static14D": 2,
        "Scene14D": 3,
    }
    arms = {
        arm_id: _selector_arm(manifest, arm_id, rows, selected[arm_id])
        for arm_id in PROFILE_ARMS
    }
    return {
        "unit_index": unit_index,
        "planned_state_id_sha256": manifest["state_plan"][unit_index]["planned_state_id_sha256"],
        "state_sha256": _sha(2000 + unit_index),
        "input": {
            "source_input_sha256": _sha(2100 + unit_index),
            "expanded_input_sha256": _sha(2200 + unit_index),
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": {
                "history": {"shape": [8, 31, 11], "dtype": "torch.float32", "finite": True},
                "sampled_trajectories": {"shape": [8, 321, 81, 4], "dtype": "torch.float32", "finite": True},
            },
        },
        "latent": {
            "seed": 24001 + unit_index,
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "finite": True,
            "tensor_sha256": _sha(2300 + unit_index),
            "row_sha256": [_sha(2400 + unit_index * 20 + index) for index in range(8)],
            "row0_zero": True,
        },
        "candidate_pool": {
            "shape": [8, 80, 4],
            "dtype": "float32",
            "finite": True,
            "pool_sha256": _sha(2500 + unit_index),
            "row_sha256": rows,
            "candidate0": {"index": 0, "row_sha256": rows[0], "default_output_sha256": rows[0]},
        },
        "forward_calls": {
            "model_call_count_before": unit_index,
            "model_call_count_after": unit_index + 1,
            "model_call_delta": 1,
            "primary_forward_count": 1,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "arms": arms,
        "comparison": {
            "selection_disagrees_with_candidate0": {
                "Static9D": True,
                "Scene9D": True,
                "Static14D": True,
                "Scene14D": True,
            },
            "static9d_vs_static14d_flip": True,
            "scene9d_vs_scene14d_flip": False,
        },
        "atom_phase_timings": {
            name: {"status": "measured", "elapsed_ns": 1000 + unit_index}
            for name in ATOM_PHASE_NAMES
        },
        "simulator": {
            "operational_arm": OPERATIONAL_ARM,
            "selected_index": 0,
            "selected_row_sha256": rows[0],
        },
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _unattempted(manifest: dict[str, object], unit_index: int) -> dict[str, object]:
    return {
        "unit_index": unit_index,
        "planned_state_id_sha256": manifest["state_plan"][unit_index]["planned_state_id_sha256"],
        "state_sha256": None,
        "input": None,
        "latent": None,
        "candidate_pool": None,
        "forward_calls": {
            "model_call_count_before": 0,
            "model_call_count_after": 0,
            "model_call_delta": 0,
            "primary_forward_count": 0,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "arms": None,
        "comparison": None,
        "atom_phase_timings": None,
        "simulator": None,
        "terminal": {"status": "unattempted", "failure_class": None, "failure_reason": None},
    }


def test_manifest_fixes_twenty_nonholdout_same_pool_states_and_five_arms() -> None:
    manifest = _manifest()
    assert validate_development_profiling_manifest(manifest) == manifest
    assert manifest["evidence_role"] == EVIDENCE_ROLE
    assert manifest["state_count"] == PROFILE_STATE_COUNT
    assert manifest["selector_arms"] == list(PROFILE_ARMS)
    assert len(manifest["state_plan"]) == PROFILE_STATE_COUNT
    assert manifest["execution_topology"]["selector_comparison"] == "same_state_same_pool_counterfactual_only"

    holdout = copy.deepcopy(manifest)
    holdout["route"]["holdout"] = True
    with pytest.raises(ValueError, match="rejects holdout"):
        validate_development_profiling_manifest(holdout)
    wrong_arms = copy.deepcopy(manifest)
    wrong_arms["selector_arms"].pop()
    with pytest.raises(ValueError, match="fixed identity"):
        validate_development_profiling_manifest(wrong_arms)


def test_completed_receipt_binds_five_arms_to_one_b8_pool_and_describes_flips() -> None:
    manifest = _manifest()
    receipt = build_development_profiling_receipt(
        manifest=manifest,
        units=[_completed_unit(manifest, index) for index in range(PROFILE_STATE_COUNT)],
    )
    assert validate_development_profiling_receipt(receipt) == receipt
    assert receipt["denominator"] == {"planned": 20, "complete": 20, "failed": 0, "unattempted": 0}
    unit = receipt["units"][0]
    assert set(unit["arms"]) == set(PROFILE_ARMS)
    assert unit["candidate_pool"]["candidate0"]["index"] == 0
    assert unit["forward_calls"]["primary_forward_count"] == 1
    assert unit["forward_calls"]["post_pool_dp_forward_count"] == 0
    assert unit["simulator"]["selected_row_sha256"] == unit["candidate_pool"]["row_sha256"][0]
    assert receipt["descriptive_summary"]["nine_d_vs_fourteen_d_selection_flips"]["static9d_vs_static14d_flip"]["flip_count"] == 20
    assert "safety" not in receipt

    bad = copy.deepcopy(receipt)
    bad["units"][0]["arms"]["Static9D"]["weight_parameter_sha256"] = _sha(9999)
    with pytest.raises(ValueError, match="parameter identity"):
        validate_development_profiling_receipt(bad)
    bad = copy.deepcopy(receipt)
    bad["units"][0]["forward_calls"]["sequential_forward_count"] = 1
    with pytest.raises(ValueError, match="extra or post-pool"):
        validate_development_profiling_receipt(bad)


def test_typed_failure_and_unattempted_units_retain_full_denominator_without_actions() -> None:
    manifest = _manifest()
    failure = _unattempted(manifest, 0)
    failure["terminal"] = {
        "status": "typed_failure",
        "failure_class": "RuntimeError",
        "failure_reason": "route replay failed",
    }
    receipt = build_development_profiling_receipt(
        manifest=manifest,
        units=[failure, *[_unattempted(manifest, index) for index in range(1, PROFILE_STATE_COUNT)]],
    )
    assert receipt["denominator"] == {"planned": 20, "complete": 0, "failed": 1, "unattempted": 19}
    assert receipt["units"][0]["arms"] is None
    assert receipt["units"][0]["simulator"] is None


def test_runner_projects_one_actual_same_pool_tick_without_model_or_legacy_entry() -> None:
    manifest = _manifest()
    completed = _completed_unit(manifest, 0)
    rows = completed["candidate_pool"]["row_sha256"]
    raw_arms = {}
    for arm_id, arm in completed["arms"].items():
        raw_arms[arm_id] = {
            "status": arm["status"],
            "failure_reason": arm["failure_reason"],
            "selected_index": arm["selected_index"],
            "selected_row_sha256": arm["selected_row_sha256"],
            "scores": arm["scores"],
            "physical_feasible_mask": arm["physical_feasible_mask"],
            "source_valid_mask": arm["source_valid_mask"],
            "weights_sha256": arm["weights_sha256"],
            "scoring_weights_sha256": arm["scoring_weights_sha256"],
            "weight_parameter_sha256": arm["weight_parameter_sha256"],
            "eligible_count": arm["eligible_count"],
            "margin_best_vs_runner_up": arm["margin_best_vs_runner_up"],
            "exact_tie_set": arm["exact_tie_set"],
        }
        if arm_id.startswith("Scene"):
            raw_arms[arm_id]["context"] = {
                "source_complete": arm["weight_input_source_complete"],
            }
    raw = {
        "status": "ok",
        "candidate_row_sha256": rows,
        "candidate_tensor_sha256_before": completed["candidate_pool"]["pool_sha256"],
        "candidate_tensor_sha256_after": completed["candidate_pool"]["pool_sha256"],
        "zero_call_receipt": {
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        "primary_pool_model_call_count": 1,
        "real_selector_receipts": raw_arms,
        "materialized_summary": {"atom_materialization_phase_receipt": completed["atom_phase_timings"]},
        "same_ego_batch_metadata": completed["input"].copy(),
        "selected_index": 0,
        "selected_trajectory_sha256": rows[0],
        "state_sha256": completed["state_sha256"],
        "source_input_sha256": completed["input"]["source_input_sha256"],
        "input_sha256": completed["input"]["expanded_input_sha256"],
        "latent_seed": completed["latent"]["seed"],
        "latent_shape": completed["latent"]["shape"],
        "latent_dtype": completed["latent"]["dtype"],
        "latent_tensor_sha256": completed["latent"]["tensor_sha256"],
        "latent_row_sha256": completed["latent"]["row_sha256"],
        "candidate_shape": completed["candidate_pool"]["shape"],
        "candidate_dtype": completed["candidate_pool"]["dtype"],
        "candidate_finite": True,
        "default_output_sha256": rows[0],
    }
    runner = importlib.import_module("scripts.integrations.run_diffusion_planner_v26_development_profiling")
    unit = runner._completed_unit(raw, SimpleNamespace(model_call_count=1), unit_index=0, manifest=manifest)
    receipt = build_development_profiling_receipt(
        manifest=manifest,
        units=[unit, *[_unattempted(manifest, index) for index in range(1, PROFILE_STATE_COUNT)]],
    )
    assert receipt["units"][0]["simulator"]["selected_row_sha256"] == rows[0]
    assert receipt["units"][0]["arms"]["Scene9D"]["selected_row_sha256"] == rows[3]
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "evaluate_all_arms=False" in source
    assert "evaluation_arms=PROFILE_ARMS" in source
    assert "preflight(" not in source


def test_runner_parser_and_prepare_manifest_are_nonholdout_and_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = importlib.import_module("scripts.integrations.run_diffusion_planner_v26_development_profiling")
    assert callable(runner.array_sha256)
    args = runner.parse_args(
        [
            "--output-dir", "out",
            "--worker-lock", "worker.lock",
            "--probe-config", "probe.json",
            "--training", "training",
            "--training-root", _sha(1),
            "--training-review", "review",
            "--training-review-root", _sha(2),
            "--fixed-dp-repo", "fixed-dp",
        ]
    )
    assert args.device == "cuda"
    with pytest.raises(SystemExit):
        runner.parse_args(["--state-count", "21"])

    def write_bound_file(name: str, payload: bytes) -> dict[str, str]:
        path = tmp_path / name
        path.write_bytes(payload)
        return {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest()}

    route = write_bound_file("route.pkl", b"route")
    map_binding = write_bound_file("map.osm", b"map")
    checkpoint = write_bound_file("model.pth", b"checkpoint")
    args_json = write_bound_file("args.json", b"{}")
    config_path = tmp_path / "probe.json"
    config_path.write_text(
        json.dumps(
            {
                "protocol": {"holdout_access_authorized": False, "route_role": "development_nonholdout"},
                "routes": [{"name": "development", **route}],
                "map": map_binding,
                "seeds": {"scenario": 17},
                "spawn_config": {"seed": 17},
                "fixed_dp": {"checkpoint": checkpoint, "args_json": args_json},
            }
        ),
        encoding="utf-8",
    )
    fake_assets = SimpleNamespace(
        training_root_sha256=_sha(5),
        training_review_root_sha256=_sha(6),
        atom_scales_sha256=_sha(7),
        static9d_weights_sha256=_sha(8),
        scene9d_theta_sha256=_sha(9),
        static14d_weights_sha256=_sha(10),
        scene14d_theta_sha256=_sha(11),
        context_scaler_sha256=_sha(12),
    )
    monkeypatch.setattr(runner, "_tracked_changes", lambda _path: False)
    monkeypatch.setattr(runner, "_git_head", lambda _path: "7a1d33da277a1992ec474b5383a0c963c72e04e4")
    monkeypatch.setattr(runner, "_load_profiling_selector_assets", lambda _args: fake_assets)
    manifest, config, assets = runner._prepare_manifest(
        argparse.Namespace(
            probe_config=config_path,
            training=tmp_path / "training",
            training_root=_sha(5),
            training_review=tmp_path / "review",
            training_review_root=_sha(6),
            fixed_dp_repo=tmp_path / "fixed_dp",
        )
    )
    assert assets is fake_assets
    assert config["protocol"]["route_role"] == "development_nonholdout"
    assert manifest["selector_arms"] == list(PROFILE_ARMS)
    holdout = copy.deepcopy(config)
    holdout["protocol"]["route_role"] = "holdout"
    with pytest.raises(ValueError, match="development_nonholdout"):
        runner._require_nonholdout_config(holdout)
