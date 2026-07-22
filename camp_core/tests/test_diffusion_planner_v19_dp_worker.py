import importlib
import hashlib
import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    build_request_metadata,
    read_response,
    write_request,
)


def _worker():
    try:
        return importlib.import_module(
            "scripts.integrations.run_diffusion_planner_dp_camp_v19_worker"
        )
    except ModuleNotFoundError:
        pytest.fail("the one-shot v19 fixed-DP worker is missing")


def _fake_infer(latent: np.ndarray) -> np.ndarray:
    assert latent.shape == (321, 81, 4)
    result = latent[:, 1:].astype(np.float32, copy=True)
    heading = result[..., 2].copy()
    result[..., 2] = np.cos(heading)
    result[..., 3] = np.sin(heading)
    return result


def _valid_candidate_tensor() -> np.ndarray:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    return candidates


def _request(
    tmp_path,
    *,
    arm: str,
    speed_source_policy: str = "full_window_exact_speed",
    route_speed_available: bool = True,
):
    arrays = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    arrays["version"] = np.array(1, dtype=np.int64)
    arrays["route_lanes"][0, :, 0] = np.linspace(0.0, 19.0, 20)
    arrays["route_lanes"][0, :, 2] = 1.0
    arrays["route_lanes"][0, :, 5] = 2.0
    arrays["route_lanes"][0, :, 7] = -2.0
    arrays["route_lanes"][0, :, 13] = 1.0
    arrays["route_lanes_has_speed_limit"][0, 0] = route_speed_available
    arrays["route_lanes_speed_limit"][0, 0] = (
        10.0 if route_speed_available else 0.0
    )
    metadata = build_request_metadata(
        arm=arm,
        log_name="log-a",
        scenario_token="scenario-a",
        iteration_index=0,
        simulation_time_us=0,
        scenario_seed=3411,
        dp_seed_root=3412,
        camp_head="a" * 40,
        dp_head="b" * 40,
        nuplan_head="c" * 40,
        causal_input=arrays,
        speed_source_policy=speed_source_policy,
        selector_hashes=("d" * 64, "e" * 64, "f" * 64)
        if arm == "camp"
        else None,
    )
    write_request(tmp_path, arrays, metadata)
    return metadata


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


def test_default_and_candidate0_are_independent_zero_latent_calls() -> None:
    module = _worker()
    calls = []

    def infer(latent: np.ndarray) -> np.ndarray:
        calls.append(latent.copy())
        return _fake_infer(latent)

    default, default_neighbors = module.run_fixed_dp_default(infer)
    candidates, neighbors = module.run_fixed_dp_candidates(
        infer, np.random.default_rng(3412), noise_scale=1.0
    )
    provenance = module.verify_default_equivalence(default, candidates[0])

    assert default.shape == (80, 4)
    assert default_neighbors.shape == (32, 80, 4)
    assert candidates.shape == (8, 80, 4)
    assert neighbors.shape == (8, 32, 80, 4)
    assert np.count_nonzero(calls[0]) == 0
    assert np.count_nonzero(calls[1]) == 0
    assert all(np.count_nonzero(latent) > 0 for latent in calls[2:])
    assert provenance["elementwise_equal"] is True
    assert provenance["max_abs_difference"] == 0.0
    assert provenance["default_output_sha256"] == provenance["candidate0_sha256"]
    assert provenance["baseline_name"] == "DP operational Top-1"
    assert provenance["baseline_provenance"] == (
        "unmodified single DP output; independently equivalent to K=8 candidate 0"
    )
    assert provenance["native_ranked_top1"] is False


def test_default_equivalence_fails_closed_on_any_drift() -> None:
    module = _worker()
    default = np.zeros((80, 4), dtype=np.float32)
    candidate0 = default.copy()
    candidate0[0, 0] = np.finfo(np.float32).eps

    with pytest.raises(ValueError, match="default.*equivalence"):
        module.verify_default_equivalence(default, candidate0)


