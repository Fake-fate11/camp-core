import importlib
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _bridge():
    try:
        return importlib.import_module(
            "camp_core.integrations.diffusion_planner_v19_nuplan_bridge"
        )
    except ModuleNotFoundError:
        pytest.fail("the v19 nuPlan file bridge is missing")


def _causal_arrays() -> dict[str, np.ndarray]:
    arrays = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    arrays["version"] = np.array(1, dtype=np.int64)
    return arrays


def _request_metadata(module, *, arm: str = "camp") -> dict[str, object]:
    return module.build_request_metadata(
        arm=arm,
        log_name="log-a",
        scenario_token="scenario-a",
        iteration_index=7,
        simulation_time_us=700_000,
        scenario_seed=3411,
        dp_seed_root=3412,
        camp_head="a" * 40,
        dp_head="b" * 40,
        nuplan_head="c" * 40,
        causal_input=_causal_arrays(),
        speed_source_policy="full_window_exact_speed",
        selector_hashes=("d" * 64, "e" * 64, "f" * 64),
    )


def _request_evidence(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "causal_input_sha256": metadata["causal_input_sha256"],
        "simulation_time_us": metadata["simulation_time_us"],
        "tick_seed": metadata["tick_seed"],
        "pair_run_key": metadata["pair_run_key"],
        "dp_head": metadata["dp_head"],
        "scenario_token": metadata["scenario_token"],
        "request_metadata_sha256": hashlib.sha256(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def test_paired_run_key_is_stable_and_arm_keys_are_distinct() -> None:
    module = _bridge()

    pair = module.paired_run_key("log-a", "scenario-a", 3411)

    assert pair == module.paired_run_key("log-a", "scenario-a", 3411)
    assert module.arm_run_key(pair, "dp_default") != module.arm_run_key(
        pair, "camp"
    )
    with pytest.raises(ValueError, match="formal seed"):
        module.paired_run_key("log-a", "scenario-a", 11)


def test_request_rejects_unapproved_speed_source_policy(tmp_path: Path) -> None:
    module = _bridge()
    arrays = _causal_arrays()
    with pytest.raises(ValueError, match="speed-source policy"):
        module.build_request_metadata(
            arm="camp",
            log_name="log-a",
            scenario_token="scenario-a",
            iteration_index=7,
            simulation_time_us=700_000,
            scenario_seed=3411,
            dp_seed_root=3412,
            camp_head="a" * 40,
            dp_head="b" * 40,
            nuplan_head="c" * 40,
            causal_input=arrays,
            speed_source_policy="nearby_lane_fallback",
            selector_hashes=("d" * 64, "e" * 64, "f" * 64),
        )

    metadata = _request_metadata(module)
    metadata["speed_source_policy"] = "nearby_lane_fallback"
    with pytest.raises(ValueError, match="speed-source policy"):
        module.write_request(tmp_path, arrays, metadata)


def test_request_round_trip_uses_json_as_readiness_marker(tmp_path: Path) -> None:
    module = _bridge()
    arrays = _causal_arrays()
    metadata = _request_metadata(module)

    module.write_request(tmp_path, arrays, metadata)
    loaded = module.read_request(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=7,
    )

    assert set(loaded.arrays) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert loaded.metadata == metadata
    assert (tmp_path / "request.npz").is_file()
    assert (tmp_path / "request.json").is_file()
    (tmp_path / "request.json").unlink()
    with pytest.raises(FileNotFoundError, match="request.json"):
        module.read_request(
            tmp_path,
            expected_run_key=str(metadata["run_key"]),
            expected_iteration_index=7,
        )


def test_request_rejects_forbidden_or_stale_inputs(tmp_path: Path) -> None:
    module = _bridge()
    arrays = _causal_arrays()
    metadata = _request_metadata(module)
    metadata["expert_future"] = [[0.0, 0.0]]
    with pytest.raises(ValueError, match="forbidden online field"):
        module.write_request(tmp_path, arrays, metadata)

    metadata.pop("expert_future")
    arrays["extra"] = np.zeros(1, dtype=np.float32)
    with pytest.raises(ValueError, match="extra"):
        module.write_request(tmp_path, arrays, metadata)

    arrays.pop("extra")
    module.write_request(tmp_path, arrays, metadata)
    with pytest.raises(ValueError, match="iteration"):
        module.read_request(
            tmp_path,
            expected_run_key=str(metadata["run_key"]),
            expected_iteration_index=8,
        )


def test_response_rejects_hash_or_shape_mismatch(tmp_path: Path) -> None:
    module = _bridge()
    trajectory = np.zeros((80, 4), dtype=np.float32)
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "dp_default",
        "run_key": "run:dp_default",
        "iteration_index": 0,
        "status": "ok",
        "selected_trajectory_sha256": module.array_sha256(trajectory),
        "baseline_name": "DP operational Top-1",
        "baseline_provenance": (
            "unmodified single DP output; independently equivalent to K=8 candidate 0"
        ),
        "native_ranked_top1": False,
        "speed_source_policy": "full_window_exact_speed",
    }
    module.write_response(tmp_path, {"selected_trajectory": trajectory}, metadata)
    loaded = module.read_response(
        tmp_path, expected_run_key="run:dp_default", expected_iteration_index=0
    )
    assert loaded.arrays["selected_trajectory"].shape == (80, 4)

    payload = json.loads((tmp_path / "response.json").read_text(encoding="utf-8"))
    payload["selected_trajectory_sha256"] = "0" * 64
    (tmp_path / "response.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="trajectory SHA"):
        module.read_response(
            tmp_path,
            expected_run_key="run:dp_default",
            expected_iteration_index=0,
        )


def test_plan_tick_response_requires_planned_red_and_worker_latency(
    tmp_path: Path,
) -> None:
    module = _bridge()
    trajectory = np.zeros((80, 4), dtype=np.float32)
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "dp_default",
        "run_key": "run:dp_default",
        "iteration_index": 0,
        "operation": "plan_tick",
        "status": "ok",
        "selected_trajectory_sha256": module.array_sha256(trajectory),
        "baseline_name": "DP operational Top-1",
        "baseline_provenance": (
            "unmodified single DP output; independently equivalent to K=8 candidate 0"
        ),
        "native_ranked_top1": False,
        "speed_source_policy": "full_window_exact_speed",
    }

    with pytest.raises(ValueError, match="planned-red|latency"):
        module.write_response(
            tmp_path / "missing", {"selected_trajectory": trajectory}, metadata
        )

    metadata.update(
        {
            "selected_planned_red_light_cost": 0.0,
            "planned_red_source": "fixed_dp_red_cost_v18",
            "worker_latency_ms": {"dp_inference": 1.0, "atom_selector": 0.0},
        }
    )
    module.write_response(
        tmp_path / "valid", {"selected_trajectory": trajectory}, metadata
    )

    bad = dict(metadata)
    bad["worker_latency_ms"] = {"dp_inference": -1.0, "atom_selector": 0.0}
    with pytest.raises(ValueError, match="latency"):
        module.write_response(
            tmp_path / "bad-latency", {"selected_trajectory": trajectory}, bad
        )


def test_all_k_infeasible_response_contains_evidence_and_no_trajectory(
    tmp_path: Path,
) -> None:
    module = _bridge()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": "run:camp",
        "iteration_index": 2,
        "status": "failed",
        "failure_reason": "all_candidates_physically_infeasible",
        "candidate_sha256_before": module.array_sha256(candidates),
        "candidate_sha256_after": module.array_sha256(candidates),
        "candidate_reasons": [["obb_collision"] for _ in range(8)],
        "native_ranked_top1": False,
        "speed_source_policy": "full_window_exact_speed",
    }
    arrays = {
        "candidates": candidates,
        "physical_feasible_mask": np.zeros(8, dtype=bool),
    }

    module.write_response(tmp_path, arrays, metadata)
    loaded = module.read_response(
        tmp_path, expected_run_key="run:camp", expected_iteration_index=2
    )

    assert "selected_trajectory" not in loaded.arrays
    assert not loaded.arrays["physical_feasible_mask"].any()


