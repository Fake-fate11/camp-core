#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_NO_FEASIBLE_RECORDS = 15
COMPLETE_STATUS = (
    "dp_native_fixed_artifact_fallback_risk_ranking_audit_complete"
)
REJECT_STATUS = (
    "dp_native_fixed_artifact_fallback_risk_ranking_audit_rejected"
)
NEXT_DESIGN_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_remediation_design_plan_only"
)

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

LENGTH_FIELDS = (
    "feasible_mask",
    "infeasibility_reasons",
    "dp_candidate_rewards",
    "atoms",
    "normalized_atoms",
    "scores",
    "selection_scores",
)

LANE_REWARD_FIELDS = (
    "lane_crossing",
    "static_crossing",
    "off_road_fraction",
    "lane_near_frac",
    "lane_wide_frac",
    "centerline",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only fallback-risk ranking audit over an existing DP-native "
            "CAMP broader nonformal evaluation artifact."
        )
    )
    parser.add_argument("--evaluation_root", type=Path, required=True)
    parser.add_argument("--expected_dp_head", default=EXPECTED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=None)
    parser.add_argument("--camp_head", default=None)
    parser.add_argument("--camp_origin_main", default=None)
    parser.add_argument("--expected_summary_sha256", default=None)
    parser.add_argument(
        "--expected_no_feasible_records",
        type=int,
        default=EXPECTED_NO_FEASIBLE_RECORDS,
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        evaluation_root=args.evaluation_root,
        expected_dp_head=args.expected_dp_head,
        dp_head=_git_head(args.dp_repo) if args.dp_repo else args.expected_dp_head,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        expected_summary_sha256=args.expected_summary_sha256,
        expected_no_feasible_records=args.expected_no_feasible_records,
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


def build_report(
    *,
    evaluation_root: Path,
    expected_dp_head: str = EXPECTED_DP_HEAD,
    dp_head: str = EXPECTED_DP_HEAD,
    camp_head: str | None = None,
    camp_origin_main: str | None = None,
    expected_summary_sha256: str | None = None,
    expected_no_feasible_records: int = EXPECTED_NO_FEASIBLE_RECORDS,
    label: str | None = None,
) -> dict[str, Any]:
    evaluation_root = evaluation_root.resolve()
    summary_path = evaluation_root / "broader_nonformal_eval_summary.json"
    selection_logs = sorted(evaluation_root.glob("*/camp_selection_log.json"))
    errors: list[str] = []
    if not summary_path.exists():
        errors.append("summary_json_missing")
    if not selection_logs:
        errors.append("camp_selection_logs_missing")

    summary = _load_json_dict(summary_path, errors) if summary_path.exists() else {}
    records = _load_selection_records(selection_logs, errors)
    no_feasible_records = [
        record for record in records if record["feasible_mask_valid"] and not any(record["feasible_mask"])
    ]
    record_audits = [
        _audit_no_feasible_record(record) for record in no_feasible_records
    ]
    checks = _build_checks(
        errors=errors,
        summary=summary,
        summary_path=summary_path,
        expected_summary_sha256=expected_summary_sha256,
        selection_logs=selection_logs,
        records=records,
        record_audits=record_audits,
        expected_no_feasible_records=expected_no_feasible_records,
        dp_head=dp_head,
        expected_dp_head=expected_dp_head,
    )
    passed = all(check["passed"] for check in checks)
    ranking = _ranking_summary(record_audits)
    provenance = _provenance_summary(record_audits)
    lower_risk_exists = (
        ranking["red"]["selected_not_min_count"] > 0
        or ranking["lane"]["selected_not_min_count"] > 0
        or ranking["quality"]["selected_not_min_count"] > 0
    )
    decision = {
        "status": COMPLETE_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": [
            check["name"] for check in checks if not check["passed"]
        ],
        "authorized_next_work": NEXT_DESIGN_GATE if passed else None,
        "existing_fallback_uniformly_least_bad_red": (
            passed and ranking["red"]["selected_not_min_count"] == 0
        ),
        "existing_fallback_uniformly_least_bad_lane": (
            passed and ranking["lane"]["selected_not_min_count"] == 0
        ),
        "existing_fallback_uniformly_least_bad_quality": (
            passed and ranking["quality"]["selected_not_min_count"] == 0
        ),
        "lower_risk_fixed_candidate_exists_under_logged_costs": (
            passed and lower_risk_exists
        ),
        "fallback_risk_training_authorized_now": False,
        "feasible_ranking_master_change_authorized": False,
        "hard_feasibility_relaxation_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "candidate_trajectory_rewrite_authorized": False,
        "postprocess_postselection_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False

    return {
        "analysis": {
            "name": "dp_native_fixed_artifact_fallback_risk_ranking_audit_v1",
            "label": label,
            "read_only": True,
            "fixed_source_artifact_only": True,
            "records_scope": "records_without_feasible_candidate_only",
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
            "math_boundary": (
                "This audit reads existing fixed candidate logs only. It "
                "compares the logged selected_index against fixed per-candidate "
                "DP reward costs and provenance flags. It does not replay, "
                "generate candidates, train CAMP, modify DP, promote selector "
                "logic, or claim safety benefit."
            ),
        },
        "source_paths": {
            "evaluation_root": str(evaluation_root),
            "summary_json": str(summary_path),
            "selection_logs": [str(path) for path in selection_logs],
        },
        "source_hashes": {
            "summary_json_sha256": _sha256(summary_path) if summary_path.exists() else None,
            "selection_log_sha256": {
                str(path.relative_to(evaluation_root)): _sha256(path)
                for path in selection_logs
            },
        },
        "heads": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": expected_dp_head,
        },
        "summary_evidence": {
            "schema_version": summary.get("schema_version"),
            "run_count": summary.get("run_count"),
            "total_selection_records": summary.get("total_selection_records"),
            "total_records_with_feasible_candidate": summary.get(
                "total_records_with_feasible_candidate"
            ),
            "total_records_without_feasible_candidate": summary.get(
                "total_records_without_feasible_candidate"
            ),
            "total_selected_index_in_range_records": summary.get(
                "total_selected_index_in_range_records"
            ),
            "total_provenance_records": summary.get("total_provenance_records"),
            "total_payload_valid_records": summary.get("total_payload_valid_records"),
            "total_prepost_equal_records": summary.get("total_prepost_equal_records"),
            "total_no_candidate_row_append_records": summary.get(
                "total_no_candidate_row_append_records"
            ),
            "total_no_coordinate_heading_speed_rewrite_records": summary.get(
                "total_no_coordinate_heading_speed_rewrite_records"
            ),
        },
        "record_counts": _record_counts(records, no_feasible_records),
        "ranking_summary": ranking,
        "provenance_summary": provenance,
        "record_audits": record_audits,
        "checks": checks,
        "final_decision": decision,
    }


