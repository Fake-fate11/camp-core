#!/usr/bin/env python3
"""Plan-only promotion decision from the v14 runtime evidence package.

This gate consumes the already-passed constructed-package static review and the
constructed evidence package manifest. It emits a conservative promotion
decision plan. It does not promote, deploy, train, replay, generate candidates,
modify Diffusion Planner, change an online selector, or make safety/CAMP-over-
DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_static_review_v1"
)
EVIDENCE_PACKAGE_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_static_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_only"
)

EXPECTED_PACKAGE_ENTRY_COUNT = 15
EXPECTED_ENTRY_NAMES = (
    "atom_scales_json",
    "offline_weights_npy",
    "runtime_manifest",
    "runtime_promotion_decision_plan",
    "runtime_result_review",
    "runtime_shadow_execution_sha256s",
    "shadow_vs_top1_delta_review",
    "source_preflight_json",
    "source_preflight_md",
    "source_preflight_sha256s",
    "static_review_json",
    "static_review_md",
    "static_review_sha256s",
    "training_artifact_static_review",
    "training_summary",
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
    parser.add_argument("--construction_static_review_json", type=Path, required=True)
    parser.add_argument("--construction_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--evidence_manifest_json", type=Path, required=True)
    parser.add_argument("--evidence_package_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_runtime_promotion_decision_from_evidence_package",
        action="store_true",
        help="Explicit opt-in for plan-only decision from the evidence package.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        construction_static_review_json=args.construction_static_review_json,
        construction_static_review_sha256s=args.construction_static_review_sha256s,
        evidence_manifest_json=args.evidence_manifest_json,
        evidence_package_sha256s=args.evidence_package_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_decision_from_evidence_package,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    construction_static_review_json: Path,
    construction_static_review_sha256s: Path,
    evidence_manifest_json: Path,
    evidence_package_sha256s: Path,
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
    static_review = _read_json_dict(construction_static_review_json)
    evidence_manifest = _read_json_dict(evidence_manifest_json)
    review_sha256s = _read_sha256sums(construction_static_review_sha256s)
    package_sha256s = _read_sha256sums(evidence_package_sha256s)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks: list[dict[str, Any]] = []
    paths = {
        "construction_static_review_json": construction_static_review_json,
        "construction_static_review_sha256s": construction_static_review_sha256s,
        "evidence_manifest_json": evidence_manifest_json,
        "evidence_package_sha256s": evidence_package_sha256s,
        "v14_audit_md": v14_audit_md,
        "current_status_md": current_status_md,
    }
    for name, path in paths.items():
        checks.extend(_file_checks(name, path))
    checks.extend(
        [
            _expect("planning_from_evidence_package_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        ]
    )
    checks.extend(
        _sha256_checks(
            construction_static_review_json,
            evidence_manifest_json,
            review_sha256s,
            package_sha256s,
        )
    )
    checks.extend(_static_review_checks(static_review))
    checks.extend(_evidence_manifest_checks(evidence_manifest))
    checks.extend(_audit_checks(v14_text, status_text))
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_default_off_selector_runtime_"
            "shadow_replay_promotion_decision_from_evidence_package_plan_v1"
        ),
        "analysis": {
            "label": label,
            "planning_only": True,
            "construction_static_review_json": str(construction_static_review_json.resolve()),
            "construction_static_review_sha256s": str(construction_static_review_sha256s.resolve()),
            "evidence_manifest_json": str(evidence_manifest_json.resolve()),
            "evidence_package_sha256s": str(evidence_package_sha256s.resolve()),
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
                "The constructed evidence package supports planning only. "
                "CAMP remains a default-off shadow reranker over fixed DP "
                "candidate tensors, using affine score_k(w)=a_k^T w over "
                "approved atoms with nonnegative simplex weights."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "source_static_review_summary": _static_review_summary(static_review),
        "evidence_package_summary": _evidence_package_summary(evidence_manifest),
        "promotion_decision_plan": _promotion_decision_plan(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_decision_from_evidence_package_plan.json", report)
    (output_dir / "runtime_promotion_decision_from_evidence_package_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["promotion_decision_plan"]
    lines = [
        "# V14 Runtime Promotion Decision From Evidence Package Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Recommendation: `{decision['recommendation']}`",
        f"- Immediate action: `{decision['immediate_action']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Required Evidence Before Any Future Promotion",
        "",
    ]
    for item in plan["required_evidence_before_any_future_promotion"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This plan did not promote atoms or selectors, deploy, train CAMP, "
            "run replay, generate candidates, modify DP, change online "
            "selection, or authorize safety/CAMP-over-DP claims.",
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
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _sha256_checks(
    static_review_json: Path,
    evidence_manifest_json: Path,
    review_sha256s: dict[str, str],
    package_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _expect(
            "static_review_sha256s_json_hash",
            review_sha256s.get(static_review_json.name),
            _sha256(static_review_json) if static_review_json.is_file() else None,
        ),
        _expect(
            "package_sha256s_manifest_hash",
            package_sha256s.get(evidence_manifest_json.name),
            _sha256(evidence_manifest_json) if evidence_manifest_json.is_file() else None,
        ),
    ]


def _static_review_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    analysis = _dict(static_review.get("analysis"))
    package = _dict(static_review.get("evidence_package_summary"))
    checks = [
        _expect("source_static_review_schema", static_review.get("schema_version"), STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_promotion_decision_planning_authorized", decision.get("promotion_decision_planning_authorized"), True),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_analysis_static_review_only", analysis.get("construction_static_review_only"), True),
        _expect("source_static_review_analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("source_static_review_analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("source_static_review_analysis_training_execution", analysis.get("training_execution"), False),
        _expect("source_static_review_analysis_replay_execution", analysis.get("replay_execution"), False),
        _expect("source_static_review_analysis_candidate_generation", analysis.get("candidate_generation"), False),
        _expect("source_static_review_analysis_dp_modification", analysis.get("dp_modification"), False),
        _expect("source_static_review_package_entries", package.get("entry_count"), EXPECTED_PACKAGE_ENTRY_COUNT),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{name}", decision.get(name), False))
    return checks


def _evidence_manifest_checks(evidence_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = _list(evidence_manifest.get("entries"))
    by_name = {entry.get("name"): entry for entry in entries if isinstance(entry, dict)}
    checks = [
        _expect("evidence_manifest_schema", evidence_manifest.get("schema_version"), EVIDENCE_PACKAGE_SCHEMA),
        _expect("evidence_manifest_score_expression", evidence_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("evidence_manifest_source_static_review_passed", evidence_manifest.get("source_static_review_passed"), True),
        _expect("evidence_manifest_entry_count", len(entries), EXPECTED_PACKAGE_ENTRY_COUNT),
        _expect("evidence_manifest_entry_names", sorted(by_name), sorted(EXPECTED_ENTRY_NAMES)),
    ]
    for name in EXPECTED_ENTRY_NAMES:
        entry = _dict(by_name.get(name))
        package_path = Path(str(entry.get("package_path", "")))
        package_sha = _sha256(package_path) if package_path.is_file() else None
        checks.extend(
            [
                _expect(f"evidence_entry_{name}_package_exists", entry.get("package_exists"), True),
                _expect(f"evidence_entry_{name}_hash_matches", entry.get("hash_matches"), True),
                _check(f"evidence_entry_{name}_package_file_exists", package_path.is_file(), str(package_path), "file"),
                _expect(f"evidence_entry_{name}_package_sha_matches_manifest", package_sha, entry.get("package_sha256")),
            ]
        )
    blocked = _dict(evidence_manifest.get("blocked_actions"))
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"evidence_manifest_blocks_{name}", blocked.get(name), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect(
            "audit_static_review_passed",
            _latest_value(v14_text, "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_passed"),
            "True",
        ),
        _expect(
            "audit_planning_authorized",
            _latest_value(v14_text, "default_off_shadow_selector_runtime_promotion_decision_plan_from_evidence_package_authorized"),
            "True",
        ),
    ]


def _promotion_decision_plan() -> dict[str, Any]:
    return {
        "recommendation": "do_not_promote_from_current_evidence_package_alone",
        "immediate_action": "record_no_promotion_closeout_only",
        "promotion_class_under_consideration": "future_default_off_shadow_selector_candidate",
        "rationale": (
            "The evidence package is internally consistent and useful for a "
            "future decision record, but it is still static/default-off "
            "shadow evidence and does not prove safety, deployment readiness, "
            "or CAMP superiority over DP Top-1."
        ),
        "required_evidence_before_any_future_promotion": [
            "explicit_human_authorization_for_actual_promotion_gate",
            "independent_closed_loop_or_holdout_evidence_defined_before_use",
            "formal_claim_scope_and_metric_thresholds_before_safety_claims",
            "fixed_dp_head_and_fixed_candidate_tensor_contract_still_holds",
            "selector_runtime_default_off_fail_closed_contract_still_holds",
            "no_reference_blend_guidance_postprocess_or_trajectory_modification",
        ],
        "no_go_conditions": [
            "dp_head_differs_from_fixed_tieriv_commit",
            "camp_generates_modifies_blends_guides_or_postprocesses_trajectories",
            "closed_loop_outcome_used_as_training_or_online_input",
            "online_selector_or_executed_trajectory_changes_without_authorization",
            "safety_or_camp_over_dp_top1_claim_from_static_evidence_only",
        ],
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    plan = _promotion_decision_plan()
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "promotion_decision_from_evidence_package_plan_ready": bool(passed),
        "recommendation": plan["recommendation"],
        "immediate_action": plan["immediate_action"],
        "promotion_class_under_consideration": plan["promotion_class_under_consideration"],
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
    if "planning_from_evidence_package_enabled" in failed_set:
        return "explicit_evidence_package_decision_planning_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("static_review_sha256s_") or name.startswith("package_sha256s_") for name in failed):
        return "evidence_package_sha256s_mismatch"
    if any(name.startswith("source_static_review_") for name in failed):
        return "source_static_review_contract_failure"
    if any(name.startswith("evidence_") for name in failed):
        return "evidence_package_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_decision_from_evidence_package_plan_contract_failure"


def _static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promotion_decision_planning_authorized": decision.get("promotion_decision_planning_authorized"),
    }


def _evidence_package_summary(evidence_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": evidence_manifest.get("schema_version"),
        "score_expression": evidence_manifest.get("score_expression"),
        "source_static_review_passed": evidence_manifest.get("source_static_review_passed"),
        "entry_count": len(_list(evidence_manifest.get("entries"))),
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
