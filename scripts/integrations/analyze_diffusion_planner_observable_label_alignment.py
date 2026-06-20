#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


READY_STATUS = "observable_label_alignment_ready_for_separability"
REJECT_STATUS = "observable_label_alignment_rejected"
FORMAL_SEED_STATUS = "observable_label_alignment_formal_seed_conflict"

FORBIDDEN_SEEDS = frozenset({11, 12, 13})
EPS = 1e-9

EXACT_FIELDS = (
    "selected_index",
    "feasible_mask",
    "infeasibility_reasons",
    "atom_names",
    "atom_schema_version",
    "used_fallback",
)
NUMERIC_FIELDS = (
    "atoms",
    "normalized_atoms",
    "scores",
    "selection_scores",
    "weights",
    "selection_weights",
    "candidate_step_reach",
    "candidate_dp_prior_deviation_cost",
    "candidate_horizon_union_planned_red_light_cost",
    "candidate_full_horizon_planned_red_light_cost",
    "candidate_red_stopping_margin_cost",
    "candidate_perfect_tracker_first_step_reach_m",
    "candidate_perfect_tracker_target_speed_mps",
    "candidate_perfect_tracker_jerk_magnitude_mps3",
    "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
)


@dataclass(frozen=True)
class PairSpec:
    run_id: str
    observable_rel: str
    label_rel: str


