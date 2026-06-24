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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    DEFAULT_DEVELOPMENT_ROOT,
)


GATE_NAME = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_plan_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_plan_rejected"
)
SOURCE_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "post_implementation_static_review_passed"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "guarded_fixed_snapshot_screen_rerun_only"
)

DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_post_implementation_static_review_b44e3f5"
)
DEFAULT_PLANNED_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_bff8f8b"
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
DEFAULT_ASSET_ROOT = "/root/autodl-tmp/camp_dp_assets"
DEFAULT_REMOTE_PYTHON = "/root/miniconda3/bin/python"
DEFAULT_EXPECTED_SNAPSHOT_COUNT = 57

SOURCE_JSON = "STATIC_REVIEW.json"
SOURCE_DECISION = "STATIC_REVIEW_DECISION.txt"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
EXIT_CODE = "EXIT_CODE"
STATIC_REVIEW_EXIT = "STATIC_REVIEW_EXIT"
STATIC_REVIEW_DECISION_EXIT = "STATIC_REVIEW_DECISION_EXIT"
SHA256SUMS_CHECK_EXIT = "SHA256SUMS_CHECK_EXIT"

GUARD_ENV_VAR = (
    "CANDIDATE_SET_CONSENSUS_LANE_PROJECTED_JERK_PROGRESS_"
    "DEFAULT_OFF_FIXED_SNAPSHOT_RERUN_APPROVED"
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
    "safety_benefit_evidence",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
    "classical_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for the default-off product-code diagnostic "
            "payload fixed-snapshot screen rerun. This writes a guarded "
            "future runbook and does not execute the rerun."
        )
    )
    parser.add_argument(
        "--static_review_root",
        type=Path,
        default=Path(DEFAULT_STATIC_REVIEW_ROOT),
    )
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
        static_review_root=args.static_review_root,
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
    static_review_root: Path,
    planned_execution_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(static_review_root)
    source = _source_summary(artifact)
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
    decision = _final_decision(passed, checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_plan_v1"
            ),
            "gate": GATE_NAME,
            "label": label,
            "role": "fixed-snapshot screen rerun plan-only gate",
            "plan_only": True,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_replay": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This gate reads only the post-implementation static review "
                "artifact and current heads, then writes a guarded future "
                "fixed-snapshot screen rerun contract. It does not execute "
                "candidate generation, rerun the screen, run replay, use "
                "formal seeds, define or promote runtime atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
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
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["fixed_snapshot_rerun_plan"]
    lines = [
        "# Default-Off Product-Code Fixed-Snapshot Screen Rerun Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Scope",
        "",
        "- plan-only gate; no screen rerun is executed here",
        "- fixed DP remains a black-box candidate trajectory source",
        "- CAMP diagnostic payloads stay default-off and selection-neutral",
        "- formal seeds 11/12/13 remain frozen",
        "",
        "## Planned Fixed Snapshot Corpus",
        "",
        f"- Snapshot dir: `{plan['fixed_snapshot_corpus']['snapshot_dir']}`",
        f"- Expected snapshots: `{plan['fixed_snapshot_corpus']['expected_snapshot_count']}`",
        f"- Route: `{plan['fixed_snapshot_corpus']['route_name']}`",
        f"- Seed: `{plan['fixed_snapshot_corpus']['seed']}`",
        "",
        "## Gates",
        "",
    ]
    for name, gate in sorted(plan["gates"].items()):
        lines.append(f"- `{name}`: {gate['contract']}")
    lines.extend(
        [
            "",
            "## Runbook Guard",
            "",
            f"- Guard variable: `{plan['guard_env_assignment']}`",
            "- The future runbook refuses to run without this guard.",
            "",
            "## Boundary",
            "",
            "- no replay, Full36, formal seeds, CAMP retraining, or DP modification",
            "- no atom promotion or online selector promotion",
            "- no safety-benefit or CAMP-over-DP-Top-1 claim",
            "",
        ]
    )
    return "\n".join(lines)


