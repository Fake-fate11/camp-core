#!/usr/bin/env python3
"""Validate zero-overlap registries for v14 fixed-DP public simulator outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CURRENT_STATUS = "public_simulator_fixed_dp_candidate_generation_execution_passed"
AUTHORIZED_CURRENT_WORK = "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation"
AUTHORIZED_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_data_preparation_preflight"
READY_STATUS = "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed"
REJECT_STATUS = "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_rejected"
EXPECTED_LOG_COUNT = 32
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_RECORDS = 3200
EXPECTED_NUM_CANDIDATES = 8
FORMAL_SEEDS = {11, 12, 13}
REGISTRY_SCHEMA_VERSION = "dp_camp_v14_public_simulator_zero_overlap_registry_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_output_root", type=Path, required=True)
    parser.add_argument("--execution_report_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--reference_candidate_tensor_hash_registry_json", type=Path, required=True)
    parser.add_argument("--reference_path_signature_registry_json", type=Path, required=True)
    parser.add_argument("--reference_record_identity_registry_json", type=Path, required=True)
    parser.add_argument("--reference_split_manifest_root_registry_json", type=Path, required=True)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_output_root=args.execution_output_root,
        execution_report_json=args.execution_report_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        reference_candidate_tensor_hash_registry_json=args.reference_candidate_tensor_hash_registry_json,
        reference_path_signature_registry_json=args.reference_path_signature_registry_json,
        reference_record_identity_registry_json=args.reference_record_identity_registry_json,
        reference_split_manifest_root_registry_json=args.reference_split_manifest_root_registry_json,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_output_root: Path,
    execution_report_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    reference_candidate_tensor_hash_registry_json: Path,
    reference_path_signature_registry_json: Path,
    reference_record_identity_registry_json: Path,
    reference_split_manifest_root_registry_json: Path,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    materialized = materialize_registries(execution_output_root)
    references = {
        "candidate_tensor_hashes": _load_registry_values(reference_candidate_tensor_hash_registry_json),
        "path_signatures": _load_registry_values(reference_path_signature_registry_json),
        "record_identity_hashes": _load_registry_values(reference_record_identity_registry_json),
        "split_manifest_roots": _load_registry_values(reference_split_manifest_root_registry_json),
    }
    intersections = {
        "candidate_tensor_hash_intersection_count": len(
            materialized["sets"]["candidate_tensor_hashes"] & references["candidate_tensor_hashes"]
        ),
        "path_signature_intersection_count": len(
            materialized["sets"]["path_signatures"] & references["path_signatures"]
        ),
        "record_identity_intersection_count": len(
            materialized["sets"]["record_identity_hashes"] & references["record_identity_hashes"]
        ),
        "split_manifest_root_intersection_count": len(
            materialized["sets"]["split_manifest_roots"] & references["split_manifest_roots"]
        ),
    }
    checks = _checks(
        execution_output_root=execution_output_root,
        execution_report_json=execution_report_json,
        execution_report=_read_json(execution_report_json),
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        v14_text=_read_text(v14_audit_md),
        status_text=_read_text(current_status_md),
        materialized=materialized,
        references=references,
        intersections=intersections,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        reference_files={
            "candidate_tensor_hash_registry_json": reference_candidate_tensor_hash_registry_json,
            "path_signature_registry_json": reference_path_signature_registry_json,
            "record_identity_registry_json": reference_record_identity_registry_json,
            "split_manifest_root_registry_json": reference_split_manifest_root_registry_json,
        },
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": "dp_camp_v14_public_simulator_zero_overlap_validation_v1",
        "analysis": {
            "zero_overlap_validation_only": True,
            "fixed_dp_candidate_generation_executed_by_source": True,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "training_execution": False,
            "promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "execution_output_root": str(execution_output_root),
            "execution_report_json": str(execution_report_json),
            "output_dir": str(output_dir),
            "reference_registry_files": {
                key: str(path) for key, path in {
                    "candidate_tensor_hashes": reference_candidate_tensor_hash_registry_json,
                    "path_signatures": reference_path_signature_registry_json,
                    "record_identity_hashes": reference_record_identity_registry_json,
                    "split_manifest_roots": reference_split_manifest_root_registry_json,
                }.items()
            },
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "registry_summary": materialized["summary"],
        "reference_registry_counts": {key: len(value) for key, value in references.items()},
        "zero_intersection_counts": intersections,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
        "registries": {
            "candidate_tensor_hashes": sorted(materialized["sets"]["candidate_tensor_hashes"]),
            "path_signatures": sorted(materialized["sets"]["path_signatures"]),
            "record_identity_hashes": sorted(materialized["sets"]["record_identity_hashes"]),
            "split_manifest_roots": sorted(materialized["sets"]["split_manifest_roots"]),
            "selection_logs": materialized["selection_logs"],
        },
    }


def materialize_registries(root: Path) -> dict[str, Any]:
    selection_logs = sorted(root.rglob("camp_selection_log.json"))
    candidate_hashes: list[str] = []
    path_signatures: list[str] = []
    record_identity_hashes: list[str] = []
    split_manifest_roots: list[str] = []
    records = 0
    wrong_step_logs: list[str] = []
    formal_seeds: set[int] = set()
    tensor_hash_mismatches = 0
    executed_non_top1 = 0
    default_off_missing = 0
    provenance_missing = 0
    closed_loop_collect_count = 0
    forbidden_runtime_flags = 0
    for log_path in selection_logs:
        validation = _read_json(log_path.parent / "camp_validation_summary.json")
        benchmark = _dict(validation.get("benchmark"))
        seed = _as_int(benchmark.get("seed"))
        if seed in FORMAL_SEEDS:
            formal_seeds.add(seed)
        path_signature = _hash_json(
            {
                "schema": "dp_camp_v14_public_simulator_path_signature_v1",
                "relative_log": str(log_path.relative_to(root)),
                "route": benchmark.get("route"),
                "map_path": benchmark.get("map_path"),
                "seed": seed,
                "traffic_lights": benchmark.get("traffic_lights"),
                "steps": benchmark.get("steps"),
                "num_candidates": EXPECTED_NUM_CANDIDATES,
            }
        )
        path_signatures.append(path_signature)
        entries = _read_json_list(log_path)
        if len(entries) != EXPECTED_STEPS_PER_LOG:
            wrong_step_logs.append(str(log_path))
        split_manifest_root = _hash_json(
            {
                "schema": "dp_camp_v14_public_simulator_split_manifest_root_v1",
                "execution_output_root": str(root),
                "route": benchmark.get("route"),
                "map_path": benchmark.get("map_path"),
            }
        )
        split_manifest_roots.append(split_manifest_root)
        for record in entries:
            records += 1
            selector = _dict(record.get("default_off_shadow_selector"))
            provenance = _dict(record.get("camp_candidate_tensor_provenance"))
            selector_hash = _dict(selector.get("candidate_tensor_hash")).get("sha256")
            pre_hash = _dict(provenance.get("pre_camp_scoring_tensor")).get("sha256")
            post_hash = _dict(provenance.get("post_camp_selector_tensor")).get("sha256")
            if not selector_hash:
                default_off_missing += 1
                continue
            if not pre_hash or not post_hash:
                provenance_missing += 1
            elif selector_hash != pre_hash or selector_hash != post_hash:
                tensor_hash_mismatches += 1
            candidate_hashes.append(str(selector_hash))
            if record.get("selected_index") != 0 or record.get("executed_index") != 0:
                executed_non_top1 += 1
            if record.get("candidate_closed_loop_outcomes") not in (None, [], {}):
                closed_loop_collect_count += 1
            if _dict(record.get("candidate_generation_contract")).get("guidance_enabled") not in (False, None):
                forbidden_runtime_flags += 1
            if record.get("candidate_reference_blend") is not None:
                forbidden_runtime_flags += 1
            record_identity_hashes.append(
                _hash_json(
                    {
                        "schema": "dp_camp_v14_public_simulator_record_identity_v1",
                        "path_signature": path_signature,
                        "selection_step": record.get("selection_step"),
                        "candidate_tensor_hash": selector_hash,
                        "num_candidates": record.get("num_candidates"),
                    }
                )
            )
    return {
        "sets": {
            "candidate_tensor_hashes": set(candidate_hashes),
            "path_signatures": set(path_signatures),
            "record_identity_hashes": set(record_identity_hashes),
            "split_manifest_roots": set(split_manifest_roots),
        },
        "selection_logs": [str(path) for path in selection_logs],
        "summary": {
            "selection_log_count": len(selection_logs),
            "record_count": records,
            "wrong_step_logs": wrong_step_logs,
            "candidate_tensor_hash_count": len(candidate_hashes),
            "unique_candidate_tensor_hash_count": len(set(candidate_hashes)),
            "path_signature_count": len(path_signatures),
            "unique_path_signature_count": len(set(path_signatures)),
            "record_identity_hash_count": len(record_identity_hashes),
            "unique_record_identity_hash_count": len(set(record_identity_hashes)),
            "split_manifest_root_count": len(split_manifest_roots),
            "unique_split_manifest_root_count": len(set(split_manifest_roots)),
            "formal_seed_intersection": sorted(formal_seeds),
            "tensor_hash_mismatches": tensor_hash_mismatches,
            "executed_non_top1": executed_non_top1,
            "default_off_missing": default_off_missing,
            "provenance_missing": provenance_missing,
            "closed_loop_collect_count": closed_loop_collect_count,
            "forbidden_runtime_flags": forbidden_runtime_flags,
        },
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    registry_paths = {
        "candidate_tensor_hash_registry": output_dir / "candidate_tensor_hash_registry.json",
        "path_signature_registry": output_dir / "path_signature_registry.json",
        "record_identity_hash_registry": output_dir / "record_identity_hash_registry.json",
        "split_manifest_root_registry": output_dir / "split_manifest_root_registry.json",
    }
    registry_key_map = {
        "candidate_tensor_hash_registry": "candidate_tensor_hashes",
        "path_signature_registry": "path_signatures",
        "record_identity_hash_registry": "record_identity_hashes",
        "split_manifest_root_registry": "split_manifest_roots",
    }
    for name, path in registry_paths.items():
        values = report["registries"][registry_key_map[name]]
        _write_json(
            path,
            {
                "schema_version": REGISTRY_SCHEMA_VERSION,
                "values": values,
                "value_count": len(values),
            },
        )
    _write_json(output_dir / "selection_logs.json", report["registries"]["selection_logs"])
    slim = dict(report)
    slim.pop("registries", None)
    _write_json(output_dir / "zero_overlap_validation_report.json", slim)
    (output_dir / "zero_overlap_validation_report.md").write_text(render_markdown(report), encoding="utf-8")
    sha_lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            sha_lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")


def _checks(
    *,
    execution_output_root: Path,
    execution_report_json: Path,
    execution_report: dict[str, Any],
    v14_audit_md: Path,
    current_status_md: Path,
    v14_text: str,
    status_text: str,
    materialized: dict[str, Any],
    references: dict[str, set[str]],
    intersections: dict[str, int],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    reference_files: dict[str, Path],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    summary = materialized["summary"]
    final = _dict(execution_report.get("final_decision"))
    execution = _dict(execution_report.get("execution"))
    add(_expect("execution_output_root_exists", execution_output_root.is_dir(), True))
    add(_expect("execution_report_exists", execution_report_json.is_file(), True))
    add(_expect("execution_report_passed", final.get("passed"), True))
    add(_expect("execution_report_status", final.get("status"), "public_simulator_fixed_dp_candidate_generation_execution_passed"))
    add(_expect("execution_commands_succeeded", execution.get("commands_succeeded"), EXPECTED_LOG_COUNT))
    add(_expect("v14_audit_exists", v14_audit_md.is_file(), True))
    add(_expect("current_status_exists", current_status_md.is_file(), True))
    add(_expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work))
    add(_expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True))
    add(_expect("status_doc_next_work", authorized_current_work in status_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    for name, path in reference_files.items():
        add(_expect(f"{name}_exists", path.is_file(), True))
    add(_expect("reference_candidate_tensor_hashes_nonempty", bool(references["candidate_tensor_hashes"]), True))
    add(_expect("reference_path_signatures_nonempty", bool(references["path_signatures"]), True))
    add(_expect("reference_record_identity_hashes_nonempty", bool(references["record_identity_hashes"]), True))
    add(_expect("reference_split_manifest_roots_nonempty", bool(references["split_manifest_roots"]), True))
    add(_expect("selection_log_count", summary["selection_log_count"], EXPECTED_LOG_COUNT))
    add(_expect("record_count", summary["record_count"], EXPECTED_RECORDS))
    add(_expect("wrong_step_logs_empty", summary["wrong_step_logs"], []))
    add(_expect("candidate_tensor_hash_count", summary["candidate_tensor_hash_count"], EXPECTED_RECORDS))
    add(_expect("path_signature_count", summary["path_signature_count"], EXPECTED_LOG_COUNT))
    add(_expect("unique_path_signature_count", summary["unique_path_signature_count"], EXPECTED_LOG_COUNT))
    add(_expect("record_identity_hash_count", summary["record_identity_hash_count"], EXPECTED_RECORDS))
    add(_expect("unique_record_identity_hash_count", summary["unique_record_identity_hash_count"], EXPECTED_RECORDS))
    add(_expect("split_manifest_root_nonempty", summary["unique_split_manifest_root_count"] > 0, True))
    add(_expect("formal_seed_intersection_empty", summary["formal_seed_intersection"], []))
    add(_expect("tensor_hash_mismatches_zero", summary["tensor_hash_mismatches"], 0))
    add(_expect("executed_non_top1_zero", summary["executed_non_top1"], 0))
    add(_expect("default_off_missing_zero", summary["default_off_missing"], 0))
    add(_expect("provenance_missing_zero", summary["provenance_missing"], 0))
    add(_expect("closed_loop_collect_count_zero", summary["closed_loop_collect_count"], 0))
    add(_expect("forbidden_runtime_flags_zero", summary["forbidden_runtime_flags"], 0))
    for name, count in intersections.items():
        add(_expect(name, count, 0))
    return checks


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["registry_summary"]
    return "\n".join(
        [
            "# V14 Public Simulator Fixed-DP Zero-Overlap Validation",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Selection logs: `{summary['selection_log_count']}`",
            f"- Records: `{summary['record_count']}`",
            f"- Candidate tensor hashes: `{summary['candidate_tensor_hash_count']}`",
            f"- Path signatures: `{summary['path_signature_count']}`",
            f"- Record identities: `{summary['record_identity_hash_count']}`",
            f"- Zero intersections: `{report['zero_intersection_counts']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
        ]
    )


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "data_preparation_preflight_authorized_next": passed,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed_by_source": True,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }


def _failure_class(failed: list[str]) -> str:
    if any("intersection_count" in check for check in failed):
        return "zero_overlap_intersection_nonzero"
    if any("reference_" in check for check in failed):
        return "reference_training_registry_missing_or_empty"
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    return "zero_overlap_validation_contract_failure"


def _load_registry_values(path: Path) -> set[str]:
    payload = _read_json(path)
    values: set[str] = set()
    if isinstance(payload, dict):
        value_keys = {"values", "entries", "items", "hashes", "signatures", "roots"}
        metadata_keys = {"schema_version", "value_count", *value_keys}
        for key in value_keys:
            value = payload.get(key)
            if isinstance(value, list):
                values.update(str(item) for item in value if str(item))
            elif isinstance(value, dict):
                values.update(str(item) for item in value.keys())
        values.update(str(key) for key in payload.keys() if key not in metadata_keys)
    elif isinstance(payload, list):
        values.update(str(item) for item in payload if str(item))
    return {value for value in values if value}


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        return []
    return [_dict(item) for item in payload]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    pattern = f"{key}="
    matches = [line.split("=", 1)[1].strip() for line in text.splitlines() if line.startswith(pattern)]
    return matches[-1] if matches else None


def _hash_json(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_stable(payload), separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": actual == expected}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
