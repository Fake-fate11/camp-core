#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = (11, 12, 13)

POST_REVIEW_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_complete"
)
POST_REVIEW_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_fixed_snapshot_screen_rerun_plan_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_fixed_snapshot_screen_rerun_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_fixed_snapshot_screen_rerun_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_only"
)

DEFAULT_POST_REVIEW_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v4_post_implementation_"
    "static_contract_bff8f8b"
)
DEFAULT_EXECUTION_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v4_fixed_snapshot_screen_"
    "rerun_bff8f8b"
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
DEFAULT_REMOTE_PYTHON = "/root/miniconda3/bin/python"
DEFAULT_EXPECTED_SNAPSHOT_COUNT = 57
DEFAULT_MAX_REMEDIATION_CANDIDATES = 12

POST_REVIEW_JSON = "static_contract_review.json"
POST_REVIEW_MD = "static_contract_review.md"
PLANNED_POLICY = "lane_red_hard_feasible_comfort_first_materialized_support"
REMEDIATION_PROFILE = (
    "lane_red_hard_feasible_comfort_first_materialized_support_v4"
)
GUARD_ENV_VAR = "CAMP_MATERIAL_GENERATOR_V4_FIXED_SNAPSHOT_RERUN_APPROVED"
GUARD_ENV_ASSIGNMENT = f"{GUARD_ENV_VAR}=yes"

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
        description="Plan-only guarded fixed-snapshot screen rerun for material v4."
    )
    parser.add_argument(
        "--post_review_root",
        type=Path,
        default=Path(DEFAULT_POST_REVIEW_ROOT),
    )
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
        post_review_root=args.post_review_root,
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
    post_review_root: Path,
    execution_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(post_review_root)
    source = _post_review_summary(artifact["payload"], artifact["markdown_text"])
    plan = _screen_rerun_plan(execution_root)
    runbook_text = render_runbook(plan)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_plan_checks(plan),
        *_runbook_checks(runbook_text),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_guarded_material_generator_v4_fixed_snapshot_screen_rerun_plan",
            "label": label,
            "role": "plan-only guarded fixed-snapshot screen rerun",
            "plan_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan writes only a future guarded screen-rerun runbook. "
                "It does not execute candidate generation, rerun the screen, "
                "run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights/code/config, claim safety "
                "benefit, or claim CAMP over DP Top-1."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "post_review_artifact": _strip_payload(artifact),
        "post_review_summary": source,
        "fixed_snapshot_screen_rerun_plan": plan,
        "runbook": {
            "path": plan["execution_artifacts"]["runbook"],
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
    plan = report["fixed_snapshot_screen_rerun_plan"]
    lines = [
        "# Guarded Material V4 Fixed-Snapshot Screen Rerun Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Guard env: `{report['runbook']['guard_env_assignment']}`",
        "",
        "## Snapshot Scope",
        "",
    ]
    for key, value in plan["snapshot_scope"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Candidate Config", ""])
    for key, value in plan["candidate_config"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Accept Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def render_runbook(plan: dict[str, Any]) -> str:
    scope = plan["snapshot_scope"]
    config = plan["candidate_config"]
    output_root = plan["execution_artifacts"]["output_root"]
    return f"""#!/usr/bin/env bash
set -euo pipefail

if [[ "${{{GUARD_ENV_VAR}:-}}" != "yes" ]]; then
  echo "Refusing to run: set {GUARD_ENV_ASSIGNMENT} after this plan gate is accepted." >&2
  exit 2
fi

PY="{DEFAULT_REMOTE_PYTHON}"
CAMP_ROOT="/root/autodl-tmp/camp_core"
OUTPUT_ROOT="{output_root}"
SNAPSHOT_DIR="{scope['snapshot_dir']}"
ROUTE_TOPOLOGY_GATE_JSON="{scope['route_topology_gate_json']}"
DIFFUSION_REPO="{scope['diffusion_repo']}"
REWARD_CONFIG="{scope['reward_config']}"
mkdir -p "${{OUTPUT_ROOT}}"

cd "${{CAMP_ROOT}}"
CAMP_HEAD="$(git rev-parse HEAD)"
CAMP_ORIGIN_MAIN="$(git rev-parse origin/main)"
DP_HEAD="$(cd "${{DIFFUSION_REPO}}" && git rev-parse HEAD)"
SNAPSHOT_COUNT="$(find "${{SNAPSHOT_DIR}}" -maxdepth 1 -type f -name 'camp_microbenchmark_step_*.npz' | wc -l | tr -d ' ')"

test "${{CAMP_HEAD}}" = "${{CAMP_ORIGIN_MAIN}}"
test "${{DP_HEAD}}" = "{EXPECTED_DP_HEAD}"
test "${{SNAPSHOT_COUNT}}" = "{scope['expected_snapshot_count']}"

{{
  printf 'CAMP_HEAD=%s\\n' "${{CAMP_HEAD}}"
  printf 'CAMP_ORIGIN_MAIN=%s\\n' "${{CAMP_ORIGIN_MAIN}}"
  printf 'DP_HEAD=%s\\n' "${{DP_HEAD}}"
  printf 'SNAPSHOT_COUNT=%s\\n' "${{SNAPSHOT_COUNT}}"
  printf 'SNAPSHOT_DIR=%s\\n' "${{SNAPSHOT_DIR}}"
  printf 'OUTPUT_ROOT=%s\\n' "${{OUTPUT_ROOT}}"
}} > "${{OUTPUT_ROOT}}/HEADS.txt"

"${{PY}}" scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py \\
  --snapshot_dir "${{SNAPSHOT_DIR}}" \\
  --route_topology_gate_json "${{ROUTE_TOPOLOGY_GATE_JSON}}" \\
  --diffusion_repo "${{DIFFUSION_REPO}}" \\
  --reward_config "${{REWARD_CONFIG}}" \\
  --device cuda \\
  --generator_policy {config['generator_policy']} \\
  --default_off_remediation_profile {config['default_off_remediation_profile']} \\
  --red_stop_margin_m 2.0 \\
  --red_stop_margin_m 4.0 \\
  --red_stop_margin_m 6.0 \\
  --backup_stop_offset_m 0.0 \\
  --backup_stop_offset_m 1.0 \\
  --prefix_step 1 \\
  --bridge_step 0 \\
  --lane_projected_offset_scale 0.0 \\
  --max_deceleration_mps2 {config['max_deceleration_mps2']} \\
  --jerk_progress_max_jerk_mps3 {config['jerk_progress_max_jerk_mps3']} \\
  --min_progress_ratio {config['min_progress_ratio']} \\
  --progress_loss_budget_m 0.5 \\
  --progress_loss_budget_m 1.0 \\
  --progress_loss_budget_m 1.5 \\
  --smoothness_loss_budget 0.0 \\
  --smoothness_loss_budget 0.5 \\
  --smoothness_loss_budget 1.0 \\
  --command_jerk_worse_budget_mps3 {config['command_jerk_worse_budget_mps3']} \\
  --rollout_jerk_worse_budget_mps3 {config['rollout_jerk_worse_budget_mps3']} \\
  --rollout_lateral_worse_budget_mps2 {config['rollout_lateral_worse_budget_mps2']} \\
  --max_remediation_candidates {config['max_remediation_candidates']} \\
  --output_json "${{OUTPUT_ROOT}}/default_off_v4_fixed_snapshot_screen.json" \\
  --output_md "${{OUTPUT_ROOT}}/default_off_v4_fixed_snapshot_screen.md" \\
  > "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.log" \\
  2> "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.err"

sha256sum "${{OUTPUT_ROOT}}"/* > "${{OUTPUT_ROOT}}/SHA256SUMS"
"""


def _screen_rerun_plan(execution_root: Path) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "snapshot_scope": {
            "snapshot_dir": DEFAULT_SNAPSHOT_DIR,
            "route_topology_gate_json": DEFAULT_ROUTE_TOPOLOGY_GATE_JSON,
            "diffusion_repo": DEFAULT_DIFFUSION_REPO,
            "reward_config": DEFAULT_REWARD_CONFIG,
            "seed": 2,
            "max_npcs": 4,
            "formal_seed": False,
            "formal_seeds_frozen": list(FORMAL_SEEDS),
            "expected_snapshot_count": DEFAULT_EXPECTED_SNAPSHOT_COUNT,
        },
        "candidate_config": {
            "generator_policy": PLANNED_POLICY,
            "default_off_remediation_profile": REMEDIATION_PROFILE,
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "prefix_steps": [1],
            "bridge_steps": [0],
            "lane_projected_offset_scales": [0.0],
            "max_deceleration_mps2": 3.0,
            "jerk_progress_max_jerk_mps3": 8.0,
            "min_progress_ratio": 0.8,
            "command_jerk_worse_budget_mps3": 0.0,
            "rollout_jerk_worse_budget_mps3": 0.0,
            "rollout_lateral_worse_budget_mps2": 0.0,
            "max_remediation_candidates": DEFAULT_MAX_REMEDIATION_CANDIDATES,
        },
        "execution_artifacts": {
            "output_root": str(execution_root),
            "runbook": str(execution_root / "guarded_material_v4_runbook.sh"),
            "json": str(execution_root / "default_off_v4_fixed_snapshot_screen.json"),
            "markdown": str(execution_root / "default_off_v4_fixed_snapshot_screen.md"),
            "log": str(execution_root / "CANDIDATE_SCREEN.log"),
            "stderr": str(execution_root / "CANDIDATE_SCREEN.err"),
            "sha256sums": str(execution_root / "SHA256SUMS"),
        },
        "accept_criteria": [
            "runbook refuses to execute without the v4 guard environment variable",
            "CAMP HEAD equals origin/main and DP HEAD equals the fixed commit",
            "snapshot count equals the predeclared nonformal fixed-snapshot count",
            "outputs include JSON, Markdown, stdout/stderr logs, HEADS, and SHA256SUMS",
            "screen result must be treated as diagnostic evidence only",
        ],
        "blocked_boundaries": [
            "this plan gate does not execute candidate generation or the screen",
            "formal seeds 11/12/13 remain frozen and unused",
            "replay, closed-loop smoke, and Full36 are not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation remain fixed",
            "no safety-benefit claim or CAMP-over-DP Top-1 claim is authorized",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / POST_REVIEW_JSON
    md_path = root / POST_REVIEW_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": json_path.is_file(),
        "md_exists": md_path.is_file(),
        "json_sha256": _sha256(json_path),
        "md_sha256": _sha256(md_path),
        "payload": _read_json(json_path),
        "markdown_text": _read_text(md_path),
    }


def _post_review_summary(payload: dict[str, Any], markdown_text: str) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "fixed_snapshot_screen_rerun_plan_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_plan_authorized")
        ),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "markdown_records_next_gate": "fixed-snapshot screen rerun plan" in markdown_text.lower()
        or POST_REVIEW_AUTHORIZED_NEXT_WORK in markdown_text,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("post_review_root_exists", artifact["exists"]),
        _check("post_review_json_exists", artifact["json_exists"]),
        _check("post_review_md_exists", artifact["md_exists"]),
        _check("post_review_json_parseable", bool(artifact["payload"])),
        _check("post_review_markdown_readable", bool(artifact["markdown_text"])),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("formal_seeds_frozen_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("post_review_status_ready", source["status"] == POST_REVIEW_READY_STATUS),
        _check("post_review_passed", source["passed"]),
        _check(
            "post_review_authorizes_this_plan",
            source["authorized_next_work"] == POST_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check(
            "post_review_plan_authorized",
            source["fixed_snapshot_screen_rerun_plan_authorized"],
        ),
        _check("post_review_no_blocked_actions", not source["blocked_authorizations"]),
        _check("post_review_markdown_records_next_gate", source["markdown_records_next_gate"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scope = plan["snapshot_scope"]
    config = plan["candidate_config"]
    return [
        _check("plan_selects_guarded_rerun_next", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_uses_nonformal_seed2", scope["seed"] == 2 and not scope["formal_seed"]),
        _check("plan_freezes_formal_seeds", scope["formal_seeds_frozen"] == [11, 12, 13]),
        _check("plan_expected_snapshot_count", scope["expected_snapshot_count"] == 57),
        _check("plan_uses_v4_policy", config["generator_policy"] == PLANNED_POLICY),
        _check("plan_uses_v4_profile", config["default_off_remediation_profile"] == REMEDIATION_PROFILE),
        _check("plan_preserves_zero_comfort_budgets", config["command_jerk_worse_budget_mps3"] == 0.0 and config["rollout_jerk_worse_budget_mps3"] == 0.0 and config["rollout_lateral_worse_budget_mps2"] == 0.0),
    ]


def _runbook_checks(runbook_text: str) -> list[dict[str, Any]]:
    lowered = runbook_text.lower()
    return [
        _check("runbook_guarded", GUARD_ENV_VAR in runbook_text and '!= "yes"' in runbook_text),
        _check("runbook_uses_fixed_python", DEFAULT_REMOTE_PYTHON in runbook_text),
        _check("runbook_uses_v4_policy", f"--generator_policy {PLANNED_POLICY}" in runbook_text),
        _check("runbook_uses_v4_profile", f"--default_off_remediation_profile {REMEDIATION_PROFILE}" in runbook_text),
        _check("runbook_checks_dp_head", EXPECTED_DP_HEAD in runbook_text),
        _check("runbook_writes_hashes", "SHA256SUMS" in runbook_text),
        _check("runbook_no_git_pull", "git pull" not in lowered),
        _check("runbook_no_git_checkout", "git checkout" not in lowered),
        _check("runbook_no_replay", "replay" not in lowered),
        _check("runbook_no_training", "train" not in lowered),
        _check("runbook_no_formal_seeds", "seed=11" not in lowered and "seed=12" not in lowered and "seed=13" not in lowered),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    return [_check(f"blocked_action.{key}", True) for key in BLOCKED_ACTIONS]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "fixed_snapshot_screen_rerun_plan_complete": passed,
        "guarded_fixed_snapshot_screen_rerun_next_gate_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key not in {"payload", "markdown_text"}}


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
