"""Independent literal review of the additive fair-pool adaptation summary."""

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
SOURCE_ROOT = "29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd"
ATOL = 1e-5
RTOL = 1e-5
STATE_COUNT = 16
ROW_COUNT = 8
ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
ARMS = ("Static14D", "Scene14D")
PRIORITY = (
    "nonfinite_or_nondiverse",
    "repeat_nondeterminism",
    "trajectory_tolerance",
    "neighbor_tolerance",
    "mask",
    "Static14D_flip",
    "Scene14D_flip",
    "post_pool_call",
    "tensor_mutation",
    "no_failure",
)
ARRAY_NAMES = frozenset(
    {
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
)


def _plain(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _array_sha256(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype.hasobject:
        raise ValueError("object arrays are forbidden")
    return hashlib.sha256(array.tobytes()).hexdigest()


def _scores(
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, int]:
    atoms = np.asarray(atoms, dtype=np.float64)
    scales = np.asarray(scales, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    mask = np.asarray(mask)
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
        raise ValueError("reviewer-local score preimage failed")
    values = np.clip(atoms / scales, 0.0, 10.0) @ weights
    return values, int(np.argmin(np.where(mask, values, np.inf)))


def _allclose_rows(left: np.ndarray, right: np.ndarray) -> list[bool]:
    return [
        bool(np.allclose(left[row], right[row], atol=ATOL, rtol=RTOL))
        for row in range(8)
    ]


def _k8(candidates: np.ndarray, neighbors: np.ndarray) -> dict[str, Any]:
    candidate_finite = [
        bool(np.isfinite(candidates[row]).all()) for row in range(8)
    ]
    neighbor_finite = [bool(np.isfinite(neighbors[row]).all()) for row in range(8)]
    row_hashes = [_array_sha256(candidates[row]) for row in range(8)]
    unique = len(set(row_hashes))
    return {
        "candidate_row_finite": candidate_finite,
        "neighbor_row_finite": neighbor_finite,
        "candidate_row_sha256": row_hashes,
        "unique_candidate_row_count": unique,
        "finite": all(candidate_finite) and all(neighbor_finite),
        "diverse": unique == 8,
        "valid": all(candidate_finite) and all(neighbor_finite) and unique == 8,
    }


def review_summary(
    source_report: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    produced_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild every requested value without importing the producer oracle."""

    report = _plain(source_report, "source report")
    produced = _plain(produced_summary, "produced summary")
    if (
        report.get("schema_version")
        != "camp_dp_v25_fair_nonholdout_validation_v1"
        or report.get("status")
        != "blocked_fair_nonholdout_engineering_validation"
        or produced.get("schema_version")
        != "camp_dp_v25_fair_nonholdout_adaptation_summary_v1"
        or produced.get("status")
        != "sealed_additive_adaptation_summary_hard_stop_preserved"
        or produced.get("state_count") != 16
        or produced.get("candidate_row_denominator") != 128
        or produced.get("atom_value_denominator") != 1792
        or produced.get("score_value_denominator_per_arm") != 128
        or produced.get("atom_names") != list(ATOM_NAMES)
        or produced.get("frozen_tolerance") != {"atol": ATOL, "rtol": RTOL}
    ):
        raise ValueError("summary top-level literal contract failed")
    if set(arrays) != ARRAY_NAMES:
        raise ValueError("reviewer-local numeric inventory drifted")
    a = {name: np.asarray(value) for name, value in arrays.items()}
    expected_shapes = {
        "primary_candidates": (16, 8, 80, 4),
        "sequential_candidates": (16, 8, 80, 4),
        "primary_neighbors": (16, 8, 32, 80, 4),
        "sequential_neighbors": (16, 8, 32, 80, 4),
        "primary_atoms": (16, 8, 14),
        "sequential_atoms": (16, 8, 14),
        "primary_source_masks": (16, 8),
        "sequential_source_masks": (16, 8),
        "primary_physical_masks": (16, 8),
        "sequential_physical_masks": (16, 8),
        "atom_scales": (14,),
        "static_weights": (14,),
    }
    if any(a[name].shape != shape for name, shape in expected_shapes.items()):
        raise ValueError("reviewer-local numeric shape drifted")
    for name in (
        "primary_source_masks",
        "sequential_source_masks",
        "primary_physical_masks",
        "sequential_physical_masks",
    ):
        if a[name].dtype != np.bool_:
            raise ValueError("reviewer-local mask dtype drifted")
    receipts = report["state_matched_replay"]["receipts"]
    states = produced.get("state_summaries")
    if type(receipts) is not list or len(receipts) != 16:
        raise ValueError("source state denominator drifted")
    if type(states) is not list or len(states) != 16:
        raise ValueError("summary state denominator drifted")
    scales = np.asarray(a["atom_scales"], dtype=np.float64)
    static_weights = np.asarray(a["static_weights"], dtype=np.float64)
    taxonomy = {name: 0 for name in PRIORITY}
    indicator_states = {name: 0 for name in PRIORITY if name != "no_failure"}
    indicator_rows = {
        "nonfinite_or_nondiverse": 0,
        "trajectory_tolerance": 0,
        "neighbor_tolerance": 0,
        "mask": 0,
    }
    atom_exact_total = 0
    atom_max = 0.0
    per_atom = [
        {"atom_index": index, "atom_name": name, "exact_count": 0, "max_abs_diff": 0.0}
        for index, name in enumerate(ATOM_NAMES)
    ]
    score_exact = {arm: 0 for arm in ARMS}
    score_max = {arm: 0.0 for arm in ARMS}
    flips = {arm: 0 for arm in ARMS}
    valid_states = {"primary": 0, "sequential": 0}
    for index, (receipt_raw, state_raw) in enumerate(zip(receipts, states)):
        receipt = _plain(receipt_raw, "source receipt")
        state = _plain(state_raw, "summary state")
        adaptation = _plain(receipt.get("adaptation"), "source adaptation")
        sequential_summary = _plain(
            adaptation.get("sequential"), "source sequential summary"
        )
        pa = np.asarray(a["primary_atoms"][index], dtype=np.float64)
        sa = np.asarray(a["sequential_atoms"][index], dtype=np.float64)
        signed_atoms = pa - sa
        abs_atoms = np.abs(signed_atoms)
        exact_atoms = signed_atoms == 0.0
        expected_atom_rows = [
            {
                "row_index": row,
                "exact_equal_atom_count": int(np.count_nonzero(exact_atoms[row])),
                "nonexact_atom_count": int(14 - np.count_nonzero(exact_atoms[row])),
                "max_abs_diff": float(np.max(abs_atoms[row])),
                "per_atom_signed_diff": signed_atoms[row].tolist(),
                "per_atom_abs_diff": abs_atoms[row].tolist(),
                "per_atom_exact_equal": exact_atoms[row].tolist(),
            }
            for row in range(8)
        ]
        atom_exact_total += int(np.count_nonzero(exact_atoms))
        atom_max = max(atom_max, float(np.max(abs_atoms)))
        for atom_index, row in enumerate(per_atom):
            row["exact_count"] += int(np.count_nonzero(exact_atoms[:, atom_index]))
            row["max_abs_diff"] = max(
                float(row["max_abs_diff"]),
                float(np.max(abs_atoms[:, atom_index])),
            )
        ps = np.asarray(a["primary_source_masks"][index])
        ss = np.asarray(a["sequential_source_masks"][index])
        pp = np.asarray(a["primary_physical_masks"][index])
        sp = np.asarray(a["sequential_physical_masks"][index])
        source_diff = np.flatnonzero(ps != ss).tolist()
        physical_diff = np.flatnonzero(pp != sp).tolist()
        mask_rows = sorted(set(source_diff + physical_diff))
        expected_score_rows = {}
        state_flips = {}
        for arm in ARMS:
            if arm == "Static14D":
                pw = sw = static_weights
            else:
                pw = np.asarray(
                    receipt["materialized_summary"]["scene_weights"],
                    dtype=np.float64,
                )
                sw = np.asarray(
                    sequential_summary["scene_weights"], dtype=np.float64
                )
            primary_scores, primary_selected = _scores(pa, scales, pw, ps)
            sequential_scores, sequential_selected = _scores(sa, scales, sw, ss)
            source_arm = _plain(
                receipt["real_selector_receipts"][arm], "source selector receipt"
            )
            if (
                source_arm.get("selected_index") != primary_selected
                or not np.allclose(
                    np.asarray(source_arm.get("scores"), dtype=np.float64),
                    primary_scores,
                    rtol=0.0,
                    atol=1e-12,
                )
            ):
                raise ValueError("source selector binding drifted")
            signed_scores = primary_scores - sequential_scores
            abs_scores = np.abs(signed_scores)
            exact_scores = signed_scores == 0.0
            flip = primary_selected != sequential_selected
            score_exact[arm] += int(np.count_nonzero(exact_scores))
            score_max[arm] = max(score_max[arm], float(np.max(abs_scores)))
            flips[arm] += int(flip)
            state_flips[arm] = flip
            expected_score_rows[arm] = {
                "primary_scores": primary_scores.tolist(),
                "sequential_scores": sequential_scores.tolist(),
                "signed_diff": signed_scores.tolist(),
                "abs_diff": abs_scores.tolist(),
                "exact_equal": exact_scores.tolist(),
                "max_abs_diff": float(np.max(abs_scores)),
                "primary_selected_index": primary_selected,
                "sequential_selected_index": sequential_selected,
                "selected_index_flip": flip,
                "primary_source_mask": ps.tolist(),
                "sequential_source_mask": ss.tolist(),
                "primary_physical_mask": pp.tolist(),
                "sequential_physical_mask": sp.tolist(),
            }
        primary_k8 = _k8(a["primary_candidates"][index], a["primary_neighbors"][index])
        sequential_k8 = _k8(
            a["sequential_candidates"][index], a["sequential_neighbors"][index]
        )
        valid_states["primary"] += int(primary_k8["valid"])
        valid_states["sequential"] += int(sequential_k8["valid"])
        trajectory_ok = _allclose_rows(
            a["primary_candidates"][index], a["sequential_candidates"][index]
        )
        neighbor_ok = _allclose_rows(
            a["primary_neighbors"][index], a["sequential_neighbors"][index]
        )
        zero = _plain(receipt.get("zero_call_receipt"), "zero-call receipt")
        post_calls = sum(
            int(zero.get(name, -1))
            for name in (
                "dp_or_model_calls_after_pool",
                "latent_replacements_after_pool",
                "candidate_generations_after_pool",
            )
        )
        mutated = (
            receipt.get("candidate_tensor_sha256_before")
            != receipt.get("candidate_tensor_sha256_after")
        )
        indicators = {
            "nonfinite_or_nondiverse": not (
                primary_k8["valid"] and sequential_k8["valid"]
            ),
            "repeat_nondeterminism": adaptation.get("repeat_exact_equal") is not True,
            "trajectory_tolerance": not all(trajectory_ok),
            "neighbor_tolerance": not all(neighbor_ok),
            "mask": bool(mask_rows),
            "Static14D_flip": state_flips["Static14D"],
            "Scene14D_flip": state_flips["Scene14D"],
            "post_pool_call": post_calls != 0,
            "tensor_mutation": mutated,
        }
        primary_class = next(
            (name for name in PRIORITY if name != "no_failure" and indicators[name]),
            "no_failure",
        )
        taxonomy[primary_class] += 1
        for name, present in indicators.items():
            indicator_states[name] += int(present)
        indicator_rows["nonfinite_or_nondiverse"] += sum(
            not value
            for value in (
                primary_k8["candidate_row_finite"]
                + primary_k8["neighbor_row_finite"]
                + sequential_k8["candidate_row_finite"]
                + sequential_k8["neighbor_row_finite"]
            )
        )
        indicator_rows["trajectory_tolerance"] += sum(not x for x in trajectory_ok)
        indicator_rows["neighbor_tolerance"] += sum(not x for x in neighbor_ok)
        indicator_rows["mask"] += len(mask_rows)
        expected_state = {
            "state_index": index,
            "tick_index": receipt.get("tick_index"),
            "state_sha256": receipt.get("state_sha256"),
            "pool_id": receipt.get("pool_id"),
            "atom_differences": expected_atom_rows,
            "score_differences": expected_score_rows,
            "mask_differences": {
                "source_row_indices": source_diff,
                "physical_row_indices": physical_diff,
                "any_difference": bool(mask_rows),
            },
            "k8_validity": {
                "primary": primary_k8,
                "sequential": sequential_k8,
            },
            "trajectory_within_tolerance": trajectory_ok,
            "neighbor_within_tolerance": neighbor_ok,
            "post_pool_forbidden_call_count": post_calls,
            "candidate_tensor_mutated": mutated,
            "failure_indicators": indicators,
            "primary_failure_class": primary_class,
        }
        if state != expected_state:
            raise ValueError(f"summary state {index} differs from literal reconstruction")
    expected_aggregates = {
        "atom_exact_equal_count": atom_exact_total,
        "atom_nonexact_count": 1792 - atom_exact_total,
        "atom_global_max_abs_diff": atom_max,
        "per_atom": per_atom,
        "score_exact_equal_count": score_exact,
        "score_nonexact_count": {arm: 128 - score_exact[arm] for arm in ARMS},
        "score_global_max_abs_diff": score_max,
        "selected_index_flip_state_count": flips,
        "mask_difference_state_count": indicator_states["mask"],
        "k8_valid_state_count": valid_states,
        "primary_failure_taxonomy_priority": list(PRIORITY),
        "primary_failure_taxonomy_state_count": taxonomy,
        "failure_indicator_state_count": indicator_states,
        "failure_indicator_row_count": indicator_rows,
    }
    if produced.get("aggregates") != expected_aggregates:
        raise ValueError("summary aggregate differs from literal reconstruction")
    interpretation = produced.get("interpretation")
    if interpretation != {
        "atom_and_score_difference_threshold_added": False,
        "atom_and_score_differences_are_exact_and_absolute_descriptive": True,
        "hard_stop_preserved": True,
        "neighbor_equivalent_rows": 114,
        "neighbor_row_denominator": 128,
        "substantive_drift_state_count": 9,
        "closed_loop_started": False,
        "closed_loop_arm_count": 0,
        "closed_loop_tick_count": 0,
        "possible_adaptation_or_ood_risk": True,
        "retraining_decision": "undecided_not_authorized",
    }:
        raise ValueError("summary interpretation boundary drifted")
    return {
        "state_count": 16,
        "candidate_row_denominator": 128,
        "atom_value_denominator": 1792,
        "score_value_denominator_per_arm": 128,
        "atom_exact_equal_count": atom_exact_total,
        "atom_global_max_abs_diff": atom_max,
        "score_exact_equal_count": score_exact,
        "score_global_max_abs_diff": score_max,
        "selected_index_flip_state_count": flips,
        "mask_difference_state_count": indicator_states["mask"],
        "k8_valid_state_count": valid_states,
        "primary_failure_taxonomy_state_count": taxonomy,
        "failure_indicator_state_count": indicator_states,
        "failure_indicator_row_count": indicator_rows,
        "hard_stop_preserved": True,
    }


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


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def review(
    *,
    source: Path,
    source_root: str,
    summary: Path,
    summary_root: str,
    output: Path,
    fixed_dp_repo: Path,
) -> str:
    if source_root != SOURCE_ROOT:
        raise ValueError("source root is not the accepted validation root")
    source = source.resolve()
    summary = summary.resolve()
    verify_complete_seal(source, source_root, label="fair validation")
    verify_complete_seal(summary, summary_root, label="fair adaptation summary")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if (
        _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted")
    source_report = json.loads((source / "report.json").read_text("utf-8"))
    artifact = json.loads((summary / "report.json").read_text("utf-8"))
    with np.load(source / "replay_preimages.npz", allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    if (
        artifact.get("schema_version")
        != "camp_dp_v25_fair_nonholdout_adaptation_summary_artifact_v1"
        or artifact.get("status")
        != "passed_additive_adaptation_summary_hard_stop_preserved"
        or artifact.get("fixed_dp_head") != FIXED_DP_HEAD
        or artifact.get("source", {}).get("path") != str(source)
        or artifact.get("source", {}).get("root_sha256") != source_root
    ):
        raise ValueError("adaptation summary artifact binding drifted")
    reconstructed = review_summary(source_report, arrays, artifact["summary"])
    boundaries = artifact.get("boundaries")
    if boundaries != {
        "source_files_read": ["report.json", "replay_preimages.npz"],
        "model_pool_selector_or_closed_loop_invoked": False,
        "fresh_or_holdout_accessed": False,
        "fresh_or_b4_raw_outcome_read": False,
        "old_artifact_or_cas_written": False,
        "training_or_retraining_executed": False,
        "threshold_or_scientific_contract_modified": False,
        "hard_stop_preserved": True,
        "confirmatory_effect_claim_authorized": False,
        "ultra_submission_authorized": False,
    }:
        raise ValueError("adaptation summary artifact boundary drifted")
    review_report = {
        "schema_version": (
            "camp_dp_v25_fair_nonholdout_adaptation_summary_independent_review_v1"
        ),
        "status": "passed_independent_additive_adaptation_summary_review",
        "review_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "source": {"path": str(source), "root_sha256": source_root},
        "summary": {"path": str(summary), "root_sha256": summary_root},
        "reviewer_imported_producer_fairness_selector_or_threshold_oracle": False,
        "reviewer_local_literal_atom_score_mask_k8_and_taxonomy_rebuilt": True,
        "reconstructed": reconstructed,
        "fresh_or_holdout_accessed": False,
        "model_pool_selector_closed_loop_or_training_invoked": False,
        "old_artifact_or_cas_written": False,
        "hard_stop_preserved": True,
        "confirmatory_effect_claim_authorized": False,
        "ultra_submission_authorized": False,
    }
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(review_report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "review_head": review_report["review_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "source_validation_root_sha256": source_root,
                    "adaptation_summary_root_sha256": summary_root,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 fair adaptation summary review")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 fair adaptation summary review"
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--summary-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
