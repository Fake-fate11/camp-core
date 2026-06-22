#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_payload_smoke import (
    DATASET_AUDIT,
    EXPECTED_DP_HEAD,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _source_checks as _candidate_set_payload_source_checks,
)


SOURCE_READY_STATUS = "candidate_set_consensus_tiny_materiality_diagnosis_ready"
SOURCE_READY_NEXT_WORK = "candidate_set_consensus_broader_nonformal_materiality_plan_only"

READY_STATUS = "candidate_set_consensus_broader_nonformal_materiality_plan_ready"
REJECT_STATUS = "candidate_set_consensus_broader_nonformal_materiality_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_broader_nonformal_materiality_replay_consideration_next_round_only"
)

FORMAL_SEEDS = frozenset({11, 12, 13})
SUMMARY_KEY = "camp_candidate_set_consensus_payload_logging"
MAX_PAYLOAD_LATENCY_MS = 2.0
MIN_POSITIVE_SPREAD_RATE = 0.25
MIN_VALID_RECORD_RATE = 0.80

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


@dataclass(frozen=True)
class EvidenceRunSpec:
    run_id: str
    map_name: str
    map_path: str
    route_name: str
    route: str
    seed: int
    max_npcs: int
    spawn_probability: float
    traffic_lights: str
    scenario_buckets: tuple[str, ...]


