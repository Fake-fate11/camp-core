#!/usr/bin/env python3
"""Static review for the v14 constructed runtime promotion evidence package.

This gate reviews a previously constructed evidence package. It validates the
construction report, package manifest, package hashes, and current audit
boundary. It does not promote, deploy, train, replay, generate candidates,
modify Diffusion Planner, change a selector, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_CONSTRUCTION_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_static_review_v1"
)
SOURCE_CONSTRUCTION_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_constructed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_only"
)

EXPECTED_PACKAGE_ENTRY_COUNT = 15
EXPECTED_SOURCE_ARTIFACT_NAMES = (
    "runtime_promotion_decision_plan",
    "runtime_result_review",
    "shadow_vs_top1_delta_review",
    "runtime_manifest",
    "training_artifact_static_review",
    "training_summary",
    "offline_weights_npy",
    "atom_scales_json",
    "runtime_shadow_execution_sha256s",
)
EXPECTED_STATIC_REVIEW_NAMES = (
    "static_review_json",
    "static_review_md",
    "static_review_sha256s",
)
EXPECTED_PREFLIGHT_NAMES = (
    "source_preflight_json",
    "source_preflight_md",
    "source_preflight_sha256s",
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
    parser.add_argument("--runtime_promotion_evidence_package_construction_json", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_construction_md", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_construction_sha256s", type=Path, required=True)
    parser.add_argument("--evidence_manifest_json", type=Path, required=True)
    parser.add_argument("--evidence_package_readme_md", type=Path, required=True)
    parser.add_argument("--evidence_package_sha256s", type=Path, required=True)
    parser.add_argument("--construction_script_py", type=Path, required=True)
    parser.add_argument("--construction_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_runtime_promotion_evidence_package_construction_static_review",
        action="store_true",
        help="Explicit opt-in for read-only constructed-package static review.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_promotion_evidence_package_construction_json=(
            args.runtime_promotion_evidence_package_construction_json
        ),
        runtime_promotion_evidence_package_construction_md=(
            args.runtime_promotion_evidence_package_construction_md
        ),
        runtime_promotion_evidence_package_construction_sha256s=(
            args.runtime_promotion_evidence_package_construction_sha256s
        ),
        evidence_manifest_json=args.evidence_manifest_json,
        evidence_package_readme_md=args.evidence_package_readme_md,
        evidence_package_sha256s=args.evidence_package_sha256s,
        construction_script_py=args.construction_script_py,
        construction_test_py=args.construction_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_evidence_package_construction_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_promotion_evidence_package_construction_json: Path,
    runtime_promotion_evidence_package_construction_md: Path,
    runtime_promotion_evidence_package_construction_sha256s: Path,
    evidence_manifest_json: Path,
    evidence_package_readme_md: Path,
    evidence_package_sha256s: Path,
    construction_script_py: Path,
    construction_test_py: Path,
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
    construction = _read_json_dict(runtime_promotion_evidence_package_construction_json)
    evidence_manifest = _read_json_dict(evidence_manifest_json)
    construction_sha256s = _read_sha256sums(runtime_promotion_evidence_package_construction_sha256s)
    package_sha256s = _read_sha256sums(evidence_package_sha256s)
    script_text = _read_text(construction_script_py)
    test_text = _read_text(construction_test_py)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)

    checks: list[dict[str, Any]] = []
    paths = {
        "runtime_promotion_evidence_package_construction_json": runtime_promotion_evidence_package_construction_json,
        "runtime_promotion_evidence_package_construction_md": runtime_promotion_evidence_package_construction_md,
        "runtime_promotion_evidence_package_construction_sha256s": runtime_promotion_evidence_package_construction_sha256s,
        "evidence_manifest_json": evidence_manifest_json,
        "evidence_package_readme_md": evidence_package_readme_md,
        "evidence_package_sha256s": evidence_package_sha256s,
        "construction_script_py": construction_script_py,
        "construction_test_py": construction_test_py,
        "v14_audit_md": v14_audit_md,
        "current_status_md": current_status_md,
    }
    for name, path in paths.items():
        checks.extend(_file_checks(name, path))
    checks.extend(
        [
            _expect("construction_static_review_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        ]
    )
    checks.extend(
        _construction_sha256_checks(
            runtime_promotion_evidence_package_construction_json,
            runtime_promotion_evidence_package_construction_md,
            evidence_manifest_json,
            evidence_package_readme_md,
            evidence_package_sha256s,
            construction_sha256s,
            package_sha256s,
        )
    )
    checks.extend(_construction_contract_checks(construction))
    checks.extend(_evidence_manifest_checks(construction, evidence_manifest))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_contract_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "construction_static_review_only": True,
            "runtime_promotion_evidence_package_construction_json": str(
                runtime_promotion_evidence_package_construction_json.resolve()
            ),
            "runtime_promotion_evidence_package_construction_md": str(
                runtime_promotion_evidence_package_construction_md.resolve()
            ),
            "runtime_promotion_evidence_package_construction_sha256s": str(
                runtime_promotion_evidence_package_construction_sha256s.resolve()
            ),
            "evidence_manifest_json": str(evidence_manifest_json.resolve()),
            "evidence_package_readme_md": str(evidence_package_readme_md.resolve()),
            "evidence_package_sha256s": str(evidence_package_sha256s.resolve()),
            "construction_script_py": str(construction_script_py.resolve()),
            "construction_test_py": str(construction_test_py.resolve()),
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
                "This static review only audits the constructed evidence "
                "package. CAMP remains a default-off shadow reranker over "
                "fixed DP candidate tensors, using affine score_k(w)=a_k^T w "
                "over approved atoms with nonnegative simplex weights. "
                "Executed trajectory selection remains DP Top-1."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "source_construction_summary": _source_construction_summary(construction),
        "evidence_package_summary": _evidence_package_summary(evidence_manifest),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_evidence_package_construction_static_review.json", report)
    (output_dir / "runtime_promotion_evidence_package_construction_static_review.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    construction = report["source_construction_summary"]
    package = report["evidence_package_summary"]
    lines = [
        "# V14 Runtime Promotion Evidence-Package Construction Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Promotion-decision planning authorized: `{decision['promotion_decision_planning_authorized']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Construction",
        "",
        f"- Construction status: `{construction.get('status')}`",
        f"- Construction passed: `{construction.get('passed')}`",
        f"- Authorized next work: `{construction.get('authorized_next_work')}`",
        f"- Package entries: `{construction.get('package_entry_count')}`",
        "",
        "## Evidence Package",
        "",
        f"- Manifest schema: `{package.get('schema_version')}`",
        f"- Entries: `{package.get('entry_count')}`",
        f"- Source static review passed: `{package.get('source_static_review_passed')}`",
        "",
        "This static review did not promote atoms or selectors, deploy, train "
        "CAMP, run replay, generate candidates, modify DP, change online "
        "selection, or authorize safety/CAMP-over-DP claims.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _construction_contract_checks(construction: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(construction.get("final_decision"))
    analysis = _dict(construction.get("analysis"))
    package_manifest = _list(construction.get("package_manifest"))
    construction_checks = _list(construction.get("construction_checks"))
    checks = [
        _expect("source_construction_schema", construction.get("schema_version"), SOURCE_CONSTRUCTION_SCHEMA),
        _expect("source_construction_status", decision.get("status"), SOURCE_CONSTRUCTION_STATUS),
        _expect("source_construction_passed", decision.get("passed"), True),
        _expect("source_construction_failed_checks", decision.get("failed_checks"), []),
        _expect("source_construction_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_construction_static_review_authorized", decision.get("constructed_package_static_review_authorized"), True),
        _expect("source_construction_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_construction_analysis_construction_only", analysis.get("construction_only"), True),
        _expect("source_construction_analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("source_construction_analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("source_construction_analysis_training_execution", analysis.get("training_execution"), False),
        _expect("source_construction_analysis_replay_execution", analysis.get("replay_execution"), False),
        _expect("source_construction_analysis_candidate_generation", analysis.get("candidate_generation"), False),
        _expect("source_construction_analysis_online_selector_change", analysis.get("online_selector_change"), False),
        _expect("source_construction_analysis_dp_modification", analysis.get("dp_modification"), False),
        _expect("source_construction_analysis_safety_claim", analysis.get("safety_or_camp_over_dp_claim"), False),
        _expect("source_construction_package_entry_count", len(package_manifest), EXPECTED_PACKAGE_ENTRY_COUNT),
        _expect("source_construction_package_hash_mismatches", [entry.get("name") for entry in package_manifest if isinstance(entry, dict) and not entry.get("hash_matches")], []),
        _check("source_construction_has_checks", bool(construction_checks), len(construction_checks), ">0"),
        _expect("source_construction_all_checks_passed", [check.get("name") for check in construction_checks if isinstance(check, dict) and not check.get("passed")], []),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_construction_decision_{name}", decision.get(name), False))
    return checks


def _evidence_manifest_checks(
    construction: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    construction_entries = _list(construction.get("package_manifest"))
    manifest_entries = _list(evidence_manifest.get("entries"))
    construction_by_name = {
        entry.get("name"): entry for entry in construction_entries if isinstance(entry, dict)
    }
    manifest_by_name = {
        entry.get("name"): entry for entry in manifest_entries if isinstance(entry, dict)
    }
    expected_names = sorted(
        EXPECTED_SOURCE_ARTIFACT_NAMES + EXPECTED_STATIC_REVIEW_NAMES + EXPECTED_PREFLIGHT_NAMES
    )
    checks = [
        _expect("evidence_manifest_schema", evidence_manifest.get("schema_version"), SOURCE_CONSTRUCTION_SCHEMA),
        _expect("evidence_manifest_score_expression", evidence_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("evidence_manifest_source_static_review_passed", evidence_manifest.get("source_static_review_passed"), True),
        _expect("evidence_manifest_entry_count", len(manifest_entries), EXPECTED_PACKAGE_ENTRY_COUNT),
        _expect("evidence_manifest_entry_names", sorted(manifest_by_name), expected_names),
        _expect("construction_package_entry_names", sorted(construction_by_name), expected_names),
    ]
    for name in expected_names:
        manifest_entry = _dict(manifest_by_name.get(name))
        construction_entry = _dict(construction_by_name.get(name))
        package_path = Path(str(manifest_entry.get("package_path", "")))
        source_path = Path(str(manifest_entry.get("source_path", "")))
        package_sha = _sha256(package_path) if package_path.is_file() else None
        source_sha = _sha256(source_path) if source_path.is_file() else None
        checks.extend(
            [
                _expect(f"evidence_entry_{name}_source_exists", manifest_entry.get("source_exists"), True),
                _expect(f"evidence_entry_{name}_package_exists", manifest_entry.get("package_exists"), True),
                _expect(f"evidence_entry_{name}_hash_matches", manifest_entry.get("hash_matches"), True),
                _check(f"evidence_entry_{name}_package_file_exists", package_path.is_file(), str(package_path), "file"),
                _check(f"evidence_entry_{name}_source_file_exists", source_path.is_file(), str(source_path), "file"),
                _expect(f"evidence_entry_{name}_package_sha_matches_manifest", package_sha, manifest_entry.get("package_sha256")),
                _expect(f"evidence_entry_{name}_source_sha_matches_manifest", source_sha, manifest_entry.get("source_sha256")),
                _expect(f"evidence_entry_{name}_matches_construction_package_sha", manifest_entry.get("package_sha256"), construction_entry.get("package_sha256")),
                _expect(f"evidence_entry_{name}_matches_construction_source_sha", manifest_entry.get("source_sha256"), construction_entry.get("source_sha256")),
            ]
        )
    for name in BLOCKED_ACTIONS:
        blocked = _dict(evidence_manifest.get("blocked_actions"))
        checks.append(_expect(f"evidence_manifest_blocks_{name}", blocked.get(name), False))
    return checks


def _construction_sha256_checks(
    construction_json: Path,
    construction_md: Path,
    evidence_manifest_json: Path,
    evidence_readme: Path,
    evidence_sha256s: Path,
    construction_sha256s: dict[str, str],
    package_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _expect(
            "construction_sha256s_json_hash",
            construction_sha256s.get(construction_json.name),
            _sha256(construction_json) if construction_json.is_file() else None,
        ),
        _expect(
            "construction_sha256s_md_hash",
            construction_sha256s.get(construction_md.name),
            _sha256(construction_md) if construction_md.is_file() else None,
        ),
        _expect(
            "construction_sha256s_evidence_manifest_hash",
            construction_sha256s.get("evidence_package/evidence_manifest.json"),
            _sha256(evidence_manifest_json) if evidence_manifest_json.is_file() else None,
        ),
        _expect(
            "construction_sha256s_evidence_readme_hash",
            construction_sha256s.get("evidence_package/README.md"),
            _sha256(evidence_readme) if evidence_readme.is_file() else None,
        ),
        _expect(
            "package_sha256s_manifest_hash",
            package_sha256s.get(evidence_manifest_json.name),
            _sha256(evidence_manifest_json) if evidence_manifest_json.is_file() else None,
        ),
        _expect(
            "package_sha256s_readme_hash",
            package_sha256s.get(evidence_readme.name),
            _sha256(evidence_readme) if evidence_readme.is_file() else None,
        ),
    ]


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_schema", script, "SCHEMA_VERSION"),
        _contains("source_surface_script_ready_status", script, "promotion_evidence_package_constructed"),
        _contains("source_surface_script_authorizes_static_review_only", script, "promotion_evidence_package_construction_static_review_only"),
        _contains("source_surface_script_affine_score", script, SCORE_EXPRESSION),
        _contains("source_surface_script_blocks_promotion", script, '"promotion_executed": False'),
        _contains("source_surface_script_blocks_deployment", script, '"deployment_executed": False'),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_dp_modification", script, '"dp_modification": False'),
        _contains("source_surface_script_blocks_safety_claim", script, '"safety_or_camp_over_dp_claim": False'),
        _contains("source_surface_test_pass_case", test, "test_runtime_promotion_evidence_package_construction_passes"),
        _contains("source_surface_test_requires_enable", test, "test_runtime_promotion_evidence_package_construction_requires_enable"),
        _contains("source_surface_test_rejects_wrong_eof", test, "test_runtime_promotion_evidence_package_construction_rejects_wrong_eof"),
        _contains("source_surface_test_rejects_failed_static_review", test, "test_runtime_promotion_evidence_package_construction_rejects_failed_static_review"),
        _contains("source_surface_test_rejects_promotion_leak", test, "test_runtime_promotion_evidence_package_construction_rejects_promotion_leak"),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    return [
        _check(
            "audit_latest_boundary_matches_construction_static_review_gate",
            f"current_v14_status={SOURCE_CONSTRUCTION_STATUS}" in eof
            and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "constructed evidence package with static review next",
        ),
        _check(
            "current_status_boundary_matches_construction_static_review_gate",
            f"current_v14_status={SOURCE_CONSTRUCTION_STATUS}" in status_text
            and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text,
            "current status boundary",
            "constructed evidence package with static review next",
        ),
        _contains("audit_records_constructed", eof, "default_off_shadow_selector_runtime_promotion_evidence_package_constructed=True"),
        _contains("audit_authorizes_construction_static_review", eof, "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_authorized=True"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_selector_promotion", eof, "selector_promotion_authorized=False"),
        _contains("audit_blocks_deployment", eof, "deployment_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _source_construction_summary(construction: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(construction.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "constructed_package_static_review_authorized": decision.get("constructed_package_static_review_authorized"),
        "package_entry_count": len(_list(construction.get("package_manifest"))),
    }


def _evidence_package_summary(evidence_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": evidence_manifest.get("schema_version"),
        "score_expression": evidence_manifest.get("score_expression"),
        "source_static_review_status": evidence_manifest.get("source_static_review_status"),
        "source_static_review_passed": evidence_manifest.get("source_static_review_passed"),
        "entry_count": len(_list(evidence_manifest.get("entries"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_promotion_evidence_package_construction_static_review_passed": bool(passed),
        "promotion_decision_planning_authorized": bool(passed),
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
    if "construction_static_review_enabled" in failed_set:
        return "explicit_construction_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("construction_sha256s_") or name.startswith("package_sha256s_") for name in failed):
        return "construction_sha256s_mismatch"
    if any(name.startswith("evidence_entry_") or name.startswith("evidence_manifest_") for name in failed):
        return "evidence_package_contract_failure"
    if any(name.startswith("source_surface_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("source_construction_") for name in failed):
        return "source_construction_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "runtime_promotion_evidence_package_construction_static_review_contract_failure"


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


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


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


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    if index == -1:
        return text
    return text[index + 1 :]


def _extract_line(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    return None


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
