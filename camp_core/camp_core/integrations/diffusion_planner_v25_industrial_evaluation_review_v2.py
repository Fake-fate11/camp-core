from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)


# Separate-role literal oracle: deliberately does not import any v1/v2
# industrial evaluation producer, registry, classification, or decision module.
EXPECTED_AUTHORITY = (
    "720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5"
)
EXPECTED_SCHEMA = "camp_dp_v25_industrial_oriented_evaluation_contract_v2"
EXPECTED_CAPABILITY_SCHEMA = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v2"
)
EXPECTED_PARENT_COUNT = 56
EXPECTED_LEAF_COUNT = 161
EXPECTED_ALPHA = 0.05
EXPECTED_METHOD = "holm_bonferroni_step_down_within_exact_family"
EXPECTED_MARGIN = "numeric_margin_not_authorized_until_future_preregistration"
EXPECTED_PARENT_REGISTRY_SHA256 = (
    "997f8776c4ba4f47eb6280f5124a1446ee9bfef55e6c14d5ee1f4417bedf308d"
)
EXPECTED_LEAF_REGISTRY_SHA256 = (
    "72aed1413ca7e6da857bd2a3ba627dc94c4da7f62704e18f9ed8080bb4afa2b9"
)

PARENT_IDS = (
    "safety.collision_any",
    "safety.collision_episode_count",
    "safety.collision_duration_s",
    "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps",
    "safety.collision_delta_v_mps",
    "safety.collision_contact_severity",
    "safety.min_full_polygon_clearance_m",
    "safety.max_closing_speed_mps",
    "safety.min_geometry_ttc_s",
    "safety.max_drac_mps2",
    "safety.critical_exposure_duration_s",
    "safety.critical_exposure_episode_count",
    "safety.time_headway_s",
    "safety.post_encroachment_time_s",
    "safety.certified_red_crossing_any",
    "safety.certified_red_crossing_count",
    "safety.certified_red_crossing_speed_mps",
    "safety.certified_red_encounter_opportunity_count",
    "safety.certified_red_phase_interval_count",
    "safety.drivable_outside_fraction_max",
    "safety.drivable_outside_duration_s",
    "safety.drivable_outside_episode_count",
    "safety.drivable_signed_clearance_min_m",
    "safety.drivable_penetration_max_m",
    "safety.wrong_way_duration_s",
    "safety.wrong_way_episode_count",
    "operations.speed_excess_max_mps",
    "operations.speed_excess_mean_positive_mps",
    "operations.speed_excess_duration_s",
    "operations.speed_excess_magnitude_duration_m",
    "operations.ordered_route_arc_final_m",
    "operations.max_forward_progress_m",
    "operations.net_forward_progress_m",
    "operations.completion_fraction",
    "operations.goal_distance_final_m",
    "operations.goal_reached",
    "operations.goal_passed",
    "operations.backtracking_duration_s",
    "operations.backtracking_distance_m",
    "operations.distance_traveled_m",
    "operations.travel_efficiency_ratio",
    "operations.false_stop_duration_s",
    "operations.false_stop_episode_count",
    "comfort.body_longitudinal_filtered_acceleration_summary",
    "comfort.planar_kinematic_vdv_like_longitudinal",
    "comfort.filtered_longitudinal_jerk_control_smoothness_summary",
    "comfort.body_lateral_filtered_acceleration_summary",
    "comfort.planar_kinematic_vdv_like_lateral",
    "comfort.filtered_lateral_jerk_control_smoothness_summary",
    "comfort.occupant_seat_iso_sae_conformity",
    "realtime.pool_generation_latency_ms",
    "realtime.atoms_latency_ms",
    "realtime.context_weights_latency_ms",
    "realtime.selector_increment_latency_ms",
    "realtime.end_to_end_latency_ms",
    "realtime.hypothetical_budget_exceedance",
)

GROUPED = {
    "safety.critical_exposure_duration_s",
    "safety.critical_exposure_episode_count",
    "operations.speed_excess_duration_s",
    "operations.speed_excess_magnitude_duration_m",
    "comfort.body_longitudinal_filtered_acceleration_summary",
    "comfort.body_lateral_filtered_acceleration_summary",
    "comfort.filtered_longitudinal_jerk_control_smoothness_summary",
    "comfort.filtered_lateral_jerk_control_smoothness_summary",
    "realtime.pool_generation_latency_ms",
    "realtime.atoms_latency_ms",
    "realtime.context_weights_latency_ms",
    "realtime.selector_increment_latency_ms",
    "realtime.end_to_end_latency_ms",
    "realtime.hypothetical_budget_exceedance",
}

