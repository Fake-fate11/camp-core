#!/usr/bin/env python3
"""Construct the v14 runtime promotion evidence package.

This gate materializes a read-only evidence package from the passed static
review. It copies already-reviewed immutable evidence into a package directory
and writes a manifest. It does not promote, deploy, train, replay, generate
candidates, modify Diffusion Planner, change a selector, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_static_review_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_passed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_constructed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_static_review_only"
)

EXPECTED_ARTIFACT_NAMES = (
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
    parser.add_argument("--runtime_promotion_evidence_package_static_review_json", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_static_review_md", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_runtime_promotion_evidence_package_construction",
        action="store_true",
        help="Explicit opt-in for read-only evidence-package construction.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_promotion_evidence_package_static_review_json=(
            args.runtime_promotion_evidence_package_static_review_json
        ),
        runtime_promotion_evidence_package_static_review_md=(
            args.runtime_promotion_evidence_package_static_review_md
        ),
        runtime_promotion_evidence_package_static_review_sha256s=(
            args.runtime_promotion_evidence_package_static_review_sha256s
        ),
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_evidence_package_construction,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_promotion_evidence_package_static_review_json: Path,
    runtime_promotion_evidence_package_static_review_md: Path,
    runtime_promotion_evidence_package_static_review_sha256s: Path,
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
    static_review = _read_json_dict(runtime_promotion_evidence_package_static_review_json)
    sha256sums = _read_sha256sums(runtime_promotion_evidence_package_static_review_sha256s)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)

    checks: list[dict[str, Any]] = []
    checks.extend(
        _file_checks(
            "runtime_promotion_evidence_package_static_review_json",
            runtime_promotion_evidence_package_static_review_json,
        )
    )
    checks.extend(
        _file_checks(
            "runtime_promotion_evidence_package_static_review_md",
            runtime_promotion_evidence_package_static_review_md,
        )
    )
    checks.extend(
        _file_checks(
            "runtime_promotion_evidence_package_static_review_sha256s",
            runtime_promotion_evidence_package_static_review_sha256s,
        )
    )
    checks.extend(
        [
            _expect("construction_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
            _check("v14_audit_md_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
            _check("current_status_md_exists", current_status_md.is_file(), str(current_status_md), "file"),
        ]
    )
    checks.extend(
        _static_review_sha256_checks(
            runtime_promotion_evidence_package_static_review_json,
            runtime_promotion_evidence_package_static_review_md,
            sha256sums,
        )
    )
    checks.extend(_static_review_contract_checks(static_review))
    checks.extend(_source_artifact_checks(static_review))
    checks.extend(_audit_contract_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    package_manifest = (
        _materialize_package(
            output_dir=output_dir,
            static_review=static_review,
            static_review_json=runtime_promotion_evidence_package_static_review_json,
            static_review_md=runtime_promotion_evidence_package_static_review_md,
            static_review_sha256s=runtime_promotion_evidence_package_static_review_sha256s,
        )
        if passed
        else []
    )
    package_checks = _package_checks(package_manifest) if passed else []
    checks.extend(package_checks)
    passed = all(check["passed"] for check in checks)

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "construction_only": True,
            "runtime_promotion_evidence_package_static_review_json": str(
                runtime_promotion_evidence_package_static_review_json.resolve()
            ),
            "runtime_promotion_evidence_package_static_review_md": str(
                runtime_promotion_evidence_package_static_review_md.resolve()
            ),
            "runtime_promotion_evidence_package_static_review_sha256s": str(
                runtime_promotion_evidence_package_static_review_sha256s.resolve()
            ),
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
                "This construction gate only materializes immutable evidence "
                "reviewed by the prior static gate. CAMP remains a default-off "
                "shadow reranker over fixed DP candidate tensors, using affine "
                "score_k(w)=a_k^T w over approved atoms with nonnegative "
                "simplex weights. Executed trajectory selection remains DP Top-1."
            ),
        },
        "source_hashes": {
            "runtime_promotion_evidence_package_static_review_json": (
                _sha256(runtime_promotion_evidence_package_static_review_json)
                if runtime_promotion_evidence_package_static_review_json.is_file()
                else None
            ),
            "runtime_promotion_evidence_package_static_review_md": (
                _sha256(runtime_promotion_evidence_package_static_review_md)
                if runtime_promotion_evidence_package_static_review_md.is_file()
                else None
            ),
            "runtime_promotion_evidence_package_static_review_sha256s": (
                _sha256(runtime_promotion_evidence_package_static_review_sha256s)
                if runtime_promotion_evidence_package_static_review_sha256s.is_file()
                else None
            ),
        },
        "source_static_review_summary": _source_static_review_summary(static_review),
        "package_manifest": package_manifest,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "construction_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_evidence_package_construction.json", report)
    (output_dir / "runtime_promotion_evidence_package_construction.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_static_review_summary"]
    lines = [
        "# V14 Runtime Promotion Evidence-Package Construction",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Constructed-package static review authorized: `{decision['constructed_package_static_review_authorized']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Static Review",
        "",
        f"- Static review status: `{summary.get('status')}`",
        f"- Static review passed: `{summary.get('passed')}`",
        f"- Authorized next work: `{summary.get('authorized_next_work')}`",
        f"- Review checks / failed checks: `{summary.get('review_check_count')}` / `{summary.get('failed_check_count')}`",
        "",
        "## Package Manifest",
        "",
        "| Name | Source SHA-256 | Package SHA-256 | Hash matches |",
        "| --- | --- | --- | ---: |",
    ]
    for item in report["package_manifest"]:
        lines.append(
            f"| `{item['name']}` | `{item['source_sha256']}` | "
            f"`{item['package_sha256']}` | `{item['hash_matches']}` |"
        )
    lines.extend(
        [
            "",
            "This construction gate did not promote atoms or selectors, deploy, "
            "train CAMP, run replay, generate candidates, modify DP, change "
            "online selection, or authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["construction_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _materialize_package(
    *,
    output_dir: Path,
    static_review: dict[str, Any],
    static_review_json: Path,
    static_review_md: Path,
    static_review_sha256s: Path,
) -> list[dict[str, Any]]:
    package_dir = output_dir / "evidence_package"
    evidence_dir = package_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    fixed_sources = [
        ("static_review_json", static_review_json, "static_review"),
        ("static_review_md", static_review_md, "static_review"),
        ("static_review_sha256s", static_review_sha256s, "static_review"),
    ]
    analysis = _dict(static_review.get("analysis"))
    for key, name in (
        ("runtime_promotion_evidence_package_preflight_json", "source_preflight_json"),
        ("runtime_promotion_evidence_package_preflight_md", "source_preflight_md"),
        ("runtime_promotion_evidence_package_preflight_sha256s", "source_preflight_sha256s"),
    ):
        path_text = analysis.get(key)
        if path_text:
            fixed_sources.append((name, Path(str(path_text)), "source_preflight"))

    for name, source, role in fixed_sources:
        entries.append(_copy_package_file(evidence_dir, name, source, role))

    for item in _list(static_review.get("artifact_manifest_review")):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name"))
        source = Path(str(item.get("path", "")))
        entries.append(_copy_package_file(evidence_dir, name, source, "source_artifact"))

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "score_expression": SCORE_EXPRESSION,
        "source_static_review_status": _dict(static_review.get("final_decision")).get("status"),
        "source_static_review_passed": _dict(static_review.get("final_decision")).get("passed"),
        "entries": entries,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
    }
    _write_json(package_dir / "evidence_manifest.json", manifest)
    (package_dir / "README.md").write_text(
        "\n".join(
            [
                "# V14 Runtime Promotion Evidence Package",
                "",
                "This package contains immutable evidence copied from the passed static review.",
                "It is not a deployment artifact and does not promote a selector.",
                "Executed trajectory selection remains DP Top-1.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_sha256sums(package_dir)
    return entries


def _copy_package_file(evidence_dir: Path, name: str, source: Path, role: str) -> dict[str, Any]:
    target_dir = evidence_dir / name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source.is_file():
        shutil.copyfile(source, target)
    source_sha = _sha256(source) if source.is_file() else None
    package_sha = _sha256(target) if target.is_file() else None
    return {
        "name": name,
        "role": role,
        "source_path": str(source),
        "package_path": str(target),
        "source_sha256": source_sha,
        "package_sha256": package_sha,
        "source_exists": source.is_file(),
        "package_exists": target.is_file(),
        "hash_matches": source_sha == package_sha and source_sha is not None,
    }


def _static_review_contract_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    analysis = _dict(static_review.get("analysis"))
    review_checks = _list(static_review.get("review_checks"))
    checks = [
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_static_review_construction_authorized", decision.get("evidence_package_construction_authorized"), True),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_analysis_static_review_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("source_static_review_analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("source_static_review_analysis_training_execution", analysis.get("training_execution"), False),
        _expect("source_static_review_analysis_replay_execution", analysis.get("replay_execution"), False),
        _expect("source_static_review_analysis_candidate_generation", analysis.get("candidate_generation"), False),
        _expect("source_static_review_analysis_online_selector_change", analysis.get("online_selector_change"), False),
        _expect("source_static_review_analysis_dp_modification", analysis.get("dp_modification"), False),
        _expect("source_static_review_analysis_safety_claim", analysis.get("safety_or_camp_over_dp_claim"), False),
        _check("source_static_review_has_checks", bool(review_checks), len(review_checks), ">0"),
        _expect(
            "source_static_review_all_checks_passed",
            [check.get("name") for check in review_checks if isinstance(check, dict) and not check.get("passed")],
            [],
        ),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{name}", decision.get(name), False))
    return checks


def _source_artifact_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    review = _list(static_review.get("artifact_manifest_review"))
    by_name = {item.get("name"): item for item in review if isinstance(item, dict)}
    checks = [_expect("source_artifact_names", sorted(by_name), sorted(EXPECTED_ARTIFACT_NAMES))]
    for name in EXPECTED_ARTIFACT_NAMES:
        item = _dict(by_name.get(name))
        path = Path(str(item.get("path", "")))
        expected_sha = item.get("sha256")
        observed_sha = _sha256(path) if path.is_file() else None
        checks.extend(
            [
                _expect(f"source_artifact_{name}_exists_in_review", item.get("exists"), True),
                _expect(f"source_artifact_{name}_hash_matches_in_review", item.get("hash_matches"), True),
                _check(f"source_artifact_{name}_file_exists", path.is_file(), str(path), "file"),
                _expect(f"source_artifact_{name}_hash_matches_file", observed_sha, expected_sha),
            ]
        )
    return checks


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    return [
        _check(
            "audit_latest_boundary_matches_construction_gate",
            f"current_v14_status={SOURCE_STATIC_REVIEW_STATUS}" in eof
            and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "passed static review with construction next",
        ),
        _check(
            "current_status_boundary_matches_construction_gate",
            f"current_v14_status={SOURCE_STATIC_REVIEW_STATUS}" in status_text
            and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text,
            "current status boundary",
            "passed static review with construction next",
        ),
        _contains("audit_records_static_review_passed", eof, "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_passed=True"),
        _contains("audit_authorizes_construction", eof, "default_off_shadow_selector_runtime_promotion_evidence_package_construction_authorized=True"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_selector_promotion", eof, "selector_promotion_authorized=False"),
        _contains("audit_blocks_deployment", eof, "deployment_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _static_review_sha256_checks(json_path: Path, md_path: Path, sha256sums: dict[str, str]) -> list[dict[str, Any]]:
    json_sha = _sha256(json_path) if json_path.is_file() else None
    md_sha = _sha256(md_path) if md_path.is_file() else None
    return [
        _expect("source_static_review_sha256s_json_hash", sha256sums.get(json_path.name), json_sha),
        _expect("source_static_review_sha256s_md_hash", sha256sums.get(md_path.name), md_sha),
    ]


def _package_checks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _check("package_manifest_nonempty", bool(entries), len(entries), ">0"),
        _expect(
            "package_entries_hash_match",
            [entry["name"] for entry in entries if not entry.get("hash_matches")],
            [],
        ),
    ]


def _source_static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    review_checks = _list(static_review.get("review_checks"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "evidence_package_construction_authorized": decision.get("evidence_package_construction_authorized"),
        "review_check_count": len(review_checks),
        "failed_check_count": len([check for check in review_checks if isinstance(check, dict) and not check.get("passed")]),
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
        "runtime_promotion_evidence_package_constructed": bool(passed),
        "constructed_package_static_review_authorized": bool(passed),
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
    if "construction_enabled" in failed_set:
        return "explicit_construction_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("source_static_review_sha256s_") for name in failed):
        return "source_static_review_sha256s_mismatch"
    if any(name.startswith("source_artifact_") for name in failed):
        return "source_artifact_hash_mismatch"
    if any(name.startswith("source_static_review_") for name in failed):
        return "source_static_review_contract_failure"
    if any(name.startswith("package_") for name in failed):
        return "package_materialization_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "runtime_promotion_evidence_package_construction_contract_failure"


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
    for path in sorted(output_dir.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}")
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
