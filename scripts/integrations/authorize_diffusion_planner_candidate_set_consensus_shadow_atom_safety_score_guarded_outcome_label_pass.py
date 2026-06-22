#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    GUARD_ENV_ASSIGNMENT,
    GUARD_ENV_VAR,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_authorized"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_authorization_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_execution_only"
)

PLAN_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_consideration_plan.json"
)
PLAN_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_consideration_plan.md"
)
RUNBOOK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_runbook.sh"
)
SHA_FILE = "SHA256SUMS"
HEADS_FILE = "HEADS.txt"
EXPECTED_ARTIFACT_FILES = (PLAN_JSON, PLAN_MD, RUNBOOK, SHA_FILE, HEADS_FILE)

FORBIDDEN_PLAN_FLAGS = (
    "outcome_label_generation_authorized",
    "label_attachment_authorized",
    "safety_score_evaluation_retry_authorized",
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
            "Authorization-only gate for the guarded nonformal outcome-label "
            "pass. It verifies plan artifacts, SHA/HEADS, runtime heads, "
            "asset paths, runbook guard, nonformal route matrix, and blocked "
            "actions. It does not execute the label pass."
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
    asset_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(plan_root)
    plan_payload = artifact["plan_json"]
    runbook_text = artifact["runbook_text"]
    runtime_summary = _runtime_summary(runtime)
    plan_summary = _plan_summary(plan_payload, runbook_text)
    asset_summary = _asset_summary(plan_summary, asset_exists or _path_is_file)
    checks = [
        *_artifact_checks(artifact),
        *_runtime_checks(runtime_summary),
        *_plan_decision_checks(plan_summary),
        *_runbook_checks(plan_summary),
        *_scope_checks(plan_summary),
        *_asset_checks(asset_summary),
        *_criteria_checks(plan_summary),
        *_boundary_checks(plan_summary),
    ]
    passed = all(check["passed"] for check in checks)
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "guarded_outcome_label_pass_authorization_v1"
            ),
            "label": label,
            "role": (
                "authorization gate for a guarded nonformal outcome-label pass "
                "only; no label pass execution in this script"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "outcome_label_pass_executed": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": 0,
            "paths": paths or {"plan_root": str(plan_root)},
            "math_boundary": (
                "This gate verifies whether a later guarded offline label pass "
                "may be run. It does not execute DP, generate "
                "candidate_closed_loop_outcomes, attach labels, compute "
                "SafetyCost v1, retry safety-score evaluation, train CAMP, or "
                "alter online selection. Posterior labels remain offline "
                "evaluation labels only and are forbidden for atom definition, "
                "lambda selection, online scoring, CAMP training, and any "
                "DP-side classical Benders claim. DP remains a fixed black-box "
                "finite candidate generator; score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 master are unchanged."
            ),
        },
        "artifact_summary": artifact["public"],
        "runtime_summary": runtime_summary,
        "plan_summary": plan_summary,
        "asset_summary": asset_summary,
        "authorization_checks": checks,
        "final_decision": _final_decision(passed, failed_checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["plan_summary"]
    runtime = report["runtime_summary"]
    lines = [
        "# Candidate-Set Consensus Guarded Outcome-Label Pass Authorization",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Outcome-label pass execution authorized: `{decision['outcome_label_pass_execution_authorized']}`",
        f"- Guard env var: `{decision['guard_env_var']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Runtime",
        "",
        f"- Current CAMP HEAD: `{runtime['current_camp_head']}`",
        f"- Current origin/main: `{runtime['current_origin_main']}`",
        f"- Current DP HEAD: `{runtime['current_dp_head']}`",
        f"- CAMP branch: `{runtime['current_camp_branch']}`",
        f"- DP branch: `{runtime['current_dp_branch']}`",
        f"- CAMP tracked dirty lines: `{runtime['camp_tracked_dirty_lines']}`",
        f"- DP tracked dirty lines: `{runtime['dp_tracked_dirty_lines']}`",
        "",
        "## Artifact",
        "",
        f"- Plan root: `{report['artifact_summary']['plan_root']}`",
        f"- SHA entries matched: `{report['artifact_summary']['sha_entries_matched']}`",
        f"- Artifact heads: `{report['artifact_summary']['heads']}`",
        "",
        "## Planned Scope",
        "",
        f"- Run count: `{plan['run_count']}`",
        f"- Command count: `{plan['label_pass_command_count']}`",
        f"- Expected records: `{plan['expected_records']}`",
        f"- Expected candidates: `{plan['expected_candidates']}`",
        f"- Seeds: `{plan['seeds']}`",
        f"- Scenario coverage: `{plan['scenario_coverage']}`",
        f"- Missing assets: `{report['asset_summary']['missing_assets']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This authorization does not execute the label pass. If accepted, the "
        "only next work is guarded outcome-label pass execution with the "
        f"`{GUARD_ENV_ASSIGNMENT}` guard and no formal seeds, no CAMP training, "
        "no atom promotion, no online selector change, and no DP modification.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["authorization_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
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
    pass_plan = _dict(plan.get("guarded_outcome_label_pass_plan"))
    route_matrix = _list_of_dicts(pass_plan.get("route_seed_matrix"))
    commands = _list_of_dicts(_dict(plan.get("commands")).get("label_passes"))
    command_seeds = sorted(
        {
            int(value)
            for value in (_command_value(item.get("command"), "--seed") for item in commands)
            if value is not None
        }
    )
    command_run_ids = sorted(str(item.get("run_id")) for item in commands)
    route_run_ids = sorted(str(row.get("run_id")) for row in route_matrix)
    seeds = sorted(
        int(row.get("seed"))
        for row in route_matrix
        if _optional_int(row.get("seed")) is not None
    )
    scenario_buckets = sorted(
        {
            str(bucket)
            for row in route_matrix
            for bucket in row.get("scenario_buckets") or []
        }
    )
    return {
        "source_status": final.get("status"),
        "source_passed": bool(final.get("passed")),
        "source_authorized_next_work": final.get("authorized_next_work"),
        "source_plan_artifact_ready": bool(final.get("plan_artifact_ready")),
        "source_execution_authorized": bool(
            final.get("outcome_label_pass_execution_authorized")
        ),
        "source_forbidden_flag_conflicts": [
            flag for flag in FORBIDDEN_PLAN_FLAGS if bool(final.get(flag))
        ],
        "source_guard_env_assignment": final.get("guard_env_assignment"),
        "guard_env_var_present": GUARD_ENV_VAR in runbook_text,
        "guard_requires_yes": '!= "yes"' in runbook_text or "!= 'yes'" in runbook_text,
        "guard_exits_before_execution": "exit 2" in runbook_text,
        "runbook_collects_outcomes": "--camp_collect_closed_loop_outcomes" in runbook_text,
        "runbook_logs_payload": "--camp_candidate_set_consensus_payload_logging" in runbook_text,
        "plan_only": bool(pass_plan.get("plan_only")),
        "label_output_root": pass_plan.get("label_output_root"),
        "expected_logs": _optional_int(pass_plan.get("expected_logs")),
        "expected_records": _optional_int(pass_plan.get("expected_records")),
        "expected_candidates": _optional_int(pass_plan.get("expected_candidates")),
        "expected_records_per_log": _optional_int(pass_plan.get("expected_records_per_log")),
        "run_count": len(route_matrix),
        "label_pass_command_count": len(commands),
        "route_run_ids": route_run_ids,
        "command_run_ids": command_run_ids,
        "seeds": seeds,
        "command_seeds": command_seeds,
        "scenario_coverage": list(pass_plan.get("scenario_coverage") or []),
        "scenario_buckets": scenario_buckets,
        "collector_settings": _dict(pass_plan.get("collector_settings")),
        "candidate_ordering_invariants": list(pass_plan.get("candidate_ordering_invariants") or []),
        "required_output_artifacts": list(pass_plan.get("required_output_artifacts") or []),
        "accept_criteria": list(plan.get("accept_criteria") or []),
        "reject_criteria": list(plan.get("reject_criteria") or []),
        "stop_conditions": list(plan.get("stop_conditions") or []),
        "math_boundary": _dict(plan.get("analysis")).get("math_boundary"),
        "commands": commands,
        "route_matrix": route_matrix,
    }


def _asset_summary(
    plan_summary: dict[str, Any],
    asset_exists: Callable[[str], bool],
) -> dict[str, Any]:
    assets: set[str] = set()
    for row in plan_summary["route_matrix"]:
        for field in ("map_path", "route"):
            value = row.get(field)
            if value:
                assets.add(str(value))
    for item in plan_summary["commands"]:
        command = _command_list(item.get("command"))
        for option in (
            "--model_path",
            "--model_args",
            "--config",
            "--reward_config",
            "--camp_atom_scales",
            "--camp_static_weights",
        ):
            value = _command_value(command, option)
            if value:
                assets.add(str(value))
    status = {asset: bool(asset_exists(asset)) for asset in sorted(assets)}
    return {
        "asset_count": len(status),
        "assets": status,
        "missing_assets": [path for path, exists in status.items() if not exists],
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
            {
                "camp_head",
                "camp_origin_main",
                "dp_head",
                "guard_env_assignment",
                "source_search_json",
                "label_output_root",
            }.issubset(heads),
            True,
        ),
        _check_equal("artifact_heads_camp_synced_at_generation", heads.get("camp_head"), heads.get("camp_origin_main")),
        _check_equal("artifact_heads_dp_fixed", heads.get("dp_head"), EXPECTED_DP_HEAD),
        _check_equal(
            "artifact_heads_guard_recorded",
            heads.get("guard_env_assignment"),
            GUARD_ENV_ASSIGNMENT,
        ),
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
        _check_equal("runtime_camp_no_tracked_dirty", summary["camp_tracked_dirty_lines"], []),
        _check_equal("runtime_dp_no_tracked_dirty", summary["dp_tracked_dirty_lines"], []),
    ]


def _plan_decision_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_status_ready", summary["source_status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", summary["source_passed"], True),
        _check_equal(
            "plan_authorizes_this_authorization_gate",
            summary["source_authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("plan_artifact_ready", summary["source_plan_artifact_ready"], True),
        _check_equal(
            "plan_execution_not_pre_authorized",
            summary["source_execution_authorized"],
            False,
        ),
        _check_equal("plan_no_forbidden_flag_conflicts", summary["source_forbidden_flag_conflicts"], []),
        _check_equal("plan_guard_assignment_matches", summary["source_guard_env_assignment"], GUARD_ENV_ASSIGNMENT),
    ]


def _runbook_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("runbook_guard_env_present", summary["guard_env_var_present"], True),
        _check_equal("runbook_requires_yes", summary["guard_requires_yes"], True),
        _check_equal("runbook_exits_before_unapproved_execution", summary["guard_exits_before_execution"], True),
        _check_equal("runbook_collects_closed_loop_outcomes", summary["runbook_collects_outcomes"], True),
        _check_equal("runbook_logs_candidate_payload", summary["runbook_logs_payload"], True),
    ]


def _scope_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    route_formal_seen = sorted(set(summary["seeds"]) & FORMAL_SEEDS)
    command_formal_seen = sorted(set(summary["command_seeds"]) & FORMAL_SEEDS)
    coverage = set(summary["scenario_coverage"])
    collector = summary["collector_settings"]
    invariants = " ".join(str(item) for item in summary["candidate_ordering_invariants"]).lower()
    artifacts = " ".join(str(item) for item in summary["required_output_artifacts"]).lower()
    command_steps = sorted(
        {
            _command_value(item.get("command"), "--steps")
            for item in summary["commands"]
        }
    )
    command_candidates = sorted(
        {
            _command_value(item.get("command"), "--num_candidates")
            for item in summary["commands"]
        }
    )
    command_collects = all(
        "--camp_collect_closed_loop_outcomes" in _command_list(item.get("command"))
        for item in summary["commands"]
    )
    command_logs_payload = all(
        "--camp_candidate_set_consensus_payload_logging" in _command_list(item.get("command"))
        for item in summary["commands"]
    )
    return [
        _check_equal("scope_plan_only", summary["plan_only"], True),
        _check_equal("scope_expected_logs", summary["expected_logs"], EXPECTED_LOGS),
        _check_equal("scope_expected_records", summary["expected_records"], EXPECTED_RECORDS),
        _check_equal("scope_expected_candidates", summary["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("scope_expected_records_per_log", summary["expected_records_per_log"], EXPECTED_RECORDS // EXPECTED_LOGS),
        _check_equal("scope_run_count", summary["run_count"], EXPECTED_LOGS),
        _check_equal("scope_label_pass_command_count", summary["label_pass_command_count"], EXPECTED_LOGS),
        _check_equal("scope_command_run_ids_match_route_matrix", summary["command_run_ids"], summary["route_run_ids"]),
        _check_equal("scope_route_matrix_no_formal_seeds", route_formal_seen, []),
        _check_equal("scope_commands_no_formal_seeds", command_formal_seen, []),
        _check_equal("scope_traffic_light_coverage", "traffic_light" in coverage, True),
        _check_equal("scope_turn_coverage", bool({"red_light_turn", "sharp_turn"} & coverage), True),
        _check_equal("scope_normal_coverage", "normal" in coverage, True),
        _check_equal("scope_dense_coverage", "dense_scene" in coverage, True),
        _check_equal("scope_collector_candidates", collector.get("num_candidates"), EXPECTED_CANDIDATES),
        _check_equal("scope_collector_outcomes_enabled", collector.get("camp_collect_closed_loop_outcomes"), True),
        _check_equal("scope_collector_payload_logging_enabled", collector.get("camp_candidate_set_consensus_payload_logging"), True),
        _check_equal("scope_command_steps_fixed", command_steps, ["10"]),
        _check_equal("scope_command_candidates_fixed", command_candidates, ["8"]),
        _check_equal("scope_commands_collect_outcomes", command_collects, True),
        _check_equal("scope_commands_log_payload", command_logs_payload, True),
        _check_equal("scope_candidate_index_invariant_declared", "candidate_index 0..7" in invariants, True),
        _check_equal("scope_no_duplicate_root_invariant_declared", "duplicate artifact roots" in invariants, True),
        _check_equal("scope_required_outputs_declare_heads_sha", "heads" in artifacts and "sha256sums" in artifacts, True),
    ]


def _asset_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("assets_declared", summary["asset_count"] > 0, True),
        _check_equal("assets_all_exist", summary["missing_assets"], []),
    ]


def _criteria_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    criteria_text = " ".join(
        [
            *summary["accept_criteria"],
            *summary["reject_criteria"],
            *summary["stop_conditions"],
        ]
    ).lower()
    return [
        _check_equal("criteria_accept_present", len(summary["accept_criteria"]) >= 5, True),
        _check_equal("criteria_reject_present", len(summary["reject_criteria"]) >= 5, True),
        _check_equal("criteria_stop_present", len(summary["stop_conditions"]) >= 5, True),
        _check_equal("criteria_mentions_heads_sha", "heads" in criteria_text and "sha" in criteria_text, True),
        _check_equal("criteria_mentions_formal_seeds", "formal seed" in criteria_text, True),
        _check_equal("criteria_mentions_candidate_ordering", "candidate ordering" in criteria_text, True),
        _check_equal("criteria_mentions_training_or_promotion_block", "training" in criteria_text and "promotion" in criteria_text, True),
        _check_equal("criteria_mentions_dp_modification_block", "dp modification" in criteria_text, True),
        _check_equal("criteria_mentions_safety_score_retry_block", "safety-score" in criteria_text, True),
    ]


def _boundary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    math_text = str(summary["math_boundary"] or "")
    return [
        _check_equal("boundary_forbids_outcome_use_for_selection", "online scoring" in math_text, True),
        _check_equal("boundary_forbids_training", "CAMP training" in math_text, True),
        _check_equal("boundary_preserves_affine_score", "score_k(w)=a_k^T w" in math_text, True),
        _check_equal("boundary_preserves_convex_master", "simplex/CVaR/L2" in math_text, True),
        _check_equal("boundary_rejects_classic_benders_claim", "classical Benders" in math_text, True),
    ]


def _final_decision(passed: bool, failed_checks: list[str]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": failed_checks,
        "guard_env_var": GUARD_ENV_VAR if passed else None,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT if passed else None,
        "guarded_outcome_label_pass_authorization_ready": passed,
        "outcome_label_pass_execution_authorized": passed,
        "new_replay_authorized": passed,
        "closed_loop_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "six nonformal route/seed logs, 60 records, 8 candidates per "
            f"record, guarded by {GUARD_ENV_ASSIGNMENT}, no formal seeds"
            if passed
            else None
        ),
        "outcome_label_generation_authorized": passed,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
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
        "outcome_label_pass_executed": False,
    }


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
        entries.append({"sha256": parts[0], "file": parts[1].lstrip("*")})
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


def _optional_int(value: Any) -> int | None:
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


def _path_is_file(path: str) -> bool:
    return Path(path).is_file()


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


if __name__ == "__main__":
    main()
