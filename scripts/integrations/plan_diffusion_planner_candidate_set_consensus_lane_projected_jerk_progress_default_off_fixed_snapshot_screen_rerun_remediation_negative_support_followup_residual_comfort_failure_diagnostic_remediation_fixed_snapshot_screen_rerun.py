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
    FORMAL_SEEDS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_post_implementation_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as POST_REVIEW_AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
    READY_STATUS as POST_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_fixed_snapshot_screen_"
    "rerun_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_fixed_snapshot_screen_"
    "rerun_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_guarded_fixed_snapshot_"
    "screen_rerun_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_POST_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_post_implementation_static_contract_review_bff8f8b"
)
DEFAULT_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_fixed_snapshot_screen_rerun_bff8f8b"
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

POST_REVIEW_JSON = "post_implementation_static_review.json"
POST_REVIEW_MD = "post_implementation_static_review.md"

GUARD_ENV_VAR = (
    "CANDIDATE_SET_CONSENSUS_RESIDUAL_COMFORT_REMEDIATION_"
    "FIXED_SNAPSHOT_RERUN_APPROVED"
)
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
        description=(
            "Plan-only guarded fixed-snapshot screen rerun after the residual "
            "comfort remediation post-implementation static review."
        )
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
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(post_review_root)
    source = _post_review_summary(artifact["payload"])
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
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_fixed_snapshot_screen_rerun_plan_v1"
            ),
            "label": label,
            "role": "plan-only guarded fixed-snapshot screen rerun contract",
            "plan_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan writes only a future guarded screen-rerun runbook. "
                "It does not execute candidate generation, rerun the screen, "
                "run replay, use formal seeds, define or promote runtime "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, or claim a "
                "DP-side classical Benders decomposition."
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
        "# Residual Comfort Remediation Fixed-Snapshot Screen Rerun Plan",
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
  --red_stop_margin_m 2.0 \\
  --red_stop_margin_m 4.0 \\
  --red_stop_margin_m 6.0 \\
  --backup_stop_offset_m 0.0 \\
  --backup_stop_offset_m 1.0 \\
  --lane_projected_offset_scale 1.0 \\
  --lane_projected_offset_scale 0.5 \\
  --lane_projected_offset_scale 0.0 \\
  --max_deceleration_mps2 {config['max_deceleration_mps2']} \\
  --jerk_progress_max_jerk_mps3 {config['jerk_progress_max_jerk_mps3']} \\
  --min_snapshot_support_rate {config['min_snapshot_support_rate']} \\
  --max_remediation_candidates {config['max_remediation_candidates']} \\
  --label residual_comfort_remediation_fixed_snapshot_screen \\
  --output_json "{plan['execution_artifacts']['screen_json']}" \\
  --output_md "{plan['execution_artifacts']['screen_md']}" \\
  > "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.log" \\
  2> "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.err"

printf '0\\n' > "${{OUTPUT_ROOT}}/EXIT_CODE"
cd "${{OUTPUT_ROOT}}"
sha256sum \\
  residual_comfort_remediation_fixed_snapshot_screen.json \\
  residual_comfort_remediation_fixed_snapshot_screen.md \\
  CANDIDATE_SCREEN.log CANDIDATE_SCREEN.err EXIT_CODE HEADS.txt > SHA256SUMS
