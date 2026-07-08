#!/usr/bin/env python3
"""Plan the v16 fixed-DP pilot evidence package."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_module(filename: str, name: str):
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_result.py",
    "v16_paired_evaluation_result_review",
)

FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_MODULE.SCORE_EXPRESSION
SOURCE_SCHEMA_VERSION = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_JSON_NAME = SOURCE_MODULE.REVIEW_JSON_NAME
SOURCE_MD_NAME = SOURCE_MODULE.REVIEW_MD_NAME
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan_static_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan.md"
REQUIRED_FILES = (
    "JSON summaries",
    "rows JSONL",
    "split metrics",
    "latency JSON",
    "model/weights/config/timing/log",
    "HEADS/COMMAND/stdout/stderr",
    "SHA256SUMS/ROOT_SHA256SUMS",
)
EXPECTED_SOURCE_ARTIFACT_IDS = (
    "smoke_corpus_generation",
    "smoke_corpus_generation_review",
    "pilot_corpus_generation",
    "pilot_corpus_generation_review",
    "split_execution",
    "split_result_review",
    "training_execution",
    "training_result_review",
    "paired_evaluation_execution",
    "paired_evaluation_result_review",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_artifact_manifest_json", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_source_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_sha256s=args.source_result_review_sha256s,
        source_result_review_root_sha256s=args.source_result_review_root_sha256s,
        source_artifact_manifest_json=args.source_artifact_manifest_json,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_sha256s: Path,
    source_result_review_root_sha256s: Path,
    source_artifact_manifest_json: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_source_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    source_artifact = source_result_review_artifact_dir.resolve()
    source = _read_json(source_result_review_json)
    manifest = _read_json(source_artifact_manifest_json)
    source_sha_entries, source_sha_failures = _verify_sha256s(source_artifact, source_result_review_sha256s)
    source_root_sha = _read_root_sha(source_result_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    artifacts = [_source_artifact(entry) for entry in manifest.get("artifacts", [])]
    review = source.get("paired_evaluation_result_review", {})
    source_final = source.get("final_decision", {})
    plan = _evidence_package_plan(artifacts, review)
    checks = [
        _expect("evidence_package_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", source_artifact.is_dir(), str(source_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_final.get("passed"), True),
        _expect("source_authorizes_evidence_package_plan", source_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_root_sha256", source_root_sha, expected_source_root_sha256),
        _check("source_result_review_sha256s_verified", not source_sha_failures, source_sha_failures[:10], []),
        _contains("audit_authorizes_evidence_package_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_evidence_package_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_artifact_ids", [artifact["id"] for artifact in artifacts], list(EXPECTED_SOURCE_ARTIFACT_IDS)),
        _expect("primary_eval_rows_161", review.get("primary_eval_rows"), 161),
        _expect("calibration_rows_14", review.get("calibration_rows"), 14),
        _expect("holdout_rows_147", review.get("holdout_rows"), 147),
        _expect("train_reporting_only_rows_863", review.get("train_reporting_only_rows"), 863),
        _expect("train_rows_excluded", review.get("train_rows_in_primary_eval"), 0),
        _expect("k_values_8", review.get("k_values"), [8]),
        _expect("candidate_count_values_8", review.get("candidate_count_values"), [8]),
        _expect("dp_head_values_fixed", review.get("dp_head_values"), [FIXED_DP_HEAD]),
        _expect("candidate_tensor_hashes_present", review.get("candidate_tensor_missing_hash_count"), 0),
        _expect("candidate_tensor_not_mutated", review.get("candidate_tensor_mutated_count"), 0),
        _expect("score_expression_affine", review.get("score_expression"), SCORE_EXPRESSION),
        _expect("weights_nonnegative", review.get("weights_nonnegative"), True),
        _expect("weights_sum_to_one", review.get("weights_sum_to_one"), True),
        _expect("approved_atoms_only", review.get("approved_atoms_only"), True),
        _expect("smoke_only", review.get("smoke_only_result"), True),
        _expect("no_performance_claim", review.get("no_performance_claim"), True),
        _expect("no_safety_claim", review.get("no_safety_claim"), True),
        _expect("no_camp_over_dp_claim", review.get("no_camp_over_dp_claim"), True),
        _expect("no_promotion", review.get("no_promotion"), True),
        _expect("no_deployment", review.get("no_deployment"), True),
        _check("all_source_artifact_sha_verified", plan["pass_checks"]["all_source_artifact_sha_verified"], _artifact_failures(artifacts), []),
        _expect("camp_head_chain_recorded", plan["pass_checks"]["camp_head_chain_recorded"], True),
        _expect("no_dp_modification", plan["pass_checks"]["no_dp_modification"], True),
        _expect("no_candidate_tensor_mutation", plan["pass_checks"]["no_candidate_tensor_mutation"], True),
        _expect("no_train_leakage", plan["pass_checks"]["no_train_leakage_into_primary_eval"], True),
        _expect("affine_simplex_preserved", plan["pass_checks"]["affine_simplex_checks_preserved"], True),
        _expect("next_path_no_claim", plan["recommended_next_path"]["pilot_result_usable_for_claim"], False),
    ]
    checks.extend(_source_file_checks(source_artifact, source_result_review_json, source_result_review_sha256s, source_result_review_root_sha256s))
    checks.extend(_no_forbidden_source_work_checks(source_final))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifact": {
                "path": str(source_artifact),
                "summary_json": str(source_result_review_json.resolve()),
                "manifest_json": str(source_artifact_manifest_json.resolve()),
                "root_sha256": source_root_sha,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": source_sha_entries,
                "failed_sha256s": source_sha_failures,
                "sha256s_sha256": _sha256(source_result_review_sha256s) if source_result_review_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_result_review_root_sha256s) if source_result_review_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
            },
            "pilot_evidence_package_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "evidence_package_plan_only": True,
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
    (output_dir / PLAN_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PLAN_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _evidence_package_plan(artifacts: list[dict[str, Any]], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_artifacts": artifacts,
        "required_files": list(REQUIRED_FILES),
        "no_claim_boundary": {
            "smoke_only": True,
            "scene_count": 4,
            "calibration_rows": 14,
            "holdout_rows": 147,
            "no_performance_claim": True,
            "no_safety_claim": True,
            "no_camp_over_dp_claim": True,
            "no_promotion_or_deployment": True,
        },
        "pass_checks": {
            "all_source_artifact_sha_verified": all(
                artifact["sha256s_verified"] and artifact["root_matches_expected"] for artifact in artifacts
            ),
            "dp_head_fixed": FIXED_DP_HEAD,
            "camp_head_chain_recorded": all(artifact["heads"].get("CAMP_HEAD") for artifact in artifacts),
            "no_dp_modification": True,
            "no_candidate_tensor_mutation": review.get("candidate_tensor_mutated_count") == 0,
            "k_candidate_count": [8, 8],
            "no_train_leakage_into_primary_eval": review.get("train_rows_in_primary_eval") == 0,
            "affine_simplex_checks_preserved": (
                review.get("score_expression") == SCORE_EXPRESSION
                and review.get("weights_nonnegative") is True
                and review.get("weights_sum_to_one") is True
                and review.get("approved_atoms_only") is True
            ),
        },
        "recommended_next_path": {
            "next_gate": "scale-up plan",
            "increase_scene_diversity": True,
            "target_records": 10000,
            "pilot_result_usable_for_claim": False,
        },
        "forbidden_work": [
            "construct_evidence_package",
            "scale_up_execution",
            "training",
            "new_paired_evaluation",
            "performance_claim",
            "safety_claim",
            "camp_over_dp_claim",
            "promotion",
            "deployment",
        ],
    }


def _source_artifact(entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(entry["path"])).resolve()
    sha_path = path / "SHA256SUMS"
    root_path = path / "ROOT_SHA256SUMS"
    sha_entries, sha_failures = _verify_sha256s(path, sha_path)
    root_sha = _read_root_sha(root_path)
    heads = _read_heads(path / "HEADS")
    expected_root = str(entry["expected_root_sha256"])
    return {
        "id": entry["id"],
        "phase": entry.get("phase"),
        "path": str(path),
        "expected_root_sha256": expected_root,
        "root_sha256": root_sha,
        "root_matches_expected": root_sha == expected_root,
        "sha256_entry_count": sha_entries,
        "failed_sha256s": sha_failures,
        "sha256s_verified": path.is_dir() and sha_path.is_file() and not sha_failures,
        "sha256s_sha256": _sha256(sha_path) if sha_path.is_file() else None,
        "root_sha256s_sha256": _sha256(root_path) if root_path.is_file() else None,
        "heads": heads,
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    checks = []
    for name in (SOURCE_JSON_NAME, SOURCE_MD_NAME, "HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", "SHA256SUMS", "ROOT_SHA256SUMS"):
        path = artifact / name
        checks.append(_check(f"source_result_review_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_result_review_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_forbidden_source_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        _expect("source_result_review_only", final.get("result_review_only"), True),
        _expect("source_paired_evaluation_executed_by_review_false", final.get("paired_evaluation_executed_by_review"), False),
    ]
    for field in (
        "training_executed",
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


def _artifact_failures(artifacts: list[dict[str, Any]]) -> list[str]:
    failures = []
    for artifact in artifacts:
        if not artifact["sha256s_verified"] or not artifact["root_matches_expected"]:
            failures.append(artifact["id"])
    return failures


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
    plan = report["pilot_evidence_package_plan"]
    boundary = plan["no_claim_boundary"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Evidence Package Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Scope: plan only; no package construction, claim, promotion, deployment, or scale-up execution.",
            f"- Source artifacts: `{[artifact['id'] for artifact in plan['source_artifacts']]}`",
            f"- Required files: `{plan['required_files']}`",
            f"- No-claim boundary: `{boundary}`",
            f"- Recommended next path: `{plan['recommended_next_path']}`",
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
    return _check(name, needle in text, needle if needle in text else "missing", needle)


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