def _load_json_dict(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path reporting
        errors.append(f"{path}:json_load_failed:{exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path}:json_root_not_object")
        return {}
    return payload


def _load_selection_records(
    selection_logs: list[Path],
    errors: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in selection_logs:
        try:
            payload = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive path reporting
            errors.append(f"{log_path}:json_load_failed:{exc}")
            continue
        if not isinstance(payload, list):
            errors.append(f"{log_path}:json_root_not_array")
            continue
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                errors.append(f"{log_path}:record_{index}_not_object")
                continue
            feasible = raw.get("feasible_mask")
            records.append(
                {
                    "run_id": log_path.parent.name,
                    "log_path": str(log_path),
                    "record_index": index,
                    "record": raw,
                    "feasible_mask_valid": isinstance(feasible, list),
                    "feasible_mask": feasible if isinstance(feasible, list) else [],
                }
            )
    return records


def _audit_no_feasible_record(record_entry: dict[str, Any]) -> dict[str, Any]:
    record = record_entry["record"]
    errors: list[str] = []
    candidate_count = _candidate_count(record, errors)
    selected_index = _selected_index(record, candidate_count, errors)
    length_checks = _length_checks(record, candidate_count)
    errors.extend(
        f"{field}_candidate_count_mismatch"
        for field, ok in length_checks.items()
        if not ok
    )
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list):
        rewards = []
        errors.append("dp_candidate_rewards_missing")
    elif len(rewards) != candidate_count:
        errors.append("dp_candidate_rewards_candidate_count_mismatch")

    red_costs = _red_light_costs(rewards, errors)
    lane_costs = _lane_costs(rewards, errors)
    quality_costs = _quality_costs(rewards, errors)
    selected_in_range = selected_index is not None and 0 <= selected_index < candidate_count
    provenance = _audit_provenance(record, candidate_count, selected_index, errors)
    mutation = _audit_no_mutation_evidence(record, errors)
    reason_signature = _reason_signature(record.get("infeasibility_reasons"))
    return {
        "run_id": record_entry["run_id"],
        "record_index": record_entry["record_index"],
        "candidate_count": candidate_count,
        "selected_index": selected_index,
        "selected_index_in_range": selected_in_range,
        "all_candidate_reason_signature": reason_signature,
        "union_reasons": sorted(
            {reason for reasons in record.get("infeasibility_reasons", []) for reason in reasons}
        )
        if isinstance(record.get("infeasibility_reasons"), list)
        else [],
        "length_checks": length_checks,
        "ranking": {
            "red": _metric_audit(red_costs, selected_index),
            "lane": _metric_audit(lane_costs, selected_index),
            "quality": _metric_audit(quality_costs, selected_index),
        },
        "candidate_tensor_provenance": provenance,
        "no_mutation_evidence": mutation,
        "errors": errors,
    }


def _candidate_count(record: dict[str, Any], errors: list[str]) -> int:
    raw = record.get("num_candidates")
    if isinstance(raw, bool) or not isinstance(raw, int):
        errors.append("num_candidates_not_int")
        return 0
    if raw <= 0:
        errors.append("num_candidates_not_positive")
    return int(raw)


def _selected_index(
    record: dict[str, Any],
    candidate_count: int,
    errors: list[str],
) -> int | None:
    raw = record.get("selected_index")
    if isinstance(raw, bool) or not isinstance(raw, int):
        errors.append("selected_index_not_int")
        return None
    if raw < 0 or raw >= candidate_count:
        errors.append("selected_index_out_of_range")
    return int(raw)


def _length_checks(record: dict[str, Any], candidate_count: int) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for field in LENGTH_FIELDS:
        value = record.get(field)
        checks[field] = isinstance(value, list) and len(value) == candidate_count
    return checks


def _red_light_costs(rewards: list[Any], errors: list[str]) -> list[float]:
    values: list[float] = []
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict):
            errors.append(f"dp_candidate_rewards_{index}_not_object")
            values.append(math.nan)
            continue
        if "red_light" not in reward:
            errors.append(f"dp_candidate_rewards_{index}_red_light_missing")
            values.append(math.nan)
            continue
        red = _finite_float(reward["red_light"], f"reward_{index}_red_light", errors)
        values.append(max(-red, 0.0))
    return values


