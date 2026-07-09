#!/usr/bin/env python3
"""Static-review the v16 fixed-DP scale-up evidence-package plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_plan_module():
    path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review.md"
REQUIRED_SOURCE_FILES = (
    PLAN_MODULE.PLAN_JSON_NAME,
    PLAN_MODULE.PLAN_MD_NAME,
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)
FORBIDDEN_WORK = (
    "construct_evidence_package",
    "new_training",
    "new_paired_evaluation",
    "performance_claim",
    "safety_claim",
    "camp_over_dp_claim",
    "promotion",
    "deployment",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_md", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_md=args.source_plan_md,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_md: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_plan_artifact_dir.resolve()
    source = _read_json(source_plan_json)
    sha_entries, sha_failures = _verify_sha256s(artifact, source_plan_sha256s)
    plan_root_sha = _read_root_sha(source_plan_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    final = source.get("final_decision", {})
    plan = source.get("scaleup_evidence_package_plan", {})
    source_artifacts = plan.get("source_artifacts", [])
    manifest = plan.get("package_manifest", {})
    package_report = plan.get("package_report", {})
    no_claim = manifest.get("no_claim_boundary", {})
    pass_checks = plan.get("pass_checks", {})
    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_plan_json_path", source_plan_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("source_plan_md_path", source_plan_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
        _expect("source_plan_sha256s_path", source_plan_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("source_plan_root_sha256s_path", source_plan_root_sha256s.resolve(), artifact / "ROOT_SHA256SUMS"),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_plan_schema", source.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", source.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _contains("audit_authorizes_static_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_plan", audit_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _contains("status_records_plan", status_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _expect("source_artifact_count_8", len(source_artifacts), len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect(
            "source_artifact_ids",
            [item.get("id") for item in source_artifacts],
            list(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS),
        ),
        _expect("manifest_source_count_8", len(manifest.get("sources", [])), len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect(
            "manifest_source_ids",
            [item.get("id") for item in manifest.get("sources", [])],
            list(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS),
        ),
        _expect("manifest_camp_head_chain_recorded", manifest.get("camp_head_chain_recorded"), True),
        _expect("manifest_dp_head_fixed", manifest.get("dp_head_fixed"), FIXED_DP_HEAD),
        _expect("no_claim_descriptive_only", no_claim.get("descriptive_paired_metrics_only"), True),
        _expect("no_performance_claim", no_claim.get("no_performance_claim"), True),
        _expect("no_safety_claim", no_claim.get("no_safety_claim"), True),
        _expect("no_camp_over_dp_claim", no_claim.get("no_camp_over_dp_claim"), True),
        _expect("no_promotion_or_deployment", no_claim.get("no_promotion_or_deployment"), True),
        _expect("package_records_10000", package_report.get("records"), PLAN_MODULE.EXPECTED_RECORDS),
        _expect("package_scenes_50", package_report.get("scenes"), PLAN_MODULE.EXPECTED_SCENES),
        _expect("package_split_rows", package_report.get("split_rows"), PLAN_MODULE.EXPECTED_SPLIT_ROWS),
        _expect("package_paired_eval_rows", package_report.get("paired_eval_rows"), PLAN_MODULE.EXPECTED_PAIRED_ROWS),
        _expect("package_metrics_summary", package_report.get("metrics_summary"), PLAN_MODULE.EXPECTED_METRICS),
        _expect("package_no_performance_claim", package_report.get("no_performance_claim"), True),
        _expect("package_no_safety_claim", package_report.get("no_safety_claim"), True),
        _expect("package_no_camp_over_dp_claim", package_report.get("no_camp_over_dp_claim"), True),
        _expect("recommended_next_allowed_gates", package_report.get("recommended_next_path", {}).get("allowed_next_gates"), ["claim-boundary plan", "32k expansion plan"]),
        _expect("recommended_next_direct_claim_not_allowed", package_report.get("recommended_next_path", {}).get("direct_claim_allowed"), False),
        _expect("all_source_artifact_sha_verified", pass_checks.get("all_source_artifact_sha_verified"), True),
        _expect("pass_check_dp_head_fixed", pass_checks.get("dp_head_fixed"), FIXED_DP_HEAD),
        _expect("camp_head_chain_recorded", pass_checks.get("camp_head_chain_recorded"), True),
        _expect("candidate_tensor_unmodified", pass_checks.get("candidate_tensor_unmodified"), True),
        _expect("k_candidate_count_8_8", pass_checks.get("k_candidate_count"), [8, 8]),
        _expect("no_train_leakage", pass_checks.get("no_train_leakage_into_primary_eval"), True),
        _expect("affine_simplex_preserved", pass_checks.get("affine_simplex_checks_preserved"), True),
    ]
    checks.extend(_manifest_source_checks(manifest.get("sources", [])))
    checks.extend(_required_file_checks(plan.get("required_files", [])))
    checks.extend(_source_file_checks(artifact, source_plan_json, source_plan_md, source_plan_sha256s, source_plan_root_sha256s, sha_entries))
    checks.extend(_source_artifact_sha_checks(source_artifacts))
    checks.extend(_forbidden_work_checks(plan.get("forbidden_work", [])))
    checks.extend(_no_forbidden_work_checks(final))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_plan_artifact": {
                "path": str(artifact),
                "json": str(source_plan_json.resolve()),
                "md": str(source_plan_md.resolve()),
                "sha256s": str(source_plan_sha256s.resolve()),
                "root_sha256s": str(source_plan_root_sha256s.resolve()),
                "root_sha256": plan_root_sha,
                "expected_root_sha256": expected_plan_root_sha256,
                "sha256_entry_count": sha_entries,
                "failed_sha256s": sha_failures,
                "sha256s_sha256": _sha256(source_plan_sha256s) if source_plan_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_plan_root_sha256s) if source_plan_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
            },
            "plan_static_review": {
                "source_plan_root_sha256": plan_root_sha,
                "source_artifact_ids": [item.get("id") for item in source_artifacts],
                "required_files": plan.get("required_files", []),
                "package_manifest": manifest,
                "package_report": package_report,
                "no_claim_boundary": no_claim,
                "pass_checks": pass_checks,
                "recommended_next_path": package_report.get("recommended_next_path", {}),
                "forbidden_work": plan.get("forbidden_work", []),
            },
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "static_review_only": True,
                "evidence_package_constructed": False,
                "scale_up_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "safety_claimed": False,
                "camp_over_dp_claimed": False,
                "promotion_executed": False,
                "deployment_executed": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "fake_candidate_tensor_generated": False,
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REVIEW_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / REVIEW_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _manifest_source_checks(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for item in sources:
        artifact_id = item.get("id", "unknown")
        checks.append(_check(f"manifest_source_{artifact_id}_has_path", bool(item.get("path")), item.get("path"), "path"))
        checks.append(_check(f"manifest_source_{artifact_id}_has_root_sha256", bool(item.get("root_sha256")), item.get("root_sha256"), "root_sha256"))
        checks.append(_check(f"manifest_source_{artifact_id}_has_files", bool(item.get("files")), item.get("files"), "files"))
        checks.append(_check(f"manifest_source_{artifact_id}_has_camp_head", bool(item.get("heads", {}).get("CAMP_HEAD")), item.get("heads", {}), "CAMP_HEAD"))
    return checks


def _required_file_checks(files: list[str]) -> list[dict[str, Any]]:
    return [_check(f"required_file_{name}", name in files, "present" if name in files else "missing", name) for name in PLAN_MODULE.REQUIRED_FILES]


def _source_artifact_sha_checks(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for item in artifacts:
        artifact_id = item.get("id", "unknown")
        checks.append(_expect(f"source_artifact_{artifact_id}_sha_verified", item.get("sha256s_verified"), True))
        checks.append(_expect(f"source_artifact_{artifact_id}_root_matches_expected", item.get("root_matches_expected"), True))
    return checks


def _source_file_checks(
    artifact: Path,
    source_plan_json: Path,
    source_plan_md: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    sha_entries: int,
) -> list[dict[str, Any]]:
    expected_paths = {
        PLAN_MODULE.PLAN_JSON_NAME: source_plan_json.resolve(),
        PLAN_MODULE.PLAN_MD_NAME: source_plan_md.resolve(),
        "SHA256SUMS": source_plan_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_plan_root_sha256s.resolve(),
    }
    checks = []
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name not in ("SHA256SUMS", "ROOT_SHA256SUMS"):
            checks.append(_check(f"source_sha256s_has_{name}", _manifest_has(source_plan_sha256s, name), "present" if _manifest_has(source_plan_sha256s, name) else "missing", name))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    checks.append(_check("source_sha256s_complete", sha_entries >= 7, sha_entries, ">=7"))
    return checks


def _forbidden_work_checks(work: list[str]) -> list[dict[str, Any]]:
    return [_check(f"forbidden_work_{name}_listed", name in work, "present" if name in work else "missing", name) for name in FORBIDDEN_WORK]


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [_expect("source_evidence_package_plan_only", final.get("evidence_package_plan_only"), True)]
    for field in (
        "evidence_package_constructed",
        "training_executed",
        "paired_evaluation_executed",
        "performance_claimed",
        "safety_claimed",
        "camp_over_dp_claimed",
        "promotion_executed",
        "deployment_executed",
        "dp_modified",
        "candidate_tensor_modified",
        "fake_candidate_tensor_generated",
    ):
        checks.append(_expect(f"source_{field}_false", final.get(field), False))
    return checks


def _verify_sha256s(root: Path, manifest: Path) -> tuple[int, list[str]]:
    if not manifest.is_file():
        return 0, ["missing_SHA256SUMS"]
    failed = []
    count = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        expected, rel = line.split(maxsplit=1)
        name = rel.strip()
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return count, failed


def _manifest_has(manifest: Path, name: str) -> bool:
    if not manifest.is_file():
        return False
    suffix = f"  {name}"
    return any(line.endswith(suffix) for line in manifest.read_text(encoding="utf-8").splitlines())


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["plan_static_review"]
    package_report = review["package_report"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Evidence Package Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan artifact: `{report['source_plan_artifact']['path']}`",
            f"- Source plan root SHA256: `{review['source_plan_root_sha256']}`",
            f"- Source artifacts: `{review['source_artifact_ids']}`",
            f"- Required files: `{review['required_files']}`",
            f"- Planned package report: `{package_report}`",
            f"- Pass checks: `{review['pass_checks']}`",
            "- Static review only; no package construction, claim, promotion, deployment, training, or paired-evaluation rerun.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_CAMP_HEAD={heads['source_camp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={report['source_plan_artifact']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
