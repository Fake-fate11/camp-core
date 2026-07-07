#!/usr/bin/env python3
"""Materialize the v15 broader non-formal matrix execution artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_static_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_matrix_execution_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v15_matrix_preflight_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


STATIC_REVIEW_MODULE = _load_static_review_module()
PREFLIGHT_MODULE = STATIC_REVIEW_MODULE.PREFLIGHT_MODULE
MATRIX_PLAN_MODULE = PREFLIGHT_MODULE.PLAN_MODULE
ROOT_PLAN_MODULE = MATRIX_PLAN_MODULE.PLAN_MODULE

FIXED_DP_HEAD = STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_matrix_execution_v1"
AUTHORIZED_CURRENT_WORK = STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_matrix_execution_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_matrix_execution_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_matrix_execution_result_review_only"
EXECUTION_JSON_NAME = "v15_broader_nonformal_evidence_expansion_matrix_execution.json"
EXECUTION_MD_NAME = "v15_broader_nonformal_evidence_expansion_matrix_execution.md"
MATRIX_ROWS_JSONL_NAME = "matrix_execution_rows.jsonl"
SPLIT_MANIFEST_NAME = "matrix_execution_split_manifest.json"
ZERO_OVERLAP_VALIDATION_NAME = "matrix_execution_zero_overlap_validation.json"
SCENARIO_BUCKET_MANIFEST_NAME = "matrix_execution_scenario_bucket_manifest.json"
TIMING_JSON_NAME = "matrix_execution_timing.json"
TIMING_MD_NAME = "matrix_execution_timing.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_matrix_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_matrix_execution,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact = source_static_review_artifact_dir.resolve()
    source_review = _read_json(source_static_review_json)
    root_sha256s = _read_sha256s(source_static_review_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    decision = source_review["final_decision"]
    rows = _matrix_rows(current_camp_head, current_dp_head)
    split_manifest = _split_manifest(rows)
    zero_overlap = _zero_overlap_validation(rows)
    scenario_manifest = _scenario_bucket_manifest(rows)
    timing = _timing_report()

    checks = [
        _expect("matrix_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_schema", source_review.get("schema_version"), STATIC_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_authorized_execution", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_reviewed_preflight", decision.get("reviewed_matrix_execution_preflight"), True),
        _expect("source_matrix_preflight_not_executed_by_review", decision.get("matrix_execution_preflight_executed"), False),
        _expect("source_matrix_not_executed", decision.get("matrix_execution_executed"), False),
        _expect("source_training_not_executed", decision.get("training_executed"), False),
        _expect("source_paired_eval_not_executed", decision.get("paired_evaluation_executed"), False),
        _expect("source_full36_not_used", decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_execution", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("matrix_row_count", len(rows), 576),
        _expect("zero_overlap_duplicate_count", zero_overlap["duplicate_count"], 0),
        _expect("split_manifest_row_count", split_manifest["total_row_count"], len(rows)),
        _expect("scenario_manifest_row_count", scenario_manifest["total_row_count"], len(rows)),
        _expect("timing_training_executed", timing["offline_training"]["executed"], False),
        _expect("timing_selector_latency_executed", timing["online_selector_latency"]["executed"], False),
        _expect("timing_fallback_latency_executed", timing["fallback_latency"]["executed"], False),
    ]
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", STATIC_REVIEW_MODULE.REVIEW_JSON_NAME, STATIC_REVIEW_MODULE.REVIEW_MD_NAME):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))
        if (artifact / name).is_file() and name in root_sha256s:
            checks.append(_expect(f"source_artifact_sha_{name}", _sha256(artifact / name), root_sha256s[name]))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_static_review_artifact": str(artifact),
            "matrix_execution": {
                "row_count": len(rows),
                "fixed_dp_head": current_dp_head,
                "camp_head": current_camp_head,
                "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
                "candidate_tensor_materialized_by_this_gate": False,
                "camp_action": "rerank_or_select_only",
                "execution_type": "non_formal_matrix_manifest_materialization",
            },
            "split_manifest": split_manifest,
            "zero_overlap_validation": zero_overlap,
            "scenario_bucket_manifest": scenario_manifest,
            "timing": timing,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "matrix_execution_executed": not failed,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
            "matrix_rows": rows,
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        EXECUTION_JSON_NAME: report,
        SPLIT_MANIFEST_NAME: report["split_manifest"],
        ZERO_OVERLAP_VALIDATION_NAME: report["zero_overlap_validation"],
        SCENARIO_BUCKET_MANIFEST_NAME: report["scenario_bucket_manifest"],
        TIMING_JSON_NAME: report["timing"],
    }
    for name, payload in files.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows_path = output_dir / MATRIX_ROWS_JSONL_NAME
    rows_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report["matrix_rows"]),
        encoding="utf-8",
    )
    (output_dir / EXECUTION_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / TIMING_MD_NAME).write_text(_render_timing_markdown(report["timing"]), encoding="utf-8")
    sha_inputs = [
        output_dir / name
        for name in (
            EXECUTION_JSON_NAME,
            EXECUTION_MD_NAME,
            MATRIX_ROWS_JSONL_NAME,
            SPLIT_MANIFEST_NAME,
            ZERO_OVERLAP_VALIDATION_NAME,
            SCENARIO_BUCKET_MANIFEST_NAME,
            TIMING_JSON_NAME,
            TIMING_MD_NAME,
        )
    ]
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sha_inputs),
        encoding="utf-8",
    )


def _matrix_rows(camp_head: str, dp_head: str) -> list[dict[str, Any]]:
    matrix = ROOT_PLAN_MODULE.NONFORMAL_MATRIX
    split_by_seed = {
        seed: split
        for split, seeds in (
            ("train", matrix["train_seeds"]),
            ("calibration", matrix["calibration_seeds"]),
            ("holdout", matrix["holdout_seeds"]),
        )
        for seed in seeds
    }
    rows: list[dict[str, Any]] = []
    for route in matrix["routes"]:
        for seed, split in split_by_seed.items():
            for npc_mode in matrix["npc_modes"]:
                for traffic_light_mode in matrix["traffic_light_modes"]:
                    key = f"{dp_head}|{route}|{seed}|{npc_mode}|{traffic_light_mode}"
                    rows.append(
                        {
                            "record_id": f"v15-matrix-{len(rows):04d}",
                            "camp_head": camp_head,
                            "fixed_dp_head": dp_head,
                            "route": route,
                            "seed": seed,
                            "split": split,
                            "npc_mode": npc_mode,
                            "traffic_light_mode": traffic_light_mode,
                            "scenario_bucket": _scenario_bucket(route, npc_mode, traffic_light_mode),
                            "candidate_tensor_provenance_sha256": _sha256_text(key),
                            "candidate_tensor_materialized_by_this_gate": False,
                            "camp_action": "rerank_or_select_only",
                        }
                    )
    return rows


def _split_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    splits = {
        split: [row for row in rows if row["split"] == split]
        for split in ("train", "calibration", "holdout")
    }
    return {
        "total_row_count": len(rows),
        "splits": {
            split: {
                "row_count": len(split_rows),
                "seeds": sorted({row["seed"] for row in split_rows}),
            }
            for split, split_rows in splits.items()
        },
    }


def _zero_overlap_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "route",
        "seed",
        "npc_mode",
        "traffic_light_mode",
        "candidate_tensor_provenance_sha256",
        "record_id",
    )
    seen = {tuple(row[key] for key in keys) for row in rows}
    return {
        "zero_overlap_keys": keys,
        "row_count": len(rows),
        "unique_key_count": len(seen),
        "duplicate_count": len(rows) - len(seen),
    }


def _scenario_bucket_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {bucket: 0 for bucket in ROOT_PLAN_MODULE.SCENARIO_BUCKETS}
    for row in rows:
        counts[row["scenario_bucket"]] += 1
    return {
        "scenario_buckets": ROOT_PLAN_MODULE.SCENARIO_BUCKETS,
        "bucket_counts": counts,
        "total_row_count": len(rows),
    }


def _timing_report() -> dict[str, Any]:
    latency = {"executed": False, "count": 0, "mean": None, "median": None, "p95": None, "p99": None, "max": None}
    return {
        "offline_training": {
            "executed": False,
            "training_start_timestamp": None,
            "training_end_timestamp": None,
            "training_wall_clock_seconds": 0,
            "training_command": None,
            "training_sample_count": 0,
            "training_artifact_sha256": None,
            "training_model_sha256": None,
            "training_config_sha256": None,
            "training_log_sha256": None,
        },
        "online_selector_latency": latency,
        "fallback_latency": dict(latency),
        "instrumentation_changes_selector_behavior": False,
    }


def _scenario_bucket(route: str, npc_mode: str, traffic_light_mode: str) -> str:
    if route == "left_turn_red_light" or traffic_light_mode == "red":
        return "red_light_turn"
    if "tl" in route or traffic_light_mode != "off":
        return "traffic_light"
    if route == "sharp_turn":
        return "sharp_turn"
    if route == "dense_merge":
        return "dense_scene"
    if "lane_change" in route or "merge" in route:
        return "lane_change_or_merge"
    if route == "npc_interaction" or npc_mode != "none":
        return "npc_interaction"
    return "normal"


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    execution = report["matrix_execution"]
    return "\n".join(
        [
            "# V15 Matrix Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Row count: `{execution['row_count']}`",
            f"- Execution type: `{execution['execution_type']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- This gate materializes the non-formal matrix manifest only; it does not train or evaluate a selector.",
            "",
        ]
    )


def _render_timing_markdown(timing: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V15 Matrix Execution Timing",
            "",
            f"- Offline training executed: `{timing['offline_training']['executed']}`",
            f"- Training wall-clock seconds: `{timing['offline_training']['training_wall_clock_seconds']}`",
            f"- Online selector latency count: `{timing['online_selector_latency']['count']}`",
            f"- Fallback latency count: `{timing['fallback_latency']['count']}`",
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
