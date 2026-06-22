#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    REQUIRED_OUTCOME_FIELDS,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SAFETY_COST_V1_ALPHA,
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_NO_WORSE_METRICS,
    SAFETY_COST_V1_WEIGHTS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    BroaderMaterialitySpec,
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    ATOM_NAME,
    COEFFICIENT_FIELD,
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
    PAYLOAD_KEY,
)


SOURCE_READY_STATUS = "candidate_set_consensus_shadow_atom_weight_sensitivity_ready"
SOURCE_READY_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_weight_sensitivity_result_review_only"
)
READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_"
    "implementation_unit_tests_only"
)

DEFAULT_REPLAY_ROOT = (
    "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality"
)
DEFAULT_CANDIDATE_ROOT = f"{DEFAULT_REPLAY_ROOT}/logging_enabled"
DEFAULT_AUDIT_ROOT = f"{DEFAULT_REPLAY_ROOT}/audit"
DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_WEIGHT_SENSITIVITY_ARTIFACT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_weight_sensitivity_b373e0cdd"
)

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
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a future read-only safety-score evaluation of "
            "candidate-set consensus shadow atom weight sensitivity. It does "
            "not execute the evaluation, run replay, train CAMP, promote an "
            "atom, change online selection, use formal seeds, or modify DP."
        )
    )
    parser.add_argument("--weight_sensitivity_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--candidate_root", default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--audit_root", default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        weight_sensitivity=_load_json(args.weight_sensitivity_json),
        label=args.label,
        candidate_root=args.candidate_root,
        audit_root=args.audit_root,
        paths={"weight_sensitivity_json": str(args.weight_sensitivity_json)},
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
    weight_sensitivity: dict[str, Any],
    label: str | None = None,
    candidate_root: str = DEFAULT_CANDIDATE_ROOT,
    audit_root: str = DEFAULT_AUDIT_ROOT,
    paths: dict[str, str] | None = None,
    broader_spec: BroaderMaterialitySpec = BroaderMaterialitySpec(),
) -> dict[str, Any]:
    source = _source_summary(weight_sensitivity)
    plan = _evaluation_plan(
        source=source,
        candidate_root=candidate_root,
        audit_root=audit_root,
        broader_spec=broader_spec,
    )
    checks = [
        *_source_checks(source),
        *_scope_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_"
                "safety_score_evaluation_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only safety-score evaluation boundary after broader-log "
                "candidate-set consensus shadow atom weight sensitivity"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_score_execution": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "The planned evaluation may read safety and outcome labels only "
                "after the shadow selected index has been fixed by the already "
                "completed lambda-grid sensitivity artifact. It must not use "
                "candidate_closed_loop_outcomes, SafetyCost v1, progress, "
                "comfort, red-light, collision, near-miss, or lane-violation "
                "fields to define the candidate-set consensus coefficient, "
                "fit weights, alter the atom schema, choose lambda online, or "
                "select candidates online. DP remains a black-box finite "
                "candidate generator, and the diagnostic selector expression "
                "remains score'_k(lambda) = selection_score_k + lambda * "
                "candidate_set_consensus_center_rms_m[k]. This plan constructs "
                "no DP-side classical Benders master/subproblem, dual, or "
                "valid cuts."
            ),
        },
        "source_summary": source,
        "safety_score_evaluation_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["safety_score_evaluation_plan"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Safety-Score Evaluation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Safety-score evaluation implementation authorized: `{decision['safety_score_evaluation_implementation_authorized']}`",
        f"- Safety-score evaluation execution authorized: `{decision['safety_score_evaluation_execution_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source authorized next work: `{source['authorized_next_work']}`",
        f"- Records: `{source['records']}`",
        f"- Valid records: `{source['valid_records']}`",
        f"- Max changed records: `{source['max_changed_records']}`",
        f"- Fallback-retained records: `{source['fallback_retained_records']}`",
        f"- Min critical positive lambda: `{source['min_critical_positive_lambda']}`",
        f"- Formal seed log count: `{source['formal_seed_log_count']}`",
        "",
        "## Planned Scope",
        "",
        f"- Candidate root: `{plan['candidate_root']}`",
        f"- Audit root: `{plan['audit_root']}`",
        f"- Source artifact root: `{plan['source_weight_sensitivity_artifact_root']}`",
        f"- Expected logs: `{plan['expected_logs']}`",
        f"- Expected records: `{plan['expected_records']}`",
        f"- Expected candidates: `{plan['expected_candidates']}`",
        f"- Lambda grid: `{plan['lambda_grid']}`",
        f"- Formal seeds forbidden: `{plan['formal_seeds_forbidden']}`",
        "",
        "## Route/Seed Matrix",
        "",
        "| Run | Route | Seed | NPCs | TL | Buckets |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for run in plan["route_seed_matrix"]:
        lines.append(
            f"| `{run['run_id']}` | `{run['route_name']}` | `{run['seed']}` | "
            f"`{run['max_npcs']}` | `{run['traffic_lights']}` | "
            f"`{', '.join(run['scenario_buckets'])}` |"
        )
    lines.extend(
        [
            "",
            "## Allowed Read-Only Fields",
            "",
        ]
    )
    for field in plan["allowed_read_only_fields"]:
        lines.append(f"- `{field}`")
    lines.extend(
        [
            "",
            "## Required Future Checks",
            "",
        ]
    )
    for item in plan["required_evaluation_checks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize evaluation execution, replay, atom "
            "promotion, CAMP training, Full36, formal seeds, online selector "
            "changes, safety-benefit claims, DP modification, or a DP-side "
            "classical Benders claim.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    summary = _dict(report.get("sensitivity_summary"))
    by_lambda = [_dict(row) for row in summary.get("by_lambda") or []]
    by_run = _dict(summary.get("by_run"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    lambda_grid = _validated_lambda_grid(summary.get("lambda_grid") or report.get("lambda_grid"))
    if not lambda_grid:
        lambda_grid = _validated_lambda_grid(
            [row.get("lambda") for row in by_lambda]
        )
    zero_changed = _changed_for_lambda(by_lambda, 0.0)
    positive_changed = [
        int(row.get("changed_records", 0))
        for row in by_lambda
        if _optional_float(row.get("lambda")) is not None
        and float(row.get("lambda")) > 0.0
    ]
    min_critical = _optional_float(
        summary.get(
            "min_critical_positive_lambda",
            decision.get("min_critical_positive_lambda"),
        )
    )
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "weight_sensitivity_ready": bool(decision.get("weight_sensitivity_ready")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "records": int(summary.get("records", -1)),
        "valid_records": int(summary.get("valid_records", -1)),
        "available_records": int(summary.get("available_records", -1)),
        "log_count": int(summary.get("log_count", -1)),
        "ranking_signal_records": int(summary.get("ranking_signal_records", -1)),
        "fallback_retained_records": int(summary.get("fallback_retained_records", -1)),
        "formal_seed_log_count": int(summary.get("formal_seed_log_count", -1)),
        "record_error_counts": dict(summary.get("record_error_counts") or {}),
        "critical_positive_lambda_records": int(
            summary.get("critical_positive_lambda_records", -1)
        ),
        "min_critical_positive_lambda": min_critical,
        "lambda_grid": lambda_grid,
        "by_lambda": by_lambda,
        "by_run": by_run,
        "max_changed_records": int(
            decision.get(
                "max_changed_records",
                max((int(row.get("changed_records", 0)) for row in by_lambda), default=0),
            )
        ),
        "lambda_zero_changed_records": zero_changed,
        "positive_lambda_changed_records": positive_changed,
    }


def _evaluation_plan(
    *,
    source: dict[str, Any],
    candidate_root: str,
    audit_root: str,
    broader_spec: BroaderMaterialitySpec,
) -> dict[str, Any]:
    route_seed_matrix = [
        {
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
        for run in broader_spec.runs
    ]
    return {
        "plan_only": True,
        "candidate_root": candidate_root,
        "audit_root": audit_root,
        "source_weight_sensitivity_artifact_root": DEFAULT_WEIGHT_SENSITIVITY_ARTIFACT,
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "fixed_dp_head": EXPECTED_DP_HEAD,
        "atom_name": ATOM_NAME,
        "payload_key": PAYLOAD_KEY,
        "coefficient_field": COEFFICIENT_FIELD,
        "lambda_grid": list(source["lambda_grid"]),
        "score_formula": (
            "score_prime_k(lambda) = selection_score_k + lambda * "
            "candidate_set_consensus_center_rms_m[k]"
        ),
        "route_seed_matrix": route_seed_matrix,
        "scenario_coverage": {
            "traffic_light": [
                run["run_id"]
                for run in route_seed_matrix
                if "traffic_light" in run["scenario_buckets"]
            ],
            "turn": [
                run["run_id"]
                for run in route_seed_matrix
                if "sharp_turn" in run["scenario_buckets"]
                or "red_light_turn" in run["scenario_buckets"]
            ],
            "normal": [
                run["run_id"]
                for run in route_seed_matrix
                if "normal" in run["scenario_buckets"]
            ],
            "nishishinjuku": [
                run["run_id"]
                for run in route_seed_matrix
                if run["map_name"] == "nishishinjuku"
            ],
            "lane_change_or_merge": [
                run["run_id"]
                for run in route_seed_matrix
                if "lane_change_or_merge" in run["scenario_buckets"]
            ],
        },
        "assets": {
            "sample_map": (
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            "sample_map_tl_route_59_to_86": (
                "/root/autodl-tmp/camp_dp_assets/"
                "sample_map_tl_route_59_to_86.pkl"
            ),
            "sample_map_route_2_to_104": (
                "/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl"
            ),
            "nishishinjuku_map": (
                "/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm"
            ),
            "nishishinjuku_release_auto_route": (
                "/root/autodl-tmp/camp_dp_assets/"
                "nishishinjuku_release_auto_route.pkl"
            ),
            "nishishinjuku_lane_change_route_7_via_8_to_1": (
                "/root/autodl-tmp/camp_dp_assets/"
                "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
            ),
        },
        "allowed_read_only_fields": _allowed_read_only_fields(),
        "safety_cost_v1_contract": {
            "weights": dict(SAFETY_COST_V1_WEIGHTS),
            "normalization": dict(SAFETY_COST_V1_NORMALIZATION),
            "clip": SAFETY_COST_V1_CLIP,
            "tail_alpha": SAFETY_COST_V1_ALPHA,
            "no_worse_metrics": list(SAFETY_COST_V1_NO_WORSE_METRICS),
            "scope": (
                "SafetyCost v1 offline candidate-branch labels only; not a "
                "closed-loop run-level proof and not an online selector"
            ),
        },
        "evaluation_cohorts": [
            "lambda_changed_records",
            "lambda_unchanged_records",
            "fallback_retained_records",
            "no_change_routes",
            "traffic_light_routes",
            "turn_routes",
            "normal_routes",
            "nishishinjuku_release_route",
            "nishishinjuku_lane_change_route",
        ],
        "diagnostics": [
            "allowed field availability and missing-field counts",
            "changed-record safety-cost deltas versus logged selected branch",
            "unchanged-record control deltas",
            "fallback-retained records reported separately",
            "route-level lambda sensitivity and safety-score heterogeneity",
            "transition-count safety deltas grouped by selected-index transition",
            "progress, comfort, hard-safety, and planned-red components separated",
            "no safety-benefit claim unless a later result-review gate accepts evidence",
        ],
        "fallback_progress_comfort_boundary": {
            "fallback": (
                "all-infeasible or CAMP fallback records remain separate and "
                "cannot be converted into positive safety evidence"
            ),
            "progress": (
                "progress_m and route_shortfall may be evaluated only as "
                "post-selection labels"
            ),
            "comfort": (
                "mean_jerk_mps3 and mean_lateral_acceleration_mps2 may be "
                "reported only as read-only comfort components"
            ),
        },
        "latency_gate": {
            "selector_latency_source": (
                "reuse existing logged p95/selection latency fields if present"
            ),
            "no_new_runtime_benchmark": True,
            "must_not_increase_online_path": True,
        },
        "accept_criteria": [
            "source weight-sensitivity artifact passes all source checks",
            "formal_seed_log_count remains zero and route seeds exclude 11/12/13",
            "future implementation reads existing logs and sensitivity JSON only",
            "lambda-zero selection remains unchanged in the source artifact",
            "positive lambda changed-record cohorts are present and route-separated",
            "allowed safety/outcome fields are read only after shadow selection is fixed",
            "fallback, progress, comfort, and hard-safety components are separated",
            "artifact JSON/markdown/HEADS/SHA256SUMS are recorded before result review",
        ],
        "reject_criteria": [
            "source artifact is rejected, incomplete, or requests a blocked action",
            "any formal seed log or route seed 11/12/13 is detected",
            "lambda-zero changes any selected index",
            "no positive-lambda changed records exist",
            "safety or outcome fields are used for atom definition, lambda selection, or online scoring",
            "route-level or fallback-separated reporting is missing",
            "artifact SHA/HEADS recording is missing",
        ],
        "required_evaluation_checks": [
            "read the completed weight-sensitivity JSON artifact and existing logging_enabled logs only",
            "require exactly 6 nonformal logs, 60 records, and 8 candidates per valid record",
            "reject formal seeds 11, 12, and 13 in paths, run ids, metadata, or route matrix",
            "require lambda 0.0 changed_records == 0 before any safety-score evaluation",
            "require at least one positive lambda with changed_records > 0",
            "evaluate safety labels only after selected indices are fixed by the sensitivity artifact",
            "never use candidate_closed_loop_outcomes or SafetyCost v1 to define the atom, coefficient, weights, lambda, or online selection",
            "keep fallback-retained records, no-change routes, changed records, and unchanged records in separate cohorts",
            "report traffic-light, turn, normal, nishishinjuku release, and nishishinjuku lane-change coverage",
            "report spread/rank/sensitivity diagnostics from the source artifact beside safety deltas",
            "report latency as an existing-log diagnostic only; do not run new replay or benchmark",
            "write JSON, markdown, HEADS.txt, and SHA256SUMS artifacts for result-review only",
        ],
        "commands_if_later_implemented": {
            "implementation_target": (
                "scripts/integrations/analyze_diffusion_planner_candidate_set_"
                "consensus_shadow_atom_safety_score_evaluation.py"
            ),
            "test_target": (
                "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
                "shadow_atom_safety_score_evaluation.py"
            ),
            "cli_shape": [
                "python",
                "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation.py",
                "--weight_sensitivity_json",
                "<candidate_set_consensus_shadow_atom_weight_sensitivity.json>",
                "--candidate_root",
                candidate_root,
                "--output_json",
                f"{audit_root}/candidate_set_consensus_shadow_atom_safety_score_evaluation.json",
                "--output_md",
                f"{audit_root}/candidate_set_consensus_shadow_atom_safety_score_evaluation.md",
            ],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_result_review",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_weight_sensitivity_ready",
            source["weight_sensitivity_ready"],
            True,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_log_count", source["log_count"], EXPECTED_LOGS),
        _check_equal("source_records", source["records"], EXPECTED_RECORDS),
        _check_equal("source_valid_records", source["valid_records"], EXPECTED_RECORDS),
        _check_equal("source_available_records", source["available_records"], EXPECTED_RECORDS),
        _check_equal("source_formal_seed_logs_zero", source["formal_seed_log_count"], 0),
        _check_equal("source_record_errors_empty", source["record_error_counts"], {}),
        _check_equal("source_ranking_signal_present", source["ranking_signal_records"] > 0, True),
        _check_equal("source_fallback_count_reported", source["fallback_retained_records"] >= 0, True),
        _check_equal("source_critical_lambda_present", source["critical_positive_lambda_records"] > 0, True),
        _check_equal(
            "source_min_critical_lambda_positive_finite",
            _finite_positive(source["min_critical_positive_lambda"]),
            True,
        ),
        _check_equal("source_lambda_grid_nonempty", bool(source["lambda_grid"]), True),
        _check_equal("source_lambda_grid_contains_zero", 0.0 in source["lambda_grid"], True),
        _check_equal(
            "source_lambda_grid_has_positive_value",
            any(value > 0.0 for value in source["lambda_grid"]),
            True,
        ),
        _check_equal(
            "source_lambda_grid_sorted_unique",
            source["lambda_grid"] == sorted(set(source["lambda_grid"])),
            True,
        ),
        _check_equal("source_lambda_zero_no_changes", source["lambda_zero_changed_records"], 0),
        _check_equal(
            "source_positive_lambda_changes_present",
            any(value > 0 for value in source["positive_lambda_changed_records"]),
            True,
        ),
        _check_equal("source_max_changed_records_positive", source["max_changed_records"] > 0, True),
        _check_equal("source_route_summary_present", bool(source["by_run"]), True),
    ]


def _scope_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    route_seeds = [int(run["seed"]) for run in plan["route_seed_matrix"]]
    return [
        _check_equal("plan_only", plan["plan_only"], True),
        _check_equal("expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal("expected_candidates", plan["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("formal_seeds_forbidden", plan["formal_seeds_forbidden"], sorted(FORMAL_SEEDS)),
        _check_equal("route_seeds_nonformal", sorted(set(route_seeds) & set(FORMAL_SEEDS)), []),
        _check_equal("fixed_dp_head", plan["fixed_dp_head"], EXPECTED_DP_HEAD),
        _check_equal("candidate_root_is_logging_enabled", plan["candidate_root"].endswith("/logging_enabled"), True),
        _check_equal("audit_root_declared", bool(plan["audit_root"]), True),
        _check_equal("atom_name", plan["atom_name"], ATOM_NAME),
        _check_equal("payload_key", plan["payload_key"], PAYLOAD_KEY),
        _check_equal("coefficient_field", plan["coefficient_field"], COEFFICIENT_FIELD),
        _check_equal("route_seed_matrix_count", len(plan["route_seed_matrix"]), EXPECTED_LOGS),
        _check_equal("traffic_light_coverage_present", bool(plan["scenario_coverage"]["traffic_light"]), True),
        _check_equal("turn_coverage_present", bool(plan["scenario_coverage"]["turn"]), True),
        _check_equal("normal_coverage_present", bool(plan["scenario_coverage"]["normal"]), True),
        _check_equal("nishishinjuku_coverage_present", len(plan["scenario_coverage"]["nishishinjuku"]) >= 2, True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    checks_text = " ".join(plan["required_evaluation_checks"]).lower()
    criteria_text = " ".join(plan["accept_criteria"] + plan["reject_criteria"]).lower()
    field_text = " ".join(plan["allowed_read_only_fields"]).lower()
    diagnostics_text = " ".join(plan["diagnostics"]).lower()
    return [
        _check_equal("allows_closed_loop_outcomes_read_only", "candidate_closed_loop_outcomes" in field_text, True),
        _check_equal("allows_safety_cost_v1_boundary", "safetycost v1" in plan["safety_cost_v1_contract"]["scope"].lower(), True),
        _check_equal("blocks_outcome_selection_leakage", "never use candidate_closed_loop_outcomes" in checks_text, True),
        _check_equal("blocks_atom_definition_leakage", "define the atom" in checks_text, True),
        _check_equal("blocks_online_selection", "online selection" in checks_text, True),
        _check_equal("requires_fallback_separation", "fallback-retained records" in checks_text, True),
        _check_equal("requires_route_reporting", "traffic-light, turn, normal" in checks_text, True),
        _check_equal("requires_spread_rank_sensitivity", "spread/rank/sensitivity" in checks_text, True),
        _check_equal("requires_latency_boundary", "do not run new replay or benchmark" in checks_text, True),
        _check_equal("requires_sha_heads_artifact", "heads.txt" in checks_text and "sha256sums" in checks_text, True),
        _check_equal("blocks_formal_seeds", "formal seed" in criteria_text, True),
        _check_equal("no_execution_command_declared_only", plan["commands_if_later_implemented"]["implementation_target"].endswith("safety_score_evaluation.py"), True),
        _check_equal("progress_comfort_separated", "progress" in diagnostics_text and "comfort" in diagnostics_text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_plan_ready": passed,
        "safety_score_evaluation_implementation_authorized": passed,
        "safety_score_evaluation_execution_authorized": False,
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


def _allowed_read_only_fields() -> list[str]:
    fields = [
        "candidate_closed_loop_outcomes",
        *[f"candidate_closed_loop_outcomes.{name}" for name in REQUIRED_OUTCOME_FIELDS],
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
        "candidate_horizon_union_near_miss_violation_cost",
        "candidate_horizon_union_lane_violation_cost",
        "selection_scores",
        "feasible_mask",
        "selected_index",
        "used_fallback",
        "camp_fallback_mode",
        "p95_selection_latency_ms",
    ]
    return sorted(dict.fromkeys(fields))


def _changed_for_lambda(by_lambda: list[dict[str, Any]], lam: float) -> int | None:
    for row in by_lambda:
        value = _optional_float(row.get("lambda"))
        if value is not None and value == lam:
            try:
                return int(row.get("changed_records"))
            except (TypeError, ValueError):
                return None
    return None


def _validated_lambda_grid(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        parsed = _optional_float(item)
        if parsed is None or not math.isfinite(parsed):
            return []
        result.append(float(parsed))
    return result


def _finite_positive(value: Any) -> bool:
    parsed = _optional_float(value)
    return parsed is not None and math.isfinite(parsed) and parsed > 0.0


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
