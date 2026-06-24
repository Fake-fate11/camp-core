#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
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
    "fixed_snapshot_screen_rerun_remediation_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "design_plan_only"
)
SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"
PLANNED_POLICY = "comfort_first_lane_projected_red_stop"

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SCREEN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "fixed_snapshot_screen_rerun_bff8f8b"
)

SCREEN_JSON = "default_off_remediation_fixed_snapshot_screen.json"
SCREEN_MD = "default_off_remediation_fixed_snapshot_screen.md"
CANDIDATE_LOG = "CANDIDATE_SCREEN.log"
CANDIDATE_ERR = "CANDIDATE_SCREEN.err"
CAMP_HEAD = "CAMP_HEAD.txt"
CAMP_ORIGIN_MAIN = "CAMP_ORIGIN_MAIN.txt"
DP_HEAD = "DP_HEAD.txt"
SHA256SUMS = "SHA256SUMS"

BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only failure attribution over the guarded default-off "
            "remediation fixed-snapshot screen rerun artifact."
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
    screen_payload = artifact["screen_payload"]
    source = _source_summary(screen_payload)
    attribution = _failure_attribution(screen_payload)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head, artifact),
        *_source_checks(source),
        *_attribution_checks(attribution),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_guarded_"
                "fixed_snapshot_screen_rerun_failure_attribution_v1"
            ),
            "label": label,
            "role": "read-only attribution over completed guarded screen rerun",
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
                "It does not create candidates, rerun the screen, run replay, "
                "use formal seeds, define or promote runtime atoms, choose "
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
        "screen_artifact": _strip_payload(artifact),
        "source_summary": source,
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Guarded Remediation Fixed-Snapshot Screen Rerun Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Screen status: `{source['status']}`",
        f"- Primary blocker family: `{attribution['primary_blocker_family']}`",
        f"- Comfort rows: `{source['comfort_admissible_rows']}`",
        f"- Hard support rate: `{source['hard_support_rate']}`",
        f"- Comfort support rate: `{source['comfort_support_rate']}`",
        "",
        "## Coverage",
        "",
        f"- Snapshots: `{source['snapshots']}`",
        f"- Snapshots with generated candidates: `{source['snapshots_with_generated_candidates']}`",
        f"- Generated candidate rows: `{source['generated_candidate_rows']}`",
        "",
        "## Comfort Blockers",
        "",
    ]
    for item in attribution["comfort_blocker_ranking"]:
        lines.append(
            f"- `{item['name']}`: count=`{item['count']}`, "
            f"hard_progress_feasible_count=`{item['hard_progress_feasible_count']}`"
        )
    lines.extend(["", "## Hard Blockers", ""])
    for item in attribution["hard_blocker_ranking"]:
        lines.append(f"- `{item['name']}`: count=`{item['count']}`")
    lines.extend(["", "## Construction Diagnostics", ""])
    for item in attribution["construction_status_ranking"]:
        lines.append(f"- `{item['name']}`: count=`{item['count']}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only analysis only",
            "- no new screen rerun, replay, Full36, formal seeds, or CAMP retraining",
            "- no atom promotion, online selector promotion, safety claim, or DP modification",
            "- no CAMP-over-DP-Top-1 claim",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
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
        "files": files,
        "sha256sums_ok": _sha256sums_ok(root / SHA256SUMS),
        "screen_json_sha256": _sha256(root / SCREEN_JSON),
        "screen_md_sha256": _sha256(root / SCREEN_MD),
        "screen_payload": _read_json(root / SCREEN_JSON),
        "screen_markdown": _read_text(root / SCREEN_MD),
        "candidate_log": _read_text(root / CANDIDATE_LOG),
        "candidate_err": _read_text(root / CANDIDATE_ERR),
        "camp_head_file": _read_text(root / CAMP_HEAD).strip(),
        "camp_origin_main_file": _read_text(root / CAMP_ORIGIN_MAIN).strip(),
        "dp_head_file": _read_text(root / DP_HEAD).strip(),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    records = _dict(payload.get("records"))
    support_gate = _dict(payload.get("support_gate"))
    config = _dict(payload.get("config"))
    failure_counts = _int_dict(payload.get("failure_class_counts"))
    hard_counts = _int_dict(payload.get("hard_reason_counts"))
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "snapshots": int(records.get("snapshots") or 0),
        "snapshots_with_generated_candidates": int(
            records.get("snapshots_with_generated_candidates") or 0
        ),
        "generated_candidate_rows": int(records.get("generated_candidate_rows") or 0),
        "lower_union_red_rows": int(records.get("lower_union_red_rows") or 0),
        "hard_feasible_rows": int(
            records.get("lower_union_red_hard_feasible_rows") or 0
        ),
        "progress_feasible_rows": int(
            records.get("lower_union_red_progress_feasible_rows") or 0
        ),
        "comfort_admissible_rows": int(
            records.get("lower_union_red_comfort_admissible_rows") or 0
        ),
        "min_snapshot_support_rate": float(
            support_gate.get("min_snapshot_support_rate") or 0.0
        ),
        "hard_support_rate": float(
            support_gate.get("hard_feasible_snapshot_support_rate") or 0.0
        ),
        "comfort_support_rate": float(
            support_gate.get("comfort_admissible_snapshot_support_rate") or 0.0
        ),
        "hard_support_pass": bool(
            support_gate.get("hard_feasible_snapshot_support_pass")
        ),
        "comfort_support_pass": bool(
            support_gate.get("comfort_admissible_snapshot_support_pass")
        ),
        "generator_policy": config.get("generator_policy"),
        "max_remediation_candidates": config.get("max_remediation_candidates"),
        "failure_class_counts": failure_counts,
        "hard_reason_counts": hard_counts,
        "source_authorization_conflicts": _list(
            decision.get("source_authorization_conflicts")
        ),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "training": bool(analysis.get("training")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "dp_modification": bool(
            analysis.get("diffusion_planner_modification")
            or decision.get("dp_modification_authorized")
        ),
    }


def _failure_attribution(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _list(payload.get("rows"))
    source = _source_summary(payload)
    comfort_counts = _comfort_counts(source["failure_class_counts"])
    hard_counts = source["hard_reason_counts"]
    hard_progress_counts: Counter[str] = Counter()
    construction_status: Counter[str] = Counter()
    construction_failure: Counter[str] = Counter()
    partition_counts: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        diag = _dict(row.get("candidate_construction_diagnostics"))
        construction_status[str(diag.get("construction_status") or "missing")] += 1
        failure_reason = diag.get("failure_reason")
        if failure_reason:
            construction_failure[str(failure_reason)] += 1
        partition = diag.get("red_stop_distance_partition")
        if partition:
            partition_counts[str(partition)] += 1
        for candidate in _list(row.get("candidate_rows")):
            if not isinstance(candidate, dict):
                continue
            if candidate.get("hard_feasible") and candidate.get("progress_feasible"):
                for failure_class in _list(candidate.get("failure_classes")):
                    if isinstance(failure_class, str) and "comfort_blocked" in failure_class:
                        hard_progress_counts[failure_class] += 1

    primary = "undetermined"
    if source["comfort_admissible_rows"] == 0 and source["hard_support_pass"] is False:
        primary = "hard_support_below_threshold_and_comfort_support_zero"
    elif source["comfort_admissible_rows"] == 0:
        primary = "comfort_support_zero"
    elif source["hard_support_pass"] is False:
        primary = "hard_support_below_threshold"

    return {
        "primary_blocker_family": primary,
        "positive_support_evidence": False,
        "training_ready": False,
        "candidate_coverage_rate": _safe_rate(
            source["snapshots_with_generated_candidates"],
            source["snapshots"],
        ),
        "hard_support_gap": max(
            0.0, source["min_snapshot_support_rate"] - source["hard_support_rate"]
        ),
        "comfort_support_gap": max(
            0.0, source["min_snapshot_support_rate"] - source["comfort_support_rate"]
        ),
        "comfort_blocker_ranking": [
            {
                "name": name,
                "count": count,
                "hard_progress_feasible_count": hard_progress_counts.get(name, 0),
            }
            for name, count in _rank_counts(comfort_counts)
        ],
        "hard_blocker_ranking": [
            {"name": name, "count": count} for name, count in _rank_counts(hard_counts)
        ],
        "construction_status_ranking": [
            {"name": name, "count": count}
            for name, count in _rank_counts(dict(construction_status))
        ],
        "construction_failure_ranking": [
            {"name": name, "count": count}
            for name, count in _rank_counts(dict(construction_failure))
        ],
        "red_stop_distance_partition_ranking": [
            {"name": name, "count": count}
            for name, count in _rank_counts(dict(partition_counts))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    files = _dict(artifact.get("files"))
    return [
        _check("screen_root_exists", bool(artifact["exists"])),
        *[_check(f"{name}_exists", bool(files.get(name))) for name in files],
        _check("sha256sums_match", bool(artifact["sha256sums_ok"])),
        _check("screen_json_parseable", bool(artifact["screen_payload"])),
        _check("screen_markdown_records_verdict", "## Verdict" in artifact["screen_markdown"]),
        _check("candidate_screen_err_empty", artifact["candidate_err"].strip() == ""),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("camp_head_file_matches_arg", artifact["camp_head_file"] == camp_head),
        _check(
            "camp_origin_main_file_matches_arg",
            artifact["camp_origin_main_file"] == camp_origin_main,
        ),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("dp_head_file_fixed", artifact["dp_head_file"] == EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_status_is_support_insufficient", source["status"] == SCREEN_REJECT_STATUS),
        _check("screen_policy_is_planned_remediation", source["generator_policy"] == PLANNED_POLICY),
        _check("screen_snapshots_present", source["snapshots"] == 57),
        _check("screen_generated_candidates_present", source["generated_candidate_rows"] > 0),
        _check("screen_hard_support_below_required", source["hard_support_pass"] is False),
        _check("screen_comfort_support_zero", source["comfort_admissible_rows"] == 0),
        _check("screen_comfort_support_below_required", source["comfort_support_pass"] is False),
        _check("screen_no_source_authorization_conflicts", not source["source_authorization_conflicts"]),
        _check("screen_no_blocked_authorizations", not source["blocked_authorizations"]),
        _check("screen_no_future_outcome_leakage", source["future_outcome_leakage"] is False),
        _check("screen_no_closed_loop_replay", source["closed_loop_replay"] is False),
        _check("screen_no_training", source["training"] is False),
        _check("screen_no_dp_modification", source["dp_modification"] is False),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    comfort_names = {item["name"] for item in attribution["comfort_blocker_ranking"]}
    hard_names = {item["name"] for item in attribution["hard_blocker_ranking"]}
    return [
        _check(
            "attribution_primary_blocker_identified",
            attribution["primary_blocker_family"]
            == "hard_support_below_threshold_and_comfort_support_zero",
        ),
        _check("attribution_positive_support_absent", attribution["positive_support_evidence"] is False),
        _check("attribution_training_not_ready", attribution["training_ready"] is False),
        _check("attribution_hard_support_gap_positive", attribution["hard_support_gap"] > 0),
        _check("attribution_comfort_support_gap_positive", attribution["comfort_support_gap"] > 0),
        _check(
            "attribution_comfort_progress_lateral_present",
            "route_topology_comfort_blocked_progress_loss" in comfort_names
            and "route_topology_comfort_blocked_command_lateral" in comfort_names,
        ),
        _check(
            "attribution_hard_red_lane_present",
            "dp_red_light" in hard_names and "dp_lane_crossing" in hard_names,
        ),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_blocks_replay", True),
        _check("boundary_blocks_formal_seeds", True),
        _check("boundary_blocks_training", True),
        _check("boundary_blocks_dp_modification", source["dp_modification"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "positive_support_evidence": False,
        "replay_evidence_ready": False,
        "training_ready": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _sha256sums_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            return False
        expected, name = parts[0], parts[-1]
        target = Path(name)
        if not target.is_absolute():
            target = path.parent / target
        if not target.is_file() or _sha256(target) != expected:
            return False
    return True


def _comfort_counts(counts: dict[str, int]) -> dict[str, int]:
    return {key: value for key, value in counts.items() if "comfort_blocked" in key}


def _rank_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _safe_rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"screen_payload", "screen_markdown", "candidate_log", "candidate_err"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, item in value.items():
        try:
            out[str(key)] = int(item)
        except (TypeError, ValueError):
            continue
    return out


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
