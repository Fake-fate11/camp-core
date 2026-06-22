#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as WEIGHT_AUTHORIZED_NEXT_WORK,
    READY_STATUS as WEIGHT_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_"
    "execution_consideration_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_"
    "execution_consideration_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_"
    "read_only_execution_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SAFETY_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan_1e7613f"
)
DEFAULT_WEIGHT_SENSITIVITY_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/"
    "candidate_set_consensus_shadow_atom_weight_sensitivity_b373e0cdd"
)
DEFAULT_CANDIDATE_ROOT = (
    "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality/"
    "logging_enabled"
)

SAFETY_PLAN_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.json"
)
SAFETY_PLAN_MD = "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.md"
WEIGHT_JSON = "candidate_set_consensus_shadow_atom_weight_sensitivity.json"
WEIGHT_MD = "candidate_set_consensus_shadow_atom_weight_sensitivity.md"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"
LOG_NAME = "camp_selection_log.json"

EVALUATOR_SCRIPT = (
    "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_evaluation.py"
)
EVALUATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_evaluation.py"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execution-consideration gate for the candidate-set consensus "
            "shadow atom safety-score evaluator. It verifies artifacts, heads, "
            "nonformal scope, and implementation readiness, but does not run "
            "the evaluator."
        )
    )
    parser.add_argument("--safety_plan_root", type=Path, default=Path(DEFAULT_SAFETY_PLAN_ROOT))
    parser.add_argument(
        "--weight_sensitivity_root",
        type=Path,
        default=Path(DEFAULT_WEIGHT_SENSITIVITY_ROOT),
    )
    parser.add_argument("--candidate_root", type=Path, default=Path(DEFAULT_CANDIDATE_ROOT))
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
        safety_plan_root=args.safety_plan_root,
        weight_sensitivity_root=args.weight_sensitivity_root,
        candidate_root=args.candidate_root,
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
    safety_plan_root: Path,
    weight_sensitivity_root: Path,
    candidate_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    plan_artifact = _artifact_summary(
        safety_plan_root,
        required_files=(SAFETY_PLAN_JSON, SAFETY_PLAN_MD, HEADS, SHA256SUMS),
        json_file=SAFETY_PLAN_JSON,
    )
    weight_artifact = _artifact_summary(
        weight_sensitivity_root,
        required_files=(WEIGHT_JSON, WEIGHT_MD, HEADS, SHA256SUMS),
        json_file=WEIGHT_JSON,
    )
    plan_payload = plan_artifact.get("json_payload") or {}
    weight_payload = weight_artifact.get("json_payload") or {}
    plan = _plan_summary(plan_payload)
    weight = _weight_summary(weight_payload)
    logs = _candidate_log_summary(candidate_root)
    implementation = _implementation_summary()
    checks = [
        *_artifact_checks("safety_plan", plan_artifact),
        *_artifact_checks("weight_sensitivity", weight_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_plan_checks(plan),
        *_weight_checks(weight),
        *_candidate_log_checks(logs, plan),
        *_implementation_checks(implementation),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_execution_consideration_v1"
            ),
            "label": label,
            "role": (
                "consider whether a later read-only broader-log safety-score "
                "evaluation execution is authorized"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_score_evaluation_executed": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(logs["formal_seed_log_count"]),
            "math_boundary": (
                "This gate verifies artifacts and scope only. It does not read "
                "candidate_closed_loop_outcomes and does not execute the "
                "safety-score evaluator. A later execution, if authorized, must "
                "reuse fixed shadow selected indices from the weight-sensitivity "
                "artifact and may compute SafetyCost v1 only as an offline label. "
                "No atom definition, CAMP weight, online selector, DP candidate "
                "generation, simplex/CVaR/L2 master, or DP-side classical "
                "Benders claim is changed."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "safety_plan_artifact": _strip_payload(plan_artifact),
        "weight_sensitivity_artifact": _strip_payload(weight_artifact),
        "plan_summary": plan,
        "weight_sensitivity_summary": weight,
        "candidate_log_summary": logs,
        "implementation_summary": implementation,
        "consideration_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    logs = report["candidate_log_summary"]
    plan = report["plan_summary"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Execution Consideration",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Read-only execution authorized: `{decision['safety_score_evaluation_read_only_execution_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Heads",
        "",
        f"`{report['head_audit']}`",
        "",
        "## Artifact Checks",
        "",
        f"- Safety plan root: `{report['safety_plan_artifact']['root']}`",
        f"- Safety plan SHA OK: `{report['safety_plan_artifact']['sha256sums_ok']}`",
        f"- Weight-sensitivity root: `{report['weight_sensitivity_artifact']['root']}`",
        f"- Weight-sensitivity SHA OK: `{report['weight_sensitivity_artifact']['sha256sums_ok']}`",
        "",
        "## Candidate Scope",
        "",
        f"- Candidate root: `{logs['root']}`",
        f"- Log count: `{logs['log_count']}`",
        f"- Records: `{logs['records']}`",
        f"- Formal seed log count: `{logs['formal_seed_log_count']}`",
        f"- Run IDs: `{logs['run_ids']}`",
        "",
        "## Route Matrix",
        "",
        f"- Plan route count: `{plan['route_count']}`",
        f"- Plan route seeds: `{plan['route_seeds']}`",
        f"- Scenario coverage: `{plan['scenario_coverage']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This consideration does not execute the evaluator. If accepted, the "
        "only next work is read-only broader-log safety-score evaluation "
        "execution with no replay, no formal seeds, no CAMP training, no atom "
        "promotion, no online selector change, and no DP modification.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["consideration_checks"]:
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
    heads = (root / HEADS).read_text(encoding="utf-8", errors="replace") if (root / HEADS).is_file() else ""
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "json_payload": payload,
    }


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("safety_score_evaluation_plan"))
    route_rows = [_dict(row) for row in plan.get("route_seed_matrix") or []]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_ready": bool(decision.get("safety_score_evaluation_plan_ready")),
        "implementation_authorized": bool(
            decision.get("safety_score_evaluation_implementation_authorized")
        ),
        "execution_authorized": bool(
            decision.get("safety_score_evaluation_execution_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "expected_logs": _optional_int(plan.get("expected_logs")),
        "expected_records": _optional_int(plan.get("expected_records")),
        "expected_candidates": _optional_int(plan.get("expected_candidates")),
        "fixed_dp_head": plan.get("fixed_dp_head"),
        "route_count": len(route_rows),
        "route_run_ids": [str(row.get("run_id")) for row in route_rows],
        "route_seeds": [
            _optional_int(row.get("seed"))
            for row in route_rows
            if _optional_int(row.get("seed")) is not None
        ],
        "scenario_coverage": _dict(plan.get("scenario_coverage")),
        "accept_criteria": list(plan.get("accept_criteria") or []),
        "reject_criteria": list(plan.get("reject_criteria") or []),
    }


def _weight_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("sensitivity_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    lambda_rows = [_dict(row) for row in summary.get("by_lambda") or []]
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
        "lambda_zero_changed_records": _changed_for_lambda(lambda_rows, 0.0),
        "max_changed_records": _optional_int(decision.get("max_changed_records")),
        "positive_lambda_changed": [
            int(row.get("changed_records", 0))
            for row in lambda_rows
            if _optional_float(row.get("lambda")) is not None
            and float(row.get("lambda")) > 0.0
        ],
    }


def _candidate_log_summary(root: Path) -> dict[str, Any]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    records = 0
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
        records += sum(1 for row in payload if isinstance(row, dict))
    return {
        "root": str(root),
        "log_count": len(paths),
        "records": records,
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
        "pytest_targets": [
            EVALUATOR_TEST,
            "camp_core/tests/test_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.py",
            "camp_core/tests/test_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity.py",
            "camp_core/tests/test_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity_plan.py",
        ],
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


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    route_seed_conflicts = sorted(set(plan["route_seeds"]) & set(FORMAL_SEEDS))
    coverage = plan["scenario_coverage"]
    return [
        _check_equal("plan_status", plan["status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", plan["passed"], True),
        _check_equal("plan_authorized_implementation", plan["authorized_next_work"], PLAN_AUTHORIZED_NEXT_WORK),
        _check_equal("plan_ready", plan["plan_ready"], True),
        _check_equal("plan_implementation_authorized", plan["implementation_authorized"], True),
        _check_equal("plan_execution_not_pre_authorized", plan["execution_authorized"], False),
        _check_equal("plan_no_blocked_actions", plan["blocked_action_conflicts"], []),
        _check_equal("plan_expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("plan_expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal("plan_expected_candidates", plan["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("plan_fixed_dp_head", plan["fixed_dp_head"], EXPECTED_DP_HEAD),
        _check_equal("plan_route_count", plan["route_count"], EXPECTED_LOGS),
        _check_equal("plan_route_seeds_nonformal", route_seed_conflicts, []),
        _check_equal("plan_has_accept_criteria", bool(plan["accept_criteria"]), True),
        _check_equal("plan_has_reject_criteria", bool(plan["reject_criteria"]), True),
        _check_equal("plan_traffic_light_coverage", bool(coverage.get("traffic_light")), True),
        _check_equal("plan_turn_coverage", bool(coverage.get("turn")), True),
        _check_equal("plan_normal_coverage", bool(coverage.get("normal")), True),
    ]


def _weight_checks(weight: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("weight_status", weight["status"], WEIGHT_READY_STATUS),
        _check_equal("weight_passed", weight["passed"], True),
        _check_equal("weight_authorized_result_review", weight["authorized_next_work"], WEIGHT_AUTHORIZED_NEXT_WORK),
        _check_equal("weight_ready", weight["weight_sensitivity_ready"], True),
        _check_equal("weight_no_blocked_actions", weight["blocked_action_conflicts"], []),
        _check_equal("weight_log_count", weight["log_count"], EXPECTED_LOGS),
        _check_equal("weight_records", weight["records"], EXPECTED_RECORDS),
        _check_equal("weight_valid_records", weight["valid_records"], EXPECTED_RECORDS),
        _check_equal("weight_formal_seed_logs_zero", weight["formal_seed_log_count"], 0),
        _check_equal("weight_record_errors_empty", weight["record_error_counts"], {}),
        _check_equal("weight_lambda_zero_no_changes", weight["lambda_zero_changed_records"], 0),
        _check_equal("weight_positive_lambda_changes_present", any(value > 0 for value in weight["positive_lambda_changed"]), True),
        _check_equal("weight_max_changed_positive", (weight["max_changed_records"] or 0) > 0, True),
    ]


def _candidate_log_checks(logs: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("candidate_log_count", logs["log_count"], EXPECTED_LOGS),
        _check_equal("candidate_record_count", logs["records"], EXPECTED_RECORDS),
        _check_equal("candidate_log_no_formal_seed", logs["formal_seed_log_count"], 0),
        _check_equal("candidate_log_errors_empty", logs["errors"], []),
        _check_equal(
            "candidate_log_run_ids_match_plan",
            sorted(logs["run_ids"]),
            sorted(plan["route_run_ids"]),
        ),
    ]


def _implementation_checks(implementation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("evaluator_script_exists", implementation["evaluator_script_exists"], True),
        _check_equal("evaluator_test_exists", implementation["evaluator_test_exists"], True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    criteria = " ".join(plan["accept_criteria"] + plan["reject_criteria"]).lower()
    return [
        _check_equal("criteria_mentions_sha_heads", "sha" in criteria and "heads" in criteria, True),
        _check_equal("criteria_blocks_formal_seed", "formal seed" in criteria, True),
        _check_equal("criteria_blocks_outcome_leakage", "safety" in criteria and "online" in criteria, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_execution_consideration_ready": passed,
        "safety_score_evaluation_read_only_execution_authorized": passed,
        "safety_score_evaluation_executed": False,
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


def _changed_for_lambda(by_lambda: list[dict[str, Any]], lam: float) -> int | None:
    for row in by_lambda:
        parsed = _optional_float(row.get("lambda"))
        if parsed is not None and parsed == lam:
            return _optional_int(row.get("changed_records"))
    return None


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
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
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
