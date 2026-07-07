#!/usr/bin/env python3
"""Preflight v16 nuScenes fixed-DP candidate tensor source inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight_v1"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review_only"
REQUIRED_V15_STATUS = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_recorded"
REQUIRED_V15_NEXT_WORK = "no_further_action_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_complete"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight.md"

ARTIFACT_LAYOUT = (
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    PREFLIGHT_JSON_NAME,
    PREFLIGHT_MD_NAME,
    "SHA256SUMS",
)
TIMING_FIELDS = (
    "DP candidate generation latency",
    "adapter conversion latency",
    "CAMP training wall-clock, later gate only",
    "CAMP online selector latency, later gate only",
)
DP_INPUT_REQUIREMENTS = (
    "ego_history",
    "ego_current_state",
    "neighbor_agents",
    "lane_map_context",
    "route_like_information",
    "traffic_light_signal_context",
    "timestamps_sample_ids",
    "candidate_tensor_output_shape_hash",
)
NO_GO_CONDITIONS = (
    "dp_head_drift",
    "dp_code_config_weight_modification",
    "missing_nuscenes_root",
    "missing_required_dp_input_without_adapter_boundary",
    "candidate_tensor_mutation",
    "train_eval_overlap",
    "full36_or_formal_seed_usage",
    "performance_or_safety_claim_before_holdout_actual_evaluation",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--nuscenes_root", type=Path, required=True)
    parser.add_argument("--camp_repo_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        v15_audit_md=args.v15_audit_md,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        nuscenes_root=args.nuscenes_root,
        camp_repo_root=args.camp_repo_root,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    v15_audit_md: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    nuscenes_root: Path,
    camp_repo_root: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    v15_text = _read_text(v15_audit_md)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    inventory = _nuscenes_inventory(nuscenes_root)
    bridge = _camp_bridge(camp_repo_root)
    checks = [
        _expect("source_inventory_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("v15_audit_exists", v15_audit_md.is_file(), str(v15_audit_md), "file"),
        _check("v14_audit_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check("current_status_exists", current_status_md.is_file(), str(current_status_md), "file"),
        _expect("v15_audit_closeout_status", _latest_value(v15_text, "current_v15_status"), REQUIRED_V15_STATUS),
        _expect("v15_audit_closeout_complete", _next_work_after_latest_status(v15_text, "current_v15_status"), REQUIRED_V15_NEXT_WORK),
        _expect("status_doc_closeout_status", _latest_value(status_text, "current_v15_status"), REQUIRED_V15_STATUS),
        _expect("status_doc_closeout_complete", _next_work_after_latest_status(status_text, "current_v15_status"), REQUIRED_V15_NEXT_WORK),
        _contains("v14_sealed_evidence", v14_text + status_text, "v14"),
        _expect("nuscenes_root_exists", inventory["root_exists"], True),
        _expect("camp_nuscenes_bridge_available", bridge["nuscenes_trajdata_bridge"]["available"], True),
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": required_dp_head,
            },
            "nuscenes_inventory": inventory,
            "camp_bridge": bridge,
            "dp_input_requirements": DP_INPUT_REQUIREMENTS,
            "nuscenes_direct_fields": _nuscenes_direct_fields(),
            "adapter_gaps": _adapter_gaps(),
            "split_rules": {
                "scene_sample_token_zero_overlap": True,
                "candidate_tensor_sha_zero_overlap": True,
                "record_id_zero_overlap": True,
                "route_map_location_zero_overlap_where_possible": True,
            },
            "smoke_scale": {
                "inventory_only_first": True,
                "min_records": 100,
                "max_records": 1000,
                "broader_10k_32k_100k_allowed_after_smoke": True,
            },
            "artifact_layout": ARTIFACT_LAYOUT,
            "timing_fields": TIMING_FIELDS,
            "no_go_conditions": NO_GO_CONDITIONS,
            "boundary": {
                "dp_training_or_modification": False,
                "camp_action": "rerank_or_select_fixed_dp_candidates_only",
                "trajectory_generation_repair_rewrite_blend": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "performance_or_safety_claim": False,
                "score": "score_k(w)=a_k^T w",
                "weights": "nonnegative_simplex",
            },
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "inventory_executed": True,
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


def _nuscenes_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    entries = _relative_entries(root, max_depth=2)
    return {
        "root": str(root),
        "root_exists": root.is_dir(),
        "split_or_archive_entries": [x for x in entries if x.startswith(("Fulldatasetv1.0", "nuImages", "nuScenes-lidarseg"))],
        "map_entries": [x for x in entries if x.startswith("Mapexpansion")],
        "can_bus_entries": [x for x in entries if x.startswith("CANbusexpansion")],
        "top_level_entries": [p.name for p in root.iterdir()] if root.is_dir() else [],
    }


def _relative_entries(root: Path, *, max_depth: int) -> list[str]:
    if not root.is_dir():
        return []
    rows = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if len(rel.parts) <= max_depth:
            rows.append(rel.as_posix())
    return sorted(rows)


def _camp_bridge(root: Path) -> dict[str, Any]:
    bridge = root / "camp_core" / "camp_core" / "data_interfaces" / "nuscenes_trajdata_bridge.py"
    batch = root / "adaptive-prediction" / "unified-av-data-loader" / "src" / "trajdata" / "data_structures" / "batch.py"
    cache_dataset = root / "scripts" / "data_gen" / "cache_dataset.py"
    return {
        "nuscenes_trajdata_bridge": {
            "available": bridge.is_file(),
            "path": str(bridge),
            "exports": ("NuscenesDatasetConfig", "NuscenesTrajdataBridge", "extract_driver_context"),
        },
        "trajdata_agent_batch": {"available": batch.is_file(), "path": str(batch)},
        "cache_dataset_entrypoint": {"available": cache_dataset.is_file(), "path": str(cache_dataset)},
    }


def _nuscenes_direct_fields() -> dict[str, dict[str, Any]]:
    return {
        "ego_history": {"direct": True, "source": "trajdata AgentBatch.agent_hist"},
        "ego_state": {"direct": True, "source": "trajdata AgentBatch.curr_agent_state"},
        "neighbor_agents": {"direct": True, "source": "trajdata neighbor histories/current states"},
        "map_lane_context": {"direct": True, "source": "map_names/vector_maps, then adapter to DP lane tensors"},
        "route_like_information": {"direct": False, "source": "must derive from map/lane context"},
        "traffic_light_signal_context": {"direct": False, "source": "nuScenes needs explicit signal approximation/boundary"},
        "timestamps_sample_ids": {"direct": True, "source": "scene/sample/token/data_idx metadata"},
    }


def _adapter_gaps() -> dict[str, dict[str, Any]]:
    return {
        "route_like_information": {
            "requires_adapter": True,
            "approximation": "derive route lanes from local lane graph near ego when no mission route exists",
            "affects_claim_boundary": True,
        },
        "traffic_light_signal_context": {
            "requires_adapter": True,
            "approximation": "record unavailable/approximated signal state; no safety claim until audited",
            "affects_claim_boundary": True,
        },
        "autoware_lane_tensor_format": {
            "requires_adapter": True,
            "approximation": "convert trajdata vector map lanes to DP lane/route lane tensor shapes",
            "affects_claim_boundary": True,
        },
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    d = report["final_decision"]
    lines = [
        "# V16 nuScenes Fixed-DP Candidate Tensor Source Inventory Preflight",
        "",
        f"- Status: `{d['status']}`",
        f"- Passed: `{d['passed']}`",
        f"- Authorized next work: `{d['authorized_next_work']}`",
        f"- nuScenes root exists: `{report['nuscenes_inventory']['root_exists']}`",
        f"- CAMP bridge available: `{report['camp_bridge']['nuscenes_trajdata_bridge']['available']}`",
        "- Boundary: fixed DP candidate generator; CAMP rerank/select only; no claim.",
        "",
        "## Adapter Gaps",
        "",
    ]
    lines.extend(f"- `{name}`: {gap['approximation']}" for name, gap in report["adapter_gaps"].items())
    lines.append("")
    return "\n".join(lines)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _next_work_after_latest_status(text: str, status_key: str) -> str | None:
    token = f"{status_key}="
    start = text.rfind(token)
    if start < 0:
        return None
    section = text[start:]
    target = "next_work_target="
    if target not in section:
        return None
    return section.split(target, maxsplit=1)[1].splitlines()[0]


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
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
