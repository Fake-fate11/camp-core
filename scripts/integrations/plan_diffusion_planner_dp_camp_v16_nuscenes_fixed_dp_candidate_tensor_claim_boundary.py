#!/usr/bin/env python3
"""Plan the v16 fixed-DP candidate tensor claim boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_source_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_result_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_source_module()
FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SOURCE_SCHEMA_VERSION = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_JSON_NAME = SOURCE_MODULE.REVIEW_JSON_NAME
SOURCE_MD_NAME = SOURCE_MODULE.REVIEW_MD_NAME
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan.md"
EXPECTED_METRICS = {
    "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
    "ci95": {"low": -0.021974139797953596, "high": -0.01326782174277094},
    "mean_delta": -0.01762098077036227,
    "non_top1_selection_rate": 0.903933636606904,
    "oracle_gap_closed": 0.9619006786247026,
}
FORBIDDEN_CLAIMS = [
    "safety claim",
    "closed-loop safety claim",
    "deployment claim",
    "broad nuScenes benchmark claim",
    "Full36/formal seeds claim",
    "DP model improvement claim",
    "trajectory generation claim",
]
FORBIDDEN_WORDING = ["safe", "deployable", "beats DP generally", "improves TIER IV DP model"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_source_root_sha256", required=True)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_sha256s=args.source_result_review_sha256s,
        source_result_review_root_sha256s=args.source_result_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan,
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
    source_review = source.get("scaleup_evidence_package_result_review", {})
    source_final = source.get("final_decision", {})
    source_sha_entries, source_sha_failures = _verify_sha256s(source_artifact, source_result_review_sha256s)
    source_root_sha = _read_root_sha(source_result_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    plan = _claim_boundary_plan(source_review)
    checks = [
        _expect("claim_boundary_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", source_artifact.is_dir(), str(source_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_final.get("passed"), True),
        _expect("source_authorizes_claim_boundary_plan", source_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_root_sha256", source_root_sha, expected_source_root_sha256),
        _check("source_result_review_sha256s_verified", not source_sha_failures, source_sha_failures[:10], []),
        _contains("audit_authorizes_claim_boundary_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_claim_boundary_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_artifact_count", source_review.get("source_artifact_count"), 8),
        _expect("source_artifacts_sha_verified", plan["preclaim_checks"]["source_artifacts_sha_verified"], True),
        _expect("fixed_dp_head", plan["preclaim_checks"]["fixed_dp_head"], True),
        _expect("no_dp_modification", plan["preclaim_checks"]["no_dp_modification"], True),
        _expect("no_candidate_tensor_mutation", plan["preclaim_checks"]["no_candidate_tensor_mutation"], True),
        _expect("no_train_leakage_into_primary_eval", plan["preclaim_checks"]["no_train_leakage_into_primary_eval"], True),
        _expect("affine_simplex_preserved", plan["preclaim_checks"]["affine_simplex_preserved"], True),
        _expect("ci95_high_less_than_zero", plan["preclaim_checks"]["ci95_high_less_than_zero"], True),
        _expect("better_greater_than_worse", plan["preclaim_checks"]["better_greater_than_worse"], True),
        _expect("primary_eval_rows_at_least_3737", plan["preclaim_checks"]["primary_eval_rows_at_least_3737"], True),
        _expect("allowed_claim_scope_records", plan["supported_claims"][0]["scope"]["records"], 10000),
        _expect("allowed_claim_scope_scenes", plan["supported_claims"][0]["scope"]["scenes"], 50),
        _expect("allowed_claim_scope_rows", plan["supported_claims"][0]["scope"]["primary_eval_rows"], 3737),
        _expect("allowed_claim_metrics", plan["supported_claims"][0]["metrics"], EXPECTED_METRICS),
        _expect("forbidden_claims", plan["forbidden_claims"], FORBIDDEN_CLAIMS),
        _expect("wording_mode_limited_descriptive", plan["wording"]["mode"], "limited/descriptive"),
        _expect("wording_forbidden_terms", plan["wording"]["forbidden_terms"], FORBIDDEN_WORDING),
        _check("allowed_wording_avoids_forbidden_terms", _allowed_wording_clean(plan), plan["wording"]["allowed_wording"], "no forbidden terms"),
        _expect("next_gate_static_review", plan["next_gates"][0], AUTHORIZED_NEXT_WORK),
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
            "claim_boundary_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "claim_boundary_plan_only": True,
                "claim_executed": False,
                "limited_descriptive_claim_planned": True,
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


def _claim_boundary_plan(source_review: dict[str, Any]) -> dict[str, Any]:
    package_report = source_review.get("package_report", {})
    metrics = package_report.get("metrics_summary", {})
    better_tie_worse = metrics.get("better_tie_worse", {})
    ci95 = metrics.get("ci95", {})
    split_rows = package_report.get("split_rows", {})
    rows = package_report.get("paired_eval_rows")
    claim = {
        "id": "fixed_dp_k8_current_paired_metric_reduction",
        "wording": (
            "On fixed-DP K=8 candidate tensors, the CAMP selector reduced the current paired metric "
            "in the v16 nuScenes scale-up paired evaluation."
        ),
        "scope": {
            "dataset_scope": "v16 nuScenes scale-up paired evaluation",
            "records": package_report.get("records"),
            "scenes": package_report.get("scenes"),
            "rows_scope": "calibration+holdout",
            "primary_eval_rows": rows,
            "fixed_dp_head": source_review.get("dp_head_fixed"),
            "k_candidate_count": source_review.get("k_candidate_count"),
        },
        "metrics": metrics,
    }
    allowed_wording = [
        "In the v16 nuScenes scale-up paired evaluation on fixed-DP K=8 candidate tensors, the CAMP selector reduced the current paired metric over 3737 calibration+holdout rows.",
        "This is limited descriptive evidence for the current paired metric within the 10k-record / 50-scene v16 scale-up scope.",
    ]
    return {
        "supported_claims": [claim],
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "source_artifact_count": source_review.get("source_artifact_count"),
        "source_artifact_ids": source_review.get("source_artifact_ids", []),
        "evidence_scope": {
            "records": package_report.get("records"),
            "scenes": package_report.get("scenes"),
            "train_calibration_holdout": [
                split_rows.get("train"),
                split_rows.get("calibration"),
                split_rows.get("holdout"),
            ],
            "paired_eval_rows": rows,
        },
        "preclaim_checks": {
            "source_artifacts_sha_verified": source_review.get("all_source_artifact_sha_verified") is True,
            "fixed_dp_head": source_review.get("dp_head_fixed") == FIXED_DP_HEAD,
            "no_dp_modification": source_review.get("dp_head_fixed") == FIXED_DP_HEAD,
            "no_candidate_tensor_mutation": source_review.get("candidate_tensor_unmodified") is True,
            "no_train_leakage_into_primary_eval": source_review.get("train_rows_in_primary_eval") == 0,
            "affine_simplex_preserved": source_review.get("affine_simplex_preserved") is True,
            "ci95_high_less_than_zero": ci95.get("high", 1) < 0,
            "better_greater_than_worse": better_tie_worse.get("better", 0) > better_tie_worse.get("worse", 0),
            "primary_eval_rows_at_least_3737": rows is not None and rows >= 3737,
        },
        "wording": {
            "mode": "limited/descriptive",
            "allowed_wording": allowed_wording,
            "forbidden_terms": FORBIDDEN_WORDING,
        },
        "next_gates": [
            AUTHORIZED_NEXT_WORK,
            "claim decision only after static review",
            "optional 32k expansion plan if stronger evidence is requested",
        ],
        "forbidden_work": [
            "direct_claim",
            "promotion",
            "deployment",
            "new_training",
            "new_paired_evaluation",
            "dp_modification",
            "candidate_tensor_mutation",
        ],
    }


def _allowed_wording_clean(plan: dict[str, Any]) -> bool:
    text = " ".join(plan["wording"]["allowed_wording"]).lower()
    return all(term.lower() not in text for term in plan["wording"]["forbidden_terms"])


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
    ]
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
        path = root / rel.strip()
        if not path.is_file():
            failed.append(f"missing:{rel.strip()}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{rel.strip()}")
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
    plan = report["claim_boundary_plan"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Claim Boundary Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Scope: plan only; no direct claim, promotion, deployment, training, or paired-evaluation rerun.",
            f"- Supported limited claim: `{plan['supported_claims'][0]}`",
            f"- Forbidden claims: `{plan['forbidden_claims']}`",
            f"- Pre-claim checks: `{plan['preclaim_checks']}`",
            f"- Wording boundary: `{plan['wording']}`",
            f"- Next gates: `{plan['next_gates']}`",
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
            f"SOURCE_ROOT_SHA256={report['source_artifact']['root_sha256']}",
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
