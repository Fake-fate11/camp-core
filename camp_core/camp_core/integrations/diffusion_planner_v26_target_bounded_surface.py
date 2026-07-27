"""Fail-closed V26 production-surface contract for the bounded runner.

This module deliberately adds no model, DP, selector, or support/OOD logic.
It only constrains the already-authorized target bounded runner and projects
its per-arm receipt into a zero-model contract that can be parser-tested.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

from camp_core.integrations.diffusion_planner_causal_atoms import (
    materialization_phase_receipt_not_available,
    validate_materialization_phase_receipt,
)


PRODUCTION_SURFACE_ID = (
    "camp_dp_v26_target_bounded_same_ego_single_invocation_b8_v1"
)
MANIFEST_SCHEMA_VERSION = "camp_dp_v26_target_bounded_production_manifest_v1"
TICK_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_target_bounded_tick_receipt_v1"
CLOSED_LOOP_COMPUTE_SCOPE = "per_arm_own_state_compute_matched"
SUPPORT_NOT_EVALUATED = "not_evaluated_no_frozen_reference"
ACTION_STABILITY_NOT_EVALUATED = "not_evaluated_no_preregistered_protocol"
V26_STAGE2_AUTHORITY_SCHEMA_VERSION = "camp_dp_v26_stage2_exact_allowlist_v1"

ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
SELECTOR_ARMS = ("Static14D", "Scene14D")

V26_STAGE2_IMPLEMENTATION_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py",
    "camp_core/camp_core/integrations/diffusion_planner_v26_target_bounded_surface.py",
    "scripts/integrations/run_diffusion_planner_v25_industrial_bounded_closed_loop.py",
    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
)
V26_STAGE2_FOCUSED_TEST_FILES = (
    "camp_core/tests/test_diffusion_planner_v18_orchestrator.py",
    "camp_core/tests/test_diffusion_planner_v26_target_bounded_surface.py",
)
V26_STAGE2_ALLOWED_CHANGED_FILES = (
    *V26_STAGE2_IMPLEMENTATION_FILES,
    *V26_STAGE2_FOCUSED_TEST_FILES,
)

_OPTION_NAMES = (
    "adaptation_diagnostics",
    "sequential_forward_enabled",
    "replay_extra_forward_enabled",
    "guidance_policy",
    "evaluate_all_arms",
)


def _require_sha256(value: Any, name: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA256 string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _require_git_commit(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError(f"{name} must be a full 40-character git commit")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _require_index(value: Any, name: str, *, allow_none: bool = False) -> int | None:
    if value is None and allow_none:
        return None
    if type(value) is not int or not 0 <= value < 8:
        raise ValueError(f"{name} must be an integer in [0,8)")
    return value


def _require_mask(value: Any, name: str, *, allow_none: bool = False) -> list[bool] | None:
    if value is None and allow_none:
        return None
    if type(value) is not list or len(value) != 8 or any(type(item) is not bool for item in value):
        raise ValueError(f"{name} must be a strict bool[8] list")
    return list(value)


def _require_margin(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("margin_best_vs_runner_up must be finite or null")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("margin_best_vs_runner_up must be finite or null")
    return result


def _require_tie_set(value: Any) -> list[int] | None:
    if value is None:
        return None
    if type(value) is not list or any(
        type(item) is not int or not 0 <= item < 8 for item in value
    ):
        raise ValueError("exact_tie_set must be an integer subset of frozen K8")
    return list(value)


def validate_production_surface_options(
    *,
    production_surface_id: str,
    options: Mapping[str, Any],
) -> dict[str, Any]:
    """Reject every extra-forward mode rather than silently changing policy."""

    if production_surface_id != PRODUCTION_SURFACE_ID:
        raise ValueError("V26 production surface id drifted")
    normalized = dict(options)
    if set(normalized) != set(_OPTION_NAMES):
        raise ValueError("V26 production surface options must be explicit and exact")
    if normalized["adaptation_diagnostics"] is not False:
        raise ValueError("V26 production surface rejects adaptation diagnostics")
    if normalized["sequential_forward_enabled"] is not False:
        raise ValueError("V26 production surface rejects sequential forwards")
    if normalized["replay_extra_forward_enabled"] is not False:
        raise ValueError("V26 production surface rejects replay extra forwards")
    if normalized["guidance_policy"] != "disabled":
        raise ValueError("V26 production surface requires disabled guidance policy")
    if normalized["evaluate_all_arms"] is not False:
        raise ValueError("V26 closed loop requires one operational arm per state")
    return normalized


def validate_v26_stage2_authority(
    *,
    baseline_implementation_head: str,
    live_implementation_head: str,
    baseline_is_ancestor: bool,
    changed_files: Sequence[str],
) -> dict[str, Any]:
    """Bind V26 production to the explicitly audited Stage-2 package only."""

    baseline = _require_git_commit(
        baseline_implementation_head, "baseline_implementation_head"
    )
    live = _require_git_commit(live_implementation_head, "live_implementation_head")
    if baseline == live or baseline_is_ancestor is not True:
        raise ValueError("V26 Stage-2 authority requires an advanced ancestor head")
    if type(changed_files) not in (list, tuple) or any(
        type(path) is not str for path in changed_files
    ):
        raise ValueError("V26 Stage-2 changed_files must be a strict path list")
    normalized_changed_files = tuple(sorted(changed_files))
    if normalized_changed_files != tuple(sorted(V26_STAGE2_ALLOWED_CHANGED_FILES)):
        raise ValueError("V26 Stage-2 change allowlist drifted")
    return {
        "schema_version": V26_STAGE2_AUTHORITY_SCHEMA_VERSION,
        "authority_route": "versioned_v26_stage2_exact_allowlist",
        "baseline_implementation_head": baseline,
        "live_implementation_head": live,
        "baseline_is_ancestor": True,
        "allowed_changed_files": list(V26_STAGE2_ALLOWED_CHANGED_FILES),
        "changed_files": list(normalized_changed_files),
    }


def production_surface_manifest(
    *,
    production_surface_id: str,
    options: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = validate_production_surface_options(
        production_surface_id=production_surface_id,
        options=options,
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "production_surface_id": production_surface_id,
        "execution_options": normalized,
        "closed_loop_compute_scope": CLOSED_LOOP_COMPUTE_SCOPE,
        "candidate_pool_contract": {
            "same_ego_batch_size": 8,
            "primary_forward_count": 1,
            "sequential_forward_count": 0,
            "candidate0_row": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "prospective_claims": {
            "support_status": SUPPORT_NOT_EVALUATED,
            "ood_status": SUPPORT_NOT_EVALUATED,
            "action_stability_status": ACTION_STABILITY_NOT_EVALUATED,
            "selected_action_identity_is_action_stability": False,
        },
    }


def validate_production_surface_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "schema_version",
        "production_surface_id",
        "execution_options",
        "closed_loop_compute_scope",
        "candidate_pool_contract",
        "prospective_claims",
    }
    if set(result) != expected:
        raise ValueError("V26 production manifest field set drifted")
    if result["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError("V26 production manifest schema drifted")
    options = validate_production_surface_options(
        production_surface_id=result["production_surface_id"],
        options=result["execution_options"],
    )
    if result["closed_loop_compute_scope"] != CLOSED_LOOP_COMPUTE_SCOPE:
        raise ValueError("V26 closed-loop compute scope drifted")
    expected_pool_contract = production_surface_manifest(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options=options,
    )["candidate_pool_contract"]
    if result["candidate_pool_contract"] != expected_pool_contract:
        raise ValueError("V26 candidate-pool contract drifted")
    expected_claims = production_surface_manifest(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options=options,
    )["prospective_claims"]
    if result["prospective_claims"] != expected_claims:
        raise ValueError("V26 prospective-claim boundary drifted")
    return result


def prospective_support_ood_receipt(
    *,
    state_unit_id: str,
    candidate_unit_id: str,
) -> dict[str, Any]:
    _require_sha256(state_unit_id, "state_unit_id")
    _require_sha256(candidate_unit_id, "candidate_unit_id")
    return {
        "frozen_reference_id": None,
        "frozen_reference_hash": None,
        "reference_scope": "not_available_no_frozen_reference",
        "state_unit": {"kind": "per_arm_own_state", "id": state_unit_id},
        "candidate_unit": {
            "kind": "frozen_same_ego_k8_candidate_pool",
            "id": candidate_unit_id,
        },
        "support_status": SUPPORT_NOT_EVALUATED,
        "ood_status": SUPPORT_NOT_EVALUATED,
    }


def validate_prospective_support_ood_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "frozen_reference_id",
        "frozen_reference_hash",
        "reference_scope",
        "state_unit",
        "candidate_unit",
        "support_status",
        "ood_status",
    }
    if set(result) != expected:
        raise ValueError("V26 prospective support/OOD receipt field set drifted")
    if result["frozen_reference_id"] is not None or result["frozen_reference_hash"] is not None:
        raise ValueError("V26 support/OOD skeleton has no frozen reference")
    if result["reference_scope"] != "not_available_no_frozen_reference":
        raise ValueError("V26 support/OOD reference scope drifted")
    for name, expected_kind in (
        ("state_unit", "per_arm_own_state"),
        ("candidate_unit", "frozen_same_ego_k8_candidate_pool"),
    ):
        unit = result[name]
        if type(unit) is not dict or unit.get("kind") != expected_kind:
            raise ValueError(f"V26 {name} contract drifted")
        _require_sha256(unit.get("id"), f"{name}.id")
    if (
        result["support_status"] != SUPPORT_NOT_EVALUATED
        or result["ood_status"] != SUPPORT_NOT_EVALUATED
    ):
        raise ValueError("V26 support/OOD claim requires a frozen reference")
    return result


def prospective_action_stability_receipt(
    *,
    base_state_id: str,
    candidate_pool_sha256: str,
    selected_index: int | None,
    selected_row_sha256: str | None,
    source_valid_mask: list[bool] | None,
    margin_best_vs_runner_up: float | None,
) -> dict[str, Any]:
    _require_sha256(base_state_id, "base_state_id")
    _require_sha256(candidate_pool_sha256, "candidate_pool_sha256")
    selected_index = _require_index(
        selected_index, "selected_index", allow_none=True
    )
    selected_row_sha256 = _require_sha256(
        selected_row_sha256, "selected_row_sha256", allow_none=True
    )
    if (selected_index is None) != (selected_row_sha256 is None):
        raise ValueError("V26 action identity must be fully present or unavailable")
    return {
        "preregistered_protocol_id": None,
        "base_state_id": base_state_id,
        "replicate_or_perturbation_id": None,
        "pool_identity": candidate_pool_sha256,
        "action_identity": {
            "selected_index": selected_index,
            "selected_row_sha256": selected_row_sha256,
        },
        "source_valid_mask": _require_mask(
            source_valid_mask, "source_valid_mask", allow_none=True
        ),
        "margin_best_vs_runner_up": _require_margin(margin_best_vs_runner_up),
        "action_stability_status": ACTION_STABILITY_NOT_EVALUATED,
        "selected_action_identity_is_action_stability": False,
    }


def validate_prospective_action_stability_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "preregistered_protocol_id",
        "base_state_id",
        "replicate_or_perturbation_id",
        "pool_identity",
        "action_identity",
        "source_valid_mask",
        "margin_best_vs_runner_up",
        "action_stability_status",
        "selected_action_identity_is_action_stability",
    }
    if set(result) != expected:
        raise ValueError("V26 prospective action-stability field set drifted")
    if (
        result["preregistered_protocol_id"] is not None
        or result["replicate_or_perturbation_id"] is not None
    ):
        raise ValueError("V26 action-stability skeleton has no preregistered protocol")
    _require_sha256(result["base_state_id"], "base_state_id")
    _require_sha256(result["pool_identity"], "pool_identity")
    action = result["action_identity"]
    if type(action) is not dict or set(action) != {
        "selected_index",
        "selected_row_sha256",
    }:
        raise ValueError("V26 action identity field set drifted")
    selected_index = _require_index(
        action["selected_index"], "selected_index", allow_none=True
    )
    selected_row_sha256 = _require_sha256(
        action["selected_row_sha256"], "selected_row_sha256", allow_none=True
    )
    if (selected_index is None) != (selected_row_sha256 is None):
        raise ValueError("V26 action identity must be fully present or unavailable")
    _require_mask(result["source_valid_mask"], "source_valid_mask", allow_none=True)
    _require_margin(result["margin_best_vs_runner_up"])
    if result["action_stability_status"] != ACTION_STABILITY_NOT_EVALUATED:
        raise ValueError("V26 action-stability claim requires a preregistered protocol")
    if result["selected_action_identity_is_action_stability"] is not False:
        raise ValueError("selected-action identity must not be labeled action stability")
    return result


def _selector_projection(
    *,
    operational_arm: str,
    pool_sha256: str,
    selector_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(selector_receipt)
    if operational_arm not in ARMS:
        raise ValueError("V26 operational arm drifted")
    status = raw.get("status")
    if type(status) is not str:
        raise ValueError("V26 selector status must be explicit")
    selected_index = _require_index(
        raw.get("selected_index"), "selector.selected_index", allow_none=True
    )
    selected_row_sha256 = _require_sha256(
        raw.get("selected_row_sha256"),
        "selector.selected_row_sha256",
        allow_none=True,
    )
    if (selected_index is None) != (selected_row_sha256 is None):
        raise ValueError("V26 selector action identity must be fully present or unavailable")
    if status == "ok":
        if selected_index is None or selected_row_sha256 is None:
            raise ValueError("V26 successful selector requires a frozen action identity")
    elif selected_index is not None or selected_row_sha256 is not None:
        raise ValueError("V26 unsuccessful selector cannot expose an action identity")
    if operational_arm in SELECTOR_ARMS:
        physical = _require_mask(
            raw.get("physical_feasible_mask"), "selector.physical_feasible_mask"
        )
        source = _require_mask(
            raw.get("source_valid_mask"), "selector.source_valid_mask"
        )
        margin = _require_margin(raw.get("margin_best_vs_runner_up"))
        tie_set = _require_tie_set(raw.get("exact_tie_set"))
    else:
        if status == "ok" and selected_index != 0:
            raise ValueError("V26 baseline selector must select candidate row0")
        physical = _require_mask(
            raw.get("physical_feasible_mask"),
            "selector.physical_feasible_mask",
            allow_none=True,
        )
        source = _require_mask(
            raw.get("source_valid_mask"),
            "selector.source_valid_mask",
            allow_none=True,
        )
        margin = None
        tie_set = None
    return {
        "operational_arm": operational_arm,
        "pool_sha256": pool_sha256,
        "status": status,
        "physical_feasible_mask": physical,
        "source_valid_mask": source,
        "margin_best_vs_runner_up": margin,
        "exact_tie_set": tie_set,
        "selected_index": selected_index,
        "selected_row_sha256": selected_row_sha256,
    }


def build_target_bounded_tick_receipt(
    *,
    production_surface_id: str,
    options: Mapping[str, Any],
    operational_arm: str,
    tick_index: int,
    state_sha256: str,
    candidate_pool_sha256_before: str,
    candidate_pool_sha256_after: str,
    primary_forward_count: int,
    sequential_forward_count: int,
    zero_call_receipt: Mapping[str, Any],
    selector_receipt: Mapping[str, Any],
    simulator_selected_row_sha256: str | None,
    materialization_phase_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_production_surface_options(
        production_surface_id=production_surface_id,
        options=options,
    )
    if type(tick_index) is not int or tick_index < 0:
        raise ValueError("V26 tick_index must be a nonnegative integer")
    _require_sha256(state_sha256, "state_sha256")
    before = _require_sha256(
        candidate_pool_sha256_before, "candidate_pool_sha256_before"
    )
    after = _require_sha256(
        candidate_pool_sha256_after, "candidate_pool_sha256_after"
    )
    if before != after:
        raise ValueError("V26 frozen candidate pool was mutated")
    if primary_forward_count != 1 or sequential_forward_count != 0:
        raise ValueError("V26 forward topology drifted")
    zero = dict(zero_call_receipt)
    if (
        zero.get("dp_or_model_calls_after_pool") != 0
        or zero.get("latent_replacements_after_pool") != 0
        or zero.get("candidate_generations_after_pool") != 0
    ):
        raise ValueError("V26 post-pool call receipt drifted")
    selector = _selector_projection(
        operational_arm=operational_arm,
        pool_sha256=before,
        selector_receipt=selector_receipt,
    )
    selected_index = selector["selected_index"]
    selected_row_sha256 = selector["selected_row_sha256"]
    simulator_sha = _require_sha256(
        simulator_selected_row_sha256,
        "simulator_selected_row_sha256",
        allow_none=True,
    )
    if selector["status"] == "ok":
        if (
            selected_index is None
            or selected_row_sha256 is None
            or simulator_sha is None
            or simulator_sha != selected_row_sha256
        ):
            raise ValueError("V26 simulator row must be the selected frozen candidate row")
        simulator = {
            "status": "matched_frozen_selected_row",
            "selected_index": selected_index,
            "candidate_row_sha256": selected_row_sha256,
            "simulator_row_sha256": simulator_sha,
            "matches_candidate_row": True,
        }
    else:
        if (
            selected_index is not None
            or selected_row_sha256 is not None
            or simulator_sha is not None
        ):
            raise ValueError("selector failure cannot expose action identity or simulator row")
        simulator = {
            "status": "not_available_selector_failure",
            "selected_index": None,
            "candidate_row_sha256": None,
            "simulator_row_sha256": None,
            "matches_candidate_row": False,
        }
    phases = (
        materialization_phase_receipt_not_available()
        if materialization_phase_receipt is None
        else validate_materialization_phase_receipt(materialization_phase_receipt)
    )
    result = {
        "schema_version": TICK_RECEIPT_SCHEMA_VERSION,
        "production_surface_id": production_surface_id,
        "closed_loop_compute_scope": CLOSED_LOOP_COMPUTE_SCOPE,
        "tick_index": tick_index,
        "state_sha256": state_sha256,
        "candidate_pool": {
            "pool_sha256": before,
            "candidate0_row": 0,
            "candidate_pool_mutation_count": 0,
        },
        "forward_topology": {
            "primary_forward_count": 1,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "selector": selector,
        "simulator_selected_row": simulator,
        "atom_materialization_phase_receipt": phases,
        "prospective_support_ood": prospective_support_ood_receipt(
            state_unit_id=state_sha256,
            candidate_unit_id=before,
        ),
        "prospective_action_stability": prospective_action_stability_receipt(
            base_state_id=state_sha256,
            candidate_pool_sha256=before,
            selected_index=selected_index,
            selected_row_sha256=selected_row_sha256,
            source_valid_mask=selector["source_valid_mask"],
            margin_best_vs_runner_up=selector["margin_best_vs_runner_up"],
        ),
    }
    return validate_target_bounded_tick_receipt(result)


def validate_target_bounded_tick_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "schema_version",
        "production_surface_id",
        "closed_loop_compute_scope",
        "tick_index",
        "state_sha256",
        "candidate_pool",
        "forward_topology",
        "selector",
        "simulator_selected_row",
        "atom_materialization_phase_receipt",
        "prospective_support_ood",
        "prospective_action_stability",
    }
    if set(result) != expected or any("cross_arm" in key for key in result):
        raise ValueError("V26 tick receipt must not contain cross-arm equality fields")
    if result["schema_version"] != TICK_RECEIPT_SCHEMA_VERSION:
        raise ValueError("V26 tick receipt schema drifted")
    if result["production_surface_id"] != PRODUCTION_SURFACE_ID:
        raise ValueError("V26 tick receipt production surface drifted")
    if result["closed_loop_compute_scope"] != CLOSED_LOOP_COMPUTE_SCOPE:
        raise ValueError("V26 tick receipt compute scope drifted")
    if type(result["tick_index"]) is not int or result["tick_index"] < 0:
        raise ValueError("V26 tick receipt index drifted")
    _require_sha256(result["state_sha256"], "state_sha256")
    pool = result["candidate_pool"]
    if type(pool) is not dict or set(pool) != {
        "pool_sha256",
        "candidate0_row",
        "candidate_pool_mutation_count",
    }:
        raise ValueError("V26 candidate-pool receipt field set drifted")
    _require_sha256(pool["pool_sha256"], "pool_sha256")
    if pool["candidate0_row"] != 0 or pool["candidate_pool_mutation_count"] != 0:
        raise ValueError("V26 candidate-pool invariants drifted")
    topology = result["forward_topology"]
    expected_topology = {
        "primary_forward_count": 1,
        "sequential_forward_count": 0,
        "post_pool_model_forward_count": 0,
        "post_pool_dp_forward_count": 0,
        "post_pool_latent_replacement_count": 0,
        "post_pool_candidate_generation_count": 0,
        "trajectory_regeneration_count": 0,
    }
    if topology != expected_topology:
        raise ValueError("V26 forward topology receipt drifted")
    selector = result["selector"]
    if type(selector) is not dict or set(selector) != {
        "operational_arm",
        "pool_sha256",
        "status",
        "physical_feasible_mask",
        "source_valid_mask",
        "margin_best_vs_runner_up",
        "exact_tie_set",
        "selected_index",
        "selected_row_sha256",
    }:
        raise ValueError("V26 selector receipt field set drifted")
    if selector["operational_arm"] not in ARMS:
        raise ValueError("V26 selector arm drifted")
    if selector["pool_sha256"] != pool["pool_sha256"]:
        raise ValueError("V26 selector pool binding drifted")
    _require_sha256(selector["pool_sha256"], "selector.pool_sha256")
    if type(selector["status"]) is not str:
        raise ValueError("V26 selector status drifted")
    selected_index = _require_index(
        selector["selected_index"], "selector.selected_index", allow_none=True
    )
    selected_row_sha256 = _require_sha256(
        selector["selected_row_sha256"],
        "selector.selected_row_sha256",
        allow_none=True,
    )
    if (selected_index is None) != (selected_row_sha256 is None):
        raise ValueError("V26 selector action identity drifted")
    if selector["status"] == "ok":
        if selected_index is None or selected_row_sha256 is None:
            raise ValueError("V26 successful selector requires a frozen action identity")
    elif selected_index is not None or selected_row_sha256 is not None:
        raise ValueError("V26 unsuccessful selector cannot expose an action identity")
    if selector["operational_arm"] in SELECTOR_ARMS:
        _require_mask(selector["physical_feasible_mask"], "selector.physical_feasible_mask")
        _require_mask(selector["source_valid_mask"], "selector.source_valid_mask")
        _require_margin(selector["margin_best_vs_runner_up"])
        _require_tie_set(selector["exact_tie_set"])
    else:
        if selector["status"] == "ok" and selected_index != 0:
            raise ValueError("V26 baseline selected index drifted")
        _require_mask(
            selector["physical_feasible_mask"],
            "selector.physical_feasible_mask",
            allow_none=True,
        )
        _require_mask(
            selector["source_valid_mask"],
            "selector.source_valid_mask",
            allow_none=True,
        )
        if selector["margin_best_vs_runner_up"] is not None or selector["exact_tie_set"] is not None:
            raise ValueError("V26 baseline must not emit selector margin/tie")
    simulator = result["simulator_selected_row"]
    if type(simulator) is not dict or set(simulator) != {
        "status",
        "selected_index",
        "candidate_row_sha256",
        "simulator_row_sha256",
        "matches_candidate_row",
    }:
        raise ValueError("V26 simulator row receipt field set drifted")
    simulator_index = _require_index(
        simulator["selected_index"], "simulator.selected_index", allow_none=True
    )
    simulator_candidate_sha = _require_sha256(
        simulator["candidate_row_sha256"],
        "simulator.candidate_row_sha256",
        allow_none=True,
    )
    simulator_row_sha = _require_sha256(
        simulator["simulator_row_sha256"],
        "simulator.simulator_row_sha256",
        allow_none=True,
    )
    if selector["status"] == "ok":
        if (
            simulator_index is None
            or simulator_candidate_sha is None
            or simulator_row_sha is None
        ):
            raise ValueError("V26 successful selector requires a simulator action binding")
        if simulator != {
            "status": "matched_frozen_selected_row",
            "selected_index": selected_index,
            "candidate_row_sha256": selected_row_sha256,
            "simulator_row_sha256": selected_row_sha256,
            "matches_candidate_row": True,
        }:
            raise ValueError("V26 simulator row correspondence drifted")
    else:
        if (
            simulator_index is not None
            or simulator_candidate_sha is not None
            or simulator_row_sha is not None
            or simulator
            != {
                "status": "not_available_selector_failure",
                "selected_index": None,
                "candidate_row_sha256": None,
                "simulator_row_sha256": None,
                "matches_candidate_row": False,
            }
        ):
            raise ValueError("V26 selector failure simulator receipt drifted")
    validate_materialization_phase_receipt(result["atom_materialization_phase_receipt"])
    validate_prospective_support_ood_receipt(result["prospective_support_ood"])
    action = validate_prospective_action_stability_receipt(
        result["prospective_action_stability"]
    )
    if (
        action["base_state_id"] != result["state_sha256"]
        or action["pool_identity"] != pool["pool_sha256"]
        or action["action_identity"]["selected_index"] != selected_index
        or action["action_identity"]["selected_row_sha256"] != selected_row_sha256
        or action["source_valid_mask"] != selector["source_valid_mask"]
        or action["margin_best_vs_runner_up"] != selector["margin_best_vs_runner_up"]
    ):
        raise ValueError("V26 prospective action-stability binding drifted")
    return result