def _lane_costs(rewards: list[Any], errors: list[str]) -> list[float]:
    values: list[float] = []
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict):
            values.append(math.nan)
            continue
        missing = [field for field in LANE_REWARD_FIELDS if field not in reward]
        if missing:
            errors.append(
                f"dp_candidate_rewards_{index}_lane_fields_missing:{','.join(missing)}"
            )
            values.append(math.nan)
            continue
        lane_cost = 0.0
        lane_cost += 1.0 if bool(reward["lane_crossing"]) else 0.0
        lane_cost += 1.0 if bool(reward["static_crossing"]) else 0.0
        for field in ("off_road_fraction", "lane_near_frac", "lane_wide_frac"):
            lane_cost += _finite_float(
                reward[field],
                f"reward_{index}_{field}",
                errors,
            )
        centerline = _finite_float(
            reward["centerline"],
            f"reward_{index}_centerline",
            errors,
        )
        lane_cost += max(-centerline, 0.0)
        values.append(lane_cost)
    return values


def _quality_costs(rewards: list[Any], errors: list[str]) -> list[float]:
    values: list[float] = []
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict):
            values.append(math.nan)
            continue
        if "total" not in reward:
            errors.append(f"dp_candidate_rewards_{index}_total_missing")
            values.append(math.nan)
            continue
        total = _finite_float(reward["total"], f"reward_{index}_total", errors)
        values.append(max(-total, 0.0))
    return values


