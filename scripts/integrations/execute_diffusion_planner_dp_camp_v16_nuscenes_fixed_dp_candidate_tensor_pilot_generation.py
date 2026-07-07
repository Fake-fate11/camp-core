#!/usr/bin/env python3
"""Execute the v16 fixed-DP K=8 candidate tensor pilot generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.integrations.run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter import (  # noqa: E402
    EXPECTED_K,
    FIXED_DP_HEAD,
)


SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_v1"
SOURCE_PREFLIGHT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_ready"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_only"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_failed"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution.md"
SOURCE_ARTIFACT_KEYS = (
    "smoke_retry",
    "smoke_result_review",
    "pilot_plan",
    "pilot_plan_static_review",
    "pilot_preflight",
)
TARGET_RECORDS = 1024


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--metadata_root", type=Path, required=True)
    parser.add_argument("--trajdata_cache_dir", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--args_json", type=Path, required=True)
    parser.add_argument("--smoke_retry_artifact", type=Path, required=True)
    parser.add_argument("--smoke_result_review_artifact", type=Path, required=True)
    parser.add_argument("--pilot_plan_artifact", type=Path, required=True)
    parser.add_argument("--pilot_plan_static_review_artifact", type=Path, required=True)
    parser.add_argument("--pilot_preflight_artifact", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--target_records", type=int, default=TARGET_RECORDS)
    parser.add_argument("--k", type=int, default=EXPECTED_K)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--export_python", default=sys.executable)
    parser.add_argument("--split", default="mini_val")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_artifacts = {
        "smoke_retry": args.smoke_retry_artifact,
        "smoke_result_review": args.smoke_result_review_artifact,
        "pilot_plan": args.pilot_plan_artifact,
        "pilot_plan_static_review": args.pilot_plan_static_review_artifact,
        "pilot_preflight": args.pilot_preflight_artifact,
    }
    report = build_report(
        output_dir=args.output_dir,
        metadata_root=args.metadata_root,
        trajdata_cache_dir=args.trajdata_cache_dir,
        dp_repo=args.dp_repo,
        checkpoint=args.checkpoint,
        args_json=args.args_json,
        source_artifacts=source_artifacts,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        target_records=args.target_records,
        k=args.k,
        noise_scale=args.noise_scale,
        seed=args.seed,
        device=args.device,
        export_python=args.export_python,
        split=args.split,
    )
    started = time.time()
    records_path = args.output_dir / "records.jsonl"
    if report["final_decision"]["passed"]:
        try:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            _run_records(args, report, records_path)
            failed = _failed_record_checks(report["records"], args)
            if failed:
                raise RuntimeError(";".join(failed))
            report["status"] = READY_STATUS
            report["authorized_next_work"] = AUTHORIZED_NEXT_WORK
            report["final_decision"] = _decision(True, [])
        except Exception as exc:
            report["status"] = FAILED_STATUS
            report["authorized_next_work"] = AUTHORIZED_CURRENT_WORK
            report["failure"] = f"{type(exc).__name__}: {exc}"
            report["final_decision"] = _decision(False, [str(exc)])
    report["wall_clock_seconds"] = round(time.time() - started, 6)
    report["record_count"] = len(report["records"])
    report["records_jsonl"] = str(records_path)
    report["timing_summary"] = _timing_summary(report["records"], report["wall_clock_seconds"])
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    output_dir: Path,
    metadata_root: Path,
    trajdata_cache_dir: Path,
    dp_repo: Path,
    checkpoint: Path,
    args_json: Path,
    source_artifacts: dict[str, Path],
    v16_audit_md: Path,
    current_status_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    target_records: int = TARGET_RECORDS,
    k: int = EXPECTED_K,
    noise_scale: float = 1.0,
    seed: int = 3407,
    device: str = "cuda",
    export_python: str = sys.executable,
    split: str = "mini_val",
) -> dict[str, Any]:
    del noise_scale, seed, device, export_python, split
    artifact_report = _source_artifacts(source_artifacts)
    checks = [
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("k_is_8", k, EXPECTED_K),
        _expect("target_records_1024", target_records, TARGET_RECORDS),
        _check("output_dir_absent", not output_dir.exists(), str(output_dir), "absent"),
        _check("metadata_root_readable", metadata_root.is_dir(), str(metadata_root), "directory"),
        _check("trajdata_cache_dir_available", trajdata_cache_dir.is_dir(), str(trajdata_cache_dir), "directory"),
        _check("dp_repo_exists", dp_repo.is_dir(), str(dp_repo), "directory"),
        _check("checkpoint_exists", checkpoint.is_file(), str(checkpoint), "file"),
        _check("args_json_exists", args_json.is_file(), str(args_json), "file"),
        _contains("audit_authorizes_execution", _read_text(v16_audit_md), f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains(
            "status_authorizes_execution",
            _read_text(current_status_md).split("## Current V15 Status", 1)[0],
            f"next_work_target={AUTHORIZED_CURRENT_WORK}",
        ),
        _contains("audit_records_preflight", _read_text(v16_audit_md), f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _contains(
            "status_records_preflight",
            _read_text(current_status_md).split("## Current V15 Status", 1)[0],
            f"current_v16_status={SOURCE_PREFLIGHT_STATUS}",
        ),
    ]
    checks.extend(
        _check(f"source_{key}_sha256s_verified", value["sha256s_verified"], value["failed_sha256s"], [])
        for key, value in artifact_report.items()
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else FAILED_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": artifact_report,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "runner": {
                "exporter": "scripts/integrations/run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py",
                "target_records": target_records,
                "k": k,
                "candidate_count": k if k == EXPECTED_K else 0,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "promotion_executed": False,
                "deployment_executed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "gpu_reported": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "fake_candidate_tensor_generated": False,
            },
            "records": [],
            "checks": checks,
            "final_decision": _decision(not failed, failed),
        }
    )


def _run_records(args: argparse.Namespace, report: dict[str, Any], records_path: Path) -> None:
    from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # noqa: PLC0415
        NuscenesDatasetConfig,
        NuscenesTrajdataBridge,
    )
    from scripts.integrations.execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_retry import (  # noqa: E501, PLC0415
        _append_jsonl,
        _run_one,
    )

    bridge = NuscenesTrajdataBridge(
        NuscenesDatasetConfig(
            data_root=str(args.metadata_root),
            cache_dir=str(args.trajdata_cache_dir),
            split="nusc_mini-mini_val",
            batch_size=1,
            num_workers=0,
            shuffle=False,
            pin_memory=False,
            use_vector_map=True,
            history_sec=(3.0, 3.0),
            future_sec=(8.0, 8.0),
            max_neighbor_num=32,
            rebuild_cache=False,
            rebuild_maps=False,
        )
    )
    records_path.write_text("", encoding="utf-8")
    for index, batch in enumerate(bridge.make_dataloader()):
        if index >= args.target_records:
            break
        record = _run_one(args, batch, index)
        _append_jsonl(records_path, record)
        report["records"].append(record)
        if (index + 1) % 16 == 0:
            print(f"records_done={index + 1}", flush=True)
    if len(report["records"]) != args.target_records:
        raise RuntimeError(f"records:{len(report['records'])}!={args.target_records}")


def _failed_record_checks(records: list[dict[str, Any]], args: argparse.Namespace) -> list[str]:
    failed = []
    for record in records:
        idx = record["record_index"]
        if record["DP_HEAD"] != FIXED_DP_HEAD:
            failed.append(f"dp_head:{idx}")
        if record["K"] != args.k or record["candidate_count"] != args.k:
            failed.append(f"candidate_count:{idx}")
        if record["candidate_tensor_shape"] != [args.k, 80, 4]:
            failed.append(f"shape:{idx}")
        if record["candidate_tensor_unchanged_by_camp"] is not True:
            failed.append(f"mutated:{idx}")
        if not (0 <= int(record.get("dp_top1_index", -1)) < args.k):
            failed.append(f"dp_top1_index:{idx}")
    return failed


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = output_dir / REPORT_JSON_NAME
    md = output_dir / REPORT_MD_NAME
    summary.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md.write_text(_render_markdown(report), encoding="utf-8")
    _write_sha_manifest(output_dir)


def _source_artifacts(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {key: _source_artifact(paths[key]) for key in SOURCE_ARTIFACT_KEYS}


def _source_artifact(path: Path) -> dict[str, Any]:
    sha256s = path / "SHA256SUMS"
    root = path / "ROOT_SHA256SUMS"
    failed = _verify_sha256s(path, sha256s)
    return {
        "path": str(path),
        "exists": path.is_dir(),
        "sha256s_sha256": _sha256(sha256s) if sha256s.is_file() else None,
        "root_sha256": _root_sha(root),
        "root_sha256s_sha256": _sha256(root) if root.is_file() else None,
        "sha256s_verified": path.is_dir() and sha256s.is_file() and not failed,
        "failed_sha256s": failed,
    }


def _verify_sha256s(root: Path, manifest: Path) -> list[str]:
    if not manifest.is_file():
        return ["missing_SHA256SUMS"]
    failed = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        rel = rel.strip()
        path = root / rel
        if not path.is_file() or _sha256(path) != expected:
            failed.append(rel)
    return failed


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  {output_dir.name}\n", encoding="utf-8")


def _timing_summary(records: list[dict[str, Any]], wall_clock: float) -> dict[str, Any]:
    values = [float(record["wall_clock_seconds"]) for record in records if "wall_clock_seconds" in record]
    return {
        "wall_clock_seconds": wall_clock,
        "per_record_seconds": {
            "count": len(values),
            "min": min(values) if values else None,
            "mean": round(float(np.mean(values)), 6) if values else None,
            "max": max(values) if values else None,
        },
    }


def _decision(passed: bool, failed: list[str]) -> dict[str, Any]:
    return {
        "passed": passed,
        "status": READY_STATUS if passed else FAILED_STATUS,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "gpu_reported": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    timing = report.get("timing_summary", {}).get("per_record_seconds", {})
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Pilot Generation Execution",
            "",
            f"- Status: `{report['status']}`",
            f"- Passed: `{report['final_decision']['passed']}`",
            f"- Records: `{report.get('record_count', 0)}`",
            f"- K: `{report['runner']['k']}`",
            f"- Candidate count: `{report['runner']['candidate_count']}`",
            f"- Wall-clock seconds: `{report.get('wall_clock_seconds')}`",
            f"- Per-record seconds min/mean/max: `{timing.get('min')}` / `{timing.get('mean')}` / `{timing.get('max')}`",
            f"- Next: `{report['final_decision']['authorized_next_work']}`",
            "",
        ]
    )


def _root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    line = path.read_text(encoding="utf-8").splitlines()[0]
    return line.split()[0] if line else None


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
    if isinstance(value, np.generic):
        return value.item()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
