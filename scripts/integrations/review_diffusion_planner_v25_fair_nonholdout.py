"""Independently review the V25 fair nonholdout validation artifact.

This reviewer deliberately does not import the fair-validation producer,
selector, pool-generator, contract producer, or their threshold tables.  It
reconstructs pool bindings, score/mask decisions, immutable-row selection,
adaptation equivalence, call counts, denominators and latency provenance from
the sealed report and numeric preimages using reviewer-local literals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
import sys

for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
ATOL = 1e-5
RTOL = 1e-5


def _array_sha256(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype.hasobject:
        raise ValueError("object arrays are forbidden")
    return hashlib.sha256(array.tobytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _plain_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _selected(
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    source_mask: np.ndarray,
) -> tuple[np.ndarray, int]:
    atoms = np.asarray(atoms, dtype=np.float64)
    scales = np.asarray(scales, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    mask = np.asarray(source_mask)
    if (
        atoms.shape != (8, 14)
        or scales.shape != (14,)
        or weights.shape != (14,)
        or mask.shape != (8,)
        or mask.dtype != np.bool_
        or not np.isfinite(atoms).all()
        or not np.isfinite(scales).all()
        or not np.isfinite(weights).all()
        or np.any(scales <= 0.0)
        or np.any(weights < -1e-12)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-8)
        or not mask.any()
    ):
        raise ValueError("independent selector preimage contract failed")
    scores = np.clip(atoms / scales, 0.0, 10.0) @ weights
    return scores, int(np.argmin(np.where(mask, scores, np.inf)))


def _review_selector_receipt(
    *,
    tick: int,
    candidates: np.ndarray,
    atoms: np.ndarray,
    source_mask: np.ndarray,
    scales: np.ndarray,
    static_weights: np.ndarray,
    receipt: Mapping[str, Any],
) -> dict[str, int]:
    row = _plain_object(receipt, f"replay receipt {tick}")
    candidate_sha = _array_sha256(candidates)
    row_hashes = [_array_sha256(candidates[index]) for index in range(8)]
    if (
        row.get("generator_name") != GENERATOR_NAME
        or row.get("candidate_tensor_sha256_before") != candidate_sha
        or row.get("candidate_tensor_sha256_after") != candidate_sha
        or row.get("candidate_row_sha256") != row_hashes
        or row.get("primary_pool_model_call_count") != 1
        or row.get("default_output_sha256") != row_hashes[0]
    ):
        raise ValueError("independent pool/tensor binding reconstruction failed")
    pool_id = _canonical_sha256(
        {
            "generator": GENERATOR_NAME,
            "input_sha256": row["input_sha256"],
            "model_sha256": row["zero_call_receipt"]["model_sha256"],
            "candidate_tensor_sha256": candidate_sha,
            "tick_index": tick,
        }
    )
    zero = _plain_object(row["zero_call_receipt"], "zero-call receipt")
    if (
        row.get("pool_id") != pool_id
        or zero.get("pool_id") != pool_id
        or zero.get("candidate_tensor_sha256_before") != candidate_sha
        or zero.get("candidate_tensor_sha256_after") != candidate_sha
        or zero.get("input_sha256") != row.get("input_sha256")
        or zero.get("model_sha256") != zero.get("checkpoint_sha256")
        or any(
            zero.get(name) != 0
            for name in (
                "dp_or_model_calls_after_pool",
                "latent_replacements_after_pool",
                "candidate_generations_after_pool",
            )
        )
    ):
        raise ValueError("independent zero-call/pool-id reconstruction failed")
    selectors = _plain_object(row["real_selector_receipts"], "selector receipts")
    if set(selectors) != set(ARMS):
        raise ValueError("real selector arm inventory drifted")
    baseline = _plain_object(selectors["pool_matched_candidate0"], "baseline")
    if (
        baseline.get("status") != "ok"
        or baseline.get("selected_index") != 0
        or baseline.get("selected_row_sha256") != row_hashes[0]
        or baseline.get("baseline_rule") != "frozen_row0"
        or baseline.get("scores") is not None
    ):
        raise ValueError("independent row0 baseline reconstruction failed")
    chosen: dict[str, int] = {}
    for arm, weights in (
        ("Static14D", static_weights),
        (
            "Scene14D",
            np.asarray(row["materialized_summary"]["scene_weights"], dtype=np.float64),
        ),
    ):
        produced = _plain_object(selectors[arm], arm)
        scores, selected = _selected(atoms, scales, weights, source_mask)
        if (
            produced.get("status") != "ok"
            or produced.get("selected_index") != selected
            or produced.get("selected_row_sha256") != row_hashes[selected]
            or not np.allclose(
                np.asarray(produced.get("scores"), dtype=np.float64),
                scores,
                rtol=0.0,
                atol=1e-12,
            )
            or produced.get("source_valid_mask") != source_mask.tolist()
        ):
            raise ValueError(f"independent {arm} score/mask/selection failed")
        chosen[arm] = selected
    return chosen


def review_payload(
    report: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> dict[str, Any]:
    """Reviewer-local reconstruction used by both CLI and adversarial tests."""

    value = _plain_object(report, "validation report")
    blocked = (
        value.get("status") == "blocked_fair_nonholdout_engineering_validation"
    )
    passed = (
        value.get("status") == "passed_fair_nonholdout_engineering_validation"
    )
    if not (blocked or passed):
        raise ValueError("independent validation terminal status drifted")
    expected_arrays = {
        "primary_candidates",
        "sequential_candidates",
        "primary_neighbors",
        "sequential_neighbors",
        "primary_atoms",
        "sequential_atoms",
        "primary_source_masks",
        "sequential_source_masks",
        "primary_physical_masks",
        "sequential_physical_masks",
        "atom_scales",
        "static_weights",
    }
    if passed:
        expected_arrays.update(
            {
                "closed_loop_candidate0_candidates",
                "closed_loop_static14d_candidates",
                "closed_loop_static14d_atoms",
                "closed_loop_static14d_source_masks",
                "closed_loop_scene14d_candidates",
                "closed_loop_scene14d_atoms",
                "closed_loop_scene14d_source_masks",
            }
        )
    if set(arrays) != expected_arrays:
        raise ValueError("independent numeric preimage inventory drifted")
    primary = np.asarray(arrays["primary_candidates"])
    sequential = np.asarray(arrays["sequential_candidates"])
    primary_neighbors = np.asarray(arrays["primary_neighbors"])
    sequential_neighbors = np.asarray(arrays["sequential_neighbors"])
    atoms = np.asarray(arrays["primary_atoms"])
    sequential_atoms = np.asarray(arrays["sequential_atoms"])
    source_masks = np.asarray(arrays["primary_source_masks"])
    sequential_masks = np.asarray(arrays["sequential_source_masks"])
    physical_masks = np.asarray(arrays["primary_physical_masks"])
    sequential_physical_masks = np.asarray(arrays["sequential_physical_masks"])
    scales = np.asarray(arrays["atom_scales"])
    static_weights = np.asarray(arrays["static_weights"])
    if (
        primary.shape != (16, 8, 80, 4)
        or sequential.shape != primary.shape
        or primary_neighbors.shape != (16, 8, 32, 80, 4)
        or sequential_neighbors.shape != primary_neighbors.shape
        or atoms.shape != (16, 8, 14)
        or sequential_atoms.shape != atoms.shape
        or source_masks.shape != (16, 8)
        or sequential_masks.shape != source_masks.shape
        or physical_masks.shape != source_masks.shape
        or sequential_physical_masks.shape != source_masks.shape
    ):
        raise ValueError("independent replay preimage shape accounting failed")
    replay = _plain_object(value.get("state_matched_replay"), "replay")
    receipts = replay.get("receipts")
    if (
        replay.get("status") != "passed"
        or replay.get("state_count") != 16
        or replay.get("authoritative_pool_count") != 16
        or replay.get("real_selector_execution") is not True
        or replay.get("structural_row0_probe_used_as_static_or_scene") is not False
        or type(receipts) is not list
        or len(receipts) != 16
    ):
        raise ValueError("independent replay denominator failed")
    primary_selected: list[dict[str, int]] = []
    equivalent_trajectory_rows = 0
    equivalent_neighbor_rows = 0
    substantive_drift_states = 0
    for tick, receipt in enumerate(receipts):
        chosen = _review_selector_receipt(
            tick=tick,
            candidates=primary[tick],
            atoms=atoms[tick],
            source_mask=source_masks[tick],
            scales=scales,
            static_weights=static_weights,
            receipt=receipt,
        )
        primary_selected.append(chosen)
        adaptation = _plain_object(receipt["adaptation"], "adaptation")
        trajectory_ok = [
            bool(
                np.allclose(
                    primary[tick, row],
                    sequential[tick, row],
                    atol=ATOL,
                    rtol=RTOL,
                )
            )
            for row in range(8)
        ]
        neighbor_ok = [
            bool(
                np.allclose(
                    primary_neighbors[tick, row],
                    sequential_neighbors[tick, row],
                    atol=ATOL,
                    rtol=RTOL,
                )
            )
            for row in range(8)
        ]
        mask_equal = bool(
            np.array_equal(source_masks[tick], sequential_masks[tick])
            and np.array_equal(
                physical_masks[tick], sequential_physical_masks[tick]
            )
        )
        selected_equal: dict[str, bool] = {}
        sequential_summary = _plain_object(
            adaptation["sequential"], "sequential summary"
        )
        sequential_scene = np.asarray(
            sequential_summary["scene_weights"], dtype=np.float64
        )
        for arm, weights in (
            ("Static14D", static_weights),
            ("Scene14D", sequential_scene),
        ):
            _scores, sequential_selected = _selected(
                sequential_atoms[tick],
                scales,
                weights,
                sequential_masks[tick],
            )
            selected_equal[arm] = sequential_selected == chosen[arm]
        expected_substantive = bool(
            adaptation.get("repeat_exact_equal") is not True
            or not all(trajectory_ok)
            or not all(neighbor_ok)
            or not mask_equal
            or not all(selected_equal.values())
        )
        if (
            type(adaptation.get("repeat_exact_equal")) is not bool
            or adaptation.get("trajectory_within_tolerance") != trajectory_ok
            or adaptation.get("neighbor_within_tolerance") != neighbor_ok
            or adaptation.get("source_and_eligibility_masks_equal")
            is not mask_equal
            or adaptation.get("selected_index_equal") != selected_equal
            or adaptation.get("substantive_drift") is not expected_substantive
        ):
            raise ValueError("independent adaptation reconstruction failed")
        equivalent_trajectory_rows += sum(trajectory_ok)
        equivalent_neighbor_rows += sum(neighbor_ok)
        substantive_drift_states += int(expected_substantive)
    adaptation_report = _plain_object(
        value.get("pool_distribution_adaptation_audit"), "adaptation report"
    )
    if (
        adaptation_report.get("status")
        != ("substantive_drift" if blocked else "passed")
        or adaptation_report.get("state_count") != 16
        or adaptation_report.get("trajectory_row_denominator") != 128
        or adaptation_report.get("neighbor_row_denominator") != 128
        or adaptation_report.get("trajectory_equivalent_row_count")
        != equivalent_trajectory_rows
        or adaptation_report.get("neighbor_equivalent_row_count")
        != equivalent_neighbor_rows
        or adaptation_report.get("substantive_drift_state_count")
        != substantive_drift_states
        or adaptation_report.get("possible_training_pool_adaptation_required")
        is not blocked
        or adaptation_report.get("training_executed") is not False
    ):
        raise ValueError("independent adaptation aggregate failed")
    closed = _plain_object(value.get("compute_matched_closed_loop"), "closed loop")
    runs = closed.get("runs")
    if type(runs) is not list:
        raise ValueError("independent closed-loop arm denominator failed")
    closed_ticks = 0
    if blocked:
        if (
            runs != []
            or closed.get("entry_conditions_passed") is not False
            or closed.get("arm_run_denominator") != 3
            or closed.get("planned_tick_denominator") != 192
            or closed.get("terminal_arm_run_count") != 0
            or closed.get("complete_arm_run_count") != 0
            or closed.get("retained_terminal_failure_count") != 0
            or closed.get("complete_case_shrinkage_used") is not False
        ):
            raise ValueError("hard-stop closed-loop exclusion accounting failed")
    elif [row.get("arm") for row in runs] != list(ARMS):
        raise ValueError("independent closed-loop arm inventory failed")
    for run in runs:
        arm = run["arm"]
        key = {
            "pool_matched_candidate0": "candidate0",
            "Static14D": "static14d",
            "Scene14D": "scene14d",
        }[arm]
        candidates = np.asarray(arrays[f"closed_loop_{key}_candidates"])
        ticks = run["native_receipt"]["ticks"]
        selector_receipts = run.get("selector_receipts")
        if (
            run.get("status") != "complete"
            or run.get("tick_denominator") != 64
            or candidates.shape != (64, 8, 80, 4)
            or len(ticks) != 64
            or type(selector_receipts) is not list
            or len(selector_receipts) != 64
        ):
            raise ValueError("independent closed-loop tick denominator failed")
        for tick, native_tick in enumerate(ticks):
            receipt = run["native_receipt"]["ticks"][tick]
            selector_receipt = _plain_object(
                selector_receipts[tick], "closed-loop selector receipt"
            )
            zero = _plain_object(
                selector_receipt["zero_call_receipt"],
                "closed-loop zero-call receipt",
            )
            if any(
                zero.get(name) != 0
                for name in (
                    "dp_or_model_calls_after_pool",
                    "latent_replacements_after_pool",
                    "candidate_generations_after_pool",
                )
            ):
                raise ValueError("closed-loop selector made a forbidden call")
            selected = int(selector_receipt["selected_index"])
            produced = _plain_object(
                selector_receipt["real_selector_receipts"][arm],
                "closed-loop arm selector",
            )
            if arm == "pool_matched_candidate0":
                if (
                    selected != 0
                    or produced.get("selected_index") != 0
                    or produced.get("scores") is not None
                    or selector_receipt["latency_ms"].get("atoms") is not None
                    or selector_receipt["latency_ms"].get("context") is not None
                    or selector_receipt["latency_ms"].get("weights") is not None
                    or selector_receipt["latency_ms"].get("selector_incremental")
                    is not None
                ):
                    raise ValueError("closed-loop row0/n-a latency reconstruction failed")
            else:
                atoms_key = f"closed_loop_{key}_atoms"
                masks_key = f"closed_loop_{key}_source_masks"
                closed_atoms = np.asarray(arrays[atoms_key])[tick]
                closed_mask = np.asarray(arrays[masks_key])[tick]
                weights = (
                    static_weights
                    if arm == "Static14D"
                    else np.asarray(
                        selector_receipt["materialized_summary"]["scene_weights"],
                        dtype=np.float64,
                    )
                )
                scores, rebuilt_selected = _selected(
                    closed_atoms, scales, weights, closed_mask
                )
                if (
                    selected != rebuilt_selected
                    or produced.get("selected_index") != rebuilt_selected
                    or not np.allclose(
                        np.asarray(produced.get("scores"), dtype=np.float64),
                        scores,
                        rtol=0.0,
                        atol=1e-12,
                    )
                ):
                    raise ValueError("closed-loop score/mask/selection reconstruction failed")
            if (
                receipt["selected_trajectory_sha256"]
                != _array_sha256(candidates[tick, selected])
                or receipt["default_output_sha256"]
                != _array_sha256(candidates[tick, 0])
                or "total_planning" not in receipt["latency_ms"]
            ):
                raise ValueError("closed-loop selected row or latency provenance failed")
        endpoint = _plain_object(
            run.get("evaluation_v2_endpoint_vector"), "endpoint vector"
        )
        if (
            set(endpoint.get("endpoints", {}))
            != {
                "collision",
                "dynamic_proximity",
                "road_containment",
                "certified_red_crossing",
                "speed",
                "route",
                "goal",
                "vehicle_body_planar_kinematic_proxy",
                "latency",
            }
            or endpoint.get("source_class") != "development_nonholdout"
            or endpoint.get("source_receipt_sha256")
            != _canonical_sha256(run["native_receipt"])
        ):
            raise ValueError("closed-loop endpoint provenance/claim drifted")
        closed_ticks += len(ticks)
    if passed and (
        closed.get("entry_conditions_passed") is not True
        or closed.get("arm_run_denominator") != 3
        or closed.get("planned_tick_denominator") != 192
        or closed.get("terminal_arm_run_count") != 3
        or closed.get("complete_arm_run_count") != 3
        or closed.get("retained_terminal_failure_count") != 0
        or closed.get("complete_case_shrinkage_used") is not False
        or closed_ticks != 192
    ):
        raise ValueError("independent closed-loop aggregate accounting failed")
    boundaries = _plain_object(value.get("boundaries"), "boundaries")
    hard_stop = _plain_object(value.get("hard_stop"), "hard stop")
    if (
        value.get("schema_version")
        != "camp_dp_v25_fair_nonholdout_validation_v1"
        or value.get("generator_name") != GENERATOR_NAME
        or value.get("fixed_dp_head") != FIXED_DP_HEAD
        or boundaries.get("development_nonholdout_only") is not True
        or boundaries.get("fresh_or_holdout_accessed") is not False
        or boundaries.get("fresh_or_b4_raw_outcome_read") is not False
        or boundaries.get("training_or_retraining_executed") is not False
        or boundaries.get("confirmatory_effect_claim_authorized") is not False
        or boundaries.get("ultra_submission_authorized") is not False
        or hard_stop
        != {
            "selector_failure": False,
            "post_pool_forbidden_call": False,
            "adaptation_substantive_drift": blocked,
        }
    ):
        raise ValueError("independent validation boundary oracle failed")
    return {
        "replay_state_count": 16,
        "trajectory_row_denominator": 128,
        "trajectory_equivalent_row_count": equivalent_trajectory_rows,
        "neighbor_row_denominator": 128,
        "neighbor_equivalent_row_count": equivalent_neighbor_rows,
        "substantive_drift_state_count": substantive_drift_states,
        "hard_stop_confirmed": blocked,
        "closed_loop_arm_count": len(runs),
        "closed_loop_tick_denominator": closed_ticks,
        "real_selector_receipt_count": 16 * 3 + closed_ticks,
        "post_pool_forbidden_call_count": 0,
        "candidate_tensor_mutation_count": 0,
    }


def review(
    *,
    source: Path,
    source_root: str,
    output: Path,
    fixed_dp_repo: Path,
) -> str:
    source = source.resolve()
    verify_complete_seal(source, source_root, label="fair nonholdout validation")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if (
        _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted before independent review")
    report = json.loads((source / "report.json").read_text("utf-8"))
    with np.load(source / "replay_preimages.npz", allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    reconstructed = review_payload(report, arrays)
    for label in ("contract", "contract_review", "training", "training_review"):
        binding = _plain_object(report["authority"][label], label)
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"fair nonholdout {label}",
        )
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        review_report = {
            "schema_version": (
                "camp_dp_v25_fair_nonholdout_independent_result_review_v1"
            ),
            "status": (
                "passed_independent_fair_nonholdout_hard_stop_review"
                if report.get("status")
                == "blocked_fair_nonholdout_engineering_validation"
                else "passed_independent_fair_nonholdout_result_review"
            ),
            "source": {"path": str(source), "root_sha256": source_root},
            "review_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewer_imported_producer_selector_pool_or_fairness_oracle": False,
            "reviewer_local_literal_score_mask_selection_rebuilt": True,
            "reviewer_local_pool_and_zero_call_bindings_rebuilt": True,
            "reviewer_local_adaptation_equivalence_rebuilt": True,
            "reviewer_local_denominator_failure_latency_provenance_rebuilt": True,
            "reconstructed": reconstructed,
            "fresh_or_holdout_accessed": False,
            "fresh_or_b4_raw_outcome_read": False,
            "fresh_arm_or_dp_k8_rerun": False,
            "training_or_retraining_executed": False,
            "old_artifact_or_cas_written": False,
            "confirmatory_effect_claim_authorized": False,
            "ultra_submission_authorized": False,
        }
        payload = (
            json.dumps(
                review_report,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        (staging / "report.json").write_bytes(payload)
        (staging / "HEADS.json").write_text(
            json.dumps(
                {
                    "review_head": review_report["review_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="ascii",
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 fair nonholdout independent result review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 fair nonholdout independent result review"
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