GRIDS = {
    "clearance_m": (("0", 0.0), ("0p5", 0.5), ("1", 1.0), ("2", 2.0)),
    "ttc_s": (("0p5", 0.5), ("1", 1.0), ("2", 2.0), ("3", 3.0), ("5", 5.0)),
    "closing_mps": (("0p5", 0.5), ("1", 1.0), ("2", 2.0), ("5", 5.0)),
    "drac_mps2": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("3", 3.0),
        ("5", 5.0),
    ),
    "speed": (("0", 0.0), ("0p05", 0.05), ("0p1", 0.1), ("0p2", 0.2)),
    "acceleration": (("0p5", 0.5), ("1", 1.0), ("2", 2.0), ("3", 3.0)),
    "jerk": (("0p5", 0.5), ("1", 1.0), ("2", 2.0), ("5", 5.0)),
    "latency": (("50", 50.0), ("100", 100.0), ("200", 200.0), ("500", 500.0), ("1000", 1000.0)),
}

LEAF_FIELDS = {
    "leaf_id",
    "parent_id",
    "domain",
    "units",
    "direction",
    "formula",
    "input_shape",
    "applicability",
    "opportunity_denominator",
    "missing_policy",
    "guardrail_role",
    "multiplicity_family",
    "confidence_interval",
    "familywise_method",
    "familywise_alpha",
    "claim_gate_state",
    "btw_applicability",
    "evidence_class",
    "source_binding_id",
}

SOURCE_ROOTS = {
    "execution": (
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
        {
            "artifact_report.json": "63483ab8e368e6281f1da63a913a6294e30ee2bd40af5d50a41e08362a95f5db",
            "report.json": "d7b8214f29b7cb7743876d2c87e2df0dc1e0a35ce6d0242186fb2ca1903bded2",
            "HEADS": "9623e17b06e35b065653c7b7d47f66c113b4a65a69be4adb7fd4309873fa4f81",
        },
    ),
    "execution_review": (
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
        {
            "report.json": "2f1e9f0288ac442110ae4f0ecf7c3a10bbdc5f29ebef008465427ec1a288e40a",
            "HEADS": "9623e17b06e35b065653c7b7d47f66c113b4a65a69be4adb7fd4309873fa4f81",
        },
    ),
    "evaluation_v2_contract": (
        "99501763a4a88c9d80fff738054b37593717df0b6d33e3749ad451d9e52a15e0",
        {
            "report.json": "e193c5ac2014777ff8d78003ae798bf61151e53ea86b85f1abf6635f5676f8a2",
            "HEADS": "005c185d95c31df65b0bc7fc87e86add13b78026926780153958680bed3731ef",
        },
    ),
    "evaluation_v2_contract_review": (
        "a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0",
        {
            "report.json": "2cd808e5f87e92c21219a887eab3eec9e5d13383599ffea8f032d76d901c6724",
            "HEADS": "80e6cedb9d321d67c4a9a6f44b682ab93648a55cbbe4e6a995db5a015c6ea360",
        },
    ),
    "evaluation_v2_materialization": (
        "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941",
        {
            "report.json": "26102e5908f4d4f9411dd76e4d89f92d0ab6b1b1da24eff46eb0393094251cbb",
            "HEADS": "95729027a5123e594d2d8c5df68c3375654852050284bf5817c2deff4091478d",
        },
    ),
    "evaluation_v2_materialization_review": (
        "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b",
        {
            "report.json": "9a8534888416f88ed13343503461308b38c1a89e7df2679e23a12f537dfd5f4b",
            "HEADS": "34ed389b296dbeabdf7e98d9df93ea77645fbdf6fac7f9fc84826ed52a7158c1",
        },
    ),
    "metric_contract": (
        "318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758",
        {
            "report.json": "bcb45030be87dd8e21e3d733cc93f8d5173275689743c302107e1fe31d075565",
            "HEADS": "78d07b6e7159e5a17df9ee16599024bad912282c4079626b700470ef7f835323",
        },
    ),
    "metric_contract_review": (
        "fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95",
        {
            "report.json": "56a270778b7f480464456083873f5732c0572bd49281cf107e1966dd9b6e4f03",
        },
    ),
}

