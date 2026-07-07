#!/usr/bin/env python3
"""Preflight the v16 nuScenes fixed-DP pilot candidate tensor generation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import py_compile
import sys
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA_VERSION
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_v1"
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_only"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight.md"
TARGET_RECORDS = 1024
EXPECTED_K = 8
PER_RECORD_MEAN_SECONDS = 5.31974


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_review_json", type=Path, required=True)
    parser.add_argument("--source_review_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--nuscenes_root", type=Path, required=True)
    parser.add_argument("--camp_repo_root", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--candidate_output_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_review_root_sha256", required=True)
    parser.add_argument("--python_executable", default=sys.executable)
    parser.add_argument("--checkpoint", default="<fixed_dp_checkpoint>")
    parser.add_argument("--args_json", default="<fixed_dp_args_json>")
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_review_artifact_dir=args.source_review_artifact_dir,
        source_review_json=args.source_review_json,
        source_review_sha256s=args.source_review_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        nuscenes_root=args.nuscenes_root,
        camp_repo_root=args.camp_repo_root,
        dp_repo=args.dp_repo,
        candidate_output_root=args.candidate_output_root,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_review_root_sha256=args.expected_review_root_sha256,
        python_executable=args.python_executable,
        checkpoint=args.checkpoint,
        args_json=args.args_json,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight,
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
    source_review_artifact_dir: Path,
    source_review_json: Path,
    source_review_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    nuscenes_root: Path,
    camp_repo_root: Path,
    dp_repo: Path,
    candidate_output_root: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    expected_review_root_sha256: str,
    python_executable: str = sys.executable,
    checkpoint: str = "<fixed_dp_checkpoint>",
    args_json: str = "<fixed_dp_args_json>",
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    source_plan_artifact = source_plan_artifact_dir.resolve()
    source_review_artifact = source_review_artifact_dir.resolve()
    plan = _read_json(source_plan_json)
    review = _read_json(source_review_json)
    plan_sha_failures = _verify_sha256s(source_plan_artifact, _read_sha256s(source_plan_sha256s))
    review_sha_failures = _verify_sha256s(source_review_artifact, _read_sha256s(source_review_sha256s))
    plan_root_sha = _sha256(source_plan_sha256s) if source_plan_sha256s.is_file() else None
    review_root_sha = _sha256(source_review_sha256s) if source_review_sha256s.is_file() else None
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    exporter = camp_repo_root / SOURCE_REVIEW_MODULE.PLAN_MODULE.EXPORTER_SCRIPT
    final = review.get("final_decision", {})
    plan_pilot = plan.get("pilot_plan", {})
    timing = plan.get("timing_estimates", {}).get("1024", {})
    preflight = _pilot_preflight(
        candidate_output_root=candidate_output_root,
        exporter=exporter,
        dp_repo=dp_repo,
        python_executable=python_executable,
        checkpoint=checkpoint,
        args_json=args_json,
    )
    checks = [
        _expect("pilot_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_pilot_preflight", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_pilot_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_plan_static_review", v16_text, f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}"),
        _contains("status_records_plan_static_review", status_text, f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}"),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_passed", plan.get("final_decision", {}).get("passed"), True),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _expect("source_review_schema", review.get("schema_version"), SOURCE_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_review_passed", final.get("passed"), True),
        _expect("source_review_authorizes_preflight", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_review_root_sha256", review_root_sha, expected_review_root_sha256),
        _expect("source_review_links_plan_root", review.get("plan_review", {}).get("source_plan_root_sha256"), expected_plan_root_sha256),
        _check("source_review_sha256s_verified", not review_sha_failures, review_sha_failures[:10], []),
        _expect("target_records_1024", plan_pilot.get("selected_target_records"), TARGET_RECORDS),
        _expect("k_is_8", plan_pilot.get("k"), EXPECTED_K),
        _expect("candidate_count_8", plan_pilot.get("candidate_count"), EXPECTED_K),
        _expect("timing_uses_smoke_mean", timing.get("per_record_mean_seconds"), PER_RECORD_MEAN_SECONDS),
        _expect("timing_wall_clock_seconds", timing.get("wall_clock_seconds"), 5447.41376),
        _expect("timing_wall_clock_hours", timing.get("wall_clock_hours"), 1.51317),
        _check("exporter_script_exists", exporter.is_file(), str(exporter), "file"),
        _check("exporter_script_py_compile", _py_compile_ok(exporter), str(exporter), "py_compile_ok"),
        _check("runner_command_constructed", bool(preflight["runner_command_template"]), preflight["runner_command_template"], "nonempty"),
        _check("nuscenes_root_readable", nuscenes_root.is_dir() and os.access(nuscenes_root, os.R_OK), str(nuscenes_root), "readable directory"),
        _check("dp_repo_exists", dp_repo.is_dir(), str(dp_repo), "directory"),
        _check("candidate_output_root_absent", not candidate_output_root.exists(), str(candidate_output_root), "absent"),
    ]
    checks.extend(_contains_all("required_output_schema", preflight["required_output_schema"], _required_output_schema()))
    checks.extend(_contains_all("stop_conditions", preflight["stop_conditions"], _required_stop_conditions()))
    checks.extend(_no_forbidden_work_checks(final))
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "source_artifacts": {
                "plan_artifact": str(source_plan_artifact),
                "plan_root_sha256": plan_root_sha,
                "review_artifact": str(source_review_artifact),
                "review_root_sha256": review_root_sha,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "pilot_preflight": preflight,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "pilot_execution_executed": False,
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


def _pilot_preflight(
    *,
    candidate_output_root: Path,
    exporter: Path,
    dp_repo: Path,
    python_executable: str,
    checkpoint: str,
    args_json: str,
) -> dict[str, Any]:
    report_json = candidate_output_root / "record_reports" / "<record_index>.json"
    report_md = candidate_output_root / "record_reports" / "<record_index>.md"
    output_npz = candidate_output_root / "candidates" / "<record_index>.npz"
    input_npz = candidate_output_root / "inputs" / "<record_index>.npz"
    command = [
        python_executable,
        str(exporter),
        "--dp_repo",
        str(dp_repo),
        "--input_npz",
        str(input_npz),
        "--checkpoint",
        checkpoint,
        "--args_json",
        args_json,
        "--output_npz",
        str(output_npz),
        "--k",
        str(EXPECTED_K),
        "--report_json",
        str(report_json),
        "--report_md",
        str(report_md),
        "--execute",
    ]
    return {
        "target_records": TARGET_RECORDS,
        "k": EXPECTED_K,
        "candidate_count": EXPECTED_K,
        "per_record_mean_seconds": PER_RECORD_MEAN_SECONDS,
        "wall_clock_seconds": 5447.41376,
        "wall_clock_hours": 1.51317,
        "candidate_output_root": str(candidate_output_root),
        "required_output_schema": list(_required_output_schema()),
        "stop_conditions": list(_required_stop_conditions()),
        "runner_command_template": command,
        "runner_command_constructed": True,
        "runner_command_executed": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
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
    preflight = report["pilot_preflight"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Generation Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Target records: `{preflight['target_records']}`",
            f"- K / candidate count: `{preflight['k']} / {preflight['candidate_count']}`",
            f"- Estimated wall-clock seconds: `{preflight['wall_clock_seconds']}`",
            "- Pilot execution in this gate: `False`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_artifacts"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={source['plan_root_sha256']}",
            f"SOURCE_REVIEW_ROOT_SHA256={source['review_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _required_output_schema() -> tuple[str, ...]:
    return ("JSON summary", "JSONL records", "MD", "HEADS", "COMMAND", "stdout", "stderr", "SHA256SUMS")


def _required_stop_conditions() -> tuple[str, ...]:
    return (
        "output root exists",
        "DP HEAD mismatch",
        "records shortfall",
        "any fake/synthetic candidate tensor",
        "any DP/candidate/trajectory mutation",
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_review_{field}_false", final.get(field), False)
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


def _py_compile_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


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
