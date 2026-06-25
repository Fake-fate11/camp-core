from __future__ import annotations

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

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension


DISABLED_STATUS = "dp_native_fallback_risk_training_data_builder_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_data_builder_contract_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_data_builder_contract_rejected"
ITERATION_AUDIT = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_AUTHORIZATION_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_"
    "implementation_authorization_only"
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


def _reward(
    *,
    red_light: object = -1.0,
    lane_crossing: object = False,
    centerline: object = 0.0,
    total: object = -50.0,
) -> dict[str, object]:
    return {
        "red_light": red_light,
        "lane_crossing": lane_crossing,
        "static_crossing": False,
        "off_road_fraction": 0.0,
        "lane_near_frac": 0.0,
        "lane_wide_frac": 0.0,
        "centerline": centerline,
        "total": total,
    }


def _provenance(
    *,
    candidate_count: int,
    selected_index: int,
    **overrides: object,
) -> dict[str, object]:
    tensor = {
        "sha256": "a" * 64,
        "shape": [candidate_count, 80, 4],
        "dtype": "float32",
        "hash_input": "contiguous_candidate_tensor_bytes",
        "nan_policy": "preserve_tensor_bytes",
    }
    payload: dict[str, object] = {
        "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
        "payload_valid": True,
        "candidate_count": candidate_count,
        "post_selector_candidate_count": candidate_count,
        "selected_index": selected_index,
        "selected_index_in_range": True,
        "pre_post_tensor_hash_equal": True,
        "no_candidate_row_append": True,
        "no_coordinate_heading_speed_rewrite_by_camp": True,
        "selection_effect": False,
        "candidate_generation_effect": False,
        "candidate_tensor_mutation_effect": False,
        "candidate_generation_authorized": False,
        "trajectory_rewrite_authorized": False,
        "dp_modification_authorized": False,
        "outcome_label_input": False,
        "closed_loop_outcome_fields_read": False,
        "pre_camp_scoring_tensor": tensor,
        "post_camp_selector_tensor": tensor,
    }
    payload.update(overrides)
    return payload


