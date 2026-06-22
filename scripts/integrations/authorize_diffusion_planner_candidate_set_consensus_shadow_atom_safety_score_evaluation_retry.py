#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as WEIGHT_AUTHORIZED_NEXT_WORK,
    READY_STATUS as WEIGHT_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_retry import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as RETRY_PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as RETRY_PLAN_READY_STATUS,
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
    "evaluation_retry_authorization_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_authorization_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_execution_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_RETRY_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_retry_consideration_plan_cc6c43c"
)
DEFAULT_SOURCE_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_outcome_label_source_review_17b9ee08f"
)
DEFAULT_WEIGHT_SENSITIVITY_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_weight_sensitivity_b373e0cdd"
)
DEFAULT_LABEL_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_candidate_set_consensus_shadow_atom_safety_score_outcome_labels"
)

RETRY_PLAN_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_consideration_plan.json"
)
RETRY_PLAN_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_consideration_plan.md"
)
SOURCE_REVIEW_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review.json"
)
SOURCE_REVIEW_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review.md"
)
WEIGHT_JSON = "candidate_set_consensus_shadow_atom_weight_sensitivity.json"
WEIGHT_MD = "candidate_set_consensus_shadow_atom_weight_sensitivity.md"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"
COMMAND_LOG = "COMMAND.log"
LOG_NAME = "camp_selection_log.json"
EVALUATOR_SCRIPT = (
    "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_evaluation.py"
)
EVALUATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_evaluation.py"
)