DEFAULT_PAIRS: tuple[PairSpec, ...] = (
    PairSpec(
        run_id="sample_tl_seed1_npc0_tlon",
        observable_rel="sample_tl_seed1_npc0_tlon/camp_selection_log.json",
        label_rel=(
            "sample_map_tl_route_59_to_86/seed_1/npc_0/spawn_0p3/"
            "tl_on/static/camp_selection_log.json"
        ),
    ),
    PairSpec(
        run_id="sample_tl_seed1_npc4_tlon",
        observable_rel="sample_tl_seed1_npc4_tlon/camp_selection_log.json",
        label_rel=(
            "sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/"
            "tl_on/static/camp_selection_log.json"
        ),
    ),
    PairSpec(
        run_id="sample_tl_seed1_npc4_tloff",
        observable_rel="sample_tl_seed1_npc4_tloff/camp_selection_log.json",
        label_rel=(
            "sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/"
            "tl_off/static/camp_selection_log.json"
        ),
    ),
    PairSpec(
        run_id="sample_normal_seed1_npc0_tloff",
        observable_rel="sample_normal_seed1_npc0_tloff/camp_selection_log.json",
        label_rel=(
            "sample_map_route_2_to_104/seed_1/npc_0/spawn_0p3/"
            "tl_off/static/camp_selection_log.json"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed alignment audit before joining no-leak observable "
            "descriptors to existing offline outcome labels. This script does "
            "not run DP, train CAMP, or change selection."
        )
    )
    parser.add_argument("--observable_root", type=Path, required=True)
    parser.add_argument("--label_root", type=Path, required=True)
    parser.add_argument("--records", type=int, default=12)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        observable_root=args.observable_root,
        label_root=args.label_root,
        records=args.records,
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    *,
    observable_root: Path,
    label_root: Path,
    records: int = 12,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    pair_specs: tuple[PairSpec, ...] = DEFAULT_PAIRS,
) -> dict[str, Any]:
    if records <= 0:
        raise ValueError("records must be positive.")
    pair_reports = [
        _pair_report(
            observable_root=observable_root,
            label_root=label_root,
            pair=pair,
            records=records,
        )
        for pair in pair_specs
    ]
    formal_seed_pairs = [
        pair["run_id"]
        for pair in pair_reports
        if pair["formal_seed_detected"]
    ]
    if fail_on_formal_seeds and formal_seed_pairs:
        raise ValueError(f"Formal seed records are forbidden: {formal_seed_pairs}")
    mismatch_records = sum(pair["records_with_mismatch"] for pair in pair_reports)
    missing_pairs = [pair for pair in pair_reports if not pair["paths_exist"]]
    missing_labels = sum(pair["missing_label_outcome_records"] for pair in pair_reports)
    missing_payloads = sum(pair["missing_observable_payload_records"] for pair in pair_reports)
    total_records = sum(pair["records_compared"] for pair in pair_reports)
    if formal_seed_pairs:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        authorized_next_work = None
    elif missing_pairs:
        status = REJECT_STATUS
        primary_gap = "missing_pair_paths"
        authorized_next_work = "predeclare_matched_observable_outcome_label_collection_plan_only"
    elif missing_labels:
        status = REJECT_STATUS
        primary_gap = "label_records_missing_candidate_outcomes"
        authorized_next_work = "predeclare_matched_observable_outcome_label_collection_plan_only"
    elif missing_payloads:
        status = REJECT_STATUS
        primary_gap = "observable_records_missing_payloads"
        authorized_next_work = None
    elif mismatch_records:
        status = REJECT_STATUS
        primary_gap = "observable_and_label_candidate_sets_not_aligned"
        authorized_next_work = "predeclare_matched_observable_outcome_label_collection_plan_only"
    else:
        status = READY_STATUS
        primary_gap = "no_gap_aligned_labels_available"
        authorized_next_work = "offline_observable_descriptor_separability_screen_only"
    return {
        "analysis": {
            "name": "dp_camp_observable_label_alignment_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_features": False,
            "future_outcome_labels_used_for_alignment_labels": True,
            "records_requested_per_pair": int(records),
            "exact_fields": list(EXACT_FIELDS),
            "numeric_fields": list(NUMERIC_FIELDS),
            "math_boundary": (
                "This audit only checks whether already logged current-tick "
                "observable descriptors can be joined to existing offline "
                "candidate outcome labels. Observable payload fields remain "
                "the only runtime descriptor source. Outcome labels are never "
                "used as features and are consulted only to prove label "
                "availability after candidate-set alignment. If alignment "
                "fails, no separability screen, selector change, replay "
                "promotion, retraining, or DP modification is authorized."
            ),
        },
        "inputs": {
            "observable_root": str(observable_root),
            "label_root": str(label_root),
            "pair_specs": [asdict(pair) for pair in pair_specs],
        },
        "counts": {
            "pairs": len(pair_reports),
            "records_compared": total_records,
            "records_with_mismatch": mismatch_records,
            "missing_label_outcome_records": missing_labels,
            "missing_observable_payload_records": missing_payloads,
            "formal_seed_pairs": len(formal_seed_pairs),
        },
        "pairs": pair_reports,
        "final_decision": {
            "status": status,
            "primary_gap": primary_gap,
            "aligned": status == READY_STATUS,
            "authorized_next_work": authorized_next_work,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _pair_report(
    *,
    observable_root: Path,
    label_root: Path,
    pair: PairSpec,
    records: int,
) -> dict[str, Any]:
    observable_path = observable_root / pair.observable_rel
    label_path = label_root / pair.label_rel
    paths_exist = observable_path.is_file() and label_path.is_file()
    report: dict[str, Any] = {
        "run_id": pair.run_id,
        "observable_log": str(observable_path),
        "label_log": str(label_path),
        "paths_exist": paths_exist,
        "formal_seed_detected": bool(
            (_path_seeds(observable_path) | _path_seeds(label_path)) & FORBIDDEN_SEEDS
        ),
        "records_compared": 0,
        "records_with_mismatch": 0,
        "missing_label_outcome_records": 0,
        "missing_observable_payload_records": 0,
        "exact_mismatches": {field: 0 for field in EXACT_FIELDS},
        "numeric_mismatches": {field: 0 for field in NUMERIC_FIELDS},
        "numeric_missing": {field: 0 for field in NUMERIC_FIELDS},
        "numeric_shape_mismatches": {field: 0 for field in NUMERIC_FIELDS},
        "numeric_max_abs_diff": {field: 0.0 for field in NUMERIC_FIELDS},
        "first_mismatches": [],
    }
    if not paths_exist:
        return report
    observable_rows = _read_log(observable_path)
    label_rows = _read_log(label_path)
    n = min(int(records), len(observable_rows), len(label_rows))
    report["records_compared"] = n
    for index in range(n):
        observable = observable_rows[index]
        labeled = label_rows[index]
        row_mismatches: list[str] = []
        if observable.get("observable_state_logging") is None:
            report["missing_observable_payload_records"] += 1
            row_mismatches.append("observable_state_logging")
        if labeled.get("candidate_closed_loop_outcomes") is None:
            report["missing_label_outcome_records"] += 1
            row_mismatches.append("candidate_closed_loop_outcomes")
        for field in EXACT_FIELDS:
            if observable.get(field) != labeled.get(field):
                report["exact_mismatches"][field] += 1
                row_mismatches.append(field)
        for field in NUMERIC_FIELDS:
            result = _numeric_alignment(observable.get(field), labeled.get(field))
            if result["missing"]:
                report["numeric_missing"][field] += 1
                row_mismatches.append(field)
            elif result["shape_mismatch"]:
                report["numeric_shape_mismatches"][field] += 1
                report["numeric_mismatches"][field] += 1
                row_mismatches.append(field)
            elif not result["aligned"]:
                report["numeric_mismatches"][field] += 1
                report["numeric_max_abs_diff"][field] = max(
                    float(report["numeric_max_abs_diff"][field]),
                    float(result["max_abs_diff"]),
                )
                row_mismatches.append(field)
        if row_mismatches:
            report["records_with_mismatch"] += 1
            if len(report["first_mismatches"]) < 10:
                report["first_mismatches"].append(
                    {"record_index": index, "fields": sorted(set(row_mismatches))}
                )
    return report


def _numeric_alignment(left: Any, right: Any) -> dict[str, Any]:
    if left is None or right is None:
        return {
            "missing": True,
            "shape_mismatch": False,
            "aligned": False,
            "max_abs_diff": None,
        }
    lhs = np.asarray(left, dtype=np.float64)
    rhs = np.asarray(right, dtype=np.float64)
    if lhs.shape != rhs.shape:
        return {
            "missing": False,
            "shape_mismatch": True,
            "aligned": False,
            "max_abs_diff": None,
        }
    finite = np.isfinite(lhs) & np.isfinite(rhs)
    finite_diff = np.abs(lhs[finite] - rhs[finite])
    max_abs = float(np.max(finite_diff)) if finite_diff.size else 0.0
    nonfinite_equal = np.array_equal(lhs[~finite], rhs[~finite], equal_nan=True)
    aligned = bool(
        nonfinite_equal
        and np.allclose(lhs[finite], rhs[finite], atol=EPS, rtol=EPS, equal_nan=True)
    )
    return {
        "missing": False,
        "shape_mismatch": False,
        "aligned": aligned,
        "max_abs_diff": max_abs,
    }


def _read_log(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list.")
    rows = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"{path} record {index} must be an object.")
        rows.append(row)
    return rows


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["counts"]
    lines = [
        "# Observable Label Alignment Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `pairs` | `{counts['pairs']}` |",
        f"| `records_compared` | `{counts['records_compared']}` |",
        f"| `records_with_mismatch` | `{counts['records_with_mismatch']}` |",
        f"| `missing_label_outcome_records` | `{counts['missing_label_outcome_records']}` |",
        f"| `missing_observable_payload_records` | `{counts['missing_observable_payload_records']}` |",
        "",
        "## Pair Results",
        "",
        "| Run | Records | Mismatch Records | Missing Labels | Missing Payloads | First Mismatch Fields |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for pair in report["pairs"]:
        first = pair["first_mismatches"][0]["fields"] if pair["first_mismatches"] else []
        lines.append(
            f"| `{pair['run_id']}` | `{pair['records_compared']}` | "
            f"`{pair['records_with_mismatch']}` | "
            f"`{pair['missing_label_outcome_records']}` | "
            f"`{pair['missing_observable_payload_records']}` | "
            f"`{', '.join(first)}` |"
        )
    lines.extend(
        [
            "",
            "This audit is a label-source gate only. It does not authorize "
            "replay, Full36, formal seeds, online selection, CAMP retraining, "
            "or DP modification.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
