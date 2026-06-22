#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
    READY_STATUS as PLAN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_broader_nonformal_materiality_replay_authorized"
)
REJECT_STATUS = (
    "candidate_set_consensus_broader_nonformal_materiality_replay_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_guarded_broader_nonformal_materiality_replay_only"
)

GUARD_ENV_VAR = "CANDIDATE_SET_CONSENSUS_BROADER_MATERIALITY_REPLAY_APPROVED"
GUARD_ENV_ASSIGNMENT = f"{GUARD_ENV_VAR}=yes"
EXPECTED_RUNS = 6
EXPECTED_PAIRED_REPLAYS = 12
EXPECTED_STEPS = 10
EXPECTED_CANDIDATES = 8
EXPECTED_RECORDS = 60
EXPECTED_CANDIDATE_ROWS = 480

PLAN_JSON = "candidate_set_consensus_broader_nonformal_materiality_plan.json"
PLAN_MD = "candidate_set_consensus_broader_nonformal_materiality_plan.md"
RUNBOOK = "run_candidate_set_consensus_broader_nonformal_materiality.sh"
SHA_FILE = "SHA256SUMS"
HEADS_FILE = "HEADS.txt"
EXPECTED_ARTIFACT_FILES = (PLAN_JSON, PLAN_MD, RUNBOOK, SHA_FILE, HEADS_FILE)

