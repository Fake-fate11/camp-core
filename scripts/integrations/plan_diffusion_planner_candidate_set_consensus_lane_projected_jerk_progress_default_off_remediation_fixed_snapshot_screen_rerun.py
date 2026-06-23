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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (  # noqa: E402
    EXIT_CODE,
    HEADS,
    SHA256SUMS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_fixed_snapshot_screen_rerun_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_fixed_snapshot_screen_rerun_plan_rejected"
)
SOURCE_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_post_implementation_static_contract_review_complete"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_fixed_snapshot_screen_rerun_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_guarded_fixed_snapshot_screen_rerun_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_post_implementation_static_"
    "contract_review_562baba"
)
DEFAULT_PLANNED_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun"
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
DEFAULT_ASSET_ROOT = "/root/autodl-tmp/camp_dp_assets"

SOURCE_JSON = "post_implementation_static_contract_review.json"
SOURCE_MD = "post_implementation_static_contract_review.md"

GUARD_ENV_VAR = (
    "CANDIDATE_SET_CONSENSUS_LANE_PROJECTED_JERK_PROGRESS_"
    "DEFAULT_OFF_REMEDIATION_FIXED_SNAPSHOT_RERUN_APPROVED"
)
GUARD_ENV_ASSIGNMENT = f"{GUARD_ENV_VAR}=yes"
POLICY_NAME = "lane_projected_jerk_progress_red_stop"
DEFAULT_POLICY_NAME = "lane_centerline_red_stop"