def _finite_float(value: Any, label: str, errors: list[str]) -> float:
    if isinstance(value, bool):
        errors.append(f"{label}_not_numeric")
        return math.nan
    try:
        result = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label}_not_numeric")
        return math.nan
    if not math.isfinite(result):
        errors.append(f"{label}_not_finite")
        return math.nan
    return result


def _metric_audit(values: list[float], selected_index: int | None) -> dict[str, Any]:
    finite = [value for value in values if math.isfinite(value)]
    if len(finite) != len(values) or not values:
        return {
            "costs": values,
            "min_cost": None,
            "min_indices": [],
            "selected_cost": None,
            "selected_is_min": False,
            "lower_cost_candidate_indices": [],
        }
    min_cost = min(values)
    min_indices = [
        index for index, value in enumerate(values) if abs(value - min_cost) <= 1e-9
    ]
    if selected_index is None or selected_index < 0 or selected_index >= len(values):
        selected_cost = None
        selected_is_min = False
        lower_indices: list[int] = []
    else:
        selected_cost = values[selected_index]
        selected_is_min = selected_index in min_indices
        lower_indices = [
            index
            for index, value in enumerate(values)
            if value < selected_cost - 1e-9
        ]
    return {
        "costs": values,
        "min_cost": min_cost,
        "min_indices": min_indices,
        "selected_cost": selected_cost,
        "selected_is_min": selected_is_min,
        "lower_cost_candidate_indices": lower_indices,
    }


def _audit_provenance(
    record: dict[str, Any],
    candidate_count: int,
    selected_index: int | None,
    errors: list[str],
) -> dict[str, Any]:
    payload = record.get("camp_candidate_tensor_provenance")
    if not isinstance(payload, dict):
        errors.append("camp_candidate_tensor_provenance_missing")
        return {"present": False, "checks": {}, "hashes": {}}
    checks = {
        "payload_valid": payload.get("payload_valid") is True,
        "candidate_count_matches": payload.get("candidate_count") == candidate_count,
        "post_selector_candidate_count_matches": payload.get(
            "post_selector_candidate_count"
        )
        == candidate_count,
        "selected_index_matches": payload.get("selected_index") == selected_index,
        "selected_index_in_range": payload.get("selected_index_in_range") is True,
        "pre_post_tensor_hash_equal": payload.get("pre_post_tensor_hash_equal") is True,
        "no_candidate_row_append": payload.get("no_candidate_row_append") is True,
        "no_coordinate_heading_speed_rewrite_by_camp": payload.get(
            "no_coordinate_heading_speed_rewrite_by_camp"
        )
        is True,
        "selection_effect_false": payload.get("selection_effect") is False,
        "candidate_generation_effect_false": payload.get(
            "candidate_generation_effect"
        )
        is False,
        "candidate_tensor_mutation_effect_false": payload.get(
            "candidate_tensor_mutation_effect"
        )
        is False,
        "outcome_label_input_false": payload.get("outcome_label_input") is False,
        "closed_loop_outcome_fields_read_false": payload.get(
            "closed_loop_outcome_fields_read"
        )
        is False,
        "reference_blend_present_false": payload.get("reference_blend_present")
        is False,
    }
    hashes = {
        "raw_dp_tensor_before_reference_blend": _tensor_hash(
            payload.get("raw_dp_tensor_before_reference_blend")
        ),
        "pre_camp_scoring_tensor": _tensor_hash(payload.get("pre_camp_scoring_tensor")),
        "post_camp_selector_tensor": _tensor_hash(
            payload.get("post_camp_selector_tensor")
        ),
    }
    pre_hash = hashes["pre_camp_scoring_tensor"]
    post_hash = hashes["post_camp_selector_tensor"]
    if pre_hash is not None and post_hash is not None:
        checks["pre_post_sha256_match_if_present"] = pre_hash == post_hash
    errors.extend(
        f"provenance_{name}_failed" for name, passed in checks.items() if not passed
    )
    return {"present": True, "checks": checks, "hashes": hashes}


