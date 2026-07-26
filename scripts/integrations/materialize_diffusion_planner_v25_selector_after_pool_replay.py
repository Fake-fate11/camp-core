"""Replay production Static14D/Scene14D selectors on 320 sealed pools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
for _path in (ROOT, PACKAGE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    materialize_canonical_14d,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    TRAINED_SIMPLEX_NONNEGATIVE_ATOL as RUNTIME_TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay import (  # noqa: E402
    CORRECTED_RAW_ROOT,
    EXACT_DIRS,
    FIXED_DP_HEAD,
    REPLAY_SCHEMA_VERSION,
    TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
    TRAINING_REVIEW_ROOT,
    TRAINING_ROOT,
    array_sha256,
    assert_python_runtime,
    assert_same_state_determinism,
    canonical_bytes,
    selection_from_preimages,
    sha256_bytes,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (  # noqa: E402
    _fixed_dp_red_cost,
    candidate_signal_source_available_mask,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (  # noqa: E402
    select_camp_candidate,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    V22_SOURCE_VALID_SELECTION,
)


AUTODL = Path("/root/autodl-tmp")
DP = AUTODL / "Diffusion-Planner"
PREFLIGHT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_replacement_preflight_v1_"
    "4c412870_e6579ca7"
)
PREFLIGHT_REVIEW = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_replacement_preflight_review_v1_"
    "4c412870_e6579ca7"
)
CORRECTED_RAW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_v1_dc76fbc8"
)
TRAINING = AUTODL / "camp_dp_v25_camp_training_863e28da_20260722T103219CST"
TRAINING_REVIEW = AUTODL / (
    "camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.array(archive[name], copy=True, order="C")
            for name in archive.files
        }


def _selection_receipt(
    *,
    arm: str,
    candidates: np.ndarray,
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
    production: Mapping[str, Any],
) -> dict[str, Any]:
    literal = selection_from_preimages(
        candidates=candidates,
        raw_atoms=atoms,
        scales=scales,
        weights=weights,
        eligibility_mask=mask,
        simplex_nonnegative_atol=TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
    )
    if (
        production.get("status") != "ok"
        or int(production["selected_index"]) != literal["selected_index"]
        or not np.array_equal(
            np.asarray(production["scores"], dtype=np.float64),
            np.asarray(literal["scores"], dtype=np.float64),
        )
        or not np.array_equal(
            np.asarray(production["normalized_atoms"], dtype=np.float64),
            np.asarray(literal["clipped_atoms"], dtype=np.float64),
        )
        or not np.array_equal(
            np.asarray(production["selected_trajectory"], dtype="<f4"),
            candidates[literal["selected_index"]],
        )
    ):
        raise RuntimeError(f"{arm} production selector/literal binding drifted")
    return {
        "arm": arm,
        **literal,
        "production_status": "ok",
        "production_eligibility_mask_name": production[
            "eligibility_mask_name"
        ],
        "production_score_contract": production["score_contract"],
        "production_tie_break_contract": production["tie_break_contract"],
    }


def materialize(
    *,
    repo: Path,
    implementation_head: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    preflight_root: str,
    preflight_review_root: str,
    output: Path,
) -> str:
    assert_python_runtime(
        executable=sys.executable,
        version_info=sys.version_info[:3],
        prefix=sys.prefix,
        expected_executable="/root/autodl-tmp/dp312_venv/bin/python",
        expected_prefix="/root/autodl-tmp/dp312_venv",
        expected_exact_version=(3, 12, 3),
    )
    if (
        RUNTIME_TRAINED_SIMPLEX_NONNEGATIVE_ATOL
        != TRAINED_SIMPLEX_NONNEGATIVE_ATOL
    ):
        raise RuntimeError("accepted runtime simplex tolerance authority drifted")
    if (
        output != Path(EXACT_DIRS["replay"])
        or output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main") != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(DP, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(DP, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("selector replay live authority drifted")
    for path, root_sha, label in (
        (contract_dir, contract_root, "selector replay contract"),
        (contract_review_dir, contract_review_root, "selector replay contract review"),
        (PREFLIGHT, preflight_root, "selector replay preflight"),
        (PREFLIGHT_REVIEW, preflight_review_root, "selector replay preflight review"),
        (CORRECTED_RAW, CORRECTED_RAW_ROOT, "corrected generator raw"),
        (TRAINING, TRAINING_ROOT, "accepted training"),
        (TRAINING_REVIEW, TRAINING_REVIEW_ROOT, "accepted training review"),
    ):
        verify_complete_seal(path, root_sha, label=label)
    preflight = _json(PREFLIGHT / "report.json")
    if (
        preflight.get("slot_count") != 320
        or len(preflight.get("slot_receipts", [])) != 320
        or preflight.get("model_dp_latent_candidate_generation_call_count") != 0
        or preflight.get("selector_call_count") != 0
    ):
        raise RuntimeError("selector replay preflight denominator drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=TRAINING,
        training_root_sha256=TRAINING_ROOT,
        training_review_artifact=TRAINING_REVIEW,
        training_review_root_sha256=TRAINING_REVIEW_ROOT,
    )
    no_signal_chain = _json(PREFLIGHT / "no_signal_chain.json")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    completed = 0
    hard_failure = False
    try:
        (staging / "slots").mkdir()
        receipts = []
        typed_failures = []
        for slot, binding in enumerate(preflight["slot_receipts"]):
            raw_run = CORRECTED_RAW / "runs" / f"{slot:03d}"
            candidate = np.fromfile(
                raw_run / "candidate.f32le", dtype="<f4"
            ).reshape(8, 80, 4)
            neighbor = np.fromfile(
                raw_run / "neighbor.f32le", dtype="<f4"
            ).reshape(8, 32, 80, 4)
            before_candidate = array_sha256(candidate)
            before_neighbor = array_sha256(neighbor)
            if (
                binding["slot"] != slot
                or before_candidate != binding["candidate_tensor_sha256"]
                or before_neighbor != binding["neighbor_tensor_sha256"]
                or len(set(binding["candidate_row_sha256"])) != 8
            ):
                hard_failure = True
                raise RuntimeError("sealed corrected tensor binding drifted")
            causal = _arrays(
                PREFLIGHT
                / preflight["state_receipts"][binding["state_index"]][
                    "causal_input_relpath"
                ]
            )
            runtime_signal = build_runtime_no_signal_receipt(
                no_signal_chain,
                scenario_id=no_signal_chain["scenario_id"],
                tick_index=binding["state_index"],
                decision_time_s=float(binding["state_index"]) * 0.1,
            )
            signal_input = build_no_signal_causal_atom_input(
                no_signal_chain, runtime_signal
            )
            slot_started = time.perf_counter_ns()
            failure = None
            selector_calls = 0
            try:
                atom_started = time.perf_counter_ns()
                signal_mask = candidate_signal_source_available_mask(
                    candidate, causal["route_lanes"]
                )
                red_cost = _fixed_dp_red_cost(candidate, causal, DP, 0.1)
                neighbor_valid = np.any(
                    np.abs(causal["neighbor_agents_past"]) > 1e-8,
                    axis=(1, 2),
                )
                materialized = materialize_canonical_14d(
                    candidates=candidate,
                    causal_input=causal,
                    neighbor_predictions=neighbor,
                    neighbor_valid_mask=neighbor_valid,
                    signal_mask=signal_mask,
                    planned_red_light_cost=red_cost,
                    causal_signal_atom_input=signal_input,
                    dt=0.1,
                    eligibility_policy=V22_SOURCE_VALID_SELECTION,
                )
                atom_ns = time.perf_counter_ns() - atom_started
                atoms = np.ascontiguousarray(
                    np.asarray(materialized["atom_matrix"], dtype=np.float64)
                )
                source_mask = np.ascontiguousarray(
                    np.asarray(materialized["source_valid_mask"], dtype=np.bool_)
                )
                physical_mask = np.ascontiguousarray(
                    np.asarray(
                        materialized["physical_feasible_mask"], dtype=np.bool_
                    )
                )
                static_started = time.perf_counter_ns()
                static = None
                static_failure = None
                try:
                    selector_calls += 1
                    static_prod = select_camp_candidate(
                        candidates=candidate,
                        materialized=materialized,
                        atom_scales=assets.atom_scales,
                        weights=assets.static14d_weights,
                        eligibility_mask_name="source_valid_mask",
                        simplex_nonnegative_atol=(
                            TRAINED_SIMPLEX_NONNEGATIVE_ATOL
                        ),
                    )
                    static = _selection_receipt(
                        arm="Static14D",
                        candidates=candidate,
                        atoms=atoms,
                        scales=assets.atom_scales,
                        weights=assets.static14d_weights,
                        mask=source_mask,
                        production=static_prod,
                    )
                except Exception as exc:
                    static_failure = {
                        "arm": "Static14D",
                        "taxonomy": "selector_replay_typed_failure_retained",
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                static_ns = time.perf_counter_ns() - static_started
                context_started = time.perf_counter_ns()
                context = build_v25_raw_context(
                    causal_input=causal,
                    candidates=candidate,
                    source_valid_mask=source_mask,
                    causal_signal_atom_input=signal_input,
                    v2i_signal_timing=None,
                )
                context_payload = {
                    "schema_version": CONTEXT_SCHEMA_VERSION,
                    "raw_context": context.as_dict(),
                    "source_complete": dict(
                        zip(RAW_FEATURE_NAMES, context.source_complete)
                    ),
                    "source_receipt": dict(context.source_receipt),
                }
                scene_weight_receipt = assets.scene14d_weight_provider(
                    context_payload
                )
                scene_weights = np.ascontiguousarray(
                    np.asarray(
                        scene_weight_receipt["weights"], dtype=np.float64
                    )
                )
                scene_phi = np.ascontiguousarray(
                    assets.scene14d_weight_provider.context_scaler.lift(
                        context.raw,
                        source_complete=np.asarray(
                            context.source_complete, dtype=np.bool_
                        ),
                    )
                )
                context_ns = time.perf_counter_ns() - context_started
                scene_started = time.perf_counter_ns()
                scene = None
                scene_failure = None
                try:
                    selector_calls += 1
                    scene_prod = select_camp_candidate(
                        candidates=candidate,
                        materialized=materialized,
                        atom_scales=assets.atom_scales,
                        weights=scene_weights,
                        eligibility_mask_name="source_valid_mask",
                        simplex_nonnegative_atol=(
                            TRAINED_SIMPLEX_NONNEGATIVE_ATOL
                        ),
                    )
                    scene = _selection_receipt(
                        arm="Scene14D",
                        candidates=candidate,
                        atoms=atoms,
                        scales=assets.atom_scales,
                        weights=scene_weights,
                        mask=source_mask,
                        production=scene_prod,
                    )
                except Exception as exc:
                    scene_failure = {
                        "arm": "Scene14D",
                        "taxonomy": "selector_replay_typed_failure_retained",
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                scene_ns = time.perf_counter_ns() - scene_started
                scaled = atoms / assets.atom_scales[None, :]
                clipped = np.clip(scaled, 0.0, 10.0)
                slot_dir = staging / "slots" / f"{slot:03d}"
                slot_dir.mkdir()
                np.savez(
                    slot_dir / "selector_preimage.npz",
                    raw_atoms=atoms,
                    scaled_atoms=scaled,
                    clipped_atoms=clipped,
                    atom_source_valid_mask=np.asarray(
                        materialized["atom_source_valid_mask"], dtype=np.bool_
                    ),
                    atom_applicable_mask=np.asarray(
                        materialized["atom_applicable_mask"], dtype=np.bool_
                    ),
                    source_valid_mask=source_mask,
                    physical_feasible_mask=physical_mask,
                    static_weights=assets.static14d_weights,
                    static_scores=(
                        np.asarray(static["scores"], dtype=np.float64)
                        if static is not None
                        else np.empty(0, dtype=np.float64)
                    ),
                    scene_context_raw=np.asarray(context.raw, dtype=np.float64),
                    scene_context_source_complete=np.asarray(
                        context.source_complete, dtype=np.bool_
                    ),
                    scene_phi=scene_phi,
                    scene_weights=scene_weights,
                    scene_scores=(
                        np.asarray(scene["scores"], dtype=np.float64)
                        if scene is not None
                        else np.empty(0, dtype=np.float64)
                    ),
                    static_selected_action=(
                        candidate[static["selected_index"]]
                        if static is not None
                        else np.empty((0, 4), dtype="<f4")
                    ),
                    scene_selected_action=(
                        candidate[scene["selected_index"]]
                        if scene is not None
                        else np.empty((0, 4), dtype="<f4")
                    ),
                    candidate0_action=candidate[0],
                )
                receipt = {
                    "schema_version": (
                        "camp_dp_v25_selector_after_pool_replay_"
                        "replacement_slot_v1"
                    ),
                    **{
                        key: binding[key]
                        for key in (
                            "slot",
                            "run_id",
                            "state_index",
                            "repeat_index",
                            "forward_id",
                            "pool_id",
                            "candidate_tensor_sha256",
                            "neighbor_tensor_sha256",
                            "candidate_row_sha256",
                        )
                    },
                    "candidate_tensor_sha256_before": before_candidate,
                    "candidate_tensor_sha256_after": array_sha256(candidate),
                    "neighbor_tensor_sha256_before": before_neighbor,
                    "neighbor_tensor_sha256_after": array_sha256(neighbor),
                    "candidate0": {
                        "selection_rule": "immutable_candidate_tensor_row0",
                        "selected_index": 0,
                        "selected_action_sha256": array_sha256(candidate[0]),
                    },
                    "atom_receipt_sha256": sha256_bytes(
                        np.ascontiguousarray(atoms).tobytes(order="C")
                    ),
                    "atom_availability": materialized["availability"],
                    "atom_source_valid_mask": np.asarray(
                        materialized["atom_source_valid_mask"], dtype=np.bool_
                    ).tolist(),
                    "atom_applicable_mask": np.asarray(
                        materialized["atom_applicable_mask"], dtype=np.bool_
                    ).tolist(),
                    "physical_feasible_mask": physical_mask.tolist(),
                    "context": context_payload,
                    "context_receipt_sha256": sha256_bytes(
                        canonical_bytes(context_payload)
                    ),
                    "scene_weight_receipt": scene_weight_receipt,
                    "static14d": static,
                    "scene14d": scene,
                    "arm_failures": [
                        value
                        for value in (static_failure, scene_failure)
                        if value is not None
                    ],
                    "latency_ns": {
                        "atoms": int(atom_ns),
                        "static_selector_increment": int(static_ns),
                        "scene_context_and_weights": int(context_ns),
                        "scene_selector_increment": int(scene_ns),
                        "end_to_end_replay": int(
                            time.perf_counter_ns() - slot_started
                        ),
                    },
                    "formal_model_call_count": 0,
                    "dp_call_count": 0,
                    "latent_generation_call_count": 0,
                    "candidate_generation_call_count": 0,
                    "selector_call_count": selector_calls,
                    "status": (
                        "computed"
                        if static_failure is None and scene_failure is None
                        else "typed_failure_retained"
                    ),
                    "failure": (
                        None
                        if static_failure is None and scene_failure is None
                        else {
                            "taxonomy": (
                                "selector_replay_arm_failure_retained"
                            ),
                            "failed_arms": [
                                value["arm"]
                                for value in (static_failure, scene_failure)
                                if value is not None
                            ],
                        }
                    ),
                }
                for arm_failure in receipt["arm_failures"]:
                    typed_failures.append(
                        {
                            "slot": slot,
                            "state_index": binding["state_index"],
                            "repeat_index": binding["repeat_index"],
                            **arm_failure,
                        }
                    )
            except Exception as exc:
                failure = {
                    "taxonomy": "selector_replay_typed_failure_retained",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
                typed_failures.append(
                    {
                        "slot": slot,
                        "state_index": binding["state_index"],
                        "repeat_index": binding["repeat_index"],
                        **failure,
                    }
                )
                receipt = {
                    "schema_version": (
                        "camp_dp_v25_selector_after_pool_replay_"
                        "replacement_slot_v1"
                    ),
                    **binding,
                    "candidate_tensor_sha256_before": before_candidate,
                    "candidate_tensor_sha256_after": array_sha256(candidate),
                    "neighbor_tensor_sha256_before": before_neighbor,
                    "neighbor_tensor_sha256_after": array_sha256(neighbor),
                    "formal_model_call_count": 0,
                    "dp_call_count": 0,
                    "latent_generation_call_count": 0,
                    "candidate_generation_call_count": 0,
                    "selector_call_count": selector_calls,
                    "status": "typed_failure_retained",
                    "failure": failure,
                }
            if (
                array_sha256(candidate) != before_candidate
                or array_sha256(neighbor) != before_neighbor
            ):
                hard_failure = True
                raise RuntimeError("selector replay mutated sealed tensor")
            receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
            receipt_dir = staging / "slots" / f"{slot:03d}"
            receipt_dir.mkdir(exist_ok=True)
            (receipt_dir / "receipt.json").write_bytes(canonical_bytes(receipt))
            receipts.append(receipt)
            completed += 1
        if completed != 320:
            hard_failure = True
            raise RuntimeError("selector replay full denominator not formed")
        by_state = {}
        for receipt in receipts:
            by_state.setdefault(receipt["state_index"], []).append(receipt)
        nondeterministic_states = []
        for state_index, rows in sorted(by_state.items()):
            try:
                assert_same_state_determinism(rows)
            except ValueError:
                nondeterministic_states.append(state_index)
        report = {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "status": (
                "PASS_runtime_selector_compatibility"
                if not typed_failures and not nondeterministic_states
                else "FULL_DENOMINATOR_WITH_TYPED_FAILURES"
            ),
            "implementation_head": implementation_head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "preflight_root_sha256": preflight_root,
            "preflight_review_root_sha256": preflight_review_root,
            "corrected_raw_root_sha256": CORRECTED_RAW_ROOT,
            "training_root_sha256": TRAINING_ROOT,
            "training_review_root_sha256": TRAINING_REVIEW_ROOT,
            "planned_slot_count": 320,
            "completed_slot_count": completed,
            "state_count": 64,
            "repeats_per_state": 5,
            "independent_unit": "state",
            "typed_failure_count": len(typed_failures),
            "typed_failures": typed_failures,
            "nondeterministic_state_count": len(nondeterministic_states),
            "nondeterministic_states": nondeterministic_states,
            "formal_model_call_count": 0,
            "dp_call_count": 0,
            "latent_generation_call_count": 0,
            "candidate_generation_call_count": 0,
            "selector_call_count": sum(
                int(receipt["selector_call_count"]) for receipt in receipts
            ),
            "candidate0_structural_receipt_count": 320,
            "tensor_mutation_count": 0,
            "fresh_or_holdout_outcome_read": False,
            "old_artifact_or_cas_write": False,
            "claim_authorized": False,
            "interpretation": (
                "sealed corrected pools runtime selector compatibility, "
                "same-pool immutability, zero-extra-call, and selection "
                "determinism only"
            ),
        }
        (staging / "report.json").write_bytes(canonical_bytes(report))
        with (staging / "receipts.jsonl").open(
            "w", encoding="ascii", newline="\n"
        ) as stream:
            for receipt in receipts:
                stream.write(canonical_bytes(receipt).decode("ascii"))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 selector-after-pool replay")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 selector-after-pool replay"
        )
        return root
    except BaseException:
        if completed == 0 and not hard_failure:
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract-dir", type=Path, default=Path(EXACT_DIRS["contract"]))
    parser.add_argument("--contract-root", required=True)
    parser.add_argument(
        "--contract-review-dir",
        type=Path,
        default=Path(EXACT_DIRS["contract_review"]),
    )
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--preflight-review-root", required=True)
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["replay"]))
    args = parser.parse_args()
    print(
        materialize(
            repo=args.repo,
            implementation_head=args.implementation_head,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            preflight_root=args.preflight_root,
            preflight_review_root=args.preflight_review_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