@dataclass(frozen=True)
class BroaderMaterialitySpec:
    camp_repo: str = "/root/autodl-tmp/camp_core"
    root: str = (
        "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality"
    )
    diffusion_repo: str = "/root/autodl-tmp/Diffusion-Planner"
    model_path: str = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth"
    model_args: str = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json"
    config: str = (
        "/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/"
        "replay_default.json"
    )
    reward_config: str = (
        "/root/autodl-tmp/camp_core/configs/integrations/"
        "dp_camp_reward_eval.json"
    )
    atom_scales: str = (
        "/root/autodl-tmp/camp_dp_assets/"
        "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
        "atom_scales_dp_static.json"
    )
    static_weights: str = (
        "/root/autodl-tmp/camp_dp_assets/"
        "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
        "offline_weights_dp_static.npy"
    )
    steps: int = 10
    num_candidates: int = 8
    candidate_noise_scale: float = 1.0
    candidate_reference_blend_steps: int = 5
    payload_steps: int = 10
    min_available_records: int = 60
    expected_dp_head: str = EXPECTED_DP_HEAD
    runs: tuple[EvidenceRunSpec, ...] = (
        EvidenceRunSpec(
            run_id="sample_tl59_seed1_npc0_tlon",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        EvidenceRunSpec(
            run_id="sample_tl59_seed2_npc4_tlon",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=2,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=(
                "traffic_light",
                "red_light_turn",
                "sharp_turn",
                "npc_interaction",
            ),
        ),
        EvidenceRunSpec(
            run_id="sample_tl59_seed3_npc4_tloff",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=3,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("sharp_turn", "npc_interaction"),
        ),
        EvidenceRunSpec(
            run_id="sample_normal2_seed1_npc0_tloff",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_route_2_to_104",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("normal",),
        ),
        EvidenceRunSpec(
            run_id="nishi_release_seed2_npc4_tlon",
            map_name="nishishinjuku",
            map_path="/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm",
            route_name="nishishinjuku_release_auto_route",
            route="/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl",
            seed=2,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "npc_interaction", "dense_scene"),
        ),
        EvidenceRunSpec(
            run_id="nishi_lanechange_seed4_npc4_tloff",
            map_name="nishishinjuku",
            map_path="/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm",
            route_name="nishishinjuku_lane_change_route_7_via_8_to_1",
            route=(
                "/root/autodl-tmp/camp_dp_assets/"
                "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
            ),
            seed=4,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("lane_change_or_merge", "npc_interaction", "dense_scene"),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only broader nonformal materiality gate for candidate-set "
            "consensus. It emits predeclared scope, gates, diagnostics, and a "
            "guarded runbook, but does not run Diffusion Planner."
        )
    )
    parser.add_argument("--tiny_materiality_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument("--payload_audit_source", type=Path, default=PAYLOAD_AUDIT)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = BroaderMaterialitySpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        tiny_materiality=_read_json(args.tiny_materiality_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        paths={"tiny_materiality_json": str(args.tiny_materiality_json)},
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
    tiny_materiality: dict[str, Any],
    label: str | None = None,
    spec: BroaderMaterialitySpec = BroaderMaterialitySpec(),
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(tiny_materiality)
    source_checks = [
        *_source_checks(source),
        *_candidate_set_payload_source_checks(
            replay_source=replay_source,
            payload_audit_source=payload_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_broader_nonformal_materiality_plan_v1",
            "label": label,
            "role": "plan-only broader materiality design; no replay execution",
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "sync_boundary": (
                "Before any later execution, CAMP must be fast-forward synced "
                "on AutoDL, CAMP HEAD must equal origin/main, and DP HEAD must "
                f"equal the fixed commit {EXPECTED_DP_HEAD}. This plan does "
                "not run those commands."
            ),
            "math_boundary": (
                "Candidate-set consensus remains a fixed current-tick "
                "finite-candidate diagnostic derived from the DP candidate "
                "tensor before selection. Its primary RMS coefficient is "
                "finite and nonnegative when available; if a later, separate "
                "atom-design gate accepts it, it can enter as a fixed "
                "coefficient a_k and preserve score_k(w)=a_k^T w plus the "
                "simplex/CVaR/L2 convex master in w. This plan constructs no "
                "DP-side classical Benders master/subproblem, dual, or valid "
                "cuts."
            ),
        },
        "source_summary": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "route_seed_matrix": [asdict(run) for run in spec.runs],
        "coverage_targets": _coverage_targets(spec),
        "operational_boundaries": _operational_boundaries(spec),
        "diagnostic_contract": _diagnostic_contract(spec),
        "safety_score_evaluation_boundary": _safety_score_evaluation_boundary(),
        "artifact_recording": _artifact_recording(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "commands": _commands(spec),
        "blocked_actions": {
            "run_replay_now": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "atom_promotion": True,
            "classic_benders_claim": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "plan_only": True,
            "plan_artifact_ready": passed,
            "broader_replay_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
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
            "proposed_replay_scope_if_later_accepted": (
                "6 paired nonformal runs x 10 steps x 8 candidates, baseline "
                "plus default-off logging-enabled candidate-set consensus, "
                "selector-neutral, no formal seeds"
                if passed
                else None
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Broader Nonformal Materiality Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- plan only: `{decision['plan_only']}`",
        f"- broader replay authorized now: `{decision['broader_replay_authorized']}`",
        f"- proposed scope if later accepted: `{decision['proposed_replay_scope_if_later_accepted']}`",
        "",
        "## Source Summary",
        "",
        f"`{report['source_summary']}`",
        "",
        "## Route/Seed Matrix",
        "",
        "| Run | Route | Seed | NPCs | Spawn | TL | Buckets |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for run in report["route_seed_matrix"]:
        buckets = ", ".join(run["scenario_buckets"])
        lines.append(
            f"| `{run['run_id']}` | `{run['route_name']}` | `{run['seed']}` | "
            f"`{run['max_npcs']}` | `{run['spawn_probability']}` | "
            f"`{run['traffic_lights']}` | `{buckets}` |"
        )
    lines.extend(
        [
            "",
            "## Source Checks",
            "",
            "| Check | Passed | Observed | Expected | Missing |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for check in report["source_checks"]:
        missing = ", ".join(check.get("missing_tokens", []))
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` | `{missing}` |"
        )
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(
        f"- `{check['name']}`: `{check['passed']}`"
        for check in report["plan_checks"]
    )
    lines.extend(["", "## Coverage Targets", "", f"`{report['coverage_targets']}`"])
    lines.extend(["", "## Operational Boundaries", "", f"`{report['operational_boundaries']}`"])
    lines.extend(["", "## Diagnostics", "", f"`{report['diagnostic_contract']}`"])
    lines.extend(
        [
            "",
            "## Safety-Score Boundary",
            "",
            f"`{report['safety_score_evaluation_boundary']}`",
            "",
            "## Commands",
            "",
        ]
    )
    command_separator = " \\\n" "  "
    commands = report["commands"]
    for name in ("camp_sync", "asset_audit", "head_audit", "selector_equivalence", "payload_audit", "dataset_audit"):
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(commands[name]),
                "```",
                "",
            ]
        )
    lines.extend(["### paired_replays", ""])
    for item in commands["paired_replays"]:
        lines.extend(
            [
                f"#### {item['run_id']} {item['variant']}",
                "",
                "```bash",
                command_separator.join(item["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["## Artifact Recording", "", f"`{report['artifact_recording']}`"])
    lines.extend(["", "## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def render_bash(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    if not decision.get("plan_artifact_ready"):
        raise ValueError("Cannot render runbook for a rejected plan.")
    commands = report["commands"]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Plan-only runbook generated by candidate-set consensus broader materiality plan.",
        "# Do not run unless a later gate explicitly authorizes broader nonformal replay.",
        "# Forbidden now: formal seeds, Full36, online selector promotion, CAMP retraining, DP modification.",
        f"# Expected DP HEAD: {EXPECTED_DP_HEAD}",
        "",
        'if [[ "${CANDIDATE_SET_CONSENSUS_BROADER_MATERIALITY_REPLAY_APPROVED:-}" != "yes" ]]; then',
        '  echo "plan-only runbook: replay is not authorized in this gate" >&2',
        "  exit 2",
        "fi",
        "",
        "cd /root/autodl-tmp/camp_core",
        "",
    ]
    for name in ("camp_sync", "asset_audit", "head_audit"):
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    for item in commands["paired_replays"]:
        lines.extend(
            [
                f'echo "== replay {item["run_id"]} {item["variant"]} =="',
                shlex.join(item["command"]),
                "",
            ]
        )
    lines.extend(
        [
            'echo "== selector_equivalence =="',
            shlex.join(commands["selector_equivalence"]),
            "",
            'echo "== payload_audit =="',
            shlex.join(commands["payload_audit"]),
            "",
            'echo "== dataset_audit =="',
            shlex.join(commands["dataset_audit"]),
            "",
            'echo "candidate_set_consensus_broader_nonformal_materiality_replay_candidate_complete"',
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    record = _dict(report.get("record_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "signal_present": bool(decision.get("signal_present")),
        "materiality_gate_passed": bool(decision.get("materiality_gate_passed")),
        "sample_too_small_for_promotion": bool(
            decision.get("sample_too_small_for_promotion")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(
            decision.get("atom_promotion_authorized")
        ),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
        "blocked_action_conflicts": conflicts,
        "records": int(record.get("records", -1)),
        "available_records": int(record.get("available_records", -1)),
        "valid_records": int(record.get("valid_records", -1)),
        "positive_spread_records": int(record.get("positive_spread_records", -1)),
        "selected_not_consensus_best_records": int(
            record.get("selected_not_consensus_best_records", -1)
        ),
        "finite_lambda_records": int(record.get("finite_lambda_records", -1)),
        "selected_rank_mean": _float_or_none(record.get("selected_rank_mean")),
        "selected_rank_max": _float_or_none(record.get("selected_rank_max")),
        "min_lambda_to_change_any_record": _float_or_none(
            record.get("min_lambda_to_change_any_record")
        ),
    }


def _source_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_tiny_materiality_status", summary["status"], SOURCE_READY_STATUS),
        _check_equal("source_tiny_materiality_passed", summary["passed"], True),
        _check_equal(
            "source_authorizes_broader_plan",
            summary["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal("source_signal_present", summary["signal_present"], True),
        _check_equal(
            "source_materiality_not_promotional",
            summary["materiality_gate_passed"],
            False,
        ),
        _check_equal(
            "source_sample_too_small_for_promotion",
            summary["sample_too_small_for_promotion"],
            True,
        ),
        _check_equal(
            "source_safety_benefit_not_claimed",
            summary["safety_benefit_evidence"],
            False,
        ),
        _check_equal(
            "source_atom_promotion_not_authorized",
            summary["atom_promotion_authorized"],
            False,
        ),
        _check_equal(
            "source_new_replay_not_authorized",
            summary["new_replay_authorized"],
            False,
        ),
        _check_empty(
            "source_no_blocked_action_conflicts",
            summary["blocked_action_conflicts"],
        ),
        _check_gte("source_valid_records", summary["valid_records"], 3),
        _check_gte("source_positive_spread_records", summary["positive_spread_records"], 1),
        _check_gte(
            "source_selected_not_consensus_best_records",
            summary["selected_not_consensus_best_records"],
            1,
        ),
        _check_gte("source_finite_lambda_records", summary["finite_lambda_records"], 1),
    ]


def _plan_checks(spec: BroaderMaterialitySpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    map_names = {run.map_name for run in spec.runs}
    route_names = {run.route_name for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    npc_counts = {run.max_npcs for run in spec.runs}
    bucket_counts = _bucket_counts(spec)
    total_records = int(spec.steps) * len(spec.runs)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": not (seeds & FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "paired_matrix_size_predeclared",
            "passed": len(spec.runs) == 6 and int(spec.steps) == 10,
            "details": {"runs": len(spec.runs), "steps": int(spec.steps)},
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": int(spec.num_candidates) == 8,
            "details": {"num_candidates": int(spec.num_candidates)},
        },
        {
            "name": "planned_records_and_candidates_material",
            "passed": total_records >= 60
            and total_records * int(spec.num_candidates) >= 480,
            "details": {
                "planned_records": total_records,
                "planned_candidate_rows": total_records * int(spec.num_candidates),
            },
        },
        {
            "name": "sample_and_nishishinjuku_maps_covered",
            "passed": {"sample_map", "nishishinjuku"}.issubset(map_names),
            "details": {"map_names": sorted(map_names)},
        },
        {
            "name": "required_routes_covered",
            "passed": {
                "sample_map_tl_route_59_to_86",
                "sample_map_route_2_to_104",
                "nishishinjuku_release_auto_route",
                "nishishinjuku_lane_change_route_7_via_8_to_1",
            }.issubset(route_names),
            "details": {"route_names": sorted(route_names)},
        },
        {
            "name": "traffic_light_on_and_off_covered",
            "passed": {"on", "off"}.issubset(traffic_modes),
            "details": {"traffic_light_modes": sorted(traffic_modes)},
        },
        {
            "name": "npc_and_no_npc_covered",
            "passed": 0 in npc_counts and any(count > 0 for count in npc_counts),
            "details": {"max_npcs": sorted(npc_counts)},
        },
        {
            "name": "scenario_buckets_cover_required_contexts",
            "passed": all(
                bucket_counts.get(bucket, 0) > 0
                for bucket in (
                    "traffic_light",
                    "red_light_turn",
                    "sharp_turn",
                    "normal",
                    "lane_change_or_merge",
                    "npc_interaction",
                    "dense_scene",
                )
            ),
            "details": {"scenario_bucket_counts": bucket_counts},
        },
        {
            "name": "payload_horizon_and_latency_budget_predeclared",
            "passed": int(spec.payload_steps) >= 2 and MAX_PAYLOAD_LATENCY_MS > 0.0,
            "details": {
                "payload_steps": int(spec.payload_steps),
                "max_payload_latency_ms": MAX_PAYLOAD_LATENCY_MS,
            },
        },
        {
            "name": "fixed_dp_head_declared",
            "passed": spec.expected_dp_head == EXPECTED_DP_HEAD,
            "details": {"expected_dp_head": spec.expected_dp_head},
        },
    ]


def _coverage_targets(spec: BroaderMaterialitySpec) -> dict[str, Any]:
    records = int(spec.steps) * len(spec.runs)
    return {
        "planned_logs": len(spec.runs),
        "planned_records": records,
        "planned_candidate_rows": records * int(spec.num_candidates),
        "expected_available_payload_records_min": int(spec.min_available_records),
        "max_payload_latency_ms": MAX_PAYLOAD_LATENCY_MS,
        "scenario_bucket_counts": _bucket_counts(spec),
        "route_counts": _route_counts(spec),
    }


def _operational_boundaries(spec: BroaderMaterialitySpec) -> dict[str, Any]:
    return {
        "selector_equivalence_gate": (
            "selected_index, feasible_mask, atoms, normalized_atoms, scores, "
            "and weights must be exactly equivalent between baseline and "
            "logging-enabled paired roots"
        ),
        "payload_no_leak_default_off_gate": (
            f"baseline {SUMMARY_KEY}.enabled=false; logging-enabled summary "
            "enabled=true; payload reports selection_effect=false, "
            "future_outcome_leakage=false, closed_loop_outcome_fields_read=false"
        ),
        "latency_gate": (
            "candidate_set_consensus_payload latency max must stay below "
            f"{MAX_PAYLOAD_LATENCY_MS} ms over the broader matrix"
        ),
        "fallback_boundary": (
            "existing learned fallback is used only as the fixed static selector "
            "fallback mode; no fallback policy, fallback trigger, or online "
            "fallback promotion is changed"
        ),
        "progress_boundary": (
            "existing camp_min_progress_ratio=0.8 and route-progress shadows "
            "remain context/audit fields only; no progress threshold tuning"
        ),
        "comfort_boundary": (
            "existing redstopfloor05 j1/lat2 static weights and reward config "
            "remain fixed; no comfort atom, comfort weight, or DP smoothing "
            "change is introduced"
        ),
        "formal_seed_boundary": "seeds 11, 12, and 13 remain forbidden",
    }


def _diagnostic_contract(spec: BroaderMaterialitySpec) -> dict[str, Any]:
    return {
        "spread_diagnostics": [
            "positive_spread_records and positive_spread_rate overall",
            "cost_spread_mean, max, and per-route bucket distributions",
            "reject if any required route bucket has zero valid spread records",
        ],
        "rank_diagnostics": [
            "selected_consensus_rank mean and max",
            "selected_not_consensus_best_records overall and per bucket",
            "best_consensus_index versus selected_index counts",
        ],
        "sensitivity_diagnostics": [
            "finite nonnegative lambda_to_change counts",
            "min_lambda_to_change_any_record and per-bucket minima",
            "lambda distribution is diagnostic only and cannot tune online weights",
        ],
        "minimum_materiality_screen": {
            "valid_record_rate": f">= {MIN_VALID_RECORD_RATE}",
            "positive_spread_rate": f">= {MIN_POSITIVE_SPREAD_RATE}",
            "records": int(spec.steps) * len(spec.runs),
            "candidate_rows": int(spec.steps) * len(spec.runs) * int(spec.num_candidates),
        },
        "non_promotion_boundary": (
            "Passing broader materiality can only justify a separate atom design "
            "review. It does not authorize atom promotion, CAMP retraining, "
            "Full36, formal seeds, or online selector changes."
        ),
    }


def _safety_score_evaluation_boundary() -> dict[str, Any]:
    return {
        "allowed": [
            "record fixed reward_config safety-score context after selector-equivalence passes",
            "use safety-score summaries only to detect logging-induced regressions or missing coverage",
            "keep SafetyCost and closed-loop outcomes out of candidate-set consensus coefficients",
        ],
        "forbidden": [
            "claim CAMP is better than DP Top-1 from this plan or materiality gate",
            "choose lambda, promote atoms, or train CAMP from safety-score outcomes",
            "use outcome metrics as online selector inputs",
            "consume formal seeds 11/12/13",
        ],
    }


def _artifact_recording(spec: BroaderMaterialitySpec) -> dict[str, Any]:
    return {
        "remote_artifact_root_template": (
            "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/"
            "candidate_set_consensus_broader_nonformal_materiality_plan_<camp_short_sha>"
        ),
        "planned_output_files": [
            "candidate_set_consensus_broader_nonformal_materiality_plan.json",
            "candidate_set_consensus_broader_nonformal_materiality_plan.md",
            "run_candidate_set_consensus_broader_nonformal_materiality.sh",
            "SHA256SUMS",
            "HEADS.txt",
        ],
        "sha_recording_command": (
            "sha256sum candidate_set_consensus_broader_nonformal_materiality_plan.json "
            "candidate_set_consensus_broader_nonformal_materiality_plan.md "
            "run_candidate_set_consensus_broader_nonformal_materiality.sh > SHA256SUMS"
        ),
        "head_recording": [
            f"git -C {spec.camp_repo} rev-parse HEAD",
            f"git -C {spec.camp_repo} rev-parse origin/main",
            f"git -C {spec.diffusion_repo} rev-parse HEAD",
        ],
    }


def _commands(spec: BroaderMaterialitySpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    candidate_root = f"{spec.root}/logging_enabled"
    audit_root = f"{spec.root}/audit"
    paired_replays = []
    for run in spec.runs:
        paired_replays.append(
            {
                "run_id": run.run_id,
                "variant": "baseline",
                "command": _runner_command(
                    spec,
                    run,
                    f"{baseline_root}/{run.run_id}",
                    logging=False,
                ),
            }
        )
        paired_replays.append(
            {
                "run_id": run.run_id,
                "variant": "logging_enabled",
                "command": _runner_command(
                    spec,
                    run,
                    f"{candidate_root}/{run.run_id}",
                    logging=True,
                ),
            }
        )
    return {
        "camp_sync": _camp_sync_command(spec),
        "asset_audit": _asset_audit_command(spec),
        "head_audit": _head_audit_command(spec),
        "paired_replays": paired_replays,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            candidate_root,
            audit_root,
        ),
        "payload_audit": _payload_audit_command(
            baseline_root,
            candidate_root,
            audit_root,
            spec,
        ),
        "dataset_audit": _dataset_audit_command(candidate_root, audit_root, spec),
    }


def _camp_sync_command(spec: BroaderMaterialitySpec) -> list[str]:
    return ["git", "-C", spec.camp_repo, "pull", "--ff-only", "origin", "main"]


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
    return ["/bin/bash", "-lc", f"{tests} && echo candidate_set_consensus_assets_ok"]


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


def _runner_command(
    spec: BroaderMaterialitySpec,
    run: EvidenceRunSpec,
    output_dir: str,
    *,
    logging: bool,
) -> list[str]:
    command = [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "REPLAY_NO_PNG=1",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "--diffusion_repo",
        spec.diffusion_repo,
        "--map_path",
        run.map_path,
        "--route",
        run.route,
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
        str(run.seed),
        "--max_npcs",
        str(run.max_npcs),
        "--spawn_probability",
        str(run.spawn_probability),
        "--traffic_lights",
        run.traffic_lights,
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
    ]
    if logging:
        command.extend(
            [
                "--camp_candidate_set_consensus_payload_logging",
                "--camp_candidate_set_consensus_payload_steps",
                str(spec.payload_steps),
            ]
        )
    return command


def _selector_equivalence_command(
    baseline_root: str,
    candidate_root: str,
    audit_root: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/compare_diffusion_planner_selector_logs.py",
        "--baseline_root",
        baseline_root,
        "--candidate_root",
        candidate_root,
        "--output_json",
        f"{audit_root}/selector_equivalence.json",
        "--require_equivalent",
    ]


def _payload_audit_command(
    baseline_root: str,
    candidate_root: str,
    audit_root: str,
    spec: BroaderMaterialitySpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_payload_smoke.py",
        "--baseline_root",
        baseline_root,
        "--candidate_root",
        candidate_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--min_available_records",
        str(spec.min_available_records),
        "--output_json",
        f"{audit_root}/candidate_set_consensus_payload_audit.json",
        "--output_md",
        f"{audit_root}/candidate_set_consensus_payload_audit.md",
        "--require_pass",
    ]


def _dataset_audit_command(
    candidate_root: str,
    audit_root: str,
    spec: BroaderMaterialitySpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--root",
        candidate_root,
        "--atom_scales",
        spec.atom_scales,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_candidates",
        str(spec.num_candidates),
        "--expected_advance_mode",
        "perfect",
        "--closed_loop_outcome_policy",
        "forbidden",
        "--forbid_seed",
        "11",
        "--forbid_seed",
        "12",
        "--forbid_seed",
        "13",
        "--require_finite_candidate_contract",
        "--output_json",
        f"{audit_root}/dataset_audit.json",
    ]


def _accept_criteria(spec: BroaderMaterialitySpec) -> list[str]:
    return [
        "plan-only source gate passes from the tiny materiality diagnosis",
        "route/seed matrix is exactly predeclared and contains no formal seed 11/12/13",
        "sample-map traffic-light/turn, sample-map normal, and nishishinjuku release/lane-change assets are declared",
        "future execution, if separately accepted, first passes CAMP sync, asset audit, and fixed DP head audit",
        "future paired baseline/logging-enabled logs pass exact selector equivalence",
        f"future baseline summaries report {SUMMARY_KEY}.enabled=false and logging-enabled summaries report enabled=true",
        "future payload audit finds no future-outcome leakage and no selection effect",
        f"future payload latency max is <= {MAX_PAYLOAD_LATENCY_MS} ms",
        "future dataset audit forbids closed-loop candidate outcomes and formal seeds",
        "spread, rank, and sensitivity diagnostics are reported overall and by required route bucket",
        "future broader materiality, if positive, only authorizes a separate atom-design review",
    ]


def _reject_criteria() -> list[str]:
    return [
        "tiny materiality source is not ready or does not authorize this plan-only next step",
        "any planned run uses formal seed 11, 12, or 13",
        "any required route, scenario bucket, traffic-light mode, or nishishinjuku asset is missing",
        "CAMP or DP head audit fails before any later execution",
        "any selector-equivalence mismatch appears between baseline and logging-enabled roots",
        "payload logging changes scores, atoms, feasibility, selected indices, fallback behavior, or outcomes",
        "payload latency exceeds the predeclared budget",
        "spread/rank/sensitivity diagnostics are absent or fail required-bucket coverage",
        "any result is used to claim CAMP improves over DP Top-1",
        "any atom promotion, CAMP retraining, Full36, formal seeds, online selector change, DP modification, or classical Benders claim is proposed from this gate",
    ]


def _bucket_counts(spec: BroaderMaterialitySpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _route_counts(spec: BroaderMaterialitySpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        counts[run.route_name] = counts.get(run.route_name, 0) + 1
    return counts


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_gte(name: str, observed: Any, expected: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("-inf")
    return {
        "name": name,
        "observed": observed,
        "expected": f">= {expected}",
        "passed": value >= expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {"name": name, "observed": value, "expected": [], "passed": len(value) == 0}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
