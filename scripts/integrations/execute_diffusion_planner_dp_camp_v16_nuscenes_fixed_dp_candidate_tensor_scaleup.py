#!/usr/bin/env python3
"""Execute the v16 fixed-DP K=8 candidate tensor scale-up."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.integrations.run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter import (  # noqa: E402
    EXPECTED_K,
    FIXED_DP_HEAD,
)


SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_v1"
SOURCE_PREFLIGHT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight_ready"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_only"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_only"
RUNNING_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_running"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_failed"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.md"
RECORDS_JSONL_NAME = "records.jsonl"
SCENE_DISTRIBUTION_JSON_NAME = "scene_distribution.json"
TIMING_JSON_NAME = "timing.json"
TIMING_MD_NAME = "timing.md"
TARGET_RECORDS = 10000
MINIMUM_DISTINCT_SCENES = 30
MAX_RECORDS_PER_SCENE = 334


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_root", "--output_dir", dest="output_root", type=Path, required=True)
    parser.add_argument("--nuscenes_root", "--metadata_root", dest="nuscenes_root", type=Path, required=True)
    parser.add_argument("--trajdata_cache_dir", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--args_json", type=Path, required=True)
    parser.add_argument("--preflight_artifact", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_preflight_root_sha256", required=True)
    parser.add_argument("--target_records", type=int, default=TARGET_RECORDS)
    parser.add_argument("--minimum_distinct_scenes", type=int, default=MINIMUM_DISTINCT_SCENES)
    parser.add_argument("--max_records_per_scene", type=int, default=MAX_RECORDS_PER_SCENE)
    parser.add_argument("--k", "--candidate_count", dest="k", type=int, default=EXPECTED_K)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--export_python", default=sys.executable)
    parser.add_argument("--split", default="mini_train")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.output_dir = args.output_root
    report = build_report(
        output_root=args.output_root,
        nuscenes_root=args.nuscenes_root,
        trajdata_cache_dir=args.trajdata_cache_dir,
        dp_repo=args.dp_repo,
        checkpoint=args.checkpoint,
        args_json=args.args_json,
        preflight_artifact=args.preflight_artifact,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        target_records=args.target_records,
        minimum_distinct_scenes=args.minimum_distinct_scenes,
        max_records_per_scene=args.max_records_per_scene,
        k=args.k,
        command=sys.argv,
        split=args.split,
    )
    if not args.execute or not report["final_decision"]["passed"]:
        write_outputs(args.output_root, report)
        print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
        return 0 if report["final_decision"]["passed"] else 1
    started = time.time()
    try:
        args.output_root.mkdir(parents=True, exist_ok=False)
        write_outputs(args.output_root, report)
        _run_records(args, report)
        failed = _failed_record_checks(
            report["records"],
            target_records=args.target_records,
            minimum_distinct_scenes=args.minimum_distinct_scenes,
            max_records_per_scene=args.max_records_per_scene,
            k=args.k,
        )
        if failed:
            raise RuntimeError(";".join(failed))
        report["status"] = READY_STATUS
        report["authorized_next_work"] = AUTHORIZED_NEXT_WORK
        report["final_decision"] = _decision(True, READY_STATUS, [], AUTHORIZED_NEXT_WORK)
    except Exception as exc:
        report["status"] = FAILED_STATUS
        report["authorized_next_work"] = AUTHORIZED_CURRENT_WORK
        report["failure"] = f"{type(exc).__name__}: {exc}"
        report["final_decision"] = _decision(False, FAILED_STATUS, [str(exc)], AUTHORIZED_CURRENT_WORK)
    report["wall_clock_seconds"] = round(time.time() - started, 6)
    report["record_count"] = len(report["records"])
    report["scene_distribution"] = _scene_distribution(report["records"])
    report["timing_summary"] = _timing_summary(report["records"], report["wall_clock_seconds"])
    write_outputs(args.output_root, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    output_root: Path,
    nuscenes_root: Path,
    trajdata_cache_dir: Path,
    dp_repo: Path,
    checkpoint: Path,
    args_json: Path,
    preflight_artifact: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_preflight_root_sha256: str,
    target_records: int = TARGET_RECORDS,
    minimum_distinct_scenes: int = MINIMUM_DISTINCT_SCENES,
    max_records_per_scene: int = MAX_RECORDS_PER_SCENE,
    k: int = EXPECTED_K,
    command: list[str] | None = None,
    split: str = "mini_train",
) -> dict[str, Any]:
    preflight = _source_artifact(preflight_artifact)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    audit_text = _read_text(v16_audit_md)
    checks = [
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_scaleup_execution", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_scaleup_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_scaleup_preflight", audit_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _contains("status_records_scaleup_preflight", status_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _check("output_root_absent", not output_root.exists(), str(output_root), "absent"),
        _check("nuscenes_root_readable", nuscenes_root.is_dir(), str(nuscenes_root), "directory"),
        _check("trajdata_cache_dir_available", trajdata_cache_dir.is_dir(), str(trajdata_cache_dir), "directory"),
        _check("dp_repo_exists", dp_repo.is_dir(), str(dp_repo), "directory"),
        _check("checkpoint_exists", checkpoint.is_file(), str(checkpoint), "file"),
        _check("args_json_exists", args_json.is_file(), str(args_json), "file"),
        _expect("target_records_10000", target_records, TARGET_RECORDS),
        _check("minimum_distinct_scenes_at_least_30", minimum_distinct_scenes >= MINIMUM_DISTINCT_SCENES, minimum_distinct_scenes, ">=30"),
        _expect("max_records_per_scene_334", max_records_per_scene, MAX_RECORDS_PER_SCENE),
        _expect("k_is_8", k, EXPECTED_K),
        _expect("preflight_root_sha256", preflight["root_sha256"], expected_preflight_root_sha256),
        _check("preflight_sha256s_verified", preflight["sha256s_verified"], preflight["failed_sha256s"], []),
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    status = RUNNING_STATUS if passed else FAILED_STATUS
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "source_artifacts": {"preflight": preflight},
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "runner": {
                "exporter": "scripts/integrations/run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py",
                "target_records": target_records,
                "minimum_distinct_scenes": minimum_distinct_scenes,
                "max_records_per_scene": max_records_per_scene,
                "split": split,
                "trajdata_split": _trajdata_split(split),
                "k": k,
                "candidate_count": k if k == EXPECTED_K else 0,
                "prefer_more_scenes_over_more_records_per_scene": True,
                "cap_records_per_scene": True,
                "scene_ids_unique": True,
                "sample_ids_unique": True,
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
            "command": command or [],
            "records": [],
            "record_count": 0,
            "scene_distribution": _scene_distribution([]),
            "timing_summary": _timing_summary([], 0.0),
            "checks": checks,
            "final_decision": _decision(passed, status, failed, AUTHORIZED_CURRENT_WORK),
        }
    )


def _run_records(args: argparse.Namespace, report: dict[str, Any]) -> None:
    from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # noqa: PLC0415
        NuscenesDatasetConfig,
        NuscenesTrajdataBridge,
    )
    from scripts.integrations.execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_retry import (  # noqa: E501, PLC0415
        _append_jsonl,
        _batch_meta,
        _run_one,
    )

    bridge = NuscenesTrajdataBridge(
        NuscenesDatasetConfig(
            data_root=str(args.nuscenes_root),
            cache_dir=str(args.trajdata_cache_dir),
            split=_trajdata_split(args.split),
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
    records_path = args.output_root / RECORDS_JSONL_NAME
    records_path.write_text("", encoding="utf-8")
    seen_samples: set[str] = set()
    scene_counts: dict[str, int] = {}
    for batch in bridge.make_dataloader():
        meta = _batch_meta(batch, len(report["records"]))
        scene_id = str(meta["scene_id"])
        sample_id = str(meta["sample_id"])
        if sample_id in seen_samples or not _can_accept_scene(scene_id, scene_counts, args.max_records_per_scene):
            continue
        record = _run_one(args, batch, len(report["records"]))
        record["source_split"] = record["split"]
        record["source_scene_id"] = record["scene_id"]
        record["source_sample_id"] = record["sample_id"]
        record["provenance"] = {
            "camp_head": args.current_camp_head,
            "dp_head": args.current_dp_head,
            "preflight_artifact": str(args.preflight_artifact),
        }
        record["timing"] = {"wall_clock_seconds": record.get("wall_clock_seconds")}
        _append_jsonl(records_path, record)
        report["records"].append(record)
        seen_samples.add(record["sample_id"])
        scene_counts[record["scene_id"]] = scene_counts.get(record["scene_id"], 0) + 1
        if len(report["records"]) % 16 == 0:
            _append_stdout(args.output_root, f"records_done={len(report['records'])}\n")
        if len(report["records"]) >= args.target_records:
            break


def _can_accept_scene(scene_id: str, scene_counts: dict[str, int], max_records_per_scene: int) -> bool:
    return scene_counts.get(scene_id, 0) < max_records_per_scene


def _failed_record_checks(
    records: list[dict[str, Any]],
    *,
    target_records: int,
    minimum_distinct_scenes: int,
    max_records_per_scene: int,
    k: int,
) -> list[str]:
    failed = []
    if len(records) != target_records:
        failed.append(f"records:{len(records)}!={target_records}")
    scene_counts = _scene_counts(records)
    if len(scene_counts) < minimum_distinct_scenes:
        failed.append(f"distinct_scenes:{len(scene_counts)}<{minimum_distinct_scenes}")
    if any(count > max_records_per_scene for count in scene_counts.values()):
        failed.append("scene_cap_exceeded")
    sample_ids = [record.get("sample_id") for record in records]
    if len(sample_ids) != len(set(sample_ids)):
        failed.append("duplicate_sample_ids")
    for record in records:
        idx = record["record_index"]
        if record["DP_HEAD"] != FIXED_DP_HEAD:
            failed.append(f"dp_head:{idx}")
        if record["K"] != k or record["candidate_count"] != k:
            failed.append(f"candidate_count:{idx}")
        if record["candidate_tensor_shape"] != [k, 80, 4]:
            failed.append(f"shape:{idx}")
        if record["candidate_tensor_unchanged_by_camp"] is not True:
            failed.append(f"mutated:{idx}")
        if not (0 <= int(record.get("dp_top1_index", -1)) < k):
            failed.append(f"dp_top1_index:{idx}")
    return failed


def write_outputs(output_root: Path, report: dict[str, Any]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / REPORT_JSON_NAME).write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    (output_root / RECORDS_JSONL_NAME).touch(exist_ok=True)
    (output_root / SCENE_DISTRIBUTION_JSON_NAME).write_text(
        json.dumps(report.get("scene_distribution", _scene_distribution([])), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / TIMING_JSON_NAME).write_text(
        json.dumps(report.get("timing_summary", _timing_summary([], 0.0)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / TIMING_MD_NAME).write_text(_render_timing_markdown(report), encoding="utf-8")
    (output_root / REPORT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_root / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_root / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    (output_root / "stdout.txt").touch(exist_ok=True)
    (output_root / "stderr.txt").write_text(str(report.get("failure", "")), encoding="utf-8")
    (output_root / "run.exit").write_text("0\n" if report["final_decision"]["passed"] else "1\n", encoding="utf-8")
    _write_sha_manifest(output_root)


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
        path = root / rel.strip()
        if not path.is_file() or _sha256(path) != expected:
            failed.append(rel.strip())
    return failed


def _write_sha_manifest(output_root: Path) -> None:
    sha_path = output_root / "SHA256SUMS"
    root_path = output_root / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_root).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  {output_root.name}\n", encoding="utf-8")


def _scene_distribution(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = _scene_counts(records)
    return {
        "distinct_scene_count": len(counts),
        "max_records_per_scene": max(counts.values()) if counts else 0,
        "scene_counts": dict(sorted(counts.items())),
    }


def _scene_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        scene = str(record.get("scene_id", ""))
        counts[scene] = counts.get(scene, 0) + 1
    return counts


def _timing_summary(records: list[dict[str, Any]], wall_clock: float) -> dict[str, Any]:
    values = [float(record["wall_clock_seconds"]) for record in records if "wall_clock_seconds" in record]
    return {
        "wall_clock_seconds": wall_clock,
        "per_record_seconds": {
            "count": len(values),
            "min": min(values) if values else None,
            "mean": round(statistics.fmean(values), 6) if values else None,
            "max": max(values) if values else None,
        },
    }


def _decision(passed: bool, status: str, failed: list[str], next_work: str) -> dict[str, Any]:
    return {
        "passed": passed,
        "status": status,
        "failed_checks": failed,
        "authorized_next_work": next_work,
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


def _trajdata_split(split: str) -> str:
    if split in {"mini_train", "mini_val"}:
        return f"nusc_mini-{split}"
    if split.startswith("nusc_"):
        return split
    return split


def _render_markdown(report: dict[str, Any]) -> str:
    runner = report["runner"]
    decision = report["final_decision"]
    scenes = report.get("scene_distribution", {})
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Records: `{report.get('record_count', 0)}`",
            f"- Distinct scenes: `{scenes.get('distinct_scene_count', 0)}`",
            f"- K / candidate count: `{runner['k']} / {runner['candidate_count']}`",
            f"- Next: `{decision['authorized_next_work']}`",
            "- No training, evaluation, claim, promotion, deployment, DP modification, or candidate tensor mutation.",
            "",
        ]
    )


def _render_timing_markdown(report: dict[str, Any]) -> str:
    timing = report.get("timing_summary", _timing_summary([], 0.0))
    per = timing["per_record_seconds"]
    return "\n".join(
        [
            "# Timing",
            "",
            f"- Wall-clock seconds: `{timing['wall_clock_seconds']}`",
            f"- Per-record count/min/mean/max: `{per['count']}` / `{per['min']}` / `{per['mean']}` / `{per['max']}`",
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
            f"NEXT_WORK_TARGET={report['final_decision']['authorized_next_work']}",
            "",
        ]
    )


def _append_stdout(output_root: Path, text: str) -> None:
    with (output_root / "stdout.txt").open("a", encoding="utf-8") as handle:
        handle.write(text)


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
    return value


if __name__ == "__main__":
    raise SystemExit(main())
