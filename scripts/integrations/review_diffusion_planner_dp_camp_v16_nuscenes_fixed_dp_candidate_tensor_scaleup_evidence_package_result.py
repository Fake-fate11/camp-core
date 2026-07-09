#!/usr/bin/env python3
"""Review the v16 fixed-DP scale-up evidence-package construction result."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_construction_module():
    path = Path(__file__).resolve().with_name(
        "construct_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_construction", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_construction_module()
PLAN_MODULE = SOURCE_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_v1"
PACKAGE_MANIFEST_JSON_NAME = SOURCE_MODULE.PACKAGE_MANIFEST_JSON_NAME
PACKAGE_REPORT_MD_NAME = SOURCE_MODULE.PACKAGE_REPORT_MD_NAME
SOURCE_INDEX_JSON_NAME = SOURCE_MODULE.SOURCE_INDEX_JSON_NAME
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review.md"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
REQUIRED_PACKAGE_FILES = (
    PACKAGE_MANIFEST_JSON_NAME,
    PACKAGE_REPORT_MD_NAME,
    SOURCE_INDEX_JSON_NAME,
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_package_artifact_dir", type=Path, required=True)
    parser.add_argument("--package_manifest_json", type=Path, required=True)
    parser.add_argument("--package_report_md", type=Path, required=True)
    parser.add_argument("--source_index_json", type=Path, required=True)
    parser.add_argument("--package_sha256s", type=Path, required=True)
    parser.add_argument("--package_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_package_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_package_artifact_dir=args.source_package_artifact_dir,
        package_manifest_json=args.package_manifest_json,
        package_report_md=args.package_report_md,
        source_index_json=args.source_index_json,
        package_sha256s=args.package_sha256s,
        package_root_sha256s=args.package_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_package_root_sha256=args.expected_package_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_package_artifact_dir: Path,
    package_manifest_json: Path,
    package_report_md: Path,
    source_index_json: Path,
    package_sha256s: Path,
    package_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_package_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    package = source_package_artifact_dir.resolve()
    manifest = _read_json(package_manifest_json)
    source_index = _read_json(source_index_json).get("source_artifacts", [])
    report_md = _read_text(package_report_md)
    package_sha_entries, package_sha_failures = _verify_sha256s(package, package_sha256s)
    package_root_sha = _read_root_sha(package_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    review = _package_result_review(package, manifest, source_index, report_md, package_sha256s)
    checks = [
        _expect("result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_package_artifact_exists", package.is_dir(), str(package), "directory"),
        _expect("source_package_root_sha256", package_root_sha, expected_package_root_sha256),
        _check("source_package_sha256s_verified", not package_sha_failures, package_sha_failures[:10], []),
        _expect("source_package_schema", manifest.get("schema_version"), "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_v1"),
        _contains("audit_authorizes_result_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_result_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_construction", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_construction", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_artifact_count", review["source_artifact_count"], len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("source_artifact_ids", review["source_artifact_ids"], list(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("manifest_source_artifact_count", manifest.get("source_artifact_count"), len(PLAN_MODULE.EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("manifest_dp_head_fixed", review["dp_head_fixed"], FIXED_DP_HEAD),
        _expect("manifest_has_source_paths", review["package_manifest_has_source_paths"], True),
        _expect("manifest_has_source_root_sha", review["package_manifest_has_source_root_sha"], True),
        _expect("source_index_has_file_list_and_sha", review["source_index_has_file_list_and_sha"], True),
        _expect("camp_head_chain_recorded", review["camp_head_chain_recorded"], True),
        _expect("package_has_no_unreviewed_files", review["package_unreviewed_files"], []),
        _expect("boundary_descriptive_only", review["no_claim_boundary"].get("descriptive_paired_metrics_only"), True),
        _expect("boundary_no_performance_claim", review["no_claim_boundary"].get("no_performance_claim"), True),
        _expect("boundary_no_safety_claim", review["no_claim_boundary"].get("no_safety_claim"), True),
        _expect("boundary_no_camp_over_dp_claim", review["no_claim_boundary"].get("no_camp_over_dp_claim"), True),
        _expect("boundary_no_promotion_or_deployment", review["no_claim_boundary"].get("no_promotion_or_deployment"), True),
        _expect("package_records_10000", review["package_report"].get("records"), PLAN_MODULE.EXPECTED_RECORDS),
        _expect("package_scenes_50", review["package_report"].get("scenes"), PLAN_MODULE.EXPECTED_SCENES),
        _expect("package_split_rows", review["package_report"].get("split_rows"), PLAN_MODULE.EXPECTED_SPLIT_ROWS),
        _expect("package_paired_eval_rows", review["package_report"].get("paired_eval_rows"), PLAN_MODULE.EXPECTED_PAIRED_ROWS),
        _expect("package_metrics_summary", review["package_report"].get("metrics_summary"), PLAN_MODULE.EXPECTED_METRICS),
        _expect("recommended_next_path", review["recommended_next_path"].get("allowed_next_gates"), ["claim-boundary plan", "32k expansion plan"]),
        _expect("direct_claim_not_allowed", review["direct_claim_allowed"], False),
        _expect("report_has_records_scenes", review["package_report_has_records_scenes"], True),
        _expect("report_has_split_rows", review["package_report_has_split_rows"], True),
        _expect("report_has_paired_eval_rows", review["package_report_has_paired_eval_rows"], True),
        _expect("report_has_metrics", review["package_report_has_metrics"], True),
        _expect("report_has_no_claim_boundary", review["package_report_has_no_claim_boundary"], True),
        _expect("report_has_next_recommendation", review["package_report_has_next_recommendation"], True),
        _expect("no_claims_authorized", review["no_claims_authorized"], True),
        _expect("all_source_artifact_sha_verified", review["all_source_artifact_sha_verified"], True),
        _expect("all_source_artifact_roots_match", review["all_source_artifact_roots_match"], True),
        _expect("all_source_artifact_files_match_index", review["all_source_artifact_files_match_index"], True),
        _expect("all_source_dp_heads_fixed", review["all_source_dp_heads_fixed"], True),
        _expect("candidate_tensor_unmodified", review["candidate_tensor_unmodified"], True),
        _expect("k_candidate_count_8_8", review["k_candidate_count"], [8, 8]),
        _expect("no_train_leakage", review["train_rows_in_primary_eval"], 0),
        _expect("affine_simplex_preserved", review["affine_simplex_preserved"], True),
        _expect("source_final_decisions_no_claim_promotion_deploy", review["source_final_decisions_no_claim_promotion_deploy"], True),
    ]
    checks.extend(_package_file_checks(package, package_manifest_json, package_report_md, source_index_json, package_sha256s, package_root_sha256s))
    checks.extend(_source_artifact_checks(source_index))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_package_artifact": {
                "path": str(package),
                "manifest_json": str(package_manifest_json.resolve()),
                "report_md": str(package_report_md.resolve()),
                "source_index_json": str(source_index_json.resolve()),
                "root_sha256": package_root_sha,
                "expected_root_sha256": expected_package_root_sha256,
                "sha256_entry_count": package_sha_entries,
                "failed_sha256s": package_sha_failures,
                "sha256s_sha256": _sha256(package_sha256s) if package_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(package_root_sha256s) if package_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_package_camp_head": _read_heads(package / "HEADS").get("CAMP_HEAD"),
            },
            "scaleup_evidence_package_result_review": review,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "result_review_only": True,
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


def _package_result_review(
    package: Path,
    manifest: dict[str, Any],
    source_index: list[dict[str, Any]],
    report_md: str,
    package_sha256s: Path,
) -> dict[str, Any]:
    summaries = _source_summaries(source_index)
    paired = summaries.get("scaleup_paired_evaluation_result_review", {}).get("paired_evaluation_result_review", {})
    training = summaries.get("scaleup_training_result_review", {}).get("training_result_review", {})
    split = summaries.get("scaleup_split_result_review", {}).get("split_result_review", {})
    final_decisions = [payload.get("final_decision", {}) for payload in summaries.values()]
    report_lower = report_md.lower()
    source_file_checks = [_source_files_match_index(item) for item in source_index]
    source_sha_checks = [_verify_source_sha(item) for item in source_index]
    source_ids = [item.get("id") for item in source_index]
    manifest_sources = manifest.get("source_artifacts", [])
    manifest_by_id = {item.get("id"): item for item in manifest_sources}
    package_report = manifest.get("package_report", {})
    return {
        "source_artifact_count": len(source_index),
        "source_artifact_ids": source_ids,
        "package_unreviewed_files": _unreviewed_files(package, package_sha256s),
        "package_manifest_has_source_paths": all(manifest_by_id.get(source_id, {}).get("path") for source_id in source_ids),
        "package_manifest_has_source_root_sha": all(manifest_by_id.get(source_id, {}).get("root_sha256") for source_id in source_ids),
        # ponytail: construction keeps the full file paths and hashes in source_index, not duplicated in the compact manifest.
        "source_index_has_file_list_and_sha": all(_has_file_list_and_sha(item) for item in source_index),
        "camp_head_chain_recorded": _camp_head_chain_recorded(manifest, source_index),
        "dp_head_fixed": manifest.get("dp_head_fixed"),
        "no_claim_boundary": manifest.get("no_claim_boundary", {}),
        "package_report": package_report,
        "recommended_next_path": package_report.get("recommended_next_path", {}),
        "direct_claim_allowed": package_report.get("recommended_next_path", {}).get("direct_claim_allowed"),
        "package_report_has_records_scenes": "10000" in report_lower and "50" in report_lower and "records" in report_lower,
        "package_report_has_split_rows": "6263" in report_lower and "2156" in report_lower and "1581" in report_lower,
        "package_report_has_paired_eval_rows": "3737" in report_lower
        and ("paired eval" in report_lower or "paired-eval" in report_lower or "paired_eval_rows" in report_lower),
        "package_report_has_metrics": "3365" in report_lower and "359" in report_lower and "13" in report_lower and "-0.01762098077036227" in report_lower,
        "package_report_has_no_claim_boundary": "no performance" in report_lower and "promotion" in report_lower and "deployment" in report_lower,
        "package_report_has_next_recommendation": "claim-boundary plan" in report_lower and "32k expansion plan" in report_lower,
        "no_claims_authorized": not any(manifest.get(field) for field in ("authorizes_claim", "authorizes_promotion", "authorizes_deployment")),
        "all_source_artifact_sha_verified": all(item.get("sha256s_verified") is True for item in source_index) and all(source_sha_checks),
        "all_source_artifact_roots_match": all(item.get("root_matches_expected") is True for item in source_index),
        "all_source_artifact_files_match_index": all(source_file_checks),
        "all_source_dp_heads_fixed": all(item.get("heads", {}).get("DP_HEAD") == FIXED_DP_HEAD for item in source_index),
        "candidate_tensor_unmodified": _all_zero(
            split.get("candidate_tensor_mutated_count"),
            training.get("candidate_tensor_mutated_count"),
            paired.get("candidate_tensor_mutated_count"),
        ),
        "k_candidate_count": [
            _single_value(paired.get("k_values") or training.get("train_k_values")),
            _single_value(paired.get("candidate_count_values") or training.get("train_candidate_count_values")),
        ],
        "train_rows_in_primary_eval": paired.get("train_rows_in_primary_eval"),
        "affine_simplex_preserved": (
            paired.get("score_expression") == SCORE_EXPRESSION
            and training.get("score_expression") == SCORE_EXPRESSION
            and paired.get("weights_nonnegative") is True
            and paired.get("weights_sum_to_one") is True
            and paired.get("approved_atoms_only") is True
            and training.get("weights_nonnegative") is True
            and training.get("weights_sum_to_one") is True
            and training.get("approved_atoms_only") is True
        ),
        "source_final_decisions_no_claim_promotion_deploy": _final_decisions_clean(final_decisions),
    }


def _package_file_checks(
    artifact: Path,
    package_manifest_json: Path,
    package_report_md: Path,
    source_index_json: Path,
    package_sha256s: Path,
    package_root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected_paths = {
        PACKAGE_MANIFEST_JSON_NAME: package_manifest_json.resolve(),
        PACKAGE_REPORT_MD_NAME: package_report_md.resolve(),
        SOURCE_INDEX_JSON_NAME: source_index_json.resolve(),
        "SHA256SUMS": package_sha256s.resolve(),
        "ROOT_SHA256SUMS": package_root_sha256s.resolve(),
    }
    checks = []
    for name in REQUIRED_PACKAGE_FILES:
        path = artifact / name
        checks.append(_check(f"source_package_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_package_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _source_artifact_checks(source_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for item in source_index:
        source_id = item.get("id", "unknown")
        checks.extend(
            [
                _check(f"source_artifact_{source_id}_exists", Path(str(item.get("path"))).is_dir(), item.get("path"), "directory"),
                _expect(f"source_artifact_{source_id}_sha_verified_flag", item.get("sha256s_verified"), True),
                _expect(f"source_artifact_{source_id}_root_matches_expected", item.get("root_matches_expected"), True),
                _expect(f"source_artifact_{source_id}_dp_head_fixed", item.get("heads", {}).get("DP_HEAD"), FIXED_DP_HEAD),
                _expect(f"source_artifact_{source_id}_files_match_index", _source_files_match_index(item), True),
                _expect(f"source_artifact_{source_id}_sha256s_reverified", _verify_source_sha(item), True),
            ]
        )
    return checks


def _source_summaries(source_index: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summaries = {}
    for item in source_index:
        root = Path(str(item.get("path")))
        payload = {}
        for file_item in item.get("files", []):
            rel = str(file_item.get("path", ""))
            if rel.endswith(".json"):
                try:
                    data = _read_json(root / rel)
                    if isinstance(data, dict):
                        payload.update(data)
                except (OSError, json.JSONDecodeError):
                    pass
        summaries[str(item.get("id"))] = payload
    return summaries


def _has_file_list_and_sha(item: dict[str, Any]) -> bool:
    files = item.get("files")
    return bool(files) and all(file_item.get("path") and file_item.get("sha256") and file_item.get("observed_sha256") for file_item in files)


def _source_files_match_index(item: dict[str, Any]) -> bool:
    root = Path(str(item.get("path")))
    for file_item in item.get("files", []):
        rel = str(file_item.get("path", ""))
        path = root / rel
        expected = file_item.get("sha256")
        observed = file_item.get("observed_sha256")
        if not path.is_file() or _sha256(path) != expected or observed != expected:
            return False
    return True


def _verify_source_sha(item: dict[str, Any]) -> bool:
    root = Path(str(item.get("path")))
    _, failures = _verify_sha256s(root, root / "SHA256SUMS")
    return not failures


def _camp_head_chain_recorded(manifest: dict[str, Any], source_index: list[dict[str, Any]]) -> bool:
    chain = manifest.get("camp_head_chain")
    expected = [item.get("heads", {}).get("CAMP_HEAD") for item in source_index]
    return bool(chain) and chain == expected and all(expected)


def _unreviewed_files(root: Path, manifest: Path) -> list[str]:
    listed = set(_manifest_paths(manifest))
    ignored = {"SHA256SUMS", "ROOT_SHA256SUMS"}
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in listed and path.name not in ignored
    ]


def _manifest_paths(manifest: Path) -> list[str]:
    if not manifest.is_file():
        return []
    paths = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            _, rel = line.split(maxsplit=1)
            paths.append(rel.strip())
    return paths


def _final_decisions_clean(final_decisions: list[dict[str, Any]]) -> bool:
    for final in final_decisions:
        for field in ("performance_claimed", "safety_claimed", "camp_over_dp_claimed", "promotion_executed", "deployment_executed", "dp_modified", "candidate_tensor_modified", "fake_candidate_tensor_generated"):
            if final.get(field) is True:
                return False
    return True


def _all_zero(*values: Any) -> bool:
    return all(value in (0, None) for value in values)


def _single_value(values: Any) -> Any:
    if isinstance(values, list) and len(values) == 1:
        return values[0]
    return values


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


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["scaleup_evidence_package_result_review"]
    metrics = review["package_report"].get("metrics_summary", {})
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Evidence Package Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source package artifact: `{report['source_package_artifact']['path']}`",
            f"- Source package root SHA256: `{report['source_package_artifact']['root_sha256']}`",
            f"- Source artifact count: `{review['source_artifact_count']}`",
            f"- Package report: `{review['package_report']}`",
            f"- Metrics summary: `{metrics}`",
            "- Result-review only. No direct claim, promotion, deployment, training, or paired-evaluation rerun is authorized.",
            f"- K/candidate_count: `{review['k_candidate_count']}`",
            f"- Recommended next path: `{review['recommended_next_path']}`",
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
            f"SOURCE_PACKAGE_CAMP_HEAD={heads['source_package_camp_head']}",
            f"SOURCE_PACKAGE_ROOT_SHA256={report['source_package_artifact']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_heads(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            rows[key] = value
    return rows


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
