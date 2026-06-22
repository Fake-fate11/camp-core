#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_candidate_generation_support_redesign import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_route_topology_comfort_support_preflight_ready"
REJECT_STATUS = "candidate_set_consensus_route_topology_comfort_support_preflight_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_design_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SPLICE_ROOT = (
    "/root/autodl-tmp/camp_dp_splice_transform_design_screen_347ae79_seed2_npc4_tlon"
)
DEFAULT_SOURCE_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_candidate_generation_"
    "support_redesign_plan_328c354"
)
DEFAULT_EVIDENCE_PATHS = {
    "route_topology_readiness": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_support_gate_d0a5e4b/"
        "route_topology_support_gate.json"
    ),
    "constant_red_stop_screen": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_candidate_screen_53fd5a5/"
        "route_topology_candidate_screen.json"
    ),
    "prefix_comfort_screen": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_comfort_transfer_screen_1f9f245/"
        "route_topology_comfort_transfer_screen.json"
    ),
    "constant_absolute_lateral_guard": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_absolute_lateral_guard_c1cfb57_constant/"
        "absolute_lateral_guard.json"
    ),
    "prefix_absolute_lateral_guard": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_absolute_lateral_guard_c1cfb57_prefix/"
        "absolute_lateral_guard.json"
    ),
    "lane_projected_screen": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_lane_projected_screen_f172bdb/"
        "route_topology_lane_projected_screen.json"
    ),
    "lane_projected_absolute_lateral_guard": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_lane_projected_absolute_lateral_guard_f172bdb/"
        "absolute_lateral_guard.json"
    ),
    "prefix_lane_projected_screen": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_prefix_lane_projected_screen_98fde10/"
        "route_topology_prefix_lane_projected_screen.json"
    ),
    "prefix_lane_projected_absolute_lateral_guard": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_prefix_lane_projected_absolute_lateral_guard_98fde10/"
        "absolute_lateral_guard.json"
    ),
    "latest_safe_screen": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_latest_safe_screen_e7b0f21/"
        "route_topology_latest_safe_screen.json"
    ),
    "latest_safe_failure_patterns": (
        f"{DEFAULT_SPLICE_ROOT}/route_topology_latest_safe_failure_patterns_ec19970/"
        "route_topology_failure_patterns.json"
    ),
}

