"""Reviewer-local oracle for fair-pool adaptation contract v3.

This module intentionally imports neither the v3 producer contract nor the v2
input-manifest producer.  It rebuilds the v3 additions from local literals and
contains independent preflight and qualification-decision checks.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import beta


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v3"
QUALIFICATION_SCHEMA = (
    "camp_dp_v25_fair_pool_adaptation_qualification_receipt_v3"
)
EXPECTED_V2_PAYLOAD_SHA256 = (
    "338b33ef7fc62ac014bcabf81ad2f349c370bbf4a5924ad72c9445e27bfeacad"
)
V2_CONTRACT_ROOT = (
    "f2314088f25c601ae80fa022dd0b4a513c29d07a54b7008c17be6644c078e9e1"
)
V2_REVIEW_ROOT = (
    "ca0bd63c057f0e58dc88d278c4f45b713f93b408b22ab33c122dfa4567ecab6b"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
ROUTE_ASSET_SHA256 = (
    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
)
MAP_SHA256 = "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
INPUT_MODULE_RELATIVE = (
    "camp_core/camp_core/integrations/"
    "diffusion_planner_v25_fair_pool_input_manifest_v2.py"
)
ROOT = Path(__file__).resolve().parents[3]
PHASE_MODE = {
    "sequential_within": "sequential_batch1_x8",
    "batch8_within": "single_invocation_batch8",
    "cross_mode": "matched_repeat_cross_mode",
}
ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
WITHIN_NUMERIC_IDS = (
    *(f"atom.normalized_delta.{index:02d}.{name}" for index, name in enumerate(ATOM_NAMES)),
    "trajectory.ego.position_max_m",
    "trajectory.ego.heading_max_rad",
    "trajectory.ego.speed_max_mps",
    "trajectory.neighbor.position_max_m",
    "trajectory.neighbor.heading_max_rad",
    "trajectory.neighbor.speed_max_mps",
    "score.static14d.abs_delta",
    "score.scene14d.abs_delta",
)
CROSS_ONLY_NUMERIC_IDS = (
    "score.static14d.within_mode_normalized_delta",
    "score.static14d.margin_ratio",
    "score.static14d.rank_error",
    "score.scene14d.within_mode_normalized_delta",
    "score.scene14d.margin_ratio",
    "score.scene14d.rank_error",
    "neighbor.relative_within_mode_inflation",
)
CROSS_NUMERIC_IDS = (*WITHIN_NUMERIC_IDS, *CROSS_ONLY_NUMERIC_IDS)
V2_ENDPOINT_ROW_SHA256 = {
    "atom.normalized_delta.00.jerk_early": "3097d4b92c543f74f351019e232121e951b3c1c2001e3795c8c35c10cc739e77",
    "atom.normalized_delta.01.jerk_late": "0da24f201aeed9000cefdab427bb03deab5971ec8f328c4920d2dfbf212ee0c6",
    "atom.normalized_delta.02.jerk_full": "6e8e107d68b759f998380d7b9d5b260e6127282571bc1c3c9a2562c9ec0a18d7",
    "atom.normalized_delta.03.rms_acceleration": "bcff947ceaf7c1caf807bc92deed845f412d79a09c7c3c93991f731b28dd786d",
    "atom.normalized_delta.04.speed_limit_margin_0_0": "4e07c7dcb8723ac8f3330db4f27d0d58c693dc9b65c3108a0e2f50d91e29a328",
    "atom.normalized_delta.05.speed_limit_margin_0_5": "30360106be86f62a58f6d3a4810a8d7fa50f4db5aed5fb208a5a3628bd8c5bbf",
    "atom.normalized_delta.06.speed_limit_margin_1_0": "856ba81b1b063ab823a2f17a2d3f8853886dfd51342d69ef3ca3b6dbae7581db",
    "atom.normalized_delta.07.lane_deviation": "37504d9abbcf5188e28e1edec6af223edcf0fe951eb46c4e698168eeef8f14cd",
    "atom.normalized_delta.08.clearance": "5efe7f8122f7a9c594d5a94ef49055d4a07b885494350508380a4d382553c711",
    "atom.normalized_delta.09.progress_shortfall": "3813052350aeff272893c6361aad9af5742c26eba2b999061c9da01aef63383b",
    "atom.normalized_delta.10.planned_red_light_cost": "35619e42368ede9dd6cd148ac74b64f07e6f914593f206a0b0a417925e2839ec",
    "atom.normalized_delta.11.planned_lateral_acceleration_cost": "ecc6d9df5c221e50b7261403eeaab37ed449fc353ebe1a870d13a419cb009f40",
    "atom.normalized_delta.12.red_stopping_margin_cost": "d5e0485bd7d96bddfc64d4e4b8964a4c19c8db549b4479d7bf9988102c42cae7",
    "atom.normalized_delta.13.dp_prior_jerk_excess_cost": "1764eeb8937669b2c11e440e22ea52931e6cf2b3683334702eb81ecd55ea2e22",
    "trajectory.ego.position_max_m": "e08ce067f91f8565b983e0a23e4db21ca3ac9bfcd8413a14946c7ce38cb5f371",
    "trajectory.ego.heading_max_rad": "71fd692cdc0a2eedbb740f73103da1c4a5333312e45e94e1e6f8fa060eddf3e9",
    "trajectory.ego.speed_max_mps": "b0bdc09a08725695d0ddaf81a72a02830f8b3e09791faad647c4b8cb8ebd51a8",
    "trajectory.neighbor.position_max_m": "12dead4179c9a99d42a6a5c1364fa3562e468e8a8661051a15c671aea01ebd7a",
    "trajectory.neighbor.heading_max_rad": "93c3849b6aef27b32605d9f66055e06d6c23a273fc2b28f559d57ce90264da62",
    "trajectory.neighbor.speed_max_mps": "18dbb7307a7bb0b365d64a3fd080f1557141ed225c7fa713ca4b40faa3aa92a8",
    "score.static14d.abs_delta": "ed06320142524fd2cd7aec0ec158511fab1bd1de06639ccc13fae9333804772d",
    "score.static14d.within_mode_normalized_delta": "8ccf828e3d8d22ab8158303261c4aef3b41a9e3607e8e02266edb8413e4eca44",
    "score.static14d.margin_ratio": "6ac4aaa14a761280274ae076c99d7d40fa7f89eaeca3c9d3d93fb188bfaf4cb3",
    "score.static14d.rank_error": "1a07ffde6fea4c48e3d9414e821945f02c86b0f90cdaa892075f3ac8c2d49de9",
    "functional.static14d.mask_eligibility": "9204ad929086b937f871afa4dd4dd25e86fbe8e868cc438f11bc32b5ab6264dd",
    "functional.static14d.selected_index_action": "c7db2577f86478afc2ac5962dc44c50db8a281e2237b516ab4d230a94254b766",
    "score.scene14d.abs_delta": "08787762a00a937eb739e66f4cb87d4fd202759f536201968986e68367418daa",
    "score.scene14d.within_mode_normalized_delta": "f4ecc958e5a5a66eeeb8790b58f52e59986caf677a7b4586b4aa497d571dc6e3",
    "score.scene14d.margin_ratio": "ac9a0cd9e0770711edcc02dcf0dfd941635c3dc21867091629ed3e394123f30f",
    "score.scene14d.rank_error": "7d7feeffeca2ce2ab5775489182c00264dde6b964b1f96b1e9fff9fbe1ebf5d1",
    "functional.scene14d.mask_eligibility": "bce37d472ae49647f55e3f3d15944d01a1bef48109d933e64e5181d5af11d9b6",
    "functional.scene14d.selected_index_action": "5da47e46d91c08c05e66d472d1ad46590a72503c0c30c660ff754ca1cb29c1bf",
    "neighbor.relative_within_mode_inflation": "cf0847a112f4d5d301e40a1b6b1a533b28e3104159a187420ddb6946cc0676ea",
    "k8.finite_and_diverse": "32a0052f7d16ddbf9e387b61bfe643dc5cc32b59117a2e5e9339c5847b36265b",
    "authority.fingerprint": "41c10c1b2a0b9f9426298e4e3fa8277b2603477e9f74b4013cdc85bb466e0c51",
    "pool.tensor_immutability_and_zero_calls": "f456862efc0c69b3c3dd38caa25d631648da50d2a9a5d603312582c7e3780008",
    "split.input_only_clone_nonoverlap": "b391216523977b82244226c2f1b64d25783e1584244dcc9ed2406c2ad6f6d5d8",
}
HARD_KEYS = (
    ("sequential_within", "sequential_batch1_x8", "k8.finite_and_diverse"),
    ("sequential_within", "sequential_batch1_x8", "authority.fingerprint"),
    ("batch8_within", "single_invocation_batch8", "k8.finite_and_diverse"),
    ("batch8_within", "single_invocation_batch8", "authority.fingerprint"),
    ("global", "none", "split.input_only_clone_nonoverlap"),
    ("cross_mode", "matched_repeat_cross_mode", "pool.tensor_immutability_and_zero_calls"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.static14d.mask_eligibility"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.scene14d.mask_eligibility"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.static14d.selected_index_action"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.scene14d.selected_index_action"),
)
ROUTE_LANELET_IDS = (3002178, 3002181, 3002185)
ROUTE_WORLD_XY_M = (
    (41.650352478027344, -166.84780883789062),
    (40.94586944580078, -163.01504516601562),
    (40.24015808105469, -159.18252563476562),
    (39.534156799316406, -155.3500518798828),
    (38.815608978271484, -151.5199432373047),
    (38.057830810546875, -147.69766235351562),
    (37.295597076416016, -143.87628173828125),
    (36.53434371948242, -140.05471801757812),
    (35.7720947265625, -136.23333740234375),
    (35.010719299316406, -132.41177368164062),
    (34.2730712890625, -128.58538818359375),
    (33.5578498840332, -124.75465393066406),
    (32.88887023925781, -121.12942504882812),
    (32.21886444091797, -117.50437927246094),
    (31.549686431884766, -113.87918853759766),
    (30.88129997253418, -110.25384521484375),
    (30.215145111083984, -106.64425659179688),
    (29.549076080322266, -103.03466033935547),
    (28.882953643798828, -99.42506408691406),
    (28.21786117553711, -95.81527709960938),
    (27.555999755859375, -92.20490264892578),
    (26.895748138427734, -88.59423828125),
    (26.232933044433594, -84.98403930664062),
    (25.565349578857422, -81.37474060058594),
    (24.89661407470703, -77.76565551757812),
    (24.23495101928711, -74.1552505493164),
)
SPAWN_POSE = {
    "x_m": 41.650352478027344,
    "y_m": -166.84780883789062,
    "z_m": 0.0,
    "heading_rad": 1.7525728940963745,
}
GOAL_POSE = {
    "x_m": 24.23495101928711,
    "y_m": -74.1552505493164,
    "z_m": 0.0,
    "heading_rad": 1.752050518989563,
}
TIER_COUNTS = {
    "no_npc": 0,
    "low_density": 2,
    "medium_density": 4,
    "high_density": 6,
}
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = "<f4"
B4_PREOPEN_PATH = (
    "/root/autodl-tmp/"
    "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST"
)
B4_PREOPEN_ROOT = (
    "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
)
B4_PREPARED_SHA = (
    "e67fee3309f822c80605b3e9b00009d2ae3e27139e36396d009b9a2b306535a2"
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def review_contract_literal_v3(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("reviewed contract must be object")
    payload = dict(value)
    supplied = payload.pop("contract_payload_sha256", None)
    if supplied != sha256_json(payload):
        raise ValueError("reviewer contract payload SHA drifted")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("reviewer schema version drifted")
    if (
        value.get("status")
        != "frozen_executable_design_only_acquisition_unauthorized"
    ):
        raise ValueError("reviewer status drifted")
    diagnostics = value.get("superseded_preacquisition_diagnostics")
    if diagnostics != {
        "v1_contract_root_sha256": (
            "b2de5b71509526407e102b3ba3aec74000290f13ab75918d0008596a6b52f824"
        ),
        "v1_review_root_sha256": (
            "a16a523766493826d6b5b3f4e0a8188a1019571e4491a53e3149af2bb408aa37"
        ),
        "v2_contract_root_sha256": V2_CONTRACT_ROOT,
        "v2_review_root_sha256": V2_REVIEW_ROOT,
    }:
        raise ValueError("reviewer superseded roots drifted")
    if value.get("inherited_v2_payload_sha256") != EXPECTED_V2_PAYLOAD_SHA256:
        raise ValueError("reviewer inherited v2 payload drifted")
    scope = value.get("scope")
    if scope != {
        "generator": GENERATOR_NAME,
        "coverage": (
            "single_route_single_map_bounded_development_nonholdout_"
            "four_density_tiers_only"
        ),
        "pass_interpretation": (
            "within_this_single_route_bounded_scope_only_current_"
            "evidence_does_not_trigger_retraining"
        ),
        "general_ood_or_architecture_equivalence_claim": False,
    }:
        raise ValueError("reviewer bounded scope drifted")
    authority = value.get("input_authority")
    module_path = ROOT / INPUT_MODULE_RELATIVE
    if (
        type(authority) is not dict
        or authority.get("module_path") != INPUT_MODULE_RELATIVE
        or authority.get("module_sha256")
        != hashlib.sha256(module_path.read_bytes()).hexdigest()
        or authority.get("source_scene_entrypoint")
        != "materialize_exact_source_scene"
        or authority.get("manifest_entrypoint")
        != "materialize_input_only_manifest"
        or authority.get("preflight_entrypoint")
        != "validate_preflight_receipt"
        or authority.get("b4_forbidden_inventory")
        != (
            "rederived_inside_validator_from_exact_sealed_prepared_"
            "runtime_cases_bytes"
        )
        or authority.get("preflight_no_drop_replacement_or_suffix") is not True
    ):
        raise ValueError("reviewer input authority drifted")
    algorithm = authority["source_scene_algorithm"]
    if (
        algorithm.get("route_asset_sha256") != ROUTE_ASSET_SHA256
        or algorithm.get("map_asset_sha256") != MAP_SHA256
        or algorithm.get("route_lanelet_ids") != [3002178, 3002181, 3002185]
        or algorithm.get("ordered_route_point_count") != 26
        or algorithm.get("actor_rng")
        != "numpy_Generator_PCG64DXSM_scenario_seed"
        or algorithm.get("actor_count_by_tier")
        != {
            "no_npc": 0,
            "low_density": 2,
            "medium_density": 4,
            "high_density": 6,
        }
        or algorithm.get("caller_supplied_source_record_allowed") is not False
    ):
        raise ValueError("reviewer source-scene algorithm drifted")
    actual = authority["actual_preimages"]
    if (
        actual.get("latent_shape") != [8, 321, 81, 4]
        or actual.get("latent_dtype") != "<f4"
        or actual.get("latent_bytes") != "C_order_little_endian_float32"
        or actual.get("tensor_converter_path")
        != "scenario_generation/tensor_converter.py"
        or actual.get("tensor_converter_sha256")
        != "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
        or actual.get("tensor_converter_entrypoint") != "to_model_tensors"
        or "source_scene_sha256" not in actual.get("input_tensor_bundle", "")
    ):
        raise ValueError("reviewer actual-preimage contract drifted")
    specs = value.get("state_specifications")
    sampler_sha = authority["module_sha256"]
    expected_calibration = _literal_state_specs(
        "development_calibration", sampler_sha
    )
    expected_validation = _literal_state_specs(
        "independent_validation", sampler_sha
    )
    if (
        specs.get("development_calibration") != expected_calibration
        or specs.get("independent_validation") != expected_validation
        or specs.get("development_calibration_sha256")
        != sha256_json(expected_calibration)
        or specs.get("independent_validation_sha256")
        != sha256_json(expected_validation)
        or specs.get("state_count_per_split") != 64
        or specs.get("actual_manifest_count_now") != 0
    ):
        raise ValueError("reviewer exact 128 state specs drifted")
    if value.get("model_fingerprint_authority") != {
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": (
            "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
        ),
        "model_source_sha256": (
            "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
        ),
        "decoder_source_sha256": (
            "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
        ),
        "encoder_source_sha256": (
            "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
        ),
        "formal_entrypoint": "Diffusion_Planner.forward(inputs)",
    }:
        raise ValueError("reviewer model fingerprint authority drifted")
    _review_registry(value.get("endpoint_registry"))
    topology = value.get("result_topology")
    if (
        topology.get("key_fields") != ["phase", "mode", "endpoint_id"]
        or topology.get("sequential_within_numeric_ids")
        != list(WITHIN_NUMERIC_IDS)
        or topology.get("batch8_within_numeric_ids")
        != list(WITHIN_NUMERIC_IDS)
        or topology.get("cross_mode_numeric_ids") != list(CROSS_NUMERIC_IDS)
        or topology.get("cross_only_ids_forbidden_in_within")
        != list(CROSS_ONLY_NUMERIC_IDS)
        or topology.get("hard_result_keys")
        != [list(key) for key in HARD_KEYS]
        or topology.get("state_denominator") != 64
        or topology.get("unknown_duplicate_or_omitted_key") != "fail_closed"
    ):
        raise ValueError("reviewer phase-aware result topology drifted")
    hard = value.get("typed_hard_evidence")
    if (
        type(hard) is not dict
        or hard.get("caller_status_or_within_boolean_accepted") is not False
        or set(hard)
        != {"fingerprints", "k8", "pool", "mask", "action", "split", "caller_status_or_within_boolean_accepted"}
    ):
        raise ValueError("reviewer typed hard-evidence contract drifted")
    decision = value.get("decision_table")
    if (
        decision.get("precedence")
        != [
            "authority_failure",
            "evidence_missing",
            "within_mode_generator_instability",
            "cross_mode_functional_drift",
            "PASS",
        ]
        or decision.get("weighted_total") is not False
        or decision.get("benefit_or_retraining_claim") is not False
        or "derived_sequential_within_pass" not in decision.get(
            "cross_entry", ""
        )
    ):
        raise ValueError("reviewer decision topology drifted")
    boundary = value.get("run_and_claim_boundary")
    for field in (
        "actual_input_manifest_materialization_count",
        "calibration_run_count",
        "repeat_model_run_count",
        "pool_run_count",
        "selector_run_count",
        "closed_loop_run_count",
        "fresh_run_count",
        "holdout_run_count",
        "training_run_count",
    ):
        if boundary.get(field) != 0:
            raise ValueError(f"reviewer nonzero boundary: {field}")
    for field in (
        "acquisition_authorized",
        "fresh_or_b4_outcome_read",
        "old_artifact_or_cas_written",
        "claim_authorized",
    ):
        if boundary.get(field) is not False:
            raise ValueError(f"reviewer false boundary drifted: {field}")
    return {
        "status": "passed_independent_executable_semantic_review_v3",
        "contract_payload_sha256": supplied,
        "state_spec_count": 128,
        "endpoint_count": 37,
        "phase_result_key_count": len(literal_expected_result_keys()),
        "input_module_sha256": authority["module_sha256"],
        "acquisition_authorized": False,
    }


def literal_expected_result_keys() -> tuple[tuple[str, str, str], ...]:
    keys = []
    for endpoint_id in WITHIN_NUMERIC_IDS:
        keys.append(("sequential_within", PHASE_MODE["sequential_within"], endpoint_id))
        keys.append(("batch8_within", PHASE_MODE["batch8_within"], endpoint_id))
    for endpoint_id in CROSS_NUMERIC_IDS:
        keys.append(("cross_mode", PHASE_MODE["cross_mode"], endpoint_id))
    keys.extend(HARD_KEYS)
    if len(keys) != len(set(keys)):
        raise ValueError("reviewer result keys duplicate")
    return tuple(keys)


def literal_decide_qualification_v3(
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    review_contract_literal_v3(contract)
    if type(receipt) is not dict or set(receipt) != {
        "schema_version",
        "contract_payload_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
        "numeric_evidence",
        "hard_evidence",
    }:
        raise ValueError("reviewer qualification receipt schema drifted")
    if (
        receipt["schema_version"] != QUALIFICATION_SCHEMA
        or receipt["contract_payload_sha256"]
        != contract["contract_payload_sha256"]
    ):
        raise ValueError("reviewer qualification authority drifted")
    for field in (
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
    ):
        _sha256(receipt[field], field)
    statuses = _literal_numeric_statuses(contract, receipt["numeric_evidence"])
    statuses.update(_literal_hard_statuses(contract, receipt))
    if set(statuses) != set(literal_expected_result_keys()):
        raise ValueError("reviewer qualification keyset drifted")
    values = set(statuses.values())
    if "authority_failure" in values:
        classification = "authority_failure"
        status = "BLOCK"
    elif "evidence_missing" in values:
        classification = "evidence_missing"
        status = "BLOCK"
    else:
        sequential = all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase == "sequential_within"
        )
        batch8 = all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase == "batch8_within"
        )
        if not sequential or not batch8:
            classification = "within_mode_generator_instability"
            status = "BLOCK"
        elif not all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase in {"cross_mode", "global"}
        ):
            classification = "cross_mode_functional_drift"
            status = "BLOCK"
        else:
            classification = "bounded_scope_no_trigger"
            status = "PASS"
    return {
        "status": status,
        "classification": classification,
        "derived_within_mode_pass": {
            "sequential_batch1_x8": all(
                value == "pass"
                for (phase, _mode, _endpoint), value in statuses.items()
                if phase == "sequential_within"
            ),
            "single_invocation_batch8": all(
                value == "pass"
                for (phase, _mode, _endpoint), value in statuses.items()
                if phase == "batch8_within"
            ),
        },
        "cross_mode_entered": all(
            value == "pass"
            for (phase, _mode, _endpoint), value in statuses.items()
            if phase in {"sequential_within", "batch8_within"}
        ),
        "derived_result_count": len(statuses),
        "caller_supplied_status_or_within_boolean_used": False,
    }


def _literal_numeric_statuses(
    contract: Mapping[str, Any],
    rows: Any,
) -> dict[tuple[str, str, str], str]:
    expected = {
        key
        for key in literal_expected_result_keys()
        if key[2] in set(WITHIN_NUMERIC_IDS).union(CROSS_ONLY_NUMERIC_IDS)
    }
    if type(rows) is not list or len(rows) != len(expected):
        raise ValueError("reviewer numeric evidence denominator drifted")
    state_ids = [
        row["state_spec_id"]
        for row in contract["state_specifications"]["independent_validation"]
    ]
    result = {}
    for row in rows:
        if type(row) is not dict or set(row) != {
            "phase",
            "mode",
            "endpoint_id",
            "state_values",
            "threshold",
            "threshold_authority",
        }:
            raise ValueError("reviewer numeric evidence schema drifted")
        key = (row["phase"], row["mode"], row["endpoint_id"])
        if key not in expected or key in result:
            raise ValueError("reviewer numeric key unknown or duplicate")
        if row["mode"] != PHASE_MODE[row["phase"]]:
            raise ValueError("reviewer numeric phase/mode drifted")
        state_values = row["state_values"]
        if (
            type(state_values) is not list
            or len(state_values) != 64
            or [
                item.get("state_spec_id") if type(item) is dict else None
                for item in state_values
            ]
            != state_ids
        ):
            raise ValueError("reviewer numeric state identity drifted")
        threshold = float(row["threshold"])
        if not math.isfinite(threshold) or threshold < 0:
            raise ValueError("reviewer threshold drifted")
        authority = {
            "schema_version": "camp_dp_v25_fair_pool_threshold_authority_v1",
            "phase": row["phase"],
            "mode": row["mode"],
            "endpoint_id": row["endpoint_id"],
            "calibration_state_count": 64,
            "threshold": threshold,
            "algorithm": (
                "q99_higher_then_10000_state_bootstrap_pcg64dxsm_"
                "seed825071_one_sided95_index9500_max_resolution_floor"
            ),
        }
        authority["authority_sha256"] = sha256_json(authority)
        if row["threshold_authority"] != authority:
            raise ValueError("reviewer threshold authority drifted")
        observed = []
        missing = False
        for item in state_values:
            if set(item) != {"state_spec_id", "value"}:
                raise ValueError("reviewer state-value schema drifted")
            if item["value"] is None:
                missing = True
            else:
                number = float(item["value"])
                if not math.isfinite(number):
                    missing = True
                else:
                    observed.append(number)
        if missing or len(observed) != 64:
            result[key] = "evidence_missing"
            continue
        k = sum(number > threshold for number in observed)
        upper = _literal_cp_upper(k, 64)
        if k <= 2 and upper <= 0.10:
            result[key] = "pass"
        elif row["phase"] == "cross_mode":
            result[key] = "cross_mode_functional_drift"
        else:
            result[key] = "within_mode_generator_instability"
    return result


def _literal_hard_statuses(
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[tuple[str, str, str], str]:
    hard = receipt["hard_evidence"]
    if type(hard) is not dict or set(hard) != {
        "fingerprints",
        "k8",
        "pool",
        "masks",
        "actions",
        "split_preflight",
    }:
        raise ValueError("reviewer hard evidence schema drifted")
    ids = [
        row["state_spec_id"]
        for row in contract["state_specifications"]["independent_validation"]
    ]
    result = {}
    expected_fp = {
        "fixed_dp_head": FIXED_DP_HEAD,
        "generator": GENERATOR_NAME,
        "candidate_k": 8,
        "checkpoint_sha256": (
            "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
        ),
        "model_source_sha256": (
            "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
        ),
        "decoder_source_sha256": (
            "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
        ),
        "encoder_source_sha256": (
            "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
        ),
        "route_asset_sha256": ROUTE_ASSET_SHA256,
        "map_geometry_sha256": MAP_SHA256,
        "dtype": "float32",
    }
    fp = hard["fingerprints"]
    if type(fp) is not dict or set(fp) != {"expected", "observed_by_mode"}:
        raise ValueError("reviewer fingerprint schema drifted")
    observed = fp["observed_by_mode"]
    if type(observed) is not dict or set(observed) != {
        "sequential_batch1_x8",
        "single_invocation_batch8",
    }:
        raise ValueError("reviewer fingerprint modes drifted")
    for phase in ("sequential_within", "batch8_within"):
        mode = PHASE_MODE[phase]
        result[(phase, mode, "authority.fingerprint")] = (
            "pass"
            if fp["expected"] == expected_fp and observed[mode] == expected_fp
            else "authority_failure"
        )
    k8 = hard["k8"]
    if type(k8) is not dict or set(k8) != set(observed):
        raise ValueError("reviewer K8 modes drifted")
    for phase in ("sequential_within", "batch8_within"):
        mode = PHASE_MODE[phase]
        rows = k8[mode]
        if type(rows) is not list or len(rows) != 64:
            raise ValueError("reviewer K8 denominator drifted")
        good = True
        for state_id, row in zip(ids, rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "all_finite",
                "row_sha256",
            }:
                raise ValueError("reviewer K8 schema drifted")
            shas = row["row_sha256"]
            good &= (
                row["state_spec_id"] == state_id
                and row["all_finite"] is True
                and type(shas) is list
                and len(shas) == 8
                and len(set(shas)) == 8
            )
            if type(shas) is list:
                for digest in shas:
                    _sha256(digest, "reviewer K8 row")
        result[(phase, mode, "k8.finite_and_diverse")] = (
            "pass" if good else "within_mode_generator_instability"
        )
    pool_good = True
    pool = hard["pool"]
    if type(pool) is not list or len(pool) != 64:
        raise ValueError("reviewer pool denominator drifted")
    for state_id, row in zip(ids, pool):
        if type(row) is not dict or set(row) != {
            "state_spec_id",
            "pre_tensor_sha256",
            "post_tensor_sha256",
            "dp_model_call_count_after_pool",
            "latent_replacement_count_after_pool",
            "candidate_generation_count_after_pool",
        }:
            raise ValueError("reviewer pool schema drifted")
        pool_good &= (
            row["state_spec_id"] == state_id
            and _sha256(row["pre_tensor_sha256"], "pre") == _sha256(row["post_tensor_sha256"], "post")
            and row["dp_model_call_count_after_pool"] == 0
            and row["latent_replacement_count_after_pool"] == 0
            and row["candidate_generation_count_after_pool"] == 0
        )
    result[("cross_mode", PHASE_MODE["cross_mode"], "pool.tensor_immutability_and_zero_calls")] = (
        "pass" if pool_good else "authority_failure"
    )
    for arm in ("static14d", "scene14d"):
        mask_rows = hard["masks"].get(arm) if type(hard["masks"]) is dict else None
        if type(mask_rows) is not list or len(mask_rows) != 64:
            raise ValueError("reviewer mask denominator drifted")
        mask_good = True
        for state_id, row in zip(ids, mask_rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "sequential_mask",
                "batch8_mask",
            }:
                raise ValueError("reviewer mask schema drifted")
            left = np.asarray(row["sequential_mask"])
            right = np.asarray(row["batch8_mask"])
            mask_good &= (
                row["state_spec_id"] == state_id
                and left.shape == (8,)
                and right.shape == (8,)
                and left.dtype == np.bool_
                and right.dtype == np.bool_
                and np.array_equal(left, right)
            )
        result[("cross_mode", PHASE_MODE["cross_mode"], f"functional.{arm}.mask_eligibility")] = (
            "pass" if mask_good else "cross_mode_functional_drift"
        )
        action_rows = hard["actions"].get(arm) if type(hard["actions"]) is dict else None
        if type(action_rows) is not list or len(action_rows) != 64:
            raise ValueError("reviewer action denominator drifted")
        action_good = True
        for state_id, row in zip(ids, action_rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "sequential_selected_index",
                "batch8_selected_index",
                "sequential_action_80x4",
                "batch8_action_80x4",
                "sequential_executable",
                "batch8_executable",
                "sequential_terminal",
                "batch8_terminal",
            }:
                raise ValueError("reviewer action schema drifted")
            comparison = _literal_action(
                row["sequential_action_80x4"],
                row["batch8_action_80x4"],
                row["sequential_executable"],
                row["batch8_executable"],
                row["sequential_terminal"],
                row["batch8_terminal"],
            )
            action_good &= (
                row["state_spec_id"] == state_id
                and type(row["sequential_selected_index"]) is int
                and type(row["batch8_selected_index"]) is int
                and 0 <= row["sequential_selected_index"] < 8
                and 0 <= row["batch8_selected_index"] < 8
                and (
                    row["sequential_selected_index"]
                    == row["batch8_selected_index"]
                    or comparison
                )
            )
        result[("cross_mode", PHASE_MODE["cross_mode"], f"functional.{arm}.selected_index_action")] = (
            "pass" if action_good else "cross_mode_functional_drift"
        )
    split = hard["split_preflight"]
    if type(split) is not dict or set(split) != {
        "status",
        "receipt_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
    }:
        raise ValueError("reviewer split schema drifted")
    split_good = (
        split["status"] == "passed_before_first_model_pool_selector_call"
        and _sha256(split["receipt_sha256"], "preflight") == split["receipt_sha256"]
        and split["contract_root_sha256"] == receipt["contract_root_sha256"]
        and split["contract_review_root_sha256"] == receipt["contract_review_root_sha256"]
        and split["acquisition_authority_root_sha256"] == receipt["acquisition_authority_root_sha256"]
    )
    result[("global", "none", "split.input_only_clone_nonoverlap")] = (
        "pass" if split_good else "authority_failure"
    )
    return result


def literal_validate_preflight_receipt_v3(
    receipt: Mapping[str, Any],
    *,
    expected_acquisition_authority_root_sha256: str,
    expected_contract_root_sha256: str,
    expected_contract_review_root_sha256: str,
    calibration_specs: Sequence[Mapping[str, Any]],
    validation_specs: Sequence[Mapping[str, Any]],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    prepared_runtime_cases_bytes: bytes,
    actual_input_tensors_by_state_id: Mapping[
        str, Mapping[str, np.ndarray]
    ],
) -> dict[str, Any]:
    if type(receipt) is not dict or set(receipt) != {
        "schema_version",
        "acquisition_authority",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "b4_forbidden_manifest_authority",
        "calibration_manifests",
        "validation_manifests",
        "model_pool_selector_call_count_before_receipt",
        "within_calibration_overlap_count",
        "within_validation_overlap_count",
        "cross_split_overlap_count",
        "b4_overlap_count",
        "no_drop_no_replacement",
        "status",
    }:
        raise ValueError("reviewer preflight receipt exact schema drifted")
    if (
        receipt["schema_version"]
        != "camp_dp_v25_fair_pool_input_only_preflight_receipt_v2"
    ):
        raise ValueError("reviewer preflight schema version drifted")
    authority = receipt["acquisition_authority"]
    if type(authority) is not dict or set(authority) != {
        "schema_version",
        "status",
        "authority_artifact_path",
        "authority_artifact_root_sha256",
        "decision_sha256",
        "authorized_contract_root_sha256",
        "authorized_contract_review_root_sha256",
        "acquisition_authorized",
        "fresh_or_holdout_authorized",
    }:
        raise ValueError("reviewer acquisition authority schema drifted")
    if (
        authority["schema_version"]
        != "camp_dp_v25_fair_pool_acquisition_authority_binding_v1"
        or authority["status"]
        != "authorized_by_future_versioned_high_control"
        or authority["acquisition_authorized"] is not True
        or authority["fresh_or_holdout_authorized"] is not False
        or type(authority["authority_artifact_path"]) is not str
        or not authority["authority_artifact_path"].startswith(
            "/root/autodl-tmp/"
        )
        or authority["authority_artifact_root_sha256"]
        != expected_acquisition_authority_root_sha256
        or authority["authorized_contract_root_sha256"]
        != expected_contract_root_sha256
        or authority["authorized_contract_review_root_sha256"]
        != expected_contract_review_root_sha256
    ):
        raise ValueError("reviewer acquisition authority binding drifted")
    for field in (
        "authority_artifact_root_sha256",
        "decision_sha256",
        "authorized_contract_root_sha256",
        "authorized_contract_review_root_sha256",
    ):
        _sha256(authority[field], f"reviewer {field}")
    if receipt["contract_root_sha256"] != expected_contract_root_sha256:
        raise ValueError("reviewer contract root not authorized")
    if (
        receipt["contract_review_root_sha256"]
        != expected_contract_review_root_sha256
    ):
        raise ValueError("reviewer contract review root not authorized")
    if receipt["model_pool_selector_call_count_before_receipt"] != 0:
        raise ValueError("reviewer preflight after forbidden call")
    if receipt["no_drop_no_replacement"] is not True:
        raise ValueError("reviewer no-drop policy drifted")
    _exact_bytes(route_asset_bytes, ROUTE_ASSET_SHA256, "reviewer route")
    _exact_bytes(map_asset_bytes, MAP_SHA256, "reviewer map")
    calibration = _literal_manifest_list(
        receipt["calibration_manifests"],
        specs=calibration_specs,
        split="development_calibration",
        actual_input_tensors_by_state_id=actual_input_tensors_by_state_id,
    )
    validation = _literal_manifest_list(
        receipt["validation_manifests"],
        specs=validation_specs,
        split="independent_validation",
        actual_input_tensors_by_state_id=actual_input_tensors_by_state_id,
    )
    forbidden = _literal_b4_forbidden(prepared_runtime_cases_bytes)
    expected_b4 = {
        "preopen_path": B4_PREOPEN_PATH,
        "preopen_root_sha256": B4_PREOPEN_ROOT,
        "prepared_runtime_cases_sha256": B4_PREPARED_SHA,
        "derived_forbidden_manifest_sha256": forbidden["manifest_sha256"],
        "derived_forbidden_clone_key_count": 100,
        "derived_inside_validator_from_exact_bytes": True,
    }
    if receipt["b4_forbidden_manifest_authority"] != expected_b4:
        raise ValueError("reviewer B4 exact-byte authority drifted")
    calibration_keys = [row["clone_key_sha256"] for row in calibration]
    validation_keys = [row["clone_key_sha256"] for row in validation]
    counts = {
        "within_calibration_overlap_count": (
            len(calibration_keys) - len(set(calibration_keys))
        ),
        "within_validation_overlap_count": (
            len(validation_keys) - len(set(validation_keys))
        ),
        "cross_split_overlap_count": len(
            set(calibration_keys).intersection(validation_keys)
        ),
        "b4_overlap_count": len(
            set(calibration_keys + validation_keys).intersection(
                forbidden["clone_keys_sorted"]
            )
        ),
    }
    for field, expected in counts.items():
        if receipt[field] != expected or expected != 0:
            raise ValueError(f"reviewer {field} must be zero")
    if receipt["status"] != "passed_before_first_model_pool_selector_call":
        raise ValueError("reviewer preflight status drifted")
    return dict(receipt)


def _literal_manifest_list(
    supplied: Any,
    *,
    specs: Sequence[Mapping[str, Any]],
    split: str,
    actual_input_tensors_by_state_id: Mapping[
        str, Mapping[str, np.ndarray]
    ],
) -> list[dict[str, Any]]:
    if type(supplied) is not list or len(supplied) != 64:
        raise ValueError("reviewer manifest denominator drifted")
    module_sha = hashlib.sha256((ROOT / INPUT_MODULE_RELATIVE).read_bytes()).hexdigest()
    expected_specs = _literal_state_specs(split, module_sha)
    if list(specs) != expected_specs:
        raise ValueError("reviewer state spec authority drifted")
    expected = []
    for spec in expected_specs:
        state_id = spec["state_spec_id"]
        if state_id not in actual_input_tensors_by_state_id:
            raise ValueError("reviewer actual input preimage missing")
        expected.append(
            _literal_manifest(
                spec,
                actual_input_tensors_by_state_id[state_id],
            )
        )
    if supplied != expected:
        raise ValueError("reviewer manifest semantic reconstruction drifted")
    return expected


def _literal_manifest(
    spec: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    source_scene = _literal_source_scene(spec)
    tensor_manifest = _literal_tensor_bundle(
        arrays,
        source_scene["source_scene_sha256"],
    )
    latent_manifest = _literal_latent(int(spec["latent_seed"]))
    clone_payload = _literal_clone_payload(
        map_sha=MAP_SHA256,
        source_sha=source_scene["scenario_source_content_sha256"],
        spawn=source_scene["spawn_pose"],
        goal=source_scene["goal_pose"],
        route=source_scene["ordered_route_polyline_xy_m"],
        actors=source_scene["dynamic_actors_initial"],
    )
    result = {
        "schema_version": "camp_dp_v25_fair_pool_input_only_manifest_v2",
        "split": spec["split"],
        "state_spec_id": spec["state_spec_id"],
        "state_spec_sha256": spec["state_spec_sha256"],
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "latent_seed": spec["latent_seed"],
        "source_scene": source_scene,
        "actual_input_tensor_manifest": tensor_manifest,
        "actual_state_sha256": source_scene["source_scene_sha256"],
        "actual_latent_tensor_manifest": latent_manifest,
        "clone_payload": clone_payload,
        "clone_key_sha256": sha256_json(clone_payload),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def _literal_source_scene(spec: Mapping[str, Any]) -> dict[str, Any]:
    actors = _literal_actors(int(spec["scenario_seed"]), str(spec["tier"]))
    policy = (
        "numpy_Generator_PCG64DXSM_scenario_seed;"
        "count_by_tier_0_2_4_6;route_fraction_even_slots_plus_"
        "uniform_minus_0_01_plus_0_01;lateral_offset_choice_"
        "minus_1_5_plus_1_5;speed_uniform_3_12;"
        "vehicle_length_4_5_width_2_0"
    )
    content = {
        "schema_version": "camp_dp_v25_fair_pool_source_content_v1",
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "tier": spec["tier"],
        "route_lanelet_ids": list(ROUTE_LANELET_IDS),
        "spawn_pose": dict(SPAWN_POSE),
        "goal_pose": dict(GOAL_POSE),
        "ordered_route_polyline_xy_m": [list(row) for row in ROUTE_WORLD_XY_M],
        "dynamic_actors_initial": actors,
        "actor_generation_policy": policy,
    }
    result = {
        "schema_version": "camp_dp_v25_fair_pool_deterministic_source_scene_v1",
        "state_spec_id": spec["state_spec_id"],
        "state_spec_sha256": spec["state_spec_sha256"],
        "source_state_ordinal": spec["source_state_ordinal"],
        "split": spec["split"],
        "family": spec["family"],
        "tier": spec["tier"],
        "scenario_seed": spec["scenario_seed"],
        "map_geometry_sha256": MAP_SHA256,
        "route_asset_sha256": ROUTE_ASSET_SHA256,
        "route_lanelet_ids": list(ROUTE_LANELET_IDS),
        "spawn_pose": dict(SPAWN_POSE),
        "goal_pose": dict(GOAL_POSE),
        "ordered_route_polyline_xy_m": [list(row) for row in ROUTE_WORLD_XY_M],
        "dynamic_actors_initial": actors,
        "actor_generation_policy": policy,
        "scenario_source_content_sha256": sha256_json(content),
    }
    result["source_scene_sha256"] = sha256_json(result)
    return result


def _literal_actors(seed: int, tier: str) -> list[dict[str, Any]]:
    count = TIER_COUNTS[tier]
    rng = np.random.Generator(np.random.PCG64DXSM(seed))
    route = np.asarray(ROUTE_WORLD_XY_M, dtype=np.float64)
    segments = np.diff(route, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(cumulative[-1])
    result = []
    for index in range(count):
        fraction = (index + 1) / (count + 1)
        fraction += float(rng.uniform(-0.01, 0.01))
        arc = min(total, max(0.0, fraction * total))
        segment_index = min(
            len(lengths) - 1,
            int(np.searchsorted(cumulative[1:], arc, side="right")),
        )
        ratio = (arc - cumulative[segment_index]) / lengths[segment_index]
        point = route[segment_index] + ratio * segments[segment_index]
        tangent = segments[segment_index] / lengths[segment_index]
        normal = np.asarray([-tangent[1], tangent[0]])
        lateral = -1.5 if int(rng.integers(0, 2)) == 0 else 1.5
        position = point + lateral * normal
        result.append(
            {
                "class": "vehicle",
                "length_m": 4.5,
                "width_m": 2.0,
                "x_m": float(position[0]),
                "y_m": float(position[1]),
                "heading_rad": float(math.atan2(tangent[1], tangent[0])),
                "speed_mps": float(rng.uniform(3.0, 12.0)),
            }
        )
    return result


def _literal_tensor_bundle(
    arrays: Mapping[str, np.ndarray],
    source_scene_sha: str,
) -> dict[str, Any]:
    if type(arrays) is not dict or not arrays:
        raise ValueError("reviewer tensor bundle missing")
    entries = []
    for name in sorted(arrays):
        array = np.asarray(arrays[name])
        if array.dtype.kind not in "biuf" or not np.isfinite(array).all():
            raise ValueError("reviewer tensor preimage invalid")
        contiguous = np.ascontiguousarray(array)
        entries.append(
            {
                "name": name,
                "dtype": contiguous.dtype.str,
                "shape": list(contiguous.shape),
                "tensor_sha256": hashlib.sha256(
                    contiguous.tobytes(order="C")
                ).hexdigest(),
            }
        )
    result = {
        "schema_version": "camp_dp_v25_tensor_bundle_preimage_manifest_v1",
        "source_scene_sha256": source_scene_sha,
        "fixed_dp_head": FIXED_DP_HEAD,
        "tensor_converter_path": "scenario_generation/tensor_converter.py",
        "tensor_converter_sha256": (
            "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
        ),
        "tensor_converter_entrypoint": "to_model_tensors",
        "tensor_order": [row["name"] for row in entries],
        "tensors": entries,
    }
    result["bundle_sha256"] = sha256_json(result)
    return result


def _literal_latent(seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)
    result = {
        "schema_version": "camp_dp_v25_batched_k8_latent_manifest_v1",
        "policy": (
            "row0_zero_rows1_7_numpy_default_rng_pcg64_"
            "standard_normal_float32_v1"
        ),
        "seed": seed,
        "bit_generator": "PCG64",
        "dtype": LATENT_DTYPE,
        "shape": list(LATENT_SHAPE),
        "row0_all_zero": bool(np.all(latent[0] == 0.0)),
        "tensor_sha256": hashlib.sha256(
            latent.astype(LATENT_DTYPE, copy=False).tobytes(order="C")
        ).hexdigest(),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def _literal_b4_forbidden(raw: bytes) -> dict[str, Any]:
    _exact_bytes(raw, B4_PREPARED_SHA, "reviewer B4 prepared cases")
    try:
        cases = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("reviewer B4 bytes invalid JSON") from error
    if type(cases) is not list or len(cases) != 100:
        raise ValueError("reviewer B4 denominator drifted")
    entries = []
    for ordinal, prepared in enumerate(cases):
        if type(prepared) is not dict or prepared.get("identity_ordinal") != ordinal:
            raise ValueError("reviewer B4 ordinal drifted")
        if (
            prepared.get("model_loaded") is not False
            or prepared.get("candidate_generation_executed") is not False
            or prepared.get("training_executed") is not False
            or prepared.get("outcome_fields_consumed") != []
        ):
            raise ValueError("reviewer B4 outcome-free boundary drifted")
        case = prepared.get("case")
        route_spec = case.get("route_spec") if type(case) is dict else None
        mapped = case.get("mapped_signal_authority") if type(case) is dict else None
        semantic = mapped.get("semantic_clone_payload") if type(mapped) is dict else None
        semantic_sha = mapped.get("semantic_clone_sha256") if type(mapped) is dict else None
        if (
            case.get("split") != "fresh_b4"
            or case.get("outcome_blind") is not True
            or case.get("holdout_outcome_consumed") is not False
            or type(route_spec) is not dict
            or type(semantic) is not dict
            or semantic_sha != sha256_json(semantic)
        ):
            raise ValueError("reviewer B4 case authority drifted")
        start = route_spec["start_pose"]
        goal = route_spec["goal_pose"]
        clone_payload = _literal_clone_payload(
            map_sha=_sha256(case["source_map_sha256"], "reviewer B4 map"),
            source_sha=_sha256(semantic_sha, "reviewer B4 semantic"),
            spawn={
                "x_m": float(start[0]),
                "y_m": float(start[1]),
                "z_m": 0.0,
                "heading_rad": float(start[2]),
            },
            goal={
                "x_m": float(goal[0]),
                "y_m": float(goal[1]),
                "z_m": 0.0,
                "heading_rad": float(goal[2]),
            },
            route=prepared["route_polyline_world_m"],
            actors=[_literal_b4_actor(actor) for actor in case["actors"]],
        )
        entries.append(
            {
                "identity_ordinal": ordinal,
                "scenario_identity_sha256": _sha256(
                    prepared["scenario_identity_sha256"],
                    "reviewer B4 identity",
                ),
                "clone_key_sha256": sha256_json(clone_payload),
            }
        )
    keys = [row["clone_key_sha256"] for row in entries]
    if len(set(keys)) != 100:
        raise ValueError("reviewer B4 clone keys duplicate")
    result = {
        "schema_version": (
            "camp_dp_v25_fresh_b4_input_only_forbidden_clone_manifest_v1"
        ),
        "source": {
            "preopen_path": B4_PREOPEN_PATH,
            "preopen_root_sha256": B4_PREOPEN_ROOT,
            "relative_path": "fresh_b4_prepared_runtime_cases.json",
            "file_sha256": B4_PREPARED_SHA,
            "case_count": 100,
            "outcome_fields_read": [],
        },
        "entries": entries,
        "clone_keys_sorted": sorted(keys),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def _literal_b4_actor(value: Mapping[str, Any]) -> dict[str, Any]:
    xy = value["initial_xy"]
    tangent = value["route_tangent"]
    normal = value["route_normal"]
    longitudinal = float(value["longitudinal_speed_mps"])
    lateral = float(value["lateral_speed_mps"])
    return {
        "class": str(value["agent_type"]),
        "length_m": float(value["length_m"]),
        "width_m": float(value["width_m"]),
        "x_m": float(xy[0]),
        "y_m": float(xy[1]),
        "heading_rad": float(value["initial_heading_rad"]),
        "speed_mps": float(
            math.hypot(
                longitudinal * float(tangent[0]) + lateral * float(normal[0]),
                longitudinal * float(tangent[1]) + lateral * float(normal[1]),
            )
        ),
    }


def _literal_clone_payload(
    *,
    map_sha: str,
    source_sha: str,
    spawn: Mapping[str, Any],
    goal: Mapping[str, Any],
    route: Sequence[Sequence[float]],
    actors: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    route_quantized = _literal_resample_route(route)
    actor_rows = sorted(
        [_literal_actor_quantized(row) for row in actors],
        key=lambda row: (
            row["class"],
            row["length_mm"],
            row["width_mm"],
            row["x_mm"],
            row["y_mm"],
            row["heading_1e4rad"],
            row["speed_mmps"],
        ),
    )
    return {
        "schema_version": "camp_dp_v25_id_free_clone_key_payload_v1",
        "units": {
            "position": "integer_millimetres",
            "heading": "integer_1e-4_radians_wrapped_minus_pi_inclusive",
            "speed": "integer_millimetres_per_second",
            "dimensions": "integer_millimetres",
            "route_resample_spacing": "0.5_m_with_exact_final_endpoint",
        },
        "map_geometry_sha256": _sha256(map_sha, "reviewer clone map"),
        "ordered_route_geometry_sha256": sha256_json(route_quantized),
        "spawn_pose_quantized": _literal_pose(spawn),
        "goal_pose_quantized": _literal_pose(goal),
        "route_polyline_resampled_0_5m_quantized": route_quantized,
        "dynamic_actor_initial_state_sorted": actor_rows,
        "scenario_source_content_sha256": _sha256(
            source_sha, "reviewer clone source"
        ),
    }


def _literal_resample_route(
    points: Sequence[Sequence[float]],
) -> list[list[int]]:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 2 or len(array) < 2 or not np.isfinite(array).all():
        raise ValueError("reviewer route points invalid")
    segments = np.diff(array, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    if np.any(lengths <= 1e-12):
        raise ValueError("reviewer route segment invalid")
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(cumulative[-1])
    samples = [0.5 * index for index in range(int(math.floor(total / 0.5)) + 1)]
    if total - samples[-1] > 1e-12:
        samples.append(total)
    else:
        samples[-1] = total
    result = []
    segment_index = 0
    for distance in samples:
        while segment_index + 1 < len(cumulative) and distance > cumulative[segment_index + 1] + 1e-12:
            segment_index += 1
        ratio = (distance - cumulative[segment_index]) / lengths[segment_index]
        point = array[segment_index] + min(1.0, max(0.0, ratio)) * segments[segment_index]
        result.append([_quantize(point[0], "0.001"), _quantize(point[1], "0.001")])
    return result


def _literal_pose(value: Mapping[str, Any]) -> dict[str, int]:
    return {
        "x_mm": _quantize(float(value["x_m"]), "0.001"),
        "y_mm": _quantize(float(value["y_m"]), "0.001"),
        "z_mm": _quantize(float(value["z_m"]), "0.001"),
        "heading_1e4rad": _quantize(
            (float(value["heading_rad"]) + math.pi) % (2 * math.pi) - math.pi,
            "0.0001",
        ),
    }


def _literal_actor_quantized(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "class": str(value["class"]),
        "length_mm": _quantize(float(value["length_m"]), "0.001"),
        "width_mm": _quantize(float(value["width_m"]), "0.001"),
        "x_mm": _quantize(float(value["x_m"]), "0.001"),
        "y_mm": _quantize(float(value["y_m"]), "0.001"),
        "heading_1e4rad": _quantize(
            (float(value["heading_rad"]) + math.pi) % (2 * math.pi) - math.pi,
            "0.0001",
        ),
        "speed_mmps": _quantize(float(value["speed_mps"]), "0.001"),
    }


def _quantize(value: float, quantum: str) -> int:
    if not math.isfinite(value):
        raise ValueError("reviewer quantized value nonfinite")
    return int(
        (Decimal(str(value)) / Decimal(quantum)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _exact_bytes(value: Any, expected_sha: str, label: str) -> bytes:
    if type(value) is not bytes or hashlib.sha256(value).hexdigest() != expected_sha:
        raise ValueError(f"{label} SHA drifted")
    return value


def _review_registry(rows: Any) -> None:
    expected_ids = set(WITHIN_NUMERIC_IDS).union(CROSS_ONLY_NUMERIC_IDS).union(
        {
            "functional.static14d.mask_eligibility",
            "functional.static14d.selected_index_action",
            "functional.scene14d.mask_eligibility",
            "functional.scene14d.selected_index_action",
            "k8.finite_and_diverse",
            "authority.fingerprint",
            "pool.tensor_immutability_and_zero_calls",
            "split.input_only_clone_nonoverlap",
        }
    )
    if type(rows) is not list or len(rows) != 37:
        raise ValueError("reviewer endpoint count drifted")
    actual = {row.get("id") for row in rows if type(row) is dict}
    if actual != expected_ids or len(actual) != len(rows):
        raise ValueError("reviewer endpoint ID registry drifted")
    for row in rows:
        endpoint_id = row["id"]
        if endpoint_id in CROSS_ONLY_NUMERIC_IDS or endpoint_id.startswith("functional.") or endpoint_id == "pool.tensor_immutability_and_zero_calls":
            phases = [["cross_mode", PHASE_MODE["cross_mode"]]]
        elif endpoint_id == "split.input_only_clone_nonoverlap":
            phases = [["global", "none"]]
        elif endpoint_id in {"k8.finite_and_diverse", "authority.fingerprint"}:
            phases = [
                ["sequential_within", PHASE_MODE["sequential_within"]],
                ["batch8_within", PHASE_MODE["batch8_within"]],
            ]
        else:
            phases = [
                ["sequential_within", PHASE_MODE["sequential_within"]],
                ["batch8_within", PHASE_MODE["batch8_within"]],
                ["cross_mode", PHASE_MODE["cross_mode"]],
            ]
        if row.get("applicable_phase_mode") != phases or row.get("caller_status_accepted") is not False:
            raise ValueError(f"reviewer endpoint applicability drifted: {endpoint_id}")
        inherited = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "applicable_phase_mode",
                "caller_status_accepted",
                "inherited_v2_row_sha256",
            }
        }
        inherited["within_mode_required"] = True
        inherited["cross_mode_required"] = True
        expected_inherited_sha = V2_ENDPOINT_ROW_SHA256[endpoint_id]
        if (
            row.get("inherited_v2_row_sha256") != expected_inherited_sha
            or sha256_json(inherited) != expected_inherited_sha
        ):
            raise ValueError(
                f"reviewer endpoint formula/schema drifted: {endpoint_id}"
            )
        if "within_mode_required" in row or "cross_mode_required" in row:
            raise ValueError("reviewer obsolete endpoint booleans remain")


def _literal_state_specs(split: str, sampler_sha: str) -> list[dict[str, Any]]:
    base = 0 if split == "development_calibration" else 64
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    rows = []
    for index in range(64):
        payload = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": sampler_sha,
            "route_asset_sha256": ROUTE_ASSET_SHA256,
            "map_geometry_sha256": MAP_SHA256,
            "family": "four_track_highway",
            "tier": tiers[index % 4],
            "scenario_seed": scenario_base + index,
            "latent_seed": latent_base + index,
            "latent_policy": (
                "row0_zero_rows1_7_numpy_default_rng_pcg64_"
                "standard_normal_float32_v1"
            ),
            "candidate_k": 8,
            "independent_statistical_unit": "state",
        }
        payload["state_spec_sha256"] = sha256_json(payload)
        rows.append(payload)
    return rows


def _literal_cp_upper(k: int, n: int) -> float:
    if type(k) is not int or type(n) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError("reviewer CP arguments drifted")
    if k == 0:
        return float(1.0 - 0.05 ** (1.0 / n))
    if k == n:
        return 1.0
    return float(beta.ppf(0.95, k + 1, n - k))


def _literal_action(
    left: Any,
    right: Any,
    left_executable: Any,
    right_executable: Any,
    left_terminal: Any,
    right_terminal: Any,
) -> bool:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != (80, 4) or b.shape != (80, 4) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("reviewer action array drifted")
    if left_executable not in {"executable", "not_executable"} or right_executable not in {"executable", "not_executable"}:
        raise ValueError("reviewer executable enum drifted")
    if left_terminal not in {"complete", "terminal_failure"} or right_terminal not in {"complete", "terminal_failure"}:
        raise ValueError("reviewer terminal enum drifted")
    xy = np.linalg.norm(a[:, :2] - b[:, :2], axis=1)
    heading = np.abs((a[:, 2] - b[:, 2] + math.pi) % (2 * math.pi) - math.pi)
    speed = np.abs(a[:, 3] - b[:, 3])
    return bool(
        float(np.max(xy)) <= 0.05
        and float(np.max(heading)) <= 0.01
        and float(np.max(speed)) <= 0.05
        and left_executable == right_executable
        and left_terminal == right_terminal
    )


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
