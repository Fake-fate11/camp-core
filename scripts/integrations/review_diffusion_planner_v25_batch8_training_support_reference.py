"""Separate-role raw-byte review of the V25 training-support reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
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
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (  # noqa: E402
    _fixed_dp_red_cost,
    candidate_signal_source_available_mask,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    V22_SOURCE_VALID_SELECTION,
)


TRAINING = Path(
    "/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST"
)
TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST"
)
TRAINING_REVIEW_ROOT = (
    "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
POOL_COUNT = 1000
ROW_COUNT = 8000
ROW_FIELDS = tuple(
    [f"normalized_atom_{index:02d}" for index in range(14)]
    + ["score_static14d", "score_scene14d"]
)
POOL_FIELDS = (
    "margin_static14d",
    "margin_scene14d",
    "eligible_count_static14d",
    "eligible_count_scene14d",
)


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.ascontiguousarray(np.asarray(archive[name]))
            for name in archive.files
        }


def _interval(values: np.ndarray) -> dict[str, Any]:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if not np.isfinite(flat).all():
        return {
            "status": "evidence_missing",
            "expected_value_count": int(flat.size),
            "finite_value_count": int(np.isfinite(flat).sum()),
            "values_sha256": _digest(
                np.ascontiguousarray(flat).tobytes(order="C")
            ),
        }
    ordered = np.sort(flat, kind="stable")
    lower = int(math.ceil(0.005 * flat.size) - 1)
    upper = int(math.ceil(0.995 * flat.size) - 1)
    return {
        "status": "computed",
        "expected_value_count": int(flat.size),
        "finite_value_count": int(flat.size),
        "values_sha256": _digest(
            np.ascontiguousarray(flat).tobytes(order="C")
        ),
        "interval": {
            "count": int(flat.size),
            "q0_005_lower_index": lower,
            "q0_995_upper_index": upper,
            "q0_005_lower": float(ordered[lower]),
            "q0_995_upper": float(ordered[upper]),
            "interval_inclusive": True,
        },
    }


def _score(
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, int, float, int]:
    normalized = np.clip(
        np.asarray(atoms, dtype=np.float64)
        / np.asarray(scales, dtype=np.float64),
        0.0,
        10.0,
    )
    scores = normalized @ np.asarray(weights, dtype=np.float64)
    eligible = np.flatnonzero(mask)
    if eligible.size < 2:
        raise RuntimeError("review margin needs two eligible candidates")
    selected = int(eligible[np.argmin(scores[eligible])])
    ordered = np.sort(scores[eligible], kind="stable")
    return scores, selected, float(ordered[1] - ordered[0]), int(eligible.size)


def review(
    *,
    source: Path,
    source_root: str,
    preflight: Path,
    preflight_root: str,
    fixed_dp_repo: Path,
    output: Path,
) -> str:
    for path, root, label in (
        (source, source_root, "training-support raw reference"),
        (preflight, preflight_root, "training-support input preflight"),
        (TRAINING, TRAINING_ROOT, "accepted training"),
        (TRAINING_REVIEW, TRAINING_REVIEW_ROOT, "accepted training review"),
    ):
        verify_complete_seal(path, root, label=label)
    if output.exists():
        raise FileExistsError(output)
    report = _json(source / "report.json")
    manifest = _json(preflight / "manifest.json")
    receipts = [
        json.loads(line)
        for line in (source / "pool_receipts.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    ]
    cached = _arrays(source / "support_values.npz")
    if (
        len(receipts) != POOL_COUNT
        or manifest.get("selected_pool_count") != POOL_COUNT
        or report.get("pool_slot_count") != POOL_COUNT
        or report.get("formal_model_call_count") != POOL_COUNT
        or report.get("selector_receipt_count") != 2000
        or report.get("all_slots_retained") is not True
        or report.get("weighted_total_created") is not False
        or report.get("outcome_fields_read") != []
        or report.get("old_artifact_or_cas_written") is not False
    ):
        raise RuntimeError("review raw denominator/no-mutation boundary drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=TRAINING,
        training_root_sha256=TRAINING_ROOT,
        training_review_artifact=TRAINING_REVIEW,
        training_review_root_sha256=TRAINING_REVIEW_ROOT,
    )
    rebuilt_atoms = np.full((POOL_COUNT, 8, 14), np.nan, dtype=np.float64)
    rebuilt_static = np.full((POOL_COUNT, 8), np.nan, dtype=np.float64)
    rebuilt_scene = np.full((POOL_COUNT, 8), np.nan, dtype=np.float64)
    rebuilt_sm = np.zeros((POOL_COUNT, 8), dtype=np.bool_)
    rebuilt_cm = np.zeros((POOL_COUNT, 8), dtype=np.bool_)
    rebuilt_smargin = np.full(POOL_COUNT, np.nan, dtype=np.float64)
    rebuilt_cmargin = np.full(POOL_COUNT, np.nan, dtype=np.float64)
    rebuilt_se = np.full(POOL_COUNT, -1, dtype=np.int64)
    rebuilt_ce = np.full(POOL_COUNT, -1, dtype=np.int64)
    rebuilt_si = np.full(POOL_COUNT, -1, dtype=np.int64)
    rebuilt_ci = np.full(POOL_COUNT, -1, dtype=np.int64)
    rebuilt_complete = 0
    for ordinal, (entry, receipt) in enumerate(
        zip(manifest["entries"], receipts)
    ):
        payload = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        if (
            receipt.get("pool_ordinal") != ordinal
            or receipt.get("pool_id") != entry["pool_id"]
            or receipt.get("manifest_entry_sha256")
            != entry["manifest_entry_sha256"]
            or receipt.get("formal_model_call_count") != 1
            or receipt.get("selector_receipt_count") != 2
            or any(
                receipt.get(name) != 0
                for name in (
                    "post_pool_model_call_count",
                    "post_pool_dp_call_count",
                    "post_pool_latent_generation_count",
                    "post_pool_candidate_generation_count",
                )
            )
            or receipt.get("outcome_fields_read") != []
            or _digest(_bytes(payload)) != receipt.get("receipt_sha256")
        ):
            raise ValueError("review pool receipt binding drifted")
        model_output = source / "pool_slots" / entry["pool_id"].replace(
            ":", "_"
        ) / "model_output.npz"
        if not model_output.is_file():
            if receipt.get("status") != "failed_retained":
                raise ValueError("review missing output lacks retained failure")
            continue
        output_arrays = _arrays(model_output)
        candidate = output_arrays["candidate"]
        neighbor = output_arrays["neighbor"]
        row_sha = [_digest(row.tobytes(order="C")) for row in candidate]
        if (
            candidate.shape != (8, 80, 4)
            or neighbor.shape != (8, 32, 80, 4)
            or not np.isfinite(candidate).all()
            or not np.isfinite(neighbor).all()
            or receipt.get("candidate_tensor_sha256")
            != _digest(candidate.tobytes(order="C"))
            or receipt.get("neighbor_tensor_sha256")
            != _digest(neighbor.tobytes(order="C"))
            or receipt.get("candidate_row_sha256") != row_sha
        ):
            if receipt.get("status") != "failed_retained":
                raise ValueError("review invalid model output not retained as failure")
            continue
        causal = _arrays(
            preflight
            / "pools"
            / entry["pool_id"].replace(":", "_")
            / "causal_input.npz"
        )
        signal = _json(
            preflight
            / "pools"
            / entry["pool_id"].replace(":", "_")
            / "causal_signal_atom_input.json"
        )
        dt = float(
            (
                preflight
                / "pools"
                / entry["pool_id"].replace(":", "_")
                / "dt.txt"
            ).read_text("ascii")
        )
        signals = candidate_signal_source_available_mask(
            candidate, causal["route_lanes"]
        )
        red = _fixed_dp_red_cost(candidate, causal, fixed_dp_repo, dt)
        neighbor_valid = np.any(
            np.abs(causal["neighbor_agents_past"]) > 1e-8, axis=(1, 2)
        )
        materialized = materialize_canonical_14d(
            candidates=candidate,
            causal_input=causal,
            neighbor_predictions=neighbor,
            neighbor_valid_mask=neighbor_valid,
            signal_mask=signals,
            planned_red_light_cost=red,
            causal_signal_atom_input=signal,
            dt=dt,
            eligibility_policy=V22_SOURCE_VALID_SELECTION,
        )
        atom = np.asarray(materialized["atom_matrix"], dtype=np.float64)
        mask = np.asarray(materialized["source_valid_mask"])
        context = build_v25_raw_context(
            causal_input=causal,
            candidates=candidate,
            source_valid_mask=mask,
            causal_signal_atom_input=signal,
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
        scene_weights = np.asarray(
            assets.scene14d_weight_provider(context_payload)["weights"],
            dtype=np.float64,
        )
        ss, si, smargin, se = _score(
            atom, assets.atom_scales, assets.static14d_weights, mask
        )
        cs, ci, cmargin, ce = _score(
            atom, assets.atom_scales, scene_weights, mask
        )
        rebuilt_atoms[ordinal] = atom
        rebuilt_static[ordinal] = ss
        rebuilt_scene[ordinal] = cs
        rebuilt_sm[ordinal] = mask
        rebuilt_cm[ordinal] = mask
        rebuilt_smargin[ordinal] = smargin
        rebuilt_cmargin[ordinal] = cmargin
        rebuilt_se[ordinal] = se
        rebuilt_ce[ordinal] = ce
        rebuilt_si[ordinal] = si
        rebuilt_ci[ordinal] = ci
        rebuilt_complete += 1
    expected_cache = {
        "atoms": rebuilt_atoms,
        "static_scores": rebuilt_static,
        "scene_scores": rebuilt_scene,
        "static_masks": rebuilt_sm,
        "scene_masks": rebuilt_cm,
        "static_margin": rebuilt_smargin,
        "scene_margin": rebuilt_cmargin,
        "static_eligible": rebuilt_se,
        "scene_eligible": rebuilt_ce,
        "static_selected": rebuilt_si,
        "scene_selected": rebuilt_ci,
    }
    if set(cached) != set(expected_cache):
        raise ValueError("review support cache keyset drifted")
    for key, expected in expected_cache.items():
        actual = cached[key]
        if actual.dtype.kind == "f":
            equal = np.array_equal(actual, expected, equal_nan=True)
        else:
            equal = np.array_equal(actual, expected)
        if not equal:
            raise ValueError(f"review support cache drifted: {key}")
    row_values = {
        **{
            f"normalized_atom_{index:02d}": rebuilt_atoms[:, :, index]
            / float(assets.atom_scales[index])
            for index in range(14)
        },
        "score_static14d": rebuilt_static,
        "score_scene14d": rebuilt_scene,
    }
    pool_values = {
        "margin_static14d": rebuilt_smargin,
        "margin_scene14d": rebuilt_cmargin,
        "eligible_count_static14d": rebuilt_se.astype(np.float64),
        "eligible_count_scene14d": rebuilt_ce.astype(np.float64),
    }
    rebuilt_row_refs = {
        key: _interval(value) for key, value in row_values.items()
    }
    rebuilt_pool_refs = {
        key: _interval(value) for key, value in pool_values.items()
    }
    if (
        set(rebuilt_row_refs) != set(ROW_FIELDS)
        or set(rebuilt_pool_refs) != set(POOL_FIELDS)
        or report.get("row_field_references") != rebuilt_row_refs
        or report.get("pool_field_references") != rebuilt_pool_refs
        or report.get("successful_pool_count") != rebuilt_complete
        or report.get("failed_pool_count") != POOL_COUNT - rebuilt_complete
    ):
        raise ValueError("review support references drifted")
    review_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_reference_"
            "independent_raw_review_v1"
        ),
        "status": (
            "passed_independent_full_reference_review"
            if report["status"] == "passed_full_reference"
            else "passed_independent_failure_reference_review"
        ),
        "reviewed_source_root_sha256": source_root,
        "reviewed_preflight_root_sha256": preflight_root,
        "reviewed_pool_slot_count": POOL_COUNT,
        "reviewed_complete_pool_count": rebuilt_complete,
        "reviewed_candidate_row_count": ROW_COUNT,
        "reviewed_selector_receipt_count": 2000,
        "row_field_references": rebuilt_row_refs,
        "pool_field_references": rebuilt_pool_refs,
        "producer_status": report["status"],
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "old_artifact_or_cas_write_count": 0,
        "review_head": review_head,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_bytes(result))
        (staging / "HEADS.json").write_bytes(
            _bytes({"review_head": review_head, "fixed_dp_head": FIXED_DP_HEAD})
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging,
            label="V25 batch8 training-support independent raw review",
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 batch8 training-support independent raw review",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        review(
            source=args.source,
            source_root=args.source_root,
            preflight=args.preflight,
            preflight_root=args.preflight_root,
            fixed_dp_repo=args.fixed_dp_repo,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
