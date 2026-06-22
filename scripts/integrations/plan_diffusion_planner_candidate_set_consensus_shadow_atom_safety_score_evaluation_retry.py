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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_source import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_consideration_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_consideration_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_authorization_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SOURCE_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review_17b9ee08f"
)
DEFAULT_WEIGHT_SENSITIVITY_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_weight_sensitivity_b373e0cdd"
)
DEFAULT_LABEL_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_candidate_set_consensus_shadow_atom_safety_score_outcome_labels"
)

SOURCE_REVIEW_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_outcome_label_source_review.json"
)
WEIGHT_SENSITIVITY_JSON = "candidate_set_consensus_shadow_atom_weight_sensitivity.json"
EVALUATOR_SCRIPT = (
    "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_evaluation.py"
)

BLOCKED_ACTIONS = (
    "label_attachment_authorized",
    "safety_score_evaluation_retry_authorized",
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
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
            "Plan-only gate for a future read-only safety-score evaluation "
            "retry using the reviewed compatible outcome-label source. It "
            "does not execute the retry, attach labels to prior artifacts, "
            "train CAMP, promote an atom, use formal seeds, change online "
            "selection, run replay, or modify DP."
        )
    )
    parser.add_argument(
        "--source_review_json",
        type=Path,
        default=Path(DEFAULT_SOURCE_REVIEW_ROOT) / SOURCE_REVIEW_JSON,
    )
    parser.add_argument(
        "--weight_sensitivity_json",
        type=Path,
        default=Path(DEFAULT_WEIGHT_SENSITIVITY_ROOT) / WEIGHT_SENSITIVITY_JSON,
    )
    parser.add_argument("--label_root", default=DEFAULT_LABEL_ROOT)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_review=_load_json(args.source_review_json),
        source_review_json=str(args.source_review_json),
        weight_sensitivity_json=str(args.weight_sensitivity_json),
        label_root=args.label_root,
        label=args.label,
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
    source_review: dict[str, Any],
    source_review_json: str = f"{DEFAULT_SOURCE_REVIEW_ROOT}/{SOURCE_REVIEW_JSON}",
    weight_sensitivity_json: str = (
        f"{DEFAULT_WEIGHT_SENSITIVITY_ROOT}/{WEIGHT_SENSITIVITY_JSON}"
    ),
    label_root: str = DEFAULT_LABEL_ROOT,
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_summary(source_review)
    plan = _retry_plan(
        source=source,
        source_review_json=source_review_json,
        weight_sensitivity_json=weight_sensitivity_json,
        label_root=label_root,
    )
    checks = [
        *_source_decision_checks(source),
        *_source_review_checks(source),
        *_scope_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_"
                "safety_score_evaluation_retry_consideration_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only boundary for a future read-only safety-score "
                "evaluation retry using reviewed compatible outcome labels"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_score_evaluation_retry_executed": False,
            "label_attachment": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(source["formal_seed_log_count"]),
            "math_boundary": (
                "The future retry may read candidate_closed_loop_outcomes only "
                "as posterior offline labels after shadow selected indices are "
                "already fixed by the prior weight-sensitivity artifact. It "
                "must not use outcomes, progress, comfort, red-light, "
                "collision, near-miss, lane-violation, or SafetyCost v1 fields "
                "to define atoms, fit weights, choose lambda, score candidates "
                "online, train CAMP, or modify DP. DP remains a black-box "
                "finite candidate generator. The affine score form "
                "score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master "
                "remain unchanged. This plan constructs no DP-side classical "
                "Benders master/subproblem, dual, or valid cuts."
            ),
        },
        "source_summary": source,
        "retry_consideration_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["retry_consideration_plan"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Evaluation Retry Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Retry authorization gate authorized: `{decision['safety_score_evaluation_retry_authorization_gate_authorized']}`",
        f"- Safety-score retry execution authorized: `{decision['safety_score_evaluation_retry_authorized']}`",
        f"- Label attachment authorized: `{decision['label_attachment_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Review",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source passed: `{source['passed']}`",
        f"- Source authorized next work: `{source['authorized_next_work']}`",
        f"- Run count: `{source['run_count']}`",
        f"- Records compared: `{source['records_compared']}`",
        f"- Compatibility mismatches: `{source['compatibility_mismatch_count']}`",
        f"- Label complete outcome records: `{source['label_complete_outcome_records']}`",
        f"- Broader outcome records present: `{source['broader_outcome_records_present']}`",
        f"- Payload no-leak records: `{source['payload_no_leak_records']}`",
        f"- Formal seed logs: `{source['formal_seed_log_count']}`",
        "",
        "## Planned Retry Inputs",
        "",
        f"- Source review JSON: `{plan['source_review_json']}`",
        f"- Weight-sensitivity JSON: `{plan['weight_sensitivity_json']}`",
        f"- Label root as evaluator candidate root: `{plan['label_root']}`",
        f"- Evaluator script: `{plan['evaluator_script']}`",
        f"- Fixed DP HEAD: `{plan['fixed_dp_head']}`",
        "",
        "## Route/Seed Matrix",
        "",
        "| Run | Seed | Buckets | Formal |",
        "| --- | ---: | --- | --- |",
    ]
    for run in plan["route_seed_matrix"]:
        lines.append(
            f"| `{run['run_id']}` | `{run['seed']}` | "
            f"`{', '.join(run['scenario_buckets'])}` | `{run['formal']}` |"
        )
    lines.extend(["", "## Required Future Authorization Checks", ""])
    for item in plan["required_authorization_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Accept Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Reject Criteria", ""])
    for item in plan["reject_criteria"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not execute the retry and does not attach labels to "
            "prior broader artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    review = _dict(report.get("source_review"))
    run_ids = [str(run_id) for run_id in review.get("run_ids") or []]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "outcome_label_source_review_ready": bool(
            decision.get("outcome_label_source_review_ready")
        ),
        "safety_score_evaluation_retry_plan_authorized": bool(
            decision.get("safety_score_evaluation_retry_plan_authorized")
        ),
        "label_attachment_authorized": bool(
            decision.get("label_attachment_authorized")
        ),
        "safety_score_evaluation_retry_authorized": bool(
            decision.get("safety_score_evaluation_retry_authorized")
        ),
        "blocked_actions_true": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "label_root": review.get("label_root"),
        "broader_candidate_root": review.get("broader_candidate_root"),
        "run_count": _int(review.get("run_count")),
        "run_ids": run_ids,
        "label_records": _int(review.get("label_records")),
        "broader_records": _int(review.get("broader_records")),
        "records_compared": _int(review.get("records_compared")),
        "compatibility_mismatch_count": _int(
            review.get("compatibility_mismatch_count")
        ),
        "label_complete_outcome_records": _int(
            review.get("label_complete_outcome_records")
        ),
        "broader_outcome_records_present": _int(
            review.get("broader_outcome_records_present")
        ),
        "payload_no_leak_records": _int(review.get("payload_no_leak_records")),
        "formal_seed_log_count": _int(review.get("formal_seed_log_count")),
        "errors": list(review.get("errors") or []),
    }