BLOCKED_ACTIONS = (
    "implementation_code_edit_authorized",
    "production_implementation_edit_authorized",
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
    "safety_benefit_evidence",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for the default-off remediation fixed-snapshot "
            "screen rerun. It validates the post-implementation static review "
            "artifact and writes a guarded future runbook; it does not execute "
            "the fixed-snapshot rerun."
        )
    )
    parser.add_argument("--review_root", type=Path, default=Path(DEFAULT_REVIEW_ROOT))
    parser.add_argument(
        "--planned_execution_root",
        type=Path,
        default=Path(DEFAULT_PLANNED_EXECUTION_ROOT),
    )
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
        review_root=args.review_root,
        planned_execution_root=args.planned_execution_root,
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
    review_root: Path,
    planned_execution_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(review_root)
    source = _source_summary(artifact.get("json_payload") or {})
    plan = _rerun_plan(source, planned_execution_root)
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
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_plan_v1"
            ),
            "label": label,
            "role": "fixed-snapshot rerun plan-only gate",
            "plan_only": True,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_candidate_generation": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This gate reads only the static review artifact and current "
                "heads, then writes a guarded future fixed-snapshot rerun "
                "contract. It does not execute candidate generation, rerun the "
                "screen, run replay, use formal seeds, define runtime atoms, "
                "choose lambda online, alter score_k(w)=a_k^T w, mutate the "
                "convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, modify DP weights or code, or claim a DP-side "
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
        "fixed_snapshot_rerun_plan": plan,
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
    plan = report["fixed_snapshot_rerun_plan"]
    lines = [
        "# Lane-Projected Jerk/Progress Default-Off Remediation Fixed-Snapshot Screen Rerun Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next gate: `{decision['authorized_next_work']}`",
        f"- Next gate requires user authorization: `{decision['next_gate_requires_user_authorization']}`",
        f"- Guard env: `{report['runbook']['guard_env_assignment']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Route/Seed Matrix",
        "",
        "| Run | Route | Seed | NPCs | Traffic lights | Buckets | Included in rerun |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in plan["route_seed_matrix"]:
        buckets = ",".join(row["scenario_buckets"])
        lines.append(
            f"| `{row['run_id']}` | `{row['route_name']}` | `{row['seed']}` | "
            f"`{row['max_npcs']}` | `{row['traffic_lights']}` | "
            f"`{buckets}` | `{row['included_in_guarded_rerun']}` |"
        )
    lines.extend(["", "## Assets", ""])
    for key, value in plan["assets"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Gates", ""])
    for name, gate in plan["gates"].items():
        lines.append(f"- `{name}`: `{gate['status']}` - {gate['contract']}")
    lines.extend(["", "## Diagnostics", ""])
    for name, values in plan["diagnostics"].items():
        lines.append(f"- `{name}`: `{values}`")
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
            "## Safety-Score Evaluation Boundary",
            "",
            f"- `{plan['safety_score_evaluation_boundary']}`",
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
    corpus = plan["fixed_snapshot_corpus"]
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
            'PY="${PY:-/root/miniconda3/envs/camp/bin/python}"',
            f'OUT="{output_root}"',
            f'SNAPSHOT_DIR="{corpus["snapshot_dir"]}"',
            f'ROUTE_TOPOLOGY_GATE_JSON="{corpus["route_topology_gate_json"]}"',
            f'REWARD_CONFIG="{corpus["reward_config"]}"',
            f'DIFFUSION_REPO="{corpus["diffusion_repo"]}"',
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
            f'test "$SNAPSHOT_COUNT" = "{corpus["expected_snapshot_count"]}"',
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
            "  --label lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_rerun \\",
            '  --output_json "$OUT/route_topology_default_off_remediation_rerun_screen.json" \\',
            '  --output_md "$OUT/route_topology_default_off_remediation_rerun_screen.md" \\',
            '  > "$OUT/CANDIDATE_SCREEN.log" 2> "$OUT/CANDIDATE_SCREEN.err"',
            "",
            "$PY scripts/integrations/analyze_diffusion_planner_route_topology_absolute_comfort_guard.py \\",
            '  --screen_json "$OUT/route_topology_default_off_remediation_rerun_screen.json" \\',
            '  --snapshot_dir "$SNAPSHOT_DIR" \\',
            '  --reward_config "$REWARD_CONFIG" \\',
            "  --label lane_projected_jerk_progress_default_off_remediation_absolute_lateral_guard \\",
            '  --output_json "$OUT/route_topology_default_off_remediation_absolute_lateral_guard.json" \\',
            '  --output_md "$OUT/route_topology_default_off_remediation_absolute_lateral_guard.md" \\',
            '  > "$OUT/ABSOLUTE_GUARD.log" 2> "$OUT/ABSOLUTE_GUARD.err"',
            "",
            "printf '0\\n' > \"$OUT/EXIT_CODE\"",
            "cd \"$OUT\"",
            "sha256sum \\",
            "  route_topology_default_off_remediation_rerun_screen.json \\",
            "  route_topology_default_off_remediation_rerun_screen.md \\",
            "  route_topology_default_off_remediation_absolute_lateral_guard.json \\",
            "  route_topology_default_off_remediation_absolute_lateral_guard.md \\",
            "  CANDIDATE_SCREEN.log CANDIDATE_SCREEN.err \\",
            "  ABSOLUTE_GUARD.log ABSOLUTE_GUARD.err \\",
            "  EXIT_CODE HEADS.txt > SHA256SUMS",
            "",
        ]
    )


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        SOURCE_JSON,
        SOURCE_MD,
        HEADS,
        "PY_COMPILE.log",
        "PY_COMPILE.err",
        "PYTEST_REVIEW.log",
        "PYTEST_REVIEW.err",
        "PYTEST_RELATED.log",
        "PYTEST_RELATED.err",
        "REVIEW_COMMAND.log",
        "REVIEW_COMMAND.err",
        EXIT_CODE,
        SHA256SUMS,
    )
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[SOURCE_JSON].is_file():
        loaded = _load_json(files[SOURCE_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
    exit_text = _read_text(root / EXIT_CODE)
    heads_text = _read_text(root / HEADS)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads_text,
        "exit_text": exit_text,
        "py_compile_exit_ok": _exit_flag(exit_text, "PY_COMPILE_EXIT", "0"),
        "pytest_review_exit_ok": _exit_flag(exit_text, "PYTEST_REVIEW_EXIT", "0"),
        "pytest_related_exit_ok": _exit_flag(exit_text, "PYTEST_RELATED_EXIT", "0"),
        "review_command_exit_ok": _exit_flag(exit_text, "REVIEW_EXIT", "0"),
        "py_compile_err_bytes": _file_size(root / "PY_COMPILE.err"),
        "pytest_review_err_bytes": _file_size(root / "PYTEST_REVIEW.err"),
        "pytest_related_err_bytes": _file_size(root / "PYTEST_RELATED.err"),
        "review_command_err_bytes": _file_size(root / "REVIEW_COMMAND.err"),
        "json_payload": payload,
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_next_work": decision.get("selected_next_work"),
        "post_implementation_static_contract_review_complete": bool(
            decision.get("post_implementation_static_contract_review_complete")
        ),
        "fixed_snapshot_screen_rerun_plan_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_plan_authorized")
        ),
        "fixed_snapshot_screen_rerun_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _rerun_plan(source: dict[str, Any], execution_root: Path) -> dict[str, Any]:
    matrix = _route_seed_matrix()
    coverage = sorted(
        {
            bucket
            for row in matrix
            for bucket in row["scenario_buckets"]
            if isinstance(bucket, str)
        }
    )
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "guarded_fixed_snapshot_screen_rerun_plan_only",
        "next_gate_requires_user_authorization": True,
        "guard_env_var": GUARD_ENV_VAR,
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "assets": _assets(),
        "route_seed_matrix": matrix,
        "coverage_summary": {
            "scenario_buckets_declared": coverage,
            "traffic_light_covered": "traffic_light" in coverage,
            "turn_covered": "turn" in coverage,
            "normal_covered": "normal" in coverage,
            "nishishinjuku_assets_declared": any(
                str(row["route_name"]).startswith("nishishinjuku") for row in matrix
            ),
            "included_guarded_rerun_count": sum(
                1 for row in matrix if row["included_in_guarded_rerun"]
            ),
            "asset_boundary_rows": sum(
                1 for row in matrix if not row["included_in_guarded_rerun"]
            ),
        },
        "fixed_snapshot_corpus": {
            "scope_type": "single_existing_nonformal_fixed_snapshot_corpus",
            "source_root": DEFAULT_SNAPSHOT_ROOT,
            "snapshot_dir": DEFAULT_SNAPSHOT_DIR,
            "expected_snapshot_count": DEFAULT_EXPECTED_SNAPSHOT_COUNT,
            "route_name": "sample_map_tl_route_59_to_86",
            "seed": 2,
            "max_npcs": 4,
            "traffic_lights": "on",
            "scenario_buckets": ["traffic_light", "turn"],
            "formal_seeds_frozen": sorted(FORMAL_SEEDS),
            "route_topology_gate_json": DEFAULT_ROUTE_TOPOLOGY_GATE_JSON,
            "reward_config": DEFAULT_REWARD_CONFIG,
            "diffusion_repo": DEFAULT_DIFFUSION_REPO,
        },
        "candidate_config": {
            "default_policy_preserved": DEFAULT_POLICY_NAME,
            "generator_policy": POLICY_NAME,
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "lane_projected_offset_scales": [1.0, 0.5, 0.0],
            "max_deceleration_mps2": 3.0,
            "jerk_progress_max_jerk_mps3": 8.0,
            "min_snapshot_support_rate": 0.25,
            "candidate_build_p95_latency_ms": 10.0,
            "total_p95_latency_ms": 100.0,
        },
        "gates": {
            "selector_equivalence": {
                "status": "predeclared",
                "contract": (
                    "default-off selector behavior must remain equivalent; "
                    "rerun artifacts must not alter online selector inputs, "
                    "weights, fallback, or selected index outside explicit "
                    "fixed-snapshot diagnostics"
                ),
            },
            "payload_no_leak_default_off": {
                "status": "predeclared",
                "contract": (
                    "candidate_construction_diagnostics stay snapshot-level "
                    "report payloads; generated_scores and outcome labels are "
                    "not emitted to candidate rows; default policy remains "
                    f"{DEFAULT_POLICY_NAME}"
                ),
            },
            "latency": {
                "status": "predeclared",
                "contract": "candidate-build p95 <= 10 ms and total p95 <= 100 ms",
            },
            "fallback_progress_comfort": {
                "status": "predeclared",
                "contract": (
                    "fallback, hard feasibility, progress feasibility, "
                    "PerfectTracker comfort, and absolute lateral guard rates "
                    "are reported without promotion"
                ),
            },
        },
        "diagnostics": {
            "spread": [
                "candidate_count",
                "finite_candidate_rows",
                "hard_feasible_support_rate",
                "progress_feasible_support_rate",
                "comfort_admissible_support_rate",
            ],
            "rank": [
                "selected_index",
                "red_stop_margin_rank",
                "lane_projected_offset_scale_rank",
                "fallback_reason_counts",
            ],
            "sensitivity": [
                "red_stop_margin_m grid",
                "backup_stop_offset_m grid",
                "lane_projected_offset_scale grid",
                "jerk_progress_max_jerk_mps3",
            ],
        },
        "execution_artifacts": {
            "output_root": str(execution_root),
            "screen_json": (
                f"{execution_root}/route_topology_default_off_"
                "remediation_rerun_screen.json"
            ),
            "absolute_lateral_guard_json": (
                f"{execution_root}/route_topology_default_off_remediation_"
                "absolute_lateral_guard.json"
            ),
            "required_files": [
                "route_topology_default_off_remediation_rerun_screen.json",
                "route_topology_default_off_remediation_rerun_screen.md",
                "route_topology_default_off_remediation_absolute_lateral_guard.json",
                "route_topology_default_off_remediation_absolute_lateral_guard.md",
                "CANDIDATE_SCREEN.log",
                "CANDIDATE_SCREEN.err",
                "ABSOLUTE_GUARD.log",
                "ABSOLUTE_GUARD.err",
                "EXIT_CODE",
                "HEADS.txt",
                "SHA256SUMS",
            ],
        },
        "artifact_recording": {
            "plan_outputs": [
                "fixed_snapshot_screen_rerun_plan.json",
                "fixed_snapshot_screen_rerun_plan.md",
                "fixed_snapshot_screen_rerun_guarded_runbook.sh",
                "HEADS.txt",
                "SHA256SUMS",
                "EXIT_CODE",
            ],
            "future_execution_outputs": [
                "HEADS.txt",
                "CANDIDATE_SCREEN.log",
                "CANDIDATE_SCREEN.err",
                "ABSOLUTE_GUARD.log",
                "ABSOLUTE_GUARD.err",
                "EXIT_CODE",
                "SHA256SUMS",
            ],
        },
        "accept_criteria": [
            "source review artifact status is complete and authorizes only this plan gate",
            "local, origin/main, GitHub, and AutoDL CAMP heads are equal before any execution gate",
            f"DP HEAD remains {EXPECTED_DP_HEAD}",
            "runbook refuses to run without the explicit guard environment variable",
            "fixed snapshot corpus is the existing nonformal seed2 NPC4 traffic-light corpus",
            "route/seed matrix declares traffic-light, turn, normal, sample-map, and nishishinjuku coverage boundaries",
            "selector-equivalence and payload no-leak/default-off gates are predeclared",
            "latency, fallback, progress, comfort, spread, rank, and sensitivity diagnostics are predeclared",
            "plan artifact records JSON, markdown, runbook, HEADS, EXIT_CODE, and SHA256SUMS",
        ],
        "reject_criteria": [
            "missing source review artifact, HEADS, logs, exit code, or SHA256SUMS",
            "source review does not authorize the fixed-snapshot rerun plan-only gate",
            "CAMP HEAD differs from origin/main",
            f"DP HEAD differs from {EXPECTED_DP_HEAD}",
            "formal seeds appear in the route/seed matrix or future runbook",
            "runbook lacks the explicit guard or attempts git pull",
            "plan authorizes execution, replay, Full36, training, online selector changes, atom promotion, safety claims, or DP modification",
            "traffic-light, turn, normal, sample-map, or nishishinjuku coverage boundaries are absent",
        ],
        "safety_score_evaluation_boundary": {
            "uses_closed_loop_outcomes": False,
            "claims_safety_benefit": False,
            "claims_camp_over_dp_top1": False,
            "allowed": (
                "fixed-snapshot diagnostic scores and PerfectTracker comfort "
                "summaries may be recorded only as screen evidence; they are "
                "not safety-benefit evidence and do not authorize promotion"
            ),
        },
        "blocked_boundaries": [
            "this gate is plan-only and does not execute the fixed-snapshot screen rerun",
            "candidate generation execution is not authorized in this gate",
            "replay is not authorized",
            "Full36 is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "CAMP retraining is not authorized",
            "atom promotion or online selector change is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
            "the next execution gate requires separate user authorization",
        ],
        "source_contract": {
            "status": source["status"],
            "selected_next_work": source["selected_next_work"],
            "fixed_snapshot_screen_rerun_plan_authorized": source[
                "fixed_snapshot_screen_rerun_plan_authorized"
            ],
            "fixed_snapshot_screen_rerun_authorized": source[
                "fixed_snapshot_screen_rerun_authorized"
            ],
        },
    }


