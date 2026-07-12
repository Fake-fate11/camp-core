import importlib

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
    return latent[:, 1:].astype(np.float32, copy=True)


def _request(tmp_path, *, arm: str):
    arrays = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    arrays["version"] = np.array(1, dtype=np.int64)
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
        selector_hashes=("d" * 64, "e" * 64, "f" * 64)
        if arm == "camp"
        else None,
    )
    write_request(tmp_path, arrays, metadata)
    return metadata


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
    assert provenance["baseline_name"] == "DP-default deterministic/MAP baseline"
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
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    atoms = np.full((8, 14), 10.0, dtype=np.float64)
    atoms[0, 0] = -100.0
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
    assert result["score_contract"] == "score_k(w)=a_k^T w"
    assert result["native_ranked_top1"] is False


def test_selector_rejects_non_simplex_and_all_k_fails_closed() -> None:
    module = _worker()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
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


def test_process_camp_tick_writes_k8_selection_without_mutation(tmp_path) -> None:
    module = _worker()
    metadata = _request(tmp_path, arm="camp")

    def materialize(**kwargs):
        candidates = kwargs["candidates"]
        atoms = np.zeros((8, 14), dtype=np.float64)
        atoms[:, 0] = np.mean(np.abs(candidates[:, :, 0]), axis=1)
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
        planned_red_cost=lambda _candidates, _causal: np.zeros(8),
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
    assert response.metadata["native_ranked_top1"] is False


def test_cli_freezes_fixed_dp_and_selector_hash_inputs(tmp_path) -> None:
    module = _worker()

    args = module.parse_args(
        [
            "--request-dir",
            str(tmp_path),
            "--operation",
            "plan_tick",
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

    assert args.operation == "plan_tick"
    assert module.FIXED_DP_HEAD == "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    assert module.NATIVE_RANKED_TOP1 is False
