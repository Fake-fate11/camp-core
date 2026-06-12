#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


LOG_NAME = "camp_selection_log.json"
EXACT_FIELDS = (
    "selected_index",
    "feasible_mask",
    "infeasibility_reasons",
    "used_fallback",
    "camp_fallback_mode",
    "atom_schema_version",
    "atom_names",
)
NUMERIC_FIELDS = (
    "scores",
    "selection_scores",
    "weights",
    "selection_weights",
    "atoms",
    "normalized_atoms",
    "selection_normalized_atoms",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _discover_logs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        raise FileNotFoundError(f"Replay root does not exist: {root}")
    return {
        str(path.parent.relative_to(root)): path
        for path in root.rglob(LOG_NAME)
    }


def _numeric_difference(
    baseline: Any,
    candidate: Any,
) -> tuple[bool, float, float, int]:
    lhs = np.asarray(baseline, dtype=np.float64)
    rhs = np.asarray(candidate, dtype=np.float64)

    exact = np.array_equal(lhs, rhs, equal_nan=True)
    finite_pair = np.isfinite(lhs) & np.isfinite(rhs)
    finite_diff = np.abs(lhs[finite_pair] - rhs[finite_pair])
    max_abs = float(np.max(finite_diff)) if finite_diff.size else 0.0

    denominator = np.maximum(
        np.abs(lhs[finite_pair]),
        np.abs(rhs[finite_pair]),
    )
    relative = np.divide(
        finite_diff,
        denominator,
        out=np.zeros_like(finite_diff),
        where=denominator > 0.0,
    )
    max_rel = float(np.max(relative)) if relative.size else 0.0
    nonexact = int(np.count_nonzero(lhs[finite_pair] != rhs[finite_pair]))

    nonfinite_equal = np.array_equal(
        lhs[~finite_pair],
        rhs[~finite_pair],
        equal_nan=True,
    )
    return exact and nonfinite_equal, max_abs, max_rel, nonexact


def compare_selector_log_roots(
    baseline_root: Path,
    candidate_root: Path,
    *,
    atol: float = 1e-12,
    rtol: float = 1e-12,
) -> dict[str, Any]:
    if atol < 0.0 or rtol < 0.0:
        raise ValueError("atol and rtol must be nonnegative.")

    baseline_logs = _discover_logs(baseline_root)
    candidate_logs = _discover_logs(candidate_root)
    baseline_keys = set(baseline_logs)
    candidate_keys = set(candidate_logs)
    if baseline_keys != candidate_keys:
        missing = sorted(baseline_keys - candidate_keys)
        unexpected = sorted(candidate_keys - baseline_keys)
        raise ValueError(
            "Replay log pairing mismatch: "
            f"missing={missing}, unexpected={unexpected}."
        )
    if not baseline_logs:
        raise ValueError("No CAMP selection logs were found.")

    exact_mismatches = {field: 0 for field in EXACT_FIELDS}
    numeric_mismatches = {field: 0 for field in NUMERIC_FIELDS}
    numeric_shape_mismatches = {field: 0 for field in NUMERIC_FIELDS}
    numeric_nonexact_entries = {field: 0 for field in NUMERIC_FIELDS}
    numeric_max_abs_diff = {field: 0.0 for field in NUMERIC_FIELDS}
    numeric_max_rel_diff = {field: 0.0 for field in NUMERIC_FIELDS}
    records = 0

    for key in sorted(baseline_logs):
        baseline_rows = _read_json(baseline_logs[key])
        candidate_rows = _read_json(candidate_logs[key])
        if not isinstance(baseline_rows, list) or not isinstance(
            candidate_rows, list
        ):
            raise ValueError(f"Selection log {key!r} must contain a JSON list.")
        if len(baseline_rows) != len(candidate_rows):
            raise ValueError(
                f"Selection log {key!r} has different record counts: "
                f"{len(baseline_rows)} != {len(candidate_rows)}."
            )

        for record_index, (baseline, candidate) in enumerate(
            zip(baseline_rows, candidate_rows)
        ):
            if not isinstance(baseline, dict) or not isinstance(candidate, dict):
                raise ValueError(
                    f"Selection log {key!r} record {record_index} must be an object."
                )
            records += 1
            for field in EXACT_FIELDS:
                if field not in baseline or field not in candidate:
                    raise ValueError(
                        f"Selection log {key!r} record {record_index} "
                        f"is missing exact field {field!r}."
                    )
                if baseline.get(field) != candidate.get(field):
                    exact_mismatches[field] += 1

            for field in NUMERIC_FIELDS:
                if field not in baseline or field not in candidate:
                    raise ValueError(
                        f"Selection log {key!r} record {record_index} "
                        f"is missing numeric field {field!r}."
                    )
                baseline_array = np.asarray(baseline[field], dtype=np.float64)
                candidate_array = np.asarray(candidate[field], dtype=np.float64)
                if baseline_array.shape != candidate_array.shape:
                    numeric_mismatches[field] += 1
                    numeric_shape_mismatches[field] += 1
                    continue
                exact, max_abs, max_rel, nonexact = _numeric_difference(
                    baseline_array,
                    candidate_array,
                )
                numeric_nonexact_entries[field] += nonexact
                numeric_max_abs_diff[field] = max(
                    numeric_max_abs_diff[field],
                    max_abs,
                )
                numeric_max_rel_diff[field] = max(
                    numeric_max_rel_diff[field],
                    max_rel,
                )
                if not exact and not np.allclose(
                    baseline_array,
                    candidate_array,
                    atol=atol,
                    rtol=rtol,
                    equal_nan=True,
                ):
                    numeric_mismatches[field] += 1

    equivalent = not any(exact_mismatches.values()) and not any(
        numeric_mismatches.values()
    )
    return {
        "audit": "diffusion_planner_selector_log_equivalence_v1",
        "baseline_root": str(baseline_root),
        "candidate_root": str(candidate_root),
        "paired_logs": len(baseline_logs),
        "records": records,
        "atol": atol,
        "rtol": rtol,
        "equivalent": equivalent,
        "exact_field_mismatches": exact_mismatches,
        "numeric_field_mismatches": numeric_mismatches,
        "numeric_shape_mismatches": numeric_shape_mismatches,
        "numeric_nonexact_entries": numeric_nonexact_entries,
        "numeric_max_abs_diff": numeric_max_abs_diff,
        "numeric_max_rel_diff": numeric_max_rel_diff,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit tick-level selector equivalence between two DP+CAMP replay trees."
        )
    )
    parser.add_argument("--baseline_root", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-12)
    parser.add_argument("--rtol", type=float, default=1e-12)
    parser.add_argument(
        "--require_equivalent",
        action="store_true",
        help="Exit with status 2 when the paired selector logs are not equivalent.",
    )
    args = parser.parse_args()

    report = compare_selector_log_roots(
        args.baseline_root,
        args.candidate_root,
        atol=args.atol,
        rtol=args.rtol,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    if args.require_equivalent and not report["equivalent"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
