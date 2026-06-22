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
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "fixed_snapshot_execution_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "fixed_snapshot_execution_plan_rejected"
)
SOURCE_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "implementation_unit_tests_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "fixed_snapshot_execution_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "guarded_fixed_snapshot_screen_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SOURCE_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_support_implementation_unit_tests_ed2a156"
)
DEFAULT_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_fixed_snapshot_screen"
)
DEFAULT_SNAPSHOT_ROOT = (
    "/root/autodl-tmp/camp_dp_splice_transform_design_screen_"
    "347ae79_seed2_npc4_tlon"
)
DEFAULT_SNAPSHOT_DIR = f"{DEFAULT_SNAPSHOT_ROOT}/snapshots_no_budget"
DEFAULT_ROUTE_TOPOLOGY_GATE_JSON = (
    f"{DEFAULT_SNAPSHOT_ROOT}/route_topology_support_gate_d0a5e4b/"
    "route_topology_support_gate.json"
)
DEFAULT_REWARD_CONFIG = (
    "/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json"
)
DEFAULT_DIFFUSION_REPO = "/root/autodl-tmp/Diffusion-Planner"
DEFAULT_EXPECTED_SNAPSHOT_COUNT = 57

SOURCE_JSON = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "implementation_unit_tests.json"
)
SOURCE_MD = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "implementation_unit_tests.md"
)
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

