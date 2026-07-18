from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


PLAN_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_execution_plan_v2"
RUN_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_run_v1"
TERMINAL_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_terminal_v1"
EXPECTED_SEED = 25001
TICKS_PER_RUN = 64
MAX_UNIQUE_IDENTITIES = 320
PHYSICAL_PARAMETER_FIELDS = (
    "crossing_speed_mps",
    "deceleration_mps2",
    "ego_speed_mps",
    "headway_m",
    "lateral_offset_m",
    "lateral_speed_mps",
    "other_speed_mps",
    "trigger_time_s",
)


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _physical_k8_payload(
    case: Mapping[str, Any], source_row: Mapping[str, Any]
) -> dict[str, Any]:
    """Return an ID-free, outcome-free payload for tie-equivalence proof."""

    route_spec = case.get("route_spec")
    if type(route_spec) is not dict:
        raise ValueError("bounded plan route_spec must be an exact object")
    actors = case.get("actors")
    if type(actors) is not list:
        raise ValueError("bounded plan actors must be a list")
    actor_fields = (
        "agent_type",
        "initial_heading_rad",
        "initial_xy",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "length_m",
        "longitudinal_acceleration_mps2",
        "longitudinal_speed_mps",
        "route_normal",
        "route_tangent",
        "trigger_time_s",
        "wheelbase_m",
        "width_m",
    )
    physical_actors = []
    for actor in actors:
        if type(actor) is not dict or any(field not in actor for field in actor_fields):
            raise ValueError("bounded plan actor physical payload drifted")
        physical_actors.append({field: actor[field] for field in actor_fields})
    chain = source_row.get("source_chain")
    layout = source_row.get("id_free_tensor_layout")
    parameters = case.get("parameters")
    if (
        type(chain) is not dict
        or type(layout) is not dict
        or type(parameters) is not dict
        or set(parameters) != {*PHYSICAL_PARAMETER_FIELDS, "variant"}
        or type(parameters["variant"]) is not int
        or parameters["variant"] < 0
        or chain.get("scenario_id") != case.get("scenario_id")
    ):
        raise ValueError("bounded plan source-chain/layout payload drifted")
    physical_parameters = {
        field: parameters[field] for field in PHYSICAL_PARAMETER_FIELDS
    }
    # source_chain_sha256 signs the identity-bound scenario_id.  It is valid
    # authority evidence but not a physical K8 input, so prove equivalence from
    # the complete chain with only those two identity wrappers removed.
    physical_source_chain = {
        key: value
        for key, value in chain.items()
        if key not in {"scenario_id", "source_chain_sha256"}
    }
    payload = {
        "schema_version": "camp_dp_v25_a162_k8_relevant_physical_payload_v2",
        "family": case.get("family"),
        "tier": case.get("tier"),
        "semantic_variant": case.get("semantic_variant"),
        "physical_parameters_without_identity_variant": physical_parameters,
        "actors_in_formal_order_without_ids": physical_actors,
        "signal": case.get("signal"),
        "route_spec": {
            "start_pose": route_spec.get("start_pose"),
            "goal_pose": route_spec.get("goal_pose"),
            "lanelet_ids": route_spec.get("lanelet_ids"),
            "route_length_m": route_spec.get("route_length_m"),
        },
        "route_identity_sha256": case.get("route_identity_sha256"),
        "source_map_sha256": case.get("source_map_sha256"),
        "seed": EXPECTED_SEED,
        "source_class": source_row.get("source_class"),
        "phase_authority_mode": source_row.get("phase_authority_mode"),
        "source_chain_physical_contract_sha256": canonical_sha256(
            physical_source_chain
        ),
        "id_free_tensor_layout_sha256": layout.get("layout_sha256"),
        "fixed_candidate_contract": "sequential_fixed_dp_k8_same_forward",
    }
    serialized = json.dumps(payload, sort_keys=True).lower()
    if any(
        forbidden in serialized
        for forbidden in (
            "outcome",
            "fresh",
            "holdout",
            "selected_index",
            "dp_private_latent",
        )
    ):
        raise ValueError("bounded plan physical payload contains a forbidden source")
    return payload


