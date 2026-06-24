#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402
from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    CANDIDATE_GENERATION_SCHEMA_VERSION,
    PROVENANCE_SCHEMA_VERSION,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_data_builder_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_data_builder_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_data_builder_rejected"

FORBIDDEN_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "Full36_authorized",
    "formal_seeds_11_12_13_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only builder for DP-native all-infeasible "
            "fallback-risk training data."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument("--extractor_json", type=Path, default=None)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_data_builder",
        action="store_true",
        help="Explicit opt-in required before reading selection logs.",
    )
    parser.add_argument("--margin_scale", type=float, default=1.0)
    parser.add_argument("--margin_clip", type=float, default=100.0)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_training_data_report(
        selection_logs=args.selection_log,
        extractor_json=args.extractor_json,
        enabled=args.enable_default_off_fallback_risk_training_data_builder,
        margin_scale=args.margin_scale,
        margin_clip=args.margin_clip,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_training_data_report(
    *,
    selection_logs: list[Path],
    extractor_json: Path | None = None,
    enabled: bool = False,
    margin_scale: float = 1.0,
    margin_clip: float = 100.0,
    label: str | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_data_builder_v1",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "records_scope": "records_without_feasible_candidate_only",
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {
            "selection_logs": [str(path) for path in selection_logs],
            "extractor_json": str(extractor_json) if extractor_json else None,
        },
        "source_hashes": {},
        "records": [],
        "record_counts": {
            "records_total": 0,
            "records_without_feasible_candidate": 0,
            "records_with_feasible_candidate": 0,
            "records_built": 0,
            "failed_records": 0,
        },
        "failed_records": [],
        "extractor_evidence": None,
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=False,
            errors=[],
        ),
    }
    if not enabled:
        return report

    errors: list[str] = []
    if margin_scale < 0.0 or not math.isfinite(margin_scale):
        errors.append("margin_scale_invalid")
    if margin_clip < 0.0 or not math.isfinite(margin_clip):
        errors.append("margin_clip_invalid")
    if extractor_json is not None:
        report["extractor_evidence"] = _load_extractor_evidence(
            extractor_json,
            errors=errors,
        )

    for selection_log in selection_logs:
        log_path, records = _records_from_path(selection_log)
        log_sha = _sha256_file(log_path)
        report["source_hashes"][str(log_path)] = log_sha
        for record_index, record in enumerate(records):
            report["record_counts"]["records_total"] += 1
            feasible = _as_bool_list(record.get("feasible_mask"))
            if feasible is None:
                _add_failed(report, log_path, record_index, ["feasible_mask_invalid"])
                continue
            if any(feasible):
                report["record_counts"]["records_with_feasible_candidate"] += 1
                continue
            report["record_counts"]["records_without_feasible_candidate"] += 1
            built, record_errors = _build_record(
                record=record,
                source_log=log_path,
                source_log_sha256=log_sha,
                record_index=record_index,
                margin_scale=margin_scale,
                margin_clip=margin_clip,
            )
            if record_errors:
                _add_failed(report, log_path, record_index, record_errors)
                continue
            report["records"].append(built)

    report["record_counts"]["records_built"] = len(report["records"])
    report["record_counts"]["failed_records"] = len(report["failed_records"])
    errors.extend(
        f"record_{item['record_index']}:{error}"
        for item in report["failed_records"]
        for error in item["errors"]
    )
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _records_from_path(path: Path) -> tuple[Path, list[dict[str, Any]]]:
    log_path = path / "camp_selection_log.json" if path.is_dir() else path
    if not log_path.is_file():
        raise FileNotFoundError(f"Selection log not found: {log_path}")
    records = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{log_path} must contain a JSON list.")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"{log_path} must contain JSON object records.")
    return log_path, records