"""


def _screen_rerun_plan(execution_root: Path) -> dict[str, Any]:
    root = execution_root.as_posix()
    return {
        "selection_type": "residual_comfort_remediation_fixed_snapshot_screen_rerun_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "snapshot_scope": {
            "scope_type": "single_existing_nonformal_fixed_snapshot_corpus",
            "snapshot_dir": DEFAULT_SNAPSHOT_DIR,
            "route_topology_gate_json": DEFAULT_ROUTE_TOPOLOGY_GATE_JSON,
            "diffusion_repo": DEFAULT_DIFFUSION_REPO,
            "reward_config": DEFAULT_REWARD_CONFIG,
            "expected_snapshot_count": DEFAULT_EXPECTED_SNAPSHOT_COUNT,
            "seed": 2,
            "formal_seed": False,
            "formal_seeds_frozen": sorted(FORMAL_SEEDS),
        },
        "candidate_config": {
            "generator_policy": PLANNED_POLICY,
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "lane_projected_offset_scales": [1.0, 0.5, 0.0],
            "max_deceleration_mps2": 3.0,
            "jerk_progress_max_jerk_mps3": 8.0,
            "min_snapshot_support_rate": 0.25,
            "max_remediation_candidates": DEFAULT_MAX_REMEDIATION_CANDIDATES,
        },
        "execution_artifacts": {
            "output_root": root,
            "screen_json": f"{root}/residual_comfort_remediation_fixed_snapshot_screen.json",
            "screen_md": f"{root}/residual_comfort_remediation_fixed_snapshot_screen.md",
            "heads": f"{root}/HEADS.txt",
            "sha256sums": f"{root}/SHA256SUMS",
            "runbook": f"{root}/fixed_snapshot_screen_rerun_guarded_runbook.sh",
        },
        "accept_criteria": [
            "plan artifact and guarded runbook are complete",
            "all planned inputs are explicit and bounded",
            "future guarded rerun must fail closed on CAMP/DP head mismatch",
            "future guarded rerun must fail closed on snapshot-count mismatch",
            "future guarded rerun may only evaluate the fixed current-tick candidate screen",
            "future guarded rerun evidence must not claim safety benefit or CAMP-over-DP Top-1 superiority",
        ],
        "blocked_boundaries": [
            "candidate generation execution is not authorized in this plan gate",
            "fixed-snapshot screen rerun is not authorized in this plan gate",
            "replay is not authorized",
            "formal seeds 11/12/13 remain frozen",
            "Full36 is not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim, CAMP-over-DP-Top-1 claim, or classical Benders claim is authorized",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / POST_REVIEW_JSON
    markdown_path = root / POST_REVIEW_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _post_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "fixed_snapshot_screen_rerun_plan_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_plan_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("post_review_root_exists", artifact["exists"]),
        _check("post_review_json_exists", artifact["json_exists"]),
        _check("post_review_markdown_exists", artifact["markdown_exists"]),
        _check("post_review_json_parseable", bool(artifact["payload"])),
        _check(
            "post_review_markdown_records_authorized_next_work",
            "Authorized next work" in artifact["markdown_text"],
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("post_review_status_complete", source["status"] == POST_REVIEW_READY_STATUS),
        _check("post_review_passed", source["passed"] is True),
        _check("post_review_failed_checks_empty", not source["failed_checks"]),
        _check("post_review_authorizes_this_plan", source["authorized_next_work"] == POST_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("post_review_plan_authorized", source["fixed_snapshot_screen_rerun_plan_authorized"] is True),
        _check("post_review_no_blocked_actions", not source["blocked_action_conflicts"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scope = plan["snapshot_scope"]
    config = plan["candidate_config"]
    text = json.dumps(plan, sort_keys=True)
    return [
        _check("plan_selected_next_work", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_is_guarded", plan["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT),
        _check("plan_nonformal_seed", int(scope["seed"]) not in FORMAL_SEEDS and scope["formal_seed"] is False),
        _check("plan_expected_snapshot_count", scope["expected_snapshot_count"] == DEFAULT_EXPECTED_SNAPSHOT_COUNT),
        _check("plan_fixed_dp_repo", scope["diffusion_repo"] == DEFAULT_DIFFUSION_REPO),
        _check("plan_uses_residual_remediation_policy", config["generator_policy"] == PLANNED_POLICY),
        _check("plan_pins_remediation_candidate_cap", config["max_remediation_candidates"] == DEFAULT_MAX_REMEDIATION_CANDIDATES),
        _check("plan_output_under_development_root", str(plan["execution_artifacts"]["output_root"]).startswith(DEFAULT_DEVELOPMENT_ROOT)),
        _check("plan_records_current_tick_contract", "current-tick" in text),
    ]


def _runbook_checks(runbook_text: str) -> list[dict[str, Any]]:
    lower = runbook_text.lower()
    return [
        _check("runbook_has_guard", GUARD_ENV_VAR in runbook_text and '!= "yes"' in runbook_text),
        _check("runbook_uses_python312", DEFAULT_REMOTE_PYTHON in runbook_text),
        _check("runbook_uses_residual_remediation_policy", f"--generator_policy {PLANNED_POLICY}" in runbook_text),
        _check("runbook_pins_remediation_candidate_cap", f"--max_remediation_candidates {DEFAULT_MAX_REMEDIATION_CANDIDATES}" in runbook_text),
        _check("runbook_has_snapshot_screen_command", "analyze_diffusion_planner_route_topology_candidate_screen.py" in runbook_text),
        _check("runbook_checks_dp_head", EXPECTED_DP_HEAD in runbook_text),
        _check("runbook_checks_snapshot_count", "SNAPSHOT_COUNT" in runbook_text),
        _check("runbook_records_sha256sums", "sha256sum" in runbook_text and "SHA256SUMS" in runbook_text),
        _check("runbook_does_not_run_replay", "replay" not in lower),
        _check("runbook_does_not_modify_git", "git pull" not in lower and "git checkout" not in lower),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_guarded_next_gate", decision["guarded_fixed_snapshot_screen_rerun_next_gate_authorized"] is True),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_safety_claims", decision["safety_benefit_claim_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "guard_env_var": GUARD_ENV_ASSIGNMENT if passed else None,
        "fixed_snapshot_screen_rerun_plan_complete": passed,
        "guarded_fixed_snapshot_screen_rerun_next_gate_authorized": passed,
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
        if key not in {"payload", "markdown_text"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