def _route_seed_matrix() -> list[dict[str, Any]]:
    return [
        {
            "run_id": "fixed_snapshot_sample_tl_turn_seed2_npc4_tlon",
            "map_name": "sample_map",
            "route_name": "sample_map_tl_route_59_to_86",
            "route_asset": f"{DEFAULT_ASSET_ROOT}/sample_map_tl_route_59_to_86.pkl",
            "seed": 2,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": "on",
            "scenario_buckets": ["traffic_light", "turn"],
            "fixed_snapshot_dir": DEFAULT_SNAPSHOT_DIR,
            "expected_snapshot_count": DEFAULT_EXPECTED_SNAPSHOT_COUNT,
            "included_in_guarded_rerun": True,
            "boundary": "existing fixed snapshot corpus",
        },
        {
            "run_id": "asset_boundary_sample_normal_seed1_npc0_tloff",
            "map_name": "sample_map",
            "route_name": "sample_map_route_2_to_104",
            "route_asset": f"{DEFAULT_ASSET_ROOT}/sample_map_route_2_to_104.pkl",
            "seed": 1,
            "max_npcs": 0,
            "spawn_probability": 0.0,
            "traffic_lights": "off",
            "scenario_buckets": ["normal"],
            "fixed_snapshot_dir": None,
            "expected_snapshot_count": None,
            "included_in_guarded_rerun": False,
            "boundary": "asset declared only; no candidate generation in plan gate",
        },
        {
            "run_id": "asset_boundary_nishishinjuku_release_seed2_npc4_tlon",
            "map_name": "nishishinjuku",
            "route_name": "nishishinjuku_release_auto_route",
            "route_asset": f"{DEFAULT_ASSET_ROOT}/nishishinjuku_release_auto_route.pkl",
            "seed": 2,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": "on",
            "scenario_buckets": ["traffic_light"],
            "fixed_snapshot_dir": None,
            "expected_snapshot_count": None,
            "included_in_guarded_rerun": False,
            "boundary": "asset declared only; no candidate generation in plan gate",
        },
        {
            "run_id": "asset_boundary_nishishinjuku_lane_change_seed1_npc4_tloff",
            "map_name": "nishishinjuku",
            "route_name": "nishishinjuku_lane_change_route_7_via_8_to_1",
            "route_asset": (
                f"{DEFAULT_ASSET_ROOT}/"
                "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
            ),
            "seed": 1,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": "off",
            "scenario_buckets": ["turn"],
            "fixed_snapshot_dir": None,
            "expected_snapshot_count": None,
            "included_in_guarded_rerun": False,
            "boundary": "asset declared only; no candidate generation in plan gate",
        },
    ]


