#!/usr/bin/env python3
"""Review the v16 fixed-DP candidate tensor claim decision result."""

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
        "decide_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim.py"
    )
    spec = importlib.util.spec_from_file_location("v16_claim_decision", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_source_module()
FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SOURCE_DECISION_SCHEMA = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_DECISION_STATUS = SOURCE_MODULE.READY_STATUS
SOURCE_DECISION_JSON_NAME = SOURCE_MODULE.DECISION_JSON_NAME
SOURCE_DECISION_MD_NAME = SOURCE_MODULE.DECISION_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review.md"
FORBIDDEN_RESULT_WORDING = [*SOURCE_MODULE.PLAN_MODULE.FORBIDDEN_WORDING, "trajectory generation"]
REQUIRED_SOURCE_FILES = (
    SOURCE_DECISION_JSON_NAME,
    SOURCE_DECISION_MD_NAME,
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
    parser.add_argument("--source_claim_decision_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_claim_decision_json", type=Path, required=True)
    parser.add_argument("--source_claim_decision_md", type=Path, required=True)
    parser.add_argument("--source_claim_decision_sha256s", type=Path, required=True)
    parser.add_argument("--source_claim_decision_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_claim_decision_root_sha256", required=True)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_claim_decision_artifact_dir=args.source_claim_decision_artifact_dir,
        source_claim_decision_json=args.source_claim_decision_json,
        source_claim_decision_md=args.source_claim_decision_md,
        source_claim_decision_sha256s=args.source_claim_decision_sha256s,
        source_claim_decision_root_sha256s=args.source_claim_decision_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_claim_decision_root_sha256=args.expected_claim_decision_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_claim_decision_artifact_dir: Path,
    source_claim_decision_json: Path,
    source_claim_decision_md: Path,
    source_claim_decision_sha256s: Path,
    source_claim_decision_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_claim_decision_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_claim_decision_artifact_dir.resolve()
    source = _read_json(source_claim_decision_json)
    source_decision = source.get("final_decision", {})
    source_claim = source.get("claim_record", {})
    sha_entries, sha_failures = _verify_sha256s(artifact, source_claim_decision_sha256s)
    source_root_sha = _read_root_sha(source_claim_decision_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    review = _review_record(source_root_sha, source_claim, source_decision)
    checks = [
        _expect("result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_claim_decision_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_claim_decision_json_path", source_claim_decision_json.resolve(), artifact / SOURCE_DECISION_JSON_NAME),
        _expect("source_claim_decision_md_path", source_claim_decision_md.resolve(), artifact / SOURCE_DECISION_MD_NAME),
        _expect("source_claim_decision_root_sha256", source_root_sha, expected_claim_decision_root_sha256),
        _check("source_claim_decision_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_claim_decision_schema", source.get("schema_version"), SOURCE_DECISION_SCHEMA),
        _expect("source_claim_decision_status", source.get("status"), SOURCE_DECISION_STATUS),
        _expect("source_claim_decision_passed", source_decision.get("passed"), True),
        _expect("source_claim_decision_authorizes_result_review", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v16_status"), SOURCE_DECISION_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_current_status", _first_value(status_text, "current_v16_status"), SOURCE_DECISION_STATUS),
        _expect("status_current_next_work", _first_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("claim_text_exact", source_claim.get("claim_text"), SOURCE_MODULE.CLAIM_TEXT),
        _expect("claim_language", source_claim.get("language"), SOURCE_MODULE.CLAIM_LANGUAGE),
        _check("claim_text_avoids_forbidden_terms", review["claim_text_avoids_forbidden_terms"], source_claim.get("claim_text"), "no forbidden terms"),
        _expect("forbidden_claims", source_claim.get("forbidden_claims"), SOURCE_MODULE.PLAN_MODULE.FORBIDDEN_CLAIMS),
        _expect("forbidden_wording", source_claim.get("forbidden_wording"), SOURCE_MODULE.PLAN_MODULE.FORBIDDEN_WORDING),
        _expect("non_claim_boundary", source_claim.get("non_claim_boundary"), SOURCE_MODULE.NON_CLAIM_BOUNDARY),
        _expect("source_limited_descriptive_claim_authorized", source_decision.get("limited_descriptive_claim_authorized"), True),
        _expect("source_claim_executed", source_decision.get("claim_executed_by_this_gate"), True),
        _expect("source_safety_claim_false", source_decision.get("safety_claim_authorized"), False),
        _expect("source_closed_loop_safety_claim_false", source_decision.get("closed_loop_safety_claim_authorized"), False),
        _expect("source_deployment_false", source_decision.get("deployment_authorized"), False),
        _expect("source_promotion_false", source_decision.get("promotion_authorized"), False),
        _expect("source_online_activation_false", source_decision.get("online_activation_authorized"), False),
        _expect("source_broad_benchmark_false", source_decision.get("broad_nuscenes_benchmark_claim_authorized"), False),
        _expect("source_full36_formal_false", source_decision.get("full36_or_formal_seed_claim_authorized"), False),
        _expect("source_dp_model_improvement_false", source_decision.get("dp_model_improvement_claim_authorized"), False),
        _expect("source_trajectory_generation_false", source_decision.get("trajectory_generation_claim_authorized"), False),
    ]
    checks.extend(_source_file_checks(artifact, source_claim_decision_json, source_claim_decision_md, source_claim_decision_sha256s, source_claim_decision_root_sha256s, sha_entries))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_claim_decision_artifact": {
                "path": str(artifact),
                "json": str(source_claim_decision_json.resolve()),
                "md": str(source_claim_decision_md.resolve()),
                "root_sha256": source_root_sha,
                "expected_root_sha256": expected_claim_decision_root_sha256,
                "sha256_entry_count": sha_entries,
                "failed_sha256s": sha_failures,
                "sha256s_sha256": _sha256(source_claim_decision_sha256s) if source_claim_decision_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_claim_decision_root_sha256s) if source_claim_decision_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_claim_decision_camp_head": source.get("heads", {}).get("camp_head"),
                "source_static_review_camp_head": source.get("heads", {}).get("source_static_review_camp_head"),
                "source_plan_camp_head": source.get("heads", {}).get("source_plan_camp_head"),
            },
            "claim_decision_result_review": review,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "result_review_only": True,
                "claim_text_modified": False,
                "promotion_authorized": False,
                "deployment_authorized": False,
                "online_activation_authorized": False,
                "training_executed": False,
                "paired_evaluation_rerun": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REVIEW_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / REVIEW_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    _write_sha_manifests(output_dir)


def _review_record(source_root_sha: str | None, source_claim: dict[str, Any], source_decision: dict[str, Any]) -> dict[str, Any]:
    claim_text = source_claim.get("claim_text", "")
    return {
        "source_claim_decision_root_sha256": source_root_sha,
        "source_static_review_root_sha256": source_claim.get("source_static_review_root_sha256"),
        "source_plan_root_sha256": source_claim.get("source_plan_root_sha256"),
        "claim_text": claim_text,
        "claim_language": source_claim.get("language"),
        "claim_text_avoids_forbidden_terms": _claim_text_clean(claim_text),
        "forbidden_claims": source_claim.get("forbidden_claims"),
        "forbidden_wording": source_claim.get("forbidden_wording"),
        "non_claim_boundary": source_claim.get("non_claim_boundary"),
        "source_claim_flags": {
            key: source_decision.get(key)
            for key in (
                "broad_nuscenes_benchmark_claim_authorized",
                "closed_loop_safety_claim_authorized",
                "deployment_authorized",
                "dp_model_improvement_claim_authorized",
                "full36_or_formal_seed_claim_authorized",
                "limited_descriptive_claim_authorized",
                "online_activation_authorized",
                "promotion_authorized",
                "safety_claim_authorized",
                "trajectory_generation_claim_authorized",
            )
        },
    }


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
            _expect("source_json_file", source_json.resolve(), artifact / SOURCE_DECISION_JSON_NAME),
            _expect("source_md_file", source_md.resolve(), artifact / SOURCE_DECISION_MD_NAME),
            _expect("source_sha256s_file", source_sha256s.resolve(), artifact / "SHA256SUMS"),
            _expect("source_root_sha256s_file", source_root_sha256s.resolve(), artifact / "ROOT_SHA256SUMS"),
            _check("source_sha256_manifest_has_wrapper_files", sha_entries >= 8, sha_entries, ">=8"),
        ]
    )
    return checks