SOURCE_REVIEW_ROOTS = {
    "execution": "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
    "execution_review": None,
    "evaluation_v2_contract": "a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0",
    "evaluation_v2_contract_review": None,
    "evaluation_v2_materialization": "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b",
    "evaluation_v2_materialization_review": None,
    "metric_contract": "fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95",
    "metric_contract_review": None,
}

ARTIFACTS_BY_BINDING = {
    "execution_kinematics_geometry": (
        "execution",
        "execution_review",
        "evaluation_v2_contract",
        "evaluation_v2_contract_review",
        "evaluation_v2_materialization",
        "evaluation_v2_materialization_review",
    ),
    "execution_route_map": (
        "execution",
        "execution_review",
        "evaluation_v2_contract",
        "evaluation_v2_contract_review",
        "evaluation_v2_materialization",
        "evaluation_v2_materialization_review",
    ),
    "execution_red_speed": (
        "execution",
        "execution_review",
        "evaluation_v2_contract",
        "evaluation_v2_contract_review",
        "evaluation_v2_materialization",
        "evaluation_v2_materialization_review",
    ),
    "execution_planar_motion": (
        "execution",
        "execution_review",
        "evaluation_v2_contract",
        "evaluation_v2_contract_review",
        "metric_contract",
        "metric_contract_review",
        "evaluation_v2_materialization",
        "evaluation_v2_materialization_review",
    ),
    "missing_contact_dynamics": (),
    "missing_unique_leader": (),
    "missing_conflict_zone": (),
    "missing_false_stop_context": (),
    "missing_target_runtime": (),
    "inapplicable_occupant_conformity": (),
}

POINTERS = {
    "execution_kinematics_geometry": (
        "/source_capability_audit/actor_fields",
        "/source_capability_audit/spawn_fields",
        "/contract/endpoint_catalog/collision",
        "/contract/endpoint_catalog/dynamic_proximity",
    ),
    "execution_route_map": (
        "/source_capability_audit/all_map_assets_present_and_sha_bound",
        "/source_capability_audit/all_route_assets_present_and_sha_bound",
        "/source_capability_audit/full_polygon_capability",
        "/source_capability_audit/ordered_route_capability",
        "/contract/endpoint_catalog/road_containment",
        "/contract/endpoint_catalog/route",
        "/contract/endpoint_catalog/goal",
    ),
    "execution_red_speed": (
        "/contract/endpoint_catalog/certified_red_crossing",
        "/contract/endpoint_catalog/speed",
        "/contract/grids/speed_tolerance_mps",
    ),
    "execution_planar_motion": (
        "/contract/geometry/dt_s",
        "/contract/geometry/boxcar_kernel",
        "/contract/endpoint_catalog/vehicle_body_planar_kinematic_proxy",
        "/contract/body_proxy/source_fields",
        "/contract/body_proxy/filter",
    ),
    "missing_contact_dynamics": (),
    "missing_unique_leader": (),
    "missing_conflict_zone": (),
    "missing_false_stop_context": (),
    "missing_target_runtime": (),
    "inapplicable_occupant_conformity": (),
}


