#!/usr/bin/env python3
"""Record the v16 fixed-DP candidate tensor limited claim decision."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_claim_boundary_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_PLAN_ROOT_SHA = "151b22be196dcd0911857e1e43a9a5919bab5211294fc593941853ada67dbce7"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_v1"
DECISION_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision.json"
DECISION_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision.md"
CLAIM_TEXT = (
    "在固定 TiER IV Diffusion Planner commit 7a1d33da、固定 K=8 candidate tensors、"
    "v16 nuScenes scale-up paired evaluation 的 3737 calibration+holdout rows 上，"
    "CAMP selector 相比 DP Top-1 降低了当前定义的 paired metric。"
)
CLAIM_LANGUAGE = "zh-CN"
REQUIRED_SOURCE_FILES = (
    SOURCE_REVIEW_JSON_NAME,
    SOURCE_REVIEW_MD_NAME,
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)
NON_CLAIM_BOUNDARY = {
    "broad_nuscenes_benchmark_claim": False,
    "candidate_tensor_mutation": False,
    "closed_loop_safety_claim": False,
    "deployment": False,
    "dp_model_improvement_claim": False,
    "dp_modification": False,
    "full36_or_formal_seeds_claim": False,
    "online_activation": False,
    "promotion": False,
    "safety_claim": False,
    "training": False,
    "trajectory_generation_claim": False,
    "trajectory_generation_or_repair": False,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_static_review_root_sha256s=args.source_static_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    source_static_review_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_static_review_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact = source_static_review_artifact_dir.resolve()
    source = _read_json(source_static_review_json)
    source_decision = source.get("final_decision", {})
    source_review = source.get("claim_boundary_plan_static_review", {})
    sha_entries, sha_failures = _verify_sha256s(artifact, source_static_review_sha256s)
    source_root_sha = _read_root_sha(source_static_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    claim = _claim_record(source_root_sha, source_review)
    checks = [
        _expect("claim_decision_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_json_path", source_static_review_json.resolve(), artifact / SOURCE_REVIEW_JSON_NAME),
        _expect("source_static_review_md_path", source_static_review_md.resolve(), artifact / SOURCE_REVIEW_MD_NAME),
        _expect("source_static_review_root_sha256", source_root_sha, expected_static_review_root_sha256),
        _check("source_static_review_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_static_review_schema", source.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        _expect("source_static_review_status", source.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_static_review_passed", source_decision.get("passed"), True),
        _expect("source_static_review_authorizes_claim_decision", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_only", source_decision.get("static_review_only"), True),
        _expect("source_claim_not_executed", source_decision.get("claim_executed"), False),
        _expect("source_promotion_not_executed", source_decision.get("promotion_executed"), False),
        _expect("source_deployment_not_executed", source_decision.get("deployment_executed"), False),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v16_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_current_status", _first_value(status_text, "current_v16_status"), SOURCE_REVIEW_STATUS),
        _expect("status_current_next_work", _first_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("allowed_claim_id", source_review.get("allowed_claim_id"), "fixed_dp_k8_current_paired_metric_reduction"),
        _expect("allowed_claim_scope", source_review.get("allowed_claim_scope"), _allowed_scope()),
        _expect("metrics", source_review.get("metrics"), PLAN_MODULE.EXPECTED_METRICS),
        _expect("source_plan_root_sha256", source_review.get("source_plan_root_sha256"), SOURCE_PLAN_ROOT_SHA),
        _expect("forbidden_claims", source_review.get("forbidden_claims"), PLAN_MODULE.FORBIDDEN_CLAIMS),
        _expect("wording_mode_limited_descriptive", source_review.get("wording_mode"), "limited/descriptive"),
        _expect("forbidden_wording_terms", source_review.get("forbidden_wording"), PLAN_MODULE.FORBIDDEN_WORDING),
        _expect("next_gate_claim_decision", (source_review.get("next_gates") or [None])[0], AUTHORIZED_CURRENT_WORK),
        _expect("claim_text", claim.get("claim_text"), CLAIM_TEXT),
        _expect("claim_language", claim.get("language"), CLAIM_LANGUAGE),
        _expect("claim_scope", claim.get("scope"), _allowed_scope()),
        _expect("claim_metrics", claim.get("metrics"), PLAN_MODULE.EXPECTED_METRICS),
        _check("claim_text_avoids_forbidden_terms", _claim_text_clean(claim["claim_text"]), claim["claim_text"], "no forbidden terms"),
        _expect("claim_forbidden_claims", claim.get("forbidden_claims"), PLAN_MODULE.FORBIDDEN_CLAIMS),
        _expect("claim_forbidden_wording", claim.get("forbidden_wording"), PLAN_MODULE.FORBIDDEN_WORDING),
        _expect("non_claim_boundary", claim.get("non_claim_boundary"), NON_CLAIM_BOUNDARY),
    ]
    checks.extend(_preclaim_checks(source_review.get("preclaim_checks", {})))
    checks.extend(_source_file_checks(artifact, source_static_review_json, source_static_review_md, source_static_review_sha256s, source_static_review_root_sha256s, sha_entries))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_static_review_artifact": {
                "path": str(artifact),
                "json": str(source_static_review_json.resolve()),
                "md": str(source_static_review_md.resolve()),
                "root_sha256": source_root_sha,
                "expected_root_sha256": expected_static_review_root_sha256,
                "sha256_entry_count": sha_entries,
                "failed_sha256s": sha_failures,
                "sha256s_sha256": _sha256(source_static_review_sha256s) if source_static_review_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_static_review_root_sha256s) if source_static_review_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_static_review_camp_head": source.get("heads", {}).get("camp_head"),
                "source_plan_camp_head": source.get("heads", {}).get("source_camp_head"),
            },
            "claim_record": claim,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "claim_executed_by_this_gate": bool(passed),
                "limited_descriptive_claim_authorized": bool(passed),
                "safety_claim_authorized": False,
                "closed_loop_safety_claim_authorized": False,
                "deployment_authorized": False,
                "promotion_authorized": False,
                "online_activation_authorized": False,
                "broad_nuscenes_benchmark_claim_authorized": False,
                "full36_or_formal_seed_claim_authorized": False,
                "dp_model_improvement_claim_authorized": False,
                "trajectory_generation_claim_authorized": False,
                "training_executed": False,
                "paired_evaluation_rerun": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "source_static_review_passed": source_decision.get("passed"),
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / DECISION_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / DECISION_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    _write_sha_manifests(output_dir)


def _write_sha_manifests(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.name}\n")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text("".join(rows), encoding="utf-8")
    (output_dir / "ROOT_SHA256SUMS").write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _claim_record(source_root_sha: str | None, source_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_text": CLAIM_TEXT,
        "language": CLAIM_LANGUAGE,
        "scope": _allowed_scope(),
        "metrics": source_review.get("metrics"),
        "source_static_review_root_sha256": source_root_sha,
        "source_plan_root_sha256": source_review.get("source_plan_root_sha256"),
        "forbidden_claims": source_review.get("forbidden_claims"),
        "forbidden_wording": source_review.get("forbidden_wording"),
        "non_claim_boundary": NON_CLAIM_BOUNDARY,
    }


def _preclaim_checks(prechecks: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("source_artifacts_sha_verified", prechecks.get("source_artifacts_sha_verified"), True),
        _expect("fixed_dp_head", prechecks.get("fixed_dp_head"), True),
        _expect("no_dp_modification", prechecks.get("no_dp_modification"), True),
        _expect("no_candidate_tensor_mutation", prechecks.get("no_candidate_tensor_mutation"), True),
        _expect("no_train_leakage_into_primary_eval", prechecks.get("no_train_leakage_into_primary_eval"), True),
        _expect("affine_simplex_preserved", prechecks.get("affine_simplex_preserved"), True),
        _expect("ci95_high_less_than_zero", prechecks.get("ci95_high_less_than_zero"), True),
        _expect("better_greater_than_worse", prechecks.get("better_greater_than_worse"), True),
        _expect("primary_eval_rows_at_least_3737", prechecks.get("primary_eval_rows_at_least_3737"), True),
    ]


def _source_file_checks(
    artifact: Path,
    source_json: Path,
    source_md: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
    sha_entries: int,
) -> list[dict[str, Any]]:
    checks = [_check(f"source_file_{name}", (artifact / name).is_file(), str(artifact / name), "file") for name in REQUIRED_SOURCE_FILES]
    checks.extend(
        [
            _expect("source_json_file", source_json.resolve(), artifact / SOURCE_REVIEW_JSON_NAME),
            _expect("source_md_file", source_md.resolve(), artifact / SOURCE_REVIEW_MD_NAME),
            _expect("source_sha256s_file", source_sha256s.resolve(), artifact / "SHA256SUMS"),
            _expect("source_root_sha256s_file", source_root_sha256s.resolve(), artifact / "ROOT_SHA256SUMS"),
            _check("source_sha256_manifest_has_wrapper_files", sha_entries >= 8, sha_entries, ">=8"),
        ]
    )
    return checks


def _allowed_scope() -> dict[str, Any]:
    return {
        "dataset_scope": "v16 nuScenes scale-up paired evaluation",
        "fixed_dp_head": FIXED_DP_HEAD,
        "k_candidate_count": [8, 8],
        "primary_eval_rows": 3737,
        "records": 10000,
        "rows_scope": "calibration+holdout",
        "scenes": 50,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    claim = report["claim_record"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Claim Decision",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source static review artifact: `{report['source_static_review_artifact']['path']}`",
            f"- Source static review root SHA256: `{claim['source_static_review_root_sha256']}`",
            f"- Claim language: `{claim['language']}`",
            "",
            "## Limited Claim",
            "",
            claim["claim_text"],
            "",
            "## Forbidden / Non-Claim Boundary",
            "",
            "- No safety, closed-loop safety, deployment, broad nuScenes benchmark, Full36/formal-seed, DP model improvement, or trajectory-generation claim.",
            "- No promotion, deployment, online activation, training, paired-evaluation rerun, DP modification, or candidate tensor mutation.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    claim = report["claim_record"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_STATIC_REVIEW_CAMP_HEAD={heads['source_static_review_camp_head']}",
            f"SOURCE_PLAN_CAMP_HEAD={heads['source_plan_camp_head']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={claim['source_static_review_root_sha256']}",
            f"SOURCE_PLAN_ROOT_SHA256={claim['source_plan_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _verify_sha256s(root: Path, manifest: Path) -> tuple[int, list[str]]:
    if not manifest.is_file():
        return 0, [str(manifest)]
    failures = []
    count = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        path = root / name.strip()
        count += 1
        if not path.is_file():
            failures.append(f"missing:{name.strip()}")
        elif _sha256(path) != expected:
            failures.append(f"mismatch:{name.strip()}")
    return count, failures


def _claim_text_clean(text: str) -> bool:
    lowered = text.lower()
    return all(term.lower() not in lowered for term in PLAN_MODULE.FORBIDDEN_WORDING)


def _latest_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, 1)[1].splitlines()[0].strip()


def _first_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    for line in text.splitlines():
        if line.startswith(marker):
            return line.split("=", 1)[1].strip()
    return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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
