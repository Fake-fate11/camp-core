#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_failure_attribution_read_only_analysis_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_failure_attribution_read_only_analysis_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_design_plan_only"
)
SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SCREEN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_bff8f8b"
)

SCREEN_JSON = "default_off_fixed_snapshot_screen.json"
SCREEN_MD = "default_off_fixed_snapshot_screen.md"
CANDIDATE_LOG = "CANDIDATE_SCREEN.log"
CANDIDATE_ERR = "CANDIDATE_SCREEN.err"
CAMP_HEAD = "CAMP_HEAD.txt"
CAMP_ORIGIN_MAIN = "CAMP_ORIGIN_MAIN.txt"
DP_HEAD = "DP_HEAD.txt"
SHA256SUMS = "SHA256SUMS"

BLOCKED_ACTIONS = (
    "fixed_snapshot_screen_rerun_authorized",
    "offline_selector_screen_authorized",
    "online_selector_authorized",
    "closed_loop_smoke_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only failure attribution for the default-off product-code "
            "fixed-snapshot screen rerun."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
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
        screen_root=args.screen_root,
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
    screen_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(screen_root)
    screen_payload = artifact.get("screen_payload") or {}
    source = _source_summary(screen_payload)
    attribution = _attribution_summary(screen_payload)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head, artifact),
        *_source_checks(source),
        *_attribution_checks(attribution),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    decision = _final_decision(passed, checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_failure_attribution_v1"
            ),
            "label": label,
            "role": "read-only failure attribution over completed screen artifacts",
            "read_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This gate reads only completed fixed-snapshot screen artifacts. "
                "It does not rerun the screen, run replay, use formal seeds, "
                "define or promote runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "screen_artifact": _strip_payload(artifact),
        "source_summary": source,
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Default-Off Fixed-Snapshot Screen Rerun Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Screen Summary",
        "",
        f"- Screen status: `{source['status']}`",
        f"- Snapshots: `{source['snapshots']}`",
        f"- Generated candidate rows: `{source['generated_candidate_rows']}`",
        f"- Comfort-admissible lower-red rows: `{source['lower_union_red_comfort_admissible_rows']}`",
        "",
        "## Failure Attribution",
        "",
    ]
    for mode in attribution["primary_failure_modes"]:
        lines.append(f"- `{mode}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only analysis only",
            "- no new screen rerun, replay, Full36, formal seeds, or CAMP retraining",
            "- no atom promotion, online selector promotion, safety claim, or DP modification",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        SCREEN_JSON,
        SCREEN_MD,
        CANDIDATE_LOG,
        CANDIDATE_ERR,
        CAMP_HEAD,
        CAMP_ORIGIN_MAIN,
        DP_HEAD,
        SHA256SUMS,
    )
    files = {name: (root / name).is_file() for name in required}
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": _sha256sums_ok(root),
        "screen_payload": _read_json(root / SCREEN_JSON),
        "camp_head_file": _read_text(root / CAMP_HEAD).strip(),
        "camp_origin_main_file": _read_text(root / CAMP_ORIGIN_MAIN).strip(),
        "dp_head_file": _read_text(root / DP_HEAD).strip(),
        "candidate_err_bytes": _file_size(root / CANDIDATE_ERR),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    records = _dict(payload.get("records"))
    support = _dict(payload.get("support_gate"))
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    latency = _dict(payload.get("latency_ms"))
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "snapshots": _int(records.get("snapshots")),
        "rows": len(_list(payload.get("rows"))),
        "snapshots_with_generated_candidates": _int(
            records.get("snapshots_with_generated_candidates")
        ),
        "generated_candidate_rows": _int(records.get("generated_candidate_rows")),
        "lower_union_red_rows": _int(records.get("lower_union_red_rows")),
        "lower_union_red_hard_feasible_rows": _int(
            records.get("lower_union_red_hard_feasible_rows")
        ),
        "lower_union_red_progress_feasible_rows": _int(
            records.get("lower_union_red_progress_feasible_rows")
        ),
        "lower_union_red_comfort_admissible_rows": _int(
            records.get("lower_union_red_comfort_admissible_rows")
        ),
        "hard_feasible_snapshot_support_rate": _float(
            support.get("hard_feasible_snapshot_support_rate")
        ),
        "hard_feasible_snapshot_support_pass": bool(
            support.get("hard_feasible_snapshot_support_pass")
        ),
        "comfort_admissible_snapshot_support_rate": _float(
            support.get("comfort_admissible_snapshot_support_rate")
        ),
        "comfort_admissible_snapshot_support_pass": bool(
            support.get("comfort_admissible_snapshot_support_pass")
        ),
        "candidate_build_p95_ms": _percentile(latency, "candidate_build", "p95"),
        "total_p95_ms": _percentile(latency, "total", "p95"),
        "selection_effect": bool(analysis.get("selection_effect")),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "training": bool(analysis.get("training")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _list(payload.get("rows"))
    zero_rows = [row for row in rows if _int(_dict(row).get("generated_count")) == 0]
    zero_reasons: dict[str, int] = {}
    for row in zero_rows:
        diagnostics = _dict(_dict(row).get("candidate_construction_diagnostics"))
        reason = str(
            diagnostics.get("failure_reason")
            or diagnostics.get("construction_status")
            or "missing_diagnostics"
        )
        zero_reasons[reason] = zero_reasons.get(reason, 0) + 1
    failure_counts = _dict(payload.get("failure_class_counts"))
    comfort_blockers = {
        key: _int(value)
        for key, value in failure_counts.items()
        if str(key).startswith("route_topology_comfort_blocked")
    }
    primary = []
    if zero_reasons.get("red_stop_distance_window", 0) > 0:
        primary.append("red_stop_distance_window_zero_candidate_partition")
    if _int(_dict(payload.get("records")).get("lower_union_red_comfort_admissible_rows")) == 0:
        primary.append("comfort_admissible_support_absent")
    if comfort_blockers:
        primary.append("comfort_blockers_dominate_generated_rows")
    source = _source_summary(payload)
    if source["candidate_build_p95_ms"] > 10.0 or source["total_p95_ms"] > 100.0:
        primary.append("latency_budget_exceeded")
    return {
        "zero_candidate_rows": len(zero_rows),
        "zero_candidate_reasons": zero_reasons,
        "failure_class_counts_top": dict(
            sorted(
                ((str(k), _int(v)) for k, v in failure_counts.items()),
                key=lambda item: item[1],
                reverse=True,
            )[:12]
        ),
        "comfort_blocker_counts": comfort_blockers,
        "primary_failure_modes": primary,
        "recommended_design_focus": [
            "red-stop distance-window coverage",
            "comfort-preserving candidate construction",
            "latency-bounded candidate expansion",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_artifact_root_exists", artifact["exists"]),
        _check("screen_artifact_required_files_present", artifact["required_files_present"]),
        _check("screen_artifact_sha256sums_ok", artifact["sha256sums_ok"]),
        _check("candidate_err_empty", artifact["candidate_err_bytes"] == 0),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_equals_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("artifact_camp_head_matches", artifact["camp_head_file"] == camp_head),
        _check(
            "artifact_camp_origin_main_matches",
            artifact["camp_origin_main_file"] == camp_origin_main,
        ),
        _check("artifact_dp_head_fixed", artifact["dp_head_file"] == EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_status_is_support_insufficient", source["status"] == SCREEN_REJECT_STATUS),
        _check("screen_has_expected_snapshot_count", source["snapshots"] == 57),
        _check("screen_has_rows", source["rows"] == 57),
        _check("screen_generated_rows_positive", source["generated_candidate_rows"] > 0),
        _check("screen_lower_red_rows_positive", source["lower_union_red_rows"] > 0),
        _check("screen_hard_support_passed", source["hard_feasible_snapshot_support_pass"] is True),
        _check("screen_comfort_support_failed", source["comfort_admissible_snapshot_support_pass"] is False),
        _check("screen_no_comfort_admissible_rows", source["lower_union_red_comfort_admissible_rows"] == 0),
        _check("screen_no_selection_effect", source["selection_effect"] is False),
        _check("screen_no_future_outcome_leakage", source["future_outcome_leakage"] is False),
        _check("screen_no_training", source["training"] is False),
        _check("screen_no_replay", source["closed_loop_replay"] is False),
        _check("screen_no_online_selector_change", source["online_selector_change"] is False),
        _check("screen_no_blocked_actions", not source["blocked_action_conflicts"]),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("attribution_zero_candidate_rows_present", attribution["zero_candidate_rows"] > 0),
        _check(
            "attribution_red_window_partition_present",
            attribution["zero_candidate_reasons"].get("red_stop_distance_window", 0) > 0,
        ),
        _check("attribution_comfort_blockers_present", bool(attribution["comfort_blocker_counts"])),
        _check("attribution_primary_modes_present", bool(attribution["primary_failure_modes"])),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_screen_not_authorized_for_promotion", source["status"] == SCREEN_REJECT_STATUS),
        _check("boundary_training_blocked", "camp_retraining_authorized" not in source["blocked_action_conflicts"]),
        _check("boundary_dp_modification_blocked", "dp_modification_authorized" not in source["blocked_action_conflicts"]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "read_only_failure_attribution_complete": passed,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "screen_payload"}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256sums_ok(root: Path) -> bool:
    sha_path = root / SHA256SUMS
    if not sha_path.is_file():
        return False
    for raw_line in sha_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split(None, 1)
        if len(parts) != 2:
            return False
        expected, name = parts
        candidate = Path(name.strip())
        if not candidate.is_absolute():
            candidate = root / candidate
        if not candidate.is_file():
            return False
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != expected:
            return False
    return True


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else -1


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _percentile(latency: dict[str, Any], group: str, key: str) -> float:
    return _float(_dict(latency.get(group)).get(key))


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