def _write_sha_manifests(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.name}\n")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text("".join(rows), encoding="utf-8")
    (output_dir / "ROOT_SHA256SUMS").write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["claim_decision_result_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Claim Decision Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source claim decision artifact: `{report['source_claim_decision_artifact']['path']}`",
            f"- Source claim decision root SHA256: `{review['source_claim_decision_root_sha256']}`",
            f"- Claim text avoids forbidden terms: `{review['claim_text_avoids_forbidden_terms']}`",
            "",
            "## Reviewed Claim",
            "",
            review["claim_text"],
            "",
            "Result review only; no claim text modification, promotion, deployment, online activation, training, paired-evaluation rerun, DP modification, or candidate tensor mutation.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    review = report["claim_decision_result_review"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_CLAIM_DECISION_CAMP_HEAD={heads['source_claim_decision_camp_head']}",
            f"SOURCE_STATIC_REVIEW_CAMP_HEAD={heads['source_static_review_camp_head']}",
            f"SOURCE_PLAN_CAMP_HEAD={heads['source_plan_camp_head']}",
            f"SOURCE_CLAIM_DECISION_ROOT_SHA256={review['source_claim_decision_root_sha256']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={review['source_static_review_root_sha256']}",
            f"SOURCE_PLAN_ROOT_SHA256={review['source_plan_root_sha256']}",
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
    return all(term.lower() not in lowered for term in FORBIDDEN_RESULT_WORDING)


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
