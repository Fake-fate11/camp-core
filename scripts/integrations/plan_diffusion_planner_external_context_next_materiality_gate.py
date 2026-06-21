#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "external_context_materiality_gap_diagnosed"

READY_STATUS = "external_context_next_materiality_gate_ready"
REJECT_STATUS = "external_context_next_materiality_gate_rejected"

SIGNAL_WIRING_NEXT_WORK = "external_context_signal_context_wiring_preflight_design_only"
ROUTE_ASSET_NEXT_WORK = "external_context_route_asset_materiality_screen_plan_only"

REQUIRED_ROUTE_SPEED_GAPS = frozenset(
    {
        "route_speed_context_available_but_no_candidate_excess",
        "route_speed_availability_constant",
        "nonmaterial_constant_speed_limit",
    }
)
REQUIRED_SIGNAL_GAP = "traffic_signal_context_absent"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only next-materiality gate after an external-context "
            "materiality rejection. It decides whether the next smaller gate "
            "should be signal-context wiring preflight or route-asset "
            "materiality screening. It does not run DP, train CAMP, or change "
            "selection."
        )
    )
    parser.add_argument("--gap_json", type=Path, required=True)
    parser.add_argument("--camp_replay_source", type=Path, required=True)
    parser.add_argument("--dp_source_root", type=Path, default=None)
    parser.add_argument("--route_asset", action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--targeted_route_speed_probe_executed",
        action="store_true",
        help=(
            "Require that the consumed gap is from the bounded route-speed "
            "targeted probe, so the gate may close the current route/noise path."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        gap=_load_json(args.gap_json),
        camp_replay_source=args.camp_replay_source,
        dp_source_root=args.dp_source_root,
        route_assets=[Path(path) for path in args.route_asset],
        targeted_route_speed_probe_executed=bool(
            args.targeted_route_speed_probe_executed
        ),
        label=args.label,
        paths={
            "gap_json": str(args.gap_json),
            "camp_replay_source": str(args.camp_replay_source),
            "dp_source_root": str(args.dp_source_root)
            if args.dp_source_root is not None
            else None,
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    gap: dict[str, Any],
    camp_replay_source: Path,
    dp_source_root: Path | None,
    route_assets: list[Path],
    targeted_route_speed_probe_executed: bool,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    source_gap = _source_gap(gap)
    source_checks = _source_checks(source_gap)
    camp_wiring = _camp_signal_wiring(camp_replay_source)
    dp_signal = _dp_signal_source(dp_source_root)
    route_assets_report = _route_asset_report(route_assets)

    route_speed_path_closed = bool(
        targeted_route_speed_probe_executed
        and source_gap["passed"]
        and REQUIRED_ROUTE_SPEED_GAPS.issubset(set(source_gap["gap_names"]))
    )
    signal_context_missing = REQUIRED_SIGNAL_GAP in source_gap["gap_names"]
    signal_wiring_candidate = bool(
        signal_context_missing
        and dp_signal["traffic_signal_source_visible"]
        and camp_wiring["status"] == "signal_context_explicitly_absent"
    )
    route_asset_candidate = bool(
        route_speed_path_closed and route_assets_report["screen_candidate_count"] > 0
    )

    decision = _decision(
        source_ready=all(check["passed"] for check in source_checks),
        signal_wiring_candidate=signal_wiring_candidate,
        route_asset_candidate=route_asset_candidate,
        route_speed_path_closed=route_speed_path_closed,
        signal_context_missing=signal_context_missing,
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_next_materiality_gate_v1",
            "label": label,
            "role": (
                "plan-only route selection after real external-context "
                "materiality rejection"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads existing gap artifacts and source text only. "
                "It creates no atom, runs no replay, trains no CAMP weights, "
                "and changes no selector. Future signal or route-speed atoms "
                "must be fixed current-tick finite-candidate coefficients, "
                "nonnegative or signed-split before scoring, so score_k(w)=a_k^T w "
                "remains affine and the simplex/CVaR/L2 master remains convex. "
                "No DP-side classical Benders master/subproblem, dual, or cut is "
                "constructed."
            ),
        },
        "source_gap": source_gap,
        "source_checks": source_checks,
        "camp_signal_wiring": camp_wiring,
        "dp_signal_source": dp_signal,
        "route_asset_screen": route_assets_report,
        "route_speed_path_closed_for_current_route": route_speed_path_closed,
        "signal_context_missing": signal_context_missing,
        "signal_wiring_candidate": signal_wiring_candidate,
        "route_asset_candidate": route_asset_candidate,
        "targeted_route_speed_probe_executed": bool(
            targeted_route_speed_probe_executed
        ),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gap(gap: dict[str, Any]) -> dict[str, Any]:
    final = gap.get("final_decision") or {}
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "gap_names": list(final.get("gap_names") or []),
        "new_replay_authorized": bool(final.get("new_replay_authorized")),
        "camp_retraining_authorized": bool(final.get("camp_retraining_authorized")),
        "formal_seeds_authorized": bool(final.get("formal_seeds_authorized")),
        "dp_modification_authorized": bool(final.get("dp_modification_authorized")),
        "classic_benders_claim_authorized": bool(
            final.get("classic_benders_claim_authorized")
        ),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_gap_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_gap_passed", source["passed"], True),
        _check_equal("source_new_replay_not_authorized", source["new_replay_authorized"], False),
        _check_equal(
            "source_training_not_authorized",
            source["camp_retraining_authorized"],
            False,
        ),
        _check_equal(
            "source_formal_not_authorized",
            source["formal_seeds_authorized"],
            False,
        ),
        _check_equal(
            "source_dp_modification_not_authorized",
            source["dp_modification_authorized"],
            False,
        ),
        _check_equal(
            "source_classic_benders_not_authorized",
            source["classic_benders_claim_authorized"],
            False,
        ),
    ]


def _camp_signal_wiring(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    has_payload_call = "build_external_context_payload(" in text
    explicitly_absent = "signal_context=None" in text
    if not has_payload_call:
        status = "payload_call_not_found"
    elif explicitly_absent:
        status = "signal_context_explicitly_absent"
    elif "signal_context=" in text:
        status = "signal_context_argument_present"
    else:
        status = "signal_context_wiring_unknown"
    return {
        "path": str(path),
        "payload_call_visible": has_payload_call,
        "signal_context_none_visible": explicitly_absent,
        "status": status,
    }


def _dp_signal_source(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {
            "root": None,
            "traffic_signal_source_visible": False,
            "matched_files": [],
            "missing_reason": "dp_source_root_absent",
        }
    files = [
        path
        for path in root.rglob("*.py")
        if path.is_file() and _is_runtime_source(path)
    ]
    matched: list[str] = []
    for path in files:
        text = _read_text(path)
        if (
            "TrafficLightController" in text
            and ("def tick" in text or ".tick(" in text)
            and (
                "_GroupState" in text
                or "write_to_route_lanes" in text
                or "color_for_lanelet" in text
            )
        ):
            matched.append(str(path))
    return {
        "root": str(root),
        "traffic_signal_source_visible": bool(matched),
        "matched_files": sorted(matched),
        "missing_reason": None if matched else "traffic_signal_runtime_source_not_visible",
    }


def _is_runtime_source(path: Path) -> bool:
    normalized = "/" + str(path).replace("\\", "/")
    runtime_markers = (
        "/scenario_generation/",
        "/diffusion_planner_ros/",
        "/diffusion_planner/diffusion_planner/model/",
    )
    blocked_markers = ("/tests/", "/docs/", "/train_", "/rlvr/")
    return any(marker in normalized for marker in runtime_markers) and not any(
        marker in normalized for marker in blocked_markers
    )


def _route_asset_report(route_assets: list[Path]) -> dict[str, Any]:
    rows = []
    for path in route_assets:
        name = path.name
        lower = name.lower()
        family = (
            "traffic_signal"
            if "_tl_" in lower or lower.startswith("sample_map_tl")
            else "nishishinjuku"
            if "nishishinjuku" in lower
            else "generic_route"
        )
        screen_candidate = bool(
            lower.endswith(".pkl")
            and (
                family == "traffic_signal"
                or "lane_change" in lower
                or family == "nishishinjuku"
            )
        )
        rows.append(
            {
                "path": str(path),
                "name": name,
                "family": family,
                "screen_candidate": screen_candidate,
            }
        )
    return {
        "route_asset_count": len(rows),
        "screen_candidate_count": sum(1 for row in rows if row["screen_candidate"]),
        "screen_candidate_names": [
            row["name"] for row in rows if row["screen_candidate"]
        ],
        "rows": rows,
    }


def _decision(
    *,
    source_ready: bool,
    signal_wiring_candidate: bool,
    route_asset_candidate: bool,
    route_speed_path_closed: bool,
    signal_context_missing: bool,
) -> dict[str, Any]:
    if not source_ready:
        status = REJECT_STATUS
        passed = False
        primary_gap = "source_gap_not_ready"
        next_work = None
        next_step = "Repair or rerun the external-context materiality gap diagnosis."
    elif signal_wiring_candidate:
        status = READY_STATUS
        passed = True
        primary_gap = "traffic_signal_source_visible_but_signal_context_not_wired"
        next_work = SIGNAL_WIRING_NEXT_WORK
        next_step = (
            "Predeclare signal-context wiring preflight. Keep it default-off, "
            "fail-closed, source-only, and do not run a new replay until the "
            "preflight contract passes."
        )
    elif route_asset_candidate:
        status = READY_STATUS
        passed = True
        primary_gap = "current_route_speed_probe_closed_but_alternate_assets_exist"
        next_work = ROUTE_ASSET_NEXT_WORK
        next_step = (
            "Predeclare a route-asset materiality screen plan before any new "
            "smoke. The screen must not train CAMP, use formal seeds, or modify DP."
        )
    else:
        status = REJECT_STATUS
        passed = True
        primary_gap = "no_smaller_materiality_gate_available"
        next_work = "pause_external_context_route_or_supply_new_source"
        next_step = (
            "Reject further external-context replay until a no-leak runtime "
            "source or route/materiality hypothesis is supplied."
        )
    return {
        "status": status,
        "passed": passed,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "route_speed_path_closed_for_current_route": route_speed_path_closed,
        "signal_context_missing": signal_context_missing,
        "signal_wiring_candidate": signal_wiring_candidate,
        "route_asset_candidate": route_asset_candidate,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Next Materiality Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Gate Inputs",
        "",
        f"- Source gap status: `{report['source_gap']['status']}`",
        f"- Present gaps: `{', '.join(report['source_gap']['gap_names'])}`",
        f"- Targeted route-speed probe executed: "
        f"`{report['targeted_route_speed_probe_executed']}`",
        f"- Route-speed path closed for current route: "
        f"`{report['route_speed_path_closed_for_current_route']}`",
        f"- Signal context missing: `{report['signal_context_missing']}`",
        "",
        "## Source Evidence",
        "",
        f"- CAMP signal wiring: `{report['camp_signal_wiring']['status']}`",
        f"- DP traffic-signal source visible: "
        f"`{report['dp_signal_source']['traffic_signal_source_visible']}`",
        f"- Route asset screen candidates: "
        f"`{report['route_asset_screen']['screen_candidate_count']}`",
        "",
        "## Candidate Route Assets",
        "",
        "| Name | Family | Screen Candidate |",
        "| --- | --- | ---: |",
    ]
    for row in report["route_asset_screen"]["rows"]:
        lines.append(
            f"| `{row['name']}` | `{row['family']}` | `{row['screen_candidate']}` |"
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


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


if __name__ == "__main__":
    main()
