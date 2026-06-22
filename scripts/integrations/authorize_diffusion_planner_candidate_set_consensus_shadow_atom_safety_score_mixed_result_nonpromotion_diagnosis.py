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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as EVALUATION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as EVALUATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_result import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_authorization_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_authorization_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_execution_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_mixed_result_nonpromotion_diagnosis_plan_162cfe9"
)
DEFAULT_RESULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_result_review_0a87b7b"
)
DEFAULT_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_retry_execution_a28d089"
)

PLAN_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_plan.json"
)
PLAN_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_plan.md"
)
REVIEW_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_result_review.json"
)
REVIEW_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_result_review.md"
)
EXECUTION_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_execution.json"
)
EXECUTION_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_execution.md"
)
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

DIAGNOSIS_SCRIPT = (
    "scripts/integrations/diagnose_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_mixed_result_nonpromotion.py"
)
DIAGNOSIS_TEST = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
    "shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis.py"
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
            "Authorization-only gate for mixed-result non-promotion diagnosis. "
            "It verifies artifacts, heads, fixed DP, and implementation "
            "readiness but does not execute the diagnosis."
        )
    )
    parser.add_argument("--plan_root", type=Path, default=Path(DEFAULT_PLAN_ROOT))
    parser.add_argument(
        "--result_review_root",
        type=Path,
        default=Path(DEFAULT_RESULT_REVIEW_ROOT),
    )
    parser.add_argument("--execution_root", type=Path, default=Path(DEFAULT_EXECUTION_ROOT))
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
        plan_root=args.plan_root,
        result_review_root=args.result_review_root,
        execution_root=args.execution_root,
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
    plan_root: Path,
    result_review_root: Path,
    execution_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    plan_artifact = _artifact_summary(
        plan_root,
        required_files=(PLAN_JSON, PLAN_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS),
        json_file=PLAN_JSON,
    )
    review_artifact = _artifact_summary(
        result_review_root,
        required_files=(REVIEW_JSON, REVIEW_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS),
        json_file=REVIEW_JSON,
    )
    execution_artifact = _artifact_summary(
        execution_root,
        required_files=(EXECUTION_JSON, EXECUTION_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS),
        json_file=EXECUTION_JSON,
    )
    plan = _plan_summary(plan_artifact.get("json_payload") or {})
    review = _review_summary(review_artifact.get("json_payload") or {})
    execution = _execution_summary(execution_artifact.get("json_payload") or {})
    implementation = _implementation_summary()
    checks = [
        *_artifact_checks("plan", plan_artifact),
        *_artifact_checks("result_review", review_artifact),
        *_artifact_checks("execution", execution_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_plan_checks(plan),
        *_review_checks(review),
        *_execution_checks(execution),
        *_implementation_checks(implementation),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_authorization_v1"
            ),
            "label": label,
            "role": "authorization-only gate for read-only mixed-result diagnosis",
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "diagnosis_executed": False,
            "math_boundary": (
                "This gate verifies evidence and implementation readiness only. "
                "It does not execute diagnosis, recompute outcomes, define "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, mutate "
                "the convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, run replay, run DP, modify DP, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "plan_artifact": _strip_payload(plan_artifact),
        "result_review_artifact": _strip_payload(review_artifact),
        "execution_artifact": _strip_payload(execution_artifact),
        "plan_summary": plan,
        "result_review_summary": review,
        "execution_summary": execution,
        "implementation_summary": implementation,
        "authorization_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Mixed Result Non-Promotion Diagnosis Authorization",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Diagnosis execution authorized: `{decision['mixed_result_nonpromotion_diagnosis_execution_authorized']}`",
        f"- Diagnosis executed: `{decision['mixed_result_nonpromotion_diagnosis_executed']}`",
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
        f"- Plan root: `{report['plan_artifact']['root']}` SHA OK `{report['plan_artifact']['sha256sums_ok']}`",
        f"- Result review root: `{report['result_review_artifact']['root']}` SHA OK `{report['result_review_artifact']['sha256sums_ok']}`",
        f"- Execution root: `{report['execution_artifact']['root']}` SHA OK `{report['execution_artifact']['sha256sums_ok']}`",
        "",
        "## Implementation",
        "",
        f"- Diagnosis script exists: `{report['implementation_summary']['diagnosis_script_exists']}`",
        f"- Diagnosis test exists: `{report['implementation_summary']['diagnosis_test_exists']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
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
    heads = (
        (root / HEADS).read_text(encoding="utf-8", errors="replace")
        if (root / HEADS).is_file()
        else ""
    )
    exit_code = (
        (root / EXIT_CODE).read_text(encoding="utf-8").strip()
        if (root / EXIT_CODE).is_file()
        else None
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "exit_code": exit_code,
        "json_payload": payload,
    }


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("diagnosis_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_ready": bool(decision.get("mixed_result_nonpromotion_diagnosis_plan_ready")),
        "authorization_gate_authorized": bool(
            decision.get("mixed_result_nonpromotion_diagnosis_authorization_gate_authorized")
        ),
        "diagnosis_authorized": bool(
            decision.get("mixed_result_nonpromotion_diagnosis_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "executes_diagnosis_now": bool(plan.get("executes_diagnosis_now")),
        "requires_new_replay": bool(plan.get("requires_new_replay")),
        "requires_atom_promotion": bool(plan.get("requires_atom_promotion")),
        "requires_online_selector_change": bool(
            plan.get("requires_online_selector_change")
        ),
        "requires_dp_modification": bool(plan.get("requires_dp_modification")),
        "diagnostic_questions": list(plan.get("diagnostic_questions") or []),
        "accept_criteria": list(plan.get("accept_criteria") or []),
        "reject_criteria": list(plan.get("reject_criteria") or []),
    }


def _review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "result_review_ready": bool(
            decision.get("safety_score_evaluation_result_review_ready")
        ),
        "result_classification": decision.get("result_classification"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _execution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("evaluation_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "evaluation_ready": bool(decision.get("safety_score_evaluation_ready")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "records": _optional_int(summary.get("records")),
        "valid_records": _optional_int(summary.get("valid_records")),
        "outcome_available_records": _optional_int(
            summary.get("outcome_available_records")
        ),
        "formal_seed_log_count": _optional_int(summary.get("formal_seed_log_count")),
        "max_changed_records": _optional_int(summary.get("max_changed_records")),
    }


def _implementation_summary() -> dict[str, Any]:
    script = ROOT / DIAGNOSIS_SCRIPT
    test = ROOT / DIAGNOSIS_TEST
    return {
        "diagnosis_script": str(script),
        "diagnosis_test": str(test),
        "diagnosis_script_exists": script.is_file(),
        "diagnosis_test_exists": test.is_file(),
    }


def _artifact_checks(prefix: str, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            f"{prefix}_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal(f"{prefix}_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal(f"{prefix}_exit_code_zero", artifact["exit_code"], "0"),
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
    return [
        _check_equal("plan_status", plan["status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", plan["passed"], True),
        _check_equal(
            "plan_authorizes_authorization_only",
            plan["authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("plan_ready", plan["plan_ready"], True),
        _check_equal(
            "plan_authorization_gate_authorized",
            plan["authorization_gate_authorized"],
            True,
        ),
        _check_equal("plan_diagnosis_not_authorized", plan["diagnosis_authorized"], False),
        _check_equal("plan_no_blocked_actions", plan["blocked_action_conflicts"], []),
        _check_equal("plan_executes_nothing_now", plan["executes_diagnosis_now"], False),
        _check_equal("plan_no_new_replay", plan["requires_new_replay"], False),
        _check_equal("plan_no_atom_promotion", plan["requires_atom_promotion"], False),
        _check_equal(
            "plan_no_online_selector_change",
            plan["requires_online_selector_change"],
            False,
        ),
        _check_equal("plan_no_dp_modification", plan["requires_dp_modification"], False),
        _check_equal("plan_has_diagnostic_questions", bool(plan["diagnostic_questions"]), True),
        _check_equal("plan_has_accept_criteria", bool(plan["accept_criteria"]), True),
        _check_equal("plan_has_reject_criteria", bool(plan["reject_criteria"]), True),
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("review_status", review["status"], REVIEW_READY_STATUS),
        _check_equal("review_passed", review["passed"], True),
        _check_equal(
            "review_authorizes_plan",
            review["authorized_next_work"],
            REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("review_ready", review["result_review_ready"], True),
        _check_equal("review_classification_mixed", review["result_classification"], "mixed_nonpromotion"),
        _check_equal("review_no_blocked_actions", review["blocked_action_conflicts"], []),
    ]


def _execution_checks(execution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("execution_status", execution["status"], EVALUATION_READY_STATUS),
        _check_equal("execution_passed", execution["passed"], True),
        _check_equal(
            "execution_authorizes_review",
            execution["authorized_next_work"],
            EVALUATION_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("execution_ready", execution["evaluation_ready"], True),
        _check_equal("execution_no_blocked_actions", execution["blocked_action_conflicts"], []),
        _check_equal("execution_records_valid", execution["valid_records"], execution["records"]),
        _check_equal(
            "execution_outcomes_available",
            execution["outcome_available_records"],
            execution["records"],
        ),
        _check_equal("execution_no_formal_seed_logs", execution["formal_seed_log_count"], 0),
        _check_equal("execution_selection_changes_present", (execution["max_changed_records"] or 0) > 0, True),
    ]


def _implementation_checks(implementation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("diagnosis_script_exists", implementation["diagnosis_script_exists"], True),
        _check_equal("diagnosis_test_exists", implementation["diagnosis_test_exists"], True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["accept_criteria"] + plan["reject_criteria"]).lower()
    return [
        _check_equal("criteria_blocks_formal_seed", "formal seed" in text, True),
        _check_equal("criteria_blocks_online", "online" in text, True),
        _check_equal("criteria_blocks_training", "training" in text, True),
        _check_equal("criteria_blocks_promotion", "promotion" in text, True),
        _check_equal("criteria_blocks_dp_modification", "dp modification" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "mixed_result_nonpromotion_diagnosis_authorization_ready": passed,
        "mixed_result_nonpromotion_diagnosis_execution_authorized": passed,
        "mixed_result_nonpromotion_diagnosis_executed": False,
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
        details.append({"path": str(item), "expected": expected, "actual": actual, "ok": matched})
    return ok, details


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
