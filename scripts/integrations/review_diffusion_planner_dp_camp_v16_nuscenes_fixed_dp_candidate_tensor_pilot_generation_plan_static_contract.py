#!/usr/bin/env python3
"""Static-review the v16 nuScenes fixed-DP pilot generation plan."""

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
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation.py"
    )
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_v1"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review_v1"
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_only"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_md", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review",
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
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review,
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
    sha_entries = _read_sha256s(source_plan_sha256s)
    sha_failures = _verify_sha256s(artifact, sha_entries)
    plan_root_sha = _sha256(source_plan_sha256s) if source_plan_sha256s.is_file() else None
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    final = source.get("final_decision", {})
    pilot_plan = source.get("pilot_plan", {})
    timing = source.get("timing_estimates", {}).get("1024", {})
    inputs = source.get("inputs", {})
    source_artifacts = source.get("source_artifacts", {})
    outputs = source.get("outputs", [])
    pass_conditions = source.get("pass_conditions", [])
    stop_conditions = source.get("stop_conditions", [])
    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_plan_json_path", source_plan_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("source_plan_md_path", source_plan_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
        _expect("source_plan_sha256s_path", source_plan_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_plan_schema", source.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_passed", final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _contains("audit_authorizes_static_review", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_pilot_plan", v16_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _contains("status_records_pilot_plan", status_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _expect("plan_selected_target_records_1024", pilot_plan.get("selected_target_records"), 1024),
        _expect("plan_k_8", pilot_plan.get("k"), 8),
        _expect("plan_candidate_count_8", pilot_plan.get("candidate_count"), 8),
        _expect("plan_dp_head_fixed", inputs.get("dp_fixed_head"), FIXED_DP_HEAD),
        _check("plan_references_smoke_source_artifact", bool(source_artifacts.get("smoke_artifact")), source_artifacts.get("smoke_artifact"), "present"),
        _check("plan_references_smoke_review_artifact", bool(inputs.get("source_smoke_review_artifact")), inputs.get("source_smoke_review_artifact"), "present"),
        _expect("plan_uses_smoke_mean_seconds", timing.get("per_record_mean_seconds"), 5.31974),
        _expect("plan_1024_wall_clock_seconds", timing.get("wall_clock_seconds"), 5447.41376),
        _expect("plan_1024_wall_clock_hours", timing.get("wall_clock_hours"), 1.51317),
    ]
    checks.extend(_contains_all("plan_output_contract", outputs, _required_outputs()))
    checks.extend(_contains_all("plan_pass_conditions", pass_conditions, _required_pass_conditions()))
    checks.extend(_contains_all("plan_stop_conditions", stop_conditions, _required_stop_conditions()))
    checks.extend(_no_forbidden_work_checks(final))
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", PLAN_MODULE.PLAN_JSON_NAME, PLAN_MODULE.PLAN_MD_NAME):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "source_plan_artifact": str(artifact),
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "plan_review": {
                "source_plan_root_sha256": plan_root_sha,
                "source_smoke_artifact": source_artifacts.get("smoke_artifact"),
                "source_review_artifact": inputs.get("source_smoke_review_artifact"),
                "selected_target_records": pilot_plan.get("selected_target_records"),
                "k": pilot_plan.get("k"),
                "candidate_count": pilot_plan.get("candidate_count"),
                "per_record_mean_seconds": timing.get("per_record_mean_seconds"),
                "wall_clock_seconds_1024": timing.get("wall_clock_seconds"),
                "wall_clock_hours_1024": timing.get("wall_clock_hours"),
                "output_contract": outputs,
                "pass_conditions": pass_conditions,
                "stop_conditions": stop_conditions,
            },
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "static_review_only": True,
                "candidate_generation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
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
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    paths = (json_path, md_path, heads_path, command_path)
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in paths),
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["plan_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Generation Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan artifact: `{report['source_plan_artifact']}`",
            f"- Source plan root SHA: `{review['source_plan_root_sha256']}`",
            f"- Selected target records: `{review['selected_target_records']}`",
            f"- Estimated 1024 wall-clock hours: `{review['wall_clock_hours_1024']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    review = report["plan_review"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={review['source_plan_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _required_outputs() -> tuple[str, ...]:
    return (
        "JSON summary",
        "JSONL records",
        "candidate tensor hashes",
        "HEADS",
        "COMMAND",
        "stdout",
        "stderr",
        "SHA256SUMS",
    )


def _required_pass_conditions() -> tuple[str, ...]:
    return (
        "records == target_records",
        "failure_count == 0",
        "all dp_top1_index in [0,7]",
        "all candidate_tensor_sha256 present",
    )


def _required_stop_conditions() -> tuple[str, ...]:
    return (
        "DP HEAD mismatch",
        "output root exists",
        "records shortfall",
        "any fake/synthetic candidate tensor",
        "any DP/candidate/trajectory mutation",
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_plan_{field}_false", final.get(field), False)
        for field in (
            "candidate_generation_executed",
            "training_executed",
            "paired_evaluation_executed",
            "performance_claimed",
            "promotion_executed",
            "deployment_executed",
            "dp_modified",
            "candidate_tensor_modified",
            "fake_candidate_tensor_generated",
        )
    ]


def _contains_all(name: str, actual: list[str], required: tuple[str, ...]) -> list[dict[str, Any]]:
    return [_check(f"{name}_{item}", item in actual, item if item in actual else "missing", item) for item in required]


def _verify_sha256s(root: Path, entries: dict[str, str]) -> list[str]:
    failed = []
    for name, expected in entries.items():
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return failed


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        entries[Path(name.strip()).as_posix()] = digest
    return entries


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
