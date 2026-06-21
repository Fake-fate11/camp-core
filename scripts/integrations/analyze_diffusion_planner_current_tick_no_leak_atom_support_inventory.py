#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_observable_state_inventory import (  # noqa: E402
    PROBES,
    Probe,
    _family_reports,
    _is_formal_seed,
    _probe_report,
    _record_summary,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)
from scripts.integrations.plan_diffusion_planner_no_leak_atom_or_proof_objective_redesign import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_NEXT_WORK,
    READY_STATUS as SOURCE_STATUS,
)


READY_STATUS = (
    "current_tick_no_leak_atom_support_inventory_has_admissible_unclosed_fields"
)
REJECT_STATUS = "current_tick_no_leak_atom_support_inventory_no_unclosed_fields"
SOURCE_BLOCKED_STATUS = "current_tick_no_leak_atom_support_inventory_source_not_ready"
FORMAL_SEED_STATUS = "current_tick_no_leak_atom_support_inventory_formal_seed_conflict"

MIN_COMPLETE_RECORD_RATE = 0.95
MIN_ADMISSIBLE_FAMILIES = 1

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Current-tick no-leak atom support inventory after the redesign "
            "plan gate. It reads existing CAMP selection logs only and does "
            "not train, replay, run DP, or change selection."
        )
    )
    parser.add_argument("--redesign_plan_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument(
        "--min_complete_record_rate",
        type=float,
        default=MIN_COMPLETE_RECORD_RATE,
    )
    parser.add_argument(
        "--min_admissible_families",
        type=int,
        default=MIN_ADMISSIBLE_FAMILIES,
    )
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
        redesign_plan_report=_load_json(args.redesign_plan_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        min_complete_record_rate=args.min_complete_record_rate,
        min_admissible_families=args.min_admissible_families,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    redesign_plan_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    min_complete_record_rate: float = MIN_COMPLETE_RECORD_RATE,
    min_admissible_families: int = MIN_ADMISSIBLE_FAMILIES,
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
        redesign_plan_report=redesign_plan_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        fail_on_formal_seeds=fail_on_formal_seeds,
        min_complete_record_rate=min_complete_record_rate,
        min_admissible_families=min_admissible_families,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    redesign_plan_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    fail_on_formal_seeds: bool = False,
    probes: tuple[Probe, ...] = PROBES,
    min_complete_record_rate: float = MIN_COMPLETE_RECORD_RATE,
    min_admissible_families: int = MIN_ADMISSIBLE_FAMILIES,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    if not 0.0 <= min_complete_record_rate <= 1.0:
        raise ValueError("min_complete_record_rate must be in [0, 1].")
    if min_admissible_families < 0:
        raise ValueError("min_admissible_families must be nonnegative.")

    source = _source_gate(redesign_plan_report)
    formal_seed_records = sum(int(_is_formal_seed(item["context"])) for item in items)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    probe_reports = [_probe_report(probe, items) for probe in probes]
    family_reports = _family_reports(probe_reports, min_complete_record_rate)
    field_inventory = _field_inventory(family_reports)
    decision = _decision(
        source,
        field_inventory,
        formal_seed_records=formal_seed_records,
        min_admissible_families=min_admissible_families,
    )
    return {
        "analysis": {
            "name": "dp_camp_current_tick_no_leak_atom_support_inventory_v1",
            "label": label,
            "role": (
                "read-only inventory of current-tick candidate fields after "
                "the objective/label sensitivity route is rejected"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_inspected": False,
            "future_outcome_leakage": False,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "min_complete_record_rate": float(min_complete_record_rate),
            "min_admissible_families": int(min_admissible_families),
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This "
                "inventory reads only fields available in existing selection "
                "logs before any new online decision. It does not inspect "
                "closed-loop outcome labels, create atoms, train weights, run "
                "replay, or change selection. A later atom may use only fixed "
                "current-tick finite-candidate coefficients a_k, preferably "
                "nonnegative or signed-split, so score_k(w)=a_k^T w stays "
                "affine and the simplex/CVaR/L2 master remains convex. No "
                "DP-side classical Benders decomposition is claimed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_redesign_plan_gate": source,
        "records": _record_summary(items, formal_seed_records),
        "probe_reports": probe_reports,
        "family_reports": family_reports,
        "field_inventory": field_inventory,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    conflicts = [
        key for key in BLOCKED_ACTIONS if bool(final.get(key))
    ]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "recommended_first_action": final.get("recommended_first_action"),
        "blocked_action_conflicts": conflicts,
    }


def _field_inventory(family_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in family_reports:
        roles = set(str(role) for role in report["roles"])
        candidate_level = bool(report["candidate_level"])
        status = str(report["status"])
        if "new_candidate_state" in roles and candidate_level and status == "available":
            support_status = "admissible_unclosed_candidate_support"
        elif "new_candidate_state" in roles and candidate_level and status == "partial":
            support_status = "partial_candidate_support_requires_logging"
        elif "new_candidate_state" in roles and candidate_level:
            support_status = "candidate_support_unavailable"
        elif any(role.startswith("existing_") for role in roles):
            support_status = "available_existing_or_closed_proxy"
        elif "diagnostic_only" in roles:
            support_status = "diagnostic_only_not_selector_input"
        else:
            support_status = "not_candidate_level_atom_support"
        rows.append(
            {
                "family": report["family"],
                "roles": report["roles"],
                "candidate_level": candidate_level,
                "source_status": status,
                "support_status": support_status,
                "best_probe": report["best_probe"],
                "best_path": report["best_path"],
                "best_record_complete_rate": report["best_record_complete_rate"],
                "best_record_present_rate": report["best_record_present_rate"],
            }
        )
    return rows


def _decision(
    source: dict[str, Any],
    field_inventory: list[dict[str, Any]],
    *,
    formal_seed_records: int,
    min_admissible_families: int,
) -> dict[str, Any]:
    admissible = [
        row
        for row in field_inventory
        if row["support_status"] == "admissible_unclosed_candidate_support"
    ]
    partial = [
        row
        for row in field_inventory
        if row["support_status"] == "partial_candidate_support_requires_logging"
    ]
    existing = [
        row
        for row in field_inventory
        if row["support_status"] == "available_existing_or_closed_proxy"
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "redesign_plan_source_not_ready"
        authorized_next_work = None
        next_step = "Repair or rerun the redesign plan gate before inventory."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        authorized_next_work = None
        next_step = "Exclude formal seeds before using this inventory as evidence."
    elif len(admissible) >= min_admissible_families:
        status = READY_STATUS
        primary_gap = "admissible_unclosed_current_tick_candidate_support_found"
        authorized_next_work = "predeclare_no_leak_atom_schema_from_inventory_design_only"
        next_step = (
            "Write a design-only atom schema preflight for the admissible "
            "families; keep replay, training, online selection, and formal "
            "seeds disabled."
        )
    else:
        status = REJECT_STATUS
        primary_gap = "no_admissible_unclosed_current_tick_candidate_support"
        authorized_next_work = "proof_objective_v2_or_default_off_logging_preflight_design_only"
        next_step = (
            "Do not train or replay from the current logs. Either redesign the "
            "proof objective or predeclare default-off logging for missing "
            "candidate-level state before another atom family."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "admissible_unclosed_candidate_families": [row["family"] for row in admissible],
        "partial_candidate_families": [row["family"] for row in partial],
        "available_existing_or_closed_proxy_families": [
            row["family"] for row in existing
        ],
        "authorized_next_work": authorized_next_work,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Current-Tick No-Leak Atom Support Inventory",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Field Inventory",
        "",
        "| Family | Support status | Source status | Best probe | Complete | Present |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in report["field_inventory"]:
        lines.append(
            f"| `{row['family']}` | `{row['support_status']}` | "
            f"`{row['source_status']}` | `{row['best_probe']}` | "
            f"`{row['best_record_complete_rate']:.6g}` | "
            f"`{row['best_record_present_rate']:.6g}` |"
        )
    lines.extend(
        [
            "",
            "This inventory does not authorize training, replay, Full36, formal "
            "seeds, online selector promotion, DP modification, or a classical "
            "Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