def _canonical_sha(value: Any) -> str:
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _expected_leaf_ids() -> dict[str, str]:
    result = {parent: parent for parent in PARENT_IDS if parent not in GROUPED}
    for parent in (
        "safety.critical_exposure_duration_s",
        "safety.critical_exposure_episode_count",
    ):
        suffix = "duration_s" if parent.endswith("duration_s") else "episode_count"
        for family, comp, unit in (
            ("clearance_m", "le", "m"),
            ("ttc_s", "le", "s"),
            ("closing_mps", "ge", "mps"),
            ("drac_mps2", "ge", "mps2"),
        ):
            for token, _ in GRIDS[family]:
                result[f"safety.{family}_{comp}_{token}{unit}_{suffix}"] = parent
    for token, _ in GRIDS["speed"]:
        result[f"operations.speed_excess_gt_{token}mps_duration_s"] = (
            "operations.speed_excess_duration_s"
        )
        result[f"operations.speed_excess_magnitude_above_{token}mps_duration_m"] = (
            "operations.speed_excess_magnitude_duration_m"
        )
    for axis in ("longitudinal", "lateral"):
        acceleration_parent = f"comfort.body_{axis}_filtered_acceleration_summary"
        for stat in (
            "signed_mean",
            "rms",
            "min",
            "max",
            "peak_abs",
            "abs_p50",
            "abs_p90",
            "abs_p95",
            "abs_p99",
        ):
            result[f"comfort.body_{axis}_filtered_acceleration_{stat}"] = acceleration_parent
        for token, _ in GRIDS["acceleration"]:
            result[
                f"comfort.body_{axis}_filtered_acceleration_abs_gt_{token}mps2_duration_s"
            ] = acceleration_parent
        jerk_parent = f"comfort.filtered_{axis}_jerk_control_smoothness_summary"
        for stat in ("rms", "peak_abs", "abs_p95"):
            result[f"comfort.filtered_{axis}_jerk_control_smoothness_{stat}"] = jerk_parent
        for token, _ in GRIDS["jerk"]:
            result[f"comfort.filtered_{axis}_jerk_abs_gt_{token}mps3_duration_s"] = jerk_parent
    for stage in (
        "pool_generation",
        "atoms",
        "context_weights",
        "selector_increment",
        "end_to_end",
    ):
        parent = f"realtime.{stage}_latency_ms"
        for stat in ("mean", "median", "p95", "p99", "max"):
            result[f"realtime.{stage}_latency_{stat}_ms"] = parent
    for token, _ in GRIDS["latency"]:
        result[f"realtime.end_to_end_exceedance_rate_{token}ms"] = (
            "realtime.hypothetical_budget_exceedance"
        )
        result[f"realtime.end_to_end_max_overrun_{token}ms_ms"] = (
            "realtime.hypothetical_budget_exceedance"
        )
    if len(result) != EXPECTED_LEAF_COUNT:
        raise AssertionError(len(result))
    return result


def _expected_source(parent: str) -> str:
    if parent in {"safety.collision_delta_v_mps", "safety.collision_contact_severity"}:
        return "missing_contact_dynamics"
    if parent == "safety.time_headway_s":
        return "missing_unique_leader"
    if parent == "safety.post_encroachment_time_s":
        return "missing_conflict_zone"
    if parent.startswith("operations.false_stop_"):
        return "missing_false_stop_context"
    if parent == "comfort.occupant_seat_iso_sae_conformity":
        return "inapplicable_occupant_conformity"
    if parent.startswith("realtime."):
        return "missing_target_runtime"
    if parent.startswith("comfort."):
        return "execution_planar_motion"
    if parent.startswith("operations.speed_") or parent.startswith("safety.certified_red_"):
        return "execution_red_speed"
    if parent.startswith("operations.") or parent.startswith("safety.drivable_") or parent.startswith("safety.wrong_way_"):
        return "execution_route_map"
    return "execution_kinematics_geometry"


def _expected_class(binding: str) -> str:
    if binding == "inapplicable_occupant_conformity":
        return "scientifically_inapplicable"
    if binding.startswith("missing_"):
        return "evidence_missing"
    return "reconstructable_with_frozen_transform"


def _expected_role(parent: str, evidence_class: str, direction: str) -> str:
    if evidence_class in {"evidence_missing", "scientifically_inapplicable"}:
        return "evidence_missing_not_testable"
    if parent.startswith(
        (
            "safety.collision_",
            "safety.certified_red_crossing",
            "safety.drivable_",
            "safety.wrong_way_",
        )
    ):
        return "hard_safety"
    if direction == "descriptive_unclassified" or parent.endswith(
        ("opportunity_count", "interval_count", "distance_traveled_m")
    ):
        return "descriptive_only"
    return "guardrail"


