#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)

REQUIRED_FAMILIES = (
    "dp_candidate_native_selector",
    "mode_seeking_candidate_generation",
    "source_donor_or_graft_transform",
    "lane_projected_stop_target",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DP-CAMP next-design boundary ledger. It consumes existing "
            "audit JSON files and summarizes which route families are already "
            "rejected before authorizing any further offline design work."
        )
    )
    parser.add_argument(
        "--evidence_json",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Named evidence JSON to include in the ledger.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence = [_load_named_json(item) for item in args.evidence_json]
    report = build_report(evidence, label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    evidence: list[dict[str, Any]],
    *,
    label: str | None = None,
) -> dict[str, Any]:
    if not evidence:
        raise ValueError("At least one evidence JSON is required.")
    entries = [_entry(item) for item in evidence]
    families = _family_summary(entries)
    conflicts = _authorization_conflicts(entries)
    decision = _decision(families, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_next_design_boundary_v1",
            "label": label,
            "role": (
                "read-only route-family evidence ledger before another DP-CAMP "
                "offline design loop"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This ledger only reads prior audit decisions. It does not "
                "generate trajectories, modify DP, modify CAMP weights, add "
                "runtime atoms, or construct a Benders master/subproblem. Any "
                "next design must still use fixed current-tick finite-candidate "
                "quantities so CAMP scores remain affine a_k^T w and the "
                "simplex/CVaR/L2 robust master remains convex."
            ),
        },
        "records": {
            "evidence_count": len(entries),
            "required_route_families": list(REQUIRED_FAMILIES),
        },
        "evidence": entries,
        "route_families": families,
        "source_authorization_conflicts": conflicts,
        "next_design_boundary": _next_design_boundary(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _entry(item: dict[str, Any]) -> dict[str, Any]:
    payload = item["payload"]
    decision = payload.get("final_decision") or {}
    status = str(decision.get("status") or "")
    analysis = payload.get("analysis") or {}
    family = _route_family(item["name"], status, str(analysis.get("name") or ""))
    return {
        "name": item["name"],
        "path": item.get("path"),
        "analysis_name": analysis.get("name"),
        "status": status,
        "route_family": family,
        "classification": _classification(status),
        "next_step": decision.get("next_step"),
        "blocked_action_flags": {
            key: bool(decision.get(key)) for key in BLOCKED_ACTIONS
        },
    }


def _route_family(name: str, status: str, analysis_name: str) -> str:
    text = f"{name} {status} {analysis_name}".lower()
    if any(token in text for token in ("latest_safe", "route_topology", "lane_projected")):
        return "lane_projected_stop_target"
    if any(token in text for token in ("source_donor", "graft", "donor_tail", "bridge")):
        return "source_donor_or_graft_transform"
    if any(token in text for token in ("mode_seeking", "candidate_generation")):
        return "mode_seeking_candidate_generation"
    if any(
        token in text
        for token in (
            "descriptor",
            "atom_aware",
            "score_margin",
            "guarded_selector",
            "composite_guard",
            "candidate_support_quality",
            "finite_filter",
        )
    ):
        return "dp_candidate_native_selector"
    if any(token in text for token in ("dense_lane_change", "feasible_support")):
        return "dp_candidate_native_selector"
    return "other"


def _classification(status: str) -> str:
    lower = status.lower()
    if any(token in lower for token in ("conflict", "source_conflict")):
        return "conflict"
    if any(token in lower for token in ("ready", "support_present", "passed")):
        return "support_present"
    if any(token in lower for token in ("reject", "insufficient", "limited", "blocked")):
        return "rejected_or_blocked"
    if not status:
        return "missing_status"
    return "inconclusive"


def _family_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["route_family"]].append(entry)
    rows: list[dict[str, Any]] = []
    for family in sorted(set(REQUIRED_FAMILIES) | set(grouped)):
        family_entries = grouped.get(family, [])
        classes = [entry["classification"] for entry in family_entries]
        if "conflict" in classes:
            status = "source_conflict"
        elif "support_present" in classes and "rejected_or_blocked" not in classes:
            status = "support_present"
        elif "rejected_or_blocked" in classes:
            status = "rejected_or_blocked"
        elif family_entries:
            status = "inconclusive"
        else:
            status = "missing_evidence"
        rows.append(
            {
                "name": family,
                "status": status,
                "evidence_count": len(family_entries),
                "evidence_names": [entry["name"] for entry in family_entries],
                "statuses": [entry["status"] for entry in family_entries],
            }
        )
    return rows


def _authorization_conflicts(entries: list[dict[str, Any]]) -> list[str]:
    conflicts: list[str] = []
    for entry in entries:
        for key, value in entry["blocked_action_flags"].items():
            if value:
                conflicts.append(f"{entry['name']}:{key}")
    return conflicts


def _decision(
    families: list[dict[str, Any]],
    conflicts: list[str],
) -> dict[str, Any]:
    family_status = {row["name"]: row["status"] for row in families}
    missing = [
        family
        for family in REQUIRED_FAMILIES
        if family_status.get(family) in {None, "missing_evidence", "inconclusive"}
    ]
    support_present = [
        family
        for family in REQUIRED_FAMILIES
        if family_status.get(family) == "support_present"
    ]
    if conflicts:
        status = "next_design_boundary_source_conflict"
        next_step = "Resolve source authorization conflicts before using this ledger."
    elif missing:
        status = "next_design_boundary_incomplete_evidence"
        next_step = "Add missing route-family evidence before declaring routes exhausted."
    elif support_present:
        status = "next_design_boundary_has_unresolved_support"
        next_step = "Inspect support-present route families before moving to a new design."
    else:
        status = "next_design_boundary_requires_new_offline_design"
        next_step = (
            "Do not repeat selector thresholds, lane-projected stops, mode-seeking "
            "route/lane guidance, or source-donor grafts. Define a materially new "
            "offline-only no-leak candidate-support gate before any replay."
        )
    return {
        "status": status,
        "missing_or_inconclusive_families": missing,
        "support_present_families": support_present,
        "source_authorization_conflicts": conflicts,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "next_step": next_step,
    }


def _next_design_boundary() -> dict[str, Any]:
    return {
        "authorized_next_work": "new_predeclared_offline_no_leak_design_gate_only",
        "must_not_repeat": [
            "dense lane-change loose finite filters",
            "descriptor-only or atom-aware threshold screens over the same support",
            "current mode-seeking route/lane guidance",
            "source-donor graft/bridge variants that rely on rejected lower-red donors",
            "lane-projected stop-target transforms",
        ],
        "required_properties": [
            "fixed DP source and weights",
            "formal-seed exclusion",
            "current-tick finite-candidate features only",
            "fail-closed deterministic metadata",
            "predeclared safety, progress, comfort, support, and latency gates",
        ],
        "blocked_until_gate_passes": list(BLOCKED_ACTIONS),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP Next Design Boundary",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Route Families",
        "",
        "| Family | Status | Evidence | Source statuses |",
        "| --- | --- | ---: | --- |",
    ]
    for family in report["route_families"]:
        statuses = ", ".join(f"`{status}`" for status in family["statuses"])
        lines.append(
            f"| `{family['name']}` | `{family['status']}` | "
            f"`{family['evidence_count']}` | {statuses or '`none`'} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Name | Family | Status | Classification |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in report["evidence"]:
        lines.append(
            f"| `{entry['name']}` | `{entry['route_family']}` | "
            f"`{entry['status']}` | `{entry['classification']}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Authorized next work: `{report['next_design_boundary']['authorized_next_work']}`",
            f"- Blocked actions: `{', '.join(report['next_design_boundary']['blocked_until_gate_passes'])}`",
            "",
            "This is a read-only evidence ledger. It does not run Diffusion "
            "Planner, change CAMP, train weights, or claim classical Benders "
            "decomposition. Any next design must preserve the fixed finite "
            "candidate boundary so CAMP scoring remains affine in `w`.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_named_json(value: str) -> dict[str, Any]:
    if "=" not in value:
        raise ValueError("--evidence_json must use NAME=PATH.")
    name, raw_path = value.split("=", 1)
    name = name.strip()
    path = Path(raw_path.strip())
    if not name:
        raise ValueError("Evidence name must be nonempty.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return {"name": name, "path": str(path), "payload": payload}


if __name__ == "__main__":
    main()