def test_camp_success_response_requires_immutable_k8_tensor(tmp_path: Path) -> None:
    module = _bridge()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[3, :, 0] = 1.0
    digest = module.array_sha256(candidates)
    arrays = {
        "candidates": candidates,
        "neighbor_predictions": np.zeros((8, 32, 80, 4), dtype=np.float32),
        "neighbor_valid_mask": np.zeros(32, dtype=bool),
        "signal_mask": np.ones(8, dtype=bool),
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "atom_matrix": np.zeros((8, 14), dtype=np.float64),
        "planned_red_light_cost": np.arange(8, dtype=np.float64) * 2e-12,
        "selected_index": np.array(3, dtype=np.int64),
        "selected_trajectory": candidates[3],
    }
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": "run:camp",
        "iteration_index": 3,
        "operation": "plan_tick",
        "status": "ok",
        "candidate_sha256_before": digest,
        "candidate_sha256_after": digest,
        "selected_trajectory_sha256": module.array_sha256(candidates[3]),
        "candidate_reasons": [[] for _ in range(8)],
        "selected_planned_red_light_cost": 6e-12,
        "planned_red_source": "fixed_dp_red_cost_v18",
        "worker_latency_ms": {"dp_inference": 1.0, "atom_selector": 2.0},
        "native_ranked_top1": False,
        "speed_source_policy": "full_window_exact_speed",
    }

    module.write_response(tmp_path, arrays, metadata)
    module.read_response(
        tmp_path, expected_run_key="run:camp", expected_iteration_index=3
    )

    metadata["candidate_sha256_after"] = "0" * 64
    with pytest.raises(ValueError, match="candidate tensor mutated"):
        module.write_response(tmp_path / "mutated", arrays, metadata)

    metadata["candidate_sha256_after"] = digest
    metadata["selected_planned_red_light_cost"] = 0.0
    with pytest.raises(ValueError, match="planned-red"):
        module.write_response(tmp_path / "red-mismatch", arrays, metadata)