def render_runbook(plan: dict[str, Any]) -> str:
    corpus = plan["fixed_snapshot_corpus"]
    outputs = plan["execution_artifacts"]
    return f"""#!/usr/bin/env bash
set -euo pipefail

if [[ "${{{GUARD_ENV_VAR}:-}}" != "yes" ]]; then
  echo "Refusing to run: set {GUARD_ENV_ASSIGNMENT} after the plan gate is accepted." >&2
  exit 2
fi

PY="{DEFAULT_REMOTE_PYTHON}"
CAMP_ROOT="/root/autodl-tmp/camp_core"
OUTPUT_ROOT="{outputs['output_root']}"
mkdir -p "${{OUTPUT_ROOT}}"

cd "${{CAMP_ROOT}}"
git rev-parse HEAD > "${{OUTPUT_ROOT}}/CAMP_HEAD.txt"
git rev-parse origin/main > "${{OUTPUT_ROOT}}/CAMP_ORIGIN_MAIN.txt"
(cd "{DEFAULT_DIFFUSION_REPO}" && git rev-parse HEAD) > "${{OUTPUT_ROOT}}/DP_HEAD.txt"

"${{PY}}" scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py \\
  --snapshot_dir "{corpus['snapshot_dir']}" \\
  --route_topology_gate_json "{corpus['route_topology_gate_json']}" \\
  --diffusion_repo "{corpus['diffusion_repo']}" \\
  --reward_config "{corpus['reward_config']}" \\
  --generator_policy lane_projected_jerk_progress_red_stop \\
  --red_stop_margin_m 2.0 \\
  --red_stop_margin_m 4.0 \\
  --red_stop_margin_m 6.0 \\
  --backup_stop_offset_m 0.0 \\
  --backup_stop_offset_m 1.0 \\
  --lane_projected_offset_scale 1.0 \\
  --lane_projected_offset_scale 0.5 \\
  --lane_projected_offset_scale 0.0 \\
  --jerk_progress_max_jerk_mps3 8.0 \\
  --min_snapshot_support_rate 0.25 \\
  --label default_off_product_code_fixed_snapshot_screen_rerun \\
  --output_json "{outputs['screen_json']}" \\
  --output_md "{outputs['screen_md']}" \\
  > "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.log" \\
  2> "${{OUTPUT_ROOT}}/CANDIDATE_SCREEN.err"

sha256sum "${{OUTPUT_ROOT}}"/* > "${{OUTPUT_ROOT}}/SHA256SUMS"
"""


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        HEADS,
        SOURCE_JSON,
        SOURCE_DECISION,
        STATIC_REVIEW_EXIT,
        STATIC_REVIEW_DECISION_EXIT,
        SHA256SUMS_CHECK_EXIT,
        EXIT_CODE,
        SHA256SUMS,
    )
    files = {name: (root / name).is_file() for name in required}
    json_payload = _read_json(root / SOURCE_JSON)
    decision_text = _read_text(root / SOURCE_DECISION)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": _sha256sums_ok(root),
        "heads": _parse_key_values(_read_text(root / HEADS)),
        "json_payload": json_payload,
        "decision": _parse_key_values(decision_text),
        "static_review_exit_ok": _exit_ok(root / STATIC_REVIEW_EXIT),
        "static_review_decision_exit_ok": _exit_ok(root / STATIC_REVIEW_DECISION_EXIT),
        "sha256sums_check_exit_ok": _exit_ok(root / SHA256SUMS_CHECK_EXIT),
        "exit_code_ok": _exit_ok(root / EXIT_CODE),
    }


