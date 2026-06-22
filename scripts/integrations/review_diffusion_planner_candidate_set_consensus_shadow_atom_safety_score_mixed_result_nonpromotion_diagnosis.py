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

from scripts.integrations.diagnose_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DIAGNOSIS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DIAGNOSIS_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_result_review_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DIAGNOSIS_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_mixed_result_nonpromotion_diagnosis_execution_9b19c5b"
)

DIAGNOSIS_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_execution.json"
)
DIAGNOSIS_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_execution.md"
)
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

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
            "Result-review-only gate for the mixed-result non-promotion "
            "diagnosis artifact. It confirms non-promotion closeout scope and "
            "does not promote atoms, train CAMP, run replay, or modify DP."
        )
    )
    parser.add_argument("--diagnosis_root", type=Path, default=Path(DEFAULT_DIAGNOSIS_ROOT))
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(diagnosis_root=args.diagnosis_root, label=args.label)
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
    diagnosis_root: Path,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(diagnosis_root)
    diagnosis = _diagnosis_summary(artifact.get("json_payload") or {})
    review = _review_summary(diagnosis)
    checks = [
        *_artifact_checks(artifact),
        *_diagnosis_checks(diagnosis),
        *_review_checks(review),
        *_boundary_checks(diagnosis),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_result_review_v1"
            ),
            "label": label,
            "role": "review-only confirmation of non-promotion diagnosis results",
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This review reads the existing diagnosis artifact only. It "
                "does not recompute outcomes, define atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "run replay, run DP, modify DP, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "diagnosis_artifact": _strip_payload(artifact),
        "diagnosis_summary": diagnosis,
        "result_review": review,
        "review_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    diagnosis = report["diagnosis_summary"]
    review = report["result_review"]
    lines = [
        "# Candidate-Set Consensus Mixed Result Non-Promotion Diagnosis Result Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout classification: `{review['closeout_classification']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Artifact",
        "",
        f"- Root: `{report['diagnosis_artifact']['root']}`",
        f"- SHA OK: `{report['diagnosis_artifact']['sha256sums_ok']}`",
        f"- Exit code: `{report['diagnosis_artifact']['exit_code']}`",
        "",
        "## Diagnosis",
        "",
        f"- Class: `{diagnosis['diagnosis_class']}`",
        f"- Records: `{diagnosis['records']}`",
        f"- Better-only lambda count: `{diagnosis['better_only_lambda_count']}`",
        f"- Worse lambda count: `{diagnosis['worse_lambda_count']}`",
        f"- Nonfallback changed records: `{diagnosis['nonfallback_changed_records']}`",
        f"- Nonfallback better/worse: `{diagnosis['nonfallback_better_records']}` / `{diagnosis['nonfallback_worse_records']}`",
        f"- Nonfallback mean delta: `{diagnosis['nonfallback_mean_delta']}`",
        "",
        "## Interpretation",
        "",
        review["interpretation"],
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This review does not authorize safety benefit claims, atom promotion, "
        "CAMP retraining, online selector changes, formal seeds, Full36, "
        "replay, label attachment, or DP modification.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        DIAGNOSIS_JSON,
        DIAGNOSIS_MD,
        COMMAND_LOG,
        COMMAND_ERR,
        EXIT_CODE,
        HEADS,
        SHA256SUMS,
    )
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[DIAGNOSIS_JSON].is_file():
        loaded = _load_json(files[DIAGNOSIS_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "exit_code": (
            files[EXIT_CODE].read_text(encoding="utf-8").strip()
            if files[EXIT_CODE].is_file()
            else None
        ),
        "heads_text": (
            files[HEADS].read_text(encoding="utf-8", errors="replace")
            if files[HEADS].is_file()
            else ""
        ),
        "json_payload": payload,
    }


def _diagnosis_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("diagnosis_summary"))
    fallback = _dict(_dict(summary.get("by_fallback")).get("fallback"))
    nonfallback = _dict(_dict(summary.get("by_fallback")).get("nonfallback"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "diagnosis_ready": bool(decision.get("mixed_result_nonpromotion_diagnosis_ready")),
        "result_review_authorized": bool(
            decision.get("mixed_result_nonpromotion_diagnosis_result_review_authorized")
        ),
        "diagnosis_class": decision.get("diagnosis_class"),
        "sample_too_small_for_promotion": bool(
            decision.get("sample_too_small_for_promotion")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "failed_checks": list(decision.get("failed_checks") or []),
        "records": _int(summary.get("records")),
        "better_only_lambda_count": _int(summary.get("better_only_lambda_count")),
        "worse_lambda_count": _int(summary.get("worse_lambda_count")),
        "fallback_changed_records": _int(fallback.get("changed_records")),
        "fallback_worse_records": _int(fallback.get("worse_records")),
        "nonfallback_changed_records": _int(nonfallback.get("changed_records")),
        "nonfallback_better_records": _int(nonfallback.get("better_records")),
        "nonfallback_worse_records": _int(nonfallback.get("worse_records")),
        "nonfallback_mean_delta": _optional_float(nonfallback.get("mean_delta")),
    }


def _review_summary(diagnosis: dict[str, Any]) -> dict[str, Any]:
    mixed = (
        diagnosis["diagnosis_class"] == "mixed_nonpromotion"
        and diagnosis["worse_lambda_count"] > 0
        and diagnosis["nonfallback_worse_records"] > 0
    )
    return {
        "closeout_classification": (
            "confirmed_mixed_nonpromotion_closeout_needed"
            if mixed
            else "unconfirmed_nonpromotion"
        ),
        "authorizes_closeout_plan": mixed,
        "interpretation": (
            "The diagnosis confirms a real but mixed non-promotion signal. "
            "Changed rows are not promotion-safe because the same diagnostic "
            "contains worse rows and a nonfallback positive mean delta. The "
            "next admissible work is a closeout plan that records promotion "
            "blockers and preserves the default-off boundary."
        ),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "artifact_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("artifact_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("artifact_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "artifact_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _diagnosis_checks(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("diagnosis_status", diagnosis["status"], DIAGNOSIS_READY_STATUS),
        _check_equal("diagnosis_passed", diagnosis["passed"], True),
        _check_equal(
            "diagnosis_authorizes_result_review",
            diagnosis["authorized_next_work"],
            DIAGNOSIS_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("diagnosis_ready", diagnosis["diagnosis_ready"], True),
        _check_equal("diagnosis_result_review_authorized", diagnosis["result_review_authorized"], True),
        _check_equal("diagnosis_class_mixed", diagnosis["diagnosis_class"], "mixed_nonpromotion"),
        _check_equal("diagnosis_no_failed_checks", diagnosis["failed_checks"], []),
        _check_equal("diagnosis_no_blocked_actions", diagnosis["blocked_action_conflicts"], []),
        _check_equal("diagnosis_records_present", diagnosis["records"] > 0, True),
        _check_equal("diagnosis_better_only_lambdas_present", diagnosis["better_only_lambda_count"] > 0, True),
        _check_equal("diagnosis_worse_lambdas_present", diagnosis["worse_lambda_count"] > 0, True),
        _check_equal("diagnosis_no_safety_benefit", diagnosis["safety_benefit_evidence"], False),
        _check_equal("diagnosis_no_atom_promotion", diagnosis["atom_promotion_authorized"], False),
        _check_equal(
            "diagnosis_sample_too_small",
            diagnosis["sample_too_small_for_promotion"],
            True,
        ),
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "review_classification_confirmed",
            review["closeout_classification"],
            "confirmed_mixed_nonpromotion_closeout_needed",
        ),
        _check_equal("review_authorizes_closeout_plan", review["authorizes_closeout_plan"], True),
    ]


def _boundary_checks(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("boundary_no_safety_benefit", diagnosis["safety_benefit_evidence"], False),
        _check_equal("boundary_no_promotion", diagnosis["atom_promotion_authorized"], False),
        _check_equal("boundary_no_blocked_actions", diagnosis["blocked_action_conflicts"], []),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "mixed_result_nonpromotion_diagnosis_result_review_ready": passed,
        "nonpromotion_closeout_plan_authorized": passed,
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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
