from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np

import pytest

from camp_core.integrations import diffusion_planner_v25_full_r_authority as authority
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (
    CRITICAL_IMPLEMENTATION_PATHS,
)
from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES
from camp_core.integrations.diffusion_planner_v25_causal_evidence_store import (
    externalize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
    canonical_json_sha256,
)
from scripts.integrations import (
    review_diffusion_planner_v25_controlled_training_corpus as corpus_reviewer,
    review_diffusion_planner_v25_full_config_preflight as full_config_reviewer,
)


def _receipt() -> dict[str, object]:
    authority: dict[str, object] = {
        "schema_version": "camp_dp_v25_full_config_receipt_v1",
        "scenario_id": "a" * 64,
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "route_identity_sha256": "b" * 64,
        "canonical_semantic_clone_sha256": "c" * 64,
        "signal_source_chain_sha256": None,
        "map_sha256": "d" * 64,
        "route_sha256": "e" * 64,
        "fixed_dp_head": full_config_reviewer.FIXED_DP_HEAD,
        "fixed_dp_checkpoint_sha256": "f" * 64,
        "fixed_dp_args_sha256": "1" * 64,
        "generation_scales_sha256": "2" * 64,
        "static_weights_sha256": "3" * 64,
        "selector_role": "static14d",
        "seed": full_config_reviewer.EXPECTED_SEED,
        "corpus_steps": full_config_reviewer.CORPUS_STEPS,
        "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
        "context_mode": "no_v2i",
        "selector_training_execution_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }
    return {
        **authority,
        "config_authority_sha256": full_config_reviewer._oracle_sha256(authority),
    }


def _snapshot() -> dict[str, object]:
    scenario_sha = "a" * 64
    route_sha = "b" * 64
    source_chain_sha = "c" * 64
    semantic_sha = "d" * 64
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidate_rows = [
        hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest()
        for row in candidates
    ]
    tensor_sha = hashlib.sha256(
        np.ascontiguousarray(candidates).tobytes()
    ).hexdigest()
    default = candidates[0]
    default_sha = hashlib.sha256(np.ascontiguousarray(default).tobytes()).hexdigest()
    route_lanes = np.zeros((25, 20, 33), dtype=np.float32)
    route_speed = np.ones((25, 1), dtype=np.float32)
    route_has_speed = np.ones((25, 1), dtype=np.bool_)
    causal_evidence = {
        "schema_version": "camp_dp_v25_bounded_causal_evidence_v1",
        "ego_current_state": np.zeros(10, dtype=np.float32).tolist(),
        "ego_shape": np.asarray([2.8, 4.8, 2.0], dtype=np.float32).tolist(),
        "neighbor_agents_past": np.zeros((32, 31, 11), dtype=np.float32).tolist(),
        "neighbor_valid_mask": np.zeros(32, dtype=np.bool_).tolist(),
        "candidate_neighbor_predictions": np.zeros(
            (8, 32, 80, 4), dtype=np.float32
        ).tolist(),
        "static_objects": np.zeros((5, 10), dtype=np.float32).tolist(),
        "route_lanes": route_lanes.tolist(),
        "route_lanes_speed_limit": route_speed.tolist(),
        "route_lanes_has_speed_limit": route_has_speed.tolist(),
        "signal_mask": np.ones(8, dtype=np.bool_).tolist(),
        "fixed_dp_planned_red_light_cost": np.zeros(8).tolist(),
    }
    runtime_receipt = {
        "schema_version": RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
        "scenario_id": scenario_sha,
        "tick_index": 0,
        "decision_time_s": 0.0,
        "source_mode": "same_tick_no_signal_rule_no_v2i",
        "current_phase": "none",
        "route_geometry_sha256": route_sha,
        "route_lanelet_ids": [1],
        "traffic_light_regulatory_element_ids": [],
        "source_chain_sha256": source_chain_sha,
        "semantic_clone_sha256": semantic_sha,
        "phase_remaining_available": False,
        "source_valid": True,
        "applicable": False,
    }
    causal_input = {
        "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
        "source_state": "not_applicable",
        "source_valid": True,
        "applicable": False,
        "current_phase": "none",
        "decision_time_s": 0.0,
        "ego_position_world_m": None,
        "ego_heading_rad": None,
        "regulatory_element_id": None,
        "stop_line_id": None,
        "stop_line_geometry_world_m": None,
        "stop_line_geometry_ego_m": None,
        "stop_line_geometry_sha256": None,
        "route_tangent_world": None,
        "route_tangent_ego": None,
        "route_geometry_sha256": route_sha,
        "route_arc_m": None,
        "source_chain_sha256": source_chain_sha,
        "runtime_receipt": runtime_receipt,
        "runtime_receipt_sha256": canonical_json_sha256(runtime_receipt),
    }
    source_complete = {name: True for name in RAW_FEATURE_NAMES}
    source_complete["traffic_signal_phase_remaining_s"] = False
    return {
        "schema_version": corpus_reviewer.SNAPSHOT_SCHEMA_VERSION,
        "feature_payload": {
            "atom_matrix": np.zeros((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "atom_source_valid_mask": np.ones((8, 14), dtype=np.bool_).tolist(),
            "atom_applicable_mask": np.asarray(
                [[column not in (10, 12) for column in range(14)]] * 8,
                dtype=np.bool_,
            ).tolist(),
            "physical_feasible_mask": [True] * 8,
            "candidate_row_sha256": candidate_rows,
            "candidate_tensor": candidates.tolist(),
            "default_output": default.tolist(),
            "causal_evidence": causal_evidence,
            "raw_context": {name: 0.0 for name in RAW_FEATURE_NAMES},
            "context_source_complete": source_complete,
        },
        "sidecar": {
            "tick_index": 0,
            "dt_s": 0.1,
            "scenario_id": scenario_sha,
            "family": "lead_vehicle_hard_brake",
            "tier": "easy",
            "parameter_block_id": "block",
            "route_identity_sha256": route_sha,
            "corridor_group_sha256": route_sha,
            "map_family_id": "map-family",
            "source_map_sha256": "3" * 64,
            "seed": 25001,
            "candidate_tensor_sha256_before": tensor_sha,
            "candidate_tensor_sha256_after": tensor_sha,
            "default_output_sha256": default_sha,
            "candidate0_sha256": candidate_rows[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": default_sha,
                "candidate0_sha256": candidate_rows[0],
                "native_ranked_k8": False,
            },
            "candidate0_semantics": "operational_default_alias_from_same_forward",
            "candidate0_independent_second_forward": False,
            "causal_input_sha256": source_chain_sha,
            "causal_evidence_sha256": corpus_reviewer._canonical_sha256(
                causal_evidence
            ),
            "route_lanes_sha256": hashlib.sha256(
                np.ascontiguousarray(route_lanes).tobytes()
            ).hexdigest(),
            "route_lanes_speed_limit_sha256": hashlib.sha256(
                np.ascontiguousarray(route_speed).tobytes()
            ).hexdigest(),
            "route_lanes_has_speed_limit_sha256": hashlib.sha256(
                np.ascontiguousarray(route_has_speed).tobytes()
            ).hexdigest(),
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "all_k_high_risk": False,
            "selected_index": 0,
            "selected_trajectory_sha256": candidate_rows[0],
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "tie_break_contract": "lowest_eligible_candidate_index",
            "normalized_atom_matrix_sha256": source_chain_sha,
            "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
            "context_source_receipt": {
                "mode": "no_v2i",
                "phase_remaining_available": False,
                "regulatory_signal_mapped": False,
            },
            "generation_behavior_scale_sha256": semantic_sha,
            "canonical_semantic_clone_sha256": semantic_sha,
            "route_signal_source_artifact_root_sha256": "4" * 64,
            "route_signal_source_row_sha256": "5" * 64,
            "signal_source_class": "no_signal",
            "phase_authority_mode": None,
            "controlled_signal_source_receipt": runtime_receipt,
            "controlled_signal_tensor_evidence": None,
            "controlled_model_input_cache_receipt": {
                "schema_version": "camp_dp_v25_model_input_signal_cache_receipt_v1",
                "scenario_id": scenario_sha,
                "tick_index": 0,
                "signal_source_class": "no_signal",
                "phase_authority_mode": None,
                "scene_map_tl_sha256": "6" * 64,
                "model_cache_tl_sha256_before": "6" * 64,
                "model_cache_tl_sha256_after": "6" * 64,
                "model_route_lanes_tl_sha256": "7" * 64,
                "cache_matches_scene_after": True,
                "observe_cache_unchanged": True,
                "sync_applied_before_tensor_conversion": True,
                "future_schedule_consumed": False,
                "phase_remaining_available": False,
            },
            "causal_signal_atom_input": causal_input,
            "offline_label_provenance": "pending_train_only_causal_label",
            "outcome_fields_consumed": [],
            "fresh_b_opened": False,
        },
    }


def test_full_config_receipts_are_type_exact_and_bind_actual_root_and_row_sha() -> None:
    expected = [_receipt()]
    root = full_config_reviewer._oracle_sha256(expected)
    full_config_reviewer._validate_config_receipts(expected, expected, root)

    mutations = []
    for field, value in (
        ("selector_training_execution_authorized", 0),
        ("seed", 25001.0),
        ("seed", False),
        ("corpus_steps", 64.0),
        ("corpus_steps", True),
    ):
        changed = copy.deepcopy(expected)
        changed[0][field] = value
        mutations.append(changed)
    fake_row_sha = copy.deepcopy(expected)
    fake_row_sha[0]["config_authority_sha256"] = "0" * 64
    mutations.append(fake_row_sha)

    for actual in mutations:
        with pytest.raises(ValueError):
            full_config_reviewer._validate_config_receipts(actual, expected, root)

    resigned_type_drift = copy.deepcopy(expected)
    resigned_type_drift[0]["seed"] = 25001.0
    resigned_authority = dict(resigned_type_drift[0])
    resigned_authority.pop("config_authority_sha256")
    resigned_type_drift[0]["config_authority_sha256"] = (
        full_config_reviewer._oracle_sha256(resigned_authority)
    )
    with pytest.raises(ValueError):
        full_config_reviewer._validate_config_receipts(
            resigned_type_drift,
            expected,
            full_config_reviewer._oracle_sha256(resigned_type_drift),
        )
    with pytest.raises(ValueError):
        full_config_reviewer._validate_config_receipts(expected, expected, "0" * 64)


def test_full_config_integer_and_boolean_authority_rejects_numeric_subtypes() -> None:
    assert full_config_reviewer._require_json_int(25001, "seed") == 25001
    assert full_config_reviewer._require_json_bool(False, "gate") is False
    for value in (25001.0, True):
        with pytest.raises(ValueError):
            full_config_reviewer._require_json_int(value, "seed")
    for value in (0, 0.0):
        with pytest.raises(ValueError):
            full_config_reviewer._require_json_bool(value, "gate")
    assert not full_config_reviewer._strict_json_equal(
        {"seed": 25001, "count": 1500, "gate": False},
        {"seed": 25001.0, "count": 1500.0, "gate": 0},
    )
    assert not full_config_reviewer._strict_json_equal([25001.0], [25001])


def _externalized_snapshot(snapshot: dict, artifact_root: Path) -> dict:
    value = copy.deepcopy(snapshot)
    value["feature_payload"]["causal_evidence"] = externalize_causal_evidence(
        output_dir=artifact_root,
        causal_evidence=value["feature_payload"]["causal_evidence"],
    )
    return value


def test_snapshot_and_index_schema_reject_extra_future_delete_and_type_drift(
    tmp_path: Path,
) -> None:
    snapshot = _externalized_snapshot(_snapshot(), tmp_path)
    referenced_shards = corpus_reviewer._validate_snapshot_field_schema(
        snapshot, artifact_root=tmp_path
    )
    assert referenced_shards
    assert all(
        path.startswith("causal_evidence_shards/") for path in referenced_shards
    )
    corpus_reviewer._validate_snapshot_index_row(
        {
            "scenario_id": "a" * 64,
            "tick_index": 0,
            "relative_path": "snapshots/" + "b" * 64 + ".json.xz",
            "sha256": "b" * 64,
        }
    )

    mutations = []
    extra_top = copy.deepcopy(snapshot)
    extra_top["future_outcome"] = 1
    mutations.append(extra_top)
    extra_feature = copy.deepcopy(snapshot)
    extra_feature["feature_payload"]["holdout_label"] = 1
    mutations.append(extra_feature)
    extra_nested = copy.deepcopy(snapshot)
    extra_nested["sidecar"]["context_source_receipt"]["id_proxy"] = "leak"
    mutations.append(extra_nested)
    deleted = copy.deepcopy(snapshot)
    del deleted["sidecar"]["fresh_b_opened"]
    mutations.append(deleted)
    seed_float = copy.deepcopy(snapshot)
    seed_float["sidecar"]["seed"] = 25001.0
    mutations.append(seed_float)
    fresh_int = copy.deepcopy(snapshot)
    fresh_int["sidecar"]["fresh_b_opened"] = 0
    mutations.append(fresh_int)
    misnamed_hash = copy.deepcopy(snapshot)
    misnamed_hash["feature_payload"]["candidate_rows_sha256"] = (
        misnamed_hash["feature_payload"].pop("candidate_row_sha256")
    )
    mutations.append(misnamed_hash)
    selected_bool = copy.deepcopy(snapshot)
    selected_bool["sidecar"]["selected_index"] = False
    mutations.append(selected_bool)
    candidate0_difference_int = copy.deepcopy(snapshot)
    candidate0_difference_int["sidecar"]["default_candidate0_identity"][
        "max_abs_difference"
    ] = 0
    mutations.append(candidate0_difference_int)

    for changed in mutations:
        with pytest.raises(ValueError):
            corpus_reviewer._validate_snapshot_field_schema(
                changed, artifact_root=tmp_path
            )

    for field, value in (("tick_index", 0.0), ("scenario_id", 1)):
        row = {
            "scenario_id": "a" * 64,
            "tick_index": 0,
            "relative_path": "snapshots/" + "b" * 64 + ".json.xz",
            "sha256": "b" * 64,
        }
        row[field] = value
        with pytest.raises(ValueError):
            corpus_reviewer._validate_snapshot_index_row(row)


def test_final_corpus_reviewer_is_in_critical_implementation_manifest() -> None:
    assert (
        "scripts/integrations/review_diffusion_planner_v25_controlled_training_corpus.py"
        in CRITICAL_IMPLEMENTATION_PATHS
    )


def _set_nested(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
    cursor = payload
    for field in path[:-1]:
        nested = cursor.get(field)
        if type(nested) is not dict:
            nested = {}
            cursor[field] = nested
        cursor = nested
    cursor[path[-1]] = copy.deepcopy(value)


def _exact_payload(role: str) -> dict[str, object]:
    payload: dict[str, object] = {}
    for path, value in authority.ROOT_EXACT_VALUES[role].items():
        _set_nested(payload, path, value)
    if role == "a11_ledger":
        ledger_authority = {
            field: "placeholder" for field in authority._LEDGER_AUTHORITY_FIELDS
        }
        ledger_authority.update(payload.get("authority", {}))
        payload["authority"] = ledger_authority
    return payload


def test_nested_control_paths_require_exact_native_values_and_reject_alias_names() -> None:
    validation = _exact_payload("a11_validation")
    authority._verify_root_exact_values("a11_validation", validation)
    for value in (False, 0, "true"):
        changed = copy.deepcopy(validation)
        changed["contract_checks"]["r_and_fresh_closed"] = value
        with pytest.raises(ValueError):
            authority._verify_root_exact_values("a11_validation", changed)

    ledger = _exact_payload("a11_ledger")
    authority._verify_root_exact_values("a11_ledger", ledger)
    paths = (
        ("passive_latency_instrumentation", "microbatch_cache_sharding_enabled"),
        ("dag_contract", "training_calibration_fresh"),
        ("dag_contract", "outcome_red_10m_heuristic_gate"),
        ("red_signal_contract", "outcome_evaluator_10m_nearest_line_heuristic"),
    )
    for path in paths:
        for value in (True, 0, "mutated"):
            changed = copy.deepcopy(ledger)
            _set_nested(changed, path, value)
            with pytest.raises(ValueError):
                authority._verify_root_exact_values("a11_ledger", changed)
    for extra in ("fullRAuthorized", "full-r-authorized", "futureOutcomeLabel"):
        changed = copy.deepcopy(ledger)
        changed.setdefault("diagnostic", {})[extra] = False
        with pytest.raises(ValueError, match="unregistered nested control"):
            authority._verify_root_exact_values("a11_ledger", changed)


def test_release_nonce_output_and_manifest_are_native_exact(tmp_path: Path) -> None:
    output = (tmp_path / "authorized").resolve()
    for nonce, authorized in ((1, str(output)), ("a" * 64, 1)):
        with pytest.raises(ValueError):
            authority.consume_one_shot_nonce(
                ledger_dir=tmp_path / "ledger",
                gate="preflight",
                nonce=nonce,
                authorized_output_dir=authorized,
                requested_output_dir=output,
            )
    noncanonical = str(output / ".." / output.name)
    with pytest.raises(ValueError, match="absolute canonical"):
        authority.consume_one_shot_nonce(
            ledger_dir=tmp_path / "ledger2",
            gate="preflight",
            nonce="b" * 64,
            authorized_output_dir=noncanonical,
            requested_output_dir=output,
        )

    repo = Path(__file__).resolve().parents[2]
    manifest = authority.build_critical_implementation_manifest(repo)
    head = authority.subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    authority.verify_dual_head_contract(
        repo=repo,
        implementation_source_head=head,
        current_pointer_head=head,
        implementation_manifest=manifest,
    )
    first = next(iter(manifest))
    variants = []
    backslash = dict(manifest)
    backslash[first.replace("/", "\\")] = backslash.pop(first)
    variants.append(backslash)
    duplicate_alias = dict(manifest)
    duplicate_alias[first.replace("/", "\\")] = manifest[first]
    variants.append(duplicate_alias)
    extra = dict(manifest)
    extra["scripts/integrations/extra.py"] = "0" * 64
    variants.append(extra)
    for changed in variants:
        with pytest.raises(ValueError, match="manifest drifted"):
            authority.verify_dual_head_contract(
                repo=repo,
                implementation_source_head=head,
                current_pointer_head=head,
                implementation_manifest=changed,
            )


def test_snapshot_rejects_context_ids_receipt_leaks_numeric_types_and_relations(
    tmp_path: Path,
) -> None:
    base = _externalized_snapshot(_snapshot(), tmp_path)
    mutations = []
    for field in ("route_id", "map_id", "scenario_id", "split_id", "parameter_block_id"):
        changed = copy.deepcopy(base)
        changed["feature_payload"]["raw_context"][field] = 1.0
        mutations.append(changed)
    for field in ("schedule", "outcome", "label"):
        changed = copy.deepcopy(base)
        changed["sidecar"]["controlled_signal_source_receipt"][field] = {}
        mutations.append(changed)
    for path, value in (
        (("feature_payload", "atom_matrix", 0, 0), "0"),
        (("feature_payload", "candidate_tensor", 0, 0, 0), True),
        (("feature_payload", "default_output", 0, 0), "0.0"),
    ):
        changed = copy.deepcopy(base)
        cursor = changed
        for part in path[:-1]:
            cursor = cursor[part]
        cursor[path[-1]] = value
        mutations.append(changed)
    candidate0 = copy.deepcopy(base)
    candidate0["sidecar"]["candidate0_independent_second_forward"] = True
    mutations.append(candidate0)
    mask = copy.deepcopy(base)
    mask["feature_payload"]["source_valid_mask"][0] = False
    mutations.append(mask)
    all_k = copy.deepcopy(base)
    all_k["sidecar"]["all_k_high_risk"] = True
    mutations.append(all_k)
    signal_applicability = copy.deepcopy(base)
    signal_applicability["feature_payload"]["atom_applicable_mask"][0][10] = True
    mutations.append(signal_applicability)
    for changed in mutations:
        with pytest.raises(ValueError):
            corpus_reviewer._validate_snapshot_field_schema(
                changed, artifact_root=tmp_path
            )


def _terminal_fixture() -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    report: dict[str, object] = {field: "placeholder" for field in corpus_reviewer.REPORT_FIELDS}
    for field in (
        "seed", "corpus_steps", "snapshot_capacity", "minimum_free_bytes",
        "free_bytes_at_start", "semantic_authority_identity_count",
        "attempted_identity_count", "source_ineligible_retained_identity_count",
        "formal_train_manifest_identity_count", "complete_identity_count",
        "failed_identity_count", "retained_capability_failure_count",
        "retained_identity_count", "snapshot_count",
    ):
        report[field] = 1
    for field in (
        "fresh_b_opened", "candidate_tensors_modified",
        "runtime_outcomes_not_read_or_copied_to_training_snapshots",
        "selector_training_executed", "calibration_executed", "claim_authorized",
    ):
        report[field] = False
    report["wall_seconds"] = 1.0
    report["rejected_roots"] = ["a" * 64]
    report["outcome_fields_consumed"] = []
    report["training_snapshot_outcome_fields"] = []
    report["critical_implementation_manifest"] = {}
    report["release_run_nonce"] = "d" * 64
    report["authorized_output_dir"] = str(Path.cwd().resolve())
    report["seven_root_bindings"] = {}
    report["seven_root_bindings_sha256"] = "e" * 64
    for field in ("generation_scales", "static_weights", "release_nonce_consumption_marker"):
        report[field] = {"path": str(Path.cwd().resolve()), "sha256": "f" * 64}
    report["red_scientific_coverage"] = {
        "formal_identity_count": 21,
        "formal_by_tier": {"easy": 6, "borderline": 10, "high_risk": 5},
        "formal_distinct_source_map_count": 4,
        "complete_by_tier": {"easy": 6, "borderline": 10, "high_risk": 5},
        "complete_distinct_source_map_count": 4,
        "minimum_complete_by_tier": {"easy": 4, "borderline": 7, "high_risk": 4},
        "minimum_distinct_source_maps": 3,
        "passed": True,
    }
    for field in ("family_identity_counts", "family_snapshot_counts", "failure_reason_counts"):
        report[field] = {"family": 1}
    progress: dict[str, object] = {
        "schema_version": "v", "status": "complete", "completed": 1,
        "total": 1, "complete": 1, "failed": 0, "snapshot_count": 64,
        "elapsed_seconds": 1.0, "free_bytes": 1, "fresh_b_opened": False,
    }
    result: dict[str, object] = {
        "ordinal": 0, "scenario_id": "b" * 64, "family": "family",
        "tier": "easy", "route_identity_sha256": "c" * 64, "seed": 25001,
        "status": "complete", "snapshot_count": 64, "failure_type": None,
        "failure_reason": None, "capability_failure": None, "wall_seconds": 1.0,
        "retained": True, "outcome_fields_consumed": [], "fresh_b_opened": False,
    }
    return report, progress, [result]


def test_terminal_report_progress_results_are_exact_and_type_closed() -> None:
    report, progress, results = _terminal_fixture()
    corpus_reviewer._validate_terminal_schemas(report, progress, results)
    mutations = []
    changed = copy.deepcopy(report)
    changed["attempted_identity_count"] = 1.0
    mutations.append((changed, progress, results))
    changed = copy.deepcopy(progress)
    changed["completed"] = True
    mutations.append((report, changed, results))
    changed = copy.deepcopy(results)
    changed[0]["seed"] = 25001.0
    mutations.append((report, progress, changed))
    changed = copy.deepcopy(report)
    changed["future_outcome"] = False
    mutations.append((changed, progress, results))
    changed = copy.deepcopy(results)
    del changed[0]["fresh_b_opened"]
    mutations.append((report, progress, changed))
    for values in mutations:
        with pytest.raises(ValueError):
            corpus_reviewer._validate_terminal_schemas(*values)


def test_terminal_retained_failure_is_bound_to_exact_route_source_state() -> None:
    report, progress, results = _terminal_fixture()
    failed = copy.deepcopy(results)
    failed[0].update(
        {
            "status": "failed",
            "snapshot_count": 0,
            "failure_type": "RetainedScenarioCapabilityFailure",
            "failure_reason": "mapped source unavailable",
            "capability_failure": {
                "scenario_id": failed[0]["scenario_id"],
                "family": failed[0]["family"],
                "source_class": "mapped_signal",
                "phase_authority_mode": "observe_same_tick_request",
                "reason": "mapped_current_signal_source_unavailable",
            },
        }
    )
    corpus_reviewer._validate_terminal_schemas(report, progress, failed)
    for key, value in (
        ("source_class", "no_signal"),
        ("phase_authority_mode", "red_light_phase_timing"),
        ("reason", "other"),
        ("source_class", 1),
    ):
        changed = copy.deepcopy(failed)
        changed[0]["capability_failure"][key] = value
        with pytest.raises(ValueError, match="capability receipt"):
            corpus_reviewer._validate_terminal_schemas(report, progress, changed)
