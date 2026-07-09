#!/usr/bin/env python3
"""Static-review the v16 fixed-DP candidate tensor claim-boundary plan."""

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
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary.py"
    )
    spec = importlib.util.spec_from_file_location("v16_claim_boundary_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review.md"
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
    "direct_claim",
    "promotion",
    "deployment",
    "new_training",
    "new_paired_evaluation",
    "dp_modification",
    "candidate_tensor_mutation",
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
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review", action="store_true")
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
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review,
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
    plan = source.get("claim_boundary_plan", {})
    claim = (plan.get("supported_claims") or [{}])[0]
    scope = claim.get("scope", {})
    metrics = claim.get("metrics", {})
    prechecks = plan.get("preclaim_checks", {})
    wording = plan.get("wording", {})
    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_plan_json_path", source_plan_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("source_plan_md_path", source_plan_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
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
        _expect("allowed_claim_id", claim.get("id"), "fixed_dp_k8_current_paired_metric_reduction"),
        _expect("allowed_scope_dataset", scope.get("dataset_scope"), "v16 nuScenes scale-up paired evaluation"),
        _expect("allowed_scope_fixed_dp_head", scope.get("fixed_dp_head"), FIXED_DP_HEAD),
        _expect("allowed_scope_k_candidate_count", scope.get("k_candidate_count"), [8, 8]),
        _expect("allowed_scope_rows", scope.get("primary_eval_rows"), 3737),
        _expect("allowed_scope_records", scope.get("records"), 10000),
        _expect("allowed_scope_scenes", scope.get("scenes"), 50),
        _expect("allowed_scope_rows_scope", scope.get("rows_scope"), "calibration+holdout"),
        _expect("metrics_summary", metrics, PLAN_MODULE.EXPECTED_METRICS),
        _expect("forbidden_claims", plan.get("forbidden_claims"), PLAN_MODULE.FORBIDDEN_CLAIMS),
        _expect("wording_mode_limited_descriptive", wording.get("mode"), "limited/descriptive"),
        _expect("forbidden_wording_terms", wording.get("forbidden_terms"), PLAN_MODULE.FORBIDDEN_WORDING),
        _check("allowed_wording_avoids_forbidden_terms", _allowed_wording_clean(wording), wording.get("allowed_wording"), "no forbidden terms"),
        _expect("source_artifacts_sha_verified", prechecks.get("source_artifacts_sha_verified"), True),
        _expect("fixed_dp_head", prechecks.get("fixed_dp_head"), True),
        _expect("no_dp_modification", prechecks.get("no_dp_modification"), True),
        _expect("no_candidate_tensor_mutation", prechecks.get("no_candidate_tensor_mutation"), True),
        _expect("no_train_leakage_into_primary_eval", prechecks.get("no_train_leakage_into_primary_eval"), True),
        _expect("affine_simplex_preserved", prechecks.get("affine_simplex_preserved"), True),
        _expect("ci95_high_less_than_zero", prechecks.get("ci95_high_less_than_zero"), True),
        _expect("better_greater_than_worse", prechecks.get("better_greater_than_worse"), True),
        _expect("primary_eval_rows_at_least_3737", prechecks.get("primary_eval_rows_at_least_3737"), True),
        _expect("next_gate_static_review", (plan.get("next_gates") or [None])[0], AUTHORIZED_CURRENT_WORK),
        _expect("next_gate_claim_decision_after_static_review", (plan.get("next_gates") or [None, None])[1], "claim decision only after static review"),
    ]
    checks.extend(_source_file_checks(artifact, source_plan_json, source_plan_md, source_plan_sha256s, source_plan_root_sha256s, sha_entries))
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
            "claim_boundary_plan_static_review": {
                "source_plan_root_sha256": plan_root_sha,
                "allowed_claim_id": claim.get("id"),
                "allowed_claim_scope": scope,
                "metrics": metrics,
                "forbidden_claims": plan.get("forbidden_claims"),
                "forbidden_wording": wording.get("forbidden_terms"),
                "wording_mode": wording.get("mode"),
                "preclaim_checks": prechecks,
                "next_gates": [AUTHORIZED_NEXT_WORK, *list((plan.get("next_gates") or [])[1:])],
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
                "claim_executed": False,
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


def _allowed_wording_clean(wording: dict[str, Any]) -> bool:
    text = " ".join(wording.get("allowed_wording", [])).lower()
    return all(term.lower() not in text for term in wording.get("forbidden_terms", []))


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
    checks.append(_check("source_sha256s_complete", sha_entries >= 8, sha_entries, ">=8"))
    return checks


def _forbidden_work_checks(work: list[str]) -> list[dict[str, Any]]:
    return [_check(f"forbidden_work_{name}_listed", name in work, "present" if name in work else "missing", name) for name in FORBIDDEN_WORK]


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        _expect("source_claim_boundary_plan_only", final.get("claim_boundary_plan_only"), True),
        _expect("source_limited_descriptive_claim_planned", final.get("limited_descriptive_claim_planned"), True),
    ]
    for field in (
        "claim_executed",
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
    review = report["claim_boundary_plan_static_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Claim Boundary Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan artifact: `{report['source_plan_artifact']['path']}`",
            f"- Source plan root SHA256: `{review['source_plan_root_sha256']}`",
            f"- Allowed claim id: `{review['allowed_claim_id']}`",
            f"- Allowed claim scope: `{review['allowed_claim_scope']}`",
            f"- Forbidden claims: `{review['forbidden_claims']}`",
            f"- Forbidden wording: `{review['forbidden_wording']}`",
            f"- Pre-claim checks: `{review['preclaim_checks']}`",
            "- Static review only; no claim decision, promotion, deployment, training, or paired-evaluation rerun.",
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