def test_selector_is_affine_simplex_feasible_only_and_nonmutating() -> None:
    module = _worker()
    candidates = _valid_candidate_tensor()
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    atoms = np.full((8, 14), 10.0, dtype=np.float64)
    atoms[0, 0] = 0.0
    atoms[3, 0] = 1.0
    atoms[5, 0] = 2.0
    feasible = np.zeros(8, dtype=bool)
    feasible[[3, 5]] = True
    materialized = {
        "canonical_eligible": True,
        "atom_matrix": atoms,
        "physical_feasible_mask": feasible,
        "candidate_reasons": [tuple() for _ in range(8)],
    }
    scales = np.ones(14, dtype=np.float64)
    weights = np.zeros(14, dtype=np.float64)
    weights[0] = 1.0
    before = candidates.copy()

    result = module.select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=scales,
        weights=weights,
    )

    assert result["status"] == "ok"
    assert result["selected_index"] == 3
    assert np.array_equal(result["selected_trajectory"], candidates[3])
    assert np.array_equal(candidates, before)
    assert result["candidate_sha256_before"] == result["candidate_sha256_after"]
    assert result["score_contract"] == "score_k=clip(a_k/s,0,10)^T w"
    assert result["tie_break_contract"] == "lowest_eligible_candidate_index"
    assert result["native_ranked_top1"] is False


def test_selector_rejects_non_simplex_and_all_k_fails_closed() -> None:
    module = _worker()
    candidates = _valid_candidate_tensor()
    materialized = {
        "canonical_eligible": False,
        "exclusion_reason": "all_candidates_physically_infeasible",
        "atom_matrix": None,
        "physical_feasible_mask": np.zeros(8, dtype=bool),
        "candidate_reasons": [("obb_collision",) for _ in range(8)],
    }
    scales = np.ones(14, dtype=np.float64)
    weights = np.ones(14, dtype=np.float64) / 14.0

    result = module.select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=scales,
        weights=weights,
    )

    assert result["status"] == "failed"
    assert result["failure_reason"] == "all_candidates_physically_infeasible"
    assert "selected_index" not in result
    assert "selected_trajectory" not in result

    bad_weights = weights.copy()
    bad_weights[0] = -0.1
    with pytest.raises(ValueError, match="nonnegative simplex"):
        module.select_camp_candidate(
            candidates=candidates,
            materialized=materialized,
            atom_scales=scales,
            weights=bad_weights,
        )


def test_selector_preserves_solver_feasible_weights_only_with_explicit_tolerance() -> None:
    module = _worker()
    candidates = _valid_candidate_tensor()
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    weights[1] += weights[0] + 5e-18
    weights[0] = -5e-18
    materialized = {
        "canonical_eligible": True,
        "atom_matrix": np.zeros((8, 14), dtype=np.float64),
        "source_valid_mask": np.ones(8, dtype=bool),
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "candidate_reasons": [tuple() for _ in range(8)],
    }

    with pytest.raises(ValueError, match="nonnegative simplex"):
        module.select_camp_candidate(
            candidates=candidates,
            materialized=materialized,
            atom_scales=np.ones(14, dtype=np.float64),
            weights=weights,
        )
    accepted = module.select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=np.ones(14, dtype=np.float64),
        weights=weights,
        simplex_nonnegative_atol=1e-9,
    )
    assert accepted["selected_index"] == 0

    outside = weights.copy()
    outside[1] += 2e-9 - 5e-18
    outside[0] = -2e-9
    with pytest.raises(ValueError, match="nonnegative simplex"):
        module.select_camp_candidate(
            candidates=candidates,
            materialized=materialized,
            atom_scales=np.ones(14, dtype=np.float64),
            weights=outside,
            simplex_nonnegative_atol=1e-9,
        )


