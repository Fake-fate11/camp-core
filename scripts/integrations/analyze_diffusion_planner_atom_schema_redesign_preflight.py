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
from scripts.integrations.analyze_diffusion_planner_descriptor_separability import (  # noqa: E402
    REJECT_STATUS as DESCRIPTOR_SEPARABILITY_REJECT_STATUS,
    _descriptor_record,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    _log_context,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "atom_schema_redesign_preflight_ready_for_offline_separability_audit"
REJECT_STATUS = "atom_schema_redesign_preflight_rejected"
SOURCE_BLOCKED_STATUS = "atom_schema_redesign_preflight_source_not_rejected"
FORMAL_SEED_STATUS = "atom_schema_redesign_preflight_formal_seed_conflict"

EPS = 1e-12
FORMAL_SEEDS = {11, 12, 13}

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class AtomSpec:
    name: str
    expression: str
    required_descriptors: tuple[str, ...]
    rationale: str


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="support_loss_composite_v2",
        expression="max(progress_loss_m, first_step_loss_m, speed_loss_mps)",
        required_descriptors=(
            "progress_loss_m",
            "first_step_loss_m",
            "speed_loss_mps",
        ),
        rationale=(
            "the previous support atom missed first-step and tail/target speed "
            "loss patterns that overlap harmful Top-1-shape switches"
        ),
    ),
    AtomSpec(
        name="comfort_worse_composite_v2",
        expression="max(jerk_worse_mps3, lateral_worse_mps2, yaw_worse_rps)",
        required_descriptors=(
            "jerk_worse_mps3",
            "lateral_worse_mps2",
            "yaw_worse_rps",
        ),
        rationale=(
            "the separability audit showed comfort regressions overlap both "
            "harmful and beneficial switches, so the next schema needs an "
            "explicit composite rather than a hidden certificate guard"
        ),
    ),
    AtomSpec(
        name="shape_support_conflict_v1",
        expression="top1_shape_gain * support_loss_composite_v2",
        required_descriptors=(
            "top1_shape_gain",
            "progress_loss_m",
            "first_step_loss_m",
            "speed_loss_mps",
        ),
        rationale=(
            "harmful switches are dominated by Top-1-shape improvement paired "
            "with support loss; this fixed atom exposes that interaction to "
            "the affine CAMP score"
        ),
    ),
    AtomSpec(
        name="shape_comfort_conflict_v1",
        expression="top1_shape_gain * comfort_worse_composite_v2",
        required_descriptors=(
            "top1_shape_gain",
            "jerk_worse_mps3",
            "lateral_worse_mps2",
            "yaw_worse_rps",
        ),
        rationale=(
            "Top-1-shape gain alone was the best but insufficient signal; "
            "multiplying by current-tick comfort regression targets the "
            "observed harmful-switch driver without using outcomes"
        ),
    ),
    AtomSpec(
        name="traffic_support_tradeoff_v1",
        expression="traffic_gain * support_loss_composite_v2",
        required_descriptors=(
            "traffic_gain",
            "progress_loss_m",
            "first_step_loss_m",
            "speed_loss_mps",
        ),
        rationale=(
            "beneficial and harmful switches both reduce traffic exposure; "
            "this atom asks whether that gain is being bought with support loss"
        ),
    ),
    AtomSpec(
        name="traffic_comfort_tradeoff_v1",
        expression="traffic_gain * comfort_worse_composite_v2",
        required_descriptors=(
            "traffic_gain",
            "jerk_worse_mps3",
            "lateral_worse_mps2",
            "yaw_worse_rps",
        ),
        rationale=(
            "traffic improvements should not silently mask jerk/lateral/yaw "
            "regressions in a candidate-level affine score"
        ),
    ),
    AtomSpec(
        name="residual_traffic_shape_risk_v1",
        expression="traffic_remaining * top1_shape_gain",
        required_descriptors=("traffic_remaining", "top1_shape_gain"),
        rationale=(
            "a candidate that still carries traffic-rule exposure should not be "
            "rewarded merely for moving toward the DP Top-1 shape"
        ),
    ),
    AtomSpec(
        name="absolute_lateral_load_v1",
        expression="absolute_lateral_mps2",
        required_descriptors=("absolute_lateral_mps2",),
        rationale=(
            "absolute lateral load had moderate separability and is an "
            "industrial comfort/safety guard available before outcome labels"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only preflight for a redesigned DP-CAMP atom schema after "
            "descriptor separability rejected threshold tuning."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--descriptor_separability_json", type=Path, required=True)
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
        descriptor_separability_report=_load_json(args.descriptor_separability_json),
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
    descriptor_separability_report: dict[str, Any],
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
        descriptor_separability_report=descriptor_separability_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    descriptor_separability_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    fail_on_formal_seeds: bool = False,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(descriptor_separability_report)
    records = [
        _record(item["raw"], item["context"], f"record {index}")
        for index, item in enumerate(items)
    ]
    formal_seed_records = sum(int(_is_formal_seed(record["context"])) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    atom_rows = [
        _atom_report(spec, records)
        for spec in atom_specs
    ]
    math_checks = _math_checks(atom_rows)
    decision = _decision(
        source,
        atom_rows,
        math_checks,
        formal_seed_records=formal_seed_records,
    )
    return {
        "analysis": {
            "name": "dp_camp_atom_schema_redesign_preflight_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_evaluation": False,
            "threshold_tuning": False,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Proposed "
                "atoms are fixed current-tick finite-candidate scalars computed "
                "before any closed-loop outcome label is consulted. Some atoms "
                "use max or products of fixed descriptors, but after computation "
                "they are just candidate coefficients a_k. CAMP scoring remains "
                "affine score_k(w)=a_k^T w over fixed atoms, and the "
                "simplex/CVaR/L2 robust master remains convex in w. This "
                "preflight makes no trajectory-coordinate convexity claim and "
                "does not construct a DP-side classical Benders decomposition, "
                "dual, or valid cut."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_descriptor_separability_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "proposed_atom_schema": [_spec_payload(spec) for spec in atom_specs],
        "atom_reports": atom_rows,
        "math_checks": math_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _record(raw: dict[str, Any], context: dict[str, Any], label: str) -> dict[str, Any]:
    descriptor = _descriptor_record(raw, context, label)
    return {
        "context": descriptor["context"],
        "candidate_count": descriptor["candidate_count"],
        "values": descriptor["values"],
    }


def _is_formal_seed(context: dict[str, Any]) -> bool:
    seed = context.get("seed")
    try:
        seed_value = int(seed)
    except (TypeError, ValueError):
        seed_value = None
    return bool(context.get("formal_seed", seed_value in FORMAL_SEEDS))


def _atom_report(spec: AtomSpec, records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_records = 0
    finite_records = 0
    nonnegative_records = 0
    values_by_record: list[np.ndarray] = []
    for record in records:
        values = _atom_values(spec, record)
        if values is None:
            missing_records += 1
            continue
        values_by_record.append(values)
        finite_records += int(np.all(np.isfinite(values)))
        nonnegative_records += int(np.all(values >= -EPS))

    candidate_rows_total = int(sum(record["candidate_count"] for record in records))
    candidate_rows_available = int(sum(values.size for values in values_by_record))
    concatenated = (
        np.concatenate(values_by_record)
        if values_by_record
        else np.asarray([], dtype=np.float64)
    )
    finite = concatenated[np.isfinite(concatenated)]
    passed = bool(
        missing_records == 0
        and finite_records == len(records)
        and nonnegative_records == len(records)
        and candidate_rows_available == candidate_rows_total
    )
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_descriptors": list(spec.required_descriptors),
        "rationale": spec.rationale,
        "records_available": len(records) - missing_records,
        "records_total": len(records),
        "candidate_rows_available": candidate_rows_available,
        "candidate_rows_total": candidate_rows_total,
        "finite_records": finite_records,
        "nonnegative_records": nonnegative_records,
        "finite_candidate_rows": int(finite.size),
        "nonnegative_candidate_rows": int(np.sum(finite >= -EPS)),
        "summary": _summary(finite),
        "no_leak": True,
        "fixed_before_weight_optimization": True,
        "affine_score_compatible": True,
        "convex_master_compatible": True,
        "trajectory_coordinate_convexity_claim": False,
        "classical_benders_claim": False,
        "passed_preflight": passed,
    }


def _atom_values(spec: AtomSpec, record: dict[str, Any]) -> np.ndarray | None:
    values = record["values"]
    required = [values.get(key) for key in spec.required_descriptors]
    if any(vector is None for vector in required):
        return None
    support_loss = _component_max(
        values,
        ("progress_loss_m", "first_step_loss_m", "speed_loss_mps"),
    )
    comfort_worse = _component_max(
        values,
        ("jerk_worse_mps3", "lateral_worse_mps2", "yaw_worse_rps"),
    )
    if spec.name == "support_loss_composite_v2":
        return support_loss
    if spec.name == "comfort_worse_composite_v2":
        return comfort_worse
    if spec.name == "shape_support_conflict_v1":
        return values["top1_shape_gain"] * support_loss
    if spec.name == "shape_comfort_conflict_v1":
        return values["top1_shape_gain"] * comfort_worse
    if spec.name == "traffic_support_tradeoff_v1":
        return values["traffic_gain"] * support_loss
    if spec.name == "traffic_comfort_tradeoff_v1":
        return values["traffic_gain"] * comfort_worse
    if spec.name == "residual_traffic_shape_risk_v1":
        return values["traffic_remaining"] * values["top1_shape_gain"]
    if spec.name == "absolute_lateral_load_v1":
        return values["absolute_lateral_mps2"]
    raise ValueError(f"Unsupported atom spec: {spec.name}")


def _component_max(values: dict[str, np.ndarray | None], keys: tuple[str, ...]) -> np.ndarray:
    vectors = [values[key] for key in keys]
    if any(vector is None for vector in vectors):
        raise ValueError(f"Missing descriptors for component max: {keys}")
    return np.max(np.vstack(vectors), axis=0)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == DESCRIPTOR_SEPARABILITY_REJECT_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_gap": (report.get("failure_gap") or {}).get("primary_gap"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
    }


def _math_checks(atom_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        (
            "all_atoms_no_leak",
            all(row["no_leak"] for row in atom_rows),
            "atoms use only fixed current-tick candidate descriptors",
        ),
        (
            "all_atoms_fixed_before_weight_optimization",
            all(row["fixed_before_weight_optimization"] for row in atom_rows),
            "atom vectors are computed before optimizing over w",
        ),
        (
            "all_atoms_nonnegative",
            all(row["nonnegative_candidate_rows"] == row["candidate_rows_total"] for row in atom_rows),
            "nonnegative coefficients keep simplex-weight interpretation direct",
        ),
        (
            "affine_score_preserved",
            all(row["affine_score_compatible"] for row in atom_rows),
            "score_k(w)=a_k^T w over fixed candidate atom coefficients",
        ),
        (
            "simplex_cvar_l2_master_convex",
            all(row["convex_master_compatible"] for row in atom_rows),
            "master remains convex in w for fixed atoms",
        ),
        (
            "no_trajectory_coordinate_convexity_claim",
            not any(row["trajectory_coordinate_convexity_claim"] for row in atom_rows),
            "the preflight does not claim convexity in trajectory coordinates",
        ),
        (
            "no_classical_benders_claim",
            not any(row["classical_benders_claim"] for row in atom_rows),
            "no DP-side master/subproblem, dual, or valid cut is constructed",
        ),
    ]
    return [
        {"name": name, "passed": bool(passed), "evidence": evidence}
        for name, passed, evidence in checks
    ]


def _decision(
    source: dict[str, Any],
    atom_rows: list[dict[str, Any]],
    math_checks: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    failed_atoms = [
        row["name"]
        for row in atom_rows
        if not row["passed_preflight"]
    ]
    failed_math = [
        check["name"]
        for check in math_checks
        if not check["passed"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not redesign atoms unless descriptor separability rejected threshold tuning."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using atom-schema preflight evidence."
    elif failed_atoms or failed_math:
        status = REJECT_STATUS
        next_step = "Reject this atom schema candidate set; fix missing fields or math checks first."
    else:
        status = READY_STATUS
        next_step = (
            "Run only an offline no-leak separability audit over the redesigned "
            "atom schema. Replay, formal seeds, online selector promotion, and "
            "CAMP retraining remain blocked."
        )
    return {
        "status": status,
        "failed_atoms": failed_atoms,
        "failed_math_checks": failed_math,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_redesigned_atom_separability_audit_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _spec_payload(spec: AtomSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_descriptors": list(spec.required_descriptors),
        "rationale": spec.rationale,
        "current_tick_only": True,
        "nonnegative_by_construction": True,
        "fixed_candidate_coefficient": True,
    }


def _summary(values: np.ndarray) -> dict[str, Any]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"n": 0, "mean": None, "min": None, "p50": None, "p95": None, "max": None}
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Atom Schema Redesign Preflight",
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
        "## Proposed Atoms",
        "",
        "| Atom | Pass | Records | Candidate Rows | p95 | Rationale |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["atom_reports"]:
        lines.append(
            f"| `{row['name']}` | `{row['passed_preflight']}` | "
            f"`{row['records_available']}/{row['records_total']}` | "
            f"`{row['candidate_rows_available']}/{row['candidate_rows_total']}` | "
            f"{_fmt(row['summary']['p95'])} | {row['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## Math Checks",
            "",
            "| Check | Passed | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["math_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {check['evidence']} |"
        )
    lines.extend(
        [
            "",
            "This is an atom-schema preflight only. It does not train weights, "
            "change online selection, run replay, modify DP, or authorize formal seeds.",
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
