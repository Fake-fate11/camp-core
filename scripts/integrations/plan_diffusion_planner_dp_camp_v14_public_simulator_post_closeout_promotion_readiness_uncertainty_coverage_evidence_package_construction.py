#!/usr/bin/env python3
"""Plan-only gate for v14 uncertainty/coverage evidence package construction."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_manifest_materialization_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_static_review_module()
MATERIALIZER_MODULE = SOURCE_REVIEW_MODULE.MATERIALIZER_MODULE
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATIC_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_MATERIALIZATION_SCHEMA = MATERIALIZER_MODULE.SCHEMA_VERSION
SOURCE_MATERIALIZATION_STATUS = MATERIALIZER_MODULE.READY_STATUS
MANIFEST_SCHEMA_VERSION = MATERIALIZER_MODULE.MANIFEST_SCHEMA_VERSION
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_construction_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_only"
)
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_MATERIALIZATION_JSON_NAME = MATERIALIZER_MODULE.REPORT_JSON_NAME
PLAN_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan.md"
)
EXPECTED_MANIFESTS = SOURCE_REVIEW_MODULE.EXPECTED_MANIFESTS
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 234
EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT = 200
EXPECTED_MANIFEST_COUNT = 5
PACKAGE_PLAN_ITEMS = (
    "source_artifact_index",
    "manifest_bundle_index",
    "review_chain_summary",
    "claim_boundary_register",
    "construction_static_review_plan",
)
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = SOURCE_REVIEW_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_materialization_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_materialization_json", type=Path, required=True)
    parser.add_argument("--source_manifests_dir", type=Path, required=True)
    parser.add_argument("--source_manifests_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan",
        action="store_true",
        help="Explicit opt-in for plan-only evidence package construction planning.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_materialization_artifact_dir=args.source_materialization_artifact_dir,
        source_materialization_json=args.source_materialization_json,
        source_manifests_dir=args.source_manifests_dir,
        source_manifests_sha256s=args.source_manifests_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    source_materialization_artifact_dir: Path,
    source_materialization_json: Path,
    source_manifests_dir: Path,
    source_manifests_sha256s: Path,
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
    review_artifact_dir = source_static_review_artifact_dir.resolve()
    materialization_artifact_dir = source_materialization_artifact_dir.resolve()
    manifests_dir = source_manifests_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_materialization_json": source_materialization_json.resolve(),
        "source_manifests_sha256s": source_manifests_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    review_artifact_files = {
        "command": review_artifact_dir / "COMMAND",
        "heads": review_artifact_dir / "HEADS",
        "stdout": review_artifact_dir / "stdout.txt",
        "stderr": review_artifact_dir / "stderr.txt",
        "run_exit": review_artifact_dir / "run.exit",
        "root_sha256s": review_artifact_dir / "SHA256SUMS",
        "review_json": review_artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": review_artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": review_artifact_dir / "review" / "SHA256SUMS",
    }
    manifest_files = {
        name: manifests_dir / f"{name}.json"
        for name in EXPECTED_MANIFESTS
    }

    source_review = PLAN_MODULE._read_json_dict(paths["source_static_review_json"])
    source_materialization = PLAN_MODULE._read_json_dict(paths["source_materialization_json"])
    review_root_sha256s = PLAN_MODULE._read_sha256sums(review_artifact_files["root_sha256s"])
    review_sha256s = PLAN_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    manifest_sha256s = PLAN_MODULE._read_sha256sums(paths["source_manifests_sha256s"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(review_artifact_files["heads"]))
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    manifest_payloads = {
        name: PLAN_MODULE._read_json_dict(path)
        for name, path in manifest_files.items()
        if path.is_file()
    }

    checks: list[dict[str, Any]] = [
        PLAN_MODULE._expect("package_construction_plan_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._check("source_static_review_artifact_dir_exists", review_artifact_dir.is_dir(), str(review_artifact_dir), "directory"),
        PLAN_MODULE._check("source_materialization_artifact_dir_exists", materialization_artifact_dir.is_dir(), str(materialization_artifact_dir), "directory"),
        PLAN_MODULE._check("source_manifests_dir_exists", manifests_dir.is_dir(), str(manifests_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, require_file=True))
    for name, path in review_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in manifest_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"manifest_{name}", path, require_file=True))
    checks.extend(
        [
            PLAN_MODULE._expect("source_static_review_json_matches_artifact_layout", paths["source_static_review_json"], review_artifact_files["review_json"]),
            PLAN_MODULE._expect("source_static_review_md_matches_artifact_layout", paths["source_static_review_md"], review_artifact_files["review_md"]),
            PLAN_MODULE._expect("source_static_review_sha256s_matches_artifact_layout", paths["source_static_review_sha256s"], review_artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(_review_artifact_hash_checks(review_artifact_files, review_root_sha256s, review_sha256s))
    checks.extend(_manifest_hash_checks(manifest_files, manifest_sha256s))
    checks.extend(_heads_checks(heads, source_review))
    checks.extend(_source_review_contract_checks(source_review))
    checks.extend(_source_materialization_contract_checks(source_materialization))
    checks.extend(_manifest_contract_checks(manifest_payloads))
    checks.extend(_audit_checks(v14_text, status_text))

    package_plan = _package_plan(
        source_review=source_review,
        source_materialization=source_materialization,
        manifests_dir=manifests_dir,
        label=label,
    )
    checks.extend(_package_plan_checks(package_plan))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "evidence_package_construction_plan_only": True,
            "source_static_review_artifact_dir": str(review_artifact_dir),
            "source_materialization_artifact_dir": str(materialization_artifact_dir),
            "source_manifests_dir": str(manifests_dir),
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
            name: PLAN_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **review_artifact_files, **manifest_files}.items()
        },
        "source_review_summary": _source_review_summary(source_review),
        "source_materialization_summary": _source_materialization_summary(source_materialization),
        "manifest_summary": _manifest_summary(manifest_payloads),
        "evidence_package_construction_plan": package_plan,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    PLAN_MODULE._write_json(output_dir / PLAN_JSON_NAME, report)
    (output_dir / PLAN_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    PLAN_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Package Plan",
    ]
    for item in report["evidence_package_construction_plan"]:
        lines.append(f"- `{item['item_name']}`: `{item['purpose']}`")
    lines.extend(["", "## Checks"])
    for check in report["plan_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{PLAN_MODULE._compact(check['observed'])}` expected=`{PLAN_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _review_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect("review_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect("review_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect("review_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect("review_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect("review_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect("review_artifact_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{SOURCE_REVIEW_JSON_NAME}", f"./review/{SOURCE_REVIEW_JSON_NAME}", SOURCE_REVIEW_JSON_NAME)),
        PLAN_MODULE._sha256sums_expect("review_artifact_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{SOURCE_REVIEW_MD_NAME}", f"./review/{SOURCE_REVIEW_MD_NAME}", SOURCE_REVIEW_MD_NAME)),
        PLAN_MODULE._sha256sums_expect("source_review_json_review_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        PLAN_MODULE._sha256sums_expect("source_review_md_review_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
        PLAN_MODULE._expect("review_artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _manifest_hash_checks(
    manifest_files: dict[str, Path],
    manifest_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect(
            f"manifest_{name}_sha",
            path,
            manifest_sha256s,
            (f"{name}.json", f"./{name}.json"),
        )
        for name, path in manifest_files.items()
    ]


def _heads_checks(heads: dict[str, str], source_review: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = PLAN_MODULE._dict(source_review.get("analysis"))
    return [
        PLAN_MODULE._expect("review_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        PLAN_MODULE._expect("review_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        PLAN_MODULE._expect("review_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        PLAN_MODULE._expect("review_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_review_contract_checks(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    summary = PLAN_MODULE._dict(source_review.get("manifest_summary"))
    checks = [
        PLAN_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        PLAN_MODULE._expect("source_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("source_review_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_review_package_plan_authorized", decision.get("evidence_package_construction_plan_authorized"), True),
        PLAN_MODULE._expect("source_review_check_count", len(PLAN_MODULE._list(source_review.get("review_checks"))), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        PLAN_MODULE._expect("source_review_manifest_count", summary.get("manifest_count"), EXPECTED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_review_all_no_execution", summary.get("all_no_execution"), True),
        PLAN_MODULE._expect("source_review_all_no_claim", summary.get("all_no_claim"), True),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    return checks


def _source_materialization_contract_checks(source_materialization: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_materialization.get("final_decision"))
    checks = [
        PLAN_MODULE._expect("source_materialization_schema", source_materialization.get("schema_version"), SOURCE_MATERIALIZATION_SCHEMA),
        PLAN_MODULE._expect("source_materialization_status", decision.get("status"), SOURCE_MATERIALIZATION_STATUS),
        PLAN_MODULE._expect("source_materialization_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_materialization_manifest_count", decision.get("materialized_manifest_count"), EXPECTED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_materialization_check_count", len(PLAN_MODULE._list(source_materialization.get("materialization_checks"))), EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_materialization_decision_{action}", decision.get(action), False))
    return checks


def _manifest_contract_checks(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        PLAN_MODULE._expect("manifest_names", list(manifests), list(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("manifest_count", len(manifests), len(EXPECTED_MANIFESTS)),
    ]
    for name in EXPECTED_MANIFESTS:
        manifest = manifests.get(name, {})
        checks.extend(
            [
                PLAN_MODULE._expect(f"manifest_{name}_schema", manifest.get("schema_version"), MANIFEST_SCHEMA_VERSION),
                PLAN_MODULE._expect(f"manifest_{name}_name", manifest.get("manifest_name"), name),
                PLAN_MODULE._expect(f"manifest_{name}_dp_fixed", manifest.get("current_dp_head"), FIXED_DP_HEAD),
                PLAN_MODULE._expect(f"manifest_{name}_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
                PLAN_MODULE._expect(f"manifest_{name}_materialized", manifest.get("materialized_by_this_gate"), True),
                PLAN_MODULE._expect(f"manifest_{name}_no_execution", manifest.get("authorizes_execution"), False),
                PLAN_MODULE._expect(f"manifest_{name}_no_claim", manifest.get("authorizes_claim"), False),
            ]
        )
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("audit_latest_status_is_static_review_passed", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("audit_latest_eof_authorizes_package_plan", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("audit_package_plan_authorized", PLAN_MODULE._latest_value(v14_text, "evidence_package_construction_plan_authorized"), "True"),
        PLAN_MODULE._expect("audit_selector_promotion_false", PLAN_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        PLAN_MODULE._expect("audit_deployment_false", PLAN_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        PLAN_MODULE._expect("audit_safety_claim_false", PLAN_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        PLAN_MODULE._expect("audit_camp_over_dp_claim_false", PLAN_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        PLAN_MODULE._expect("status_doc_latest_status_is_static_review_passed", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("status_doc_latest_eof_authorizes_package_plan", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("status_doc_mentions_package_plan", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _package_plan(
    *,
    source_review: dict[str, Any],
    source_materialization: dict[str, Any],
    manifests_dir: Path,
    label: str | None,
) -> list[dict[str, Any]]:
    source_decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    materialization_decision = PLAN_MODULE._dict(source_materialization.get("final_decision"))
    specs = [
        ("source_artifact_index", "Index source plan, materialization, manifest, and static-review artifacts."),
        ("manifest_bundle_index", "Reference the five materialized uncertainty/coverage evidence manifests."),
        ("review_chain_summary", "Preserve the audited plan, materialization, and static-review chain."),
        ("claim_boundary_register", "Carry no-promotion, no-deployment, and no safety/CAMP-over-DP claim boundaries."),
        ("construction_static_review_plan", "Prepare only a static review of any future constructed evidence package."),
    ]
    return [
        {
            "item_name": name,
            "label": label,
            "purpose": purpose,
            "source_static_review_status": source_decision.get("status"),
            "source_materialization_status": materialization_decision.get("status"),
            "source_manifests_dir": str(manifests_dir.resolve()),
            "required_manifest_names": list(EXPECTED_MANIFESTS),
            "package_constructed_by_this_gate": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        }
        for name, purpose in specs
    ]


def _package_plan_checks(package_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("package_plan_item_names", [item["item_name"] for item in package_plan], list(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("package_plan_item_count", len(package_plan), len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("package_plan_no_construction", [item["package_constructed_by_this_gate"] for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("package_plan_no_execution", [item["authorizes_execution"] for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("package_plan_no_claim", [item["authorizes_claim"] for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("package_plan_no_promotion", [item["authorizes_promotion"] for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
    ]


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(PLAN_MODULE._list(source_review.get("review_checks"))),
    }


def _source_materialization_summary(source_materialization: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_materialization.get("final_decision"))
    return {
        "schema_version": source_materialization.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "materialized_manifest_count": decision.get("materialized_manifest_count"),
        "materialization_check_count": len(PLAN_MODULE._list(source_materialization.get("materialization_checks"))),
    }


def _manifest_summary(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "manifest_count": len(manifests),
        "manifest_names": list(manifests),
        "all_materialized": all(manifest.get("materialized_by_this_gate") is True for manifest in manifests.values()),
        "all_no_execution": all(manifest.get("authorizes_execution") is False for manifest in manifests.values()),
        "all_no_claim": all(manifest.get("authorizes_claim") is False for manifest in manifests.values()),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "package_construction_plan_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_package_construction_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "manifest_", "package_plan_")) for name in failed):
        failure_class = "source_evidence_package_construction_plan_contract_failure"
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
        "uncertainty_coverage_evidence_package_construction_plan_ready": passed,
        "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized": passed,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "static_review_uncertainty_coverage_evidence_package_construction_plan_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_package_construction_plan_static_review_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
