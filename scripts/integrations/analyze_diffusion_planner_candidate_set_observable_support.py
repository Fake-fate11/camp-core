#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
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
    AtomSpec,
    _atom_values,
    _record as _preflight_record,
)
from scripts.integrations.analyze_diffusion_planner_descriptor_separability import (  # noqa: E402
    _auc,
    _summary,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    ATOM_FAMILIES,
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (  # noqa: E402
    BOOL_FIELDS,
    _load_record,
)
from scripts.integrations.analyze_diffusion_planner_redesigned_atom_separability import (  # noqa: E402
    REJECT_STATUS as REDESIGNED_ATOM_SEPARABILITY_REJECT_STATUS,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "candidate_set_observable_support_promising"
REJECT_STATUS = "candidate_set_observable_support_rejected"
SOURCE_BLOCKED_STATUS = "candidate_set_observable_support_source_not_rejected"
FORMAL_SEED_STATUS = "candidate_set_observable_support_formal_seed_conflict"

PROGRESS_LOSS_BUDGET_M = 0.05
MIN_ELIGIBLE_ORACLE_RECORD_RATE = 0.05
MIN_OBSERVABLE_AUC = 0.70
MIN_TOP1_ORACLE_CAPTURE_RATE = 0.50
EPS = 1e-12

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class CandidateRow:
    record_index: int
    candidate_index: int
    feasible: bool
    selected: bool
    safety_delta: float
    progress_delta: float
    hard_worse: bool
    eligible_oracle: bool
    safety_improving: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline audit of whether the fixed DP candidate set contains "
            "eligible oracle opportunities and whether current-tick visible "
            "features can identify them."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--redesigned_atom_separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
        redesigned_atom_separability_report=_load_json(
            args.redesigned_atom_separability_json
        ),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
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
    paths: list[Path],
    *,
    redesigned_atom_separability_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
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
        redesigned_atom_separability_report=redesigned_atom_separability_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    redesigned_atom_separability_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    fail_on_formal_seeds: bool = False,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    min_eligible_oracle_record_rate: float = MIN_ELIGIBLE_ORACLE_RECORD_RATE,
    min_observable_auc: float = MIN_OBSERVABLE_AUC,
    min_top1_oracle_capture_rate: float = MIN_TOP1_ORACLE_CAPTURE_RATE,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(redesigned_atom_separability_report)
    records = []
    for index, item in enumerate(items):
        records.append(_record_bundle(item["raw"], item["context"], f"record {index}", atom_specs))
    formal_seed_records = sum(int(record["base"]["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    candidate_rows = [
        row
        for record_index, record in enumerate(records)
        for row in _candidate_rows(record_index, record, progress_loss_budget_m)
    ]
    record_support = _record_support(records, candidate_rows)
    feature_reports = _feature_reports(records, candidate_rows)
    decision = _decision(
        source,
        record_support,
        feature_reports,
        formal_seed_records=formal_seed_records,
        min_eligible_oracle_record_rate=min_eligible_oracle_record_rate,
        min_observable_auc=min_observable_auc,
        min_top1_oracle_capture_rate=min_top1_oracle_capture_rate,
    )
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_observable_support_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_features": False,
            "future_outcome_labels_used_for_oracle_labels": True,
            "future_outcome_labels_used_for_evaluation": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "progress_loss_budget_m": progress_loss_budget_m,
            "accept_criteria": {
                "eligible_oracle_record_rate": f">= {min_eligible_oracle_record_rate}",
                "best_observable_auc": f">= {min_observable_auc}",
                "best_top1_oracle_capture_rate": f">= {min_top1_oracle_capture_rate}",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Runtime-visible "
                "features are fixed current-tick finite-candidate scalars computed "
                "before outcome labels are consulted. Outcome labels are used only "
                "offline to mark eligible oracle candidates and diagnose candidate "
                "support. If any feature later becomes an atom, it is a fixed "
                "coefficient a_k and CAMP scoring remains affine score_k(w)=a_k^T w; "
                "the simplex/CVaR/L2 master remains convex in w. No DP-side "
                "classical Benders decomposition, dual, or valid cut is claimed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_redesigned_atom_separability_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "candidate_support": record_support,
        "feature_catalog": _feature_catalog(records),
        "feature_reports": feature_reports,
        "ranked_features": _rank_features(feature_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _record_bundle(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    atom_specs: tuple[AtomSpec, ...],
) -> dict[str, Any]:
    base = _load_record(raw, context, label)
    preflight = _preflight_record(raw, context, label)
    redesigned_atoms = {
        spec.name: _atom_values(spec, preflight)
        for spec in atom_specs
    }
    if any(values is None for values in redesigned_atoms.values()):
        missing = [name for name, values in redesigned_atoms.items() if values is None]
        raise ValueError(f"{label} missing redesigned atoms: {missing}")
    features = _visible_features(base, preflight, redesigned_atoms)
    return {
        "base": base,
        "preflight": preflight,
        "features": features,
    }


def _visible_features(
    base: dict[str, Any],
    preflight: dict[str, Any],
    redesigned_atoms: dict[str, np.ndarray | None],
) -> dict[str, np.ndarray]:
    features: dict[str, np.ndarray] = {}
    for index, family in enumerate(ATOM_FAMILIES):
        features[f"material:{family}"] = np.asarray(base["material_atoms"][:, index], dtype=np.float64)
    for key, values in preflight["values"].items():
        if values is not None:
            features[f"descriptor:{key}"] = np.asarray(values, dtype=np.float64)
    for key in ("top1_shape_gain", "traffic_gain", "comfort_gain"):
        values = preflight["values"].get(key)
        if values is not None:
            feasible = np.asarray(base["feasible"], dtype=bool)
            source = np.asarray(values, dtype=np.float64)
            feasible_values = source[feasible] if feasible.any() else source
            max_value = float(np.max(feasible_values)) if feasible_values.size else 0.0
            features[f"opportunity_deficit:{key}"] = np.maximum(max_value - source, 0.0)
    for name, values in redesigned_atoms.items():
        if values is not None:
            features[f"redesigned:{name}"] = np.asarray(values, dtype=np.float64)
    return features


def _candidate_rows(
    record_index: int,
    record: dict[str, Any],
    progress_loss_budget_m: float,
) -> list[CandidateRow]:
    base = record["base"]
    selected = int(base["selected_index"])
    safety = np.asarray(base["safety_cost"], dtype=np.float64)
    progress = np.asarray(base["progress"], dtype=np.float64)
    rows = []
    for candidate in range(int(base["candidate_count"])):
        feasible = bool(base["feasible"][candidate])
        selected_row = candidate == selected
        safety_delta = float(safety[candidate] - safety[selected])
        progress_delta = float(progress[candidate] - progress[selected])
        hard_worse = _hard_worse(base, candidate, selected)
        safety_improving = bool(feasible and not selected_row and safety_delta < -EPS)
        eligible = bool(
            safety_improving
            and progress_delta >= -float(progress_loss_budget_m) - EPS
            and not hard_worse
        )
        rows.append(
            CandidateRow(
                record_index=record_index,
                candidate_index=candidate,
                feasible=feasible,
                selected=selected_row,
                safety_delta=safety_delta,
                progress_delta=progress_delta,
                hard_worse=hard_worse,
                eligible_oracle=eligible,
                safety_improving=safety_improving,
            )
        )
    return rows


def _record_support(
    records: list[dict[str, Any]],
    rows: list[CandidateRow],
) -> dict[str, Any]:
    by_record: dict[int, list[CandidateRow]] = {}
    for row in rows:
        by_record.setdefault(row.record_index, []).append(row)
    eligible_records = []
    safety_improving_records = []
    tradeoff_only_records = []
    no_safety_improvement_records = []
    oracle_safety_delta = []
    oracle_progress_delta = []
    for index in range(len(records)):
        record_rows = by_record[index]
        eligible = [row for row in record_rows if row.eligible_oracle]
        safety_improving = [row for row in record_rows if row.safety_improving]
        if eligible:
            eligible_records.append(index)
            best = sorted(eligible, key=lambda row: (row.safety_delta, -row.progress_delta))[0]
            oracle_safety_delta.append(best.safety_delta)
            oracle_progress_delta.append(best.progress_delta)
        if safety_improving:
            safety_improving_records.append(index)
        if safety_improving and not eligible:
            tradeoff_only_records.append(index)
        if not safety_improving:
            no_safety_improvement_records.append(index)
    total = max(len(records), 1)
    candidate_total = max(len(rows), 1)
    feasible_nonselected = [
        row for row in rows if row.feasible and not row.selected
    ]
    return {
        "records_total": len(records),
        "candidate_rows_total": len(rows),
        "feasible_nonselected_candidate_rows": len(feasible_nonselected),
        "eligible_oracle_records": len(eligible_records),
        "eligible_oracle_record_rate": len(eligible_records) / total,
        "safety_improving_records": len(safety_improving_records),
        "safety_improving_record_rate": len(safety_improving_records) / total,
        "tradeoff_only_records": len(tradeoff_only_records),
        "tradeoff_only_record_rate": len(tradeoff_only_records) / total,
        "no_safety_improvement_records": len(no_safety_improvement_records),
        "no_safety_improvement_record_rate": len(no_safety_improvement_records) / total,
        "eligible_oracle_candidate_rows": sum(int(row.eligible_oracle) for row in rows),
        "eligible_oracle_candidate_rate": sum(int(row.eligible_oracle) for row in rows) / candidate_total,
        "safety_improving_candidate_rows": sum(int(row.safety_improving) for row in rows),
        "safety_improving_candidate_rate": sum(int(row.safety_improving) for row in rows) / candidate_total,
        "best_oracle_safety_delta": _summary(np.asarray(oracle_safety_delta, dtype=np.float64)),
        "best_oracle_progress_delta": _summary(np.asarray(oracle_progress_delta, dtype=np.float64)),
    }


def _feature_reports(
    records: list[dict[str, Any]],
    rows: list[CandidateRow],
) -> list[dict[str, Any]]:
    feature_names = sorted(records[0]["features"])
    return [
        _feature_report(feature_name, records, rows)
        for feature_name in feature_names
    ]


def _feature_report(
    feature_name: str,
    records: list[dict[str, Any]],
    rows: list[CandidateRow],
) -> dict[str, Any]:
    candidate_rows = [
        row for row in rows if row.feasible and not row.selected
    ]
    values = np.asarray(
        [
            records[row.record_index]["features"][feature_name][row.candidate_index]
            for row in candidate_rows
        ],
        dtype=np.float64,
    )
    eligible_mask = np.asarray([row.eligible_oracle for row in candidate_rows], dtype=bool)
    finite = np.isfinite(values)
    positive = values[eligible_mask & finite]
    negative = values[(~eligible_mask) & finite]
    auc_low = _auc(-positive, -negative)
    auc_high = _auc(positive, negative)
    if auc_high is not None and (auc_low is None or auc_high > auc_low):
        best_auc = auc_high
        best_direction = "high"
    else:
        best_auc = auc_low
        best_direction = "low"
    capture = _topk_capture(feature_name, records, rows, best_direction)
    return {
        "feature": feature_name,
        "candidate_rows": len(candidate_rows),
        "finite_candidate_rows": int(np.sum(finite)),
        "eligible_oracle_rows": int(np.sum(eligible_mask & finite)),
        "noneligible_rows": int(np.sum((~eligible_mask) & finite)),
        "auc_low_is_oracle": auc_low,
        "auc_high_is_oracle": auc_high,
        "best_auc": best_auc,
        "best_direction": best_direction,
        "top1_oracle_capture_rate": capture["top1_oracle_capture_rate"],
        "top3_oracle_capture_rate": capture["top3_oracle_capture_rate"],
        "eligible_record_count": capture["eligible_record_count"],
        "eligible_distribution": _summary(positive),
        "noneligible_distribution": _summary(negative),
    }


def _topk_capture(
    feature_name: str,
    records: list[dict[str, Any]],
    rows: list[CandidateRow],
    direction: str,
) -> dict[str, Any]:
    by_record: dict[int, list[CandidateRow]] = {}
    for row in rows:
        if row.feasible and not row.selected:
            by_record.setdefault(row.record_index, []).append(row)
    total = 0
    top1 = 0
    top3 = 0
    for record_index, record_rows in by_record.items():
        if not any(row.eligible_oracle for row in record_rows):
            continue
        total += 1
        values = records[record_index]["features"][feature_name]
        ordered = sorted(
            record_rows,
            key=lambda row: (
                values[row.candidate_index]
                if direction == "low"
                else -values[row.candidate_index],
                row.candidate_index,
            ),
        )
        top1 += int(bool(ordered and ordered[0].eligible_oracle))
        top3 += int(any(row.eligible_oracle for row in ordered[:3]))
    denom = max(total, 1)
    return {
        "eligible_record_count": total,
        "top1_oracle_capture_rate": top1 / denom,
        "top3_oracle_capture_rate": top3 / denom,
    }


def _feature_catalog(records: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for feature in sorted(records[0]["features"]):
        values = np.concatenate(
            [record["features"][feature] for record in records]
        )
        result[feature] = {
            "records_available": len(records),
            "candidate_rows": int(values.size),
            "summary": _summary(values),
        }
    return result


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == REDESIGNED_ATOM_SEPARABILITY_REJECT_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_gap": (report.get("failure_gap") or {}).get("primary_gap"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
    }


def _decision(
    source: dict[str, Any],
    support: dict[str, Any],
    feature_reports: list[dict[str, Any]],
    *,
    formal_seed_records: int,
    min_eligible_oracle_record_rate: float,
    min_observable_auc: float,
    min_top1_oracle_capture_rate: float,
) -> dict[str, Any]:
    best_feature = _rank_features(feature_reports)[0] if feature_reports else None
    best_auc = float(best_feature["best_auc"] or 0.0) if best_feature else 0.0
    best_top1 = float(best_feature["top1_oracle_capture_rate"]) if best_feature else 0.0
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        bottleneck = "source_gate_not_rejected"
        next_step = "Do not audit candidate-set support unless redesigned atom separability was rejected."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        bottleneck = "formal_seed_conflict"
        next_step = "Exclude formal seeds before using candidate-set support evidence."
    elif support["eligible_oracle_record_rate"] < min_eligible_oracle_record_rate:
        status = REJECT_STATUS
        if support["safety_improving_record_rate"] >= min_eligible_oracle_record_rate:
            bottleneck = "evaluation_tradeoff_or_progress_hard_constraint"
        else:
            bottleneck = "candidate_set_support_limitation"
        next_step = (
            "Do not tune CAMP weights; the fixed candidate set rarely contains "
            "eligible safety-improving alternatives under the current objective."
        )
    elif best_auc >= min_observable_auc and best_top1 >= min_top1_oracle_capture_rate:
        status = READY_STATUS
        bottleneck = "observable_support_present"
        next_step = (
            "Design only an offline oracle-feature screen around the visible "
            "support signal; replay, formal seeds, online selector promotion, "
            "and retraining remain blocked."
        )
    else:
        status = REJECT_STATUS
        bottleneck = "missing_observable_state_or_descriptor_information"
        next_step = (
            "The fixed candidate set contains eligible oracle opportunities, "
            "but current runtime-visible features do not identify them reliably. "
            "Do not run another atom/weight threshold screen without new "
            "state descriptors or candidate-support evidence."
        )
    return {
        "status": status,
        "primary_bottleneck": bottleneck,
        "best_feature": best_feature,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_oracle_feature_screen_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _rank_features(feature_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        feature_reports,
        key=lambda row: (
            -float(row["best_auc"] or 0.0),
            -float(row["top1_oracle_capture_rate"]),
            -float(row["top3_oracle_capture_rate"]),
            row["feature"],
        ),
    )


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["base"]["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["base"]["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["base"]["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _hard_worse(record: dict[str, Any], candidate: int, selected: int) -> bool:
    candidate_outcome = record["outcomes"][candidate]
    selected_outcome = record["outcomes"][selected]
    return any(
        float(bool(candidate_outcome[field])) > float(bool(selected_outcome[field]))
        for field in BOOL_FIELDS
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    support = report["candidate_support"]
    lines = [
        "# Candidate Set Observable Support Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Primary bottleneck: `{decision['primary_bottleneck']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Candidate Support",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `records_total` | `{support['records_total']}` |",
        f"| `eligible_oracle_record_rate` | {_fmt(support['eligible_oracle_record_rate'])} |",
        f"| `safety_improving_record_rate` | {_fmt(support['safety_improving_record_rate'])} |",
        f"| `tradeoff_only_record_rate` | {_fmt(support['tradeoff_only_record_rate'])} |",
        f"| `eligible_oracle_candidate_rate` | {_fmt(support['eligible_oracle_candidate_rate'])} |",
        "",
        "## Ranked Visible Features",
        "",
        "| Feature | Direction | AUC | Top1 Capture | Top3 Capture |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in report["ranked_features"][:20]:
        lines.append(
            f"| `{row['feature']}` | `{row['best_direction']}` | "
            f"{_fmt(row['best_auc'])} | "
            f"{_fmt(row['top1_oracle_capture_rate'])} | "
            f"{_fmt(row['top3_oracle_capture_rate'])} |"
        )
    lines.extend(
        [
            "",
            "This is an offline support diagnostic only. It does not train "
            "weights, change online selection, run replay, modify DP, or "
            "authorize formal seeds.",
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