def _source_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = artifact.get("json_payload") or {}
    decision = artifact.get("decision") or {}
    return {
        "status": payload.get("status"),
        "decision_status": decision.get("status"),
        "passed": bool(payload.get("passed")),
        "decision_passed": _bool_value(decision.get("passed")),
        "post_implementation_static_review_complete": _bool_value(
            decision.get("post_implementation_static_review_complete")
        ),
        "recommended_next_gate": payload.get("next_recommended_gate"),
        "decision_recommended_next_gate": decision.get("recommended_next_gate"),
        "fixed_snapshot_screen_rerun_authorized": bool(
            payload.get("fixed_snapshot_screen_rerun_authorized")
        )
        or _bool_value(decision.get("fixed_snapshot_screen_rerun_authorized")),
        "checks": payload.get("checks") if isinstance(payload.get("checks"), dict) else {},
        "blocked_action_conflicts": _blocked_action_conflicts(payload, decision),
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
        "product_code_payload_contract": {
            "diagnostic_payloads_default_off": True,
            "selection_effect_allowed": False,
            "future_outcome_leakage_allowed": False,
            "closed_loop_outcome_fields_read": False,
            "payloads_after_selection_only": True,
            "missing_route_progress_support_fails_closed": True,
        },
        "candidate_config": {
            "default_policy_preserved": "lane_centerline_red_stop",
            "generator_policy": "lane_projected_jerk_progress_red_stop",
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "lane_projected_offset_scales": [1.0, 0.5, 0.0],
            "jerk_progress_max_jerk_mps3": 8.0,
            "min_snapshot_support_rate": 0.25,
            "candidate_build_p95_latency_ms": 10.0,
            "total_p95_latency_ms": 100.0,
        },
        "gates": {
            "selector_equivalence": {
                "status": "predeclared",
                "contract": (
                    "default-off selector behavior and selected_index must "
                    "remain equivalent with diagnostic payloads disabled"
                ),
            },
            "payload_no_leak_default_off": {
                "status": "predeclared",
                "contract": (
                    "opt-in diagnostic payloads may read only current-tick "
                    "candidate and route geometry features and must report "
                    "selection_effect=False"
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
                    "PerfectTracker comfort, and absolute lateral guards are "
                    "reported without promotion"
                ),
            },
            "safety_score_boundary": {
                "status": "predeclared",
                "contract": (
                    "fixed-snapshot scores may be recorded only as diagnostic "
                    "screen evidence, not as safety-benefit evidence"
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
                "diagnostic_payload_count",
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
            "screen_json": f"{execution_root}/default_off_fixed_snapshot_screen.json",
            "screen_md": f"{execution_root}/default_off_fixed_snapshot_screen.md",
            "required_files": [
                "default_off_fixed_snapshot_screen.json",
                "default_off_fixed_snapshot_screen.md",
                "CANDIDATE_SCREEN.log",
                "CANDIDATE_SCREEN.err",
                "CAMP_HEAD.txt",
                "CAMP_ORIGIN_MAIN.txt",
                "DP_HEAD.txt",
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
                "CAMP_HEAD.txt",
                "CAMP_ORIGIN_MAIN.txt",
                "DP_HEAD.txt",
                "CANDIDATE_SCREEN.log",
                "CANDIDATE_SCREEN.err",
                "SHA256SUMS",
            ],
        },
        "accept_criteria": [
            "post-implementation static review artifact passed and recommends this plan gate",
            "CAMP HEAD equals origin/main before any future execution gate",
            f"DP HEAD remains {EXPECTED_DP_HEAD}",
            "runbook refuses to run without the explicit guard environment variable",
            "fixed snapshot corpus is the existing nonformal seed2 NPC4 traffic-light corpus",
            "formal seeds 11/12/13 are absent from the planned run matrix",
            "selector equivalence and payload no-leak/default-off gates are predeclared",
            "latency, fallback, progress, comfort, spread, rank, and sensitivity diagnostics are predeclared",
        ],
        "reject_criteria": [
            "missing source review artifact, exit code, or SHA256SUMS",
            "source review does not recommend this plan gate",
            "CAMP HEAD differs from origin/main",
            f"DP HEAD differs from {EXPECTED_DP_HEAD}",
            "formal seeds appear in the planned run matrix or runbook",
            "runbook lacks the explicit guard or attempts git pull",
            "plan authorizes replay, Full36, training, online selector changes, atom promotion, safety claims, or DP modification",
        ],
        "safety_score_evaluation_boundary": {
            "uses_closed_loop_outcomes": False,
            "claims_safety_benefit": False,
            "claims_camp_over_dp_top1": False,
            "allowed": (
                "fixed-snapshot diagnostic scores and PerfectTracker comfort "
                "summaries may be recorded only as screen evidence"
            ),
        },
        "blocked_boundaries": [
            "this gate is plan-only and does not execute the fixed-snapshot screen rerun",
            "replay is not authorized",
            "Full36 is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "CAMP retraining is not authorized",
            "atom promotion or online selector change is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or CAMP-over-DP-Top-1 claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "recommended_next_gate": source["recommended_next_gate"],
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
            "boundary": "asset declared only; no generation in plan gate",
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
            "boundary": "asset declared only; no generation in plan gate",
        },
    ]


def _assets() -> dict[str, Any]:
    return {
        "asset_root": DEFAULT_ASSET_ROOT,
        "declared_only_assets": [
            "sample_map_route_2_to_104.pkl",
            "nishishinjuku_release_auto_route.pkl",
        ],
        "guarded_rerun_asset": "sample_map_tl_route_59_to_86.pkl",
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("source_artifact_root_exists", artifact["exists"]),
        _check("source_artifact_required_files_present", artifact["required_files_present"]),
        _check("source_artifact_sha256sums_ok", artifact["sha256sums_ok"]),
        _check("source_static_review_exit_ok", artifact["static_review_exit_ok"]),
        _check(
            "source_static_review_decision_exit_ok",
            artifact["static_review_decision_exit_ok"],
        ),
        _check("source_sha256sums_check_exit_ok", artifact["sha256sums_check_exit_ok"]),
        _check("source_exit_code_ok", artifact["exit_code_ok"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_equals_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        _check("source_status", source["status"] == SOURCE_STATUS),
        _check("source_decision_status", source["decision_status"] == SOURCE_STATUS),
        _check("source_passed", source["passed"] is True),
        _check("source_decision_passed", source["decision_passed"] is True),
        _check(
            "source_post_implementation_static_review_complete",
            source["post_implementation_static_review_complete"] is True,
        ),
        _check("source_recommends_this_plan_gate", source["recommended_next_gate"] == GATE_NAME),
        _check(
            "source_decision_recommends_this_plan_gate",
            source["decision_recommended_next_gate"] == GATE_NAME,
        ),
        _check(
            "source_rerun_execution_not_authorized",
            source["fixed_snapshot_screen_rerun_authorized"] is False,
        ),
        _check("source_no_blocked_actions", not source["blocked_action_conflicts"]),
    ]
    for required in (
        "default_off_consensus_signature",
        "default_off_progress_signature",
        "diagnostic_payloads_default_none",
        "payloads_after_selection",
        "selection_effect_false",
        "future_outcome_leakage_false",
        "no_dp_path_changed",
        "no_formal_seed_execution",
        "no_replay_execution_artifact",
        "no_camp_retraining",
    ):
        checks.append(_check(f"source_check_{required}", source["checks"].get(required) is True))
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = {int(row["seed"]) for row in plan["route_seed_matrix"]}
    runbook_required = plan["execution_artifacts"]["required_files"]
    return [
        _check("plan_selection_type", plan["selection_type"] == "guarded_fixed_snapshot_screen_rerun_plan_only"),
        _check("plan_authorized_next_work", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_guard_declared", plan["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT),
        _check("plan_no_formal_seeds", not (seeds & set(FORMAL_SEEDS))),
        _check("plan_traffic_light_covered", plan["coverage_summary"]["traffic_light_covered"]),
        _check("plan_turn_covered", plan["coverage_summary"]["turn_covered"]),
        _check("plan_normal_covered", plan["coverage_summary"]["normal_covered"]),
        _check("plan_nishishinjuku_boundary_declared", plan["coverage_summary"]["nishishinjuku_assets_declared"]),
        _check("plan_single_guarded_rerun", plan["coverage_summary"]["included_guarded_rerun_count"] == 1),
        _check("plan_selector_gate_declared", "selector_equivalence" in plan["gates"]),
        _check("plan_payload_gate_declared", "payload_no_leak_default_off" in plan["gates"]),
        _check("plan_latency_gate_declared", "latency" in plan["gates"]),
        _check("plan_future_artifacts_declared", "SHA256SUMS" in runbook_required),
        _check("plan_safety_boundary_no_claim", plan["safety_score_evaluation_boundary"]["claims_safety_benefit"] is False),
        _check("plan_camp_top1_boundary_no_claim", plan["safety_score_evaluation_boundary"]["claims_camp_over_dp_top1"] is False),
    ]


def _runbook_checks(runbook_text: str) -> list[dict[str, Any]]:
    return [
        _check("runbook_has_guard", GUARD_ENV_VAR in runbook_text and "Refusing to run" in runbook_text),
        _check("runbook_has_snapshot_dir", DEFAULT_SNAPSHOT_DIR in runbook_text),
        _check("runbook_has_expected_policy", "lane_projected_jerk_progress_red_stop" in runbook_text),
        _check("runbook_has_sha_recording", "sha256sum" in runbook_text),
        _check("runbook_no_git_pull", "git pull" not in runbook_text),
        _check("runbook_no_formal_seed_11", "seed 11" not in runbook_text and "seed=11" not in runbook_text),
        _check("runbook_no_formal_seed_12", "seed 12" not in runbook_text and "seed=12" not in runbook_text),
        _check("runbook_no_formal_seed_13", "seed 13" not in runbook_text and "seed=13" not in runbook_text),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_blocks_training", "CAMP retraining is not authorized" in plan["blocked_boundaries"]),
        _check("boundary_blocks_dp_modification", "DP weights and DP code must remain fixed" in plan["blocked_boundaries"]),
        _check("boundary_blocks_safety_claim", "no safety benefit or CAMP-over-DP-Top-1 claim is authorized" in plan["blocked_boundaries"]),
        _check("boundary_product_payload_selection_neutral", plan["product_code_payload_contract"]["selection_effect_allowed"] is False),
        _check("boundary_product_payload_no_future_leakage", plan["product_code_payload_contract"]["future_outcome_leakage_allowed"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "fixed_snapshot_screen_rerun_plan_ready": passed,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "candidate_generation_execution_authorized": False,
        "replay_authorized": False,
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
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"json_payload", "decision"}
    }


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


def _parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _exit_ok(path: Path) -> bool:
    return path.is_file() and path.read_text(encoding="utf-8").strip() == "0"


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
        candidate = root / name.strip()
        if not candidate.is_file():
            return False
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != expected:
            return False
    return True


def _blocked_action_conflicts(
    payload: dict[str, Any],
    decision: dict[str, str],
) -> list[str]:
    conflicts = []
    for key in BLOCKED_ACTIONS:
        if bool(payload.get(key)) or _bool_value(decision.get(key)):
            conflicts.append(key)
    return conflicts


def _bool_value(value: Optional[str]) -> bool:
    return str(value).strip().lower() == "true"


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
