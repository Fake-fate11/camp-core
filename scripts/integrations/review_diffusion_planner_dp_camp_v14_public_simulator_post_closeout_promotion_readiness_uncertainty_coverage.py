#!/usr/bin/env python3
"""Read-only v14 uncertainty/coverage review gate."""

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
    "promotion_readiness_uncertainty_coverage_review_preflight_static_review_v1"
)
SOURCE_PREFLIGHT_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_preflight_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passed"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready"
)
SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_only"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_only"
)
STATIC_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.json"
)
STATIC_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.md"
)
PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.md"
REVIEW_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review.md"

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
FALSE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
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
EXPECTED_PREFLIGHT_ITEMS = (
    "source_artifact_inventory",
    "fixed_dp_candidate_tensor_boundary",
    "uncertainty_input_manifest",
    "coverage_slice_manifest",
    "atom_stability_manifest",
    "default_off_fail_closed_boundary",
    "claim_and_promotion_no_go_boundary",
)
EXPECTED_NO_GO = (
    "dp_head_drift",
    "camp_candidate_generation_or_repair",
    "closed_loop_outcome_input",
    "full36_or_formal_seed_11_12_13",
    "non_affine_score",
    "non_simplex_or_nonconvex_master",
    "promotion_deployment_online_or_claim_bundled",
)
EXPECTED_FUTURE_MANIFESTS = (
    "future_uncertainty_input_manifest",
    "future_coverage_slice_manifest",
    "future_atom_stability_manifest",
    "future_no_go_summary",
    "future_claim_boundary_summary",
)
EXPECTED_REVIEW_ITEMS = (
    "fixed_dp_candidate_tensor_boundary",
    "score_margin_uncertainty_surface",
    "coverage_slice_matrix",
    "candidate_tensor_support_coverage",
    "atom_contribution_stability",
    "default_off_fail_closed_boundary",
    "claim_and_promotion_boundary",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_preflight_md", type=Path, required=True)
    parser.add_argument("--source_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review",
        action="store_true",
        help="Explicit opt-in for the read-only uncertainty/coverage review.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        preflight_static_review_artifact_dir=args.preflight_static_review_artifact_dir,
        preflight_static_review_json=args.preflight_static_review_json,
        preflight_static_review_md=args.preflight_static_review_md,
        preflight_static_review_sha256s=args.preflight_static_review_sha256s,
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_preflight_md=args.source_preflight_md,
        source_preflight_sha256s=args.source_preflight_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    preflight_static_review_artifact_dir: Path,
    preflight_static_review_json: Path,
    preflight_static_review_md: Path,
    preflight_static_review_sha256s: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_preflight_md: Path,
    source_preflight_sha256s: Path,
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
    static_artifact = preflight_static_review_artifact_dir.resolve()
    preflight_artifact = source_preflight_artifact_dir.resolve()
    paths = {
        "preflight_static_review_json": preflight_static_review_json.resolve(),
        "preflight_static_review_md": preflight_static_review_md.resolve(),
        "preflight_static_review_sha256s": preflight_static_review_sha256s.resolve(),
        "source_preflight_json": source_preflight_json.resolve(),
        "source_preflight_md": source_preflight_md.resolve(),
        "source_preflight_sha256s": source_preflight_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_files = {
        "command": static_artifact / "COMMAND",
        "heads": static_artifact / "HEADS",
        "stdout": static_artifact / "stdout.txt",
        "stderr": static_artifact / "stderr.txt",
        "run_exit": static_artifact / "run.exit",
        "root_sha256s": static_artifact / "SHA256SUMS",
        "review_json": static_artifact / "review" / STATIC_REVIEW_JSON_NAME,
        "review_md": static_artifact / "review" / STATIC_REVIEW_MD_NAME,
        "review_sha256s": static_artifact / "review" / "SHA256SUMS",
    }
    preflight_files = {
        "command": preflight_artifact / "COMMAND",
        "heads": preflight_artifact / "HEADS",
        "stdout": preflight_artifact / "stdout.txt",
        "stderr": preflight_artifact / "stderr.txt",
        "run_exit": preflight_artifact / "run.exit",
        "root_sha256s": preflight_artifact / "SHA256SUMS",
        "preflight_json": preflight_artifact / "preflight" / PREFLIGHT_JSON_NAME,
        "preflight_md": preflight_artifact / "preflight" / PREFLIGHT_MD_NAME,
        "preflight_sha256s": preflight_artifact / "preflight" / "SHA256SUMS",
    }
    source_static_review = _read_json_dict(paths["preflight_static_review_json"])
    source_preflight = _read_json_dict(paths["source_preflight_json"])
    static_root_sha256s = _read_sha256sums(static_files["root_sha256s"])
    static_review_sha256s = _read_sha256sums(paths["preflight_static_review_sha256s"])
    preflight_root_sha256s = _read_sha256sums(preflight_files["root_sha256s"])
    preflight_sha256s = _read_sha256sums(paths["source_preflight_sha256s"])
    static_heads = _parse_key_values(_read_text(static_files["heads"]))
    preflight_heads = _parse_key_values(_read_text(preflight_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("uncertainty_coverage_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_preflight_artifact_dir_exists", preflight_artifact.is_dir(), str(preflight_artifact), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_files.items():
        checks.extend(_path_checks(f"static_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in preflight_files.items():
        checks.extend(_path_checks(f"preflight_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["preflight_static_review_json"], static_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["preflight_static_review_md"], static_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["preflight_static_review_sha256s"], static_files["review_sha256s"]),
            _expect("source_preflight_json_matches_artifact_layout", paths["source_preflight_json"], preflight_files["preflight_json"]),
            _expect("source_preflight_md_matches_artifact_layout", paths["source_preflight_md"], preflight_files["preflight_md"]),
            _expect("source_preflight_sha256s_matches_artifact_layout", paths["source_preflight_sha256s"], preflight_files["preflight_sha256s"]),
        ]
    )
    checks.extend(_static_artifact_hash_checks(static_files, static_root_sha256s, static_review_sha256s))
    checks.extend(_preflight_artifact_hash_checks(preflight_files, preflight_root_sha256s, preflight_sha256s))
    checks.extend(_heads_checks(static_heads, preflight_heads, source_static_review, source_preflight))
    checks.extend(_source_static_review_contract_checks(source_static_review))
    checks.extend(_source_preflight_contract_checks(source_preflight))
    checks.extend(_audit_checks(v14_text, status_text))

    review_items = _review_items(source_preflight)
    evidence_gaps = _evidence_gaps(source_preflight)
    checks.extend(
        [
            _expect("review_item_names", [item["name"] for item in review_items], list(EXPECTED_REVIEW_ITEMS)),
            _expect("review_item_count", len(review_items), len(EXPECTED_REVIEW_ITEMS)),
            _expect("review_items_authorize_execution", [item["authorizes_execution"] for item in review_items], [False] * len(EXPECTED_REVIEW_ITEMS)),
            _expect("review_items_authorize_claim", [item["authorizes_claim"] for item in review_items], [False] * len(EXPECTED_REVIEW_ITEMS)),
            _expect("evidence_gap_names", [item["name"] for item in evidence_gaps], list(EXPECTED_FUTURE_MANIFESTS)),
            _expect("evidence_gap_count", len(evidence_gaps), len(EXPECTED_FUTURE_MANIFESTS)),
            _expect("evidence_gaps_block_promotion_claim", [item["blocks_promotion_or_claim"] for item in evidence_gaps], [True] * len(EXPECTED_FUTURE_MANIFESTS)),
        ]
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "uncertainty_coverage_review_only": True,
            "read_only": True,
            "preflight_static_review_artifact_dir": str(static_artifact),
            "source_preflight_artifact_dir": str(preflight_artifact),
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
            "direct_promotion_recommendation": False,
            "score_expression": SCORE_EXPRESSION,
            "math_boundary": (
                "This review inspects only already-audited preflight/static-review "
                "artifacts. CAMP remains a default-off reranker over fixed DP "
                "candidate tensors with affine score_k(w)=a_k^T w and convex "
                "simplex/CVaR/L2 master constraints."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **static_files, **preflight_files}.items()
        },
        "source_static_review_summary": _source_static_summary(source_static_review),
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "uncertainty_coverage_review": review_items,
        "evidence_gap_matrix": evidence_gaps,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        f"- direct_promotion_recommendation: `{decision['direct_promotion_recommendation']}`",
        "",
        "## Source Static Review Summary",
    ]
    for key, value in report["source_static_review_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Source Preflight Summary")
    for key, value in report["source_preflight_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Review Items"])
    for item in report["uncertainty_coverage_review"]:
        lines.append(
            f"- `{item['name']}`: status=`{item['status']}` "
            f"finding=`{item['finding']}`"
        )
    lines.extend(["", "## Evidence Gap Matrix"])
    for item in report["evidence_gap_matrix"]:
        lines.append(
            f"- `{item['name']}`: available=`{item['available_from_current_artifacts']}` "
            f"blocks_promotion_or_claim=`{item['blocks_promotion_or_claim']}`"
        )
    lines.extend(["", "## Checks"])
    for check in report["review_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    lines.extend(
        [
            "",
            "This is a read-only uncertainty/coverage review. It does not run "
            "replay, train CAMP, generate candidates, modify DP, promote, deploy, "
            "activate an online selector, or make safety/CAMP-over-DP claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def _static_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("static_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("static_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("static_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("static_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("static_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("static_artifact_review_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{STATIC_REVIEW_JSON_NAME}", f"./review/{STATIC_REVIEW_JSON_NAME}", STATIC_REVIEW_JSON_NAME)),
        _sha256sums_expect("static_artifact_review_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{STATIC_REVIEW_MD_NAME}", f"./review/{STATIC_REVIEW_MD_NAME}", STATIC_REVIEW_MD_NAME)),
        _sha256sums_expect("static_artifact_review_json_review_sha", artifact_files["review_json"], review_sha256s, (STATIC_REVIEW_JSON_NAME, f"./{STATIC_REVIEW_JSON_NAME}")),
        _sha256sums_expect("static_artifact_review_md_review_sha", artifact_files["review_md"], review_sha256s, (STATIC_REVIEW_MD_NAME, f"./{STATIC_REVIEW_MD_NAME}")),
        _expect("static_artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _preflight_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    preflight_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("preflight_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("preflight_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("preflight_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("preflight_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("preflight_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("preflight_artifact_json_root_sha", artifact_files["preflight_json"], root_sha256s, (f"preflight/{PREFLIGHT_JSON_NAME}", f"./preflight/{PREFLIGHT_JSON_NAME}", PREFLIGHT_JSON_NAME)),
        _sha256sums_expect("preflight_artifact_md_root_sha", artifact_files["preflight_md"], root_sha256s, (f"preflight/{PREFLIGHT_MD_NAME}", f"./preflight/{PREFLIGHT_MD_NAME}", PREFLIGHT_MD_NAME)),
        _sha256sums_expect("preflight_artifact_sha256s_root_sha", artifact_files["preflight_sha256s"], root_sha256s, ("preflight/SHA256SUMS", "./preflight/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("source_preflight_json_preflight_sha", artifact_files["preflight_json"], preflight_sha256s, (PREFLIGHT_JSON_NAME, f"./{PREFLIGHT_JSON_NAME}")),
        _sha256sums_expect("source_preflight_md_preflight_sha", artifact_files["preflight_md"], preflight_sha256s, (PREFLIGHT_MD_NAME, f"./{PREFLIGHT_MD_NAME}")),
        _expect("preflight_artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(
    static_heads: dict[str, str],
    preflight_heads: dict[str, str],
    source_static_review: dict[str, Any],
    source_preflight: dict[str, Any],
) -> list[dict[str, Any]]:
    static_analysis = _dict(source_static_review.get("analysis"))
    preflight_analysis = _dict(source_preflight.get("analysis"))
    return [
        _expect("static_heads_dp_fixed", static_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("preflight_heads_dp_fixed", preflight_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("static_heads_camp_matches_origin", static_heads.get("camp_head"), static_heads.get("camp_origin_main")),
        _expect("preflight_heads_camp_matches_origin", preflight_heads.get("camp_head"), preflight_heads.get("camp_origin_main")),
        _expect("static_heads_camp_matches_source_analysis", static_heads.get("camp_head"), static_analysis.get("current_camp_head")),
        _expect("preflight_heads_camp_matches_source_analysis", preflight_heads.get("camp_head"), preflight_analysis.get("current_camp_head")),
    ]


def _source_static_review_contract_checks(source_static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_static_review.get("final_decision"))
    analysis = _dict(source_static_review.get("analysis"))
    summary = _dict(source_static_review.get("source_preflight_summary"))
    checks = [
        _expect("source_static_review_schema", source_static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_uncertainty_coverage_review_authorized", decision.get("uncertainty_coverage_review_authorized"), True),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_static_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_read_only", analysis.get("read_only"), True),
        _expect("source_static_review_check_failures", _failed_source_checks(source_static_review, "review_checks"), []),
        _expect("source_static_review_summary_status", summary.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_static_review_summary_passed", summary.get("passed"), True),
        _expect("source_static_review_summary_check_count", summary.get("check_count"), 190),
        _expect("source_static_review_summary_review_preflight_item_count", summary.get("review_preflight_item_count"), 7),
        _expect("source_static_review_summary_artifact_manifest_requirement_count", summary.get("artifact_manifest_requirement_count"), 7),
        _expect("source_static_review_summary_no_go_status_count", summary.get("no_go_status_count"), 7),
        _expect("source_static_review_summary_future_review_requirement_count", summary.get("future_review_requirement_count"), 5),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_static_review_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_static_review_blocked_{action}", _dict(source_static_review.get("blocked_actions")).get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_preflight_contract_checks(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_preflight.get("final_decision"))
    analysis = _dict(source_preflight.get("analysis"))
    review_preflight = _list(source_preflight.get("uncertainty_coverage_review_preflight"))
    artifact_requirements = _list(source_preflight.get("artifact_manifest_requirements"))
    future_requirements = _list(source_preflight.get("future_review_requirements"))
    no_go_status = _list(source_preflight.get("no_go_status"))
    checks = [
        _expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
        _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks", decision.get("failed_checks"), []),
        _expect("source_preflight_failure_class", decision.get("failure_class"), None),
        _expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK),
        _expect("source_preflight_static_review_authorized", decision.get("uncertainty_coverage_review_preflight_static_review_authorized"), True),
        _expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_preflight_read_only", analysis.get("read_only"), True),
        _expect("source_preflight_preflight_only", analysis.get("preflight_only"), True),
        _expect("source_preflight_item_names", _names(review_preflight), list(EXPECTED_PREFLIGHT_ITEMS)),
        _expect("source_preflight_item_count", len(review_preflight), len(EXPECTED_PREFLIGHT_ITEMS)),
        _expect("source_preflight_items_no_execution", [item.get("authorizes_execution") for item in review_preflight], [False] * len(EXPECTED_PREFLIGHT_ITEMS)),
        _expect("source_preflight_items_no_claim", [item.get("authorizes_claim") for item in review_preflight], [False] * len(EXPECTED_PREFLIGHT_ITEMS)),
        _expect("source_preflight_artifact_manifest_count", len(artifact_requirements), 7),
        _expect("source_preflight_future_manifest_names", [item.get("name") for item in artifact_requirements if str(item.get("name", "")).startswith("future_")], list(EXPECTED_FUTURE_MANIFESTS)),
        _expect("source_preflight_future_manifest_status", [item.get("status") for item in artifact_requirements if str(item.get("name", "")).startswith("future_")], ["required_before_review_execution"] * len(EXPECTED_FUTURE_MANIFESTS)),
        _expect("source_preflight_future_review_requirement_count", len(future_requirements), 5),
        _expect("source_preflight_no_go_names", _names(no_go_status), list(EXPECTED_NO_GO)),
        _expect("source_preflight_no_go_triggered", [item.get("triggered") for item in no_go_status], [False] * len(EXPECTED_NO_GO)),
        _expect("source_preflight_check_failures", _failed_source_checks(source_preflight, "preflight_checks"), []),
        _expect("source_preflight_check_count", len(_list(source_preflight.get("preflight_checks"))), 190),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_preflight_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_preflight_blocked_{action}", _dict(source_preflight.get("blocked_actions")).get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_preflight_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_STATIC_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_uncertainty_coverage_review", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_uncertainty_coverage_review", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_preflight_static_review_passed", _latest_value(v14_text, "uncertainty_coverage_review_preflight_static_review_passed"), "True"),
        _expect("audit_uncertainty_coverage_review_authorized", _latest_value(v14_text, "uncertainty_coverage_review_authorized"), "True"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _review_items(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    gap_names = {item["name"] for item in _evidence_gaps(source_preflight)}
    return [
        {
            "name": "fixed_dp_candidate_tensor_boundary",
            "status": "confirmed_from_preflight_static_review",
            "finding": "review remains limited to fixed DP candidate tensors and does not alter trajectories",
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "score_margin_uncertainty_surface",
            "status": "insufficient_for_promotion_claim",
            "finding": "future_uncertainty_input_manifest is required before any promotion or CAMP-over-DP claim",
            "source_gap_present": "future_uncertainty_input_manifest" in gap_names,
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "coverage_slice_matrix",
            "status": "insufficient_for_promotion_claim",
            "finding": "future_coverage_slice_manifest is required before any promotion or safety claim",
            "source_gap_present": "future_coverage_slice_manifest" in gap_names,
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "candidate_tensor_support_coverage",
            "status": "insufficient_for_promotion_claim",
            "finding": "current evidence does not establish coverage beyond the audited fixed-DP candidate source",
            "source_gap_present": "future_coverage_slice_manifest" in gap_names,
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "atom_contribution_stability",
            "status": "insufficient_for_promotion_claim",
            "finding": "future_atom_stability_manifest is required; no atom or weight promotion is authorized",
            "source_gap_present": "future_atom_stability_manifest" in gap_names,
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "default_off_fail_closed_boundary",
            "status": "confirmed_from_preflight",
            "finding": "selector remains default-off and this review does not change executed trajectories",
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
        {
            "name": "claim_and_promotion_boundary",
            "status": "no_go_for_promotion_or_claim",
            "finding": "future no-go and claim-boundary summaries remain required before promotion planning can resume",
            "source_gap_present": {"future_no_go_summary", "future_claim_boundary_summary"}.issubset(gap_names),
            "authorizes_execution": False,
            "authorizes_claim": False,
        },
    ]


def _evidence_gaps(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    artifact_requirements = _list(source_preflight.get("artifact_manifest_requirements"))
    future_items = [
        item
        for item in artifact_requirements
        if isinstance(item, dict) and str(item.get("name", "")).startswith("future_")
    ]
    by_name = {str(item.get("name")): item for item in future_items}
    rows = []
    for name in EXPECTED_FUTURE_MANIFESTS:
        source = by_name.get(name, {})
        rows.append(
            {
                "name": name,
                "source_preflight_status": source.get("status"),
                "available_from_current_artifacts": False,
                "blocks_promotion_or_claim": True,
                "resolution": "materialize_or_audit_manifest_before_any_promotion_deployment_or_claim",
            }
        )
    return rows


def _source_static_summary(source_static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_static_review.get("final_decision"))
    return {
        "schema_version": source_static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(source_static_review.get("review_checks"))),
    }


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_check_count": len(_list(source_preflight.get("preflight_checks"))),
        "review_preflight_item_count": len(_list(source_preflight.get("uncertainty_coverage_review_preflight"))),
        "artifact_manifest_requirement_count": len(_list(source_preflight.get("artifact_manifest_requirements"))),
        "future_manifest_requirement_count": len(_evidence_gaps(source_preflight)),
        "no_go_status_count": len(_list(source_preflight.get("no_go_status"))),
        "future_review_requirement_count": len(_list(source_preflight.get("future_review_requirements"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_uncertainty_coverage_review_passed": bool(passed),
        "uncertainty_coverage_review_static_review_authorized": bool(passed),
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "recommendation": "static_review_this_uncertainty_coverage_review_only",
        "immediate_action": "static_review_uncertainty_coverage_review_only",
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "uncertainty_coverage_review_enabled" in failed_set:
        return "explicit_uncertainty_coverage_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "static_heads_dp_fixed", "preflight_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_static_review") for name in failed):
        return "source_uncertainty_coverage_preflight_static_review_contract_failure"
    if any(name.startswith("source_preflight") for name in failed):
        return "source_uncertainty_coverage_preflight_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_uncertainty_coverage_review_failure"


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.is_dir()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "directory")]
    if require_file and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.is_file() and path.stat().st_size > 0, path.stat().st_size if path.is_file() else None, ">0 bytes"))
    return checks


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    listed = [sha256sums.get(key) for key in keys if key in sha256sums]
    return _check(name, observed is not None and observed in listed, {"observed": observed, "listed": listed, "keys": keys}, "matching sha256 listed in SHA256SUMS")


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


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
            key = parts[1].strip()
            value = parts[0]
            values[key] = value
            values[key.removeprefix("./")] = value
            values[Path(key).name] = value
    return values


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        values[key] = value
        values[key.lower()] = value
    return values


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _names(value: Any) -> list[str]:
    return [
        str(item.get("name"))
        for item in _list(value)
        if isinstance(item, dict) and item.get("name")
    ]


def _failed_source_checks(payload: dict[str, Any], field: str) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(payload.get(field))
        if isinstance(check, dict) and not check.get("passed")
    ]


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    return value


def _compact(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 160 else text[:157] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