def _tensor_hash(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    sha = value.get("sha256")
    return sha if isinstance(sha, str) else None


def _audit_no_mutation_evidence(
    record: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    contract = record.get("candidate_generation_contract")
    checks: dict[str, bool] = {}
    if isinstance(contract, dict):
        guidance = contract.get("guidance")
        checks["candidate_generation_contract_guidance_disabled"] = (
            contract.get("guidance_enabled") is False
        )
        checks["candidate_generation_contract_dp_weights_unchanged"] = (
            contract.get("changes_diffusion_planner_weights") is False
        )
        checks["candidate_generation_contract_camp_score_unchanged"] = (
            contract.get("changes_camp_score") is False
        )
        if isinstance(guidance, dict):
            checks["candidate_generation_contract_guidance_payload_disabled"] = (
                guidance.get("enabled") is False
            )
        reference_steps = contract.get("reference_blend_steps")
        checks["candidate_generation_contract_reference_blend_disabled"] = (
            reference_steps in (None, 0, [], {})
        )
    else:
        errors.append("candidate_generation_contract_missing")

    vector_reference_steps = record.get("candidate_reference_blend_steps")
    if isinstance(vector_reference_steps, list):
        checks["candidate_reference_blend_steps_all_zero"] = all(
            _is_zero_like(value) for value in vector_reference_steps
        )
    elif vector_reference_steps is None:
        checks["candidate_reference_blend_steps_all_zero"] = True
    else:
        checks["candidate_reference_blend_steps_all_zero"] = _is_zero_like(
            vector_reference_steps
        )

    for field in (
        "perfect_tracker_command_postselection",
        "traffic_light_hybrid_postselection",
        "underprogress_relaxation",
        "splice_shadow_rule",
    ):
        checks[f"{field}_disabled"] = _disabled_policy(record.get(field))
    errors.extend(f"{name}_failed" for name, passed in checks.items() if not passed)
    return {"checks": checks, "all_clean": all(checks.values()) if checks else False}


def _is_zero_like(value: Any) -> bool:
    if value in (None, False):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return math.isfinite(float(value)) and abs(float(value)) <= 1e-12
    if isinstance(value, list):
        return all(_is_zero_like(item) for item in value)
    return False


def _disabled_policy(value: Any) -> bool:
    if value in (None, False):
        return True
    if value is True:
        return False
    if isinstance(value, dict):
        suspicious = (
            "enabled",
            "selection_effect",
            "candidate_tensor_mutation_effect",
            "trajectory_rewrite_authorized",
            "postselection_executed",
            "relaxation_enabled",
        )
        found = False
        for key, item in value.items():
            if any(fragment in key for fragment in suspicious):
                found = True
                if item is not False:
                    return False
        return found
    return False


def _reason_signature(value: Any) -> str:
    if not isinstance(value, list):
        return "invalid_reasons"
    signatures = {tuple(reason_list) for reason_list in value if isinstance(reason_list, list)}
    if len(signatures) != 1:
        return "mixed_candidate_reasons"
    return str(list(next(iter(signatures))))


def _record_counts(
    records: list[dict[str, Any]],
    no_feasible_records: list[dict[str, Any]],
) -> dict[str, Any]:
    route_counts: Counter[str] = Counter()
    route_no_feasible: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    for entry in records:
        route = _route_from_run_id(entry["run_id"])
        route_counts[route] += 1
        selected = entry["record"].get("selected_index")
        selected_counts[str(selected)] += 1
    for entry in no_feasible_records:
        route_no_feasible[_route_from_run_id(entry["run_id"])] += 1
    return {
        "records_total": len(records),
        "records_without_feasible_candidate": len(no_feasible_records),
        "records_with_feasible_candidate": len(records) - len(no_feasible_records),
        "route_records": dict(sorted(route_counts.items())),
        "route_records_without_feasible_candidate": dict(
            sorted(route_no_feasible.items())
        ),
        "selected_index_counts": dict(sorted(selected_counts.items())),
    }


def _route_from_run_id(run_id: str) -> str:
    for suffix in ("_seed109_tl_off_static", "_seed109_tl_on_static", "_seed110_tl_off_static", "_seed110_tl_on_static"):
        if run_id.endswith(suffix):
            return run_id[: -len(suffix)]
    if "_seed" in run_id:
        return run_id.split("_seed", 1)[0]
    return run_id


def _ranking_summary(record_audits: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    by_reason: dict[str, Counter[str]] = defaultdict(Counter)
    for metric in ("red", "lane", "quality"):
        selected_min = sum(
            1 for audit in record_audits if audit["ranking"][metric]["selected_is_min"]
        )
        selected_not_min = len(record_audits) - selected_min
        lower = sum(
            1
            for audit in record_audits
            if audit["ranking"][metric]["lower_cost_candidate_indices"]
        )
        summary[metric] = {
            "records": len(record_audits),
            "selected_min_count": selected_min,
            "selected_not_min_count": selected_not_min,
            "lower_cost_candidate_available_count": lower,
        }
    for audit in record_audits:
        reason = "+".join(audit["union_reasons"]) or audit["all_candidate_reason_signature"]
        by_reason[reason]["records"] += 1
        for metric in ("red", "lane", "quality"):
            if audit["ranking"][metric]["selected_is_min"]:
                by_reason[reason][f"{metric}_selected_min"] += 1
            if audit["ranking"][metric]["lower_cost_candidate_indices"]:
                by_reason[reason][f"{metric}_lower_cost_available"] += 1
    summary["by_union_reason"] = {
        key: dict(value) for key, value in sorted(by_reason.items())
    }
    return summary


def _provenance_summary(record_audits: list[dict[str, Any]]) -> dict[str, Any]:
    check_counts: dict[str, int] = Counter()
    hash_pairs: Counter[str] = Counter()
    for audit in record_audits:
        payload = audit["candidate_tensor_provenance"]
        for name, passed in payload.get("checks", {}).items():
            if passed:
                check_counts[name] += 1
        hashes = payload.get("hashes", {})
        pre = hashes.get("pre_camp_scoring_tensor")
        post = hashes.get("post_camp_selector_tensor")
        if pre and post:
            hash_pairs[f"{pre}=={post}"] += 1
    return {
        "records": len(record_audits),
        "passed_check_counts": dict(sorted(check_counts.items())),
        "pre_post_hash_pair_counts": dict(sorted(hash_pairs.items())),
        "all_record_errors": [
            {
                "run_id": audit["run_id"],
                "record_index": audit["record_index"],
                "errors": audit["errors"],
            }
            for audit in record_audits
            if audit["errors"]
        ],
    }


def _build_checks(
    *,
    errors: list[str],
    summary: dict[str, Any],
    summary_path: Path,
    expected_summary_sha256: str | None,
    selection_logs: list[Path],
    records: list[dict[str, Any]],
    record_audits: list[dict[str, Any]],
    expected_no_feasible_records: int,
    dp_head: str,
    expected_dp_head: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("source_json_loads", not errors),
        _check("summary_json_present", summary_path.exists()),
        _check("selection_logs_present", bool(selection_logs)),
        _check("summary_selection_records_match", summary.get("total_selection_records") == len(records)),
        _check(
            "summary_without_feasible_matches",
            summary.get("total_records_without_feasible_candidate")
            == len(record_audits),
        ),
        _check(
            "expected_without_feasible_records",
            len(record_audits) == expected_no_feasible_records,
        ),
        _check("dp_head_fixed", dp_head == expected_dp_head),
        _check(
            "all_selected_index_in_range",
            all(audit["selected_index_in_range"] for audit in record_audits),
        ),
        _check(
            "all_candidate_counts_unchanged",
            all(
                all(audit["length_checks"].values())
                and all(audit["candidate_tensor_provenance"].get("checks", {}).get(name, False) for name in (
                    "candidate_count_matches",
                    "post_selector_candidate_count_matches",
                    "no_candidate_row_append",
                ))
                for audit in record_audits
            ),
        ),
        _check(
            "all_provenance_prepost_hashes_clean",
            all(
                audit["candidate_tensor_provenance"].get("checks", {}).get(
                    "pre_post_tensor_hash_equal", False
                )
                for audit in record_audits
            ),
        ),
        _check(
            "all_no_candidate_rewrite_evidence",
            all(
                audit["no_mutation_evidence"]["all_clean"]
                and audit["candidate_tensor_provenance"].get("checks", {}).get(
                    "no_coordinate_heading_speed_rewrite_by_camp", False
                )
                and audit["candidate_tensor_provenance"].get("checks", {}).get(
                    "candidate_tensor_mutation_effect_false", False
                )
                for audit in record_audits
            ),
        ),
        _check("all_required_record_costs_present", all(not audit["errors"] for audit in record_audits)),
    ]
    if expected_summary_sha256:
        checks.append(
            _check(
                "summary_sha256_matches_expected",
                _sha256(summary_path) == expected_summary_sha256,
            )
        )
    return checks


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(path: Path | None) -> str:
    if path is None:
        return EXPECTED_DP_HEAD
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["record_counts"]
    ranking = report["ranking_summary"]
    lines = [
        "# DP Native Fixed-Artifact Fallback Risk Ranking Audit",
        "",
        "This read-only audit compares logged fallback selections against fixed "
        "per-candidate DP reward costs for records without any feasible candidate.",
        "",
        "## Decision",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"authorized_next_work={decision['authorized_next_work']}",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "```",
        "",
        "## Fixed Source",
        "",
        "```text",
        f"evaluation_root={report['source_paths']['evaluation_root']}",
        f"summary_json_sha256={report['source_hashes']['summary_json_sha256']}",
        f"camp_head={report['heads']['camp_head']}",
        f"camp_origin_main={report['heads']['camp_origin_main']}",
        f"dp_head={report['heads']['dp_head']}",
        f"expected_dp_head={report['heads']['expected_dp_head']}",
        "```",
        "",
        "## Counts",
        "",
        "```text",
        f"records_total={counts['records_total']}",
        f"records_with_feasible_candidate={counts['records_with_feasible_candidate']}",
        f"records_without_feasible_candidate={counts['records_without_feasible_candidate']}",
        f"route_records_without_feasible_candidate={json.dumps(counts['route_records_without_feasible_candidate'], sort_keys=True)}",
        "```",
        "",
        "## Ranking Summary",
        "",
        "| Metric | Records | Selected at min | Lower-cost fixed candidate available |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in ("red", "lane", "quality"):
        item = ranking[metric]
        lines.append(
            "| `{}` | {} | {} | {} |".format(
                metric,
                item["records"],
                item["selected_min_count"],
                item["lower_cost_candidate_available_count"],
            )
        )
    lines.extend(
        [
            "",
            "## By Reason",
            "",
            "```json",
            json.dumps(ranking["by_union_reason"], indent=2, sort_keys=True),
            "```",
            "",
            "## Checks",
            "",
            "| Check | Passed |",
            "| --- | --- |",
        ]
    )
    for check in report["checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This audit does not add all-infeasible records to the feasible-ranking "
            "master, does not relax DP red-light or lane-crossing hard feasibility, "
            "does not change any candidate trajectory, and does not claim safety "
            "benefit or CAMP superiority over DP Top-1.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