def _read_inventory(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in (path / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        sha, name = line.split("  ", 1)
        rows[name] = sha
    return rows


def _pointer(value: Any, pointer: str) -> Any:
    current = value
    for token in pointer.split("/")[1:]:
        if not isinstance(current, Mapping) or token not in current:
            raise ValueError(f"independent missing JSON pointer: {pointer}")
        current = current[token]
    return current


def review_contract_v2_literal(contract: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    if value.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("independent v2 schema drifted")
    if value.get("high_authority_sha256") != EXPECTED_AUTHORITY:
        raise ValueError("independent v2 authority drifted")
    if value.get("parent_endpoint_count") != EXPECTED_PARENT_COUNT:
        raise ValueError("independent v2 parent count drifted")
    parents = value.get("parent_endpoints")
    if not isinstance(parents, list) or [x.get("endpoint_id") for x in parents] != list(PARENT_IDS):
        raise ValueError("independent v2 parent registry drifted")
    if _canonical_sha(parents) != EXPECTED_PARENT_REGISTRY_SHA256:
        raise ValueError("independent v2 parent semantic preimage drifted")
    onset = parents[3]
    if (
        onset.get("evidence_class") != "reconstructable_with_frozen_transform"
        or onset.get("source") != "sealed_execution"
        or "last noncollision interval" not in onset.get("formula", "")
        or "first contact fraction" not in onset.get("formula", "")
        or "never delta-v" not in onset.get("industrial_interpretation", "")
    ):
        raise ValueError("independent collision-onset proxy drifted")
    expected = _expected_leaf_ids()
    rows = value.get("scalar_leaf_registry")
    if (
        value.get("scalar_leaf_count") != EXPECTED_LEAF_COUNT
        or not isinstance(rows, list)
        or len(rows) != EXPECTED_LEAF_COUNT
    ):
        raise ValueError("independent scalar leaf count drifted")
    if _canonical_sha(rows) != EXPECTED_LEAF_REGISTRY_SHA256:
        raise ValueError("independent scalar leaf semantic preimage drifted")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != LEAF_FIELDS:
            raise ValueError("independent scalar leaf schema drifted")
        leaf_id = row["leaf_id"]
        if leaf_id in seen or expected.get(leaf_id) != row["parent_id"]:
            raise ValueError("independent scalar leaf ID or parent drifted")
        seen.add(leaf_id)
        binding = _expected_source(row["parent_id"])
        evidence_class = _expected_class(binding)
        role = _expected_role(row["parent_id"], evidence_class, row["direction"])
        if (
            row["source_binding_id"] != binding
            or row["evidence_class"] != evidence_class
            or row["guardrail_role"] != role
            or not isinstance(row["formula"], str)
            or not row["formula"]
            or not isinstance(row["units"], str)
            or not row["units"]
        ):
            raise ValueError("independent scalar leaf semantics drifted")
        if role == "evidence_missing_not_testable":
            if (
                row["familywise_method"] != "none_not_testable"
                or row["familywise_alpha"] is not None
                or row["claim_gate_state"] != "not_testable_evidence_missing"
            ):
                raise ValueError("independent missing leaf topology drifted")
        else:
            if (
                row["familywise_method"] != EXPECTED_METHOD
                or row["familywise_alpha"] != EXPECTED_ALPHA
                or row["claim_gate_state"]
                not in {EXPECTED_MARGIN, "descriptive_only_not_claim_gate"}
            ):
                raise ValueError("independent testable leaf topology drifted")
    if seen != set(expected):
        raise ValueError("independent scalar leaf omission")
    topology = value.get("decision_topology")
    if (
        topology.get("familywise_method") != EXPECTED_METHOD
        or topology.get("familywise_alpha") != EXPECTED_ALPHA
        or topology.get("numeric_margin_state") != EXPECTED_MARGIN
        or topology.get("current_claim_gate_authorized") is not False
        or topology.get("weighted_compensation_allowed") is not False
        or "intersection_union" not in topology.get("hard_safety_combination", "")
        or "intersection_union" not in topology.get("guardrail_combination", "")
    ):
        raise ValueError("independent decision topology drifted")
    family_ids = {leaf for members in topology["families"].values() for leaf in members}
    if family_ids != set(expected):
        raise ValueError("independent multiplicity family coverage drifted")
    if (
        value.get("claim_authorized") is not False
        or value.get("outcome_values_read") is not False
        or value.get("model_pool_selector_call_count") != 0
        or value.get("old_artifact_or_cas_write_count") != 0
        or value.get("evaluation_and_selector_training_decoupled") is not True
    ):
        raise ValueError("independent no-run/no-claim boundary drifted")
    return value


def review_capability_v2_literal(
    matrix: Mapping[str, Any],
    contract: Mapping[str, Any],
    source_dirs: Mapping[str, str | Path],
) -> dict[str, Any]:
    value = copy.deepcopy(dict(matrix))
    reviewed = review_contract_v2_literal(contract)
    if set(source_dirs) != set(SOURCE_ROOTS):
        raise ValueError("independent sealed source set drifted")
    inventories: dict[str, Any] = {}
    reports: dict[str, Any] = {}
    for name, (root, expected_entries) in SOURCE_ROOTS.items():
        path = Path(source_dirs[name])
        verify_complete_seal(path, root)
        actual = _read_inventory(path)
        if any(actual.get(filename) != sha for filename, sha in expected_entries.items()):
            raise ValueError(f"independent sealed inventory drifted: {name}")
        selected = {filename: actual[filename] for filename in sorted(expected_entries)}
        inventories[name] = {
            "artifact_root_sha256": root,
            "artifact_review_root_sha256": SOURCE_REVIEW_ROOTS[name],
            "inventory_manifest_sha256": _canonical_sha(selected),
            "entries": selected,
        }
        if name in {"evaluation_v2_contract", "metric_contract"}:
            reports[name] = json.loads((path / "report.json").read_text(encoding="utf-8"))
    if (
        value.get("schema_version") != EXPECTED_CAPABILITY_SCHEMA
        or value.get("contract_sha256") != _canonical_sha(reviewed)
        or value.get("scalar_leaf_count") != EXPECTED_LEAF_COUNT
        or value.get("structure_only") is not True
        or value.get("outcome_values_read") is not False
        or value.get("model_pool_selector_call_count") != 0
        or value.get("old_artifact_or_cas_write_count") != 0
    ):
        raise ValueError("independent capability authority drifted")
    if value.get("sealed_inventory_audit") != inventories:
        raise ValueError("independent capability sealed inventory audit drifted")
    leaves = {row["leaf_id"]: row for row in reviewed["scalar_leaf_registry"]}
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_LEAF_COUNT:
        raise ValueError("independent capability row count drifted")
    seen: set[str] = set()
    for row in rows:
        leaf_id = row.get("leaf_id")
        if leaf_id in seen or leaf_id not in leaves:
            raise ValueError("independent capability leaf drifted")
        seen.add(leaf_id)
        leaf = leaves[leaf_id]
        binding = _expected_source(leaf["parent_id"])
        if (
            row.get("parent_id") != leaf["parent_id"]
            or row.get("evidence_class") != _expected_class(binding)
            or row.get("canonical_json_pointers") != list(POINTERS[binding])
            or row.get("structure_only") is not True
            or row.get("outcome_values_read") is not False
        ):
            raise ValueError("independent capability classification drifted")
        for pointer in POINTERS[binding]:
            report_name = "metric_contract" if pointer.startswith("/contract/body_proxy/") else "evaluation_v2_contract"
            _pointer(reports[report_name], pointer)
        evidence_rows = row.get("evidence_inventory", [])
        if not isinstance(evidence_rows, list):
            raise ValueError("independent capability evidence inventory type drifted")
        expected_evidence = []
        for artifact_name in ARTIFACTS_BY_BINDING[binding]:
            inventory = inventories[artifact_name]
            for filename, sha in inventory["entries"].items():
                expected_evidence.append(
                    {
                        "artifact_name": artifact_name,
                        "artifact_root_sha256": inventory["artifact_root_sha256"],
                        "artifact_review_root_sha256": inventory[
                            "artifact_review_root_sha256"
                        ],
                        "inventory_file": filename,
                        "inventory_file_sha256": sha,
                        "inventory_manifest_sha256": inventory[
                            "inventory_manifest_sha256"
                        ],
                    }
                )
        if evidence_rows != expected_evidence:
            raise ValueError("independent capability exact evidence set drifted")
        expected_artifacts = {item["artifact_name"]: item for item in evidence_rows}
        for artifact_name, item in expected_artifacts.items():
            if artifact_name not in inventories:
                raise ValueError("independent capability unknown artifact")
            expected_inventory = inventories[artifact_name]
            if (
                item.get("artifact_root_sha256")
                != expected_inventory["artifact_root_sha256"]
                or item.get("inventory_manifest_sha256")
                != expected_inventory["inventory_manifest_sha256"]
                or expected_inventory["entries"].get(item.get("inventory_file"))
                != item.get("inventory_file_sha256")
            ):
                raise ValueError("independent capability inventory binding drifted")
        if ARTIFACTS_BY_BINDING[binding] and not expected_artifacts:
            raise ValueError("independent reconstructable capability has no evidence")
    if seen != set(leaves):
        raise ValueError("independent capability omitted leaf")
    return value
