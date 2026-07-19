from __future__ import annotations

import collections
import hashlib
import json
import math
from typing import Any, Mapping, Sequence


PLAN_SCHEMA_VERSION = "camp_dp_v25_a17_route_level_bounded_execution_plan_v3"
RUN_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_run_v1"
TERMINAL_SCHEMA_VERSION = "camp_dp_v25_a17_route_level_bounded_terminal_v3"
RUN_EVIDENCE_SCHEMA_VERSION = "camp_dp_v25_a17_bounded_run_evidence_v2"
RESULT_SCHEMA_VERSION = "camp_dp_v25_a17_bounded_result_v2"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FIXED_DP_FAILURE_CLASS = "fixed_dp_candidate_generation_capability_failure"
FIXED_DP_FAILURE_REASON = "invalid_k8_heading_norm_envelope"
FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_a17_fixed_dp_candidate_generation_capability_failure_v1"
)
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
                "family": case["family"],
                "tier": case["tier"],
                "route_identity_sha256": case["route_identity_sha256"],
                "source_map_sha256": case["source_map_sha256"],
                "corridor_group_sha256": case["corridor_group_sha256"],
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
    run_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive terminal/repeat acceptance from actual per-run evidence.

    The caller may not supply pass/fail booleans for the identity0 repeat.  It
    must provide the frozen sequences and projections produced by every run;
    this function validates their exact schema and computes all eight equality
    decisions itself.  The independent post-run reviewer rebuilds the same
    evidence from sealed raw snapshots and native receipts.
    """

    runs = plan.get("runs")
    if (
        plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or type(runs) is not list
        or type(results) is not list
        or type(run_evidence) is not list
        or len(results) != len(runs)
        or len(run_evidence) != len(runs)
    ):
        raise ValueError("bounded terminal plan/result denominator drifted")
    exact_result_fields = {
        "schema_version",
        "run_ordinal",
        "scenario_id",
        "occurrence",
        "status",
        "tick_count",
        "retained_capability_failure",
        "failure_class",
        "fresh_b2_opened",
        "outcome_fields_consumed",
        "family",
        "tier",
        "source_class",
        "phase_authority_mode",
        "source_map_sha256",
        "corridor_group_sha256",
    }
    evidence_fields = {
        "schema_version",
        "run_ordinal",
        "scenario_id",
        "occurrence",
        "tick_count",
        "candidate0_sha256_sequence",
        "k8_row_sha256_sequence",
        "atom_matrix_sha256_sequence",
        "context_sha256_sequence",
        "selected_index_sequence",
        "failure_class",
        "closed_loop_trajectory_sha256",
        "speed_probe_sha256",
        "capability_failure_sha256",
    }

    def sha256(value: Any) -> bool:
        return _is_sha256(value)

    complete_run_count = 0
    retained_run_count = 0
    unique_results: dict[str, Mapping[str, Any]] = {}
    for expected, result, evidence in zip(runs, results, run_evidence):
        status = result.get("status") if type(result) is dict else None
        complete = status == "complete"
        retained = status == "retained_fixed_dp_capability_failure"
        if (
            type(result) is not dict
            or set(result) != exact_result_fields
            or result.get("schema_version") != RESULT_SCHEMA_VERSION
            or result.get("run_ordinal") != expected.get("run_ordinal")
            or result.get("scenario_id") != expected.get("scenario_id")
            or result.get("occurrence") != expected.get("occurrence")
            or result.get("source_class") != expected.get("source_class")
            or result.get("phase_authority_mode")
            != expected.get("phase_authority_mode")
            or result.get("family") != expected.get("family")
            or result.get("tier") != expected.get("tier")
            or result.get("source_map_sha256")
            != expected.get("source_map_sha256")
            or result.get("corridor_group_sha256")
            != expected.get("corridor_group_sha256")
            or not (complete or retained)
            or result.get("tick_count") != (TICKS_PER_RUN if complete else 0)
            or (
                complete
                and (
                    result.get("retained_capability_failure") is not None
                    or result.get("failure_class") != "none"
                )
            )
            or (
                retained
                and (
                    result.get("failure_class") != FIXED_DP_FAILURE_CLASS
                    or not _validate_fixed_dp_failure_receipt(
                        result.get("retained_capability_failure"),
                        result=result,
                    )
                    or result["retained_capability_failure"].get(
                        "route_identity_sha256"
                    )
                    != expected.get("route_identity_sha256")
                )
            )
            or result.get("fresh_b2_opened") is not False
            or result.get("outcome_fields_consumed") != []
        ):
            raise ValueError("bounded run terminal contract drifted")
        scenario_id = str(result["scenario_id"])
        prior = unique_results.get(scenario_id)
        if prior is not None and (
            result.get("occurrence") != "identity0_final_repeat"
            or prior.get("occurrence") != "identity0_first"
            or prior.get("status") != "complete"
            or result.get("status") != "complete"
        ):
            raise ValueError("bounded duplicate identity terminal drifted")
        unique_results.setdefault(scenario_id, result)
        complete_run_count += int(complete)
        retained_run_count += int(retained)
        if (
            type(evidence) is not dict
            or set(evidence) != evidence_fields
            or evidence.get("schema_version") != RUN_EVIDENCE_SCHEMA_VERSION
            or evidence.get("run_ordinal") != expected.get("run_ordinal")
            or evidence.get("scenario_id") != expected.get("scenario_id")
            or evidence.get("occurrence") != expected.get("occurrence")
            or type(evidence.get("tick_count")) is not int
            or evidence["tick_count"] != (TICKS_PER_RUN if complete else 0)
            or evidence.get("failure_class") != result.get("failure_class")
            or any(
                type(evidence.get(field)) is not list
                or len(evidence[field]) != (TICKS_PER_RUN if complete else 0)
                for field in (
                    "candidate0_sha256_sequence",
                    "k8_row_sha256_sequence",
                    "atom_matrix_sha256_sequence",
                    "context_sha256_sequence",
                    "selected_index_sequence",
                )
            )
            or any(
                not sha256(value)
                for field in (
                    "candidate0_sha256_sequence",
                    "atom_matrix_sha256_sequence",
                    "context_sha256_sequence",
                )
                for value in evidence[field]
            )
            or any(
                type(row) is not list
                or len(row) != 8
                or any(not sha256(value) for value in row)
                for row in evidence["k8_row_sha256_sequence"]
            )
            or any(
                type(value) is not int or value < 0 or value >= 8
                for value in evidence["selected_index_sequence"]
            )
            or (
                complete
                and (
                    not sha256(evidence.get("closed_loop_trajectory_sha256"))
                    or not sha256(evidence.get("speed_probe_sha256"))
                    or evidence.get("capability_failure_sha256") is not None
                )
            )
            or (
                retained
                and (
                    evidence.get("closed_loop_trajectory_sha256") is not None
                    or evidence.get("speed_probe_sha256") is not None
                    or evidence.get("capability_failure_sha256")
                    != canonical_sha256(result["retained_capability_failure"])
                )
            )
        ):
            raise ValueError("bounded run evidence schema/content drifted")

    first = run_evidence[0]
    final = run_evidence[-1]
    if (
        first.get("occurrence") != "identity0_first"
        or final.get("occurrence") != "identity0_final_repeat"
        or first.get("scenario_id") != final.get("scenario_id")
    ):
        raise ValueError("identity0 repeat evidence positions drifted")
    repeat_comparison = {
        "candidate0_sha256_sequence_equal": first["candidate0_sha256_sequence"]
        == final["candidate0_sha256_sequence"],
        "k8_row_sha256_sequence_equal": first["k8_row_sha256_sequence"]
        == final["k8_row_sha256_sequence"],
        "atom_matrix_sequence_equal": first["atom_matrix_sha256_sequence"]
        == final["atom_matrix_sha256_sequence"],
        "context_sequence_equal": first["context_sha256_sequence"]
        == final["context_sha256_sequence"],
        "selected_index_sequence_equal": first["selected_index_sequence"]
        == final["selected_index_sequence"],
        "failure_class_equal": first["failure_class"] == final["failure_class"],
        "closed_loop_trajectory_equal": first["closed_loop_trajectory_sha256"]
        == final["closed_loop_trajectory_sha256"],
        "speed_probe_equal": first["speed_probe_sha256"]
        == final["speed_probe_sha256"],
    }
    if (
        results[0].get("status") != "complete"
        or results[-1].get("status") != "complete"
        or any(value is not True for value in repeat_comparison.values())
    ):
        raise ValueError("identity0 first/final determinism comparison failed")
    if len(unique_results) != plan["unique_identity_count"]:
        raise ValueError("bounded unique identity denominator drifted")
    coverage = _bounded_coverage(list(unique_results.values()))
    if coverage["passed"] is not True:
        raise ValueError("bounded fixed-DP support coverage gate failed")
    return {
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "status": "passed_exact_bounded_terminal",
        "run_count": len(results),
        "unique_identity_count": plan["unique_identity_count"],
        "tick_count": complete_run_count * TICKS_PER_RUN,
        "retained_capability_failure_count": retained_run_count,
        "mapped_runtime_source_failure_count": 0,
        "fixed_dp_support_coverage": coverage,
        "identity0_repeat_deterministic": True,
        "repeat_comparison": repeat_comparison,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _validate_fixed_dp_failure_receipt(
    value: Any, *, result: Mapping[str, Any]
) -> bool:
    fields = {
        "schema_version", "failure_class", "reason", "scenario_id",
        "route_identity_sha256", "family", "tier", "source_class",
        "phase_authority_mode", "source_map_sha256", "corridor_group_sha256",
        "fixed_dp_head", "tick_index", "invalid_indices", "invalid_count",
        "minimum_heading_norm", "maximum_heading_norm",
        "heading_norm_minimum", "heading_norm_maximum", "raw_k8_sha256",
        "candidate0_sha256", "default_output_sha256",
        "default_candidate0_identity", "raw_preimage", "training_eligible",
        "calibration_eligible", "evaluation_eligible", "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        return False
    if (
        value.get("schema_version") != FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION
        or value.get("failure_class") != FIXED_DP_FAILURE_CLASS
        or value.get("reason") != FIXED_DP_FAILURE_REASON
        or value.get("fixed_dp_head") != FIXED_DP_HEAD
        or any(
            value.get(field) != result.get(field)
            for field in (
                "scenario_id", "family", "tier", "source_class",
                "phase_authority_mode", "source_map_sha256",
                "corridor_group_sha256",
            )
        )
        or value.get("training_eligible") is not False
        or value.get("calibration_eligible") is not False
        or value.get("evaluation_eligible") is not False
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
    ):
        return False
    sha_fields = (
        "scenario_id", "route_identity_sha256", "source_map_sha256",
        "corridor_group_sha256", "raw_k8_sha256", "candidate0_sha256",
        "default_output_sha256",
    )
    if any(not _is_sha256(value.get(field)) for field in sha_fields):
        return False
    if (
        type(value.get("tick_index")) is not int
        or value["tick_index"] < 0
        or value["tick_index"] >= TICKS_PER_RUN
        or type(value.get("invalid_count")) is not int
        or value["invalid_count"] <= 0
        or type(value.get("invalid_indices")) is not list
        or len(value["invalid_indices"]) != value["invalid_count"]
    ):
        return False
    pairs: list[tuple[int, int]] = []
    for row in value["invalid_indices"]:
        if (
            type(row) is not dict
            or set(row) != {"candidate_index", "step_index"}
            or type(row.get("candidate_index")) is not int
            or type(row.get("step_index")) is not int
            or not 0 <= row["candidate_index"] < 8
            or not 0 <= row["step_index"] < 80
        ):
            return False
        pairs.append((row["candidate_index"], row["step_index"]))
    if pairs != sorted(set(pairs)):
        return False
    for field in (
        "minimum_heading_norm", "maximum_heading_norm",
        "heading_norm_minimum", "heading_norm_maximum",
    ):
        if type(value.get(field)) not in (int, float) or not math.isfinite(
            float(value[field])
        ):
            return False
    if (
        float(value["heading_norm_minimum"]) != 0.5
        or float(value["heading_norm_maximum"]) != 1.5
        or (
            0.5 <= float(value["minimum_heading_norm"])
            and float(value["maximum_heading_norm"]) <= 1.5
        )
    ):
        return False
    preimage = value.get("raw_preimage")
    if (
        type(preimage) is not dict
        or set(preimage)
        != {"relative_path", "file_sha256", "array_sha256", "shape", "dtype"}
        or preimage.get("array_sha256") != value.get("raw_k8_sha256")
        or preimage.get("file_sha256") != value.get("raw_k8_sha256")
        or preimage.get("relative_path")
        != f"fixed_dp_capability_failures/{value['raw_k8_sha256']}.bin"
        or preimage.get("shape") != [8, 80, 4]
        or preimage.get("dtype") != "float32"
    ):
        return False
    identity = value.get("default_candidate0_identity")
    return bool(
        type(identity) is dict
        and set(identity)
        == {
            "elementwise_equal",
            "max_abs_difference",
            "default_output_sha256",
            "candidate0_sha256",
            "native_ranked_k8",
        }
        and identity.get("elementwise_equal") is True
        and identity.get("max_abs_difference") == 0.0
        and identity.get("native_ranked_k8") is False
        and identity.get("candidate0_sha256") == value.get("candidate0_sha256")
        and identity.get("default_output_sha256")
        == value.get("default_output_sha256")
        and value.get("candidate0_sha256") == value.get("default_output_sha256")
    )


def _bounded_coverage(unique_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(unique_results)
    complete = [row for row in unique_results if row.get("status") == "complete"]

    def grouped(fields: tuple[str, ...], minimum_percent: int) -> dict[str, Any]:
        totals: collections.Counter[tuple[str, ...]] = collections.Counter()
        completes: collections.Counter[tuple[str, ...]] = collections.Counter()
        for row in unique_results:
            key = tuple(str(row[field]) for field in fields)
            totals[key] += 1
            if row.get("status") == "complete":
                completes[key] += 1
        rows = []
        passed = True
        for key in sorted(totals):
            ok = completes[key] * 100 > totals[key] * minimum_percent
            passed = passed and ok
            rows.append(
                {
                    "key": list(key), "planned": totals[key],
                    "complete": completes[key], "passed": ok,
                }
            )
        return {"fields": list(fields), "minimum_percent_exclusive": minimum_percent, "rows": rows, "passed": passed}

    family = grouped(("family",), 90)
    source = grouped(("source_class", "phase_authority_mode"), 90)
    family_tier = grouped(("family", "tier"), 80)
    red = [row for row in unique_results if row.get("family") == "red_light_phase_timing"]
    red_complete = [row for row in red if row.get("status") == "complete"]
    red_by_tier = collections.Counter(str(row["tier"]) for row in red_complete)
    red_maps = {str(row["source_map_sha256"]) for row in red_complete}
    red_pass = not red or (
        red_by_tier["easy"] >= 4
        and red_by_tier["borderline"] >= 7
        and red_by_tier["high_risk"] >= 4
        and len(red_maps) >= 3
    )
    minimum_complete = math.ceil(total * 0.95)
    overall_pass = total > 0 and len(complete) >= minimum_complete
    passed = bool(
        overall_pass and family["passed"] and source["passed"]
        and family_tier["passed"] and red_pass
    )
    return {
        "planned_unique_identity_count": total,
        "complete_unique_identity_count": len(complete),
        "minimum_complete_unique_identity_count": minimum_complete,
        "family": family,
        "source_mode": source,
        "family_tier": family_tier,
        "red_complete_by_tier": {
            tier: int(red_by_tier[tier])
            for tier in ("easy", "borderline", "high_risk")
        },
        "red_complete_distinct_source_map_count": len(red_maps),
        "red_minimum_complete_by_tier": {"easy": 4, "borderline": 7, "high_risk": 4},
        "red_minimum_distinct_source_maps": 3,
        "passed": passed,
    }
