from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    canonical_score_atoms,
    project_candidates_to_route,
    validate_fixed_k8_candidate_tensor,
)

from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    BRIDGE_SCHEMA_VERSION,
    DP_OPERATIONAL_TOP1_NAME,
    DP_OPERATIONAL_TOP1_PROVENANCE,
    array_sha256,
    read_request,
    request_evidence,
    write_response,
)


_FULL_OUTPUT_SHAPE = (321, 80, 4)
_LATENT_SHAPE = (321, 81, 4)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
NATIVE_RANKED_TOP1 = False
_FIXED_SOURCE_HASHES = {
    "diffusion_planner/diffusion_planner/model/module/decoder.py": (
        "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
    ),
    "scenario_generation/tensor_converter.py": (
        "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
    ),
    "scenario_generation/simulate.py": (
        "de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e"
    ),
    "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py": (
        "3341028ca11f45e73b7b43ab49dbf38980711f422dccfdb2f816f301443a5f53"
    ),
}


def process_request(
    request_dir: str | Path,
    *,
    operation: str,
    infer_one: Callable[[np.ndarray], np.ndarray],
    atom_scales: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    planned_red_cost: Callable[[np.ndarray, Mapping[str, Any]], np.ndarray]
    | None = None,
    signal_mask: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None,
    materialize: Callable[..., Mapping[str, Any]] | None = None,
) -> None:
    directory = Path(request_dir)
    raw_metadata = json.loads((directory / "request.json").read_text("utf-8"))
    request = read_request(
        directory,
        expected_run_key=str(raw_metadata["run_key"]),
        expected_iteration_index=int(raw_metadata["iteration_index"]),
    )
    arm = str(request.metadata["arm"])
    if operation not in {"default_provenance", "plan_tick", "source_probe"}:
        raise ValueError("unsupported worker operation")
    if operation == "default_provenance" and arm != "dp_default":
        raise ValueError("default provenance requires the DP-default arm")
    if operation == "source_probe" and arm != "camp":
        raise ValueError("source probe requires the CAMP arm")
    response_metadata: dict[str, object] = {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "arm": arm,
        "run_key": request.metadata["run_key"],
        "iteration_index": request.metadata["iteration_index"],
        "operation": operation,
        "native_ranked_top1": False,
        "speed_source_policy": request.metadata["speed_source_policy"],
        "request_evidence": request_evidence(request.metadata),
    }
    if arm == "dp_default":
        response_metadata.update(
            {
                "baseline_name": DP_OPERATIONAL_TOP1_NAME,
                "baseline_provenance": DP_OPERATIONAL_TOP1_PROVENANCE,
            }
        )
    if arm == "dp_default":
        inference_start = time.perf_counter_ns()
        default, _ = run_fixed_dp_default(infer_one)
        inference_ms = (time.perf_counter_ns() - inference_start) / 1e6
        if operation == "default_provenance":
            reference, _ = run_fixed_dp_default(infer_one)
            evidence = verify_default_equivalence(default, reference)
            arrays = {
                "selected_trajectory": default,
                "default_trajectory": default,
                "independent_reference_trajectory": reference,
            }
            response_metadata.update(evidence)
        else:
            if request.metadata["speed_source_policy"] == CANDIDATE_LOCAL_EXACT_SPEED:
                projection = project_candidates_to_route(
                    default[None, ...],
                    request.arrays["route_lanes"],
                    request.arrays["route_lanes_speed_limit"],
                    request.arrays["route_lanes_has_speed_limit"],
                    speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
                )
                if not bool(projection["route_speed_source_eligible_mask"][0]):
                    response_metadata.update(
                        {
                            "status": "failed",
                            "failure_reason": (
                                "dp_default_route_speed_source_ineligible"
                            ),
                            "worker_latency_ms": {
                                "dp_inference": inference_ms,
                                "atom_selector": 0.0,
                            },
                        }
                    )
                    write_response(directory, {}, response_metadata)
                    return
            if planned_red_cost is None:
                raise ValueError("DP-default plan_tick requires planned-red evidence")
            red_cost = _planned_red_cost(
                planned_red_cost(default[None, ...], request.arrays), 1
            )
            arrays = {"selected_trajectory": default}
            response_metadata.update(
                {
                    "selected_planned_red_light_cost": float(red_cost[0]),
                    "planned_red_source": "fixed_dp_red_cost_v18",
                    "worker_latency_ms": {
                        "dp_inference": inference_ms,
                        "atom_selector": 0.0,
                    },
                }
            )
        response_metadata.update(
            {
                "status": "ok",
                "selected_trajectory_sha256": array_sha256(default),
            }
        )
        write_response(directory, arrays, response_metadata)
        return

    if operation == "source_probe":
        candidates, _ = run_fixed_dp_candidates(
            infer_one,
            np.random.default_rng(int(request.metadata["tick_seed"])),
            noise_scale=1.0,
        )
        projection = project_candidates_to_route(
            candidates,
            request.arrays["route_lanes"],
            request.arrays["route_lanes_speed_limit"],
            request.arrays["route_lanes_has_speed_limit"],
            speed_source_policy=str(request.metadata["speed_source_policy"]),
        )
        source_mask = np.asarray(
            projection["route_speed_source_eligible_mask"], dtype=bool
        )
        digest = array_sha256(candidates)
        response_metadata.update(
            {
                "status": "ok",
                "candidate_sha256_before": digest,
                "candidate_sha256_after": digest,
                "dp_default_source_complete": bool(source_mask[0]),
                "eligible_candidate_count": int(source_mask.sum()),
            }
        )
        write_response(
            directory,
            {
                "candidates": candidates,
                "route_speed_source_eligible_mask": source_mask,
            },
            response_metadata,
        )
        return

    if any(
        value is None
        for value in (atom_scales, weights, planned_red_cost, signal_mask, materialize)
    ):
        raise ValueError("CAMP plan_tick dependencies are incomplete")
    inference_start = time.perf_counter_ns()
    candidates, neighbor_predictions = run_fixed_dp_candidates(
        infer_one,
        np.random.default_rng(int(request.metadata["tick_seed"])),
        noise_scale=1.0,
    )
    inference_ms = (time.perf_counter_ns() - inference_start) / 1e6
    selector_start = time.perf_counter_ns()
    raw_neighbors = request.arrays["neighbor_agents_past"]
    neighbor_valid = np.any(np.abs(raw_neighbors) > 1e-8, axis=(1, 2))
    signals = np.asarray(
        signal_mask(candidates, request.arrays["route_lanes"]), dtype=bool
    )
    red_cost = _planned_red_cost(planned_red_cost(candidates, request.arrays), 8)
    materialized = materialize(
        candidates=candidates,
        causal_input=request.arrays,
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid,
        signal_mask=signals,
        planned_red_light_cost=red_cost,
        dt=0.1,
        speed_source_policy=str(request.metadata["speed_source_policy"]),
    )
    selection = select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=np.asarray(atom_scales),
        weights=np.asarray(weights),
    )
    response_metadata.update(
        {
            "status": selection["status"],
            "candidate_sha256_before": selection["candidate_sha256_before"],
            "candidate_sha256_after": selection["candidate_sha256_after"],
            "candidate_reasons": selection["candidate_reasons"],
            "planned_red_source": "fixed_dp_red_cost_v18",
            "worker_latency_ms": {
                "dp_inference": inference_ms,
                "atom_selector": (time.perf_counter_ns() - selector_start) / 1e6,
            },
        }
    )
    physical = np.asarray(selection["physical_feasible_mask"], dtype=bool)
    arrays = {
        "candidates": candidates,
        "physical_feasible_mask": physical,
        "planned_red_light_cost": red_cost,
    }
    if selection["status"] == "failed":
        response_metadata["failure_reason"] = selection["failure_reason"]
    else:
        selected = np.asarray(selection["selected_trajectory"], dtype=np.float32)
        response_metadata["selected_trajectory_sha256"] = array_sha256(selected)
        response_metadata["selected_planned_red_light_cost"] = float(
            red_cost[int(selection["selected_index"])]
        )
        arrays.update(
            {
                "neighbor_predictions": neighbor_predictions,
                "neighbor_valid_mask": neighbor_valid,
                "signal_mask": signals,
                "atom_matrix": np.asarray(materialized["atom_matrix"], dtype=np.float64),
                "selected_index": np.array(selection["selected_index"], dtype=np.int64),
                "selected_trajectory": selected,
            }
        )
    write_response(directory, arrays, response_metadata)


