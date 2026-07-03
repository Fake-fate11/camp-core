#!/usr/bin/env python3
"""Record-only no-promotion closeout for the v14 runtime evidence package.

This gate consumes the passed promotion-decision plan from the constructed
evidence package. It records the no-promotion closeout decision and authorizes
only a later closeout review. It does not promote, deploy, train, replay,
generate candidates, modify Diffusion Planner, change an online selector, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_PLAN_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_from_evidence_package_plan_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_recorded"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_review_only"
)

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "replay_execution_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion_decision_plan_json", type=Path, required=True)
    parser.add_argument("--promotion_decision_plan_md", type=Path, required=True)
    parser.add_argument("--promotion_decision_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_runtime_no_promotion_closeout_record",
        action="store_true",
        help="Explicit opt-in for record-only no-promotion closeout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        promotion_decision_plan_json=args.promotion_decision_plan_json,
        promotion_decision_plan_md=args.promotion_decision_plan_md,
        promotion_decision_plan_sha256s=args.promotion_decision_plan_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_no_promotion_closeout_record,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    promotion_decision_plan_json: Path,
    promotion_decision_plan_md: Path,
    promotion_decision_plan_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    source_plan = _read_json_dict(promotion_decision_plan_json)
    plan_sha256s = _read_sha256sums(promotion_decision_plan_sha256s)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks: list[dict[str, Any]] = []
    paths = {
        "promotion_decision_plan_json": promotion_decision_plan_json,
        "promotion_decision_plan_md": promotion_decision_plan_md,
        "promotion_decision_plan_sha256s": promotion_decision_plan_sha256s,
        "v14_audit_md": v14_audit_md,
        "current_status_md": current_status_md,
    }
    for name, path in paths.items():
        checks.extend(_file_checks(name, path))
    checks.extend(
        [
            _expect("no_promotion_closeout_record_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        ]
    )
    checks.extend(
        _sha256_checks(
            promotion_decision_plan_json,
            promotion_decision_plan_md,
            plan_sha256s,
        )
    )
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_audit_checks(v14_text, status_text))
    closeout = _closeout_record(source_plan)
    checks.extend(_closeout_record_checks(closeout))
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_default_off_selector_runtime_"
            "shadow_replay_promotion_decision_no_promotion_closeout_record_v1"
        ),
        "analysis": {
            "label": label,
            "record_only": True,
            "promotion_decision_plan_json": str(promotion_decision_plan_json.resolve()),
            "promotion_decision_plan_md": str(promotion_decision_plan_md.resolve()),
            "promotion_decision_plan_sha256s": str(promotion_decision_plan_sha256s.resolve()),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
            "math_boundary": (
                "This record closes the current evidence-package promotion "
                "decision as no-promotion. CAMP remains a default-off shadow "
                "reranker over fixed DP candidate tensors, using affine "
                "score_k(w)=a_k^T w over approved atoms with nonnegative "
                "simplex weights."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "source_plan_summary": _source_plan_summary(source_plan),
        "no_promotion_closeout_record": closeout,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "record_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_no_promotion_closeout_record.json", report)
    (output_dir / "runtime_no_promotion_closeout_record.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    closeout = report["no_promotion_closeout_record"]
    lines = [
        "# V14 Runtime No-Promotion Closeout Record",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout recorded: `{decision['no_promotion_closeout_recorded']}`",
        f"- Promotion recommended: `{decision['promotion_recommended']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Record",
        "",
        f"- Record decision: `{closeout['record_decision']}`",
        f"- Final selector state: `{closeout['final_selector_state']}`",
        f"- Evidence class: `{closeout['evidence_class']}`",
        "",
        "## Promotion Blockers",
        "",
    ]
    for item in closeout["promotion_blockers"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "This record did not promote atoms or selectors, deploy, train "
            "CAMP, run replay, generate candidates, modify DP, change online "
            "selection, or authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["record_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _sha256_checks(
    plan_json: Path,
    plan_md: Path,
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _expect(
            "plan_sha256s_json_hash",
            plan_sha256s.get(plan_json.name),
            _sha256(plan_json) if plan_json.is_file() else None,
        ),
        _expect(
            "plan_sha256s_md_hash",
            plan_sha256s.get(plan_md.name),
            _sha256(plan_md) if plan_md.is_file() else None,
        ),
    ]


def _source_plan_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("promotion_decision_plan"))
    analysis = _dict(source_plan.get("analysis"))
    checks = [
        _expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        _expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready", decision.get("promotion_decision_from_evidence_package_plan_ready"), True),
        _expect("source_plan_recommendation", decision.get("recommendation"), "do_not_promote_from_current_evidence_package_alone"),
        _expect("source_plan_immediate_action", decision.get("immediate_action"), "record_no_promotion_closeout_only"),
        _expect("source_plan_promotion_executed", decision.get("promotion_executed_by_this_gate"), False),
        _expect("source_plan_deployment_executed", decision.get("deployment_executed_by_this_gate"), False),
        _expect("source_plan_training_executed", decision.get("training_executed_by_this_gate"), False),
        _expect("source_plan_replay_executed", decision.get("replay_executed_by_this_gate"), False),
        _expect("source_plan_candidate_generation_executed", decision.get("candidate_generation_executed_by_this_gate"), False),
        _expect("source_plan_dp_modified", decision.get("dp_modified_by_this_gate"), False),
        _expect("source_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_analysis_planning_only", analysis.get("planning_only"), True),
        _expect("source_plan_analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("source_plan_analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("source_plan_required_future_evidence_present", bool(plan.get("required_evidence_before_any_future_promotion")), True),
        _expect("source_plan_no_go_conditions_present", bool(plan.get("no_go_conditions")), True),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_plan_decision_{name}", decision.get(name), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect(
            "audit_plan_ready",
            _latest_value(v14_text, "default_off_shadow_selector_runtime_promotion_decision_from_evidence_package_plan_ready"),
            "True",
        ),
        _expect(
            "audit_no_promotion_closeout_authorized",
            _latest_value(v14_text, "default_off_shadow_selector_runtime_promotion_no_promotion_closeout_authorized"),
            "True",
        ),
    ]


def _closeout_record(source_plan: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(source_plan.get("promotion_decision_plan"))
    return {
        "record_decision": "close_current_evidence_package_without_promotion",
        "final_selector_state": "default_off_shadow_only_not_promoted",
        "promotion_recommended": False,
        "evidence_class": "static_default_off_shadow_evidence_not_deployment_or_safety_proof",
        "source_recommendation": plan.get("recommendation"),
        "source_immediate_action": plan.get("immediate_action"),
        "promotion_blockers": [
            "source plan recommends do_not_promote_from_current_evidence_package_alone",
            "evidence package is static/default-off shadow evidence only",
            "no closed-loop safety or deployment-readiness evidence was produced by this chain",
            "actual selector promotion remains a separate explicitly authorized future gate",
        ],
        "future_work_boundary": [
            "this chain is closed as no-promotion evidence-package decision record",
            "no selector promotion, deployment, online selector change, CAMP-over-DP claim, or safety claim is authorized",
            "any future promotion work must start from a fresh EOF gate and explicit authorization",
        ],
    }


def _closeout_record_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(record["promotion_blockers"] + record["future_work_boundary"]).lower()
    return [
        _expect("closeout_record_decision", record["record_decision"], "close_current_evidence_package_without_promotion"),
        _expect("closeout_final_selector_state", record["final_selector_state"], "default_off_shadow_only_not_promoted"),
        _expect("closeout_promotion_recommended", record["promotion_recommended"], False),
        _expect("closeout_source_recommendation", record["source_recommendation"], "do_not_promote_from_current_evidence_package_alone"),
        _expect("closeout_source_immediate_action", record["source_immediate_action"], "record_no_promotion_closeout_only"),
        _check("closeout_blocks_promotion", "no selector promotion" in text or "without promotion" in text, text, "promotion blocked"),
        _check("closeout_blocks_deployment", "deployment" in text, text, "deployment blocked"),
        _check("closeout_blocks_safety_claim", "safety claim" in text, text, "safety claim blocked"),
        _check("closeout_blocks_online_change", "online selector change" in text, text, "online selector change blocked"),
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "no_promotion_closeout_record_ready": bool(passed),
        "no_promotion_closeout_recorded": bool(passed),
        "no_promotion_closeout_review_authorized": bool(passed),
        "promotion_recommended": False,
        "recommendation": "do_not_promote_from_current_evidence_package_alone",
        "score_expression": SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "no_promotion_closeout_record_enabled" in failed_set:
        return "explicit_no_promotion_closeout_record_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("plan_sha256s_") for name in failed):
        return "source_plan_sha256s_mismatch"
    if any(name.startswith("source_plan_") for name in failed):
        return "source_plan_contract_failure"
    if any(name.startswith("closeout_") for name in failed):
        return "closeout_record_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "no_promotion_closeout_record_failure"


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("promotion_decision_plan"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "recommendation": decision.get("recommendation"),
        "immediate_action": decision.get("immediate_action"),
        "required_evidence_count": len(_list(plan.get("required_evidence_before_any_future_promotion"))),
        "no_go_condition_count": len(_list(plan.get("no_go_conditions"))),
    }


def _file_checks(name: str, path: Path) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_exists", path.is_file(), str(path), "file"),
        _check(
            f"{name}_nonempty",
            path.is_file() and path.stat().st_size > 0,
            path.stat().st_size if path.is_file() else None,
            ">0 bytes",
        ),
    ]


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            values[parts[1].strip()] = parts[0]
            values[Path(parts[1].strip()).name] = parts[0]
    return values


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
