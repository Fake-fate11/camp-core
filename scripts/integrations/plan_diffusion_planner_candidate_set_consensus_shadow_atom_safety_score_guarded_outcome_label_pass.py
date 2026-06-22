#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
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
    BroaderMaterialitySpec,
    EvidenceRunSpec,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)
from scripts.integrations.search_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_sources import (  # noqa: E402
    AUTHORIZED_NEXT_WORK_NO_SOURCE as SOURCE_AUTHORIZED_NEXT_WORK,
    NO_SOURCE_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_consideration_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_consideration_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_authorization_only"
)

GUARD_ENV_VAR = "CANDIDATE_SET_CONSENSUS_OUTCOME_LABEL_PASS_APPROVED"
GUARD_ENV_ASSIGNMENT = f"{GUARD_ENV_VAR}=yes"
DEFAULT_LABEL_OUTPUT_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_candidate_set_consensus_shadow_atom_safety_score_outcome_labels"
)

BLOCKED_SOURCE_ACTIONS = (
    "outcome_label_generation_authorized",
    "label_attachment_authorized",
    "safety_score_evaluation_retry_authorized",
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
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a guarded nonformal outcome-label pass after "
            "the existing-source search found no compatible labels. It emits "
            "scope, guards, commands, and accept/reject criteria, but does not "
            "run replay, generate labels, attach labels, train CAMP, or modify DP."
        )
    )
    parser.add_argument("--source_search_json", type=Path, required=True)
    parser.add_argument("--label_output_root", default=DEFAULT_LABEL_OUTPUT_ROOT)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_search=_load_json(args.source_search_json),
        label=args.label,
        label_output_root=args.label_output_root,
        paths={"source_search_json": str(args.source_search_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if args.output_bash is not None:
        args.output_bash.parent.mkdir(parents=True, exist_ok=True)
        args.output_bash.write_text(render_bash(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    source_search: dict[str, Any],
    label: str | None = None,
    label_output_root: str = DEFAULT_LABEL_OUTPUT_ROOT,
    paths: dict[str, str] | None = None,
    broader_spec: BroaderMaterialitySpec = BroaderMaterialitySpec(),
) -> dict[str, Any]:
    source = _source_summary(source_search)
    selected_runs = _selected_runs(source["expected_run_ids"], broader_spec)
    plan = _outcome_label_pass_plan(
        selected_runs=selected_runs,
        label_output_root=label_output_root,
        broader_spec=broader_spec,
    )
    commands = _commands(plan, broader_spec)
    runbook = render_bash_from_commands(commands, broader_spec)
    checks = [
        *_source_checks(source),
        *_scope_checks(source, plan),
        *_plan_checks(plan),
        *_runbook_checks(runbook),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "guarded_outcome_label_pass_consideration_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only consideration for acquiring missing posterior "
                "candidate_closed_loop_outcomes on the fixed broader nonformal "
                "candidate-set consensus scope"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "outcome_label_generation": False,
            "label_attachment": False,
            "safety_score_evaluation_retry": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This gate only plans a guarded offline label acquisition pass. "
                "It does not generate candidate_closed_loop_outcomes, attach "
                "labels, compute SafetyCost v1, rerun the safety-score "
                "evaluation, or use posterior outcomes for atom definition, "
                "lambda selection, online scoring, CAMP training, or online "
                "candidate selection. DP remains a fixed black-box finite "
                "candidate generator, score_k(w)=a_k^T w is unchanged, the "
                "simplex/CVaR/L2 master is untouched, and no DP-side classical "
                "Benders master/subproblem, dual, or valid-cut claim is made."
            ),
        },
        "source_search_summary": source,
        "guarded_outcome_label_pass_plan": plan,
        "commands": commands,
        "runbook_preview": runbook,
        "consideration_checks": checks,
        "accept_criteria": _accept_criteria(),
        "reject_criteria": _reject_criteria(),
        "stop_conditions": _stop_conditions(),
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["guarded_outcome_label_pass_plan"]
    source = report["source_search_summary"]
    lines = [
        "# Candidate-Set Consensus Guarded Outcome-Label Pass Consideration Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Guard env assignment: `{decision['guard_env_assignment']}`",
        f"- Outcome-label pass execution authorized: `{decision['outcome_label_pass_execution_authorized']}`",
        f"- Outcome-label generation authorized now: `{decision['outcome_label_generation_authorized']}`",
        f"- Replay authorized now: `{decision['new_replay_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Search",
        "",
        f"- Source status: `{source['status']}`",
        f"- Compatible source found: `{source['compatible_source_found']}`",
        f"- Complete outcome logs: `{source['complete_outcome_log_count']}`",
        f"- Formal seed logs: `{source['formal_seed_log_count']}`",
        "",
        "## Planned Scope",
        "",
        f"- Label output root: `{plan['label_output_root']}`",
        f"- Expected logs: `{plan['expected_logs']}`",
        f"- Expected records: `{plan['expected_records']}`",
        f"- Expected candidates: `{plan['expected_candidates']}`",
        f"- Scenario coverage: `{plan['scenario_coverage']}`",
        f"- Guarded runbook env: `{plan['guard_env_assignment']}`",
        "",
        "## Candidate Ordering Invariants",
        "",
    ]
    lines.extend(f"- {item}" for item in plan["candidate_ordering_invariants"])
    lines.extend(["", "## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(f"- {item}" for item in report["stop_conditions"])
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["consideration_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def render_bash(report: dict[str, Any]) -> str:
    if not report["final_decision"].get("plan_artifact_ready"):
        raise ValueError("Cannot render runbook for a rejected plan.")
    spec = BroaderMaterialitySpec()
    return render_bash_from_commands(report["commands"], spec)


def render_bash_from_commands(
    commands: dict[str, Any],
    broader_spec: BroaderMaterialitySpec,
) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Plan-only runbook for a guarded candidate outcome-label pass.",
        "# Do not run unless a later authorization gate explicitly permits it.",
        "# Forbidden now: formal seeds, Full36, online selector promotion, CAMP retraining, DP modification.",
        f"# Expected DP HEAD: {broader_spec.expected_dp_head}",
        "",
        f'if [[ "${{{GUARD_ENV_VAR}:-}}" != "yes" ]]; then',
        '  echo "plan-only runbook: outcome-label pass is not authorized in this gate" >&2',
        "  exit 2",
        "fi",
        "",
        "cd /root/autodl-tmp/camp_core",
        "",
    ]
    for name in ("camp_sync", "asset_audit", "head_audit"):
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    for item in commands["label_passes"]:
        lines.extend(
            [
                f'echo "== outcome label pass {item["run_id"]} =="',
                shlex.join(item["command"]),
                "",
            ]
        )
    lines.extend(
        [
            'echo "candidate_set_consensus_guarded_outcome_label_pass_candidate_complete"',
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    expected = _dict(report.get("expected_scope"))
    source = _dict(report.get("source_summary"))
    scan = _dict(report.get("search_summary"))
    route_seed_matrix = list(source.get("route_seed_matrix") or [])
    blocked_conflicts = [key for key in BLOCKED_SOURCE_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "compatible_source_found": bool(decision.get("compatible_source_found")),
        "guarded_consideration_authorized": bool(
            decision.get("guarded_outcome_label_pass_consideration_plan_authorized")
        ),
        "complete_outcome_log_count": int(scan.get("complete_outcome_log_count") or 0),
        "formal_seed_log_count": int(scan.get("formal_seed_log_count") or 0),
        "expected_logs": int(expected.get("expected_logs") or -1),
        "expected_records": int(expected.get("expected_records") or -1),
        "expected_candidates": int(expected.get("expected_candidates") or -1),
        "expected_run_ids": sorted(str(run_id) for run_id in expected.get("run_ids") or []),
        "route_seed_matrix": route_seed_matrix,
        "route_seeds": sorted(
            int(row.get("seed"))
            for row in route_seed_matrix
            if isinstance(row, dict) and row.get("seed") is not None
        ),
        "blocked_action_conflicts": blocked_conflicts,
    }


def _selected_runs(
    expected_run_ids: list[str],
    broader_spec: BroaderMaterialitySpec,
) -> tuple[EvidenceRunSpec, ...]:
    expected = set(expected_run_ids)
    return tuple(run for run in broader_spec.runs if run.run_id in expected)


def _outcome_label_pass_plan(
    *,
    selected_runs: tuple[EvidenceRunSpec, ...],
    label_output_root: str,
    broader_spec: BroaderMaterialitySpec,
) -> dict[str, Any]:
    return {
        "plan_only": True,
        "label_output_root": label_output_root,
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "expected_records_per_log": EXPECTED_RECORDS // EXPECTED_LOGS,
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "outcome_label_pass_execution_authorized_now": False,
        "route_seed_matrix": [_run_row(run) for run in selected_runs],
        "scenario_coverage": sorted(
            {bucket for run in selected_runs for bucket in run.scenario_buckets}
        ),
        "collector_settings": {
            "camp_collect_closed_loop_outcomes": True,
            "camp_candidate_set_consensus_payload_logging": True,
            "num_candidates": broader_spec.num_candidates,
            "candidate_noise_scale": broader_spec.candidate_noise_scale,
            "candidate_reference_blend_steps": broader_spec.candidate_reference_blend_steps,
            "steps": broader_spec.steps,
            "camp_outcome_horizon_steps": 30,
            "near_miss_threshold_m": 2.0,
            "advance_mode": "perfect",
        },
        "candidate_ordering_invariants": [
            "same six nonformal run_id values as the broader materiality scope",
            "same route, seed, max_npcs, traffic_lights, and spawn_probability per run_id",
            "same num_candidates=8, candidate_noise_scale=1.0, and candidate_reference_blend_steps=5",
            "candidate_closed_loop_outcomes must be length 8 with candidate_index 0..7 per record",
            "records must preserve original tick order and must not mix duplicate artifact roots",
            "posterior labels remain offline evaluation labels and are forbidden for online selection",
        ],
        "required_output_artifacts": [
            "six camp_selection_log.json files under label_output_root/<run_id>/",
            "each log has 10 records and complete candidate_closed_loop_outcomes for all 8 candidates",
            "HEADS.txt with CAMP HEAD, origin/main, DP HEAD, source-search artifact, and runbook path",
            "SHA256SUMS covering JSON, markdown, runbook, HEADS, and produced log manifest",
        ],
    }


def _commands(plan: dict[str, Any], spec: BroaderMaterialitySpec) -> dict[str, Any]:
    label_passes = []
    for row in plan["route_seed_matrix"]:
        output_dir = f"{plan['label_output_root']}/{row['run_id']}"
        label_passes.append(
            {
                "run_id": row["run_id"],
                "command": _label_pass_command(spec, row, output_dir),
            }
        )
    return {
        "camp_sync": ["git", "-C", spec.camp_repo, "pull", "--ff-only", "origin", "main"],
        "asset_audit": _asset_audit_command(spec),
        "head_audit": _head_audit_command(spec),
        "label_passes": label_passes,
    }


def _label_pass_command(
    spec: BroaderMaterialitySpec,
    row: dict[str, Any],
    output_dir: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "REPLAY_NO_PNG=1",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "--diffusion_repo",
        spec.diffusion_repo,
        "--map_path",
        row["map_path"],
        "--route",
        row["route"],
        "--model_path",
        spec.model_path,
        "--model_args",
        spec.model_args,
        "--config",
        spec.config,
        "--output_dir",
        output_dir,
        "--device",
        "cuda",
        "--advance_mode",
        "perfect",
        "--steps",
        str(spec.steps),
        "--seed",
        str(row["seed"]),
        "--max_npcs",
        str(row["max_npcs"]),
        "--spawn_probability",
        str(row["spawn_probability"]),
        "--traffic_lights",
        row["traffic_lights"],
        "--reward_config",
        spec.reward_config,
        "--camp_selector_mode",
        "static",
        "--camp_atom_scales",
        spec.atom_scales,
        "--camp_static_weights",
        spec.static_weights,
        "--num_candidates",
        str(spec.num_candidates),
        "--candidate_noise_scale",
        str(spec.candidate_noise_scale),
        "--candidate_reference_blend_steps",
        str(spec.candidate_reference_blend_steps),
        "--camp_lane_corridor_buffer",
        "1.0",
        "--camp_feasibility_source",
        "dp_reward",
        "--camp_fallback_mode",
        "learned",
        "--camp_min_progress_ratio",
        "0.8",
        "--camp_shadow_route_progress",
        "--camp_shadow_obstacle_clearance",
        "--camp_reward_horizon_steps",
        "30",
        "--camp_outcome_horizon_steps",
        "30",
        "--near_miss_threshold_m",
        "2.0",
        "--camp_candidate_set_consensus_payload_logging",
        "--camp_candidate_set_consensus_payload_steps",
        str(spec.payload_steps),
        "--camp_collect_closed_loop_outcomes",
    ]


def _asset_audit_command(spec: BroaderMaterialitySpec) -> list[str]:
    assets = sorted(
        {
            spec.model_path,
            spec.model_args,
            spec.config,
            spec.reward_config,
            spec.atom_scales,
            spec.static_weights,
            *(run.map_path for run in spec.runs),
            *(run.route for run in spec.runs),
        }
    )
    tests = " && ".join(f"test -f {shlex.quote(path)}" for path in assets)
    return ["/bin/bash", "-lc", f"{tests} && echo outcome_label_pass_assets_ok"]


def _head_audit_command(spec: BroaderMaterialitySpec) -> list[str]:
    return [
        "/bin/bash",
        "-lc",
        (
            f'test "$(git -C {spec.camp_repo} rev-parse HEAD)" = '
            f'"$(git -C {spec.camp_repo} rev-parse origin/main)" && '
            f'test "$(git -C {spec.diffusion_repo} rev-parse HEAD)" = '
            f'"{spec.expected_dp_head}" && '
            f'echo "CAMP_HEAD=$(git -C {spec.camp_repo} rev-parse HEAD)" && '
            f'echo "DP_HEAD=$(git -C {spec.diffusion_repo} rev-parse HEAD)"'
        ),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_guarded_plan",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_has_no_compatible_labels", source["compatible_source_found"], False),
        _check_equal(
            "source_guarded_consideration_authorized",
            source["guarded_consideration_authorized"],
            True,
        ),
        _check_equal("source_no_complete_outcome_logs", source["complete_outcome_log_count"], 0),
        _check_equal("source_no_formal_seed_logs", source["formal_seed_log_count"], 0),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal(
            "source_route_seeds_nonformal",
            sorted(set(source["route_seeds"]) & set(FORMAL_SEEDS)),
            [],
        ),
    ]


def _scope_checks(source: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    run_ids = [row["run_id"] for row in plan["route_seed_matrix"]]
    seeds = [row["seed"] for row in plan["route_seed_matrix"]]
    coverage = set(plan["scenario_coverage"])
    return [
        _check_equal("expected_log_count", source["expected_logs"], EXPECTED_LOGS),
        _check_equal("expected_record_count", source["expected_records"], EXPECTED_RECORDS),
        _check_equal("expected_candidate_count", source["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("planned_run_count", len(run_ids), EXPECTED_LOGS),
        _check_equal("planned_run_ids_match_source", sorted(run_ids), source["expected_run_ids"]),
        _check_equal("planned_seeds_nonformal", sorted(set(seeds) & set(FORMAL_SEEDS)), []),
        _check_equal("traffic_light_coverage", "traffic_light" in coverage, True),
        _check_equal("turn_coverage", bool({"red_light_turn", "sharp_turn"} & coverage), True),
        _check_equal("normal_coverage", "normal" in coverage, True),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    collector = plan["collector_settings"]
    return [
        _check_equal("plan_is_plan_only", plan["plan_only"], True),
        _check_equal(
            "execution_not_authorized_now",
            plan["outcome_label_pass_execution_authorized_now"],
            False,
        ),
        _check_equal("guard_env_assignment", plan["guard_env_assignment"], GUARD_ENV_ASSIGNMENT),
        _check_equal("collector_records_candidates", collector["num_candidates"], EXPECTED_CANDIDATES),
        _check_equal(
            "collector_outcomes_enabled_in_planned_command",
            collector["camp_collect_closed_loop_outcomes"],
            True,
        ),
        _check_equal(
            "collector_payload_logging_enabled",
            collector["camp_candidate_set_consensus_payload_logging"],
            True,
        ),
    ]


def _runbook_checks(runbook: str) -> list[dict[str, Any]]:
    return [
        _check_equal("runbook_guard_env_present", GUARD_ENV_VAR in runbook, True),
        _check_equal("runbook_guard_requires_yes", f'!= "yes"' in runbook, True),
        _check_equal(
            "runbook_collects_closed_loop_outcomes",
            "--camp_collect_closed_loop_outcomes" in runbook,
            True,
        ),
        _check_equal("runbook_forbids_now", "not authorized in this gate" in runbook, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "plan_artifact_ready": passed,
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "guarded_outcome_label_pass_authorization_only": passed,
        "outcome_label_pass_execution_authorized": False,
        "outcome_label_generation_authorized": False,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
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


def _accept_criteria() -> list[str]:
    return [
        "source-search artifact is passed and found no compatible existing outcome-label source",
        "plan contains exactly six nonformal route/seed runs with traffic-light, turn, and normal coverage",
        "guarded runbook contains CANDIDATE_SET_CONSENSUS_OUTCOME_LABEL_PASS_APPROVED=yes guard",
        "planned command preserves candidate ordering inputs and enables candidate_closed_loop_outcomes collection",
        "future execution artifact must produce six logs, 60 records, and complete 8-candidate outcomes per record",
        "HEADS and SHA256SUMS must capture CAMP HEAD, origin/main, fixed DP HEAD, runbook, and outputs",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source-search artifact is not the no-compatible-source ready status",
        "any formal seed 11/12/13 appears in source scope, planned scope, paths, or future logs",
        "planned run count, record count, candidate count, or run_id set differs from the broader nonformal scope",
        "runbook lacks the explicit approval guard or implies execution is already authorized",
        "candidate ordering invariants cannot be audited before attaching labels",
        "any plan flag authorizes training, promotion, safety-score retry, replay execution, online selection, or DP modification",
    ]


def _stop_conditions() -> list[str]:
    return [
        "stop before execution unless a later authorization gate verifies this plan artifact, HEADS, SHA, assets, and guard",
        "stop if CAMP HEAD differs from origin/main or DP HEAD differs from the fixed Tier4 commit",
        "stop if route assets or model assets are missing on AutoDL",
        "stop if future output contains incomplete candidate_closed_loop_outcomes or candidate_index is not contiguous 0..7",
        "stop if any output path or metadata indicates formal seeds, Full36, online selector promotion, training, or DP modification",
    ]


def _run_row(run: EvidenceRunSpec) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "map_name": run.map_name,
        "map_path": run.map_path,
        "route_name": run.route_name,
        "route": run.route,
        "seed": run.seed,
        "max_npcs": run.max_npcs,
        "spawn_probability": run.spawn_probability,
        "traffic_lights": run.traffic_lights,
        "scenario_buckets": list(run.scenario_buckets),
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
