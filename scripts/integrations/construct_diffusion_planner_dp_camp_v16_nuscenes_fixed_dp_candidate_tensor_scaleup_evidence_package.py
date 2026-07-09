#!/usr/bin/env python3
"""Construct the v16 fixed-DP scale-up evidence package manifest."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_static_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_static_review_module()
PLAN_MODULE = SOURCE_STATIC_REVIEW_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_STATIC_REVIEW_SCHEMA_VERSION = SOURCE_STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_STATIC_REVIEW_MD_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_constructed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction_v1"
PACKAGE_MANIFEST_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_manifest.json"
PACKAGE_REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_report.md"
SOURCE_INDEX_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_index.json"
REQUIRED_SOURCE_FILES = ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "SHA256SUMS", "ROOT_SHA256SUMS")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_static_review_root_sha256s=args.source_static_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_sha256s: Path,
    source_static_review_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    plan_artifact = source_plan_artifact_dir.resolve()
    static_review_artifact = source_static_review_artifact_dir.resolve()
    plan = _read_json(source_plan_json)
    static_review = _read_json(source_static_review_json)
    plan_sha_entries, plan_sha_failures = _verify_sha256s(plan_artifact, source_plan_sha256s)
    static_sha_entries, static_sha_failures = _verify_sha256s(static_review_artifact, source_static_review_sha256s)
    plan_root_sha = _read_root_sha(source_plan_root_sha256s)
    static_root_sha = _read_root_sha(source_static_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    plan_payload = plan.get("scaleup_evidence_package_plan", {})
    source_index = [_source_artifact_index(item) for item in plan_payload.get("source_artifacts", [])]
    manifest = _package_manifest(plan_payload, source_index)
    static_final = static_review.get("final_decision", {})
    plan_final = plan.get("final_decision", {})
    checks = [
        _expect("construction_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
        _check("source_static_review_artifact_exists", static_review_artifact.is_dir(), str(static_review_artifact), "directory"),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _expect("source_static_review_root_sha256", static_root_sha, expected_static_review_root_sha256),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _check("source_static_review_sha256s_verified", not static_sha_failures, static_sha_failures[:10], []),
        _expect("source_plan_schema", plan.get("schema_version"), PLAN_MODULE.SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", plan_final.get("passed"), True),
        _expect("source_plan_authorized_static_review", plan_final.get("authorized_next_work"), SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA_VERSION),
        _expect("source_static_review_status", static_review.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", static_final.get("passed"), True),
        _expect("source_static_review_authorizes_construction", static_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _contains("audit_authorizes_construction", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_construction", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_STATIC_REVIEW_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_STATIC_REVIEW_STATUS}"),
        _expect("source_artifact_ids", [item["id"] for item in source_index], list(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("source_artifact_count", len(source_index), len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("manifest_source_artifact_count", manifest["source_artifact_count"], len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("manifest_dp_head_fixed", manifest["dp_head_fixed"], FIXED_DP_HEAD),
        _expect("manifest_camp_head_chain_recorded", manifest["camp_head_chain_recorded"], True),
        _expect("manifest_no_claim_boundary", manifest["no_claim_boundary"], plan_payload.get("package_manifest", {}).get("no_claim_boundary")),
        _expect("package_report_records", manifest["package_report"].get("records"), PLAN_MODULE.EXPECTED_RECORDS),
        _expect("package_report_scenes", manifest["package_report"].get("scenes"), PLAN_MODULE.EXPECTED_SCENES),
        _expect("package_report_split_rows", manifest["package_report"].get("split_rows"), PLAN_MODULE.EXPECTED_SPLIT_ROWS),
        _expect("package_report_paired_eval_rows", manifest["package_report"].get("paired_eval_rows"), PLAN_MODULE.EXPECTED_PAIRED_ROWS),
        _expect("package_report_metrics", manifest["package_report"].get("metrics_summary"), PLAN_MODULE.EXPECTED_METRICS),
        _expect("recommended_next_direct_claim_not_allowed", manifest["package_report"].get("recommended_next_path", {}).get("direct_claim_allowed"), False),
        _expect("pass_all_source_artifact_sha_verified", plan_payload.get("pass_checks", {}).get("all_source_artifact_sha_verified"), True),
        _expect("pass_candidate_tensor_unmodified", plan_payload.get("pass_checks", {}).get("candidate_tensor_unmodified"), True),
        _expect("pass_k_candidate_count", plan_payload.get("pass_checks", {}).get("k_candidate_count"), [8, 8]),
        _expect("pass_no_train_leakage", plan_payload.get("pass_checks", {}).get("no_train_leakage_into_primary_eval"), True),
        _expect("pass_affine_simplex_preserved", plan_payload.get("pass_checks", {}).get("affine_simplex_checks_preserved"), True),
    ]
    checks.extend(_required_file_checks(plan_payload.get("required_files", [])))
    checks.extend(_source_artifact_checks(source_index))
    checks.extend(_no_forbidden_work_checks(plan_final, "source_plan"))
    checks.extend(_no_forbidden_work_checks(static_final, "source_static_review"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_plan_artifact": {
                "path": str(plan_artifact),
                "root_sha256": plan_root_sha,
                "expected_root_sha256": expected_plan_root_sha256,
                "sha256_entry_count": plan_sha_entries,
                "failed_sha256s": plan_sha_failures,
            },
            "source_static_review_artifact": {
                "path": str(static_review_artifact),
                "root_sha256": static_root_sha,
                "expected_root_sha256": expected_static_review_root_sha256,
                "sha256_entry_count": static_sha_entries,
                "failed_sha256s": static_sha_failures,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_plan_camp_head": plan.get("heads", {}).get("camp_head"),
                "source_static_review_camp_head": static_review.get("heads", {}).get("camp_head"),
            },
            "source_index": {"source_artifacts": source_index},
            "package_manifest": manifest,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "evidence_package_constructed": passed,
                "evidence_package_constructed_by_this_gate": passed,
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
    (output_dir / PACKAGE_MANIFEST_JSON_NAME).write_text(
        json.dumps(report["package_manifest"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / SOURCE_INDEX_JSON_NAME).write_text(
        json.dumps(report["source_index"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / PACKAGE_REPORT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _package_manifest(plan: dict[str, Any], source_index: list[dict[str, Any]]) -> dict[str, Any]:
    package_manifest = plan.get("package_manifest", {})
    return {
        "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_v1",
        "source_artifact_count": len(source_index),
        "source_artifacts": [
            {
                "id": item["id"],
                "path": item["path"],
                "root_sha256": item["root_sha256"],
                "file_count": len(item["files"]),
            }
            for item in source_index
        ],
        "camp_head_chain": [item["heads"].get("CAMP_HEAD") for item in source_index],
        "camp_head_chain_recorded": all(item["heads"].get("CAMP_HEAD") for item in source_index),
        "dp_head_fixed": package_manifest.get("dp_head_fixed"),
        "no_claim_boundary": package_manifest.get("no_claim_boundary", {}),
        "package_report": plan.get("package_report", {}),
        "pass_checks": plan.get("pass_checks", {}),
        "authorizes_claim": False,
        "authorizes_promotion": False,
        "authorizes_deployment": False,
    }


def _source_artifact_index(entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(entry["path"])).resolve()
    sha_path = path / "SHA256SUMS"
    root_path = path / "ROOT_SHA256SUMS"
    sha_entries, sha_failures, files = _verify_sha256s(path, sha_path, include_files=True)
    root_sha = _read_root_sha(root_path)
    expected_root = str(entry.get("expected_root_sha256") or entry.get("root_sha256"))
    heads = _read_heads(path / "HEADS")
    return {
        "id": entry.get("id"),
        "phase": entry.get("phase"),
        "path": str(path),
        "expected_root_sha256": expected_root,
        "root_sha256": root_sha,
        "root_matches_expected": root_sha == expected_root,
        "sha256_entry_count": sha_entries,
        "failed_sha256s": sha_failures,
        "sha256s_verified": path.is_dir() and sha_path.is_file() and not sha_failures,
        "heads": heads,
        "files": files,
        "json_summaries": [item["path"] for item in files if item["path"].endswith(".json")],
        "rows_jsonl": [item["path"] for item in files if item["path"].endswith(".jsonl")],
        "split_manifests_metrics": [
            item["path"]
            for item in files
            if "split" in item["path"] and item["path"].endswith((".json", ".jsonl", ".txt"))
        ],
        "latency_json": [item["path"] for item in files if "latency" in item["path"] and item["path"].endswith(".json")],
        "model_weights_config_timing_log": [
            item["path"]
            for item in files
            if any(token in item["path"] for token in ("model", "weight", "config", "timing", "log"))
        ],
    }


def _required_file_checks(files: list[str]) -> list[dict[str, Any]]:
    return [_check(f"required_file_{name}", name in files, "present" if name in files else "missing", name) for name in PLAN_MODULE.REQUIRED_FILES]


def _source_artifact_checks(source_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for item in source_index:
        artifact_id = item["id"]
        checks.extend(
            [
                _check(f"source_artifact_{artifact_id}_exists", Path(item["path"]).is_dir(), item["path"], "directory"),
                _expect(f"source_artifact_{artifact_id}_sha_verified", item["sha256s_verified"], True),
                _expect(f"source_artifact_{artifact_id}_root_matches_expected", item["root_matches_expected"], True),
                _expect(f"source_artifact_{artifact_id}_dp_head_fixed", item["heads"].get("DP_HEAD"), FIXED_DP_HEAD),
                _check(f"source_artifact_{artifact_id}_has_json_summary", bool(item["json_summaries"]), item["json_summaries"], "json summary"),
            ]
        )
        for name in REQUIRED_SOURCE_FILES:
            checks.append(
                _check(
                    f"source_artifact_{artifact_id}_has_{name}",
                    (Path(item["path"]) / name).is_file(),
                    str(Path(item["path"]) / name),
                    "file",
                )
            )
    return checks


def _no_forbidden_work_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
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
        )
        if field in final
    ]


def _verify_sha256s(
    root: Path,
    manifest: Path,
    *,
    include_files: bool = False,
) -> tuple[int, list[str]] | tuple[int, list[str], list[dict[str, str]]]:
    if not manifest.is_file():
        return (0, ["missing_SHA256SUMS"], []) if include_files else (0, ["missing_SHA256SUMS"])
    failed = []
    files = []
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
        else:
            observed = _sha256(path)
            if observed != expected:
                failed.append(f"mismatch:{name}")
            files.append({"path": name, "sha256": expected, "observed_sha256": observed})
    return (count, failed, files) if include_files else (count, failed)


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
    manifest = report["package_manifest"]
    package_report = manifest["package_report"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Evidence Package",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact count: `{manifest['source_artifact_count']}`",
            "- Claim boundary: no performance, safety, CAMP-over-DP, promotion, or deployment.",
            f"- Package report: `{package_report}`",
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
            f"SOURCE_PLAN_ROOT_SHA256={report['source_plan_artifact']['root_sha256']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={report['source_static_review_artifact']['root_sha256']}",
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


def _read_heads(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            rows[key] = value
    return rows


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