def _load_extractor_evidence(path: Path, *, errors: list[str]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    decision = payload.get("final_decision")
    if not isinstance(decision, dict) or decision.get("passed") is not True:
        errors.append("extractor_json_not_passed")
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "status": decision.get("status") if isinstance(decision, dict) else None,
        "passed": decision.get("passed") if isinstance(decision, dict) else None,
        "records_without_feasible_candidate": payload.get("record_counts", {}).get(
            "records_without_feasible_candidate"
        ),
    }


def _build_record(
    *,
    record: dict[str, Any],
    source_log: Path,
    source_log_sha256: str,
    record_index: int,
    margin_scale: float,
    margin_clip: float,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or not all(isinstance(item, dict) for item in rewards):
        return {}, ["dp_candidate_rewards_invalid"]
    candidate_count = len(rewards)
    if candidate_count < 1:
        return {}, ["candidate_count_empty"]
    selected_index = _as_index(record.get("selected_index"), candidate_count, errors)
    errors.extend(_validate_generation_contract(record.get("candidate_generation_contract"), candidate_count))
    errors.extend(_validate_provenance(record.get("camp_candidate_tensor_provenance"), candidate_count, selected_index))
    atoms = _validate_atoms(record, candidate_count, errors)
    cost_rows = [
        _costs(reward, index=index, errors=errors)
        for index, reward in enumerate(rewards)
    ]
    reasons = record.get("infeasibility_reasons")
    if not isinstance(reasons, list):
        errors.append("infeasibility_reasons_invalid")
        reasons = [[] for _ in range(candidate_count)]
    policy = _reason_policy(reasons)
    ordered = [
        tuple(cost_rows[index][name] for name in policy) + (float(index),)
        for index in range(candidate_count)
    ]
    oracle_index = min(range(candidate_count), key=lambda index: ordered[index])
    oracle_tuple = ordered[oracle_index]
    margins = [
        min(
            max(
                margin_scale
                * sum(
                    max(value - oracle_tuple[pos], 0.0)
                    for pos, value in enumerate(item[:3])
                ),
                0.0,
            ),
            margin_clip,
        )
        for item in ordered
    ]
    if errors:
        return {}, errors
    run_id = record.get("run_id") or source_log.parent.name
    output_record_index = record.get("record_index", record_index)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_log": str(source_log),
        "source_log_sha256": source_log_sha256,
        "source_artifact_sha256": record.get("source_artifact_sha256", source_log_sha256),
        "run_id": run_id,
        "record_index": output_record_index,
        "record_identity_hash": _record_identity_hash(
            source_log=str(source_log),
            source_log_sha256=source_log_sha256,
            run_id=run_id,
            record_index=output_record_index,
        ),
        "selection_step": record.get("selection_step"),
        "candidate_count": candidate_count,
        "selected_index": selected_index,
        "oracle_index": oracle_index,
        "oracle_policy": list(policy),
        "costs": cost_rows,
        "margins": margins,
        "atom_schema_version": record.get("atom_schema_version"),
        "atom_names": record.get("atom_names"),
        "atoms": atoms,
        "normalized_atoms": record.get("normalized_atoms"),
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }, []


def _validate_generation_contract(contract: Any, candidate_count: int) -> list[str]:
    if not isinstance(contract, dict):
        return ["candidate_generation_contract_missing"]
    errors: list[str] = []
    if contract.get("schema_version") != CANDIDATE_GENERATION_SCHEMA_VERSION:
        errors.append("candidate_generation_contract_schema_mismatch")
    contract_candidates = _strict_int(
        contract.get("num_candidates"),
        "candidate_generation_contract_num_candidates",
        errors,
    )
    if contract_candidates != candidate_count:
        errors.append("candidate_generation_contract_candidate_count_mismatch")
    if "reference_blend_steps" not in contract:
        errors.append("candidate_generation_contract_reference_blend_missing")
    if contract.get("reference_blend_steps") is not None:
        errors.append("candidate_generation_contract_reference_blend_enabled")
    if contract.get("guidance_enabled") is not False:
        errors.append("candidate_generation_contract_guidance_enabled")
    if contract.get("changes_diffusion_planner_weights") is not False:
        errors.append("candidate_generation_contract_changes_dp_weights")
    return errors


