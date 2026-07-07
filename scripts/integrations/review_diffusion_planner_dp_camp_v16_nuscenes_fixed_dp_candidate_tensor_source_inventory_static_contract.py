#!/usr/bin/env python3
"""Static-review the v16 nuScenes fixed-DP candidate tensor source inventory."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_preflight_module():
    path = Path(__file__).resolve().with_name(
        "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory.py"
    )
    spec = importlib.util.spec_from_file_location("v16_nuscenes_source_inventory_preflight", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREFLIGHT_MODULE = _load_preflight_module()
FIXED_DP_HEAD = PREFLIGHT_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review_v1"
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_only"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review.md"
ADAPTER_PLAN_REQUIREMENTS = (
    "route_like_information",
    "traffic_light_signal_context",
    "autoware_lane_tensor_format",
)
DIRECT_FIELDS = (
    "ego_history",
    "ego_state",
    "neighbor_agents",
    "map_lane_context",
    "timestamps_sample_ids",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_preflight_md", type=Path, required=True)
    parser.add_argument("--source_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_preflight_md=args.source_preflight_md,
        source_preflight_sha256s=args.source_preflight_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_preflight_md: Path,
    source_preflight_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_preflight_artifact_dir.resolve()
    source = _read_json(source_preflight_json)
    source_sha256s = _read_sha256s(source_preflight_sha256s)
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_preflight_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_preflight_json_path", source_preflight_json.resolve(), artifact / PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME),
        _expect("source_preflight_md_path", source_preflight_md.resolve(), artifact / PREFLIGHT_MODULE.PREFLIGHT_MD_NAME),
        _expect("source_preflight_sha256s_path", source_preflight_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("source_preflight_schema", source.get("schema_version"), PREFLIGHT_MODULE.SCHEMA_VERSION),
        _expect("source_preflight_passed", source["final_decision"].get("passed"), True),
        _expect("source_authorizes_static_review", source["final_decision"].get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_candidate_generation_not_executed", source["final_decision"].get("candidate_generation_executed"), False),
        _expect("source_training_not_executed", source["final_decision"].get("training_executed"), False),
        _expect("source_paired_eval_not_executed", source["final_decision"].get("paired_evaluation_executed"), False),
        _expect("source_performance_not_claimed", source["final_decision"].get("performance_claimed"), False),
        _expect("source_full36_not_used", source["final_decision"].get("full36_used"), False),
        _expect("source_formal_seed_not_used", source["final_decision"].get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", source["final_decision"].get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", source["final_decision"].get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", source["final_decision"].get("trajectory_modified"), False),
        _expect("source_score_affine", source.get("boundary", {}).get("score"), "score_k(w)=a_k^T w"),
        _expect("source_weights_simplex", source.get("boundary", {}).get("weights"), "nonnegative_simplex"),
        _contains("audit_authorizes_static_review", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_source_ready", v16_text, f"current_v16_status={PREFLIGHT_MODULE.READY_STATUS}"),
        _contains("status_records_source_ready", status_text, f"current_v16_status={PREFLIGHT_MODULE.READY_STATUS}"),
        _expect("smoke_min_records", source.get("smoke_scale", {}).get("min_records"), 100),
        _expect("smoke_max_records", source.get("smoke_scale", {}).get("max_records"), 1000),
    ]
    for name in (
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
        PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME,
        PREFLIGHT_MODULE.PREFLIGHT_MD_NAME,
    ):
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if path.is_file() and name in source_sha256s:
            checks.append(_expect(f"source_artifact_sha_{name}", _sha256(path), source_sha256s[name]))
    for requirement in PREFLIGHT_MODULE.DP_INPUT_REQUIREMENTS:
        checks.append(
            _check(
                f"dp_input_requirement_{requirement}",
                requirement in source.get("dp_input_requirements", []),
                requirement,
                "present",
            )
        )
    direct_fields = source.get("nuscenes_direct_fields", {})
    for field in DIRECT_FIELDS:
        checks.append(_expect(f"direct_field_{field}", direct_fields.get(field, {}).get("direct"), True))
    adapter_gaps = source.get("adapter_gaps", {})
    for gap in ADAPTER_PLAN_REQUIREMENTS:
        checks.append(_expect(f"adapter_gap_{gap}", adapter_gaps.get(gap, {}).get("requires_adapter"), True))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_preflight_artifact": str(artifact),
            "adapter_plan_requirements": ADAPTER_PLAN_REQUIREMENTS,
            "smoke_plan": {"min_records": 100, "max_records": 1000, "training_executed": False},
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
            "# V16 nuScenes Fixed-DP Candidate Tensor Source Inventory Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source preflight artifact: `{report['source_preflight_artifact']}`",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
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
        return {str(key): _stable(value[key]) for key in sorted(value)}
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
