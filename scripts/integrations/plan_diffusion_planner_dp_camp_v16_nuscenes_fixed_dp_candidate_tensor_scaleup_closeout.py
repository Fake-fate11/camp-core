#!/usr/bin/env python3
"""Plan closeout for the v16 fixed-DP candidate tensor scale-up evidence chain."""

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
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result.py"
    )
    spec = importlib.util.spec_from_file_location("v16_claim_decision_result_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_source_module()
FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SOURCE_REVIEW_SCHEMA = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_rejected"
AUTHORIZED_NEXT_WORK = "user_decision_required_before_v16_nuscenes_fixed_dp_candidate_tensor_next_stage"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan.md"
NEXT_OPTIONS = [
    "32k expansion plan for stronger evidence",
    "formal benchmark/claim pathway",
    "integration/runtime packaging pathway",
]
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_result_review_root_sha256", required=True)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
        source_result_review_root_sha256s=args.source_result_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_result_review_root_sha256=args.expected_result_review_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    source_result_review_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_result_review_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_result_review_artifact_dir.resolve()
    source = _read_json(source_result_review_json)
    source_decision = source.get("final_decision", {})
    source_review = source.get("claim_decision_result_review", {})
    sha_entries, sha_failures = _verify_sha256s(artifact, source_result_review_sha256s)
    source_root_sha = _read_root_sha(source_result_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    closeout = _closeout_plan(source_root_sha, source_review)
    checks = [
        _expect("closeout_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_result_review_json_path", source_result_review_json.resolve(), artifact / SOURCE_REVIEW_JSON_NAME),
        _expect("source_result_review_md_path", source_result_review_md.resolve(), artifact / SOURCE_REVIEW_MD_NAME),
        _expect("source_result_review_root_sha256", source_root_sha, expected_result_review_root_sha256),
        _check("source_result_review_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_result_review_schema", source.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        _expect("source_result_review_status", source.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_result_review_passed", source_decision.get("passed"), True),
        _expect("source_result_review_authorizes_closeout", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_only", source_decision.get("result_review_only"), True),
        _expect("source_claim_text_modified_false", source_decision.get("claim_text_modified"), False),
        _expect("source_promotion_false", source_decision.get("promotion_authorized"), False),
        _expect("source_deployment_false", source_decision.get("deployment_authorized"), False),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v16_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_current_status", _first_value(status_text, "current_v16_status"), SOURCE_REVIEW_STATUS),
        _expect("status_current_next_work", _first_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("claim_text", source_review.get("claim_text"), SOURCE_MODULE.SOURCE_MODULE.CLAIM_TEXT),
        _expect("claim_text_clean", source_review.get("claim_text_avoids_forbidden_terms"), True),
        _expect("next_options", closeout["next_options"], NEXT_OPTIONS),
        _expect("not_executed", closeout["not_executed"], _not_executed()),
    ]
    checks.extend(_source_file_checks(artifact, source_result_review_json, source_result_review_md, source_result_review_sha256s, source_result_review_root_sha256s, sha_entries))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_result_review_artifact": {
                "path": str(artifact),
                "json": str(source_result_review_json.resolve()),
                "md": str(source_result_review_md.resolve()),
                "root_sha256": source_root_sha,
                "expected_root_sha256": expected_result_review_root_sha256,
                "sha256_entry_count": sha_entries,
                "failed_sha256s": sha_failures,
                "sha256s_sha256": _sha256(source_result_review_sha256s) if source_result_review_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_result_review_root_sha256s) if source_result_review_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_result_review_camp_head": source.get("heads", {}).get("camp_head"),
                "source_claim_decision_camp_head": source.get("heads", {}).get("source_claim_decision_camp_head"),
            },
            "scaleup_closeout_plan": closeout,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "closeout_plan_only": True,
                "user_decision_required": bool(passed),
                "next_stage_executed": False,
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
    (output_dir / PLAN_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PLAN_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    _write_sha_manifests(output_dir)


def _closeout_plan(source_root_sha: str | None, source_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_result_review_root_sha256": source_root_sha,
        "source_claim_decision_root_sha256": source_review.get("source_claim_decision_root_sha256"),
        "claim_text": source_review.get("claim_text"),
        "current_scope": {
            "candidate_count": 8,
            "dataset": "v16 nuScenes scale-up paired evaluation",
            "fixed_dp_head": FIXED_DP_HEAD,
            "primary_eval_rows": 3737,
            "records": 10000,
            "scenes": 50,
        },
        "current_metrics": {
            "better_tie_worse": [3365, 359, 13],
            "mean_delta": -0.01762098077036227,
            "ci95_high": -0.01326782174277094,
            "non_top1_selection_rate": 0.903933636606904,
            "oracle_gap_closed": 0.9619006786247026,
        },
        "current_limitations": [
            "limited/descriptive current paired metric claim only",
            "no safety or deployment claim",
            "no broad nuScenes benchmark claim",
            "no DP model improvement claim",
            "no trajectory generation claim",
        ],
        "next_options": NEXT_OPTIONS,
        "not_executed": _not_executed(),
    }


def _not_executed() -> dict[str, bool]:
    return {
        "32k_expansion": True,
        "formal_benchmark": True,
        "integration_runtime_packaging": True,
        "promotion": True,
        "deployment": True,
        "online_activation": True,
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
            _expect("source_json_file", source_json.resolve(), artifact / SOURCE_REVIEW_JSON_NAME),
            _expect("source_md_file", source_md.resolve(), artifact / SOURCE_REVIEW_MD_NAME),
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
    plan = report["scaleup_closeout_plan"]
    lines = [
        "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Closeout Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source result-review artifact: `{report['source_result_review_artifact']['path']}`",
        "",
        "## Current Outcome",
        "",
        f"- Claim: {plan['claim_text']}",
        f"- Scope: `{plan['current_scope']}`",
        f"- Metrics: `{plan['current_metrics']}`",
        "",
        "## Next Options",
        "",
    ]
    for option in plan["next_options"]:
        lines.append(f"- {option}")
    lines.extend(["", "Closeout plan only; no next-stage execution.", ""])
    return "\n".join(lines)


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    plan = report["scaleup_closeout_plan"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_RESULT_REVIEW_CAMP_HEAD={heads['source_result_review_camp_head']}",
            f"SOURCE_CLAIM_DECISION_CAMP_HEAD={heads['source_claim_decision_camp_head']}",
            f"SOURCE_RESULT_REVIEW_ROOT_SHA256={plan['source_result_review_root_sha256']}",
            f"SOURCE_CLAIM_DECISION_ROOT_SHA256={plan['source_claim_decision_root_sha256']}",
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
