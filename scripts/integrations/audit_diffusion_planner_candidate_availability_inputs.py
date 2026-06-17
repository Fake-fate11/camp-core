#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


BOOL_OUTCOME_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
NUMERIC_OUTCOME_FIELDS = (
    "progress_m",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
)
ATOM_FALLBACKS = {
    "progress_shortfall": ("atom:progress_shortfall",),
    "proxy_lateral": (
        "candidate_horizon_lateral_acceleration_cost",
        "atom:planned_lateral_acceleration_cost",
    ),
    "proxy_jerk": (
        "candidate_dp_prior_jerk_excess_cost",
        "atom:dp_prior_jerk_excess_cost",
    ),
    "union_red": (
        "candidate_horizon_union_planned_red_light_cost",
        "atom:planned_red_light_cost",
    ),
    "red_stopping": (
        "candidate_red_stopping_margin_cost",
        "atom:red_stopping_margin_cost",
    ),
}
MAX_EXAMPLES = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether DP-CAMP selection logs contain the fixed finite "
            "candidate inputs required by the offline candidate availability "
            "oracle. This is read-only and never selects trajectories."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--fail_on_not_ready",
        action="store_true",
        help="Exit nonzero when the outcome-labeled oracle inputs are incomplete.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_inputs([*args.root, *args.selection_log])
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if args.fail_on_not_ready and not report["readiness"][
        "candidate_availability_oracle_ready"
    ]:
        raise SystemExit(report["readiness"]["next_step"])


def audit_inputs(paths: list[Path]) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    totals = {
        "logs": len(log_paths),
        "records": 0,
        "fallback_records": 0,
        "nonfallback_records": 0,
    }
    field_counts: Counter[str] = Counter()
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    missing_examples: dict[str, list[str]] = defaultdict(list)
    candidate_counts: Counter[int] = Counter()

    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            _record_missing(missing_examples, "nonempty_log_list", str(log_path))
            continue
        for index, record in enumerate(payload):
            label = f"{log_path}#{index}"
            totals["records"] += 1
            if not isinstance(record, dict):
                _record_missing(missing_examples, "record_object", label)
                continue
            candidate_count = _candidate_count(record, label, missing_examples)
            if candidate_count <= 0:
                continue
            candidate_counts[candidate_count] += 1
            _selected_index(record, candidate_count, label, missing_examples)
            feasible = _list_of_length(
                record.get("feasible_mask"),
                candidate_count,
                label,
                "feasible_mask",
                missing_examples,
            )
            if feasible is None:
                continue
            if any(bool(value) for value in feasible):
                totals["nonfallback_records"] += 1
            else:
                totals["fallback_records"] += 1
            _audit_outcomes(record, candidate_count, label, field_counts, missing_examples)
            _audit_proxy_inputs(
                record,
                candidate_count,
                label,
                field_counts,
                source_counts,
                missing_examples,
            )

    readiness = _readiness(totals, field_counts)
    return {
        "analysis": {
            "name": "dp_camp_candidate_availability_input_readiness_v1",
            "role": "read-only input contract audit before outcome-labeled candidate availability oracle",
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "formal_seeds": False,
            "future_outcome_leakage": (
                "candidate closed-loop outcomes are required only as offline "
                "labels for the oracle; this audit does not select online trajectories"
            ),
            "convexity_boundary": (
                "All audited proxy quantities are fixed finite-candidate "
                "constants at the current tick. This readiness audit is not "
                "Benders and makes no trajectory-coordinate convexity claim."
            ),
        },
        "records": totals,
        "candidate_counts": {
            str(count): records for count, records in sorted(candidate_counts.items())
        },
        "field_coverage": _coverage(totals["records"], field_counts),
        "proxy_sources": {
            name: dict(counter) for name, counter in sorted(source_counts.items())
        },
        "missing_examples": {
            key: values for key, values in sorted(missing_examples.items())
        },
        "readiness": readiness,
    }


def _candidate_count(
    record: dict[str, Any],
    label: str,
    missing_examples: dict[str, list[str]],
) -> int:
    try:
        candidate_count = int(record.get("num_candidates"))
    except (TypeError, ValueError):
        _record_missing(missing_examples, "num_candidates", label)
        return 0
    if candidate_count <= 0:
        _record_missing(missing_examples, "num_candidates_positive", label)
        return 0
    return candidate_count


def _selected_index(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
    missing_examples: dict[str, list[str]],
) -> None:
    try:
        selected = int(record.get("selected_index"))
    except (TypeError, ValueError):
        _record_missing(missing_examples, "selected_index", label)
        return
    if selected < 0 or selected >= candidate_count:
        _record_missing(missing_examples, "selected_index_in_range", label)


def _audit_outcomes(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
    field_counts: Counter[str],
    missing_examples: dict[str, list[str]],
) -> None:
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        _record_missing(missing_examples, "candidate_closed_loop_outcomes", label)
        return
    complete = True
    for idx, outcome in enumerate(outcomes):
        item_label = f"{label}.candidate[{idx}]"
        if not isinstance(outcome, dict):
            _record_missing(missing_examples, "candidate_outcome_object", item_label)
            complete = False
            continue
        for field in NUMERIC_OUTCOME_FIELDS:
            if _finite_number(outcome.get(field)) is None:
                _record_missing(missing_examples, f"outcome_{field}", item_label)
                complete = False
        for field in BOOL_OUTCOME_FIELDS:
            if outcome.get(field) is None:
                _record_missing(missing_examples, f"outcome_{field}", item_label)
                complete = False
    if complete:
        field_counts["candidate_closed_loop_outcomes_complete"] += 1