def _planned_red_cost(value: Any, count: int) -> np.ndarray:
    costs = np.asarray(value, dtype=np.float64)
    if costs.shape != (count,) or not np.isfinite(costs).all() or np.any(costs < 0.0):
        raise ValueError(f"planned-red cost must be finite nonnegative [{count}]")
    return costs


def run_fixed_dp_default(
    infer_one: Callable[[np.ndarray], np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    output = _validated_inference(
        infer_one(np.zeros(_LATENT_SHAPE, dtype=np.float32))
    )
    return output[0].copy(), output[1:33].copy()


def run_fixed_dp_candidates(
    infer_one: Callable[[np.ndarray], np.ndarray],
    rng: np.random.Generator,
    *,
    noise_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    if not np.isfinite(noise_scale) or noise_scale < 0.0:
        raise ValueError("noise_scale must be finite and nonnegative")
    outputs = []
    for index in range(8):
        latent = np.zeros(_LATENT_SHAPE, dtype=np.float32)
        if index:
            latent = (
                rng.standard_normal(_LATENT_SHAPE).astype(np.float32)
                * float(noise_scale)
            )
        outputs.append(_validated_inference(infer_one(latent))[:33])
    stacked = np.stack(outputs)
    return stacked[:, 0].copy(), stacked[:, 1:33].copy()


def verify_default_equivalence(
    default_output: np.ndarray, candidate0: np.ndarray
) -> dict[str, object]:
    default = _trajectory(default_output, "default output")
    reference = _trajectory(candidate0, "candidate 0")
    difference = float(np.max(np.abs(default.astype(np.float64) - reference)))
    default_sha = array_sha256(default)
    reference_sha = array_sha256(reference)
    if not np.array_equal(default, reference) or default_sha != reference_sha:
        raise ValueError("DP-default deterministic/MAP equivalence failed")
    return {
        "elementwise_equal": True,
        "max_abs_difference": difference,
        "default_output_sha256": default_sha,
        "candidate0_sha256": reference_sha,
        "baseline_name": DP_OPERATIONAL_TOP1_NAME,
        "baseline_provenance": DP_OPERATIONAL_TOP1_PROVENANCE,
        "native_ranked_top1": False,
    }


def select_camp_candidate(
    *,
    candidates: np.ndarray,
    materialized: Mapping[str, Any],
    atom_scales: np.ndarray,
    weights: np.ndarray,
    eligibility_mask_name: str = "physical_feasible_mask",
    simplex_nonnegative_atol: float = 0.0,
) -> dict[str, object]:
    trajectories = validate_fixed_k8_candidate_tensor(candidates)
    scales = np.asarray(atom_scales, dtype=np.float64)
    coefficients = np.asarray(weights, dtype=np.float64)
    if (
        scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
    ):
        raise ValueError("atom scales must be finite positive [14]")
    if (
        not np.isfinite(simplex_nonnegative_atol)
        or simplex_nonnegative_atol < 0.0
    ):
        raise ValueError("simplex nonnegative tolerance must be finite and nonnegative")
    if (
        coefficients.shape != (14,)
        or not np.isfinite(coefficients).all()
        or np.any(coefficients < -float(simplex_nonnegative_atol))
        or not np.isclose(coefficients.sum(), 1.0, rtol=0.0, atol=1e-8)
    ):
        raise ValueError("weights must be a nonnegative simplex [14]")

    if eligibility_mask_name not in {
        "physical_feasible_mask",
        "source_valid_mask",
    }:
        raise ValueError("unknown eligibility mask")
    before = array_sha256(trajectories)
    def strict_mask(key: str) -> np.ndarray:
        if key not in materialized:
            raise ValueError(f"materialized {key} is required")
        raw = np.asarray(materialized[key])
        if raw.dtype != np.bool_:
            raise ValueError(f"{key} must contain strict booleans")
        if raw.shape != (8,):
            raise ValueError(f"{key} must have shape [8]")
        return raw.copy()

    physical = strict_mask("physical_feasible_mask")
    source_valid = strict_mask("source_valid_mask")
    if np.any(physical & ~source_valid):
        raise ValueError("physical feasible mask must be a subset of source valid")
    if eligibility_mask_name == "source_valid_mask" and not source_valid.any():
        raise ValueError("source_valid candidate set is empty; fallback is forbidden")
    eligible = (
        physical
        if eligibility_mask_name == "physical_feasible_mask"
        else source_valid
    )
    reasons = [list(value) for value in materialized["candidate_reasons"]]
    if len(reasons) != 8:
        raise ValueError("candidate reasons must contain all K records")
    common: dict[str, object] = {
        "candidate_sha256_before": before,
        "candidate_sha256_after": array_sha256(trajectories),
        "candidate_reasons": reasons,
        "physical_feasible_mask": physical.copy(),
        "source_valid_mask": source_valid.copy(),
        "all_k_high_risk": bool(source_valid.all() and not physical.any()),
        "eligibility_mask_name": eligibility_mask_name,
        "score_contract": "score_k=clip(a_k/s,0,10)^T w",
        "tie_break_contract": "lowest_eligible_candidate_index",
        "native_ranked_top1": False,
    }
    if not bool(materialized.get("canonical_eligible")) or not eligible.any():
        return {
            **common,
            "status": "failed",
            "failure_reason": str(
                materialized.get("exclusion_reason")
                or (
                    "all_candidates_physically_infeasible"
                    if eligibility_mask_name == "physical_feasible_mask"
                    else "all_candidates_source_invalid"
                )
            ),
        }

    atoms = np.asarray(materialized["atom_matrix"], dtype=np.float64)
    normalized, scores = canonical_score_atoms(
        atoms,
        scales,
        coefficients,
        simplex_nonnegative_atol=simplex_nonnegative_atol,
    )
    masked_scores = np.where(eligible, scores, np.inf)
    selected = int(np.argmin(masked_scores))
    after = array_sha256(trajectories)
    if after != before:
        raise ValueError("candidate tensor mutated during CAMP selection")
    return {
        **common,
        "candidate_sha256_after": after,
        "status": "ok",
        "normalized_atoms": normalized,
        "scores": scores,
        "selected_index": selected,
        "selected_trajectory": trajectories[selected].copy(),
    }


def _validated_inference(value: np.ndarray) -> np.ndarray:
    output = np.asarray(value)
    if output.shape != _FULL_OUTPUT_SHAPE or output.dtype != np.float32:
        raise ValueError("fixed-DP inference must return float32 [321,80,4]")
    if not np.isfinite(output).all():
        raise ValueError("fixed-DP inference output must be finite")
    return output


def _trajectory(value: np.ndarray, name: str) -> np.ndarray:
    output = np.asarray(value)
    if output.shape != (80, 4) or output.dtype != np.float32:
        raise ValueError(f"{name} must be float32 [80,4]")
    if not np.isfinite(output).all():
        raise ValueError(f"{name} must be finite")
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-dir", type=Path, required=True)
    parser.add_argument(
        "--operation",
        choices=("default_provenance", "plan_tick", "source_probe"),
        required=True,
    )
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--args-json", type=Path, required=True)
    parser.add_argument("--args-json-sha256", required=True)
    parser.add_argument("--selector-root", type=Path, required=True)
    parser.add_argument("--selector-root-sha256", required=True)
    parser.add_argument("--atom-scales", type=Path, required=True)
    parser.add_argument("--atom-scales-sha256", required=True)
    parser.add_argument("--static-weights", type=Path, required=True)
    parser.add_argument("--static-weights-sha256", required=True)
    parser.add_argument("--device", default="cuda")
    return parser.parse_args(argv)


def _real_infer_one(context: Mapping[str, Any], causal_input: Mapping[str, Any]):
    from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
        prepare_causal_arrays,
    )

    torch = context["torch"]
    device = context["device"]
    arrays = prepare_causal_arrays(causal_input)
    tensors = {
        key: torch.as_tensor(value).unsqueeze(0).to(device)
        for key, value in arrays.items()
    }
    tensors["ego_agent_past"] = context["heading_to_cos_sin"](
        tensors["ego_agent_past"]
    )
    tensors["goal_pose"] = context["heading_to_cos_sin"](tensors["goal_pose"])
    normalized = context["config"].observation_normalizer(tensors)
    normalized["delay"] = torch.zeros(1, dtype=torch.float32, device=device)
    model = context["model"]

    def infer(latent: np.ndarray) -> np.ndarray:
        original_fn = model.decoder._guidance_fn
        original_scale = model.decoder._guidance_scale
        model.decoder._guidance_fn = None
        model.decoder._guidance_scale = 0.5
        normalized["sampled_trajectories"] = torch.from_numpy(latent).unsqueeze(0).to(
            device
        )
        try:
            with torch.no_grad():
                _, output = model(normalized)
        finally:
            model.decoder._guidance_fn = original_fn
            model.decoder._guidance_scale = original_scale
        return output["prediction"][0].detach().cpu().numpy().astype(np.float32)

    return infer


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha(path: Path, expected: str, name: str) -> None:
    if _sha256(path) != expected:
        raise ValueError(f"{name} SHA256 mismatch")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from camp_core.integrations.diffusion_planner import load_dp_camp_atom_scales
    from camp_core.integrations.diffusion_planner_causal_atoms import (
        materialize_canonical_14d,
    )
    from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
        _fixed_dp_red_cost,
        _load_context,
        _verify_fixed_dp_repo,
        candidate_signal_source_available_mask,
    )

    if _verify_fixed_dp_repo(args.dp_repo) != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    for relative, expected in _FIXED_SOURCE_HASHES.items():
        _require_sha(args.dp_repo / relative, expected, relative)
    _require_sha(args.checkpoint, args.checkpoint_sha256, "checkpoint")
    _require_sha(args.args_json, args.args_json_sha256, "args JSON")
    _require_sha(
        args.selector_root / "SHA256SUMS",
        args.selector_root_sha256,
        "selector root",
    )
    _require_sha(args.atom_scales, args.atom_scales_sha256, "atom scales")
    _require_sha(args.static_weights, args.static_weights_sha256, "static weights")

    raw = json.loads((args.request_dir / "request.json").read_text("utf-8"))
    request = read_request(
        args.request_dir,
        expected_run_key=str(raw["run_key"]),
        expected_iteration_index=int(raw["iteration_index"]),
    )
    if request.metadata["arm"] == "camp" and request.metadata.get(
        "selector_hashes"
    ) != [
        args.selector_root_sha256,
        args.atom_scales_sha256,
        args.static_weights_sha256,
    ]:
        raise ValueError("request selector hashes do not match frozen artifacts")
    context = _load_context(
        args.dp_repo, args.checkpoint, args.args_json, args.device
    )
    infer_one = _real_infer_one(context, request.arrays)
    if request.metadata["arm"] == "camp" and args.operation == "source_probe":
        process_request(
            args.request_dir,
            operation=args.operation,
            infer_one=infer_one,
        )
    elif request.metadata["arm"] == "camp":
        scales = load_dp_camp_atom_scales(args.atom_scales)
        weights = np.load(args.static_weights, allow_pickle=False)
        process_request(
            args.request_dir,
            operation=args.operation,
            infer_one=infer_one,
            atom_scales=scales,
            weights=weights,
            planned_red_cost=lambda candidates, causal: _fixed_dp_red_cost(
                candidates, causal, args.dp_repo, 0.1
            ),
            signal_mask=candidate_signal_source_available_mask,
            materialize=materialize_canonical_14d,
        )
    else:
        process_request(
            args.request_dir,
            operation=args.operation,
            infer_one=infer_one,
            planned_red_cost=lambda candidates, causal: _fixed_dp_red_cost(
                candidates, causal, args.dp_repo, 0.1
            ),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