SOURCE_JSON = "candidate_set_consensus_candidate_generation_support_redesign_plan.json"
SOURCE_MD = "candidate_set_consensus_candidate_generation_support_redesign_plan.md"
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "candidate_generation_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only route/topology comfort-support preflight after the "
            "candidate-set consensus support-redesign gate. It reads existing "
            "fixed artifacts only and selects a jerk/progress design plan."
        )
    )
    parser.add_argument("--support_redesign_root", type=Path, default=Path(DEFAULT_SOURCE_ROOT))
    parser.add_argument(
        "--evidence_json",
        action="append",
        default=[],
        help="Evidence mapping as name=/path/to/artifact.json",
    )
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_redesign_root=args.support_redesign_root,
        evidence_paths=_evidence_paths(args.evidence_json),
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
        label=args.label,
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
    support_redesign_root: Path,
    evidence_paths: dict[str, Path],
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(support_redesign_root)
    source = _source_summary(artifact.get("json_payload") or {})
    evidence = _evidence_summary(evidence_paths)
    preflight = _preflight_plan(source, evidence)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_evidence_checks(evidence),
        *_preflight_checks(preflight),
        *_boundary_checks(preflight),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_route_topology_comfort_support_preflight_v1",
            "label": label,
            "role": (
                "preflight-only synthesis of existing route/topology comfort "
                "support evidence before any new candidate generation design"
            ),
            "plan_only": True,
            "preflight_only": True,
            "candidate_generation_execution": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This preflight reads only existing fixed artifacts and "
                "fixed-head audit. It does not generate candidates, run DP, "
                "run replay, recompute outcomes, define runtime atoms, choose "
                "lambda online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "support_redesign_artifact": _strip_payload(artifact),
        "source_summary": source,
        "evidence_summary": evidence,
        "preflight_plan": preflight,
        "preflight_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["preflight_plan"]
    lines = [
        "# Candidate-Set Consensus Route/Topology Comfort-Support Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{plan['selected_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Evidence Inputs",
        "",
    ]
    for name, item in sorted(report["evidence_summary"].items()):
        lines.append(f"- `{name}`: status `{item['status']}`, present `{item['present']}`")
    lines.extend(["", "## Preflight Conclusions", ""])
    for item in plan["conclusions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Next Design Plan", ""])
    for item in plan["required_next_design_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["preflight_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _evidence_paths(items: list[str]) -> dict[str, Path]:
    paths = {name: Path(value) for name, value in DEFAULT_EVIDENCE_PATHS.items()}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"bad --evidence_json mapping: {item}")
        name, value = item.split("=", 1)
        paths[name] = Path(value)
    return paths


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (SOURCE_JSON, SOURCE_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[SOURCE_JSON].is_file():
        loaded = _load_json(files[SOURCE_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
    heads = (
        (root / HEADS).read_text(encoding="utf-8", errors="replace")
        if (root / HEADS).is_file()
        else ""
    )
    exit_code = (
        (root / EXIT_CODE).read_text(encoding="utf-8").strip()
        if (root / EXIT_CODE).is_file()
        else None
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "exit_code": exit_code,
        "json_payload": payload,
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("support_redesign_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "support_redesign_plan_ready": bool(
            decision.get("candidate_generation_support_redesign_plan_ready")
        ),
        "preflight_authorized": bool(
            decision.get("route_topology_comfort_support_preflight_authorized")
        ),
        "selected_next_work": decision.get("selected_next_work"),
        "source_selected_next_work": plan.get("selected_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _evidence_summary(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    summary = {}
    for name, path in paths.items():
        payload = {}
        if path.is_file():
            loaded = _load_json(path)
            payload = loaded if isinstance(loaded, dict) else {}
        decision = _dict(payload.get("final_decision"))
        summary[name] = {
            "path": str(path),
            "present": path.is_file(),
            "status": decision.get("status"),
            "final_decision": decision,
            "support_gate": _dict(payload.get("support_gate")),
            "snapshot_aggregate": _dict(payload.get("snapshot_aggregate")),
            "records": _dict(payload.get("records")),
            "source_screen": _dict(payload.get("source_screen")),
            "latency_ms": _dict(payload.get("latency_ms")),
        }
    return summary


def _preflight_plan(
    source: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "fresh_plan_only_gate",
        "conclusions": [
            "route/topology tensor readiness is already present on the fixed nonformal snapshots",
            "constant red-stop and prefix comfort-transfer families remain rejected because relative comfort support is zero",
            "constant and prefix absolute lateral guard audits remain below the predeclared support threshold",
            "lane-projected and prefix lane-projected families produce enough absolute lateral guard support, but still fail relative comfort and are not replay-ready",
            "latest-safe narrowing regressed hard support and is rejected as a minor variant",
            "the next work must address jerk and progress explicitly before any candidate generation execution or replay",
        ],
        "required_next_design_checks": [
            "predeclare a jerk/progress-aware lane-projected design hypothesis before implementation",
            "preserve candidate0 exactly and keep any generated candidates default-off",
            "use only current-tick route/lane/red-light/candidate tensors and fixed constants",
            "predeclare acceleration, jerk, progress, smoothness, lateral, and rollout comfort gates",
            "predeclare endpoint/mode diversity and red-light/lane hard-feasibility diagnostics",
            "predeclare fallback behavior when no candidate passes every gate",
            "predeclare latency p95 and candidate-build p95 rejection thresholds",
            "record all source artifact paths, HEADS, SHA256SUMS, command logs, and exit code",
            "keep formal seeds 11/12/13 frozen and use only nonformal fixed artifacts unless a later gate authorizes otherwise",
        ],
        "accept_criteria": [
            "source support-redesign artifact is ready and authorizes only this preflight",
            "route/topology readiness is present for the fixed nonformal snapshots",
            "lane-projected absolute lateral guard support is present above the predeclared support threshold",
            "prior constant, prefix, and latest-safe variants are classified as rejected or insufficient",
            "the selected next work is plan-only and cannot execute candidate generation",
        ],
        "reject_criteria": [
            "source artifact SHA, HEADS, or exit code cannot be verified",
            "CAMP HEAD diverges from origin/main or DP HEAD is not fixed",
            "route/topology readiness is absent or source tensors are not current-tick",
            "lane-projected absolute lateral guard support is missing or below threshold",
            "the next design repeats stop-margin, prefix-length, bridge-length, latest-safe, or selector tuning",
            "candidate generation execution, replay, formal seeds, CAMP retraining, atom promotion, or DP changes are required",
        ],
        "blocked_boundaries": [
            "this gate is preflight-only and authorizes only a plan-only next gate",
            "no candidate generation execution is authorized",
            "no replay or closed-loop smoke is authorized",
            "no CAMP retraining is authorized",
            "no atom promotion or online selector change is authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or DP Top-1 superiority claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "selected_next_work": source["selected_next_work"],
        },
        "evidence_contract": {name: item["status"] for name, item in evidence.items()},
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "support_redesign_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("support_redesign_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("support_redesign_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal("support_redesign_heads_present", bool(str(artifact.get("heads_text") or "").strip()), True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal("source_authorizes_preflight", source["authorized_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_support_redesign_plan_ready", source["support_redesign_plan_ready"], True),
        _check_equal("source_preflight_authorized", source["preflight_authorized"], True),
        _check_equal("source_selected_next_work", source["selected_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_plan_selected_next_work", source["source_selected_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _evidence_checks(evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    expected_status = {
        "route_topology_readiness": "route_topology_candidate_design_ready",
        "constant_red_stop_screen": "route_topology_candidate_support_insufficient",
        "prefix_comfort_screen": "route_topology_candidate_support_insufficient",
        "constant_absolute_lateral_guard": "route_topology_absolute_lateral_guard_support_insufficient",
        "prefix_absolute_lateral_guard": "route_topology_absolute_lateral_guard_support_insufficient",
        "lane_projected_screen": "route_topology_candidate_support_insufficient",
        "lane_projected_absolute_lateral_guard": "route_topology_absolute_lateral_guard_support_present",
        "prefix_lane_projected_screen": "route_topology_candidate_support_insufficient",
        "prefix_lane_projected_absolute_lateral_guard": "route_topology_absolute_lateral_guard_support_present",
        "latest_safe_screen": "route_topology_candidate_support_insufficient",
        "latest_safe_failure_patterns": "route_topology_failure_patterns_hard_support_insufficient",
    }
    checks = []
    for name, status in expected_status.items():
        item = evidence.get(name, {"present": False, "status": None})
        checks.append(_check_equal(f"evidence_{name}_present", item["present"], True))
        checks.append(_check_equal(f"evidence_{name}_status", item["status"], status))

    readiness = evidence.get("route_topology_readiness", {})
    checks.extend(
        [
            _check_equal(
                "readiness_snapshot_rate_full",
                _number(_section(readiness, "snapshot_aggregate").get("ready_snapshot_rate")),
                1.0,
            ),
            _check_equal(
                "readiness_authorizes_offline_only",
                bool(_decision(readiness).get("offline_candidate_augmentation_screen_authorized")),
                True,
            ),
        ]
    )
    for name in ("constant_red_stop_screen", "lane_projected_screen", "prefix_lane_projected_screen"):
        item = evidence.get(name, {})
        gate = _section(item, "support_gate")
        checks.append(
            _check_compare(
                f"{name}_hard_support_at_or_above_min",
                _number(gate.get("hard_feasible_snapshot_support_rate")),
                ">=",
                _number(gate.get("min_snapshot_support_rate")),
            )
        )
        checks.append(
            _check_equal(
                f"{name}_relative_comfort_zero",
                _number(gate.get("comfort_admissible_snapshot_support_rate")),
                0.0,
            )
        )
    prefix_gate = _section(evidence.get("prefix_comfort_screen", {}), "support_gate")
    checks.append(
        _check_compare(
            "prefix_comfort_hard_support_below_min",
            _number(prefix_gate.get("hard_feasible_snapshot_support_rate")),
            "<",
            _number(prefix_gate.get("min_snapshot_support_rate")),
        )
    )
    checks.append(
        _check_equal(
            "prefix_comfort_relative_comfort_zero",
            _number(prefix_gate.get("comfort_admissible_snapshot_support_rate")),
            0.0,
        )
    )
    for name in ("constant_absolute_lateral_guard", "prefix_absolute_lateral_guard", "latest_safe_screen"):
        item = evidence.get(name, {})
        gate = _section(item, "support_gate")
        checks.append(
            _check_compare(
                f"{name}_support_below_min",
                _support_rate(item),
                "<",
                _number(gate.get("min_snapshot_support_rate")),
            )
        )
    for name in ("lane_projected_absolute_lateral_guard", "prefix_lane_projected_absolute_lateral_guard"):
        item = evidence.get(name, {})
        gate = _section(item, "support_gate")
        checks.append(
            _check_compare(
                f"{name}_support_at_or_above_min",
                _support_rate(item),
                ">=",
                _number(gate.get("min_snapshot_support_rate")),
            )
        )
    return checks


def _preflight_checks(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        preflight["conclusions"]
        + preflight["required_next_design_checks"]
        + preflight["accept_criteria"]
        + preflight["reject_criteria"]
    ).lower()
    return [
        _check_equal("preflight_selected_next_work", preflight["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("preflight_selection_type", preflight["selection_type"], "fresh_plan_only_gate"),
        _check_equal("preflight_mentions_lane_projected", "lane-projected" in text, True),
        _check_equal("preflight_requires_jerk_progress", "jerk" in text and "progress" in text, True),
        _check_equal("preflight_requires_candidate0", "candidate0" in text, True),
        _check_equal("preflight_requires_no_leak_current_tick", "current-tick" in text, True),
        _check_equal("preflight_requires_fallback", "fallback" in text, True),
        _check_equal("preflight_requires_latency", "latency" in text and "p95" in text, True),
        _check_equal("preflight_requires_artifact_sha", "sha256sums" in text and "heads" in text, True),
        _check_equal("preflight_rejects_minor_tuning", "stop-margin" in text and "prefix-length" in text, True),
    ]


def _boundary_checks(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        preflight["conclusions"]
        + preflight["required_next_design_checks"]
        + preflight["accept_criteria"]
        + preflight["reject_criteria"]
        + preflight["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("boundary_mentions_preflight_only", "preflight-only" in text, True),
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal("boundary_blocks_candidate_generation_execution", "no candidate generation execution" in text, True),
        _check_equal("boundary_blocks_replay", "no replay" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp weights" in text and "fixed" in text, True),
        _check_equal("boundary_blocks_benders_claim", "classical benders" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "route_topology_comfort_support_preflight_ready": passed,
        "lane_projected_jerk_progress_support_design_plan_authorized": passed,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "candidate_generation_execution_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _decision(item: dict[str, Any]) -> dict[str, Any]:
    return _dict(item.get("final_decision"))


def _section(item: dict[str, Any], key: str) -> dict[str, Any]:
    return _dict(item.get(key))


def _support_rate(item: dict[str, Any]) -> float | None:
    gate = _section(item, "support_gate")
    if "absolute_lateral_guard_snapshot_support_rate" in gate:
        return _number(gate.get("absolute_lateral_guard_snapshot_support_rate"))
    if "hard_feasible_snapshot_support_rate" in gate:
        return _number(gate.get("hard_feasible_snapshot_support_rate"))
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _sha256sum_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    root = path.parent
    details = []
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            ok = False
            details.append({"line": line, "ok": False, "reason": "malformed"})
            continue
        expected, name = parts
        item = root / name.strip()
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append({"path": str(item), "expected": expected, "actual": actual, "ok": matched})
    return ok, details


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _check_compare(name: str, observed: float | None, op: str, expected: float | None) -> dict[str, Any]:
    passed = False
    if observed is not None and expected is not None:
        if op == ">=":
            passed = observed >= expected
        elif op == "<":
            passed = observed < expected
        else:
            raise ValueError(f"unsupported op: {op}")
    return {"name": name, "observed": observed, "expected": f"{op} {expected}", "passed": passed}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