def _audit_proxy_inputs(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
    field_counts: Counter[str],
    source_counts: dict[str, Counter[str]],
    missing_examples: dict[str, list[str]],
) -> None:
    for name, sources in ATOM_FALLBACKS.items():
        source = _first_available_source(record, candidate_count, sources)
        if source is None:
            _record_missing(missing_examples, name, label)
            continue
        field_counts[name] += 1
        source_counts[name][source] += 1


def _first_available_source(
    record: dict[str, Any],
    candidate_count: int,
    sources: tuple[str, ...],
) -> str | None:
    atom_names = record.get("atom_names")
    atoms = record.get("atoms")
    for source in sources:
        if source.startswith("atom:"):
            atom_name = source.removeprefix("atom:")
            if _has_atom_vector(atom_names, atoms, atom_name, candidate_count):
                return source
            continue
        if _has_vector(record.get(source), candidate_count):
            return source
    return None


def _has_atom_vector(
    atom_names: Any,
    atoms: Any,
    atom_name: str,
    candidate_count: int,
) -> bool:
    if not isinstance(atom_names, list) or atom_name not in atom_names:
        return False
    atom_index = atom_names.index(atom_name)
    if not isinstance(atoms, list) or len(atoms) != candidate_count:
        return False
    for row in atoms:
        if not isinstance(row, list) or atom_index >= len(row):
            return False
        if _finite_number(row[atom_index]) is None:
            return False
    return True


def _has_vector(value: Any, candidate_count: int) -> bool:
    if not isinstance(value, list) or len(value) != candidate_count:
        return False
    return all(_finite_number(item) is not None for item in value)


def _list_of_length(
    value: Any,
    expected: int,
    label: str,
    field: str,
    missing_examples: dict[str, list[str]],
) -> list[Any] | None:
    if not isinstance(value, list) or len(value) != expected:
        _record_missing(missing_examples, field, label)
        return None
    return value


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _record_missing(
    missing_examples: dict[str, list[str]],
    key: str,
    label: str,
) -> None:
    examples = missing_examples[key]
    if len(examples) < MAX_EXAMPLES:
        examples.append(label)


def _coverage(total_records: int, field_counts: Counter[str]) -> dict[str, dict[str, Any]]:
    keys = ("candidate_closed_loop_outcomes_complete", *ATOM_FALLBACKS)
    denom = max(total_records, 1)
    return {
        key: {
            "records": int(field_counts.get(key, 0)),
            "rate": float(field_counts.get(key, 0) / denom),
        }
        for key in keys
    }


def _readiness(totals: dict[str, int], field_counts: Counter[str]) -> dict[str, Any]:
    total = int(totals["records"])
    complete_outcomes = int(field_counts.get("candidate_closed_loop_outcomes_complete", 0))
    proxy_ready = all(int(field_counts.get(key, 0)) == total for key in ATOM_FALLBACKS)
    outcome_ready = total > 0 and complete_outcomes == total
    oracle_ready = bool(outcome_ready and proxy_ready)
    if oracle_ready:
        next_step = "run_outcome_labeled_candidate_availability_oracle"
    elif not outcome_ready and proxy_ready:
        next_step = (
            "generate_or_attach_candidate_closed_loop_outcomes_before_running_oracle"
        )
    elif outcome_ready and not proxy_ready:
        next_step = "add_missing_current_tick_proxy_fields_or_atom_fallbacks"
    else:
        next_step = "repair_selection_log_schema_before_candidate_availability_oracle"
    return {
        "candidate_availability_oracle_ready": oracle_ready,
        "outcome_labels_ready": outcome_ready,
        "current_tick_proxy_inputs_ready": proxy_ready,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    readiness = report["readiness"]
    lines = [
        "# DP CAMP Candidate Availability Input Readiness",
        "",
        "This is a read-only audit of selection-log inputs required by the "
        "offline outcome-labeled candidate availability oracle.",
        "",
        "## Readiness",
        "",
        f"- oracle ready: `{readiness['candidate_availability_oracle_ready']}`",
        f"- outcome labels ready: `{readiness['outcome_labels_ready']}`",
        f"- current-tick proxy inputs ready: `{readiness['current_tick_proxy_inputs_ready']}`",
        f"- next step: `{readiness['next_step']}`",
        "",
        "## Records",
        "",
        "| Logs | Records | Nonfallback | Fallback |",
        "| ---: | ---: | ---: | ---: |",
        (
            f"| {report['records']['logs']} | {report['records']['records']} | "
            f"{report['records']['nonfallback_records']} | "
            f"{report['records']['fallback_records']} |"
        ),
        "",
        "## Field Coverage",
        "",
        "| Field | Records | Rate |",
        "| --- | ---: | ---: |",
    ]
    for field, row in report["field_coverage"].items():
        lines.append(f"| `{field}` | {row['records']} | {row['rate']:.6f} |")
    lines.extend(["", "## Proxy Sources", "", "```json"])
    lines.append(json.dumps(report["proxy_sources"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Missing Examples", "", "```json"])
    lines.append(json.dumps(report["missing_examples"], indent=2, sort_keys=True))
    lines.append("```")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