def _validate_provenance(payload: Any, candidate_count: int, selected_index: int) -> list[str]:
    if not isinstance(payload, dict):
        return ["camp_candidate_tensor_provenance_missing"]
    errors: list[str] = []
    if payload.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        errors.append("provenance_schema_mismatch")
    for field in (
        "selection_effect",
        "candidate_generation_effect",
        "candidate_tensor_mutation_effect",
        "candidate_generation_authorized",
        "trajectory_rewrite_authorized",
        "dp_modification_authorized",
        "outcome_label_input",
        "closed_loop_outcome_fields_read",
    ):
        if payload.get(field) is not False:
            errors.append(f"provenance_{field}_not_false")
    for field in (
        "payload_valid",
        "pre_post_tensor_hash_equal",
        "selected_index_in_range",
        "no_candidate_row_append",
        "no_coordinate_heading_speed_rewrite_by_camp",
    ):
        if payload.get(field) is not True:
            errors.append(f"provenance_{field}_not_true")
    payload_candidates = _strict_int(
        payload.get("candidate_count"),
        "provenance_candidate_count",
        errors,
    )
    if payload_candidates != candidate_count:
        errors.append("provenance_candidate_count_mismatch")
    post_selector_candidates = _strict_int(
        payload.get("post_selector_candidate_count"),
        "provenance_post_selector_candidate_count",
        errors,
    )
    if post_selector_candidates != candidate_count:
        errors.append("provenance_post_selector_candidate_count_mismatch")
    payload_selected = _strict_int(
        payload.get("selected_index"),
        "provenance_selected_index",
        errors,
    )
    if payload_selected != selected_index:
        errors.append("provenance_selected_index_mismatch")
    return errors


def _validate_atoms(record: dict[str, Any], candidate_count: int, errors: list[str]) -> list[list[float]]:
    rows = _validate_nonnegative_matrix(
        record.get("atoms"),
        candidate_count,
        "atoms",
        errors,
    )
    atom_dim = len(rows[0]) if rows else 0
    try:
        expected_version, expected_names = atom_schema_for_dimension(atom_dim)
    except ValueError:
        expected_version, expected_names = "", ()
        errors.append("atom_schema_dimension_not_approved")
    if record.get("atom_schema_version") != expected_version:
        errors.append("atom_schema_version_mismatch")
    if tuple(record.get("atom_names") or ()) != tuple(expected_names):
        errors.append("atom_names_mismatch")
    normalized_rows = _validate_nonnegative_matrix(
        record.get("normalized_atoms"),
        candidate_count,
        "normalized_atoms",
        errors,
    )
    if normalized_rows and atom_dim and len(normalized_rows[0]) != atom_dim:
        errors.append("normalized_atoms_atom_dimension_mismatch")
    return rows


def _costs(reward: dict[str, Any], *, index: int, errors: list[str]) -> dict[str, float]:
    required = (
        "red_light",
        "lane_crossing",
        "static_crossing",
        "off_road_fraction",
        "lane_near_frac",
        "lane_wide_frac",
        "centerline",
        "total",
    )
    missing = [field for field in required if field not in reward]
    if missing:
        errors.append(f"reward_{index}_missing_fields:{','.join(missing)}")
        return {"red": 0.0, "lane": 0.0, "quality": 0.0}
    red = max(-_number(reward["red_light"], f"reward_{index}_red_light", errors), 0.0)
    lane = (
        _bool_cost(reward["lane_crossing"], f"reward_{index}_lane_crossing", errors)
        + _bool_cost(reward["static_crossing"], f"reward_{index}_static_crossing", errors)
        + _number(reward["off_road_fraction"], f"reward_{index}_off_road_fraction", errors)
        + _number(reward["lane_near_frac"], f"reward_{index}_lane_near_frac", errors)
        + _number(reward["lane_wide_frac"], f"reward_{index}_lane_wide_frac", errors)
        + max(-_number(reward["centerline"], f"reward_{index}_centerline", errors), 0.0)
    )
    quality = max(-_number(reward["total"], f"reward_{index}_total", errors), 0.0)
    return {"red": red, "lane": lane, "quality": quality}