BLOCKED_ACTIONS = (
    "label_attachment_authorized",
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
            "Authorization-only gate for the candidate-set consensus "
            "safety-score evaluation retry. It verifies artifact SHA/HEADS, "
            "CAMP/DP heads, label-root availability, nonformal scope, and "
            "evaluator readiness, but does not execute the retry."
        )
    )
    parser.add_argument("--retry_plan_root", type=Path, default=Path(DEFAULT_RETRY_PLAN_ROOT))
    parser.add_argument(
        "--source_review_root",
        type=Path,
        default=Path(DEFAULT_SOURCE_REVIEW_ROOT),
    )
    parser.add_argument(
        "--weight_sensitivity_root",
        type=Path,
        default=Path(DEFAULT_WEIGHT_SENSITIVITY_ROOT),
    )
    parser.add_argument("--label_root", type=Path, default=Path(DEFAULT_LABEL_ROOT))
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        retry_plan_root=args.retry_plan_root,
        source_review_root=args.source_review_root,
        weight_sensitivity_root=args.weight_sensitivity_root,
        label_root=args.label_root,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
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
    retry_plan_root: Path,
    source_review_root: Path,
    weight_sensitivity_root: Path,
    label_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    retry_plan_artifact = _artifact_summary(
        retry_plan_root,
        required_files=(RETRY_PLAN_JSON, RETRY_PLAN_MD, COMMAND_LOG, HEADS, SHA256SUMS),
        json_file=RETRY_PLAN_JSON,
    )
    source_review_artifact = _artifact_summary(
        source_review_root,
        required_files=(SOURCE_REVIEW_JSON, SOURCE_REVIEW_MD, HEADS, SHA256SUMS),
        json_file=SOURCE_REVIEW_JSON,
    )
    weight_artifact = _artifact_summary(
        weight_sensitivity_root,
        required_files=(WEIGHT_JSON, WEIGHT_MD, HEADS, SHA256SUMS),
        json_file=WEIGHT_JSON,
    )
    retry_plan = _retry_plan_summary(retry_plan_artifact.get("json_payload") or {})
    source_review = _source_review_summary(
        source_review_artifact.get("json_payload") or {}
    )
    weight = _weight_summary(weight_artifact.get("json_payload") or {})
    labels = _label_root_summary(label_root)
    implementation = _implementation_summary()
    checks = [
        *_artifact_checks("retry_plan", retry_plan_artifact),
        *_artifact_checks("source_review", source_review_artifact),
        *_artifact_checks("weight_sensitivity", weight_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_retry_plan_checks(retry_plan, label_root),
        *_source_review_checks(source_review),
        *_weight_checks(weight),
        *_label_root_checks(labels, retry_plan, source_review),
        *_implementation_checks(implementation),
        *_boundary_checks(retry_plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_"
                "safety_score_evaluation_retry_authorization_v1"
            ),
            "label": label,
            "role": (
                "authorization-only gate for a later read-only safety-score "
                "evaluation retry"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_score_evaluation_retry_executed": False,
            "label_attachment": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(labels["formal_seed_log_count"]),
            "math_boundary": (
                "This gate verifies evidence and scope only. It does not "
                "execute the evaluator. If authorized, a later retry may read "
                "candidate_closed_loop_outcomes only as offline posterior "
                "labels after shadow selected indices are fixed by the "
                "weight-sensitivity artifact. It must not define atoms, fit "
                "weights, choose lambda, alter online candidate scoring, train "
                "CAMP, modify DP, or claim a DP-side classical Benders "
                "decomposition. The affine score form score_k(w)=a_k^T w and "
                "the convex simplex/CVaR/L2 master remain unchanged."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "retry_plan_artifact": _strip_payload(retry_plan_artifact),
        "source_review_artifact": _strip_payload(source_review_artifact),
        "weight_sensitivity_artifact": _strip_payload(weight_artifact),
        "retry_plan_summary": retry_plan,
        "source_review_summary": source_review,
        "weight_sensitivity_summary": weight,
        "label_root_summary": labels,
        "implementation_summary": implementation,
        "authorization_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    labels = report["label_root_summary"]
    plan = report["retry_plan_summary"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Evaluation Retry Authorization",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Retry execution authorized: `{decision['safety_score_evaluation_retry_execution_authorized']}`",
        f"- Retry executed: `{decision['safety_score_evaluation_retry_executed']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Heads",
        "",
        f"`{report['head_audit']}`",
        "",
        "## Artifacts",
        "",
        f"- Retry plan root: `{report['retry_plan_artifact']['root']}`",
        f"- Retry plan SHA OK: `{report['retry_plan_artifact']['sha256sums_ok']}`",
        f"- Source review root: `{report['source_review_artifact']['root']}`",
        f"- Source review SHA OK: `{report['source_review_artifact']['sha256sums_ok']}`",
        f"- Weight-sensitivity root: `{report['weight_sensitivity_artifact']['root']}`",
        f"- Weight-sensitivity SHA OK: `{report['weight_sensitivity_artifact']['sha256sums_ok']}`",
        "",
        "## Label Root",
        "",
        f"- Root: `{labels['root']}`",
        f"- Log count: `{labels['log_count']}`",
        f"- Records: `{labels['records']}`",
        f"- Complete outcome records: `{labels['complete_outcome_records']}`",
        f"- Payload no-leak records: `{labels['payload_no_leak_records']}`",
        f"- Formal seed log count: `{labels['formal_seed_log_count']}`",
        f"- Run IDs: `{labels['run_ids']}`",
        "",
        "## Planned Execution",
        "",
        f"- Evaluator script: `{plan['evaluator_script']}`",
        f"- Label root as candidate root: `{plan['label_root']}`",
        f"- Weight-sensitivity JSON: `{plan['weight_sensitivity_json']}`",
        f"- Future command: `{plan['future_evaluator_command']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This authorization gate does not execute the evaluator.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["authorization_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(
    root: Path,
    *,
    required_files: tuple[str, ...],
    json_file: str,
) -> dict[str, Any]:
    files = {name: root / name for name in required_files}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[json_file].is_file():
        loaded = _load_json(files[json_file])
        payload = loaded if isinstance(loaded, dict) else {}
    heads_path = root / HEADS
    heads = (
        heads_path.read_text(encoding="utf-8", errors="replace")
        if heads_path.is_file()
        else ""
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "json_payload": payload,
    }


def _retry_plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("retry_consideration_plan"))
    rows = [_dict(row) for row in plan.get("route_seed_matrix") or []]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    command = [str(item) for item in plan.get("future_evaluator_command") or []]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_ready": bool(decision.get("safety_score_evaluation_retry_plan_ready")),
        "authorization_gate_authorized": bool(
            decision.get("safety_score_evaluation_retry_authorization_gate_authorized")
        ),
        "execution_authorized": bool(
            decision.get("safety_score_evaluation_retry_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "source_review_json": plan.get("source_review_json"),
        "weight_sensitivity_json": plan.get("weight_sensitivity_json"),
        "label_root": plan.get("label_root"),
        "evaluator_script": plan.get("evaluator_script"),
        "future_evaluator_command": command,
        "expected_logs": _optional_int(plan.get("expected_logs")),
        "expected_records": _optional_int(plan.get("expected_records")),
        "expected_candidates": _optional_int(plan.get("expected_candidates")),
        "fixed_dp_head": plan.get("fixed_dp_head"),
        "route_count": len(rows),
        "route_run_ids": [str(row.get("run_id")) for row in rows],
        "route_seeds": [
            _optional_int(row.get("seed"))
            for row in rows
            if _optional_int(row.get("seed")) is not None
        ],
        "formal_route_ids": [str(row.get("run_id")) for row in rows if row.get("formal")],
        "scenario_coverage": _dict(plan.get("scenario_coverage")),
        "accept_criteria": list(plan.get("accept_criteria") or []),
        "reject_criteria": list(plan.get("reject_criteria") or []),
    }


def _source_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("source_review"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_ready": bool(decision.get("outcome_label_source_review_ready")),
        "retry_plan_authorized": bool(
            decision.get("safety_score_evaluation_retry_plan_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "run_ids": [str(run_id) for run_id in review.get("run_ids") or []],
        "run_count": _optional_int(review.get("run_count")),
        "label_records": _optional_int(review.get("label_records")),
        "broader_records": _optional_int(review.get("broader_records")),
        "records_compared": _optional_int(review.get("records_compared")),
        "compatibility_mismatch_count": _optional_int(
            review.get("compatibility_mismatch_count")
        ),
        "label_complete_outcome_records": _optional_int(
            review.get("label_complete_outcome_records")
        ),
        "broader_outcome_records_present": _optional_int(
            review.get("broader_outcome_records_present")
        ),
        "payload_no_leak_records": _optional_int(review.get("payload_no_leak_records")),
        "formal_seed_log_count": _optional_int(review.get("formal_seed_log_count")),
        "errors": list(review.get("errors") or []),
    }


def _weight_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("sensitivity_summary"))
    rows = [_dict(row) for row in summary.get("by_lambda") or []]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "weight_sensitivity_ready": bool(decision.get("weight_sensitivity_ready")),
        "blocked_action_conflicts": conflicts,
        "log_count": _optional_int(summary.get("log_count")),
        "records": _optional_int(summary.get("records")),
        "valid_records": _optional_int(summary.get("valid_records")),
        "formal_seed_log_count": _optional_int(summary.get("formal_seed_log_count")),
        "record_error_counts": dict(summary.get("record_error_counts") or {}),
        "lambda_zero_changed_records": _changed_for_lambda(rows, 0.0),
        "positive_lambda_changed": [
            int(row.get("changed_records", 0))
            for row in rows
            if _optional_float(row.get("lambda")) is not None
            and float(row.get("lambda")) > 0.0
        ],
        "max_changed_records": _optional_int(decision.get("max_changed_records")),
    }


def _label_root_summary(root: Path) -> dict[str, Any]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    records = 0
    complete_outcomes = 0
    payload_no_leak = 0
    run_ids = []
    errors = []
    formal_paths = []
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
        for row in payload:
            if not isinstance(row, dict):
                continue
            records += 1
            if _complete_outcomes(row.get("candidate_closed_loop_outcomes")):
                complete_outcomes += 1
            payload_log = _dict(row.get("candidate_set_consensus_payload_logging"))
            if (
                payload_log.get("closed_loop_outcome_fields_read") is False
                and payload_log.get("future_outcome_leakage") is False
                and payload_log.get("classical_benders_claim") is False
            ):
                payload_no_leak += 1
    return {
        "root": str(root),
        "log_count": len(paths),
        "records": records,
        "complete_outcome_records": complete_outcomes,
        "payload_no_leak_records": payload_no_leak,
        "run_ids": run_ids,
        "formal_seed_log_count": len(formal_paths),
        "formal_seed_log_paths": formal_paths,
        "errors": errors,
    }


def _implementation_summary() -> dict[str, Any]:
    script = ROOT / EVALUATOR_SCRIPT
    test = ROOT / EVALUATOR_TEST
    return {
        "evaluator_script": str(script),
        "evaluator_test": str(test),
        "evaluator_script_exists": script.is_file(),
        "evaluator_test_exists": test.is_file(),
    }


def _artifact_checks(prefix: str, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            f"{prefix}_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal(f"{prefix}_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal(
            f"{prefix}_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _retry_plan_checks(
    plan: dict[str, Any],
    label_root: Path,
) -> list[dict[str, Any]]:
    coverage = plan["scenario_coverage"]
    formal_seed_conflicts = sorted(set(plan["route_seeds"]) & set(FORMAL_SEEDS))
    return [
        _check_equal("plan_status", plan["status"], RETRY_PLAN_READY_STATUS),
        _check_equal("plan_passed", plan["passed"], True),
        _check_equal(
            "plan_authorizes_authorization_only",
            plan["authorized_next_work"],
            RETRY_PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("plan_ready", plan["plan_ready"], True),
        _check_equal(
            "plan_authorization_gate_authorized",
            plan["authorization_gate_authorized"],
            True,
        ),
        _check_equal("plan_execution_not_authorized", plan["execution_authorized"], False),
        _check_equal("plan_no_blocked_actions", plan["blocked_action_conflicts"], []),
        _check_equal("plan_label_root_matches", plan["label_root"], str(label_root)),
        _check_equal("plan_expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("plan_expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal(
            "plan_expected_candidates",
            plan["expected_candidates"],
            EXPECTED_CANDIDATES,
        ),
        _check_equal("plan_fixed_dp_head", plan["fixed_dp_head"], EXPECTED_DP_HEAD),
        _check_equal("plan_route_count", plan["route_count"], EXPECTED_LOGS),
        _check_equal("plan_formal_route_ids_empty", plan["formal_route_ids"], []),
        _check_equal("plan_route_seeds_nonformal", formal_seed_conflicts, []),
        _check_equal("plan_traffic_light_coverage", bool(coverage.get("traffic_light")), True),
        _check_equal("plan_turn_coverage", bool(coverage.get("turn")), True),
        _check_equal("plan_normal_coverage", bool(coverage.get("normal")), True),
    ]


def _source_review_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_review_status", source["status"], SOURCE_REVIEW_READY_STATUS),
        _check_equal("source_review_passed", source["passed"], True),
        _check_equal(
            "source_review_authorizes_retry_plan",
            source["authorized_next_work"],
            SOURCE_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_review_ready", source["review_ready"], True),
        _check_equal("source_retry_plan_authorized", source["retry_plan_authorized"], True),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_run_count", source["run_count"], EXPECTED_LOGS),
        _check_equal("source_label_records", source["label_records"], EXPECTED_RECORDS),
        _check_equal("source_broader_records", source["broader_records"], EXPECTED_RECORDS),
        _check_equal(
            "source_records_compared",
            source["records_compared"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "source_compatibility_mismatches_zero",
            source["compatibility_mismatch_count"],
            0,
        ),
        _check_equal(
            "source_label_complete_outcomes",
            source["label_complete_outcome_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "source_broader_outcomes_absent",
            source["broader_outcome_records_present"],
            0,
        ),
        _check_equal(
            "source_payload_no_leak_all_records",
            source["payload_no_leak_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal("source_no_formal_seed_logs", source["formal_seed_log_count"], 0),
        _check_equal("source_errors_empty", source["errors"], []),
    ]


def _weight_checks(weight: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("weight_status", weight["status"], WEIGHT_READY_STATUS),
        _check_equal("weight_passed", weight["passed"], True),
        _check_equal(
            "weight_authorizes_result_review",
            weight["authorized_next_work"],
            WEIGHT_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("weight_ready", weight["weight_sensitivity_ready"], True),
        _check_equal("weight_no_blocked_actions", weight["blocked_action_conflicts"], []),
        _check_equal("weight_log_count", weight["log_count"], EXPECTED_LOGS),
        _check_equal("weight_records", weight["records"], EXPECTED_RECORDS),
        _check_equal("weight_valid_records", weight["valid_records"], EXPECTED_RECORDS),
        _check_equal("weight_formal_seed_logs_zero", weight["formal_seed_log_count"], 0),
        _check_equal("weight_record_errors_empty", weight["record_error_counts"], {}),
        _check_equal("weight_lambda_zero_no_changes", weight["lambda_zero_changed_records"], 0),
        _check_equal(
            "weight_positive_lambda_changes_present",
            any(value > 0 for value in weight["positive_lambda_changed"]),
            True,
        ),
        _check_equal(
            "weight_max_changed_positive",
            (weight["max_changed_records"] or 0) > 0,
            True,
        ),
    ]


def _label_root_checks(
    labels: dict[str, Any],
    plan: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_equal("label_log_count", labels["log_count"], EXPECTED_LOGS),
        _check_equal("label_record_count", labels["records"], EXPECTED_RECORDS),
        _check_equal(
            "label_complete_outcome_records",
            labels["complete_outcome_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "label_payload_no_leak_records",
            labels["payload_no_leak_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal("label_no_formal_seed_logs", labels["formal_seed_log_count"], 0),
        _check_equal("label_errors_empty", labels["errors"], []),
        _check_equal(
            "label_run_ids_match_plan",
            sorted(labels["run_ids"]),
            sorted(plan["route_run_ids"]),
        ),
        _check_equal(
            "label_run_ids_match_source_review",
            sorted(labels["run_ids"]),
            sorted(source["run_ids"]),
        ),
    ]


def _implementation_checks(implementation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "evaluator_script_exists",
            implementation["evaluator_script_exists"],
            True,
        ),
        _check_equal(
            "evaluator_test_exists",
            implementation["evaluator_test_exists"],
            True,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    command = plan["future_evaluator_command"]
    criteria = " ".join(plan["accept_criteria"] + plan["reject_criteria"]).lower()
    return [
        _check_equal("command_uses_evaluator", EVALUATOR_SCRIPT in command, True),
        _check_equal("command_uses_require_pass", "--require_pass" in command, True),
        _check_equal("criteria_mentions_formal_seed", "formal seed" in criteria, True),
        _check_equal("criteria_blocks_online_selection", "online" in criteria, True),
        _check_equal("criteria_blocks_dp_modification", "modify dp" in criteria, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_retry_authorization_ready": passed,
        "safety_score_evaluation_retry_execution_authorized": passed,
        "safety_score_evaluation_retry_executed": False,
        "label_attachment_authorized": False,
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
        details.append(
            {
                "path": str(item),
                "expected": expected,
                "actual": actual,
                "ok": matched,
            }
        )
    return ok, details


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


def _changed_for_lambda(rows: list[dict[str, Any]], lam: float) -> int | None:
    for row in rows:
        parsed = _optional_float(row.get("lambda"))
        if parsed is not None and parsed == lam:
            return _optional_int(row.get("changed_records"))
    return None


def _complete_outcomes(outcomes: Any) -> bool:
    if not isinstance(outcomes, list) or len(outcomes) != EXPECTED_CANDIDATES:
        return False
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            return False
        if _optional_int(outcome.get("candidate_index")) != index:
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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
