#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    BroaderMaterialitySpec,
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


SOURCE_REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_rejected"
)
READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_availability_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_availability_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_existing_source_search_only"
)

DEFAULT_CANDIDATE_ROOT = (
    "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality/"
    "logging_enabled"
)
DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
LOG_NAME = "camp_selection_log.json"

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
            "Plan-only outcome-label availability gate after a read-only "
            "safety-score evaluation rejected because candidate outcomes were "
            "missing. It inspects coverage and emits a source-search plan; it "
            "does not generate labels or run replay."
        )
    )
    parser.add_argument("--safety_execution_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, default=Path(DEFAULT_CANDIDATE_ROOT))
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        safety_execution=_load_json(args.safety_execution_json),
        candidate_root=args.candidate_root,
        label=args.label,
        paths={"safety_execution_json": str(args.safety_execution_json)},
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
    safety_execution: dict[str, Any],
    candidate_root: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
    broader_spec: BroaderMaterialitySpec = BroaderMaterialitySpec(),
) -> dict[str, Any]:
    source = _source_summary(safety_execution)
    availability = _candidate_root_availability(candidate_root)
    plan = _availability_plan(
        availability=availability,
        broader_spec=broader_spec,
        candidate_root=candidate_root,
    )
    checks = [
        *_source_checks(source),
        *_availability_checks(availability, plan),
        *_plan_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_availability_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only gate for resolving missing candidate-level outcome "
                "labels after safety-score evaluation rejection"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "outcome_label_generation": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(availability["formal_seed_log_count"]),
            "paths": paths or {},
            "math_boundary": (
                "This plan may inspect log schemas and artifact metadata only. "
                "It does not produce candidate_closed_loop_outcomes, does not "
                "execute replay or DP, and does not compute SafetyCost v1. A "
                "future label source, if found, must be matched to fixed "
                "run_id, record_index, candidate_count, and candidate ordering "
                "before it can be used as offline labels after shadow selected "
                "indices are fixed. Outcome labels remain forbidden for atom "
                "definition, lambda selection, online scoring, CAMP training, "
                "and any DP-side classical Benders claim."
            ),
        },
        "source_summary": source,
        "current_candidate_root_availability": availability,
        "outcome_label_availability_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    availability = report["current_candidate_root_availability"]
    plan = report["outcome_label_availability_plan"]
    lines = [
        "# Candidate-Set Consensus Outcome-Label Availability Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Existing source search authorized: `{decision['outcome_label_existing_source_search_authorized']}`",
        f"- Outcome-label generation authorized: `{decision['outcome_label_generation_authorized']}`",
        f"- Replay authorized: `{decision['new_replay_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Current Availability",
        "",
        f"- Candidate root: `{availability['root']}`",
        f"- Logs: `{availability['log_count']}`",
        f"- Records: `{availability['records']}`",
        f"- Candidate-count-compatible records: `{availability['candidate_count_compatible_records']}`",
        f"- Outcome-label records: `{availability['candidate_closed_loop_outcome_records']}`",
        f"- Planned-red records: `{availability['planned_red_records']}`",
        f"- Formal seed logs: `{availability['formal_seed_log_count']}`",
        "",
        "## Source Search Plan",
        "",
        "This plan authorizes only existing-source search.",
        "",
    ]
    for item in plan["existing_source_search_plan"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Guarded Label-Pass Outline",
            "",
        ]
    )
    for item in plan["guarded_label_pass_outline"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize replay, label generation, CAMP "
            "training, atom promotion, formal seeds, online selector changes, "
            "safety-benefit claims, DP modification, or a DP-side classical "
            "Benders claim.",
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
    summary = _dict(report.get("evaluation_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    failed_checks = list(decision.get("failed_checks") or [])
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failed_checks": failed_checks,
        "outcome_label_failure": "all_records_have_outcome_labels" in failed_checks,
        "safety_score_evaluation_ready": bool(
            decision.get("safety_score_evaluation_ready")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "records": _optional_int(summary.get("records")),
        "valid_records": _optional_int(summary.get("valid_records")),
        "outcome_available_records": _optional_int(
            summary.get("outcome_available_records")
        ),
        "formal_seed_log_count": _optional_int(summary.get("formal_seed_log_count")),
        "record_error_counts": dict(summary.get("record_error_counts") or {}),
    }


def _candidate_root_availability(root: Path) -> dict[str, Any]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    records = 0
    candidate_count_compatible = 0
    outcome_records = 0
    complete_outcome_records = 0
    planned_red_records = 0
    formal_paths = []
    run_ids = []
    errors = []
    missing_examples = []
    for path in paths:
        run_id = path.parent.name
        run_ids.append(run_id)
        if _contains_formal_seed(f"{run_id} {path}"):
            formal_paths.append(str(path))
        try:
            payload = _load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        if not isinstance(payload, list):
            errors.append(f"{path}: not_json_list")
            continue
        for index, row in enumerate(payload):
            if not isinstance(row, dict):
                continue
            records += 1
            if _candidate_count(row) == EXPECTED_CANDIDATES:
                candidate_count_compatible += 1
            outcomes = row.get("candidate_closed_loop_outcomes")
            if isinstance(outcomes, list):
                outcome_records += 1
                if _outcomes_complete(outcomes, EXPECTED_CANDIDATES):
                    complete_outcome_records += 1
                elif len(missing_examples) < 5:
                    missing_examples.append(f"{path} record {index}: incomplete outcomes")
            elif len(missing_examples) < 5:
                missing_examples.append(f"{path} record {index}: outcomes missing")
            if isinstance(row.get("candidate_horizon_union_planned_red_light_cost"), list) or isinstance(
                row.get("candidate_full_horizon_planned_red_light_cost"),
                list,
            ):
                planned_red_records += 1
    return {
        "root": str(root),
        "log_count": len(paths),
        "records": records,
        "run_ids": run_ids,
        "candidate_count_compatible_records": candidate_count_compatible,
        "candidate_closed_loop_outcome_records": outcome_records,
        "candidate_closed_loop_outcome_complete_records": complete_outcome_records,
        "planned_red_records": planned_red_records,
        "formal_seed_log_count": len(formal_paths),
        "formal_seed_log_paths": formal_paths,
        "errors": errors,
        "missing_examples": missing_examples,
    }


def _availability_plan(
    *,
    availability: dict[str, Any],
    broader_spec: BroaderMaterialitySpec,
    candidate_root: Path,
) -> dict[str, Any]:
    route_rows = [
        {
            "run_id": run.run_id,
            "map_name": run.map_name,
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
        "candidate_root": str(candidate_root),
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "fixed_dp_head": EXPECTED_DP_HEAD,
        "route_seed_matrix": route_rows,
        "required_outcome_fields": list(REQUIRED_OUTCOME_FIELDS),
        "existing_source_search_authorized": True,
        "outcome_label_generation_authorized": False,
        "replay_authorized": False,
        "existing_source_search_roots": [
            DEFAULT_DEVELOPMENT_ROOT,
            "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality",
            "/root/autodl-tmp/camp_dp_assets",
        ],
        "existing_source_search_plan": [
            "read-only scan for camp_selection_log.json files with complete candidate_closed_loop_outcomes",
            "require exact run_id match to the six broader nonformal runs",
            "require exactly 60 records and 8 candidate outcomes per record",
            "require no formal seed 11/12/13 in path, run id, metadata, or route matrix",
            "require candidate ordering compatibility before attaching or reusing labels",
            "write JSON/markdown/HEADS/SHA256SUMS source-search artifact",
            "if no compatible source exists, stop and design a guarded outcome-label pass consideration",
        ],
        "guarded_label_pass_outline": [
            "not authorized by this plan",
            "would need a separate guard before any DP/replay execution",
            "would use the same six nonformal route/seed/NPC/traffic-light/static settings",
            "would collect candidate_closed_loop_outcomes as offline labels only",
            "would preserve fixed shadow-selection artifact semantics and never use labels for online scoring",
        ],
        "accept_criteria": [
            "source safety-score execution rejected specifically because outcome labels are missing",
            "current candidate root still has 6 logs, 60 records, and no formal seeds",
            "current candidate root has zero complete candidate_closed_loop_outcomes records",
            "plan authorizes only read-only existing-source search",
            "plan records exact compatibility and SHA/HEADS requirements",
        ],
        "reject_criteria": [
            "source rejection was caused by safety degradation rather than missing labels",
            "current candidate root has formal seeds or unexpected route/log count",
            "candidate-count compatibility is not 60/60",
            "plan authorizes replay, label generation, training, online selection, or DP modification",
        ],
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_REJECT_STATUS),
        _check_equal("source_passed_false", source["passed"], False),
        _check_equal("source_no_next_work", source["authorized_next_work"], None),
        _check_equal("source_outcome_label_failure", source["outcome_label_failure"], True),
        _check_equal("source_records", source["records"], EXPECTED_RECORDS),
        _check_equal("source_valid_records_zero", source["valid_records"], 0),
        _check_equal("source_outcome_available_zero", source["outcome_available_records"], 0),
        _check_equal("source_formal_seed_logs_zero", source["formal_seed_log_count"], 0),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _availability_checks(
    availability: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    route_seed_conflicts = sorted(
        set(run["seed"] for run in plan["route_seed_matrix"]) & set(FORMAL_SEEDS)
    )
    return [
        _check_equal("candidate_log_count", availability["log_count"], EXPECTED_LOGS),
        _check_equal("candidate_record_count", availability["records"], EXPECTED_RECORDS),
        _check_equal("candidate_no_formal_seed_logs", availability["formal_seed_log_count"], 0),
        _check_equal("candidate_errors_empty", availability["errors"], []),
        _check_equal(
            "candidate_count_compatible",
            availability["candidate_count_compatible_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "candidate_outcome_records_absent",
            availability["candidate_closed_loop_outcome_records"],
            0,
        ),
        _check_equal("candidate_planned_red_present", availability["planned_red_records"], EXPECTED_RECORDS),
        _check_equal("route_seeds_nonformal", route_seed_conflicts, []),
        _check_equal(
            "candidate_run_ids_match_plan",
            sorted(availability["run_ids"]),
            sorted(run["run_id"] for run in plan["route_seed_matrix"]),
        ),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        plan["existing_source_search_plan"]
        + plan["guarded_label_pass_outline"]
        + plan["accept_criteria"]
        + plan["reject_criteria"]
    ).lower()
    return [
        _check_equal("plan_only", plan["plan_only"], True),
        _check_equal("plan_expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("plan_expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal("plan_expected_candidates", plan["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("plan_fixed_dp_head", plan["fixed_dp_head"], EXPECTED_DP_HEAD),
        _check_equal("plan_source_search_authorized", plan["existing_source_search_authorized"], True),
        _check_equal("plan_label_generation_not_authorized", plan["outcome_label_generation_authorized"], False),
        _check_equal("plan_replay_not_authorized", plan["replay_authorized"], False),
        _check_equal("plan_requires_exact_match", "exact run_id match" in text, True),
        _check_equal("plan_requires_candidate_ordering", "candidate ordering" in text, True),
        _check_equal("plan_requires_sha_heads", "sha256sums" in text and "heads" in text, True),
        _check_equal("plan_blocks_formal_seeds", "formal seed" in text, True),
        _check_equal("plan_blocks_online_scoring", "online scoring" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "outcome_label_availability_plan_ready": passed,
        "outcome_label_existing_source_search_authorized": passed,
        "outcome_label_generation_authorized": False,
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


def _candidate_count(row: dict[str, Any]) -> int | None:
    direct = _optional_int(row.get("num_candidates"))
    if direct is not None:
        return direct
    payload = _dict(row.get("candidate_set_consensus_payload_logging"))
    return _optional_int(payload.get("candidate_count"))


def _outcomes_complete(outcomes: list[Any], expected_candidates: int) -> bool:
    if len(outcomes) != expected_candidates:
        return False
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            return False
        if outcome.get("candidate_index", index) != index:
            return False
        if any(field not in outcome for field in REQUIRED_OUTCOME_FIELDS):
            return False
    return True


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
