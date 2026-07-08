#!/usr/bin/env python3
"""Preflight the v16 nuScenes fixed-DP candidate tensor scale-up."""

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
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight_v1"
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_only"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight.md"
EXPORTER_SCRIPT = "scripts/integrations/run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py"
TARGET_RECORDS = 10000
MINIMUM_DISTINCT_SCENES = 30
EXPECTED_K = 8
PER_RECORD_SECONDS = 5.31974
ESTIMATED_WALL_CLOCK_HOURS = 14.8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_review_json", type=Path, required=True)
    parser.add_argument("--source_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_review_root_sha256s", type=Path, required=True)
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
    parser.add_argument("--exporter_script", default=EXPORTER_SCRIPT)
    parser.add_argument("--runner_script", default=EXPORTER_SCRIPT)
    parser.add_argument("--checkpoint", default="<fixed_dp_checkpoint>")
    parser.add_argument("--args_json", default="<fixed_dp_args_json>")
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        source_review_artifact_dir=args.source_review_artifact_dir,
        source_review_json=args.source_review_json,
        source_review_sha256s=args.source_review_sha256s,
        source_review_root_sha256s=args.source_review_root_sha256s,
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
        exporter_script=args.exporter_script,
        runner_script=args.runner_script,
        checkpoint=args.checkpoint,
        args_json=args.args_json,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight,
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
    source_plan_root_sha256s: Path,
    source_review_artifact_dir: Path,
    source_review_json: Path,
    source_review_sha256s: Path,
    source_review_root_sha256s: Path,
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
    exporter_script: str | Path = EXPORTER_SCRIPT,
    runner_script: str | Path = EXPORTER_SCRIPT,
    checkpoint: str = "<fixed_dp_checkpoint>",
    args_json: str = "<fixed_dp_args_json>",
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    source_plan_artifact = source_plan_artifact_dir.resolve()
    source_review_artifact = source_review_artifact_dir.resolve()
    plan = _read_json(source_plan_json)
    review = _read_json(source_review_json)
    plan_sha_entries, plan_sha_failures = _verify_sha256s(source_plan_artifact, source_plan_sha256s)
    review_sha_entries, review_sha_failures = _verify_sha256s(source_review_artifact, source_review_sha256s)
    plan_root_sha = _read_root_sha(source_plan_root_sha256s)
    review_root_sha = _read_root_sha(source_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    exporter = _resolve_script(camp_repo_root, exporter_script)
    runner = _resolve_script(camp_repo_root, runner_script)
    plan_final = plan.get("final_decision", {})
    review_final = review.get("final_decision", {})
    scaleup_plan = plan.get("scaleup_plan", {})
    selected = scaleup_plan.get("selected_stage", {})
    review_static = review.get("scaleup_plan_static_review", {})
    stop_conditions = scaleup_plan.get("stop_conditions", [])
    exporter_py_compile = _py_compile_ok(exporter)
    runner_py_compile = _py_compile_ok(runner)
    preflight = _scaleup_preflight(
        candidate_output_root=candidate_output_root,
        exporter=exporter,
        runner=runner,
        dp_repo=dp_repo,
        nuscenes_root=nuscenes_root,
        python_executable=python_executable,
        checkpoint=checkpoint,
        args_json=args_json,
        selected=selected,
        stop_conditions=stop_conditions,
        exporter_py_compile=exporter_py_compile,
        runner_py_compile=runner_py_compile,
    )
    checks = [
        _expect("scaleup_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_scaleup_preflight", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_scaleup_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_scaleup_static_review", audit_text, f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}"),
        _contains("status_records_scaleup_static_review", status_text, f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}"),
        _check("source_plan_artifact_exists", source_plan_artifact.is_dir(), str(source_plan_artifact), "directory"),
        _check("source_review_artifact_exists", source_review_artifact.is_dir(), str(source_review_artifact), "directory"),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", plan_final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", plan_final.get("authorized_next_work"), SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_complete", plan_sha_entries >= 7, plan_sha_entries, ">=7"),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _expect("source_review_schema", review.get("schema_version"), SOURCE_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_review_status", review.get("status"), SOURCE_REVIEW_MODULE.READY_STATUS),
        _expect("source_review_passed", review_final.get("passed"), True),
        _expect("source_review_authorizes_preflight", review_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_review_root_sha256", review_root_sha, expected_review_root_sha256),
        _expect("source_review_links_plan_root", review_static.get("source_plan_root_sha256"), expected_plan_root_sha256),
        _check("source_review_sha256s_complete", review_sha_entries >= 7, review_sha_entries, ">=7"),
        _check("source_review_sha256s_verified", not review_sha_failures, review_sha_failures[:10], []),
        _expect("target_records_10000", selected.get("target_records"), TARGET_RECORDS),
        _check("minimum_distinct_scenes_at_least_30", selected.get("minimum_distinct_scenes", 0) >= MINIMUM_DISTINCT_SCENES, selected.get("minimum_distinct_scenes"), ">=30"),
        _expect("k_is_8", selected.get("k"), EXPECTED_K),
        _expect("candidate_count_8", selected.get("candidate_count"), EXPECTED_K),
        _check("per_scene_record_cap_configured", isinstance(selected.get("max_records_per_scene"), int), selected.get("max_records_per_scene"), "int"),
        _expect("per_record_timing_seconds", scaleup_plan.get("per_record_timing_seconds"), PER_RECORD_SECONDS),
        _expect("estimated_wall_clock_hours", selected.get("estimated_wall_clock_hours"), ESTIMATED_WALL_CLOCK_HOURS),
        _check("exporter_script_exists", exporter.is_file(), str(exporter), "file"),
        _expect("exporter_script_py_compile", exporter_py_compile, True),
        _check("runner_script_exists", runner.is_file(), str(runner), "file"),
        _expect("runner_script_py_compile", runner_py_compile, True),
        _check("dp_repo_exists", dp_repo.is_dir(), str(dp_repo), "directory"),
        _check("nuscenes_root_readable", nuscenes_root.is_dir() and os.access(nuscenes_root, os.R_OK), str(nuscenes_root), "readable directory"),
        _check("candidate_output_root_absent", not candidate_output_root.exists(), str(candidate_output_root), "absent"),
        _check("source_selection_command_constructed", bool(preflight["source_selection_command_template"]), preflight["source_selection_command_template"], "nonempty"),
        _expect("source_selection_command_not_executed", preflight["source_selection_command_executed"], False),
    ]
    checks.extend(_contains_all("stop_condition", preflight["stop_conditions"], _required_stop_conditions()))
    checks.extend(_no_forbidden_work_checks(plan_final, "source_plan"))
    checks.extend(_no_forbidden_work_checks(review_final, "source_review"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
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
            "scaleup_preflight": preflight,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "preflight_only": True,
                "scale_up_executed": False,
                "candidate_generation_executed": False,
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


def _scaleup_preflight(
    *,
    candidate_output_root: Path,
    exporter: Path,
    runner: Path,
    dp_repo: Path,
    nuscenes_root: Path,
    python_executable: str,
    checkpoint: str,
    args_json: str,
    selected: dict[str, Any],
    stop_conditions: list[str],
    exporter_py_compile: bool,
    runner_py_compile: bool,
) -> dict[str, Any]:
    target_records = selected.get("target_records")
    minimum_scenes = selected.get("minimum_distinct_scenes")
    max_records_per_scene = selected.get("max_records_per_scene")
    command = [
        python_executable,
        str(runner),
        "--dp_repo",
        str(dp_repo),
        "--nuscenes_root",
        str(nuscenes_root),
        "--output_root",
        str(candidate_output_root),
        "--target_records",
        str(target_records),
        "--minimum_distinct_scenes",
        str(minimum_scenes),
        "--max_records_per_scene",
        str(max_records_per_scene),
        "--k",
        str(EXPECTED_K),
        "--candidate_count",
        str(EXPECTED_K),
        "--checkpoint",
        checkpoint,
        "--args_json",
        args_json,
        "--execute",
    ]
    return {
        "target_records": target_records,
        "minimum_distinct_scenes": minimum_scenes,
        "k": selected.get("k"),
        "candidate_count": selected.get("candidate_count"),
        "max_records_per_scene": max_records_per_scene,
        "per_record_timing_seconds": PER_RECORD_SECONDS,
        "estimated_wall_clock_hours": selected.get("estimated_wall_clock_hours"),
        "candidate_output_root": str(candidate_output_root),
        "exporter_script": str(exporter),
        "runner_script": str(runner),
        "exporter_py_compile": exporter_py_compile,
        "runner_py_compile": runner_py_compile,
        "dp_repo": str(dp_repo),
        "nuscenes_root": str(nuscenes_root),
        "stop_conditions": stop_conditions,
        "source_selection_command_template": command,
        "source_selection_command_constructed": True,
        "source_selection_command_executed": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / PREFLIGHT_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PREFLIGHT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _required_stop_conditions() -> tuple[str, ...]:
    return (
        "output root exists",
        "DP HEAD mismatch",
        "records shortfall",
        "scene count shortfall",
        "fake/synthetic candidate tensor",
        "runtime/cost too high",
    )


def _no_forbidden_work_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
            "scale_up_executed",
            "candidate_generation_executed",
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
        )
    ]


def _resolve_script(root: Path, script: str | Path) -> Path:
    path = Path(script)
    return path if path.is_absolute() else root / path


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


def _py_compile_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


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
    preflight = report["scaleup_preflight"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Target: `{preflight['target_records']}` records, minimum `{preflight['minimum_distinct_scenes']}` scenes.",
            f"- K / candidate count: `{preflight['k']} / {preflight['candidate_count']}`",
            f"- Estimated wall-clock hours: `{preflight['estimated_wall_clock_hours']}`",
            f"- Candidate output root: `{preflight['candidate_output_root']}`",
            "- Source selection command constructed but not executed.",
            "- No scale-up execution, corpus generation, training, evaluation, claim, promotion, or deployment.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_artifacts"]
    preflight = report["scaleup_preflight"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={source['plan_root_sha256']}",
            f"SOURCE_REVIEW_ROOT_SHA256={source['review_root_sha256']}",
            f"CANDIDATE_OUTPUT_ROOT={preflight['candidate_output_root']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _contains_all(name: str, actual: list[str], required: tuple[str, ...]) -> list[dict[str, Any]]:
    return [_check(f"{name}_{item}", item in actual, "present" if item in actual else "missing", item) for item in required]


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
