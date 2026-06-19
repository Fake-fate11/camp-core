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
from scripts.integrations.analyze_diffusion_planner_atom_schema_redesign_preflight import (  # noqa: E402
    ATOM_SPECS,
    READY_STATUS as PREFLIGHT_READY_STATUS,
    AtomSpec,
    _atom_values,
    _record as _preflight_record,
)
from scripts.integrations.analyze_diffusion_planner_descriptor_separability import (  # noqa: E402
    BENEFICIAL_RETAIN_RATE_TARGET,
    HARMFUL_BLOCK_RATE_TARGET,
    HARD_NONWORSE_RATE_TARGET,
    PROGRESS_LOSS_BUDGET_M,
    SEPARABILITY_AUC_TARGET,
    _allow_mask,
    _auc,
    _best_screen,
    _class_mask,
    _rank_screens,
    _screen_row,
    _summary,
    _thresholds,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (  # noqa: E402
    PREDECLARED_VARIANTS,
    WeightVariant,
    _load_record,
    _scales,
    _select,
    _weights,
)
from scripts.integrations.analyze_diffusion_planner_material_weight_failure_attribution import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_NON_SWITCH,
    _event,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "redesigned_atom_separability_promising_for_offline_weight_screen"
REJECT_STATUS = "redesigned_atom_separability_rejected"
SOURCE_BLOCKED_STATUS = "redesigned_atom_separability_source_not_ready"
FORMAL_SEED_STATUS = "redesigned_atom_separability_formal_seed_conflict"

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
            "Offline no-leak separability audit for redesigned DP-CAMP atom "
            "coefficients after the atom-schema preflight."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--atom_schema_preflight_json", type=Path, required=True)
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
        atom_schema_preflight_report=_load_json(args.atom_schema_preflight_json),
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
    atom_schema_preflight_report: dict[str, Any],
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
        atom_schema_preflight_report=atom_schema_preflight_report,
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
    atom_schema_preflight_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
    variants: tuple[WeightVariant, ...] = PREDECLARED_VARIANTS,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    hard_nonworse_rate_target: float = HARD_NONWORSE_RATE_TARGET,
    separability_auc_target: float = SEPARABILITY_AUC_TARGET,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(atom_schema_preflight_report)
    records: list[dict[str, Any]] = []
    atom_records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        label_prefix = f"record {index}"
        records.append(_load_record(item["raw"], item["context"], label_prefix))
        atom_records.append(_atom_record(item["raw"], item["context"], label_prefix, atom_specs))
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    scales = _scales(records, scale_percentile)
    variant_reports = [
        _variant_report(
            variant,
            records,
            atom_records,
            scales,
            atom_specs=atom_specs,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
            separability_auc_target=separability_auc_target,
        )
        for variant in variants
    ]
    decision = _decision(source, variant_reports, formal_seed_records=formal_seed_records)
    return {
        "analysis": {
            "name": "dp_camp_redesigned_atom_separability_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_thresholds": True,
            "future_outcome_labels_used_for_evaluation": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "accept_criteria": {
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_safety_delta_mean": "<= 0",
                "allowed_progress_delta_mean": f">= -{progress_loss_budget_m}",
                "final_hard_nonworse_rate": f">= {hard_nonworse_rate_target}",
                "atom_auc": f">= {separability_auc_target} for atom-level evidence",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Redesigned "
                "atoms are fixed current-tick finite-candidate coefficients "
                "computed before any closed-loop outcome label is consulted. "
                "The audit uses outcome labels only after fixed material-weight "
                "switch proposals to classify harmful or beneficial switches and "
                "to evaluate offline threshold diagnostics. CAMP scoring remains "
                "affine score_k(w)=a_k^T w over fixed atom coefficients, and the "
                "simplex/CVaR/L2 robust master remains convex in w. This audit "
                "does not claim trajectory-coordinate convexity and does not "
                "construct a DP-side classical Benders decomposition, dual, or "
                "valid cut."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_atom_schema_preflight_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "atom_coverage": _atom_coverage(atom_records, atom_specs),
        "variants": variant_reports,
        "ranked_atom_screens": _rank_atom_screens(variant_reports),
        "ranked_pair_screens": _rank_pair_screens(variant_reports),
        "failure_gap": _failure_gap(variant_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _atom_record(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    atom_specs: tuple[AtomSpec, ...],
) -> dict[str, Any]:
    record = _preflight_record(raw, context, label)
    atoms = {}
    for spec in atom_specs:
        values = _atom_values(spec, record)
        if values is None:
            raise ValueError(f"{label} missing redesigned atom {spec.name}.")
        atoms[spec.name] = np.asarray(values, dtype=np.float64)
    return {
        "context": record["context"],
        "candidate_count": record["candidate_count"],
        "atoms": atoms,
    }


def _variant_report(
    variant: WeightVariant,
    records: list[dict[str, Any]],
    atom_records: list[dict[str, Any]],
    scales: dict[str, float],
    *,
    atom_specs: tuple[AtomSpec, ...],
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
    separability_auc_target: float,
) -> dict[str, Any]:
    weights = _weights(variant)
    events = [
        {
            **_event(
                record,
                _select(record, weights, scales),
                weights,
                scales,
                progress_loss_budget_m=progress_loss_budget_m,
            ),
            "record_index": index,
        }
        for index, record in enumerate(records)
    ]
    changed = [event for event in events if event["changed"]]
    atom_reports = [
        _atom_report(
            spec,
            changed,
            atom_records,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
            separability_auc_target=separability_auc_target,
        )
        for spec in atom_specs
    ]
    atom_by_name = {report["atom"]: report for report in atom_reports}
    pair_reports = [
        _pair_report(
            pair,
            atom_by_name,
            changed,
            atom_records,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for pair in _pair_specs(atom_specs)
    ]
    return {
        "name": variant.name,
        "changed_switches": len(changed),
        "classification_counts": _class_counts(events),
        "atom_reports": atom_reports,
        "pair_reports": pair_reports,
        "best_atom_screen": _best_screen(
            [screen for report in atom_reports for screen in report["threshold_screens"]]
        ),
        "best_pair_screen": _best_screen(
            [screen for report in pair_reports for screen in report["threshold_screens"]]
        ),
    }


def _atom_report(
    spec: AtomSpec,
    changed: list[dict[str, Any]],
    atom_records: list[dict[str, Any]],
    *,
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
    separability_auc_target: float,
) -> dict[str, Any]:
    values = _atom_values_for_events(spec.name, changed, atom_records)
    harmful_values = values[_class_mask(changed, CLASS_HARMFUL)]
    beneficial_values = values[_class_mask(changed, CLASS_BENEFICIAL)]
    auc = _auc(harmful_values, beneficial_values)
    screens = [
        _screen_row(
            changed,
            values,
            _allow_mask(values, "block_high", threshold),
            screen_name=f"{spec.name}:block_high:{threshold:.12g}",
            feature=spec.name,
            direction="block_high",
            threshold=float(threshold),
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for threshold in _thresholds(values)
    ]
    return {
        "atom": spec.name,
        "expression": spec.expression,
        "rationale": spec.rationale,
        "direction": "block_high",
        "auc_harmful_vs_beneficial": auc,
        "meets_auc_target": bool(auc is not None and auc >= separability_auc_target),
        "harmful_distribution": _summary(harmful_values),
        "beneficial_distribution": _summary(beneficial_values),
        "neutral_distribution": _summary(values[_class_mask(changed, CLASS_NEUTRAL)]),
        "threshold_screens": screens,
        "best_screen": _best_screen(screens),
    }


def _pair_report(
    pair: tuple[str, str],
    atom_by_name: dict[str, dict[str, Any]],
    changed: list[dict[str, Any]],
    atom_records: list[dict[str, Any]],
    *,
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
) -> dict[str, Any]:
    left_values = _atom_values_for_events(pair[0], changed, atom_records)
    right_values = _atom_values_for_events(pair[1], changed, atom_records)
    screens = []
    for left_threshold in _thresholds(left_values):
        left_mask = _allow_mask(left_values, "block_high", left_threshold)
        for right_threshold in _thresholds(right_values):
            right_mask = _allow_mask(right_values, "block_high", right_threshold)
            screens.append(
                _screen_row(
                    changed,
                    np.maximum(left_values, right_values),
                    left_mask & right_mask,
                    screen_name=(
                        f"{pair[0]}:block_high:{left_threshold:.12g}+"
                        f"{pair[1]}:block_high:{right_threshold:.12g}"
                    ),
                    feature="+".join(pair),
                    direction="pair_and",
                    threshold=None,
                    progress_loss_budget_m=progress_loss_budget_m,
                    harmful_block_rate_target=harmful_block_rate_target,
                    beneficial_retain_rate_target=beneficial_retain_rate_target,
                    hard_nonworse_rate_target=hard_nonworse_rate_target,
                    extra={
                        "left_atom": pair[0],
                        "left_threshold": float(left_threshold),
                        "right_atom": pair[1],
                        "right_threshold": float(right_threshold),
                    },
                )
            )
    return {
        "atoms": list(pair),
        "threshold_screens": screens,
        "best_screen": _best_screen(screens),
    }


def _pair_specs(atom_specs: tuple[AtomSpec, ...]) -> tuple[tuple[str, str], ...]:
    names = {spec.name for spec in atom_specs}
    pairs = (
        ("shape_support_conflict_v1", "traffic_support_tradeoff_v1"),
        ("shape_support_conflict_v1", "shape_comfort_conflict_v1"),
        ("traffic_support_tradeoff_v1", "traffic_comfort_tradeoff_v1"),
        ("residual_traffic_shape_risk_v1", "absolute_lateral_load_v1"),
    )
    return tuple(pair for pair in pairs if pair[0] in names and pair[1] in names)


def _atom_values_for_events(
    atom: str,
    events: list[dict[str, Any]],
    atom_records: list[dict[str, Any]],
) -> np.ndarray:
    values = [
        float(atom_records[int(event["record_index"])]["atoms"][atom][int(event["chosen"])])
        for event in events
    ]
    return np.asarray(values, dtype=np.float64)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == PREFLIGHT_READY_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
        "failed_atoms": decision.get("failed_atoms", []),
        "failed_math_checks": decision.get("failed_math_checks", []),
    }


def _decision(
    source: dict[str, Any],
    variants: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    promising = [
        row
        for row in [*_rank_atom_screens(variants), *_rank_pair_screens(variants)]
        if row["promising_descriptor_screen"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not run redesigned atom separability unless the atom-schema preflight passed."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using redesigned atom separability evidence."
    elif promising:
        status = READY_STATUS
        next_step = (
            "Design only an offline material-weight screen over the promising "
            "redesigned atom rows; replay, formal seeds, online promotion, and "
            "retraining remain blocked."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "Reject the redesigned atom threshold screens. Use the failure_gap "
            "to decide whether a different atom schema or candidate-support "
            "route is needed before any weight screen."
        )
    return {
        "status": status,
        "promising_screens": promising[:20],
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_redesigned_atom_weight_screen_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _failure_gap(variants: list[dict[str, Any]]) -> dict[str, Any]:
    all_rows = [*_rank_atom_screens(variants), *_rank_pair_screens(variants)]
    best = all_rows[0] if all_rows else None
    best_auc = _best_auc(variants)
    if best is None:
        primary = "no_screen_rows"
    elif best["promising_descriptor_screen"]:
        primary = "no_gap_promising_redesigned_atom_screen_found"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "redesigned_atoms_block_beneficial_opportunities"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "redesigned_atoms_too_permissive_for_harmful_switches"
    elif (best["allowed_safety_delta_mean"] is None) or best["allowed_safety_delta_mean"] > 0.0:
        primary = "allowed_switches_remain_safety_negative"
    elif (
        best["allowed_progress_delta_mean"] is None
        or best["allowed_progress_delta_mean"] < -PROGRESS_LOSS_BUDGET_M
    ):
        primary = "allowed_switches_remain_progress_negative"
    else:
        primary = "unclassified_redesigned_atom_gap"
    return {
        "primary_gap": primary,
        "best_auc": best_auc,
        "best_screen": _screen_digest(best),
    }


def _best_auc(variants: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = []
    for variant in variants:
        for report in variant["atom_reports"]:
            auc = report["auc_harmful_vs_beneficial"]
            if auc is not None:
                rows.append(
                    {
                        "variant": variant["name"],
                        "atom": report["atom"],
                        "auc_harmful_vs_beneficial": auc,
                    }
                )
    if not rows:
        return None
    return sorted(rows, key=lambda row: -float(row["auc_harmful_vs_beneficial"]))[0]


def _rank_atom_screens(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        for report in variant["atom_reports"]:
            for screen in report["threshold_screens"]:
                rows.append({"variant": variant["name"], **screen})
    return _rank_screens(rows)


def _rank_pair_screens(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        for report in variant["pair_reports"]:
            for screen in report["threshold_screens"]:
                rows.append({"variant": variant["name"], **screen})
    return _rank_screens(rows)


def _screen_digest(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = (
        "variant",
        "screen_name",
        "feature",
        "direction",
        "threshold",
        "harmful_block_rate",
        "beneficial_retain_rate",
        "allowed_safety_delta_mean",
        "allowed_progress_delta_mean",
        "final_hard_nonworse_rate",
        "promising_descriptor_screen",
    )
    return {key: row.get(key) for key in keys}


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _atom_coverage(
    atom_records: list[dict[str, Any]],
    atom_specs: tuple[AtomSpec, ...],
) -> dict[str, Any]:
    total = len(atom_records)
    candidate_rows = int(sum(record["candidate_count"] for record in atom_records))
    result = {}
    for spec in atom_specs:
        rows = [
            record
            for record in atom_records
            if spec.name in record["atoms"]
        ]
        values = (
            np.concatenate([record["atoms"][spec.name] for record in rows])
            if rows
            else np.asarray([], dtype=np.float64)
        )
        result[spec.name] = {
            "records_available": len(rows),
            "records_total": total,
            "candidate_rows_available": int(values.size),
            "candidate_rows_total": candidate_rows,
            "summary": _summary(values),
        }
    return result


def _class_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        CLASS_HARMFUL: sum(int(event["class"] == CLASS_HARMFUL) for event in events),
        CLASS_BENEFICIAL: sum(int(event["class"] == CLASS_BENEFICIAL) for event in events),
        CLASS_NEUTRAL: sum(int(event["class"] == CLASS_NEUTRAL) for event in events),
        CLASS_NON_SWITCH: sum(int(event["class"] == CLASS_NON_SWITCH) for event in events),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gap = report["failure_gap"]
    lines = [
        "# Redesigned Atom Separability Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary gap: `{gap['primary_gap']}`",
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
        "## Ranked Atom Screens",
        "",
        "| Variant | Atom | Threshold | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_atom_screens"][:20]:
        lines.append(_screen_markdown_row(row, include_threshold=True))
    lines.extend(
        [
            "",
            "## Ranked Pair Screens",
            "",
            "| Variant | Atom | Threshold | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_pair_screens"][:20]:
        lines.append(_screen_markdown_row(row, include_threshold=False))
    lines.extend(
        [
            "",
            "This is an offline separability audit only. It does not train "
            "weights, change online selection, run replay, modify DP, or "
            "authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _screen_markdown_row(row: dict[str, Any], *, include_threshold: bool) -> str:
    threshold = row.get("threshold") if include_threshold else None
    threshold_text = _fmt(threshold) if threshold is not None else "`see_json`"
    return (
        f"| `{row['variant']}` | `{row['feature']}` | {threshold_text} | "
        f"`{row['promising_descriptor_screen']}` | "
        f"{_fmt(row['harmful_block_rate'])} | "
        f"{_fmt(row['beneficial_retain_rate'])} | "
        f"{_fmt(row['allowed_safety_delta_mean'])} | "
        f"{_fmt(row['allowed_progress_delta_mean'])} |"
    )


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