def _assets() -> dict[str, str]:
    return {
        "sample_map_tl_route_59_to_86": (
            f"{DEFAULT_ASSET_ROOT}/sample_map_tl_route_59_to_86.pkl"
        ),
        "sample_map_route_2_to_104": (
            f"{DEFAULT_ASSET_ROOT}/sample_map_route_2_to_104.pkl"
        ),
        "nishishinjuku_release_auto_route": (
            f"{DEFAULT_ASSET_ROOT}/nishishinjuku_release_auto_route.pkl"
        ),
        "nishishinjuku_lane_change_route_7_via_8_to_1": (
            f"{DEFAULT_ASSET_ROOT}/nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
        ),
        "nishishinjuku_no_ros_map": f"{DEFAULT_ASSET_ROOT}/nishishinjuku_no_ros.osm",
        "nishishinjuku_autoware_no_ros_map": (
            f"{DEFAULT_ASSET_ROOT}/nishishinjuku_autoware_map/"
            "nishishinjuku_autoware_map/lanelet2_map_no_ros.osm"
        ),
        "fixed_snapshot_corpus": DEFAULT_SNAPSHOT_DIR,
        "route_topology_gate_json": DEFAULT_ROUTE_TOPOLOGY_GATE_JSON,
        "reward_config": DEFAULT_REWARD_CONFIG,
        "diffusion_repo": DEFAULT_DIFFUSION_REPO,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    expected_files = {key: True for key in artifact["required_files_present"]}
    return [
        _check_equal("review_artifact_exists", artifact["exists"], True),
        _check_equal(
            "review_required_files_present",
            artifact["required_files_present"],
            expected_files,
        ),
        _check_equal("review_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("review_py_compile_exit_ok", artifact["py_compile_exit_ok"], True),
        _check_equal("review_pytest_review_exit_ok", artifact["pytest_review_exit_ok"], True),
        _check_equal("review_pytest_related_exit_ok", artifact["pytest_related_exit_ok"], True),
        _check_equal("review_command_exit_ok", artifact["review_command_exit_ok"], True),
        _check_equal("review_py_compile_err_empty", artifact["py_compile_err_bytes"], 0),
        _check_equal("review_pytest_review_err_empty", artifact["pytest_review_err_bytes"], 0),
        _check_equal("review_pytest_related_err_empty", artifact["pytest_related_err_bytes"], 0),
        _check_equal("review_command_err_empty", artifact["review_command_err_bytes"], 0),
        _check_equal(
            "review_heads_present",
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
            "source_authorizes_rerun_plan",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "source_selected_next_work",
            source["selected_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "source_static_review_complete",
            source["post_implementation_static_contract_review_complete"],
            True,
        ),
        _check_equal(
            "source_rerun_plan_authorized",
            source["fixed_snapshot_screen_rerun_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_rerun_execution_not_authorized",
            source["fixed_snapshot_screen_rerun_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = {int(row["seed"]) for row in plan["route_seed_matrix"]}
    route_names = {str(row["route_name"]) for row in plan["route_seed_matrix"]}
    coverage = set(plan["coverage_summary"]["scenario_buckets_declared"])
    config = plan["candidate_config"]
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "guarded_fixed_snapshot_screen_rerun_plan_only",
        ),
        _check_equal(
            "plan_next_gate_requires_user_authorization",
            plan["next_gate_requires_user_authorization"],
            True,
        ),
        _check_equal("plan_guard_assignment", plan["guard_env_assignment"], GUARD_ENV_ASSIGNMENT),
        _check_equal("plan_no_formal_seeds", bool(seeds & set(FORMAL_SEEDS)), False),
        _check_equal("plan_traffic_light_covered", "traffic_light" in coverage, True),
        _check_equal("plan_turn_covered", "turn" in coverage, True),
        _check_equal("plan_normal_covered", "normal" in coverage, True),
        _check_equal(
            "plan_sample_map_assets_declared",
            {
                "sample_map_tl_route_59_to_86",
                "sample_map_route_2_to_104",
            }.issubset(route_names),
            True,
        ),
        _check_equal(
            "plan_nishishinjuku_assets_declared",
            plan["coverage_summary"]["nishishinjuku_assets_declared"],
            True,
        ),
        _check_equal(
            "plan_single_existing_fixed_corpus_rerun",
            plan["coverage_summary"]["included_guarded_rerun_count"],
            1,
        ),
        _check_equal(
            "plan_expected_snapshot_count",
            plan["fixed_snapshot_corpus"]["expected_snapshot_count"],
            DEFAULT_EXPECTED_SNAPSHOT_COUNT,
        ),
        _check_equal("plan_default_policy_preserved", config["default_policy_preserved"], DEFAULT_POLICY_NAME),
        _check_equal("plan_explicit_generator_policy", config["generator_policy"], POLICY_NAME),
        _check_equal("plan_latency_candidate_p95", config["candidate_build_p95_latency_ms"], 10.0),
        _check_equal("plan_latency_total_p95", config["total_p95_latency_ms"], 100.0),
        _check_equal("plan_selector_gate_declared", "selector_equivalence" in plan["gates"], True),
        _check_equal("plan_payload_no_leak_gate_declared", "payload_no_leak_default_off" in plan["gates"], True),
        _check_equal("plan_spread_diagnostics_declared", bool(plan["diagnostics"]["spread"]), True),
        _check_equal("plan_rank_diagnostics_declared", bool(plan["diagnostics"]["rank"]), True),
        _check_equal("plan_sensitivity_diagnostics_declared", bool(plan["diagnostics"]["sensitivity"]), True),
        _check_equal(
            "plan_safety_boundary_no_claim",
            plan["safety_score_evaluation_boundary"]["claims_safety_benefit"],
            False,
        ),
        _check_equal(
            "plan_artifact_records_sha_heads",
            "HEADS.txt" in plan["artifact_recording"]["plan_outputs"]
            and "SHA256SUMS" in plan["artifact_recording"]["plan_outputs"],
            True,
        ),
    ]


def _runbook_checks(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    return [
        _check_equal("runbook_guard_env_present", GUARD_ENV_VAR in text, True),
        _check_equal("runbook_requires_guard_yes", '!= "yes"' in text, True),
        _check_equal("runbook_exits_without_guard", "exit 2" in text, True),
        _check_equal("runbook_has_no_git_pull", "git pull" not in lower, True),
        _check_equal("runbook_checks_dp_head", EXPECTED_DP_HEAD in text, True),
        _check_equal("runbook_checks_snapshot_count", "SNAPSHOT_COUNT" in text, True),
        _check_equal("runbook_policy_present", POLICY_NAME in text, True),
        _check_equal(
            "runbook_runs_candidate_screen",
            "analyze_diffusion_planner_route_topology_candidate_screen.py" in text,
            True,
        ),
        _check_equal(
            "runbook_runs_absolute_guard",
            "analyze_diffusion_planner_route_topology_absolute_comfort_guard.py" in text,
            True,
        ),
        _check_equal(
            "runbook_records_sha256sums",
            "sha256sum" in text and "SHA256SUMS" in text,
            True,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["blocked_boundaries"] + plan["reject_criteria"]).lower()
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal(
            "boundary_blocks_execution",
            decision["fixed_snapshot_screen_rerun_execution_authorized"],
            False,
        ),
        _check_equal(
            "boundary_blocks_candidate_generation",
            decision["candidate_generation_execution_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_full36", decision["full36_authorized"], False),
        _check_equal(
            "boundary_blocks_formal_seeds",
            decision["formal_seeds_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_training", decision["camp_retraining_authorized"], False),
        _check_equal("boundary_blocks_promotion", decision["atom_promotion_authorized"], False),
        _check_equal(
            "boundary_blocks_online_selector",
            decision["online_selector_promotion_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal(
            "boundary_blocks_camp_top1_claim",
            decision["camp_over_dp_top1_claim_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_benders", decision["classic_benders_claim_authorized"], False),
        _check_equal(
            "boundary_next_gate_requires_user_authorization",
            decision["next_gate_requires_user_authorization"],
            True,
        ),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "fixed_snapshot_screen_rerun_plan_ready": passed,
        "fixed_snapshot_screen_rerun_plan_authorized": passed,
        "guarded_fixed_snapshot_screen_rerun_next_gate_authorized": passed,
        "next_gate_requires_user_authorization": True if passed else False,
        "guard_env_var": GUARD_ENV_ASSIGNMENT if passed else None,
        "implementation_code_edit_authorized": False,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
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
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
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
        item = Path(name.strip())
        if not item.is_absolute():
            item = root / item
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


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def _exit_flag(text: str, key: str, expected: str) -> bool:
    return any(line.strip() == f"{key}={expected}" for line in text.splitlines())


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