def _retry_plan(
    *,
    source: dict[str, Any],
    source_review_json: str,
    weight_sensitivity_json: str,
    label_root: str,
) -> dict[str, Any]:
    route_seed_matrix = [_route_seed_row(run_id) for run_id in source["run_ids"]]
    command = [
        "python",
        EVALUATOR_SCRIPT,
        "--weight_sensitivity_json",
        weight_sensitivity_json,
        "--candidate_root",
        label_root,
        "--label",
        "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry",
        "--output_json",
        "<artifact_root>/candidate_set_consensus_shadow_atom_safety_score_evaluation_retry.json",
        "--output_md",
        "<artifact_root>/candidate_set_consensus_shadow_atom_safety_score_evaluation_retry.md",
        "--require_pass",
    ]
    return {
        "source_review_json": source_review_json,
        "weight_sensitivity_json": weight_sensitivity_json,
        "label_root": label_root,
        "evaluator_script": EVALUATOR_SCRIPT,
        "future_evaluator_command": command,
        "fixed_dp_head": EXPECTED_DP_HEAD,
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "route_seed_matrix": route_seed_matrix,
        "scenario_coverage": _scenario_coverage(route_seed_matrix),
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "uses_reviewed_label_source_as_candidate_root": True,
        "attaches_labels_to_prior_artifacts": False,
        "runs_new_replay": False,
        "modifies_dp": False,
        "trains_camp": False,
        "promotes_atom": False,
        "changes_online_selector": False,
        "required_authorization_checks": [
            "source review JSON/MD/HEADS/SHA256SUMS exist and SHA256SUMS match",
            "CAMP local, origin/main, and AutoDL HEADs are identical before execution",
            f"AutoDL DP HEAD remains {EXPECTED_DP_HEAD}",
            "label root contains the same six nonformal run IDs and 60 complete outcome records",
            "weight-sensitivity artifact is unchanged and provides fixed shadow selected indices",
            "formal seed strings seed11, seed12, and seed13 are absent from planned inputs",
            "the evaluator candidate_root is the reviewed label root, not a mutated broader artifact",
            "the retry output root records JSON, markdown, HEADS, SHA256SUMS, and command log",
        ],
        "accept_criteria": [
            "all source-review readiness checks pass",
            "route/seed matrix remains nonformal and covers traffic-light, turn, and normal buckets",
            "payload no-leak count equals all 60 compared records",
            "future retry remains read-only and offline with no online selector effect",
            "future retry computes only diagnostic SafetyCost v1 deltas after fixed shadow selection",
        ],
        "reject_criteria": [
            "source-review status is not ready or does not authorize this plan-only gate",
            "any compatibility mismatch, missing label outcome, or broader outcome label is detected",
            "any formal seed 11/12/13 path, run ID, or log is detected",
            "any plan path would attach labels to prior broader artifacts",
            "any gate attempts to train CAMP, promote an atom, enable online selection, run replay, or modify DP",
        ],
    }


