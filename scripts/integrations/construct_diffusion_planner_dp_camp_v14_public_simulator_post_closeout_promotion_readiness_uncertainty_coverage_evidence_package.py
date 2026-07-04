#!/usr/bin/env python3
"""Construct a v14 uncertainty/coverage evidence package from audited sources.

This gate materializes only audit evidence files. It does not promote,
deploy, train, replay, generate candidates, modify Diffusion Planner, change
online selection, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_package_construction_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_static_review_module()
PLAN_MODULE = SOURCE_STATIC_REVIEW_MODULE.PLAN_MODULE
SOURCE_PLAN_MODULE = SOURCE_STATIC_REVIEW_MODULE.SOURCE_PLAN_MODULE
MATERIALIZER_MODULE = SOURCE_PLAN_MODULE.MATERIALIZER_MODULE

FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_STATIC_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATIC_REVIEW_SCHEMA = SOURCE_STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_PLAN_SCHEMA = SOURCE_PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = SOURCE_PLAN_MODULE.READY_STATUS
SOURCE_MATERIALIZATION_STATIC_REVIEW_SCHEMA = SOURCE_PLAN_MODULE.SOURCE_STATIC_REVIEW_SCHEMA
SOURCE_MATERIALIZATION_STATIC_REVIEW_STATUS = SOURCE_PLAN_MODULE.SOURCE_STATIC_REVIEW_STATUS
SOURCE_MATERIALIZATION_SCHEMA = MATERIALIZER_MODULE.SCHEMA_VERSION
SOURCE_MATERIALIZATION_STATUS = MATERIALIZER_MODULE.READY_STATUS
MANIFEST_SCHEMA_VERSION = MATERIALIZER_MODULE.MANIFEST_SCHEMA_VERSION
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_construction_v1"
)
EVIDENCE_PACKAGE_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_constructed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_only"
)
SOURCE_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_STATIC_REVIEW_MD_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_PLAN_JSON_NAME = SOURCE_PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = SOURCE_PLAN_MODULE.PLAN_MD_NAME
SOURCE_MATERIALIZATION_STATIC_REVIEW_JSON_NAME = SOURCE_PLAN_MODULE.SOURCE_REVIEW_JSON_NAME
SOURCE_MATERIALIZATION_STATIC_REVIEW_MD_NAME = SOURCE_PLAN_MODULE.SOURCE_REVIEW_MD_NAME
SOURCE_MATERIALIZATION_JSON_NAME = MATERIALIZER_MODULE.REPORT_JSON_NAME
CONSTRUCTION_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction.json"
)
CONSTRUCTION_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction.md"
)
PACKAGE_DIR_NAME = "evidence_package"
PACKAGE_JSON_FILES = (
    "source_artifact_index.json",
    "manifest_bundle_index.json",
    "review_chain_summary.json",
    "claim_boundary_register.json",
    "construction_static_review_plan.json",
    "evidence_package_manifest.json",
)
PACKAGE_FILES = PACKAGE_JSON_FILES + ("README.md",)
EXPECTED_STATIC_REVIEW_CHECK_COUNT = 139
EXPECTED_PLAN_CHECK_COUNT = 186
EXPECTED_MATERIALIZATION_STATIC_REVIEW_CHECK_COUNT = 234
EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT = 200
EXPECTED_MANIFEST_COUNT = 5
EXPECTED_MANIFESTS = SOURCE_PLAN_MODULE.EXPECTED_MANIFESTS
PACKAGE_PLAN_ITEMS = SOURCE_STATIC_REVIEW_MODULE.PACKAGE_PLAN_ITEMS
BLOCKED_ACTIONS = SOURCE_STATIC_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_STATIC_REVIEW_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = SOURCE_STATIC_REVIEW_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_md", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_materialization_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_materialization_static_review_json", type=Path, required=True)
    parser.add_argument("--source_materialization_static_review_md", type=Path, required=True)
    parser.add_argument("--source_materialization_static_review_sha256s", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction",
        action="store_true",
        help="Explicit opt-in to construct the read-only uncertainty/coverage evidence package.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_md=args.source_plan_md,
        source_plan_sha256s=args.source_plan_sha256s,
        source_materialization_static_review_artifact_dir=args.source_materialization_static_review_artifact_dir,
        source_materialization_static_review_json=args.source_materialization_static_review_json,
        source_materialization_static_review_md=args.source_materialization_static_review_md,
        source_materialization_static_review_sha256s=args.source_materialization_static_review_sha256s,
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
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction,
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
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_md: Path,
    source_plan_sha256s: Path,
    source_materialization_static_review_artifact_dir: Path,
    source_materialization_static_review_json: Path,
    source_materialization_static_review_md: Path,
    source_materialization_static_review_sha256s: Path,
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
    static_review_artifact_dir = source_static_review_artifact_dir.resolve()
    plan_artifact_dir = source_plan_artifact_dir.resolve()
    materialization_static_review_artifact_dir = source_materialization_static_review_artifact_dir.resolve()
    materialization_artifact_dir = source_materialization_artifact_dir.resolve()
    manifests_dir = source_manifests_dir.resolve()
    output_root = output_dir.resolve()
    package_dir = output_root / PACKAGE_DIR_NAME
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_plan_json": source_plan_json.resolve(),
        "source_plan_md": source_plan_md.resolve(),
        "source_plan_sha256s": source_plan_sha256s.resolve(),
        "source_materialization_static_review_json": source_materialization_static_review_json.resolve(),
        "source_materialization_static_review_md": source_materialization_static_review_md.resolve(),
        "source_materialization_static_review_sha256s": source_materialization_static_review_sha256s.resolve(),
        "source_materialization_json": source_materialization_json.resolve(),
        "source_manifests_sha256s": source_manifests_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_review_artifact_files = {
        "command": static_review_artifact_dir / "COMMAND",
        "heads": static_review_artifact_dir / "HEADS",
        "stdout": static_review_artifact_dir / "stdout.txt",
        "stderr": static_review_artifact_dir / "stderr.txt",
        "run_exit": static_review_artifact_dir / "run.exit",
        "root_sha256s": static_review_artifact_dir / "SHA256SUMS",
        "review_json": static_review_artifact_dir / "review" / SOURCE_STATIC_REVIEW_JSON_NAME,
        "review_md": static_review_artifact_dir / "review" / SOURCE_STATIC_REVIEW_MD_NAME,
        "review_sha256s": static_review_artifact_dir / "review" / "SHA256SUMS",
    }
    plan_artifact_files = {
        "command": plan_artifact_dir / "COMMAND",
        "heads": plan_artifact_dir / "HEADS",
        "stdout": plan_artifact_dir / "stdout.txt",
        "stderr": plan_artifact_dir / "stderr.txt",
        "run_exit": plan_artifact_dir / "run.exit",
        "root_sha256s": plan_artifact_dir / "SHA256SUMS",
        "plan_json": plan_artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_md": plan_artifact_dir / "plan" / SOURCE_PLAN_MD_NAME,
        "plan_sha256s": plan_artifact_dir / "plan" / "SHA256SUMS",
    }
    materialization_static_review_artifact_files = {
        "command": materialization_static_review_artifact_dir / "COMMAND",
        "heads": materialization_static_review_artifact_dir / "HEADS",
        "stdout": materialization_static_review_artifact_dir / "stdout.txt",
        "stderr": materialization_static_review_artifact_dir / "stderr.txt",
        "run_exit": materialization_static_review_artifact_dir / "run.exit",
        "root_sha256s": materialization_static_review_artifact_dir / "SHA256SUMS",
        "review_json": materialization_static_review_artifact_dir / "review" / SOURCE_MATERIALIZATION_STATIC_REVIEW_JSON_NAME,
        "review_md": materialization_static_review_artifact_dir / "review" / SOURCE_MATERIALIZATION_STATIC_REVIEW_MD_NAME,
        "review_sha256s": materialization_static_review_artifact_dir / "review" / "SHA256SUMS",
    }
    manifest_files = {
        name: manifests_dir / f"{name}.json"
        for name in EXPECTED_MANIFESTS
    }

    source_static_review = PLAN_MODULE._read_json_dict(paths["source_static_review_json"])
    source_plan = PLAN_MODULE._read_json_dict(paths["source_plan_json"])
    source_materialization_static_review = PLAN_MODULE._read_json_dict(
        paths["source_materialization_static_review_json"]
    )
    source_materialization = PLAN_MODULE._read_json_dict(paths["source_materialization_json"])
    source_manifests = {
        name: PLAN_MODULE._read_json_dict(path)
        for name, path in manifest_files.items()
        if path.is_file()
    }
    static_review_root_sha256s = PLAN_MODULE._read_sha256sums(static_review_artifact_files["root_sha256s"])
    static_review_sha256s = PLAN_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    plan_root_sha256s = PLAN_MODULE._read_sha256sums(plan_artifact_files["root_sha256s"])
    plan_sha256s = PLAN_MODULE._read_sha256sums(paths["source_plan_sha256s"])
    materialization_static_review_root_sha256s = PLAN_MODULE._read_sha256sums(
        materialization_static_review_artifact_files["root_sha256s"]
    )
    materialization_static_review_sha256s = PLAN_MODULE._read_sha256sums(
        paths["source_materialization_static_review_sha256s"]
    )
    manifest_sha256s = PLAN_MODULE._read_sha256sums(paths["source_manifests_sha256s"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(static_review_artifact_files["heads"]))
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        PLAN_MODULE._expect("construction_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._check("source_static_review_artifact_dir_exists", static_review_artifact_dir.is_dir(), str(static_review_artifact_dir), "directory"),
        PLAN_MODULE._check("source_plan_artifact_dir_exists", plan_artifact_dir.is_dir(), str(plan_artifact_dir), "directory"),
        PLAN_MODULE._check("source_materialization_static_review_artifact_dir_exists", materialization_static_review_artifact_dir.is_dir(), str(materialization_static_review_artifact_dir), "directory"),
        PLAN_MODULE._check("source_materialization_artifact_dir_exists", materialization_artifact_dir.is_dir(), str(materialization_artifact_dir), "directory"),
        PLAN_MODULE._check("source_manifests_dir_exists", manifests_dir.is_dir(), str(manifests_dir), "directory"),
        PLAN_MODULE._check("evidence_package_absent_before_write", not package_dir.exists(), str(package_dir), "absent"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, require_file=True))
    for name, path in static_review_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"static_review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in plan_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"plan_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in materialization_static_review_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"materialization_static_review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in manifest_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"manifest_{name}", path, require_file=True))
    checks.extend(
        [
            PLAN_MODULE._expect("source_static_review_json_matches_artifact_layout", paths["source_static_review_json"], static_review_artifact_files["review_json"]),
            PLAN_MODULE._expect("source_static_review_md_matches_artifact_layout", paths["source_static_review_md"], static_review_artifact_files["review_md"]),
            PLAN_MODULE._expect("source_static_review_sha256s_matches_artifact_layout", paths["source_static_review_sha256s"], static_review_artifact_files["review_sha256s"]),
            PLAN_MODULE._expect("source_plan_json_matches_artifact_layout", paths["source_plan_json"], plan_artifact_files["plan_json"]),
            PLAN_MODULE._expect("source_plan_md_matches_artifact_layout", paths["source_plan_md"], plan_artifact_files["plan_md"]),
            PLAN_MODULE._expect("source_plan_sha256s_matches_artifact_layout", paths["source_plan_sha256s"], plan_artifact_files["plan_sha256s"]),
            PLAN_MODULE._expect("source_materialization_static_review_json_matches_artifact_layout", paths["source_materialization_static_review_json"], materialization_static_review_artifact_files["review_json"]),
            PLAN_MODULE._expect("source_materialization_static_review_md_matches_artifact_layout", paths["source_materialization_static_review_md"], materialization_static_review_artifact_files["review_md"]),
            PLAN_MODULE._expect("source_materialization_static_review_sha256s_matches_artifact_layout", paths["source_materialization_static_review_sha256s"], materialization_static_review_artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(
        _static_review_artifact_hash_checks(
            "static_review",
            static_review_artifact_files,
            static_review_root_sha256s,
            static_review_sha256s,
            SOURCE_STATIC_REVIEW_JSON_NAME,
            SOURCE_STATIC_REVIEW_MD_NAME,
        )
    )
    checks.extend(_plan_artifact_hash_checks(plan_artifact_files, plan_root_sha256s, plan_sha256s))
    checks.extend(
        _static_review_artifact_hash_checks(
            "materialization_static_review",
            materialization_static_review_artifact_files,
            materialization_static_review_root_sha256s,
            materialization_static_review_sha256s,
            SOURCE_MATERIALIZATION_STATIC_REVIEW_JSON_NAME,
            SOURCE_MATERIALIZATION_STATIC_REVIEW_MD_NAME,
        )
    )
    checks.extend(_manifest_hash_checks(manifest_files, manifest_sha256s))
    checks.extend(_heads_checks(heads, source_static_review))
    checks.extend(_source_static_review_contract_checks(source_static_review))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_source_materialization_static_review_contract_checks(source_materialization_static_review))
    checks.extend(_source_materialization_contract_checks(source_materialization))
    checks.extend(_source_manifest_contract_checks(source_manifests))
    checks.extend(_audit_checks(v14_text, status_text))

    package_payloads = _package_payloads(
        label=label,
        source_static_review=source_static_review,
        source_plan=source_plan,
        source_materialization_static_review=source_materialization_static_review,
        source_materialization=source_materialization,
        source_manifests=source_manifests,
        source_paths={**paths, "source_manifests_dir": manifests_dir},
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    checks.extend(_package_payload_checks(package_payloads))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "construction_only": True,
            "read_only_source_reviews": True,
            "source_static_review_artifact_dir": str(static_review_artifact_dir),
            "source_plan_artifact_dir": str(plan_artifact_dir),
            "source_materialization_static_review_artifact_dir": str(materialization_static_review_artifact_dir),
            "source_materialization_artifact_dir": str(materialization_artifact_dir),
            "source_manifests_dir": str(manifests_dir),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_root),
            "evidence_package_dir": str(package_dir),
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
            for name, path in {
                **paths,
                **static_review_artifact_files,
                **plan_artifact_files,
                **materialization_static_review_artifact_files,
                **manifest_files,
            }.items()
        },
        "source_static_review_summary": _source_static_review_summary(source_static_review),
        "source_plan_summary": _source_plan_summary(source_plan),
        "source_materialization_static_review_summary": _source_materialization_static_review_summary(source_materialization_static_review),
        "source_materialization_summary": _source_materialization_summary(source_materialization),
        "source_manifest_summary": _source_manifest_summary(source_manifests),
        "evidence_package_payloads": package_payloads,
        "evidence_package_files": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "construction_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_files: list[dict[str, Any]] = []
    if report["final_decision"]["passed"]:
        package_dir = output_dir / PACKAGE_DIR_NAME
        package_dir.mkdir(parents=True, exist_ok=False)
        payloads = PLAN_MODULE._dict(report.get("evidence_package_payloads"))
        for file_name in PACKAGE_JSON_FILES:
            path = package_dir / file_name
            PLAN_MODULE._write_json(path, PLAN_MODULE._dict(payloads.get(file_name)))
            package_files.append(_package_file_record(file_name, path, kind="json"))
        readme_path = package_dir / "README.md"
        readme_path.write_text(_package_readme(report), encoding="utf-8")
        package_files.append(_package_file_record("README.md", readme_path, kind="markdown"))
        sha_path = PLAN_MODULE._write_sha256sums(package_dir)
        package_files.append(_package_file_record("SHA256SUMS", sha_path, kind="sha256sums"))
    report["evidence_package_files"] = package_files
    PLAN_MODULE._write_json(output_dir / CONSTRUCTION_JSON_NAME, report)
    (output_dir / CONSTRUCTION_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    PLAN_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        f"- evidence_package_file_count: `{len(report['evidence_package_files'])}`",
        "",
        "## Evidence Package Files",
    ]
    for item in report["evidence_package_files"]:
        lines.append(f"- `{item['name']}`: `{item['sha256']}`")
    lines.extend(["", "## Checks"])
    for check in report["construction_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{PLAN_MODULE._compact(check['observed'])}` expected=`{PLAN_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _static_review_artifact_hash_checks(
    prefix: str,
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
    json_name: str,
    md_name: str,
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{json_name}", f"./review/{json_name}", json_name)),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_artifact_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{md_name}", f"./review/{md_name}", md_name)),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_json_review_sha", artifact_files["review_json"], review_sha256s, (json_name, f"./{json_name}")),
        PLAN_MODULE._sha256sums_expect(f"{prefix}_md_review_sha", artifact_files["review_md"], review_sha256s, (md_name, f"./{md_name}")),
        PLAN_MODULE._expect(f"{prefix}_artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _plan_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect("plan_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect("plan_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect("plan_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect("plan_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect("plan_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect("plan_artifact_json_root_sha", artifact_files["plan_json"], root_sha256s, (f"plan/{SOURCE_PLAN_JSON_NAME}", f"./plan/{SOURCE_PLAN_JSON_NAME}", SOURCE_PLAN_JSON_NAME)),
        PLAN_MODULE._sha256sums_expect("plan_artifact_md_root_sha", artifact_files["plan_md"], root_sha256s, (f"plan/{SOURCE_PLAN_MD_NAME}", f"./plan/{SOURCE_PLAN_MD_NAME}", SOURCE_PLAN_MD_NAME)),
        PLAN_MODULE._sha256sums_expect("source_plan_json_plan_sha", artifact_files["plan_json"], plan_sha256s, (SOURCE_PLAN_JSON_NAME, f"./{SOURCE_PLAN_JSON_NAME}")),
        PLAN_MODULE._sha256sums_expect("source_plan_md_plan_sha", artifact_files["plan_md"], plan_sha256s, (SOURCE_PLAN_MD_NAME, f"./{SOURCE_PLAN_MD_NAME}")),
        PLAN_MODULE._expect("plan_artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
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


def _heads_checks(heads: dict[str, str], source_static_review: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = PLAN_MODULE._dict(source_static_review.get("analysis"))
    return [
        PLAN_MODULE._expect("static_review_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        PLAN_MODULE._expect("static_review_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        PLAN_MODULE._expect("static_review_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        PLAN_MODULE._expect("static_review_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_static_review_contract_checks(source_static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_static_review.get("final_decision"))
    package_summary = PLAN_MODULE._dict(source_static_review.get("package_plan_summary"))
    checks = [
        PLAN_MODULE._expect("source_static_review_schema", source_static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        PLAN_MODULE._expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("source_static_review_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_static_review_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_static_review_construction_authorized", decision.get("evidence_package_construction_authorized"), True),
        PLAN_MODULE._expect("source_static_review_package_constructed_false", decision.get("evidence_package_constructed_by_this_gate"), False),
        PLAN_MODULE._expect("source_static_review_check_count", len(PLAN_MODULE._list(source_static_review.get("review_checks"))), EXPECTED_STATIC_REVIEW_CHECK_COUNT),
        PLAN_MODULE._expect("source_static_review_package_plan_item_count", package_summary.get("package_plan_item_count"), len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_static_review_all_no_construction", package_summary.get("all_no_construction"), True),
        PLAN_MODULE._expect("source_static_review_all_no_execution", package_summary.get("all_no_execution"), True),
        PLAN_MODULE._expect("source_static_review_all_no_claim", package_summary.get("all_no_claim"), True),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_static_review_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(PLAN_MODULE._expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    manifest_summary = PLAN_MODULE._dict(source_plan.get("manifest_summary"))
    package_plan = [PLAN_MODULE._dict(item) for item in PLAN_MODULE._list(source_plan.get("evidence_package_construction_plan"))]
    checks = [
        PLAN_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        PLAN_MODULE._expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("source_plan_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_plan_no_package_constructed", decision.get("evidence_package_constructed_by_this_gate"), False),
        PLAN_MODULE._expect("source_plan_check_count", len(PLAN_MODULE._list(source_plan.get("plan_checks"))), EXPECTED_PLAN_CHECK_COUNT),
        PLAN_MODULE._expect("source_manifest_count", manifest_summary.get("manifest_count"), EXPECTED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_manifest_all_no_execution", manifest_summary.get("all_no_execution"), True),
        PLAN_MODULE._expect("source_manifest_all_no_claim", manifest_summary.get("all_no_claim"), True),
        PLAN_MODULE._expect("source_package_plan_item_names", [item.get("item_name") for item in package_plan], list(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_construction", [item.get("package_constructed_by_this_gate") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_execution", [item.get("authorizes_execution") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_claim", [item.get("authorizes_claim") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_promotion", [item.get("authorizes_promotion") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_plan_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(PLAN_MODULE._expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(PLAN_MODULE._expect(f"source_plan_analysis_{flag}", PLAN_MODULE._dict(source_plan.get("analysis")).get(flag), False))
    return checks


def _source_materialization_static_review_contract_checks(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    summary = PLAN_MODULE._dict(source_review.get("manifest_summary"))
    checks = [
        PLAN_MODULE._expect("source_materialization_static_review_schema", source_review.get("schema_version"), SOURCE_MATERIALIZATION_STATIC_REVIEW_SCHEMA),
        PLAN_MODULE._expect("source_materialization_static_review_status", decision.get("status"), SOURCE_MATERIALIZATION_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("source_materialization_static_review_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_materialization_static_review_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_materialization_static_review_check_count", len(PLAN_MODULE._list(source_review.get("review_checks"))), EXPECTED_MATERIALIZATION_STATIC_REVIEW_CHECK_COUNT),
        PLAN_MODULE._expect("source_materialization_static_review_manifest_count", summary.get("manifest_count"), EXPECTED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_materialization_static_review_all_no_execution", summary.get("all_no_execution"), True),
        PLAN_MODULE._expect("source_materialization_static_review_all_no_claim", summary.get("all_no_claim"), True),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_materialization_static_review_decision_{action}", decision.get(action), False))
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
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(PLAN_MODULE._expect(f"source_materialization_decision_{flag}", decision.get(flag), False))
    return checks


def _source_manifest_contract_checks(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
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
        PLAN_MODULE._expect("audit_latest_eof_authorizes_construction", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("audit_construction_authorized", PLAN_MODULE._latest_value(v14_text, "evidence_package_construction_authorized"), "True"),
        PLAN_MODULE._expect("audit_package_not_constructed_yet", PLAN_MODULE._latest_value(v14_text, "evidence_package_constructed_by_this_gate"), "False"),
        PLAN_MODULE._expect("audit_selector_promotion_false", PLAN_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        PLAN_MODULE._expect("audit_deployment_false", PLAN_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        PLAN_MODULE._expect("audit_safety_claim_false", PLAN_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        PLAN_MODULE._expect("audit_camp_over_dp_claim_false", PLAN_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        PLAN_MODULE._expect("status_doc_latest_status_is_static_review_passed", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        PLAN_MODULE._expect("status_doc_latest_eof_authorizes_construction", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("status_doc_mentions_construction_next", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _package_payloads(
    *,
    label: str | None,
    source_static_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_materialization_static_review: dict[str, Any],
    source_materialization: dict[str, Any],
    source_manifests: dict[str, dict[str, Any]],
    source_paths: dict[str, Path],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    source_index = _source_artifact_index(source_paths)
    manifest_bundle = _manifest_bundle_index(source_manifests, source_paths["source_manifests_dir"])
    review_chain = _review_chain_summary(
        source_static_review=source_static_review,
        source_plan=source_plan,
        source_materialization_static_review=source_materialization_static_review,
        source_materialization=source_materialization,
    )
    claim_boundary = _claim_boundary_register(current_camp_head=current_camp_head, current_dp_head=current_dp_head)
    static_review_plan = _construction_static_review_plan()
    package_manifest = {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "label": label,
        "package_files": list(PACKAGE_FILES),
        "source_artifact_count": len(source_index["source_artifacts"]),
        "manifest_count": manifest_bundle["manifest_count"],
        "review_chain_steps": len(review_chain["review_chain"]),
        "current_camp_head": current_camp_head,
        "current_dp_head": current_dp_head,
        "required_dp_head": FIXED_DP_HEAD,
        "score_expression": SCORE_EXPRESSION,
        "evidence_package_constructed_by_this_gate": True,
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
    }
    return {
        "source_artifact_index.json": source_index,
        "manifest_bundle_index.json": manifest_bundle,
        "review_chain_summary.json": review_chain,
        "claim_boundary_register.json": claim_boundary,
        "construction_static_review_plan.json": static_review_plan,
        "evidence_package_manifest.json": package_manifest,
    }


def _source_artifact_index(source_paths: dict[str, Path]) -> dict[str, Any]:
    artifacts = [
        ("source_static_review_json", "source_package_plan_static_review"),
        ("source_static_review_md", "source_package_plan_static_review"),
        ("source_static_review_sha256s", "source_package_plan_static_review"),
        ("source_plan_json", "source_package_plan"),
        ("source_plan_md", "source_package_plan"),
        ("source_plan_sha256s", "source_package_plan"),
        ("source_materialization_static_review_json", "source_materialization_static_review"),
        ("source_materialization_static_review_md", "source_materialization_static_review"),
        ("source_materialization_static_review_sha256s", "source_materialization_static_review"),
        ("source_materialization_json", "source_materialization"),
        ("source_manifests_sha256s", "source_manifests"),
    ]
    return {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "source_artifacts": [
            {
                "name": name,
                "role": role,
                "path": str(source_paths[name]),
                "sha256": PLAN_MODULE._sha256(source_paths[name]) if source_paths[name].is_file() else None,
            }
            for name, role in artifacts
        ],
        "source_manifests_dir": str(source_paths["source_manifests_dir"]),
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
    }


def _manifest_bundle_index(
    source_manifests: dict[str, dict[str, Any]],
    manifests_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "manifest_count": len(source_manifests),
        "manifests": [
            {
                "manifest_name": name,
                "path": str((manifests_dir / f"{name}.json").resolve()),
                "sha256": PLAN_MODULE._sha256(manifests_dir / f"{name}.json") if (manifests_dir / f"{name}.json").is_file() else None,
                "source_gap": source_manifests.get(name, {}).get("source_gap"),
                "materialized_by_this_gate": source_manifests.get(name, {}).get("materialized_by_this_gate"),
                "authorizes_execution": False,
                "authorizes_claim": False,
                "authorizes_promotion": False,
            }
            for name in EXPECTED_MANIFESTS
        ],
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
    }


def _review_chain_summary(
    *,
    source_static_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_materialization_static_review: dict[str, Any],
    source_materialization: dict[str, Any],
) -> dict[str, Any]:
    steps = [
        ("materialization", source_materialization, "materialization_checks"),
        ("materialization_static_review", source_materialization_static_review, "review_checks"),
        ("evidence_package_construction_plan", source_plan, "plan_checks"),
        ("evidence_package_construction_plan_static_review", source_static_review, "review_checks"),
        ("evidence_package_construction", {}, "construction_checks"),
    ]
    return {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "review_chain": [
            {
                "step": name,
                "schema_version": payload.get("schema_version", SCHEMA_VERSION if name == "evidence_package_construction" else None),
                "status": PLAN_MODULE._dict(payload.get("final_decision")).get("status", READY_STATUS if name == "evidence_package_construction" else None),
                "passed": PLAN_MODULE._dict(payload.get("final_decision")).get("passed", True if name == "evidence_package_construction" else None),
                "check_count": len(PLAN_MODULE._list(payload.get(check_key))),
                "authorizes_execution": False,
                "authorizes_claim": False,
                "authorizes_promotion": False,
            }
            for name, payload, check_key in steps
        ],
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
    }


def _claim_boundary_register(*, current_camp_head: str, current_dp_head: str) -> dict[str, Any]:
    register = {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "current_camp_head": current_camp_head,
        "current_dp_head": current_dp_head,
        "required_dp_head": FIXED_DP_HEAD,
        "score_expression": SCORE_EXPRESSION,
        "evidence_package_constructed_by_this_gate": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_generation_by_camp_authorized_by_current_boundary": False,
        "trajectory_generation_by_camp_authorized_by_current_boundary": False,
        "trajectory_modification_by_camp_authorized_by_current_boundary": False,
        "dp_modification_authorized_by_current_boundary": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "formal_seed_11_12_13_execution_authorized": False,
    }
    for action in BLOCKED_ACTIONS:
        register[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        register[flag] = False
    return register


def _construction_static_review_plan() -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_PACKAGE_SCHEMA_VERSION,
        "review_target": "constructed_uncertainty_coverage_evidence_package",
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "required_package_files": list(PACKAGE_FILES),
        "required_checks": [
            "package_files_exist_and_hash",
            "source_artifact_index_matches_audited_sources",
            "manifest_bundle_matches_five_materialized_manifests",
            "review_chain_preserves_passed_statuses",
            "claim_boundary_register_blocks_promotion_deployment_and_claims",
        ],
        "authorizes_execution": False,
        "authorizes_claim": False,
        "authorizes_promotion": False,
    }


def _package_payload_checks(package_payloads: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        PLAN_MODULE._expect("package_payload_file_names", list(package_payloads), list(PACKAGE_JSON_FILES)),
        PLAN_MODULE._expect("package_payload_file_count", len(package_payloads), len(PACKAGE_JSON_FILES)),
    ]
    for file_name, payload in package_payloads.items():
        data = PLAN_MODULE._dict(payload)
        checks.extend(
            [
                PLAN_MODULE._expect(f"package_payload_{file_name}_schema", data.get("schema_version"), EVIDENCE_PACKAGE_SCHEMA_VERSION),
                PLAN_MODULE._expect(f"package_payload_{file_name}_no_execution", data.get("authorizes_execution"), False),
                PLAN_MODULE._expect(f"package_payload_{file_name}_no_claim", data.get("authorizes_claim"), False),
                PLAN_MODULE._expect(f"package_payload_{file_name}_no_promotion", data.get("authorizes_promotion"), False),
            ]
        )
    return checks


def _package_file_record(name: str, path: Path, *, kind: str) -> dict[str, Any]:
    return {
        "name": name,
        "kind": kind,
        "path": str(path.resolve()),
        "sha256": PLAN_MODULE._sha256(path) if path.is_file() else None,
        "exists": path.is_file(),
    }


def _package_readme(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package",
            "",
            f"- Status: `{decision['status']}`",
            f"- Fixed DP head: `{FIXED_DP_HEAD}`",
            f"- Score expression: `{SCORE_EXPRESSION}`",
            "- This package is audit evidence only.",
            "- It does not authorize promotion, deployment, online selector activation, or safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _source_static_review_summary(source_static_review: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_static_review.get("final_decision"))
    return {
        "schema_version": source_static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(PLAN_MODULE._list(source_static_review.get("review_checks"))),
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    package_plan = PLAN_MODULE._list(source_plan.get("evidence_package_construction_plan"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(PLAN_MODULE._list(source_plan.get("plan_checks"))),
        "package_plan_item_count": len(package_plan),
    }


def _source_materialization_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
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


def _source_manifest_summary(source_manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "manifest_count": len(source_manifests),
        "manifest_names": list(source_manifests),
        "all_materialized": all(manifest.get("materialized_by_this_gate") is True for manifest in source_manifests.values()),
        "all_no_execution": all(manifest.get("authorizes_execution") is False for manifest in source_manifests.values()),
        "all_no_claim": all(manifest.get("authorizes_claim") is False for manifest in source_manifests.values()),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "construction_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_package_construction_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "manifest_", "package_")) for name in failed):
        failure_class = "source_evidence_package_construction_contract_failure"
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
        "uncertainty_coverage_evidence_package_constructed": passed,
        "evidence_package_constructed_by_this_gate": passed,
        "uncertainty_coverage_evidence_package_construction_static_review_authorized": passed,
        "evidence_package_construction_static_review_authorized": passed,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "static_review_uncertainty_coverage_evidence_package_construction_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_package_construction_static_review_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