def _number(value: Any, field: str, errors: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{field}_not_numeric")
        return 0.0
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"{field}_not_finite")
        return 0.0
    return number


def _bool_cost(value: Any, field: str, errors: list[str]) -> float:
    if not isinstance(value, bool):
        errors.append(f"{field}_not_bool")
        return 0.0
    return 1.0 if value else 0.0


def _reason_policy(reasons: list[Any]) -> tuple[str, str, str]:
    flat = set()
    for per_candidate in reasons:
        if isinstance(per_candidate, list):
            flat.update(str(reason) for reason in per_candidate)
    if "dp_red_light" in flat:
        return ("red", "lane", "quality")
    if flat & {"dp_lane_crossing", "lane_crossing", "dp_static_crossing"}:
        return ("lane", "red", "quality")
    return ("quality", "red", "lane")


def _as_bool_list(value: Any) -> list[bool] | None:
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, bool) for item in value):
        return None
    return list(value)


def _as_index(value: Any, candidate_count: int, errors: list[str]) -> int:
    index = _strict_int(value, "selected_index", errors)
    if index is None:
        return -1
    if index < 0 or index >= candidate_count:
        errors.append("selected_index_out_of_range")
    return index


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return int(value)


def _validate_nonnegative_matrix(
    value: Any,
    candidate_count: int,
    field: str,
    errors: list[str],
) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != candidate_count:
        errors.append(f"{field}_candidate_count_mismatch")
        return []
    rows: list[list[float]] = []
    atom_dim: int | None = None
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or not row:
            errors.append(f"{field}_{row_index}_row_invalid")
            continue
        if atom_dim is None:
            atom_dim = len(row)
        elif len(row) != atom_dim:
            errors.append(f"{field}_{row_index}_row_dimension_mismatch")
        values: list[float] = []
        for item in row:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                errors.append(f"{field}_{row_index}_not_numeric")
                continue
            number = float(item)
            if not math.isfinite(number) or number < 0.0:
                errors.append(f"{field}_{row_index}_not_finite_nonnegative")
                continue
            values.append(number)
        rows.append(values)
    return rows


def _add_failed(
    report: dict[str, Any],
    source_log: Path,
    record_index: int,
    errors: list[str],
) -> None:
    report["failed_records"].append(
        {
            "source_log": str(source_log),
            "record_index": record_index,
            "errors": errors,
        }
    )


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": errors,
        "dataset_builder_output_written": bool(enabled and passed),
        "training_authorized": False,
        "production_selector_change_authorized": False,
        "online_selector_change_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "hard_feasibility_relaxation_authorized": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_identity_hash(
    *,
    source_log: str,
    source_log_sha256: str,
    run_id: Any,
    record_index: Any,
) -> str:
    identity = {
        "source_log": source_log,
        "source_log_sha256": source_log_sha256,
        "run_id": run_id,
        "record_index": record_index,
    }
    return _sha256_text(json.dumps(identity, sort_keys=True, separators=(",", ":")))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["record_counts"]
    lines = [
        "# DP Native Fallback Risk Training Data Builder",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"records_total={counts['records_total']}",
        f"records_without_feasible_candidate={counts['records_without_feasible_candidate']}",
        f"records_built={counts['records_built']}",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "```",
        "",
    ]
    lines.extend(
        [
            "This builder only reads existing fixed-candidate selection logs "
            "after an explicit enable flag. It does not run replay, generate "
            "candidates, train CAMP, modify DP, promote a selector or atom, "
            "or claim safety benefit.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