def _source_decision_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_REVIEW_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_retry_plan",
            source["authorized_next_work"],
            SOURCE_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "source_review_ready",
            source["outcome_label_source_review_ready"],
            True,
        ),
        _check_equal(
            "source_retry_plan_authorized",
            source["safety_score_evaluation_retry_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_label_attachment_not_authorized",
            source["label_attachment_authorized"],
            False,
        ),
        _check_equal(
            "source_retry_execution_not_authorized",
            source["safety_score_evaluation_retry_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_actions_true"], []),
    ]


def _source_review_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("review_run_count", source["run_count"], EXPECTED_LOGS),
        _check_equal("review_label_records", source["label_records"], EXPECTED_RECORDS),
        _check_equal(
            "review_broader_records",
            source["broader_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "review_records_compared",
            source["records_compared"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "review_compatibility_mismatches_zero",
            source["compatibility_mismatch_count"],
            0,
        ),
        _check_equal(
            "review_label_complete_outcomes",
            source["label_complete_outcome_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "review_broader_outcomes_absent",
            source["broader_outcome_records_present"],
            0,
        ),
        _check_equal(
            "review_payload_no_leak_all_records",
            source["payload_no_leak_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "review_no_formal_seed_logs",
            source["formal_seed_log_count"],
            0,
        ),
        _check_equal("review_errors_empty", source["errors"], []),
    ]


def _scope_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = plan["route_seed_matrix"]
    coverage = plan["scenario_coverage"]
    return [
        _check_equal("scope_expected_logs", len(matrix), EXPECTED_LOGS),
        _check_equal(
            "scope_no_formal_seed_runs",
            [row["run_id"] for row in matrix if row["formal"]],
            [],
        ),
        _check_equal(
            "scope_traffic_light_covered",
            bool(coverage["traffic_light"]),
            True,
        ),
        _check_equal("scope_turn_covered", bool(coverage["turn"]), True),
        _check_equal("scope_normal_covered", bool(coverage["normal"]), True),
        _check_equal(
            "scope_uses_label_root_as_candidate_root",
            plan["uses_reviewed_label_source_as_candidate_root"],
            True,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("boundary_no_label_attachment", plan["attaches_labels_to_prior_artifacts"], False),
        _check_equal("boundary_no_new_replay", plan["runs_new_replay"], False),
        _check_equal("boundary_no_dp_modification", plan["modifies_dp"], False),
        _check_equal("boundary_no_camp_training", plan["trains_camp"], False),
        _check_equal("boundary_no_atom_promotion", plan["promotes_atom"], False),
        _check_equal("boundary_no_online_selector_change", plan["changes_online_selector"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_retry_plan_ready": passed,
        "safety_score_evaluation_retry_authorization_gate_authorized": passed,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
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


def _route_seed_row(run_id: str) -> dict[str, Any]:
    seed = _seed_from_run_id(run_id)
    buckets: list[str] = []
    lower = run_id.lower()
    if "tl" in lower or "tlon" in lower:
        buckets.append("traffic_light")
    if "normal" in lower:
        buckets.append("normal")
    if "lanechange" in lower:
        buckets.append("lane_change")
    if "nishi" in lower:
        buckets.append("nishishinjuku")
    if "normal" not in lower:
        buckets.append("turn")
    return {
        "run_id": run_id,
        "seed": seed,
        "scenario_buckets": sorted(set(buckets)),
        "formal": seed in FORMAL_SEEDS or _contains_formal_seed(run_id),
    }


def _scenario_coverage(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    coverage = {
        "traffic_light": [],
        "turn": [],
        "normal": [],
        "nishishinjuku": [],
    }
    for row in rows:
        for bucket in coverage:
            if bucket in row["scenario_buckets"]:
                coverage[bucket].append(row["run_id"])
    return coverage


def _seed_from_run_id(run_id: str) -> int | None:
    match = re.search(r"(?<!\d)seed[-_]?(\d+)(?!\d)", run_id.lower())
    if not match:
        return None
    return int(match.group(1))


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