def test_source_probe_response_requires_unchanged_k8_and_source_mask(
    tmp_path: Path,
) -> None:
    module = _bridge()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    source_mask = np.array([True, False, True, False, False, False, False, False])
    digest = module.array_sha256(candidates)
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": "run:camp",
        "iteration_index": 0,
        "operation": "source_probe",
        "speed_source_policy": "candidate_local_exact_speed",
        "status": "ok",
        "native_ranked_top1": False,
        "candidate_sha256_before": digest,
        "candidate_sha256_after": digest,
        "dp_default_source_complete": True,
        "eligible_candidate_count": 2,
    }

    module.write_response(
        tmp_path,
        {
            "candidates": candidates,
            "route_speed_source_eligible_mask": source_mask,
        },
        metadata,
    )
    loaded = module.read_response(
        tmp_path,
        expected_run_key="run:camp",
        expected_iteration_index=0,
    )

    assert loaded.arrays["candidates"].shape == (8, 80, 4)
    np.testing.assert_array_equal(
        loaded.arrays["route_speed_source_eligible_mask"], source_mask
    )
    assert loaded.metadata["candidate_sha256_before"] == digest
    assert loaded.metadata["candidate_sha256_after"] == digest


def test_response_rejects_request_speed_source_policy_mismatch(tmp_path: Path) -> None:
    module = _bridge()
    arrays = _causal_arrays()
    metadata = _request_metadata(module)
    module.write_request(tmp_path, arrays, metadata)
    response = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": metadata["run_key"],
        "iteration_index": 7,
        "operation": "source_probe",
        "speed_source_policy": "candidate_local_exact_speed",
        "status": "ok",
        "native_ranked_top1": False,
        "candidate_sha256_before": module.array_sha256(
            np.zeros((8, 80, 4), dtype=np.float32)
        ),
        "candidate_sha256_after": module.array_sha256(
            np.zeros((8, 80, 4), dtype=np.float32)
        ),
        "dp_default_source_complete": True,
        "eligible_candidate_count": 8,
        "request_evidence": _request_evidence(metadata),
    }
    with pytest.raises(ValueError, match="speed-source policy mismatch"):
        module.write_response(
            tmp_path,
            {
                "candidates": np.zeros((8, 80, 4), dtype=np.float32),
                "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
            },
            response,
        )


@pytest.mark.parametrize("tamper", ("missing", "unknown", "changed"))
def test_response_with_request_requires_exact_request_evidence(
    tmp_path: Path, tamper: str
) -> None:
    module = _bridge()
    directory = tmp_path / tamper
    arrays = _causal_arrays()
    request = _request_metadata(module)
    module.write_request(directory, arrays, request)
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    response = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": request["run_key"],
        "iteration_index": 7,
        "operation": "source_probe",
        "speed_source_policy": "full_window_exact_speed",
        "status": "ok",
        "native_ranked_top1": False,
        "candidate_sha256_before": module.array_sha256(candidates),
        "candidate_sha256_after": module.array_sha256(candidates),
        "dp_default_source_complete": True,
        "eligible_candidate_count": 8,
        "request_evidence": _request_evidence(request),
    }
    if tamper == "missing":
        del response["request_evidence"]
    elif tamper == "unknown":
        response["request_evidence"]["unknown"] = None
    else:
        response["request_evidence"]["causal_input_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="request evidence"):
        module.write_response(
            directory,
            {
                "candidates": candidates,
                "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
            },
            response,
        )
