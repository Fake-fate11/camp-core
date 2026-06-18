#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import CAMPSelector  # noqa: E402
from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_guarded_safety_selector import (  # noqa: E402
    GuardConfig,
    _guard_decision,
)
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    DEFAULT_REQUIRED_BUCKETS,
    EPS,
    FORMAL_SEEDS,
    _aggregate,
    _coverage_gaps,
    _fmt,
    _log_context,
    _record_row,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)
from scripts.integrations.evaluate_diffusion_planner_camp_safety_cost import (  # noqa: E402
    _bucket_aggregates,
    _select_record_index,
    _selection_pair,
    _selector_comparison,
)


TOL = 1e-12
FLOOR_RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "guarded_no_top1_floor",
        "description": "the current guarded selector; included as an exact reference",
        "checks": (),
    },
    {
        "name": "top1_red_floor",
        "description": (
            "fall back to DP Top-1 when the guarded candidate is worse than "
            "Top-1 on current-tick red-light proxies"
        ),
        "checks": ("union_red", "red_stopping"),
        "require_candidate0_feasible": True,
    },
    {
        "name": "top1_red_floor_unconditional",
        "description": (
            "diagnostic contrast: red floor that may return DP Top-1 even "
            "when the CAMP feasible mask marks candidate0 ineligible"
        ),
        "checks": ("union_red", "red_stopping"),
        "require_candidate0_feasible": False,
    },
    {
        "name": "top1_red_or_proxy_jerk_floor",
        "description": (
            "red floor plus fallback when the guarded candidate has higher "
            "current-tick proxy jerk than Top-1"
        ),
        "checks": ("union_red", "red_stopping", "proxy_jerk"),
        "require_candidate0_feasible": True,
    },
    {
        "name": "top1_red_or_proxy_jerk_floor_unconditional",
        "description": (
            "diagnostic contrast: red-or-jerk floor that may return DP Top-1 "
            "even when the CAMP feasible mask marks candidate0 ineligible"
        ),
        "checks": ("union_red", "red_stopping", "proxy_jerk"),
        "require_candidate0_feasible": False,
    },
    {
        "name": "top1_red_or_proxy_comfort_floor",
        "description": (
            "red floor plus fallback when either proxy jerk or proxy lateral "
            "is worse than Top-1"
        ),
        "checks": ("union_red", "red_stopping", "proxy_jerk", "proxy_lateral"),
        "require_candidate0_feasible": True,
    },
    {
        "name": "top1_red_or_proxy_comfort_floor_unconditional",
        "description": (
            "diagnostic contrast: red-or-comfort floor that may return DP "
            "Top-1 even when the CAMP feasible mask marks candidate0 ineligible"
        ),
        "checks": ("union_red", "red_stopping", "proxy_jerk", "proxy_lateral"),
        "require_candidate0_feasible": False,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline Top-1-relative floor counterfactual for a guarded CAMP "
            "selector. This is read-only and does not change online selection."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--atom_scales", type=Path, required=True)
    parser.add_argument("--static_weights", type=Path, required=True)
    parser.add_argument("--selector_name", default="guarded_top1_floor")
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        default=None,
    )
    parser.add_argument("--fail_on_missing_required", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required_buckets = (
        tuple(args.required_bucket)
        if args.required_bucket is not None
        else DEFAULT_REQUIRED_BUCKETS
    )
    report = analyze(
        [*args.root, *args.selection_log],
        atom_scales=args.atom_scales,
        static_weights=args.static_weights,
        selector_name=args.selector_name,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        required_buckets=required_buckets,
    )
    if args.fail_on_missing_required and report["coverage_gaps"][
        "missing_required_buckets"
    ]:
        missing = ", ".join(report["coverage_gaps"]["missing_required_buckets"])
        raise SystemExit(f"Missing required scenario bucket coverage: {missing}")
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
    paths: list[Path],
    *,
    atom_scales: Path,
    static_weights: Path,
    selector_name: str = "guarded_top1_floor",
    scenario_bucket_manifest: Path | None = None,
    fail_on_formal_seeds: bool = False,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    selector = CAMPSelector.from_files(
        atom_scales_path=atom_scales,
        static_weights_path=static_weights,
        mode="static",
    )
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    guard = GuardConfig()

    logs: list[dict[str, Any]] = []
    rows_by_rule: dict[str, list[dict[str, Any]]] = {
        str(rule["name"]): [] for rule in FLOOR_RULES
    }
    pairs_by_rule: dict[str, list[dict[str, Any]]] = {
        str(rule["name"]): [] for rule in FLOOR_RULES
    }
    events_by_rule: dict[str, list[dict[str, Any]]] = {
        str(rule["name"]): [] for rule in FLOOR_RULES
    }
    logged_rows: list[dict[str, Any]] = []

    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        formal_seed = context["seed"] in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        logs.append(
            {
                "path": str(log_path),
                "run_key": context["run_key"],
                "seed": context["seed"],
                "formal_seed": formal_seed,
                "scenario_buckets": context["scenario_buckets"],
                "records": len(payload),
            }
        )

        for record_index, record in enumerate(payload):
            label = f"{log_path} record {record_index}"
            raw_index, _scores, _used_fallback = _select_record_index(
                record,
                selector,
                label=label,
            )
            logged_index = int(record.get("selected_index"))
            decision = _guard_decision(
                record,
                raw_index=raw_index,
                logged_index=logged_index,
                guard=guard,
                label=label,
            )
            guarded_index = raw_index if decision["accepted"] else logged_index
            logged_row = _record_row(
                record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            logged_rows.append(logged_row)

            for rule in FLOOR_RULES:
                rule_name = str(rule["name"])
                floor_index, floor_decision = _floor_index(
                    record,
                    guarded_index=int(guarded_index),
                    rule=rule,
                    label=label,
                )
                floor_record = {**record, "selected_index": int(floor_index)}
                floor_row = _record_row(
                    floor_record,
                    label=label,
                    log_path=log_path,
                    record_index=record_index,
                    context=context,
                    formal_seed=formal_seed,
                )
                rows_by_rule[rule_name].append(floor_row)
                pairs_by_rule[rule_name].append(
                    _selection_pair(
                        record,
                        evaluated_row=floor_row,
                        logged_row=logged_row,
                        log_path=log_path,
                        record_index=record_index,
                        context=context,
                    )
                )
                events_by_rule[rule_name].append(
                    _floor_event(
                        floor_decision,
                        floor_row=floor_row,
                        logged_row=logged_row,
                        guarded_index=int(guarded_index),
                        log_path=log_path,
                        record_index=record_index,
                        context=context,
                    )
                )

    formal_seed_logs = [log["path"] for log in logs if log["formal_seed"]]
    reference_rows = rows_by_rule["guarded_no_top1_floor"]
    coverage_gaps = _coverage_gaps(reference_rows, required_buckets)
    rule_reports = []
    for rule in FLOOR_RULES:
        rule_name = str(rule["name"])
        rows = rows_by_rule[rule_name]
        overall = _aggregate(rows, seed_key=f"{selector_name}:{rule_name}")
        by_bucket = _bucket_aggregates(rows)
        rule_reports.append(
            {
                "name": rule_name,
                "description": str(rule["description"]),
                "checks": list(rule["checks"]),
                "overall": overall,
                "by_bucket": by_bucket,
                "selector_vs_logged": _selector_comparison(pairs_by_rule[rule_name]),
                "floor_summary": _floor_summary(events_by_rule[rule_name]),
                "gate": _selector_gate(
                    overall,
                    by_bucket,
                    formal_seed_logs=formal_seed_logs,
                    coverage_gaps=coverage_gaps,
                    required_buckets=required_buckets,
                ),
            }
        )

    return {
        "analysis": {
            "name": "dp_camp_guarded_top1_floor_counterfactual_v1",
            "role": (
                "read-only counterfactual that starts from the guarded CAMP "
                "choice and may fall back to DP Top-1 using current-tick "
                "finite-candidate proxy floors"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate_closed_loop_outcomes evaluate SafetyCost only; "
                "floor rules use current-tick candidate constants"
            ),
            "classical_benders_claim": False,
            "selector_name": selector_name,
            "selector_artifacts": {
                "atom_scales": str(atom_scales),
                "static_weights": str(static_weights),
            },
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "formal_seed_policy": (
                "forbidden" if fail_on_formal_seeds else "reported_only"
            ),
            "formal_seed_logs": formal_seed_logs,
            "required_buckets": list(required_buckets),
            "selection_contract": (
                "Compute the saved CAMP raw selection, apply the existing "
                "fail-closed guard against logged redstopfloor05, then apply a "
                "deterministic Top-1 floor when the guarded candidate is worse "
                "than candidate0 on the rule's fixed current-tick proxy checks. "
                "Rules with require_candidate0_feasible=true retain the guarded "
                "choice when candidate0 is not base-feasible; rules marked "
                "unconditional are diagnostic contrasts that may return DP "
                "Top-1 despite the CAMP feasible mask."
            ),
            "math_boundary": (
                "DP remains a fixed black-box generator. This audit reads "
                "saved finite-candidate diagnostics and posterior labels only. "
                "The floor uses fixed current-tick nonnegative candidate "
                "constants and deterministic tie-free fallback to candidate0; "
                "it does not alter DP, atoms, affine score semantics, or the "
                "simplex/CVaR/L2 master, and it is not a Benders subproblem."
            ),
        },
        "logs": {
            "total": len(logs),
            "formal_seed_logs": len(formal_seed_logs),
            "items": logs,
        },
        "coverage_gaps": coverage_gaps,
        "rules": rule_reports,
        "logged_selector": {
            "overall": _aggregate(logged_rows, seed_key="logged:overall"),
            "by_bucket": _bucket_aggregates(logged_rows),
        },
    }


def _floor_index(
    record: dict[str, Any],
    *,
    guarded_index: int,
    rule: dict[str, Any],
    label: str,
) -> tuple[int, dict[str, Any]]:
    candidate_count = int(record.get("num_candidates", 0))
    if not 0 <= guarded_index < candidate_count:
        raise ValueError(f"{label} guarded index is out of range.")
    checks = tuple(str(check) for check in rule["checks"])
    require_candidate0_feasible = bool(rule.get("require_candidate0_feasible", True))
    if not checks or guarded_index == 0:
        return guarded_index, {
            "changed_to_top1": False,
            "candidate0_feasible": _candidate0_feasible(record, candidate_count),
            "require_candidate0_feasible": require_candidate0_feasible,
            "trigger_reasons": [],
        }
    candidate0_feasible = _candidate0_feasible(record, candidate_count)
    if require_candidate0_feasible and not candidate0_feasible:
        return guarded_index, {
            "changed_to_top1": False,
            "candidate0_feasible": False,
            "require_candidate0_feasible": True,
            "trigger_reasons": ["candidate0_not_base_feasible"],
        }

    trigger_reasons = [
        check
        for check in checks
        if _proxy_loss(record, check, guarded_index, candidate_count, label) > TOL
    ]
    changed = bool(trigger_reasons)
    return (
        0 if changed else guarded_index,
        {
            "changed_to_top1": changed,
            "candidate0_feasible": candidate0_feasible,
            "require_candidate0_feasible": require_candidate0_feasible,
            "trigger_reasons": trigger_reasons,
        },
    )


def _candidate0_feasible(record: dict[str, Any], candidate_count: int) -> bool:
    mask = _bool_vector(record.get("feasible_mask"), candidate_count, "feasible_mask")
    return bool(mask.any() and mask[0])


def _proxy_loss(
    record: dict[str, Any],
    check: str,
    guarded_index: int,
    candidate_count: int,
    label: str,
) -> float:
    field_by_check = {
        "union_red": "candidate_horizon_union_planned_red_light_cost",
        "red_stopping": "candidate_red_stopping_margin_cost",
        "proxy_jerk": "candidate_dp_prior_jerk_excess_cost",
        "proxy_lateral": "candidate_horizon_lateral_acceleration_cost",
    }
    field = field_by_check.get(check)
    if field is None:
        raise ValueError(f"Unsupported Top-1 floor check: {check}")
    values = _vector(record.get(field), candidate_count, f"{label} {field}")
    return float(values[guarded_index] - values[0])


def _floor_event(
    decision: dict[str, Any],
    *,
    floor_row: dict[str, Any],
    logged_row: dict[str, Any],
    guarded_index: int,
    log_path: Path,
    record_index: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    floor_index = int(floor_row["camp_index"])
    guarded_worse_than_top1 = bool(
        guarded_index != 0 and floor_row["costs"]["top1"] < logged_row["costs"]["camp"]
    )
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "run_key": context["run_key"],
        "scenario_buckets": context["scenario_buckets"],
        "guarded_index": int(guarded_index),
        "floor_index": floor_index,
        "changed_to_top1": bool(decision["changed_to_top1"]),
        "candidate0_feasible": bool(decision["candidate0_feasible"]),
        "require_candidate0_feasible": bool(decision["require_candidate0_feasible"]),
        "trigger_reasons": list(decision["trigger_reasons"]),
        "floor_minus_logged_cost": float(
            floor_row["costs"]["camp"] - logged_row["costs"]["camp"]
        ),
        "floor_minus_top1_cost": float(floor_row["deltas"]["camp_minus_top1"]),
        "guarded_worse_than_top1_blocked": bool(
            decision["changed_to_top1"] and guarded_index != 0
        ),
        "guarded_worse_than_logged_baseline": guarded_worse_than_top1,
    }


def _floor_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    changed = [event for event in events if event["changed_to_top1"]]
    trigger_counts = Counter(
        reason for event in changed for reason in event["trigger_reasons"]
    )
    return {
        "records": len(events),
        "top1_fallbacks": len(changed),
        "top1_fallback_rate": len(changed) / max(len(events), 1),
        "candidate0_infeasible_records": sum(
            int(not event["candidate0_feasible"]) for event in events
        ),
        "candidate0_infeasible_top1_fallbacks": sum(
            int(event["changed_to_top1"] and not event["candidate0_feasible"])
            for event in events
        ),
        "trigger_reason_counts": dict(trigger_counts),
        "posterior_worse_than_top1_blocked": sum(
            int(event["changed_to_top1"] and event["floor_minus_top1_cost"] == 0.0)
            for event in events
        ),
    }


def _selector_gate(
    overall: dict[str, Any],
    by_bucket: list[dict[str, Any]],
    *,
    formal_seed_logs: list[str],
    coverage_gaps: dict[str, Any],
    required_buckets: tuple[str, ...],
) -> dict[str, Any]:
    bucket_by_name = {entry["bucket"]: entry for entry in by_bucket}
    required_bucket_checks = {}
    for bucket in required_buckets:
        entry = bucket_by_name.get(bucket)
        ci_high = None
        records = 0
        if entry is not None:
            records = int(entry.get("records", 0))
            ci_high = (
                entry.get("run_level_delta_ci", {})
                .get("camp_minus_top1", {})
                .get("ci95_high")
            )
        required_bucket_checks[bucket] = {
            "records": records,
            "ci95_high": ci_high,
            "passed": ci_high is not None and float(ci_high) < 0.0,
        }
    overall_ci_high = (
        overall.get("run_level_delta_ci", {})
        .get("camp_minus_top1", {})
        .get("ci95_high")
    )
    checks = {
        "no_formal_seed_logs": not formal_seed_logs,
        "required_bucket_coverage": not coverage_gaps["missing_required_buckets"],
        "overall_camp_minus_top1_ci_high_below_zero": (
            overall_ci_high is not None and float(overall_ci_high) < 0.0
        ),
        "required_bucket_camp_minus_top1_ci_high_below_zero": all(
            row["passed"] for row in required_bucket_checks.values()
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "overall_ci95_high": overall_ci_high,
        "required_bucket_checks": required_bucket_checks,
    }


def _vector(value: Any, size: int, label: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"{label} must contain {size} values.")
    arr = np.asarray(value, dtype=np.float64)
    if not np.isfinite(arr).all():
        raise ValueError(f"{label} contains non-finite values.")
    return arr


def _bool_vector(value: Any, size: int, label: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"{label} must contain {size} values.")
    return np.asarray([bool(item) for item in value], dtype=bool)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Guarded Top-1 Floor Counterfactual",
        "",
        "This is a read-only offline audit. The floor starts from the existing "
        "guarded selector and may fall back to DP Top-1 using only current-tick "
        "finite-candidate proxies. Candidate outcomes are posterior labels for "
        "SafetyCost evaluation only.",
        "",
        f"- Logs: `{report['logs']['total']}`",
        f"- Formal-seed logs: `{report['logs']['formal_seed_logs']}`",
        f"- Missing required buckets: "
        f"`{', '.join(report['coverage_gaps']['missing_required_buckets']) or 'none'}`",
        "",
        "## Rules",
        "",
        "| Rule | Gate | Mean delta vs Top-1 | CI high | Top-1 fallbacks | Changed vs logged | Mean vs logged |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule in report["rules"]:
        overall = rule["overall"]
        ci = overall["run_level_delta_ci"]["camp_minus_top1"]
        compare = rule["selector_vs_logged"]
        lines.append(
            f"| `{rule['name']}` | `{rule['gate']['passed']}` | "
            f"{_fmt(ci['mean'])} | {_fmt(ci['ci95_high'])} | "
            f"`{rule['floor_summary']['top1_fallbacks']}` | "
            f"{_fmt(compare['changed_record_rate'])} | "
            f"{_fmt(compare['evaluated_minus_logged_cost_mean'])} |"
        )
    for rule in report["rules"]:
        lines.extend(
            [
                "",
                f"## {rule['name']}",
                "",
                rule["description"],
                "",
                f"- Checks: `{', '.join(rule['checks']) or 'none'}`",
                f"- Gate passed: `{rule['gate']['passed']}`",
                "",
                "### Required Buckets",
                "",
                "| Bucket | Records | CI high vs Top-1 | Passed |",
                "| --- | ---: | ---: | --- |",
            ]
        )
        for bucket, row in rule["gate"]["required_bucket_checks"].items():
            lines.append(
                f"| `{bucket}` | `{row['records']}` | "
                f"{_fmt(row['ci95_high'])} | `{row['passed']}` |"
            )
        lines.extend(
            [
                "",
                "### Floor Summary",
                "",
                "```json",
                json.dumps(rule["floor_summary"], indent=2, sort_keys=True),
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