def build_route_level_bounded_execution_plan(
    *,
    formal_train: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    source_root_sha256: str,
    source_review_root_sha256: str,
) -> dict[str, Any]:
    if not _is_sha256(source_root_sha256) or not _is_sha256(
        source_review_root_sha256
    ):
        raise ValueError("bounded plan source roots must be SHA256 digests")
    rows = {str(row.get("scenario_id")): row for row in source_rows}
    if len(rows) != len(source_rows) or len(formal_train) != len(source_rows):
        raise ValueError("bounded plan formal/source denominator drifted")
    cases = {str(case.get("scenario_id")): case for case in formal_train}
    if len(cases) != len(formal_train) or set(cases) != set(rows):
        raise ValueError("bounded plan formal/source identities drifted")
    executable = [
        case for case in formal_train if case.get("runner_eligible") is True
    ]
    if not executable:
        raise ValueError("bounded plan executable universe is empty")
    if any(case.get("seeds") != [EXPECTED_SEED] for case in executable):
        raise ValueError("bounded plan executable seed drifted")

    def tie(case: Mapping[str, Any]) -> tuple[str, str, str]:
        row = rows[str(case["scenario_id"])]
        return (
            str(row["source_chain"]["semantic_clone_sha256"]),
            str(case["route_identity_sha256"]),
            str(case["scenario_id"]),
        )

    mapped = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "mapped_signal"
    ]
    no_signal = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "no_signal"
    ]
    if len(mapped) + len(no_signal) != len(executable):
        raise ValueError("bounded plan source class drifted")
    selected = {str(case["scenario_id"]): case for case in mapped}
    primary: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    for case in no_signal:
        key = (
            str(case["family"]),
            str(case["semantic_variant"]),
            str(case["tier"]),
            str(case["source_map_sha256"]),
        )
        primary.setdefault(key, []).append(case)

    tie_proofs: list[dict[str, Any]] = []
    for key, group in sorted(primary.items()):
        chosen = min(group, key=tie)
        selected[str(chosen["scenario_id"])] = chosen
        first_two = tie(chosen)[:2]
        terminal = [case for case in group if tie(case)[:2] == first_two]
        if len(terminal) > 1:
            payloads = [
                _physical_k8_payload(case, rows[str(case["scenario_id"])])
                for case in terminal
            ]
            hashes = [canonical_sha256(payload) for payload in payloads]
            equivalent = len(set(hashes)) == 1
            if not equivalent:
                for case in terminal:
                    selected[str(case["scenario_id"])] = case
            tie_proofs.append(
                {
                    "primary_cell": list(key),
                    "terminal_scenario_ids": sorted(
                        str(case["scenario_id"]) for case in terminal
                    ),
                    "route_identity_sha256": first_two[1],
                    "semantic_clone_sha256": first_two[0],
                    "k8_relevant_physical_payload_sha256": hashes,
                    "all_terminal_items_equivalent": equivalent,
                    "non_equivalent_items_all_included": not equivalent,
                }
            )

    def augment(field) -> None:
        universe = {field(case) for case in no_signal}
        covered = {
            field(case)
            for case in no_signal
            if str(case["scenario_id"]) in selected
        }
        for value in sorted(universe - covered):
            candidates = [case for case in no_signal if field(case) == value]
            chosen = min(candidates, key=tie)
            selected[str(chosen["scenario_id"])] = chosen

    augment(lambda case: str(case["corridor_group_sha256"]))
    augment(
        lambda case: str(
            rows[str(case["scenario_id"])]["id_free_tensor_layout"][
                "layout_sha256"
            ]
        )
    )
    identity0 = executable[0]
    selected[str(identity0["scenario_id"])] = identity0
    selected_cases = sorted(selected.values(), key=tie)
    if len(selected_cases) > MAX_UNIQUE_IDENTITIES:
        raise ValueError("bounded plan exceeds the 320-identity hard cap")
    selected_ids = [str(case["scenario_id"]) for case in selected_cases]
    identity0_id = str(identity0["scenario_id"])
    middle = [scenario_id for scenario_id in selected_ids if scenario_id != identity0_id]
    sequence_ids = [identity0_id, *middle, identity0_id]
    runs = []
    for ordinal, scenario_id in enumerate(sequence_ids):
        case = cases[scenario_id]
        row = rows[scenario_id]
        occurrence = (
            "identity0_first"
            if ordinal == 0
            else "identity0_final_repeat"
            if ordinal == len(sequence_ids) - 1
            else "unique_identity"
        )
        runs.append(
            {
                "run_ordinal": ordinal,
                "scenario_id": scenario_id,
                "occurrence": occurrence,
                "ticks": TICKS_PER_RUN,
                "seed": EXPECTED_SEED,
                "source_class": row["source_class"],
                "phase_authority_mode": row["phase_authority_mode"],
                "route_identity_sha256": case["route_identity_sha256"],
                "source_map_sha256": case["source_map_sha256"],
                "semantic_clone_sha256": row["source_chain"][
                    "semantic_clone_sha256"
                ],
                "source_row_sha256": canonical_sha256(row),
                "k8_relevant_physical_payload_sha256": canonical_sha256(
                    _physical_k8_payload(case, row)
                ),
            }
        )
    status = (
        "passed_preflight_plan_k8_execute_closed"
        if all(proof["all_terminal_items_equivalent"] for proof in tie_proofs)
        else "requires_ultra_review_after_non_equivalent_tie_expansion"
    )
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": status,
        "source_root_sha256": source_root_sha256,
        "source_review_root_sha256": source_review_root_sha256,
        "seed": EXPECTED_SEED,
        "ticks_per_run": TICKS_PER_RUN,
        "unique_identity_count": len(selected_cases),
        "run_count": len(runs),
        "snapshot_capacity": len(runs) * TICKS_PER_RUN,
        "mapped_identity_count": len(mapped),
        "no_signal_selected_count": len(selected_cases) - len(mapped),
        "identity0_scenario_id": identity0_id,
        "execution_order_contract": (
            "identity0_first_then_remaining_unique_then_identity0_final_repeat"
        ),
        "selection_contract": (
            "all_mapped_plus_outcome_blind_nosignal_cells_corridor_layout"
        ),
        "tie_break_contract": (
            "semantic_clone_sha256_route_identity_sha256_scenario_id"
        ),
        "tie_equivalence_proofs": tie_proofs,
        "runs": runs,
        "sequential_fixed_k8": True,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "normalization_contract": "clip(raw_atoms/generation_scales,0,10)",
        "selection_eligibility": "strict_source_valid_mask",
        "tie_break_selected_index": "lowest_eligible_candidate_index",
        "microbatch_enabled": False,
        "cache_optimization_enabled": False,
        "sharding_enabled": False,
        "k8_executed": False,
        "candidate_generation_started": False,
        "model_loaded": False,
        "simulator_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def validate_bounded_terminal_acceptance(
    plan: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    *,
    repeat_comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed unless every planned run completed exactly 64 ticks."""

    runs = plan.get("runs")
    if (
        plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or type(runs) is not list
        or type(results) is not list
        or len(results) != len(runs)
    ):
        raise ValueError("bounded terminal plan/result denominator drifted")
    exact_result_fields = {
        "run_ordinal",
        "scenario_id",
        "status",
        "tick_count",
        "retained_capability_failure",
        "failure_class",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    for expected, result in zip(runs, results):
        if (
            type(result) is not dict
            or set(result) != exact_result_fields
            or result.get("run_ordinal") != expected.get("run_ordinal")
            or result.get("scenario_id") != expected.get("scenario_id")
            or result.get("status") != "complete"
            or result.get("tick_count") != TICKS_PER_RUN
            or result.get("retained_capability_failure") is not None
            or result.get("failure_class") != "none"
            or result.get("fresh_b2_opened") is not False
            or result.get("outcome_fields_consumed") != []
        ):
            raise ValueError("bounded run was not an exact 64-tick completion")
    required_repeat_fields = {
        "candidate0_sha256_sequence_equal",
        "k8_row_sha256_sequence_equal",
        "atom_matrix_sequence_equal",
        "context_sequence_equal",
        "selected_index_sequence_equal",
        "failure_class_equal",
        "closed_loop_trajectory_equal",
        "speed_probe_equal",
    }
    if (
        type(repeat_comparison) is not dict
        or set(repeat_comparison) != required_repeat_fields
        or any(value is not True for value in repeat_comparison.values())
    ):
        raise ValueError("identity0 first/final determinism comparison failed")
    return {
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "status": "passed_exact_bounded_terminal",
        "run_count": len(results),
        "unique_identity_count": plan["unique_identity_count"],
        "tick_count": len(results) * TICKS_PER_RUN,
        "retained_capability_failure_count": 0,
        "mapped_runtime_source_failure_count": 0,
        "identity0_repeat_deterministic": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
