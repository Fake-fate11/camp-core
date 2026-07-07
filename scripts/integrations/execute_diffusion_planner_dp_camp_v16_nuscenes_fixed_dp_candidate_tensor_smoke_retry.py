#!/usr/bin/env python3
"""Execute the v16 fixed-DP K=8 candidate tensor smoke retry."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # noqa: E402
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
)
from scripts.integrations.resolve_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker import (  # noqa: E402
    dp_input_from_agent_batch,
    validate_dp_input,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REMEDIATION_NEXT_WORK,
    EXPECTED_K,
    FIXED_DP_HEAD,
    validate_exported_npz,
)


SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_v1"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_only"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_failed"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--metadata_root", type=Path, required=True)
    parser.add_argument("--trajdata_cache_dir", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--args_json", type=Path, required=True)
    parser.add_argument("--preflight_artifact", type=Path, required=True)
    parser.add_argument("--retry_failure_artifact", type=Path, required=True)
    parser.add_argument("--runner_remediation_artifact", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--target_records", type=int, default=256)
    parser.add_argument("--k", type=int, default=EXPECTED_K)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--export_python", default=sys.executable)
    parser.add_argument("--split", default="mini_val")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.time()
    report: dict[str, Any] = _base_report(args)
    records_path = args.output_dir / "records.jsonl"
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _preflight_or_raise(args, report)
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
    finally:
        report["wall_clock_seconds"] = round(time.time() - started, 6)
        report["record_count"] = len(report["records"])
        report["records_jsonl"] = str(records_path)
        _write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def _run_one(args: argparse.Namespace, batch: Any, index: int) -> dict[str, Any]:
    inputs_dir = args.output_dir / "inputs"
    candidates_dir = args.output_dir / "candidates"
    reports_dir = args.output_dir / "record_reports"
    input_npz = inputs_dir / f"dp_input_{index:06d}.npz"
    output_npz = candidates_dir / f"candidate_tensor_{index:06d}.npz"
    report_json = reports_dir / f"record_{index:06d}.json"
    report_md = reports_dir / f"record_{index:06d}.md"
    data = dp_input_from_agent_batch(batch, metadata_root=args.metadata_root)
    errors = validate_dp_input(data)
    if errors:
        raise ValueError(f"input_schema:{index}:{';'.join(errors)}")
    input_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(input_npz, **data)
    meta = _batch_meta(batch, index)
    command = [
        args.export_python,
        str(ROOT / "scripts" / "integrations" / "run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py"),
        "--dp_repo",
        str(args.dp_repo),
        "--input_npz",
        str(input_npz),
        "--checkpoint",
        str(args.checkpoint),
        "--args_json",
        str(args.args_json),
        "--output_npz",
        str(output_npz),
        "--v16_audit_md",
        str(args.v16_audit_md),
        "--current_status_md",
        str(args.current_status_md),
        "--current_camp_head",
        args.current_camp_head,
        "--current_camp_origin_main",
        args.current_camp_origin_main,
        "--current_dp_head",
        args.current_dp_head,
        "--required_dp_head",
        FIXED_DP_HEAD,
        "--k",
        str(args.k),
        "--noise_scale",
        str(args.noise_scale),
        "--seed",
        str(args.seed + index),
        "--device",
        args.device,
        "--split",
        args.split,
        "--scene_id",
        meta["scene_id"],
        "--sample_id",
        meta["sample_id"],
        "--report_json",
        str(report_json),
        "--report_md",
        str(report_md),
        "--execute",
    ]
    started = time.time()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    elapsed = round(time.time() - started, 6)
    if result.returncode != 0:
        raise RuntimeError(f"exporter:{index}:exit={result.returncode}:{result.stderr[-500:]}")
    record = json.loads(report_json.read_text(encoding="utf-8"))["exported_candidate"]
    validation = validate_exported_npz(output_npz, expected_k=args.k)
    if not validation["passed"]:
        raise RuntimeError(f"export_validation:{index}:{validation['failed_checks']}")
    record.update(
        {
            "record_index": index,
            "scene_ts": meta["scene_ts"],
            "data_idx": meta["data_idx"],
            "input_npz": str(input_npz),
            "candidate_npz": str(output_npz),
            "candidate_npz_sha256": _sha256(output_npz),
            "exporter_command": command,
            "exporter_exit": result.returncode,
            "exporter_stdout": result.stdout,
            "exporter_stderr": result.stderr,
            "wall_clock_seconds": elapsed,
        }
    )
    return _stable(record)


def _preflight_or_raise(args: argparse.Namespace, report: dict[str, Any]) -> None:
    checks = [
        ("camp_head_matches_origin", args.current_camp_head == args.current_camp_origin_main),
        ("dp_head_fixed", args.current_dp_head == FIXED_DP_HEAD),
        ("k_is_8", args.k == EXPECTED_K),
        ("target_records_256", args.target_records == 256),
        ("runner_remediation_next_gate", _remediation_next(args.runner_remediation_artifact) == REMEDIATION_NEXT_WORK),
        ("audit_authorizes_retry", f"next_work_target={AUTHORIZED_CURRENT_WORK}" in _read_text(args.v16_audit_md)),
        ("status_authorizes_retry", f"next_work_target={AUTHORIZED_CURRENT_WORK}" in _read_text(args.current_status_md)),
    ]
    report["checks"] = [{"name": name, "passed": passed} for name, passed in checks]
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise RuntimeError("preflight:" + ",".join(failed))


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
    return failed


def _base_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": FAILED_STATUS,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "source_artifacts": {
            "preflight": str(args.preflight_artifact),
            "retry_failure": str(args.retry_failure_artifact),
            "runner_remediation": str(args.runner_remediation_artifact),
            "runner_remediation_root_sha256": _root_sha(args.runner_remediation_artifact),
        },
        "heads": {
            "camp_head": args.current_camp_head,
            "camp_origin_main": args.current_camp_origin_main,
            "dp_head": args.current_dp_head,
            "required_dp_head": FIXED_DP_HEAD,
        },
        "runner": {
            "exporter": "scripts/integrations/run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py",
            "target_records": args.target_records,
            "k": args.k,
            "noise_scale": args.noise_scale,
            "smoke_retry_scope_only": True,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "records": [],
        "checks": [],
        "final_decision": _decision(False, ["not_started"]),
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
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
    }


def _batch_meta(batch: Any, index: int) -> dict[str, Any]:
    scene_id = _first(getattr(batch, "scene_ids", None), f"scene_unknown_{index:06d}")
    scene_ts = _first(getattr(batch, "scene_ts", None), index)
    data_idx = _first(getattr(batch, "data_idx", None), index)
    return {
        "scene_id": str(scene_id),
        "scene_ts": int(scene_ts),
        "data_idx": int(data_idx),
        "sample_id": f"{scene_id}_{int(scene_ts):06d}_{int(data_idx):06d}",
    }


def _first(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    if hasattr(value, "tolist") and not isinstance(value, list):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value


def _remediation_next(path: Path) -> str | None:
    report = path / "remediation.json"
    if not report.is_file():
        return None
    return json.loads(report.read_text(encoding="utf-8")).get("authorized_next_work")


def _write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    summary = output_dir / "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry.json"
    md = output_dir / "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry.md"
    summary.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md.write_text(_render_markdown(report), encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Smoke Execution Retry",
            "",
            f"- Status: `{report['status']}`",
            f"- Passed: `{report['final_decision']['passed']}`",
            f"- Records: `{report['record_count']}`",
            f"- K: `{report['runner']['k']}`",
            f"- Next: `{report['authorized_next_work']}`",
            f"- Wall-clock seconds: `{report['wall_clock_seconds']}`",
            "",
        ]
    )


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_stable(value), sort_keys=True) + "\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _root_sha(path: Path) -> str | None:
    root = path / "ROOT_SHA256SUMS"
    if not root.is_file():
        return None
    line = root.read_text(encoding="utf-8").splitlines()[0]
    return line.split()[0] if line else None


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