FORBIDDEN_DECISION_FLAGS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Authorize only the guarded broader nonformal candidate-set "
            "consensus materiality replay after auditing the plan artifact, "
            "CAMP/DP heads, runbook guard, nonformal route matrix, and "
            "promotion boundaries. This script does not run replay."
        )
    )
    parser.add_argument("--plan_root", type=Path, required=True)
    parser.add_argument("--camp_repo", type=Path, default=Path("/root/autodl-tmp/camp_core"))
    parser.add_argument(
        "--diffusion_repo",
        type=Path,
        default=Path("/root/autodl-tmp/Diffusion-Planner"),
    )
    parser.add_argument("--current_camp_head")
    parser.add_argument("--current_origin_main")
    parser.add_argument("--current_dp_head")
    parser.add_argument("--current_camp_branch")
    parser.add_argument("--current_dp_branch")
    parser.add_argument("--current_camp_status_path", type=Path)
    parser.add_argument("--current_dp_status_path", type=Path)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = collect_runtime(args)
    report = build_report(
        plan_root=args.plan_root,
        runtime=runtime,
        label=args.label,
        paths={
            "plan_root": str(args.plan_root),
            "camp_repo": str(args.camp_repo),
            "diffusion_repo": str(args.diffusion_repo),
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


def collect_runtime(args: argparse.Namespace) -> dict[str, Any]:
    camp_repo = Path(args.camp_repo)
    diffusion_repo = Path(args.diffusion_repo)
    camp_status = _read_text(args.current_camp_status_path)
    dp_status = _read_text(args.current_dp_status_path)
    if camp_status is None:
        camp_status = _git(camp_repo, "status", "--short", "--branch")
    if dp_status is None:
        dp_status = _git(diffusion_repo, "status", "--short", "--branch")
    return {
        "current_camp_head": args.current_camp_head
        or _git(camp_repo, "rev-parse", "HEAD").strip(),
        "current_origin_main": args.current_origin_main
        or _git(camp_repo, "rev-parse", "origin/main").strip(),
        "current_dp_head": args.current_dp_head
        or _git(diffusion_repo, "rev-parse", "HEAD").strip(),
        "current_camp_branch": args.current_camp_branch
        or _git(camp_repo, "branch", "--show-current").strip(),
        "current_dp_branch": args.current_dp_branch
        or _git(diffusion_repo, "branch", "--show-current").strip(),
        "current_camp_status": camp_status,
        "current_dp_status": dp_status,
    }


def build_report(
    *,
    plan_root: Path,
    runtime: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(plan_root)
    plan = artifact["plan_json"]
    runtime_summary = _runtime_summary(runtime)
    plan_summary = _plan_summary(plan, artifact["runbook_text"])
    checks = [
        *_artifact_checks(artifact),
        *_runtime_checks(runtime_summary),
        *_plan_decision_checks(plan_summary),
        *_runbook_checks(plan_summary),
        *_scope_checks(plan_summary),
        *_criteria_checks(plan_summary),
        *_boundary_checks(plan_summary),
    ]
    passed = all(check["passed"] for check in checks)
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_broader_nonformal_"
                "materiality_replay_authorization_v1"
            ),
            "label": label,
            "role": (
                "authorization gate for guarded broader nonformal replay only; "
                "no replay execution in this script"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {"plan_root": str(plan_root)},
            "math_boundary": (
                "DP remains a fixed black-box finite-candidate generator. This "
                "gate authorizes only replay of the predeclared current-tick "
                "candidate-set consensus logging matrix. It introduces no atom, "
                "no online selector weight, no CAMP retraining, and no DP "
                "modification. Any later atom must separately prove a fixed "
                "coefficient preserving score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master; no DP-side classical Benders "
                "master/subproblem, dual, or valid cuts are claimed here."
            ),
        },
        "artifact_summary": artifact["public"],
        "runtime_summary": runtime_summary,
        "plan_summary": plan_summary,
        "checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "failed_checks": failed_checks,
            "plan_artifact_authorized_for_guarded_replay": passed,
            "broader_replay_authorized": passed,
            "new_replay_authorized": passed,
            "closed_loop_replay_authorized": passed,
            "closed_loop_replay_scope": (
                "6 paired nonformal runs x 10 steps x 8 candidates, baseline "
                "plus default-off logging-enabled candidate-set consensus, "
                "selector-neutral, guarded by "
                f"{GUARD_ENV_ASSIGNMENT}, no formal seeds"
                if passed
                else None
            ),
            "guard_env_var": GUARD_ENV_ASSIGNMENT if passed else None,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Broader Nonformal Materiality Replay Authorization",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Broader replay authorized: `{decision['broader_replay_authorized']}`",
        f"- Guard env var: `{decision['guard_env_var']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Artifact",
        "",
        f"- Plan root: `{report['artifact_summary']['plan_root']}`",
        f"- SHA entries matched: `{report['artifact_summary']['sha_entries_matched']}`",
        f"- Artifact CAMP HEAD: `{report['artifact_summary']['heads'].get('CAMP_HEAD')}`",
        f"- Artifact DP HEAD: `{report['artifact_summary']['heads'].get('DP_HEAD')}`",
        "",
        "## Runtime",
        "",
        f"- Current CAMP HEAD: `{report['runtime_summary']['current_camp_head']}`",
        f"- Current origin/main: `{report['runtime_summary']['current_origin_main']}`",
        f"- Current DP HEAD: `{report['runtime_summary']['current_dp_head']}`",
        f"- CAMP branch: `{report['runtime_summary']['current_camp_branch']}`",
        f"- DP branch: `{report['runtime_summary']['current_dp_branch']}`",
        f"- CAMP tracked dirty lines: `{report['runtime_summary']['camp_tracked_dirty_lines']}`",
        f"- DP tracked dirty lines: `{report['runtime_summary']['dp_tracked_dirty_lines']}`",
        "",
        "## Scope",
        "",
        f"- Runs: `{report['plan_summary']['run_count']}`",
        f"- Paired replay commands: `{report['plan_summary']['paired_replay_count']}`",
        f"- Planned records: `{report['plan_summary']['planned_records']}`",
        f"- Planned candidate rows: `{report['plan_summary']['planned_candidate_rows']}`",
        f"- Route names: `{report['plan_summary']['route_names']}`",
        f"- Seeds: `{report['plan_summary']['seeds']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(plan_root: Path) -> dict[str, Any]:
    paths = {name: plan_root / name for name in EXPECTED_ARTIFACT_FILES}
    exists = {name: path.is_file() for name, path in paths.items()}
    plan_json = _load_json(paths[PLAN_JSON]) if exists[PLAN_JSON] else {}
    runbook_text = paths[RUNBOOK].read_text(encoding="utf-8") if exists[RUNBOOK] else ""
    sha_entries = _parse_sha256sums(paths[SHA_FILE]) if exists[SHA_FILE] else []
    sha_results = []
    for entry in sha_entries:
        file_path = plan_root / entry["file"]
        actual = _sha256(file_path) if file_path.is_file() else None
        sha_results.append(
            {
                "file": entry["file"],
                "expected": entry["sha256"],
                "actual": actual,
                "passed": actual == entry["sha256"],
            }
        )
    heads = _parse_heads(paths[HEADS_FILE]) if exists[HEADS_FILE] else {}
    expected_sha_files = {PLAN_JSON, PLAN_MD, RUNBOOK, HEADS_FILE}
    return {
        "plan_json": plan_json,
        "runbook_text": runbook_text,
        "public": {
            "plan_root": str(plan_root),
            "file_exists": exists,
            "sha_entries": sha_results,
            "sha_entries_matched": bool(sha_results)
            and all(entry["passed"] for entry in sha_results),
            "sha_files_recorded": sorted(entry["file"] for entry in sha_entries),
            "expected_sha_files": sorted(expected_sha_files),
            "heads": heads,
        },
    }


def _runtime_summary(runtime: dict[str, Any]) -> dict[str, Any]:
    camp_status = str(runtime.get("current_camp_status") or "")
    dp_status = str(runtime.get("current_dp_status") or "")
    return {
        "current_camp_head": runtime.get("current_camp_head"),
        "current_origin_main": runtime.get("current_origin_main"),
        "current_dp_head": runtime.get("current_dp_head"),
        "current_camp_branch": runtime.get("current_camp_branch"),
        "current_dp_branch": runtime.get("current_dp_branch"),
        "current_camp_status": camp_status,
        "current_dp_status": dp_status,
        "camp_tracked_dirty_lines": _tracked_dirty_lines(camp_status),
        "dp_tracked_dirty_lines": _tracked_dirty_lines(dp_status),
        "camp_untracked_lines": _untracked_lines(camp_status),
        "dp_untracked_lines": _untracked_lines(dp_status),
    }


def _plan_summary(plan: dict[str, Any], runbook_text: str) -> dict[str, Any]:
    final = _dict(plan.get("final_decision"))
    spec = _dict(plan.get("plan_spec"))
    coverage = _dict(plan.get("coverage_targets"))
    route_matrix = _list_of_dicts(plan.get("route_seed_matrix"))
    paired_replays = _list_of_dicts(_dict(plan.get("commands")).get("paired_replays"))
    seeds = sorted({int(run.get("seed", -1)) for run in route_matrix})
    command_seeds = sorted(
        {
            int(value)
            for value in (
                _command_value(item.get("command"), "--seed") for item in paired_replays
            )
            if value is not None
        }
    )
    route_names = sorted(
        str(run.get("route_name"))
        for run in route_matrix
        if run.get("route_name") is not None
    )
    map_names = sorted(
        str(run.get("map_name"))
        for run in route_matrix
        if run.get("map_name") is not None
    )
    buckets: set[str] = set()
    for run in route_matrix:
        buckets.update(str(item) for item in run.get("scenario_buckets") or [])
    variants_by_run: dict[str, set[str]] = {}
    for item in paired_replays:
        run_id = str(item.get("run_id"))
        variants_by_run.setdefault(run_id, set()).add(str(item.get("variant")))
    return {
        "source_status": final.get("status"),
        "source_passed": bool(final.get("passed")),
        "source_authorized_next_work": final.get("authorized_next_work"),
        "source_plan_only": bool(final.get("plan_only")),
        "source_broader_replay_authorized": bool(
            final.get("broader_replay_authorized")
        ),
        "source_new_replay_authorized": bool(final.get("new_replay_authorized")),
        "source_forbidden_flag_conflicts": [
            flag for flag in FORBIDDEN_DECISION_FLAGS if bool(final.get(flag))
        ],
        "guard_env_var_present": GUARD_ENV_VAR in runbook_text,
        "guard_requires_yes": '!= "yes"' in runbook_text or "!= 'yes'" in runbook_text,
        "guard_exits_before_replay": "exit 2" in runbook_text,
        "run_count": len(route_matrix),
        "paired_replay_count": len(paired_replays),
        "baseline_replay_count": sum(
            1 for item in paired_replays if item.get("variant") == "baseline"
        ),
        "logging_replay_count": sum(
            1 for item in paired_replays if item.get("variant") == "logging_enabled"
        ),
        "variants_by_run": {
            run_id: sorted(variants) for run_id, variants in variants_by_run.items()
        },
        "steps": _int_or_none(spec.get("steps")),
        "num_candidates": _int_or_none(spec.get("num_candidates")),
        "payload_steps": _int_or_none(spec.get("payload_steps")),
        "planned_records": coverage.get("planned_records"),
        "planned_candidate_rows": coverage.get("planned_candidate_rows"),
        "min_available_records": coverage.get("expected_available_payload_records_min"),
        "seeds": seeds,
        "command_seeds": command_seeds,
        "route_names": route_names,
        "map_names": map_names,
        "scenario_buckets": sorted(buckets),
        "traffic_light_modes": sorted(
            str(run.get("traffic_lights"))
            for run in route_matrix
            if run.get("traffic_lights") is not None
        ),
        "baseline_commands_logging_neutral": all(
            "--camp_candidate_set_consensus_payload_logging"
            not in _command_list(item.get("command"))
            for item in paired_replays
            if item.get("variant") == "baseline"
        ),
        "logging_commands_enable_payload": all(
            "--camp_candidate_set_consensus_payload_logging"
            in _command_list(item.get("command"))
            for item in paired_replays
            if item.get("variant") == "logging_enabled"
        ),
        "all_command_steps": sorted(
            {
                _command_value(item.get("command"), "--steps")
                for item in paired_replays
            }
        ),
        "all_command_candidates": sorted(
            {
                _command_value(item.get("command"), "--num_candidates")
                for item in paired_replays
            }
        ),
        "accept_criteria": list(plan.get("accept_criteria") or []),
        "reject_criteria": list(plan.get("reject_criteria") or []),
        "operational_boundaries": _dict(plan.get("operational_boundaries")),
        "diagnostic_contract": _dict(plan.get("diagnostic_contract")),
        "safety_score_evaluation_boundary": _dict(
            plan.get("safety_score_evaluation_boundary")
        ),
        "math_boundary": _dict(plan.get("analysis")).get("math_boundary"),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    public = artifact["public"]
    file_exists = public["file_exists"]
    heads = public["heads"]
    sha_files = set(public["sha_files_recorded"])
    return [
        _check_equal("artifact_plan_json_exists", file_exists[PLAN_JSON], True),
        _check_equal("artifact_plan_md_exists", file_exists[PLAN_MD], True),
        _check_equal("artifact_runbook_exists", file_exists[RUNBOOK], True),
        _check_equal("artifact_sha256sums_exists", file_exists[SHA_FILE], True),
        _check_equal("artifact_heads_exists", file_exists[HEADS_FILE], True),
        _check_equal("artifact_sha_entries_match", public["sha_entries_matched"], True),
        _check_equal(
            "artifact_sha_records_required_payloads",
            {PLAN_JSON, PLAN_MD, RUNBOOK, HEADS_FILE}.issubset(sha_files),
            True,
        ),
        _check_equal(
            "artifact_heads_have_required_keys",
            {"CAMP_HEAD", "CAMP_ORIGIN_MAIN", "DP_HEAD"}.issubset(heads),
            True,
        ),
        _check_equal(
            "artifact_heads_camp_synced_at_generation",
            heads.get("CAMP_HEAD"),
            heads.get("CAMP_ORIGIN_MAIN"),
        ),
        _check_equal("artifact_heads_dp_fixed", heads.get("DP_HEAD"), EXPECTED_DP_HEAD),
    ]


def _runtime_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "runtime_camp_head_matches_origin_main",
            summary["current_camp_head"],
            summary["current_origin_main"],
        ),
        _check_equal("runtime_dp_head_fixed", summary["current_dp_head"], EXPECTED_DP_HEAD),
        _check_equal("runtime_camp_branch_main", summary["current_camp_branch"], "main"),
        _check_equal("runtime_dp_branch_tier4_main", summary["current_dp_branch"], "tier4-main"),
        _check_equal(
            "runtime_camp_no_tracked_dirty",
            summary["camp_tracked_dirty_lines"],
            [],
        ),
        _check_equal("runtime_dp_no_tracked_dirty", summary["dp_tracked_dirty_lines"], []),
    ]


def _plan_decision_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_status_ready", summary["source_status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", summary["source_passed"], True),
        _check_equal(
            "plan_authorizes_this_consideration_gate",
            summary["source_authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("plan_is_plan_only", summary["source_plan_only"], True),
        _check_equal(
            "plan_did_not_authorize_broader_replay",
            summary["source_broader_replay_authorized"],
            False,
        ),
        _check_equal(
            "plan_did_not_authorize_new_replay",
            summary["source_new_replay_authorized"],
            False,
        ),
        _check_equal(
            "plan_no_forbidden_flag_conflicts",
            summary["source_forbidden_flag_conflicts"],
            [],
        ),
    ]


def _runbook_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("runbook_guard_env_present", summary["guard_env_var_present"], True),
        _check_equal("runbook_requires_yes", summary["guard_requires_yes"], True),
        _check_equal(
            "runbook_exits_before_unapproved_replay",
            summary["guard_exits_before_replay"],
            True,
        ),
    ]


def _scope_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    required_routes = {
        "sample_map_tl_route_59_to_86",
        "sample_map_route_2_to_104",
        "nishishinjuku_release_auto_route",
        "nishishinjuku_lane_change_route_7_via_8_to_1",
    }
    required_buckets = {
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "normal",
        "lane_change_or_merge",
        "npc_interaction",
        "dense_scene",
    }
    formal_seen = set(summary["seeds"]) & FORMAL_SEEDS
    formal_command_seen = set(summary["command_seeds"]) & FORMAL_SEEDS
    paired_variants_ok = all(
        variants == ["baseline", "logging_enabled"]
        for variants in summary["variants_by_run"].values()
    )
    return [
        _check_equal("scope_run_count", summary["run_count"], EXPECTED_RUNS),
        _check_equal(
            "scope_paired_replay_count",
            summary["paired_replay_count"],
            EXPECTED_PAIRED_REPLAYS,
        ),
        _check_equal("scope_baseline_replay_count", summary["baseline_replay_count"], EXPECTED_RUNS),
        _check_equal("scope_logging_replay_count", summary["logging_replay_count"], EXPECTED_RUNS),
        _check_equal("scope_each_run_has_paired_variants", paired_variants_ok, True),
        _check_equal("scope_steps", summary["steps"], EXPECTED_STEPS),
        _check_equal("scope_num_candidates", summary["num_candidates"], EXPECTED_CANDIDATES),
        _check_equal("scope_payload_steps", summary["payload_steps"], EXPECTED_STEPS),
        _check_equal("scope_planned_records", summary["planned_records"], EXPECTED_RECORDS),
        _check_equal(
            "scope_planned_candidate_rows",
            summary["planned_candidate_rows"],
            EXPECTED_CANDIDATE_ROWS,
        ),
        _check_equal("scope_min_available_records", summary["min_available_records"], EXPECTED_RECORDS),
        _check_equal("scope_route_matrix_no_formal_seeds", sorted(formal_seen), []),
        _check_equal(
            "scope_replay_commands_no_formal_seeds",
            sorted(formal_command_seen),
            [],
        ),
        _check_equal(
            "scope_required_routes_present",
            required_routes.issubset(set(summary["route_names"])),
            True,
        ),
        _check_equal(
            "scope_sample_and_nishishinjuku_maps_present",
            {"sample_map", "nishishinjuku"}.issubset(set(summary["map_names"])),
            True,
        ),
        _check_equal(
            "scope_required_scenario_buckets_present",
            required_buckets.issubset(set(summary["scenario_buckets"])),
            True,
        ),
        _check_equal(
            "scope_traffic_light_on_off_present",
            {"on", "off"}.issubset(set(summary["traffic_light_modes"])),
            True,
        ),
        _check_equal(
            "scope_baseline_commands_do_not_enable_payload",
            summary["baseline_commands_logging_neutral"],
            True,
        ),
        _check_equal(
            "scope_logging_commands_enable_payload",
            summary["logging_commands_enable_payload"],
            True,
        ),
        _check_equal(
            "scope_replay_command_steps_fixed",
            summary["all_command_steps"],
            [str(EXPECTED_STEPS)],
        ),
        _check_equal(
            "scope_replay_command_candidates_fixed",
            summary["all_command_candidates"],
            [str(EXPECTED_CANDIDATES)],
        ),
    ]


def _criteria_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    criteria_text = " ".join(
        [*summary["accept_criteria"], *summary["reject_criteria"]]
    ).lower()
    return [
        _check_equal("criteria_accept_present", len(summary["accept_criteria"]) >= 10, True),
        _check_equal("criteria_reject_present", len(summary["reject_criteria"]) >= 10, True),
        _check_equal("criteria_mentions_selector_equivalence", "selector" in criteria_text, True),
        _check_equal("criteria_mentions_payload_no_leak", "leak" in criteria_text, True),
        _check_equal("criteria_mentions_latency", "latency" in criteria_text, True),
        _check_equal("criteria_mentions_formal_seed_rejection", "formal seed" in criteria_text, True),
        _check_equal("criteria_mentions_promotion_block", "promotion" in criteria_text, True),
        _check_equal("criteria_mentions_retraining_block", "retraining" in criteria_text, True),
        _check_equal("criteria_mentions_dp_modification_block", "dp modification" in criteria_text, True),
        _check_equal("criteria_mentions_dp_top1_claim_block", "dp top-1" in criteria_text, True),
    ]


def _boundary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    operational = summary["operational_boundaries"]
    diagnostics = summary["diagnostic_contract"]
    safety = summary["safety_score_evaluation_boundary"]
    math_text = str(summary["math_boundary"] or "")
    safety_forbidden = " ".join(str(item) for item in safety.get("forbidden") or [])
    return [
        _check_equal("boundary_selector_equivalence_gate_declared", "selector_equivalence_gate" in operational, True),
        _check_equal("boundary_payload_no_leak_gate_declared", "payload_no_leak_default_off_gate" in operational, True),
        _check_equal("boundary_latency_gate_declared", "latency_gate" in operational, True),
        _check_equal("boundary_fallback_declared", "fallback_boundary" in operational, True),
        _check_equal("boundary_progress_declared", "progress_boundary" in operational, True),
        _check_equal("boundary_comfort_declared", "comfort_boundary" in operational, True),
        _check_equal("boundary_spread_diagnostics_declared", "spread_diagnostics" in diagnostics, True),
        _check_equal("boundary_rank_diagnostics_declared", "rank_diagnostics" in diagnostics, True),
        _check_equal("boundary_sensitivity_diagnostics_declared", "sensitivity_diagnostics" in diagnostics, True),
        _check_equal("boundary_safety_score_forbids_dp_top1_claim", "DP Top-1" in safety_forbidden, True),
        _check_equal("boundary_math_preserves_affine_score", "score_k(w)=a_k^T w" in math_text, True),
        _check_equal("boundary_math_rejects_classic_benders_claim", "classical Benders" in math_text, True),
    ]


def _parse_sha256sums(path: Path) -> list[dict[str, str]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            entries.append({"sha256": "", "file": stripped})
            continue
        file_name = parts[1].lstrip("*")
        entries.append({"sha256": parts[0], "file": file_name})
    return entries


def _parse_heads(path: Path) -> dict[str, str]:
    heads: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        heads[key.strip()] = value.strip()
    return heads


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked_dirty_lines(status: str) -> list[str]:
    return [
        line
        for line in status.splitlines()
        if line and not line.startswith("## ") and not line.startswith("?? ")
    ]


def _untracked_lines(status: str) -> list[str]:
    return [line for line in status.splitlines() if line.startswith("?? ")]


def _command_value(command: Any, option: str) -> str | None:
    command_list = _command_list(command)
    if option not in command_list:
        return None
    index = command_list.index(option)
    if index + 1 >= len(command_list):
        return None
    return str(command_list[index + 1])


def _command_list(command: Any) -> list[str]:
    if not isinstance(command, list):
        return []
    return [str(item) for item in command]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _read_text(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8")


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