def _record(
    *,
    reasons: list[list[str]] | None = None,
    rewards: list[dict[str, object]] | None = None,
    feasible_mask: list[bool] | None = None,
    atoms: list[list[float]] | None = None,
    selected_index: int = 0,
    provenance_overrides: dict[str, object] | None = None,
    generation_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    rewards = rewards or [_reward(), _reward(red_light=-2.0)]
    candidate_count = len(rewards)
    version, names = atom_schema_for_dimension(9)
    atoms = atoms or [[0.1 * (index + 1) for _ in range(9)] for index in range(candidate_count)]
    generation_contract: dict[str, object] = {
        "schema_version": "dp_candidate_generation_contract_v1",
        "num_candidates": candidate_count,
        "noise_strategy": "iid",
        "reference_blend_steps": None,
        "guidance_enabled": False,
        "changes_diffusion_planner_weights": False,
    }
    generation_contract.update(generation_overrides or {})
    return {
        "source_artifact_sha256": "b" * 64,
        "run_id": "synthetic_run",
        "record_index": 0,
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": candidate_count,
        "feasible_mask": feasible_mask or [False for _ in range(candidate_count)],
        "infeasibility_reasons": reasons
        or [["dp_red_light"] for _ in range(candidate_count)],
        "dp_candidate_rewards": rewards,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": atoms,
        "normalized_atoms": atoms,
        "candidate_generation_contract": generation_contract,
        "camp_candidate_tensor_provenance": _provenance(
            candidate_count=candidate_count,
            selected_index=selected_index,
            **(provenance_overrides or {}),
        ),
    }


def _as_finite_number(value: object, *, field: str, errors: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{field}_not_numeric")
        return 0.0
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"{field}_not_finite")
        return 0.0
    return number


def _bool_cost(value: object, *, field: str, errors: list[str]) -> float:
    if not isinstance(value, bool):
        errors.append(f"{field}_not_bool")
        return 0.0
    return 1.0 if value else 0.0


def _costs(reward: dict[str, object], *, index: int, errors: list[str]) -> dict[str, float]:
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
    red = max(-_as_finite_number(reward["red_light"], field=f"reward_{index}_red_light", errors=errors), 0.0)
    lane = (
        _bool_cost(reward["lane_crossing"], field=f"reward_{index}_lane_crossing", errors=errors)
        + _bool_cost(reward["static_crossing"], field=f"reward_{index}_static_crossing", errors=errors)
        + _as_finite_number(reward["off_road_fraction"], field=f"reward_{index}_off_road_fraction", errors=errors)
        + _as_finite_number(reward["lane_near_frac"], field=f"reward_{index}_lane_near_frac", errors=errors)
        + _as_finite_number(reward["lane_wide_frac"], field=f"reward_{index}_lane_wide_frac", errors=errors)
        + max(-_as_finite_number(reward["centerline"], field=f"reward_{index}_centerline", errors=errors), 0.0)
    )
    quality = max(-_as_finite_number(reward["total"], field=f"reward_{index}_total", errors=errors), 0.0)
    return {"red": red, "lane": lane, "quality": quality}


def _reason_policy(reasons: list[list[str]]) -> tuple[str, str, str]:
    flat = {reason for per_candidate in reasons for reason in per_candidate}
    if "dp_red_light" in flat:
        return ("red", "lane", "quality")
    if flat & {"dp_lane_crossing", "lane_crossing", "dp_static_crossing"}:
        return ("lane", "red", "quality")
    return ("quality", "red", "lane")


def _decision(status: str, passed: bool, enabled: bool, errors: list[str]) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "enabled": enabled,
        "errors": errors,
        "dataset_builder_implementation_authorized": False,
        "fallback_risk_training_authorized_now": False,
        "fallback_risk_smoke_authorized_now": False,
        "feasible_ranking_master_change_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _reference_contract_report(
    records: list[dict[str, object]] | None,
    *,
    enabled: bool = False,
    margin_scale: float = 1.0,
    margin_clip: float = 100.0,
) -> dict[str, object]:
    if not enabled:
        return {
            "schema_version": "dp_native_fallback_risk_training_data_v1",
            "records": [],
            "final_decision": _decision(DISABLED_STATUS, True, False, []),
        }
    dataset_records: list[dict[str, object]] = []
    errors: list[str] = []
    for record_index, record in enumerate(records or []):
        feasible = record.get("feasible_mask")
        if not isinstance(feasible, list) or any(bool(value) for value in feasible):
            errors.append(f"record_{record_index}_feasible_branch_rejected")
            continue
        rewards = record.get("dp_candidate_rewards")
        if not isinstance(rewards, list):
            errors.append(f"record_{record_index}_dp_candidate_rewards_missing")
            continue
        candidate_count = len(rewards)
        selected_index = int(record.get("selected_index", -1))
        provenance = record.get("camp_candidate_tensor_provenance")
        if not isinstance(provenance, dict) or provenance.get("payload_valid") is not True:
            errors.append(f"record_{record_index}_provenance_invalid")
        if isinstance(provenance, dict) and provenance.get("pre_post_tensor_hash_equal") is not True:
            errors.append(f"record_{record_index}_tensor_hash_mismatch")
        generation = record.get("candidate_generation_contract")
        if not isinstance(generation, dict) or generation.get("reference_blend_steps") is not None:
            errors.append(f"record_{record_index}_candidate_generation_contract_rejected")
        if isinstance(generation, dict) and bool(generation.get("guidance_enabled")):
            errors.append(f"record_{record_index}_guidance_rejected")
        atoms = record.get("atoms")
        if not isinstance(atoms, list) or len(atoms) != candidate_count:
            errors.append(f"record_{record_index}_atoms_candidate_count_mismatch")
        elif any(
            not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0
            for row in atoms
            for value in row
        ):
            errors.append(f"record_{record_index}_atoms_not_finite_nonnegative")
        cost_rows = [
            _costs(reward, index=index, errors=errors)
            for index, reward in enumerate(rewards)
            if isinstance(reward, dict)
        ]
        if len(cost_rows) != candidate_count:
            errors.append(f"record_{record_index}_reward_row_invalid")
            continue
        reasons = record.get("infeasibility_reasons")
        if not isinstance(reasons, list):
            errors.append(f"record_{record_index}_reasons_missing")
            continue
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
                    * sum(max(value - oracle_tuple[pos], 0.0) for pos, value in enumerate(item[:3])),
                    0.0,
                ),
                margin_clip,
            )
            for item in ordered
        ]
        dataset_records.append(
            {
                "source_artifact_sha256": record.get("source_artifact_sha256"),
                "run_id": record.get("run_id"),
                "record_index": record.get("record_index"),
                "candidate_count": candidate_count,
                "selected_index": selected_index,
                "oracle_index": oracle_index,
                "oracle_policy": policy,
                "margins": margins,
                "training_authorized": False,
                "selected_index_used_as_feature": False,
                "candidate_rank_used_as_feature": False,
            }
        )
    return {
        "schema_version": "dp_native_fallback_risk_training_data_v1",
        "records": dataset_records,
        "final_decision": _decision(
            REJECT_STATUS if errors else COMPLETE_STATUS,
            not errors,
            True,
            errors,
        ),
    }