GUARD_ENV_VAR = (
    "CANDIDATE_SET_CONSENSUS_LANE_PROJECTED_JERK_PROGRESS_"
    "FIXED_SNAPSHOT_APPROVED"
)
GUARD_ENV_ASSIGNMENT = f"{GUARD_ENV_VAR}=yes"
POLICY_NAME = "lane_projected_jerk_progress_red_stop"

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
    "fixed_snapshot_candidate_generation_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a guarded fixed-snapshot lane-projected "
            "jerk/progress screen. It audits the implementation-unit artifact "
            "and writes a guarded runbook, but does not run the screen."
        )
    )
    parser.add_argument("--implementation_root", type=Path, default=Path(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--execution_root", type=Path, default=Path(DEFAULT_EXECUTION_ROOT))
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        implementation_root=args.implementation_root,
        execution_root=args.execution_root,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_bash.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    args.output_bash.write_text(report["runbook"]["text"], encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    implementation_root: Path,
    execution_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(implementation_root)
    source = _source_summary(artifact.get("json_payload") or {})
    plan = _execution_plan(source, execution_root)
    runbook_text = render_runbook(plan)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_plan_checks(plan),
        *_runbook_checks(runbook_text),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_"
                "jerk_progress_fixed_snapshot_execution_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only guarded fixed-snapshot screen contract after "
                "synthetic unit tests"
            ),
            "plan_only": True,
            "fixed_snapshot_candidate_generation_execution": False,
            "diffusion_planner_candidate_generation": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan reads only the implementation-unit artifact and "
                "fixed-head audit, then writes a guarded future screen runbook. "
                "It does not execute candidate generation, run DP as a "
                "candidate generator, run replay, recompute outcomes, define "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "source_artifact": _strip_payload(artifact),
        "source_summary": source,
        "fixed_snapshot_execution_plan": plan,
        "runbook": {
            "guard_env_var": GUARD_ENV_VAR,
            "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
            "text": runbook_text,
        },
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["fixed_snapshot_execution_plan"]
    lines = [
        "# Lane-Projected Jerk/Progress Fixed-Snapshot Execution Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{plan['selected_next_work']}`",
        f"- Guard env: `{report['runbook']['guard_env_assignment']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Scope",
        "",
    ]
    for key, value in plan["snapshot_scope"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Command Contract", ""])
    for item in plan["command_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Accept Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Reject Criteria", ""])
    for item in plan["reject_criteria"]:
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
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def render_runbook(plan: dict[str, Any]) -> str:
    scope = plan["snapshot_scope"]
    config = plan["candidate_config"]
    output_root = plan["execution_artifacts"]["output_root"]
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            f'if [ "${{{GUARD_ENV_VAR}:-}}" != "yes" ]; then',
            f"  echo 'Refusing to run without {GUARD_ENV_ASSIGNMENT}' >&2",
            "  exit 2",
            "fi",
            "",
            "cd /root/autodl-tmp/camp_core",
            'PY="${PY:-/root/miniconda3/bin/python}"',
            f'OUT="{output_root}"',
            f'SNAPSHOT_DIR="{scope["snapshot_dir"]}"',
            f'ROUTE_TOPOLOGY_GATE_JSON="{scope["route_topology_gate_json"]}"',
            f'REWARD_CONFIG="{scope["reward_config"]}"',
            f'DIFFUSION_REPO="{scope["diffusion_repo"]}"',
            "mkdir -p \"$OUT\"",
            "",
            'CAMP_HEAD="$(git rev-parse HEAD)"',
            'CAMP_ORIGIN_MAIN="$(git rev-parse origin/main)"',
            'DP_HEAD="$(cd "$DIFFUSION_REPO" && git rev-parse HEAD)"',
            'SNAPSHOT_COUNT="$(find "$SNAPSHOT_DIR" -maxdepth 1 -type f -name '
            "'camp_microbenchmark_step_*.npz' | wc -l | tr -d ' ')" + '"',
            "",
            "{",
            "  printf 'CAMP_HEAD=%s\\n' \"$CAMP_HEAD\"",
            "  printf 'CAMP_ORIGIN_MAIN=%s\\n' \"$CAMP_ORIGIN_MAIN\"",
            "  printf 'CAMP_BRANCH=%s\\n' \"$(git branch --show-current)\"",
            "  printf 'DP_HEAD=%s\\n' \"$DP_HEAD\"",
            "  printf 'DP_BRANCH=%s\\n' \"$(cd \"$DIFFUSION_REPO\" && git branch --show-current)\"",
            "  printf 'SNAPSHOT_COUNT=%s\\n' \"$SNAPSHOT_COUNT\"",
            "  printf 'SNAPSHOT_DIR=%s\\n' \"$SNAPSHOT_DIR\"",
            "  printf 'OUTPUT_ROOT=%s\\n' \"$OUT\"",
            "} > \"$OUT/HEADS.txt\"",
            "",
            'test "$CAMP_HEAD" = "$CAMP_ORIGIN_MAIN"',
            f'test "$DP_HEAD" = "{EXPECTED_DP_HEAD}"',
            f'test "$SNAPSHOT_COUNT" = "{scope["expected_snapshot_count"]}"',
            "",
            "$PY scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py \\",
            '  --snapshot_dir "$SNAPSHOT_DIR" \\',
            '  --route_topology_gate_json "$ROUTE_TOPOLOGY_GATE_JSON" \\',
            '  --diffusion_repo "$DIFFUSION_REPO" \\',
            '  --reward_config "$REWARD_CONFIG" \\',
            "  --device cuda \\",
            f"  --generator_policy {POLICY_NAME} \\",
            "  --red_stop_margin_m 2.0 \\",
            "  --red_stop_margin_m 4.0 \\",
            "  --red_stop_margin_m 6.0 \\",
            "  --backup_stop_offset_m 0.0 \\",
            "  --backup_stop_offset_m 1.0 \\",
            "  --lane_projected_offset_scale 1.0 \\",
            "  --lane_projected_offset_scale 0.5 \\",
            "  --lane_projected_offset_scale 0.0 \\",
            f"  --max_deceleration_mps2 {config['max_deceleration_mps2']} \\",
            f"  --jerk_progress_max_jerk_mps3 {config['jerk_progress_max_jerk_mps3']} \\",
            "  --label lane_projected_jerk_progress_fixed_snapshot_screen \\",
            '  --output_json "$OUT/route_topology_lane_projected_jerk_progress_screen.json" \\',
            '  --output_md "$OUT/route_topology_lane_projected_jerk_progress_screen.md" \\',
            '  > "$OUT/CANDIDATE_SCREEN.log" 2> "$OUT/CANDIDATE_SCREEN.err"',
            "",
            "$PY scripts/integrations/analyze_diffusion_planner_route_topology_absolute_comfort_guard.py \\",
            '  --screen_json "$OUT/route_topology_lane_projected_jerk_progress_screen.json" \\',
            '  --snapshot_dir "$SNAPSHOT_DIR" \\',
            '  --reward_config "$REWARD_CONFIG" \\',
            "  --label lane_projected_jerk_progress_absolute_lateral_guard \\",
            '  --output_json "$OUT/route_topology_lane_projected_jerk_progress_absolute_lateral_guard.json" \\',
            '  --output_md "$OUT/route_topology_lane_projected_jerk_progress_absolute_lateral_guard.md" \\',
            '  > "$OUT/ABSOLUTE_GUARD.log" 2> "$OUT/ABSOLUTE_GUARD.err"',
            "",
            "printf '0\\n' > \"$OUT/EXIT_CODE\"",
            "cd \"$OUT\"",
            "sha256sum \\",
            "  route_topology_lane_projected_jerk_progress_screen.json \\",
            "  route_topology_lane_projected_jerk_progress_screen.md \\",
            "  route_topology_lane_projected_jerk_progress_absolute_lateral_guard.json \\",
            "  route_topology_lane_projected_jerk_progress_absolute_lateral_guard.md \\",
            "  CANDIDATE_SCREEN.log CANDIDATE_SCREEN.err \\",
            "  ABSOLUTE_GUARD.log ABSOLUTE_GUARD.err \\",
            "  EXIT_CODE HEADS.txt > SHA256SUMS",
            "",
        ]
    )


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
    implementation = _dict(payload.get("implementation"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_unit_tests_ready": bool(
            decision.get("implementation_unit_tests_ready")
        ),
        "fixed_snapshot_execution_plan_authorized": bool(
            decision.get("fixed_snapshot_execution_plan_authorized")
        ),
        "selected_next_work": decision.get("selected_next_work"),
        "policy": implementation.get("policy"),
        "default_policy_remains": implementation.get("default_policy_remains"),
        "generated_shape": implementation.get("generated_shape"),
        "jerk_abs_max_mps3": implementation.get("jerk_abs_max_mps3"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _execution_plan(source: dict[str, Any], execution_root: Path) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "guarded_fixed_snapshot_screen_plan_only",
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "snapshot_scope": {
            "scope_type": "single_existing_nonformal_fixed_snapshot_corpus",
            "source_root": DEFAULT_SNAPSHOT_ROOT,
            "snapshot_dir": DEFAULT_SNAPSHOT_DIR,
            "expected_snapshot_count": DEFAULT_EXPECTED_SNAPSHOT_COUNT,
            "route_name": "sample_map_tl_route_59_to_86",
            "seed": 2,
            "max_npcs": 4,
            "traffic_lights": "on",
            "formal_seeds_frozen": sorted(FORMAL_SEEDS),
            "route_topology_gate_json": DEFAULT_ROUTE_TOPOLOGY_GATE_JSON,
            "reward_config": DEFAULT_REWARD_CONFIG,
            "diffusion_repo": DEFAULT_DIFFUSION_REPO,
        },
        "candidate_config": {
            "generator_policy": POLICY_NAME,
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "lane_projected_offset_scales": [1.0, 0.5, 0.0],
            "max_deceleration_mps2": 3.0,
            "jerk_progress_max_jerk_mps3": 8.0,
            "min_snapshot_support_rate": 0.25,
        },
        "execution_artifacts": {
            "output_root": str(execution_root),
            "candidate_screen_json": (
                f"{execution_root}/route_topology_lane_projected_"
                "jerk_progress_screen.json"
            ),
            "absolute_lateral_guard_json": (
                f"{execution_root}/route_topology_lane_projected_"
                "jerk_progress_absolute_lateral_guard.json"
            ),
            "required_files": [
                "route_topology_lane_projected_jerk_progress_screen.json",
                "route_topology_lane_projected_jerk_progress_screen.md",
                "route_topology_lane_projected_jerk_progress_absolute_lateral_guard.json",
                "route_topology_lane_projected_jerk_progress_absolute_lateral_guard.md",
                "CANDIDATE_SCREEN.log",
                "CANDIDATE_SCREEN.err",
                "ABSOLUTE_GUARD.log",
                "ABSOLUTE_GUARD.err",
                "EXIT_CODE",
                "HEADS.txt",
                "SHA256SUMS",
            ],
        },
        "command_contract": [
            f"runbook must refuse to run unless {GUARD_ENV_ASSIGNMENT} is set",
            "runbook must not git pull, modify remotes, or modify DP",
            "CAMP HEAD must equal origin/main at execution time",
            f"DP HEAD must equal {EXPECTED_DP_HEAD}",
            f"snapshot count must equal {DEFAULT_EXPECTED_SNAPSHOT_COUNT}",
            f"candidate screen must use explicit {POLICY_NAME} policy",
            "candidate screen may recompute DP reward metrics on fixed snapshots only",
            "absolute lateral guard audit must consume the produced screen JSON",
            "artifact must record HEADS, logs, exit code, and SHA256SUMS",
        ],
        "accept_criteria": [
            "candidate screen command exits 0",
            "absolute lateral guard command exits 0",
            "screen status is route_topology_candidate_support_present",
            "hard-feasible snapshot support rate >= 0.25",
            "progress-feasible snapshot support rate >= 0.25",
            "comfort-admissible snapshot support rate >= 0.25",
            "absolute lateral guard status is route_topology_absolute_lateral_guard_support_present",
            "absolute lateral guard snapshot support rate >= 0.25",
            "generated candidate rows > 0 and finite",
            "candidate-build p95 latency <= 10 ms",
            "total p95 latency <= 100 ms",
        ],
        "reject_criteria": [
            "missing source artifact, HEADS, logs, exit code, or SHA256SUMS",
            "CAMP HEAD differs from origin/main",
            f"DP HEAD differs from {EXPECTED_DP_HEAD}",
            "runbook guard is missing or bypassed",
            "snapshot scope differs from the single nonformal seed2 npc4 tl-on corpus",
            "formal seeds 11/12/13 appear in the scope or command",
            "screen or absolute guard command exits nonzero",
            "hard, progress, comfort, absolute lateral guard, or latency gate fails",
            "output attempts replay, CAMP retraining, online selector promotion, Full36, or DP modification",
        ],
        "safety_score_evaluation_boundary": {
            "uses_closed_loop_outcomes": False,
            "claims_safety_benefit": False,
            "allowed": (
                "screen may report fixed-snapshot DP hard-feasibility, red-light, "
                "lane, progress, and PerfectTracker comfort diagnostics only"
            ),
        },
        "blocked_boundaries": [
            "this gate is plan-only and does not execute the fixed-snapshot screen",
            "candidate generation execution is not authorized in this gate",
            "replay is not authorized",
            "CAMP retraining is not authorized",
            "atom promotion or online selector change is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or DP Top-1 superiority claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "selected_next_work": source["selected_next_work"],
            "policy": source["policy"],
        },
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "implementation_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("implementation_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("implementation_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "implementation_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
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
        _check_equal(
            "source_authorizes_execution_plan",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_unit_tests_ready", source["implementation_unit_tests_ready"], True),
        _check_equal(
            "source_fixed_snapshot_execution_plan_authorized",
            source["fixed_snapshot_execution_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_selected_next_work",
            source["selected_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_policy", source["policy"], POLICY_NAME),
        _check_equal(
            "source_default_policy_remains",
            source["default_policy_remains"],
            "lane_centerline_red_stop",
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scope = plan["snapshot_scope"]
    config = plan["candidate_config"]
    text = " ".join(
        plan["command_contract"]
        + plan["accept_criteria"]
        + plan["reject_criteria"]
        + plan["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("plan_selection_type", plan["selection_type"], "guarded_fixed_snapshot_screen_plan_only"),
        _check_equal("plan_guard_assignment", plan["guard_env_assignment"], GUARD_ENV_ASSIGNMENT),
        _check_equal("plan_single_nonformal_seed", scope["seed"] not in FORMAL_SEEDS, True),
        _check_equal("plan_expected_snapshot_count", scope["expected_snapshot_count"], 57),
        _check_equal("plan_route_topology_gate_declared", bool(scope["route_topology_gate_json"]), True),
        _check_equal("plan_reward_config_declared", bool(scope["reward_config"]), True),
        _check_equal("plan_policy", config["generator_policy"], POLICY_NAME),
        _check_equal("plan_jerk_limit_positive", config["jerk_progress_max_jerk_mps3"] > 0.0, True),
        _check_equal("plan_mentions_latency_p95", "p95" in text and "latency" in text, True),
        _check_equal("plan_mentions_absolute_guard", "absolute lateral guard" in text, True),
        _check_equal("plan_mentions_sha_heads", "sha256sums" in text and "heads" in text, True),
    ]


def _runbook_checks(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    return [
        _check_equal("runbook_guard_env_present", GUARD_ENV_VAR in text, True),
        _check_equal("runbook_requires_guard_yes", '!= "yes"' in text, True),
        _check_equal("runbook_exits_without_guard", "exit 2" in text, True),
        _check_equal("runbook_policy_present", POLICY_NAME in text, True),
        _check_equal("runbook_has_no_git_pull", "git pull" not in lower, True),
        _check_equal("runbook_checks_dp_head", EXPECTED_DP_HEAD in text, True),
        _check_equal("runbook_checks_snapshot_count", "SNAPSHOT_COUNT" in text, True),
        _check_equal("runbook_runs_candidate_screen", "analyze_diffusion_planner_route_topology_candidate_screen.py" in text, True),
        _check_equal("runbook_runs_absolute_guard", "analyze_diffusion_planner_route_topology_absolute_comfort_guard.py" in text, True),
        _check_equal("runbook_records_sha256sums", "sha256sum" in text and "SHA256SUMS" in text, True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["blocked_boundaries"] + plan["reject_criteria"]).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal("boundary_blocks_candidate_generation", "not authorized" in text and "candidate generation" in text, True),
        _check_equal("boundary_blocks_replay", "replay is not authorized" in text, True),
        _check_equal("boundary_blocks_training", "retraining is not authorized" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp weights" in text and "fixed" in text, True),
        _check_equal("boundary_blocks_benders", "classical benders" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "fixed_snapshot_execution_plan_ready": passed,
        "guarded_fixed_snapshot_screen_next_gate_authorized": passed,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "guard_env_var": GUARD_ENV_ASSIGNMENT if passed else None,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
