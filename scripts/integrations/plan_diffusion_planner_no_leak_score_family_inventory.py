#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_SCORE_FAMILIES = (
    "progress_lane_hard_context",
    "revised_context_atom_family",
    "relaxed_strict_atom_family",
    "observable_interaction_family",
    "turn_logit_atom_family",
    "non_turn_interaction_family",
)

BLOCKED_ACTION_KEYS = (
    "closed_loop_smoke_authorized",
    "new_replay_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only no-leak score-family inventory for CAMP-on-DP. It "
            "summarizes existing gate artifacts before starting another "
            "current-tick descriptor or score-family design loop."
        )
    )
    parser.add_argument(
        "--family_json",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Named score-family evidence JSON to include in the inventory.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence = [_load_named_json(item) for item in args.family_json]
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
        raise ValueError("At least one family evidence JSON is required.")
    entries = [_entry(item) for item in evidence]
    families = _family_summary(entries)
    conflicts = _authorization_conflicts(entries)
    decision = _decision(families, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_no_leak_score_family_inventory_v1",
            "label": label,
            "role": (
                "read-only inventory of already tested no-leak score or "
                "descriptor families before another CAMP-on-DP design loop"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This inventory reads only prior gate decisions. It does not "
                "create atoms, train weights, run Diffusion Planner, use "
                "outcome labels as runtime inputs, or construct a Benders "
                "master/subproblem. Any later atom must be a current-tick "
                "finite-candidate coefficient so score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 robust master remains convex."
            ),
        },
        "records": {
            "evidence_count": len(entries),
            "required_score_families": list(REQUIRED_SCORE_FAMILIES),
        },
        "evidence": entries,
        "score_families": families,
        "source_authorization_conflicts": conflicts,
        "blocked_actions": {key: False for key in BLOCKED_ACTION_KEYS},
        "final_decision": decision,
    }


def _entry(item: dict[str, Any]) -> dict[str, Any]:
    payload = item["payload"]
    status = _decision_status(payload)
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    family = _score_family(item["name"], status, str(analysis.get("name") or ""))
    return {
        "name": item["name"],
        "path": item.get("path"),
        "analysis_name": analysis.get("name"),
        "status": status,
        "score_family": family,
        "classification": _classification(status),
        "authorized_next_work": _authorized_next_work(payload),
        "blocked_action_flags": _blocked_action_flags(payload),
    }


def _decision_status(payload: dict[str, Any]) -> str:
    for path in (
        ("final_decision", "status"),
        ("decision", "status"),
        ("status",),
    ):
        value = _get(payload, *path)
        if value is not None:
            return str(value)
    return ""


def _authorized_next_work(payload: dict[str, Any]) -> str | None:
    for path in (
        ("final_decision", "authorized_next_work"),
        ("decision", "authorized_next_work"),
        ("next_gate", "authorized_next_work"),
    ):
        value = _get(payload, *path)
        if value is not None:
            return str(value)
    return None


def _blocked_action_flags(payload: dict[str, Any]) -> dict[str, bool]:
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    return {key: bool(decision.get(key)) for key in BLOCKED_ACTION_KEYS}


def _score_family(name: str, status: str, analysis_name: str) -> str:
    text = f"{name} {status} {analysis_name}".lower()
    if "observable_interaction" in text:
        return "observable_interaction_family"
    if "non_turn_logit" in text or "non_turn_interaction" in text:
        return "non_turn_interaction_family"
    if "turn_logit" in text or "turn_indicator" in text:
        return "turn_logit_atom_family"
    if "relaxed_strict" in text:
        return "relaxed_strict_atom_family"
    if "revised_context" in text or "revised_progress_lane_hard" in text:
        return "revised_context_atom_family"
    if "progress_lane_hard_context" in text or "progress+lane/hard" in text:
        return "progress_lane_hard_context"
    return "other"


def _classification(status: str) -> str:
    lower = status.lower()
    if not lower:
        return "missing_status"
    if "conflict" in lower:
        return "source_conflict"
    if any(
        token in lower
        for token in (
            "rejected",
            "insufficient",
            "observability_limit_recorded",
            "bottleneck_diagnosed",
            "current_route_rejected",
            "family_rejected",
        )
    ):
        return "rejected_or_limited"
    if any(token in lower for token in ("ready", "passed", "support_present", "plan_ready")):
        return "unresolved_support_present"
    return "inconclusive"


def _family_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["score_family"]].append(entry)

    rows: list[dict[str, Any]] = []
    for family in sorted(set(REQUIRED_SCORE_FAMILIES) | set(grouped)):
        family_entries = grouped.get(family, [])
        classes = [entry["classification"] for entry in family_entries]
        if "source_conflict" in classes:
            status = "source_conflict"
        elif "rejected_or_limited" in classes:
            status = "rejected_or_limited"
        elif "unresolved_support_present" in classes:
            status = "unresolved_support_present"
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
                "authorized_next_work": [
                    entry["authorized_next_work"]
                    for entry in family_entries
                    if entry["authorized_next_work"]
                ],
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
        for family in REQUIRED_SCORE_FAMILIES
        if family_status.get(family) in {None, "missing_evidence", "inconclusive"}
    ]
    unresolved = [
        family
        for family in REQUIRED_SCORE_FAMILIES
        if family_status.get(family) == "unresolved_support_present"
    ]
    if conflicts:
        status = "no_leak_score_family_inventory_source_conflict"
        next_step = "Resolve source authorization conflicts before using this inventory."
    elif missing:
        status = "no_leak_score_family_inventory_incomplete_evidence"
        next_step = (
            "Provide missing family evidence before declaring the current "
            "no-leak score-family cycle exhausted."
        )
    elif unresolved:
        status = "no_leak_score_family_inventory_has_unclosed_support"
        next_step = (
            "Close support-present families with a separability or bottleneck "
            "gate before designing another descriptor family."
        )
    else:
        status = "no_leak_score_family_inventory_requires_new_design"
        next_step = (
            "Do not tune the rejected progress/lane-hard, revised-context, "
            "relaxed-strict, observable-interaction, turn-logit, or non-turn "
            "interaction families. Predeclare a genuinely new current-tick "
            "no-leak descriptor family or return to a broader observable-state "
            "inventory before any replay."
        )
    return {
        "status": status,
        "missing_or_inconclusive_families": missing,
        "unclosed_support_families": unresolved,
        "source_authorization_conflicts": conflicts,
        "authorized_next_work": (
            "predeclare_new_current_tick_no_leak_descriptor_family_or_"
            "observable_state_inventory_design_only"
        ),
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP No-Leak Score-Family Inventory",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Score Families",
        "",
        "| Family | Status | Evidence | Source statuses |",
        "| --- | --- | ---: | --- |",
    ]
    for family in report["score_families"]:
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
            "| Name | Family | Status | Classification | Authorized next work |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for entry in report["evidence"]:
        lines.append(
            f"| `{entry['name']}` | `{entry['score_family']}` | "
            f"`{entry['status']}` | `{entry['classification']}` | "
            f"`{entry['authorized_next_work'] or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This inventory is not a selector, not a replay result, not CAMP "
            "training, and not a classical Benders decomposition.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_named_json(value: str) -> dict[str, Any]:
    if "=" not in value:
        raise ValueError("--family_json must use NAME=PATH.")
    name, raw_path = value.split("=", 1)
    name = name.strip()
    path = Path(raw_path.strip())
    if not name:
        raise ValueError("Family evidence name must be nonempty.")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return {"name": name, "path": str(path), "payload": payload}


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
