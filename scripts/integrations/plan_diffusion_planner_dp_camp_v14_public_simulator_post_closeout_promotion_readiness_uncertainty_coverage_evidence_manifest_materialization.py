#!/usr/bin/env python3
"""Plan-only gate for v14 uncertainty/coverage evidence manifest materialization."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_only"
)
SOURCE_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.json"
)
SOURCE_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review.md"
)
PLAN_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.md"
)

EXPECTED_MANIFESTS = (
    "uncertainty_input_manifest",
    "coverage_slice_manifest",
    "atom_stability_manifest",
    "no_go_summary",
    "claim_boundary_summary",
)
EXPECTED_SOURCE = {
    "static_review_check_count": 157,
    "source_plan_check_count": 143,
    "source_plan_item_count": 5,
    "source_static_review_check_count": 134,
    "source_review_gap_count": 5,
}
BLOCKED_ACTIONS = (
    "evidence_manifest_materialization_authorized",
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
FALSE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
    "evidence_manifest_materialized_by_this_gate",
)
ANALYSIS_FALSE_FLAGS = (
    "training_execution",
    "replay_execution",
    "candidate_generation",
    "dp_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--static_review_json", type=Path, required=True)
    parser.add_argument("--static_review_md", type=Path, required=True)
    parser.add_argument("--static_review_sha256s", type=Path, required=True)
    parser.add_argument("--planned_manifest_root", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan",
        action="store_true",
        help="Explicit opt-in for read-only evidence manifest materialization planning.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        static_review_artifact_dir=args.static_review_artifact_dir,
        static_review_json=args.static_review_json,
        static_review_md=args.static_review_md,
        static_review_sha256s=args.static_review_sha256s,
        planned_manifest_root=args.planned_manifest_root,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    static_review_artifact_dir: Path,
    static_review_json: Path,
    static_review_md: Path,
    static_review_sha256s: Path,
    planned_manifest_root: Path,
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
    artifact_dir = static_review_artifact_dir.resolve()
    planned_root = planned_manifest_root.resolve()
    paths = {
        "static_review_json": static_review_json.resolve(),
        "static_review_md": static_review_md.resolve(),
        "static_review_sha256s": static_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "command": artifact_dir / "COMMAND",
        "heads": artifact_dir / "HEADS",
        "stdout": artifact_dir / "stdout.txt",
        "stderr": artifact_dir / "stderr.txt",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }
    source_static_review = _read_json_dict(paths["static_review_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    review_sha256s = _read_sha256sums(paths["static_review_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("evidence_manifest_materialization_plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _check("planned_manifest_root_not_preexisting", not planned_root.exists(), str(planned_root), "absent"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["static_review_json"], artifact_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["static_review_md"], artifact_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["static_review_sha256s"], artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, review_sha256s))
    checks.extend(_heads_checks(heads, source_static_review))
    checks.extend(_source_static_review_contract_checks(source_static_review))
    checks.extend(_audit_checks(v14_text, status_text))

    manifest_plan = _manifest_plan_items(planned_root)
    checks.extend(
        [
            _expect("manifest_plan_item_names", [item["manifest_name"] for item in manifest_plan], list(EXPECTED_MANIFESTS)),
            _expect("manifest_plan_item_count", len(manifest_plan), len(EXPECTED_MANIFESTS)),
            _expect("manifest_plan_no_materialization", [item["materialized_by_this_gate"] for item in manifest_plan], [False] * len(EXPECTED_MANIFESTS)),
            _expect("manifest_plan_no_execution", [item["authorizes_execution"] for item in manifest_plan], [False] * len(EXPECTED_MANIFESTS)),
            _expect("manifest_plan_no_claim", [item["authorizes_claim"] for item in manifest_plan], [False] * len(EXPECTED_MANIFESTS)),
            _expect("manifest_plan_requires_static_review_next", AUTHORIZED_NEXT_WORK.endswith("_static_review_only"), True),
        ]
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "uncertainty_coverage_evidence_manifest_materialization_plan_only": True,
            "static_review_artifact_dir": str(artifact_dir),
            "static_review_json": str(paths["static_review_json"]),
            "planned_manifest_root": str(planned_root),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_static_review_summary": _source_summary(source_static_review),
        "evidence_manifest_materialization_plan": manifest_plan,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / PLAN_JSON_NAME, report)
    (output_dir / PLAN_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Source Static Review Summary",
    ]
    for key, value in report["source_static_review_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Materialization Plan"])
    for item in report["evidence_manifest_materialization_plan"]:
        lines.extend(
            [
                f"- `{item['manifest_name']}` -> `{item['planned_path']}`",
                f"  - source_gap: `{item['source_gap']}`",
                f"  - required_inputs: `{', '.join(item['required_inputs'])}`",
                f"  - acceptance_checks: `{', '.join(item['acceptance_checks'])}`",
            ]
        )
    lines.extend(["", "## Checks"])
    for check in report["plan_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    lines.extend(
        [
            "",
            "This is a read-only plan. It authorizes only static review of this "
            "materialization plan and does not materialize evidence manifests, run "
            "replay, train CAMP, generate candidates, modify DP, promote, deploy, "
            "activate an online selector, or make safety/CAMP-over-DP claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def _manifest_plan_items(planned_root: Path) -> list[dict[str, Any]]:
    specs = [
        (
            "uncertainty_input_manifest",
            "future_uncertainty_input_manifest",
            ["fixed_dp_candidate_tensor_manifest", "selector_feature_manifest", "shadow_score_margin_table"],
            ["fixed_dp_head", "no_closed_loop_outcomes", "affine_score_terms_only"],
        ),
        (
            "coverage_slice_manifest",
            "future_coverage_slice_manifest",
            ["audited_split_manifest", "scenario_bucket_manifest", "source_candidate_manifest"],
            ["zero_overlap", "formal_seed_exclusion", "slice_count_is_audited"],
        ),
        (
            "atom_stability_manifest",
            "future_atom_stability_manifest",
            ["approved_atom_registry", "simplex_weight_contract", "shadow_selector_score_terms"],
            ["approved_atoms_only", "nonnegative_simplex_weights", "convex_master_contract"],
        ),
        (
            "no_go_summary",
            "future_no_go_summary",
            ["fixed_dp_boundary", "split_boundary", "selector_boundary", "claim_boundary"],
            ["all_hard_boundaries_present", "promotion_not_authorized", "deployment_not_authorized"],
        ),
        (
            "claim_boundary_summary",
            "future_claim_boundary_summary",
            ["review_evidence_gap_matrix", "promotion_readiness_boundary", "current_evidence_package_summary"],
            ["no_safety_benefit_claim", "no_camp_over_dp_top1_claim", "no_deployable_checkpoint_claim"],
        ),
    ]
    return [
        {
            "manifest_name": name,
            "source_gap": gap,
            "planned_path": str(planned_root / f"{name}.json"),
            "required_inputs": inputs,
            "acceptance_checks": checks,
            "materialized_by_this_gate": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
        }
        for name, gap, inputs, checks in specs
    ]


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("artifact_review_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{SOURCE_REVIEW_JSON_NAME}", f"./review/{SOURCE_REVIEW_JSON_NAME}", SOURCE_REVIEW_JSON_NAME)),
        _sha256sums_expect("artifact_review_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{SOURCE_REVIEW_MD_NAME}", f"./review/{SOURCE_REVIEW_MD_NAME}", SOURCE_REVIEW_MD_NAME)),
        _sha256sums_expect("artifact_review_sha256s_root_sha", artifact_files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "./review/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("source_review_json_review_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        _sha256sums_expect("source_review_md_review_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
        _expect("artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_static_review: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = _dict(source_static_review.get("analysis"))
    return [
        _expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        _expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        _expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        _expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_static_review_contract_checks(source_static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_static_review.get("final_decision"))
    analysis = _dict(source_static_review.get("analysis"))
    summary = _dict(source_static_review.get("source_plan_summary"))
    checks = [
        _expect("source_static_review_schema", source_static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_authorizes_manifest_plan", decision.get("uncertainty_coverage_evidence_manifest_materialization_plan_authorized"), True),
        _expect("source_static_review_direct_promotion", decision.get("direct_promotion_recommendation"), False),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_check_count", len(_list(source_static_review.get("review_checks"))), EXPECTED_SOURCE["static_review_check_count"]),
        _expect("source_plan_summary_plan_check_count", summary.get("plan_check_count"), EXPECTED_SOURCE["source_plan_check_count"]),
        _expect("source_plan_summary_plan_item_count", summary.get("plan_item_count"), EXPECTED_SOURCE["source_plan_item_count"]),
        _expect("source_plan_summary_source_static_review_check_count", summary.get("source_static_review_check_count"), EXPECTED_SOURCE["source_static_review_check_count"]),
        _expect("source_plan_summary_source_review_gap_count", summary.get("source_review_gap_count"), EXPECTED_SOURCE["source_review_gap_count"]),
        _expect("source_analysis_static_review_only", analysis.get("static_review_only"), True),
        _expect("source_analysis_read_only", analysis.get("read_only"), True),
        _expect("source_analysis_dp_fixed", analysis.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_analysis_{flag}", analysis.get(flag), False))
    blocked = _dict(source_static_review.get("blocked_actions"))
    for action in BLOCKED_ACTIONS:
        if action in blocked:
            checks.append(_expect(f"source_blocked_{action}", blocked.get(action), False))
        if action in decision:
            checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status_is_static_review_passed", _latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("audit_latest_eof_authorizes_manifest_plan", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("audit_manifest_plan_authorized_flag", _latest_value(v14_text, "uncertainty_coverage_evidence_manifest_materialization_plan_authorized"), "True"),
        _expect("audit_direct_promotion_false", _latest_value(v14_text, "direct_promotion_recommendation"), "False"),
        _expect("audit_selector_promotion_false", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_false", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_claim_false", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_claim_false", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        _expect("status_doc_latest_status_is_static_review_passed", _latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("status_doc_latest_eof_authorizes_manifest_plan", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("status_doc_mentions_evidence_manifest_plan", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _source_summary(source_static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_static_review.get("final_decision"))
    summary = _dict(source_static_review.get("source_plan_summary"))
    return {
        "schema_version": source_static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_review_check_count": len(_list(source_static_review.get("review_checks"))),
        "source_plan_check_count": summary.get("plan_check_count"),
        "source_plan_item_count": summary.get("plan_item_count"),
        "source_static_review_check_count": summary.get("source_static_review_check_count"),
        "source_review_gap_count": summary.get("source_review_gap_count"),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "evidence_manifest_materialization_plan_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_manifest_materialization_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "source_plan_summary")) for name in failed):
        failure_class = "source_evidence_gap_closure_plan_static_review_contract_failure"
    elif any("dp_head" in name or "dp_fixed" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    else:
        failure_class = "artifact_contract_failure"
    decision: dict[str, Any] = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "uncertainty_coverage_evidence_manifest_materialization_plan_ready": passed,
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized": passed,
        "evidence_manifest_materialization_authorized": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "static_review_evidence_manifest_materialization_plan_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_manifest_materialization_plan_static_review_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
    checks = [_check(f"{name}_exists", path.exists(), str(path), "exists")]
    if require_file:
        checks.append(_check(f"{name}_is_file", path.is_file(), str(path), "file"))
    if path.is_file() and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    expected = next((sha256sums[key] for key in keys if key in sha256sums), None)
    return _expect(name, observed, expected)


def _read_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(_read_text(path))
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not contain a JSON object")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        values[parts[1].strip()] = parts[0].strip()
    return values


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(json.dumps(_stable(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_sha256sums(output_dir: Path) -> Path:
    rows = []
    for path in sorted(p for p in output_dir.iterdir() if p.is_file() and p.name != "SHA256SUMS"):
        rows.append(f"{_sha256(path)}  {path.name}")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return sha_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    value = None
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": observed, "expected": expected}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 160 else text[:157] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
