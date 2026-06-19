#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    ATOM_FAMILIES,
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (  # noqa: E402
    BOOL_FIELDS,
    FORMAL_SEEDS,
    PREDECLARED_VARIANTS,
    REJECT_STATUS,
    WeightVariant,
    _conditional_rate,
    _load_record,
    _normalized_atoms,
    _scales,
    _select,
    _summary,
    _weights,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "material_weight_failure_attribution_progress_certificate_promising"
REJECT_STATUS_ATTRIBUTION = "material_weight_failure_attribution_progress_certificate_rejected"
SOURCE_BLOCKED_STATUS = "material_weight_failure_attribution_source_not_rejected"
FORMAL_SEED_STATUS = "material_weight_failure_attribution_formal_seed_conflict"

CLASS_HARMFUL = "harmful_switch"
CLASS_BENEFICIAL = "beneficial_switch"
CLASS_NEUTRAL = "neutral_switch"
CLASS_NON_SWITCH = "non_switch"

SUPPORT_BUDGETS = (0.0, 0.02, 0.05, 0.10, 0.20)
PROGRESS_LOSS_BUDGET_M = 0.05
HARMFUL_BLOCK_RATE_TARGET = 0.75
BENEFICIAL_RETAIN_RATE_TARGET = 0.75
EPS = 1e-12

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak failure attribution for rejected material-atom "
            "weight directions. Selection and attribution use fixed current-"
            "tick atoms; outcomes are used only for post-selection labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--weight_sensitivity_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        weight_sensitivity_report=_load_json(args.weight_sensitivity_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        scale_percentile=args.scale_percentile,
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
    paths: list[Path],
    *,
    weight_sensitivity_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            items.append({"raw": raw, "context": {**context, "record_index": index}})
    return analyze_records(
        items,
        weight_sensitivity_report=weight_sensitivity_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        scale_percentile=scale_percentile,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    weight_sensitivity_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
    support_budgets: tuple[float, ...] = SUPPORT_BUDGETS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    variants: tuple[WeightVariant, ...] = PREDECLARED_VARIANTS,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(weight_sensitivity_report)
    records = [
        _load_record(item["raw"], item["context"], f"record {index}")
        for index, item in enumerate(items)
    ]
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    scales = _scales(records, scale_percentile)
    variant_reports = [
        _variant_attribution(
            variant,
            records,
            scales,
            support_budgets=support_budgets,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
        )
        for variant in variants
    ]
    decision = _decision(
        source,
        variant_reports,
        formal_seed_records=formal_seed_records,
    )
    return {
        "analysis": {
            "name": "dp_camp_material_weight_failure_attribution_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_selection": False,
            "future_outcome_labels_used_for_attribution": False,
            "future_outcome_labels_used_for_evaluation": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "atom_families": list(ATOM_FAMILIES),
            "support_budgets": list(support_budgets),
            "progress_loss_budget_m": float(progress_loss_budget_m),
            "promising_certificate_thresholds": {
                "harmful_block_rate": harmful_block_rate_target,
                "beneficial_retain_rate": beneficial_retain_rate_target,
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Selection, "
                "score-contribution attribution, and support-certificate screens "
                "use only fixed current-tick finite-candidate material atoms. "
                "Closed-loop outcomes are used only after those fixed choices "
                "are made to label harmful or beneficial switches. CAMP scores "
                "remain affine a_k^T w over nonnegative simplex weights; no "
                "DP-side master/subproblem, dual, cut, or classical Benders "
                "claim is made."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_weight_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "variants": variant_reports,
        "ranked_certificates": _rank_certificates(variant_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _variant_attribution(
    variant: WeightVariant,
    records: list[dict[str, Any]],
    scales: dict[str, float],
    *,
    support_budgets: tuple[float, ...],
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
) -> dict[str, Any]:
    weights = _weights(variant)
    events = [
        _event(
            record,
            _select(record, weights, scales),
            weights,
            scales,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        for record in records
    ]
    class_counts = _class_counts(events)
    harmful = [event for event in events if event["class"] == CLASS_HARMFUL]
    beneficial = [event for event in events if event["class"] == CLASS_BENEFICIAL]
    certificate_rows = [
        _certificate_row(
            events,
            budget,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        for budget in support_budgets
    ]
    return {
        "name": variant.name,
        "weights": dict(zip(ATOM_FAMILIES, weights)),
        "classification_counts": class_counts,
        "scenario_bucket_breakdown": _bucket_breakdown(events),
        "harmful_driver_summary": _driver_summary(harmful),
        "harmful_switch_delta_summary": _delta_summary(harmful),
        "beneficial_switch_delta_summary": _delta_summary(beneficial),
        "non_switch_delta_summary": _delta_summary(
            [event for event in events if event["class"] == CLASS_NON_SWITCH]
        ),
        "certificate_sensitivity": certificate_rows,
        "best_certificate": _best_certificate(certificate_rows),
    }


def _event(
    record: dict[str, Any],
    chosen: int,
    weights: np.ndarray,
    scales: dict[str, float],
    *,
    progress_loss_budget_m: float,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    normalized = _normalized_atoms(record["material_atoms"], scales)
    contribution_delta = weights * (normalized[chosen] - normalized[selected])
    raw_delta = record["material_atoms"][chosen] - record["material_atoms"][selected]
    safety_delta = float(record["safety_cost"][chosen] - record["safety_cost"][selected])
    progress_delta = float(record["progress"][chosen] - record["progress"][selected])
    hard_worse = _hard_worse(record, chosen, selected)
    changed = chosen != selected
    if not changed:
        cls = CLASS_NON_SWITCH
    elif safety_delta > EPS or hard_worse or progress_delta < -progress_loss_budget_m - EPS:
        cls = CLASS_HARMFUL
    elif safety_delta < -EPS and progress_delta >= -progress_loss_budget_m - EPS:
        cls = CLASS_BENEFICIAL
    else:
        cls = CLASS_NEUTRAL
    driver = _dominant_driver(contribution_delta)
    return {
        "class": cls,
        "changed": changed,
        "chosen": int(chosen),
        "selected": selected,
        "context": record["context"],
        "safety_delta": safety_delta,
        "progress_delta": progress_delta,
        "hard_worse": hard_worse,
        "raw_atom_delta": dict(zip(ATOM_FAMILIES, [float(value) for value in raw_delta])),
        "score_contribution_delta": dict(
            zip(ATOM_FAMILIES, [float(value) for value in contribution_delta])
        ),
        "score_improvement_by_atom": dict(
            zip(ATOM_FAMILIES, [float(max(-value, 0.0)) for value in contribution_delta])
        ),
        "dominant_driver": driver,
        "support_delta": float(raw_delta[ATOM_FAMILIES.index("support_preservation_deficit")]),
    }


def _dominant_driver(contribution_delta: np.ndarray) -> str | None:
    improvement = np.maximum(-np.asarray(contribution_delta, dtype=np.float64), 0.0)
    if float(np.max(improvement)) <= EPS:
        return None
    return str(ATOM_FAMILIES[int(np.argmax(improvement))])


def _driver_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "events": 0,
            "dominant_driver_counts": {},
            "mean_score_improvement_by_atom": {
                family: None for family in ATOM_FAMILIES
            },
            "mean_raw_delta_by_atom": {family: None for family in ATOM_FAMILIES},
        }
    counts: dict[str, int] = {}
    for event in events:
        driver = event["dominant_driver"] or "none"
        counts[driver] = counts.get(driver, 0) + 1
    return {
        "events": len(events),
        "dominant_driver_counts": dict(sorted(counts.items())),
        "mean_score_improvement_by_atom": {
            family: _mean(
                [event["score_improvement_by_atom"][family] for event in events]
            )
            for family in ATOM_FAMILIES
        },
        "mean_raw_delta_by_atom": {
            family: _mean([event["raw_atom_delta"][family] for event in events])
            for family in ATOM_FAMILIES
        },
    }


def _delta_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "events": len(events),
        "safety_delta": _summary([event["safety_delta"] for event in events]),
        "progress_delta": _summary([event["progress_delta"] for event in events]),
        "hard_worse_rate": _mean([float(event["hard_worse"]) for event in events]),
        "raw_atom_delta": {
            family: _summary([event["raw_atom_delta"][family] for event in events])
            for family in ATOM_FAMILIES
        },
    }


def _bucket_breakdown(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for bucket in event["context"].get("scenario_buckets", ["overall"]):
            grouped.setdefault(bucket, []).append(event)
    rows = []
    for bucket, bucket_events in sorted(grouped.items()):
        counts = _class_counts(bucket_events)
        rows.append(
            {
                "bucket": bucket,
                "events": len(bucket_events),
                "classification_counts": counts,
                "harmful_rate": counts[CLASS_HARMFUL] / max(len(bucket_events), 1),
                "beneficial_rate": counts[CLASS_BENEFICIAL] / max(len(bucket_events), 1),
                "changed_rate": (
                    sum(int(event["changed"]) for event in bucket_events)
                    / max(len(bucket_events), 1)
                ),
            }
        )
    return rows


def _certificate_row(
    events: list[dict[str, Any]],
    budget: float,
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    progress_loss_budget_m: float,
) -> dict[str, Any]:
    changed = [event for event in events if event["changed"]]
    harmful = [event for event in changed if event["class"] == CLASS_HARMFUL]
    beneficial = [event for event in changed if event["class"] == CLASS_BENEFICIAL]
    allowed = [
        event
        for event in changed
        if event["support_delta"] <= float(budget) + EPS
    ]
    allowed_harmful = [event for event in allowed if event["class"] == CLASS_HARMFUL]
    allowed_beneficial = [
        event for event in allowed if event["class"] == CLASS_BENEFICIAL
    ]
    harmful_block_rate = 1.0 - len(allowed_harmful) / max(len(harmful), 1)
    beneficial_retain_rate = len(allowed_beneficial) / max(len(beneficial), 1)
    allowed_safety_mean = _mean([event["safety_delta"] for event in allowed])
    allowed_progress_mean = _mean([event["progress_delta"] for event in allowed])
    promising = bool(
        harmful
        and beneficial
        and harmful_block_rate >= harmful_block_rate_target
        and beneficial_retain_rate >= beneficial_retain_rate_target
        and (allowed_safety_mean is not None and allowed_safety_mean <= 0.0)
        and (
            allowed_progress_mean is not None
            and allowed_progress_mean >= -float(progress_loss_budget_m)
        )
    )
    return {
        "support_delta_budget": float(budget),
        "changed_switches": len(changed),
        "harmful_switches": len(harmful),
        "beneficial_switches": len(beneficial),
        "allowed_switches": len(allowed),
        "allowed_harmful_switches": len(allowed_harmful),
        "allowed_beneficial_switches": len(allowed_beneficial),
        "harmful_block_rate": harmful_block_rate,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_safety_delta_mean": allowed_safety_mean,
        "allowed_progress_delta_mean": allowed_progress_mean,
        "promising_progress_support_certificate": promising,
    }


def _best_certificate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            not row["promising_progress_support_certificate"],
            -float(row["harmful_block_rate"]),
            -float(row["beneficial_retain_rate"]),
            float(row["allowed_safety_delta_mean"] or 0.0),
        ),
    )[0]


def _rank_certificates(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        best = variant.get("best_certificate")
        if best is None:
            continue
        rows.append({"variant": variant["name"], **best})
    return sorted(
        rows,
        key=lambda row: (
            not row["promising_progress_support_certificate"],
            -float(row["harmful_block_rate"]),
            -float(row["beneficial_retain_rate"]),
            float(row["allowed_safety_delta_mean"] or 0.0),
        ),
    )


def _decision(
    source: dict[str, Any],
    variants: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    promising = [
        row
        for row in _rank_certificates(variants)
        if row["promising_progress_support_certificate"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not attribute rejected weights unless the source gate was rejected."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using this attribution evidence."
    elif promising:
        status = READY_STATUS
        next_step = (
            "Design only an offline no-leak progress/support certificate screen "
            "around the promising rows; replay and retraining remain blocked."
        )
    else:
        status = REJECT_STATUS_ATTRIBUTION
        next_step = (
            "A simple support-preservation certificate is insufficient for the "
            "rejected material-weight variants; redesign atoms or weighting "
            "before any selector screen."
        )
    return {
        "status": status,
        "promising_certificates": promising,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_progress_support_certificate_screen_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == REJECT_STATUS,
        "passing_variants": decision.get("passing_variants", []),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
    }


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _class_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        CLASS_HARMFUL: sum(int(event["class"] == CLASS_HARMFUL) for event in events),
        CLASS_BENEFICIAL: sum(int(event["class"] == CLASS_BENEFICIAL) for event in events),
        CLASS_NEUTRAL: sum(int(event["class"] == CLASS_NEUTRAL) for event in events),
        CLASS_NON_SWITCH: sum(int(event["class"] == CLASS_NON_SWITCH) for event in events),
    }


def _hard_worse(record: dict[str, Any], chosen: int, selected: int) -> bool:
    chosen_outcome = record["outcomes"][chosen]
    selected_outcome = record["outcomes"][selected]
    return any(
        float(bool(chosen_outcome[field])) > float(bool(selected_outcome[field]))
        for field in BOOL_FIELDS
    )


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Material Weight Failure Attribution",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `logs` | `{report['records']['logs']}` |",
        f"| `total` | `{report['records']['total']}` |",
        f"| `candidate_rows` | `{report['records']['candidate_rows']}` |",
        f"| `formal_seed_records` | `{report['records']['formal_seed_records']}` |",
        "",
        "## Ranked Certificates",
        "",
        "| Variant | Budget | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_certificates"]:
        lines.append(
            f"| `{row['variant']}` | {_fmt(row['support_delta_budget'])} | "
            f"`{row['promising_progress_support_certificate']}` | "
            f"{_fmt(row['harmful_block_rate'])} | "
            f"{_fmt(row['beneficial_retain_rate'])} | "
            f"{_fmt(row['allowed_safety_delta_mean'])} | "
            f"{_fmt(row['allowed_progress_delta_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Harmful Drivers",
            "",
            "| Variant | Harmful | Dominant drivers | Support delta mean | Traffic delta mean | Top1 delta mean |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for variant in report["variants"]:
        drivers = variant["harmful_driver_summary"]
        raw = drivers["mean_raw_delta_by_atom"]
        lines.append(
            f"| `{variant['name']}` | `{drivers['events']}` | "
            f"`{drivers['dominant_driver_counts']}` | "
            f"{_fmt(raw['support_preservation_deficit'])} | "
            f"{_fmt(raw['traffic_rule_exposure'])} | "
            f"{_fmt(raw['top1_shape_deviation'])} |"
        )
    lines.extend(
        [
            "",
            "This is an offline attribution audit only. It does not train weights, "
            "change online selection, run replay, modify DP, or authorize formal "
            "seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "`n/a`"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "`n/a`"
    if not np.isfinite(result):
        return "`n/a`"
    return f"`{result:.6g}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