def test_contract_builder_is_default_off_and_does_not_read_records() -> None:
    report = _reference_contract_report(None, enabled=False)

    assert report["records"] == []
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True


def test_contract_filters_to_all_infeasible_records_only() -> None:
    report = _reference_contract_report(
        [_record(feasible_mask=[True, False])],
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "record_0_feasible_branch_rejected" in report["final_decision"]["errors"]
    assert report["final_decision"]["all_infeasible_records_added_to_feasible_training"] is False


def test_contract_reason_conditioned_oracle_policy_and_margins() -> None:
    red_report = _reference_contract_report(
        [
            _record(
                reasons=[["dp_red_light"], ["dp_red_light"]],
                rewards=[_reward(red_light=-3.0), _reward(red_light=-1.0)],
            )
        ],
        enabled=True,
    )
    lane_report = _reference_contract_report(
        [
            _record(
                reasons=[["dp_lane_crossing"], ["dp_lane_crossing"]],
                rewards=[
                    _reward(lane_crossing=True, red_light=-1.0),
                    _reward(lane_crossing=False, red_light=-5.0),
                ],
            )
        ],
        enabled=True,
    )
    quality_report = _reference_contract_report(
        [
            _record(
                reasons=[["dp_other"], ["dp_other"]],
                rewards=[_reward(total=-9.0), _reward(total=-1.0)],
            )
        ],
        enabled=True,
    )

    red_record = red_report["records"][0]
    lane_record = lane_report["records"][0]
    quality_record = quality_report["records"][0]
    assert red_record["oracle_index"] == 1
    assert red_record["oracle_policy"] == ("red", "lane", "quality")
    assert lane_record["oracle_index"] == 1
    assert lane_record["oracle_policy"] == ("lane", "red", "quality")
    assert quality_record["oracle_index"] == 1
    assert quality_record["oracle_policy"] == ("quality", "red", "lane")
    assert all(value >= 0.0 for value in red_record["margins"])


def test_contract_fails_closed_on_missing_costs_and_mutation_paths() -> None:
    bad_reward = _reward(red_light="bad")
    del bad_reward["centerline"]
    report = _reference_contract_report(
        [
            _record(
                rewards=[bad_reward, _reward()],
                provenance_overrides={"pre_post_tensor_hash_equal": False},
                generation_overrides={"guidance_enabled": True},
            )
        ],
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "reward_0_missing_fields:centerline" in errors
    assert "record_0_tensor_hash_mismatch" in errors
    assert "record_0_guidance_rejected" in errors


def test_contract_rejects_negative_atoms_and_forbids_training() -> None:
    report = _reference_contract_report(
        [_record(atoms=[[-0.1 for _ in range(9)], [0.1 for _ in range(9)]])],
        enabled=True,
    )
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert "record_0_atoms_not_finite_nonnegative" in decision["errors"]
    for flag in [
        "replay_execution_authorized",
        "candidate_generation_authorized",
        "camp_training_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ]:
        assert decision[flag] is False


def test_iteration_audit_records_builder_unit_tests_current_head_history() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-105:])
    current_head = "3fe7714f66bfd756761b9f2d95ea3c6eb07ef0c4"

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_unit_tests_current_head_revalidated_latest",
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_builder_unit_tests_plan_status=fallback_risk_training_data_default_off_builder_unit_tests_plan_current_head_revalidated_latest",
        "prior_builder_unit_tests_plan_tail_verified=True",
        "prior_builder_unit_tests_plan_autodl_verified=True",
        "contract_test_file=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_contract.py",
        "plan_test_file=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_unit_tests_plan.py",
        "production_builder_file=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py",
        "local_py_compile_exit=0",
        "local_target_pytest=68 passed",
        "local_git_diff_check_exit=0",
        "synthetic_records_only=True",
        "default_off_disabled_status_pinned=True",
        "all_infeasible_scope_pinned=True",
        "reason_conditioned_oracle_policy_pinned=True",
        "nonnegative_margin_contract_pinned=True",
        "missing_costs_fail_closed_pinned=True",
        "provenance_mutation_rejection_pinned=True",
        "negative_atom_rejection_pinned=True",
        "training_and_promotion_forbidden_pinned=True",
        "production_builder_edited_in_this_gate=False",
        "production_builder_executed_in_this_gate=False",
        "dataset_builder_implementation_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "training_execution_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_AUTHORIZATION_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(f"`{NEXT_AUTHORIZATION_GATE}`")
