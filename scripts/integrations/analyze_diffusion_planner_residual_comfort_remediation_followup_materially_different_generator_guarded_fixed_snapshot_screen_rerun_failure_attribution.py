#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLANNED_POLICY = "lane_station_jerk_limited_red_stop_material_support"
REMEDIATION_PROFILE = "lane_station_jerk_limited_red_stop_support_v1"
SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)

DEFAULT_SCREEN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_fixed_snapshot_screen_rerun_bff8f8b"
)
SCREEN_JSON = "material_generator_fixed_snapshot_screen.json"
SCREEN_MD = "material_generator_fixed_snapshot_screen.md"
CANDIDATE_LOG = "CANDIDATE_SCREEN.log"
CANDIDATE_ERR = "CANDIDATE_SCREEN.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"
PY39_IMPORT_FAILURE_ERR = "CANDIDATE_SCREEN.python39_import_failure.err"

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
            "Read-only attribution over the material generator guarded "
            "fixed-snapshot screen rerun result."
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
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(screen_root)
    payload = artifact["screen_payload"]
    source = _source_summary(payload)
    attribution = _failure_attribution(source, payload)
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
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_materially_different_generator_guarded_"
                "fixed_snapshot_screen_rerun_failure_attribution_v1"
            ),
            "label": label,
            "role": "read-only attribution over completed material generator screen",
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
                "modify DP weights/code/config, or claim a DP-side classical "
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
        "# Material Generator Screen Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Screen status: `{source['status']}`",
        f"- Primary blocker family: `{attribution['primary_blocker_family']}`",
        f"- Training ready: `{attribution['training_ready']}`",
        "",
        "## Support Shape",
        "",
        f"- Snapshots: `{source['snapshots']}`",
        f"- Snapshots with generated candidates: `{source['snapshots_with_generated_candidates']}`",
        f"- Generated candidate rows: `{source['generated_candidate_rows']}`",
        f"- Lower-red rows: `{source['lower_union_red_rows']}`",
        f"- Hard-feasible rows: `{source['hard_feasible_rows']}`",
        f"- Progress-feasible rows: `{source['progress_feasible_rows']}`",
        f"- Comfort-admissible rows: `{source['comfort_admissible_rows']}`",
        f"- Hard support rate: `{source['hard_support_rate']}`",
        f"- Comfort support rate: `{source['comfort_support_rate']}`",
        "",
        "## Attribution",
        "",
        attribution["interpretation"],
        "",
        "## Hard Blockers",
        "",
    ]
    for item in attribution["hard_blocker_ranking"]:
        lines.append(f"- `{item['name']}`: `{item['count']}`")
    lines.extend(["", "## Comfort Blockers", ""])
    for item in attribution["comfort_blocker_ranking"]:
        lines.append(f"- `{item['name']}`: `{item['count']}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only attribution only",
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
    required = (SCREEN_JSON, SCREEN_MD, CANDIDATE_LOG, CANDIDATE_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: (root / name).is_file() for name in required}
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "files": files,
        "sha256sums_ok": _sha256sums_ok(root / SHA256SUMS),
        "screen_json_sha256": _sha256(root / SCREEN_JSON),
        "screen_md_sha256": _sha256(root / SCREEN_MD),
        "python39_import_failure_sha256": _sha256(root / PY39_IMPORT_FAILURE_ERR),
        "screen_payload": _read_json(root / SCREEN_JSON),
        "screen_markdown": _read_text(root / SCREEN_MD),
        "candidate_log": _read_text(root / CANDIDATE_LOG),
        "candidate_err": _read_text(root / CANDIDATE_ERR),
        "exit_code": _read_text(root / EXIT_CODE).strip(),
        "heads": _parse_heads(_read_text(root / HEADS)),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    records = _dict(payload.get("records"))
    support = _dict(payload.get("support_gate"))
    config = _dict(payload.get("config"))
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "snapshots": _int(records.get("snapshots")),
        "snapshots_with_generated_candidates": _int(
            records.get("snapshots_with_generated_candidates")
        ),
        "generated_candidate_rows": _int(records.get("generated_candidate_rows")),
        "lower_union_red_rows": _int(records.get("lower_union_red_rows")),
        "hard_feasible_rows": _int(records.get("lower_union_red_hard_feasible_rows")),
        "progress_feasible_rows": _int(
            records.get("lower_union_red_progress_feasible_rows")
        ),
        "comfort_admissible_rows": _int(
            records.get("lower_union_red_comfort_admissible_rows")
        ),
        "support_snapshots": _int(support.get("snapshots")),
        "hard_support_rate": _float(support.get("hard_feasible_snapshot_support_rate")),
        "comfort_support_rate": _float(
            support.get("comfort_admissible_snapshot_support_rate")
        ),
        "min_snapshot_support_rate": _float(support.get("min_snapshot_support_rate")),
        "hard_support_pass": bool(support.get("hard_feasible_snapshot_support_pass")),
        "comfort_support_pass": bool(
            support.get("comfort_admissible_snapshot_support_pass")
        ),
        "generator_policy": config.get("generator_policy"),
        "default_off_remediation_profile": config.get(
            "default_off_remediation_profile"
        ),
        "failure_class_counts": _int_dict(payload.get("failure_class_counts")),
        "hard_reason_counts": _int_dict(payload.get("hard_reason_counts")),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "source_authorization_conflicts": _list(
            decision.get("source_authorization_conflicts")
        ),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "training": bool(analysis.get("training")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "dp_modification": bool(
            analysis.get("diffusion_planner_modification")
            or decision.get("dp_modification_authorized")
        ),
    }


def _failure_attribution(
    source: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    candidate_rows = [
        candidate
        for row in _list(payload.get("rows"))
        for candidate in _list(_dict(row).get("candidate_rows"))
    ]
    descriptor_rows = [
        candidate
        for candidate in candidate_rows
        if _dict(_dict(candidate).get("candidate_meta")).get(
            "remediation_descriptor_payload"
        )
    ]
    comfort_counts = {
        key: value
        for key, value in source["failure_class_counts"].items()
        if "comfort_blocked" in key
    }
    hard_counts = source["hard_reason_counts"]
    if (
        source["generated_candidate_rows"] > 0
        and source["hard_support_rate"] < source["min_snapshot_support_rate"]
        and source["comfort_admissible_rows"] == 0
    ):
        primary = "hard_support_below_threshold_plus_zero_comfort_support"
        interpretation = (
            "The material generator produced lower-red candidates and material "
            "descriptors, but the fixed-snapshot screen still fails before "
            "training: hard support is below the required snapshot-support "
            "threshold and comfort-admissible support is zero. The largest "
            "hard blockers remain lane/red/kinematic/road-border failures; the "
            "few hard/progress survivors are then blocked by progress, jerk, "
            "lateral, rollout jerk/lateral, and smoothness comfort filters."
        )
    elif source["comfort_admissible_rows"] == 0:
        primary = "zero_comfort_support"
        interpretation = "Comfort support is zero, so the artifact is not training-ready."
    else:
        primary = "unexpected_positive_support_shape"
        interpretation = "The artifact does not match the expected negative-support shape."
    return {
        "primary_blocker_family": primary,
        "interpretation": interpretation,
        "candidate_row_count": len(candidate_rows),
        "descriptor_row_count": len(descriptor_rows),
        "descriptor_coverage_rate": _safe_rate(len(descriptor_rows), len(candidate_rows)),
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
        "positive_support_evidence": False,
        "training_ready": False,
        "replay_evidence_ready": False,
        "hard_blocker_ranking": [
            {"name": name, "count": count} for name, count in _rank_counts(hard_counts)
        ],
        "comfort_blocker_ranking": [
            {"name": name, "count": count}
            for name, count in _rank_counts(comfort_counts)
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
        _check("screen_exit_code_zero", artifact["exit_code"] == "0"),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    heads = _dict(artifact.get("heads"))
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("camp_head_file_matches_arg", heads.get("CAMP_HEAD") == camp_head),
        _check("camp_origin_main_file_matches_arg", heads.get("CAMP_ORIGIN_MAIN") == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("dp_head_file_fixed", heads.get("DP_HEAD") == EXPECTED_DP_HEAD),
        _check("snapshot_count_file", heads.get("SNAPSHOT_COUNT") == "57"),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_status_is_support_insufficient", source["status"] == SCREEN_REJECT_STATUS),
        _check("screen_policy_is_material_support", source["generator_policy"] == PLANNED_POLICY),
        _check("screen_profile_is_material_support", source["default_off_remediation_profile"] == REMEDIATION_PROFILE),
        _check("screen_snapshots_present", source["snapshots"] == 57),
        _check("screen_generated_candidates_present", source["generated_candidate_rows"] > 0),
        _check("screen_lower_red_candidates_present", source["lower_union_red_rows"] > 0),
        _check("screen_hard_support_below_threshold", source["hard_support_pass"] is False),
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
    return [
        _check(
            "attribution_primary_blocker_expected",
            attribution["primary_blocker_family"]
            == "hard_support_below_threshold_plus_zero_comfort_support",
        ),
        _check("attribution_descriptor_rows_present", attribution["descriptor_row_count"] > 0),
        _check("attribution_descriptor_coverage_complete", attribution["descriptor_coverage_rate"] == 1.0),
        _check("attribution_hard_gap_positive", attribution["hard_support_gap"] > 0.0),
        _check("attribution_comfort_gap_positive", attribution["comfort_support_gap"] > 0.0),
        _check("attribution_has_hard_blockers", bool(attribution["hard_blocker_ranking"])),
        _check("attribution_has_comfort_blockers", bool(attribution["comfort_blocker_ranking"])),
        _check("attribution_not_training_ready", attribution["training_ready"] is False),
        _check("attribution_no_positive_support", attribution["positive_support_evidence"] is False),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_no_training_ready_claim", source["comfort_admissible_rows"] == 0),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "fixed_snapshot_screen_rerun_failure_attribution_complete": passed,
        "remediation_design_plan_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _sha256sums_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            return False
        expected, name = parts[0], parts[-1]
        target = path.parent / name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            return False
    return True


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _parse_heads(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"screen_payload", "screen_markdown", "candidate_log", "candidate_err"}
    }


def _rank_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _safe_rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _int(item) for key, item in value.items()}


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


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
