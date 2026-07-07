#!/usr/bin/env python3
"""Static-review the v15 paired-evaluation preflight plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight.py"
    )
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_preflight_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review_v1"
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_only"
REVIEW_JSON_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review.json"
REVIEW_MD_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_md", type=Path, required=True)
    parser.add_argument("--source_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_md=args.source_plan_md,
        source_sha256s=args.source_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_md: Path,
    source_sha256s: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_plan_artifact_dir.resolve()
    source = _read_json(source_plan_json)
    sha256s = _read_sha256s(source_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    decision = source["final_decision"]
    plan = source["paired_evaluation_preflight_plan"]

    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_plan_schema", source.get("schema_version"), PLAN_MODULE.SCHEMA_VERSION),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_authorized_static_review", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_training_not_executed", decision.get("training_executed"), False),
        _expect("source_paired_eval_not_executed", decision.get("paired_evaluation_executed"), False),
        _expect("source_online_latency_not_executed", decision.get("online_selector_latency_executed"), False),
        _expect("source_fallback_latency_not_executed", decision.get("fallback_latency_executed"), False),
        _expect("source_performance_not_claimed", decision.get("performance_claimed"), False),
        _expect("source_full36_not_used", decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_static_review", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _check("plan_eval_splits", set(plan["required_inputs"]["evaluation_splits"]) == {"calibration", "holdout"}, plan["required_inputs"]["evaluation_splits"], "calibration and holdout"),
        _check("plan_train_split_not_evaluated", "train" not in plan["required_inputs"]["evaluation_splits"], plan["required_inputs"]["evaluation_splits"], "no train split"),
        _expect("plan_baseline", plan["paired_protocol"].get("baseline"), "dp_top1"),
        _expect("plan_camp_policy", plan["paired_protocol"].get("camp_selection_policy"), "select_from_fixed_dp_candidate_tensor"),
        _expect("plan_candidate_tensor_provenance", plan["paired_protocol"].get("candidate_tensor_provenance"), "fixed_dp_candidate_tensor_only"),
        _expect("plan_online_latency_fields", tuple(plan["timing_contract"]["online_selector_latency_required_fields"]), PLAN_MODULE.LATENCY_FIELDS),
        _expect("plan_fallback_latency_fields", tuple(plan["timing_contract"]["fallback_latency_required_fields"]), PLAN_MODULE.LATENCY_FIELDS),
        _expect("plan_timing_behavior_unchanged", plan["timing_contract"].get("instrumentation_changes_selector_behavior"), False),
        _expect("plan_full36_used", plan["blocked_inputs"].get("Full36"), False),
        _expect("plan_formal_seed_used", plan["blocked_inputs"].get("formal_seeds_11_12_13"), False),
        _expect("plan_train_split_for_evaluation", plan["blocked_inputs"].get("train_split_for_evaluation"), False),
        _expect("plan_dp_modified", plan["mutations"].get("dp_modified"), False),
        _expect("plan_candidate_tensor_modified", plan["mutations"].get("candidate_tensor_modified"), False),
        _expect("plan_trajectory_modified", plan["mutations"].get("trajectory_modified"), False),
    ]
    for path in (source_plan_json, source_plan_md):
        checks.append(_expect(f"source_sha_{path.name}", _sha256(path), sha256s[path.name]))
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_plan_artifact": str(artifact),
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "reviewed_paired_evaluation_preflight_plan": True,
                "paired_evaluation_preflight_plan_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "online_selector_latency_executed": False,
                "fallback_latency_executed": False,
                "performance_claimed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V15 Paired Evaluation Preflight Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            entries[Path(name.strip()).name] = digest
    return entries


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