def test_v22_selector_scores_all_source_valid_candidates_when_all_high_risk() -> None:
    module = _worker()
    candidates = _valid_candidate_tensor()
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    atoms = np.ones((8, 14), dtype=np.float64)
    atoms[6, 0] = 0.0
    materialized = {
        "canonical_eligible": True,
        "atom_matrix": atoms,
        "source_valid_mask": np.ones(8, dtype=bool),
        "physical_feasible_mask": np.zeros(8, dtype=bool),
        "all_k_high_risk": True,
        "candidate_reasons": [("lane_corridor",)] * 8,
    }

    result = module.select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=np.ones(14, dtype=np.float64),
        weights=np.eye(1, 14, dtype=np.float64).reshape(14),
        eligibility_mask_name="source_valid_mask",
    )

    assert result["status"] == "ok"
    assert result["selected_index"] == 6
    assert result["all_k_high_risk"] is True
    assert result["physical_feasible_mask"].tolist() == [False] * 8
    assert result["source_valid_mask"].tolist() == [True] * 8
    assert result["candidate_sha256_before"] == result["candidate_sha256_after"]


def test_process_default_provenance_writes_independent_equivalence(tmp_path) -> None:
    module = _worker()
    metadata = _request(tmp_path, arm="dp_default")

    module.process_request(
        tmp_path,
        operation="default_provenance",
        infer_one=_fake_infer,
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert response.metadata["elementwise_equal"] is True
    assert response.metadata["max_abs_difference"] == 0.0
    assert np.array_equal(
        response.arrays["default_trajectory"],
        response.arrays["independent_reference_trajectory"],
    )
    assert response.metadata["native_ranked_top1"] is False
    assert response.metadata["baseline_name"] == "DP operational Top-1"
    assert response.metadata["baseline_provenance"] == (
        "unmodified single DP output; independently equivalent to K=8 candidate 0"
    )
    assert response.metadata["request_evidence"] == _request_evidence(metadata)


def test_process_default_tick_records_planned_red_without_generating_k8(
    tmp_path,
) -> None:
    module = _worker()
    metadata = _request(tmp_path, arm="dp_default")
    inference_calls = []
    planned_calls = []

    def infer(latent: np.ndarray) -> np.ndarray:
        inference_calls.append(latent.copy())
        return _fake_infer(latent)

    def planned(candidates: np.ndarray, _causal):
        planned_calls.append(candidates.copy())
        return np.array([2e-12], dtype=np.float64)

    module.process_request(
        tmp_path,
        operation="plan_tick",
        infer_one=infer,
        planned_red_cost=planned,
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert len(inference_calls) == 1
    assert planned_calls[0].shape == (1, 80, 4)
    assert "candidates" not in response.arrays
    assert response.metadata["operation"] == "plan_tick"
    assert response.metadata["selected_planned_red_light_cost"] == pytest.approx(
        2e-12
    )
    assert response.metadata["planned_red_source"] == "fixed_dp_red_cost_v18"
    assert response.metadata["worker_latency_ms"]["dp_inference"] >= 0.0
    assert response.metadata["worker_latency_ms"]["atom_selector"] == 0.0


def test_process_default_candidate_local_tick_fails_without_speed_source(
    tmp_path,
) -> None:
    module = _worker()
    metadata = _request(
        tmp_path,
        arm="dp_default",
        speed_source_policy="candidate_local_exact_speed",
        route_speed_available=False,
    )

    module.process_request(
        tmp_path,
        operation="plan_tick",
        infer_one=_fake_infer,
        planned_red_cost=lambda _candidates, _causal: np.zeros(1),
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert response.metadata["status"] == "failed"
    assert response.metadata["failure_reason"] == (
        "dp_default_route_speed_source_ineligible"
    )
    assert response.metadata["baseline_name"] == "DP operational Top-1"
    assert response.metadata["baseline_provenance"] == (
        "unmodified single DP output; independently equivalent to K=8 candidate 0"
    )
    assert response.metadata["native_ranked_top1"] is False
    assert "selected_trajectory" not in response.arrays


def test_source_probe_writes_only_unchanged_candidates_and_source_mask(
    tmp_path,
) -> None:
    module = _worker()
    metadata = _request(
        tmp_path,
        arm="camp",
        speed_source_policy="candidate_local_exact_speed",
    )

    module.process_request(
        tmp_path,
        operation="source_probe",
        infer_one=_fake_infer,
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert set(response.arrays) == {
        "candidates",
        "route_speed_source_eligible_mask",
    }
    assert response.arrays["candidates"].shape == (8, 80, 4)
    assert response.arrays["route_speed_source_eligible_mask"].all()
    assert response.metadata["candidate_sha256_before"] == response.metadata[
        "candidate_sha256_after"
    ]
    assert response.metadata["eligible_candidate_count"] == 8
    assert response.metadata["request_evidence"] == _request_evidence(metadata)


def test_source_probe_rejects_dp_default_arm(tmp_path) -> None:
    module = _worker()
    _request(
        tmp_path,
        arm="dp_default",
        speed_source_policy="candidate_local_exact_speed",
    )

    with pytest.raises(ValueError, match="source probe requires the CAMP arm"):
        module.process_request(
            tmp_path,
            operation="source_probe",
            infer_one=_fake_infer,
        )


def test_process_camp_tick_writes_k8_selection_without_mutation(tmp_path) -> None:
    module = _worker()
    metadata = _request(tmp_path, arm="camp")

    def materialize(**kwargs):
        atoms = np.full((8, 14), 10.0, dtype=np.float64)
        atoms[3, 0] = 0.0
        return {
            "canonical_eligible": True,
            "atom_matrix": atoms,
            "physical_feasible_mask": np.ones(8, dtype=bool),
            "candidate_reasons": [tuple() for _ in range(8)],
        }

    weights = np.zeros(14, dtype=np.float64)
    weights[0] = 1.0
    module.process_request(
        tmp_path,
        operation="plan_tick",
        infer_one=_fake_infer,
        atom_scales=np.ones(14, dtype=np.float64),
        weights=weights,
        planned_red_cost=lambda _candidates, _causal: (
            np.arange(8, dtype=np.float64) * 2e-12
        ),
        signal_mask=lambda _candidates, _route: np.ones(8, dtype=bool),
        materialize=materialize,
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert response.arrays["candidates"].shape == (8, 80, 4)
    assert response.arrays["atom_matrix"].shape == (8, 14)
    assert response.metadata["candidate_sha256_before"] == response.metadata[
        "candidate_sha256_after"
    ]
    assert response.arrays["selected_index"] == 3
    assert response.metadata["selected_planned_red_light_cost"] == pytest.approx(
        6e-12
    )
    assert response.arrays["planned_red_light_cost"][3] == pytest.approx(6e-12)
    assert response.metadata["worker_latency_ms"]["dp_inference"] >= 0.0
    assert response.metadata["worker_latency_ms"]["atom_selector"] >= 0.0
    assert response.metadata["native_ranked_top1"] is False


def test_cli_freezes_fixed_dp_and_selector_hash_inputs(tmp_path) -> None:
    module = _worker()

    args = module.parse_args(
        [
            "--request-dir",
            str(tmp_path),
            "--operation",
            "source_probe",
            "--dp-repo",
            "/fixed/dp",
            "--checkpoint",
            "/fixed/checkpoint.pth",
            "--checkpoint-sha256",
            "1" * 64,
            "--args-json",
            "/fixed/args.json",
            "--args-json-sha256",
            "2" * 64,
            "--selector-root",
            "/fixed/selector",
            "--selector-root-sha256",
            "3" * 64,
            "--atom-scales",
            "/fixed/scales.json",
            "--atom-scales-sha256",
            "4" * 64,
            "--static-weights",
            "/fixed/weights.npy",
            "--static-weights-sha256",
            "5" * 64,
        ]
    )

    assert args.operation == "source_probe"
    assert module.FIXED_DP_HEAD == "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    assert module.NATIVE_RANKED_TOP1 is False
