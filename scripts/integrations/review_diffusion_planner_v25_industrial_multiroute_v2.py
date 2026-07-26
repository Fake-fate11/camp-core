from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_review import (  # noqa: E402
    EXPECTED_AUTHORITY,
    EXPECTED_FIXED_DP,
    review_contract_semantics,
)
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay_review import (  # noqa: E402
    RAW_FEATURE_NAMES,
    literal_scene_weights,
    literal_selection,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v3 import (  # noqa: E402
    review_contract_v3_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)
from scripts.integrations.review_diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    _body as _literal_body,
    _collision_proximity as _literal_collision_proximity,
    _geometry as _literal_geometry,
    _goal as _literal_goal,
    _red as _literal_red,
    _road as _literal_road,
    _route as _literal_route,
    _speed as _literal_speed,
)


EXPECTED_SOURCE_ROOT = (
    "ebbc7140e65fb2d2baf2aed8fa1a990e3c47b8b8ed3f6f4583ae0e2121be065a"
)
EXPECTED_SELECTED_MANIFEST = (
    "b779319aa0d32847a13c7522edeffc35ac03a044483c176d699b60a97cb9c40c"
)
EXPECTED_TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _write_review(
    output: Path,
    report: Mapping[str, Any],
    *,
    role: str,
    source_root: str,
    label: str,
) -> str:
    return write_atomic(
        output,
        dict(report),
        {
            "role": role,
            "authority_sha256": EXPECTED_AUTHORITY,
            "implementation_head": git_head(),
            "source_root_sha256": source_root,
        },
        label=label,
    )


def review_contract(
    output: Path, *, source_dir: Path, source_root: str
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 contract")
    reviewed = review_contract_semantics(source["contract"])
    if (
        source.get("authority_sha256") != EXPECTED_AUTHORITY
        or source.get("fixed_dp_head") != EXPECTED_FIXED_DP
        or source.get("model_pool_selector_calls") != 0
        or source.get("outcome_values_read") is not False
    ):
        raise ValueError("reviewer contract artifact boundary drifted")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_contract_review_v1",
        "status": "independent_literal_contract_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_sha256": reviewed["contract_sha256"],
        "local_literal_checks": {
            "authority_and_continuation": True,
            "100_cluster_300_arm_19200_tick_denominator": True,
            "same_ego_single_invocation_b8": True,
            "actor_and_same_tick_signal_before_tensor_conversion": True,
            "161_leaf_no_weighted_total_no_claim": True,
            "independent_n_100_cluster_first": True,
            "exact_dirs_and_forbidden_permissions": True,
        },
        "producer_contract_or_decision_oracle_imported": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return _write_review(
        output,
        report,
        role="industrial_v3_multiroute_v2_contract_review",
        source_root=source_root,
        label="V25 industrial-v3 multiroute-v2 contract review",
    )


def review_matrix(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
    capability_dir: Path,
    capability_root: str,
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 matrix")
    contract = _verify(contract_dir, contract_root, "multiroute-v2 contract")
    capability = _verify(capability_dir, capability_root, "industrial capability")
    review_contract_semantics(contract["contract"])
    rows = capability.get("rows")
    if type(rows) is not list:
        rows = capability.get("capability_matrix", {}).get("rows")
    matrix_rows = source.get("scalar_leaf_capture_mapping")
    if type(rows) is not list or type(matrix_rows) is not list:
        raise ValueError("reviewer capability rows absent")
    if len(rows) != 161 or len(matrix_rows) != 161:
        raise ValueError("reviewer scalar leaf denominator drifted")
    expected = {}
    for row in rows:
        evidence = row["evidence_class"]
        capture = {
            "scientifically_inapplicable": "route_inapplicable",
            "evidence_missing": "permanent_evidence_missing",
            "directly_reconstructable": "runner_capture_direct",
            "reconstructable_with_frozen_transform": (
                "runner_capture_plus_frozen_transform"
            ),
        }.get(evidence)
        if capture is None:
            raise ValueError("reviewer unknown evidence class")
        expected[row["leaf_id"]] = (
            evidence,
            capture,
            row["source_shape"],
            row["source_units"],
            row["canonical_json_pointers"],
            row["applicability_prerequisites"],
            row["transform_inputs"],
        )
    actual = {}
    for row in matrix_rows:
        leaf = row["leaf_id"]
        if leaf in actual:
            raise ValueError("reviewer duplicate capture leaf")
        actual[leaf] = (
            row["baseline_evidence_class"],
            row["capture_class"],
            row["source_shape"],
            row["source_units"],
            row["canonical_json_pointers"],
            row["applicability_prerequisites"],
            row["transform_inputs"],
        )
    if actual != expected:
        raise ValueError("reviewer scalar leaf capture semantics drifted")
    parameters = source.get("parameter_propagation_rows")
    if (
        type(parameters) is not list
        or len(parameters) < 8
        or len({row["parameter"] for row in parameters}) != len(parameters)
        or any(row.get("implicit_default_allowed") is not False for row in parameters)
    ):
        raise ValueError("reviewer parameter propagation matrix drifted")
    if source.get("zero_bug_claimed") is not False:
        raise ValueError("reviewer matrix claimed zero bug")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_matrix_review_v1",
        "status": "independent_literal_hardening_matrix_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "capability_root_sha256": capability_root,
        "scalar_leaf_count": 161,
        "capture_mapping_sha256": _canonical_sha(matrix_rows),
        "parameter_propagation_sha256": _canonical_sha(parameters),
        "producer_capture_or_decision_oracle_imported": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return _write_review(
        output,
        report,
        role="industrial_v3_multiroute_v2_matrix_review",
        source_root=source_root,
        label="V25 industrial-v3 multiroute-v2 matrix review",
    )


def _local_latent(clone_key: str, tick: int) -> np.ndarray:
    parent = "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
    seed = int.from_bytes(
        hashlib.sha256(f"{parent}|{clone_key}|{tick}".encode("ascii")).digest()[:8],
        "little",
    )
    rng = np.random.Generator(np.random.PCG64DXSM(seed))
    value = np.zeros((8, 321, 81, 4), dtype="<f4")
    value[1:] = rng.standard_normal(value[1:].shape).astype("<f4")
    return value


def review_preflight(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
    matrix_dir: Path,
    matrix_root: str,
    focused_dir: Path,
    focused_root: str,
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 preflight")
    contract = _verify(contract_dir, contract_root, "multiroute-v2 contract")
    matrix = _verify(matrix_dir, matrix_root, "multiroute-v2 matrix")
    focused = _verify(
        focused_dir, focused_root, "multiroute-v2 hardening focused"
    )
    review_contract_semantics(contract["contract"])
    if (
        source.get("status") != "passed_before_first_model_call"
        or source.get("source_root_sha256") != EXPECTED_SOURCE_ROOT
        or source.get("selected_manifest_sha256") != EXPECTED_SELECTED_MANIFEST
        or source.get("cluster_count") != 100
        or source.get("planned_tick_slots") != 19_200
        or source.get("model_pool_selector_calls") != 0
        or source.get("hardening_focused_root_sha256") != focused_root
        or focused.get("status")
        != "passed_zero_model_pre_execution_hardening_focused"
    ):
        raise ValueError("reviewer preflight authority or denominator drifted")
    manifest = object_from(source_dir / "prepared_manifest.json")["clusters"]
    if (
        len(manifest) != 100
        or [row["cluster_index"] for row in manifest] != list(range(100))
        or len({row["clone_key_sha256"] for row in manifest}) != 100
    ):
        raise ValueError("reviewer prepared manifest topology drifted")
    for row in manifest:
        cluster_dir = source_dir / "prepared" / f"{row['cluster_index']:03d}"
        for name, key in (
            ("lanelet2_map.osm", "map_sha256"),
            ("route.pkl", "route_file_sha256"),
            ("config.json", "config_sha256"),
            ("latent_manifest.json", "latent_manifest_sha256"),
            ("source_record.json", "source_record_file_sha256"),
        ):
            if _file_sha(cluster_dir / name) != row[key]:
                raise ValueError("reviewer prepared file binding drifted")
        latent = object_from(cluster_dir / "latent_manifest.json")["ticks"]
        if len(latent) != 64:
            raise ValueError("reviewer latent schedule denominator drifted")
        for tick, receipt in enumerate(latent):
            value = _local_latent(row["clone_key_sha256"], tick)
            rows = [_array_sha(item) for item in value]
            if (
                receipt["tick_index"] != tick
                or receipt["shape"] != [8, 321, 81, 4]
                or receipt["dtype"] != "<f4"
                or receipt["tensor_sha256"] != _array_sha(value)
                or receipt["row_sha256"] != rows
                or len(set(rows)) != 8
                or np.any(value[0] != 0.0)
            ):
                raise ValueError("reviewer latent schedule semantic drifted")
    capacity = source["capacity"]
    if (
        capacity["projected_free_after_persistent_and_peak_bytes"]
        < capacity["required_free_after_bytes"]
        or capacity["projected_free_inodes"] < capacity["required_free_inodes"]
    ):
        raise ValueError("reviewer capacity gate drifted")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_preflight_review_v1",
        "status": "independent_preflight_review_passed_before_first_model_call",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "matrix_root_sha256": matrix_root,
        "cluster_count": 100,
        "latent_tick_records": 6_400,
        "latent_schedules_independently_rebuilt": True,
        "capacity_independently_checked": True,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "producer_manifest_or_latent_oracle_imported": False,
    }
    return _write_review(
        output,
        report,
        role="industrial_v3_multiroute_v2_preflight_review",
        source_root=source_root,
        label="V25 industrial-v3 multiroute-v2 preflight review",
    )


def _load_training(training_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if _file_sha(training_dir / "runtime_atom_scales.json") != (
        "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
    ):
        raise ValueError("reviewer atom scale file drifted")
    scale_json = object_from(training_dir / "runtime_atom_scales.json")
    scales = np.asarray(scale_json["scales"], dtype=np.float64)
    static = np.load(training_dir / "static14d_runtime_weights.npy", allow_pickle=False)
    with np.load(training_dir / "model_parameters.npz", allow_pickle=False) as archive:
        q05 = np.asarray(archive["context_q05"], dtype=np.float64)
        q95 = np.asarray(archive["context_q95"], dtype=np.float64)
        theta = np.asarray(archive["scene14d_theta"], dtype=np.float64)
    return scales, static, q05, q95, theta


def review_execution(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    preflight_dir: Path,
    preflight_root: str,
    training_dir: Path,
    training_root: str,
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 execution")
    preflight = _verify(preflight_dir, preflight_root, "multiroute-v2 preflight")
    _verify(training_dir, training_root, "accepted selector training")
    if training_root != EXPECTED_TRAINING_ROOT:
        raise ValueError("reviewer training root drifted")
    if (
        source.get("status")
        != "complete_full_denominator_hard_integrity_passed"
        or source.get("cluster_count") != 100
        or source.get("arm_run_count") != 300
        or source.get("planned_tick_slots") != 19_200
        or source.get("formal_model_calls") != 19_200
        or source.get("selector_calls") != {"Scene14D": 6400, "Static14D": 6400}
        or source.get("sequential_calls") != 0
        or source.get("post_pool_model_dp_latent_generation_calls") != 0
        or source.get("candidate_tensor_mutation_count") != 0
        or source.get("hard_integrity_failure_count") != 0
    ):
        raise ValueError("reviewer execution authority or integrity drifted")
    terminal = source["terminal_accounting"]
    if (
        terminal["complete"] + terminal["failed"] != 19_200
        or terminal["unattempted"] != 0
        or terminal["planned"] != 19_200
    ):
        raise ValueError("reviewer execution denominator drifted")
    prepared = object_from(preflight_dir / "prepared_manifest.json")["clusters"]
    scales, static, q05, q95, theta = _load_training(training_dir)
    model_calls = 0
    selector_calls = {"Static14D": 0, "Scene14D": 0}
    selected_counts = {arm: np.zeros(8, dtype=np.int64) for arm in ARMS}
    for binding in prepared:
        cluster = int(binding["cluster_index"])
        summary = source["cluster_artifacts"][cluster]
        cluster_dir = source_dir / "clusters" / f"{cluster:03d}"
        verify_complete_seal(
            cluster_dir,
            summary["root_sha256"],
            label=f"multiroute-v2 cluster {cluster}",
        )
        report = object_from(cluster_dir / "report.json")
        if (
            report["cluster_index"] != cluster
            or report["clone_key_sha256"] != binding["clone_key_sha256"]
            or report["formal_model_calls"] != 192
        ):
            raise ValueError("reviewer cluster binding drifted")
        with np.load(cluster_dir / "preimages.npz", allow_pickle=False) as archive:
            arrays = {key: np.asarray(archive[key]) for key in archive.files}
        initial_source_inputs = []
        for arm_index, arm in enumerate(report["arms"]):
            if arm["arm"] != ARMS[arm_index] or len(arm["ticks"]) != 64:
                raise ValueError("reviewer arm topology drifted")
            candidates = arrays[f"{arm_index}_candidates"]
            neighbors = arrays[f"{arm_index}_neighbors"]
            if (
                candidates.shape != (64, 8, 80, 4)
                or candidates.dtype != np.dtype("<f4")
                or neighbors.shape != (64, 8, 32, 80, 4)
                or neighbors.dtype != np.dtype("<f4")
                or not np.isfinite(candidates).all()
                or not np.isfinite(neighbors).all()
            ):
                raise ValueError("reviewer candidate/neighbor raw bytes drifted")
            for tick, receipt in enumerate(arm["ticks"]):
                expected_latent = _local_latent(binding["clone_key_sha256"], tick)
                rows = [_array_sha(value) for value in candidates[tick]]
                if (
                    receipt["tick_index"] != tick
                    or receipt["latent_tensor_sha256"] != _array_sha(expected_latent)
                    or receipt["candidate_tensor_sha256_before"]
                    != _array_sha(candidates[tick])
                    or receipt["candidate_tensor_sha256_after"]
                    != _array_sha(candidates[tick])
                    or receipt["candidate_neighbor_sha256"]
                    != _array_sha(neighbors[tick])
                    or receipt["candidate_row_sha256"] != rows
                    or len(set(rows)) != 8
                    or receipt["primary_pool_model_call_count"] != 1
                    or receipt["zero_call_receipt"][
                        "dp_or_model_calls_after_pool"
                    ]
                    != 0
                ):
                    raise ValueError("reviewer per-tick raw binding drifted")
                selected = int(receipt["selected_index"])
                if receipt["selected_trajectory_sha256"] != rows[selected]:
                    raise ValueError("reviewer selected action binding drifted")
                selected_counts[arm["arm"]][selected] += 1
                if tick == 0:
                    initial_source_inputs.append(receipt["source_input_sha256"])
                if arm["arm"] == "pool_matched_candidate0":
                    if selected != 0:
                        raise ValueError("reviewer candidate0 was not row0")
                    continue
                atoms = arrays[f"{arm_index}_atoms"][tick]
                mask = arrays[f"{arm_index}_source_masks"][tick].astype(np.bool_)
                selector = receipt["real_selector_receipts"][arm["arm"]]
                if arm["arm"] == "Static14D":
                    weights = static
                else:
                    context = selector["context"]
                    raw = np.asarray(
                        [
                            context["raw_context"][name]
                            for name in RAW_FEATURE_NAMES
                        ],
                        dtype=np.float64,
                    )
                    complete = np.asarray(
                        [
                            bool(context["source_complete"][name])
                            for name in RAW_FEATURE_NAMES
                        ],
                        dtype=np.bool_,
                    )
                    weights = literal_scene_weights(
                        raw_context=raw,
                        source_complete=complete,
                        q05=q05,
                        q95=q95,
                        theta=theta,
                    )["weights"]
                rebuilt = literal_selection(
                    candidates=candidates[tick],
                    raw_atoms=atoms,
                    scales=scales,
                    weights=weights,
                    eligibility_mask=mask,
                    simplex_nonnegative_atol=1e-9,
                )
                if (
                    rebuilt["scores"] != selector["scores"]
                    or rebuilt["selected_index"] != selector["selected_index"]
                    or rebuilt["selected_row_sha256"]
                    != selector["selected_row_sha256"]
                    or rebuilt["tie_set"] != selector["exact_tie_set"]
                ):
                    raise ValueError("reviewer selector literal reconstruction drifted")
                selector_calls[arm["arm"]] += 1
            model_calls += 64
        if len(set(initial_source_inputs)) != 1:
            raise ValueError("reviewer cluster arms did not share initial state")
        for tick in range(64):
            latent_sha = {
                arm["ticks"][tick]["latent_tensor_sha256"]
                for arm in report["arms"]
            }
            if len(latent_sha) != 1:
                raise ValueError("reviewer cross-arm latent schedule drifted")
    if model_calls != 19_200 or selector_calls != {
        "Static14D": 6400,
        "Scene14D": 6400,
    }:
        raise ValueError("reviewer global call denominator drifted")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_execution_review_v1",
        "status": "independent_raw_execution_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "preflight_root_sha256": preflight_root,
        "cluster_count": 100,
        "arm_run_count": 300,
        "tick_slot_count": 19_200,
        "formal_model_calls": model_calls,
        "selector_calls": selector_calls,
        "selected_index_counts": {
            key: value.astype(int).tolist() for key, value in selected_counts.items()
        },
        "same_initial_state_and_cross_arm_latent_schedule": True,
        "candidate_neighbor_bytes_and_selector_values_rebuilt": True,
        "producer_generator_selector_decision_oracle_imported": False,
        "claim_authorized": False,
    }
    return _write_review(
        output,
        report,
        role="industrial_v3_multiroute_v2_execution_review",
        source_root=source_root,
        label="V25 industrial-v3 multiroute-v2 execution review",
    )


def _episodes(mask: Sequence[bool]) -> int:
    return sum(
        bool(value) and (index == 0 or not bool(mask[index - 1]))
        for index, value in enumerate(mask)
    )


def _literal_native(
    arm: Mapping[str, Any], config: Mapping[str, Any]
) -> dict[str, Any]:
    ticks = []
    for receipt in arm["ticks"]:
        safety = receipt.get("_safety_record")
        if type(safety) is not dict:
            raise ValueError("reviewer evaluation safety record missing")
        ticks.append(
            {
                "tick_index": int(receipt["tick_index"]),
                "input_sha256": str(receipt["input_sha256"]),
                "default_output_sha256": str(receipt["default_output_sha256"]),
                "selected_index": int(receipt["selected_index"]),
                "selected_trajectory_sha256": str(
                    receipt["selected_trajectory_sha256"]
                ),
                "safety": dict(safety),
                "controlled_scene": {"actors": list(safety.get("actors", []))},
                "latency_ms": {
                    key: float(value)
                    for key, value in receipt["latency_ms"].items()
                    if value is not None
                },
            }
        )
    return {
        "schema_version": "camp_dp_v25_industrial_multiroute_v2_review_native_v1",
        "status": "ok",
        "route_name": str(config["routes"][0]["name"]),
        "route_sha256": str(config["routes"][0]["sha256"]),
        "logical_map_sha256": str(config["map"]["sha256"]),
        "fixed_dp_head": EXPECTED_FIXED_DP,
        "checkpoint_sha256": str(config["fixed_dp"]["checkpoint"]["sha256"]),
        "args_sha256": str(config["fixed_dp"]["args_json"]["sha256"]),
        "arm": arm["arm"],
        "scenario_seed": int(config["seeds"]["scenario"]),
        "ticks": ticks,
        "native_result": dict(arm["native_result"]),
        "claim_authorized": False,
    }


def _distribution(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (64,) or not np.all(np.isfinite(array)):
        raise ValueError("reviewer latency distribution requires 64 finite values")
    return {
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p95": float(np.quantile(array, 0.95, method="linear")),
        "p99": float(np.quantile(array, 0.99, method="linear")),
        "max": float(np.max(array)),
    }


def _literal_latency(arm: Mapping[str, Any]) -> dict[str, Any]:
    stage_sources = {
        "pool_generation": ("pool_generation",),
        "atoms": ("atoms",),
        "context_weights": ("context", "weights"),
        "selector_increment": ("selector_incremental",),
        "end_to_end": ("end_to_end",),
    }
    latency: dict[str, Any] = {}
    for stage, sources in stage_sources.items():
        if arm["arm"] == "pool_matched_candidate0" and stage not in {
            "pool_generation",
            "end_to_end",
        }:
            latency[stage] = None
            continue
        values = []
        for tick in arm["ticks"]:
            row = tick["latency_ms"]
            if any(row.get(source) is None for source in sources):
                values = []
                break
            values.append(sum(float(row[source]) for source in sources))
        latency[stage] = _distribution(values) if len(values) == 64 else None
    end_values = np.asarray(
        [float(tick["latency_ms"]["end_to_end"]) for tick in arm["ticks"]],
        dtype=np.float64,
    )
    latency["budget"] = {
        str(budget): {
            "exceedance_rate": float(np.count_nonzero(end_values > budget) / 64),
            "max_overrun_ms": float(
                np.maximum(0.0, end_values - budget).max()
            ),
        }
        for budget in (50.0, 100.0, 200.0, 500.0, 1000.0)
    }
    return latency


def _literal_wrong_way(ticks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    mask = []
    missing = 0
    for tick in ticks:
        safety = tick["safety"]
        route_heading = safety.get("route_heading_rad")
        coverage = safety.get("five_point_drivable_coverage")
        if route_heading is None or type(coverage) is not list:
            missing += 1
            mask.append(False)
            continue
        delta = math.atan2(
            math.sin(float(safety["ego_heading_rad"]) - float(route_heading)),
            math.cos(float(safety["ego_heading_rad"]) - float(route_heading)),
        )
        mask.append(
            bool(
                all(bool(value) for value in coverage)
                and float(safety["speed_mps"]) > 0.5
                and abs(delta) > math.pi / 2
            )
        )
    return {
        "status": "evidence_missing" if missing else "benchmark_only",
        "missing_tick_count": missing,
        "duration_s": None if missing else float(sum(mask) * 0.1),
        "episode_count": None if missing else _episodes(mask),
        "unique_route_direction_required": True,
    }


def _literal_vdv_like(
    ticks: Sequence[dict[str, Any]]
) -> dict[str, float]:
    positions = np.asarray(
        [tick["safety"]["position_xy"] for tick in ticks], dtype=np.float64
    )
    headings = np.asarray(
        [tick["safety"]["ego_heading_rad"] for tick in ticks], dtype=np.float64
    )
    velocity = np.diff(positions, axis=0) / 0.1
    acceleration = np.diff(velocity, axis=0) / 0.1
    cosine = np.cos(headings[1:-1])
    sine = np.sin(headings[1:-1])
    longitudinal = acceleration[:, 0] * cosine + acceleration[:, 1] * sine
    lateral = -acceleration[:, 0] * sine + acceleration[:, 1] * cosine
    kernel = np.full(11, 1.0 / 11.0, dtype=np.float64)
    filtered = {
        "longitudinal": np.convolve(longitudinal, kernel, mode="valid"),
        "lateral": np.convolve(lateral, kernel, mode="valid"),
    }
    return {
        axis: float((np.sum(np.abs(value) ** 4) * 0.1) ** 0.25)
        for axis, value in filtered.items()
    }


def _literal_arm_metrics(
    arm: Mapping[str, Any],
    config: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    native = _literal_native(arm, config)
    ticks = native["ticks"]
    actors = ticks[0]["controlled_scene"]["actors"] if ticks else []
    specs = {
        str(row["id"]): {
            "id": row["id"],
            "length_m": row["length_m"],
            "width_m": row["width_m"],
            "wheelbase_m": row["wheelbase_m"],
        }
        for row in actors
    }
    spawn = config["spawn_config"]
    collision, proximity = _literal_collision_proximity(
        ticks, ticks, specs, spawn
    )
    body = _literal_body(ticks)
    body["planar_kinematic_vdv_like"] = _literal_vdv_like(ticks)
    summary = {
        "endpoints": {
            "collision": collision,
            "dynamic_proximity": proximity,
            "road_containment": _literal_road(
                ticks,
                geometry["drivable_polygons"],
                spawn,
                config["map"]["sha256"],
            ),
            "certified_red_crossing": _literal_red(
                ticks,
                [],
                float(spawn["ego_width"]),
                float(geometry["initial_heading_rad"]),
            ),
            "speed": _literal_speed(ticks),
            "route": _literal_route(
                ticks, dict(geometry), spawn, native["native_result"]
            ),
            "goal": _literal_goal(
                ticks, dict(geometry), spawn, native["native_result"]
            ),
            "vehicle_body_planar_kinematic_proxy": body,
            "wrong_way": _literal_wrong_way(ticks),
        }
    }
    return summary, _literal_latency(arm)


def _literal_lookup_leaf(
    leaf: Mapping[str, Any],
    summary: Mapping[str, Any],
    latency: Mapping[str, Any],
) -> tuple[str, Any, str | None]:
    leaf_id = str(leaf["leaf_id"])
    endpoints = summary["endpoints"]
    collision = endpoints["collision"]
    proximity = endpoints["dynamic_proximity"]
    road = endpoints["road_containment"]
    red = endpoints["certified_red_crossing"]
    speed = endpoints["speed"]
    route = endpoints["route"]
    goal = endpoints["goal"]
    proxy = endpoints["vehicle_body_planar_kinematic_proxy"]
    wrong_way = endpoints["wrong_way"]
    direct = {
        "safety.collision_any": collision.get("collision_any"),
        "safety.collision_episode_count": collision.get("episode_count"),
        "safety.collision_duration_s": collision.get("duration_s"),
        "safety.min_full_polygon_clearance_m": proximity.get("min_clearance_m"),
        "safety.max_closing_speed_mps": proximity.get("max_closing_mps"),
        "safety.min_geometry_ttc_s": proximity.get("min_finite_geometry_ttc_s"),
        "safety.max_drac_mps2": proximity.get("max_drac_mps2"),
        "safety.certified_red_crossing_any": red.get("unthresholded_crossing_any"),
        "safety.certified_red_crossing_count": red.get(
            "unthresholded_crossing_count"
        ),
        "safety.certified_red_crossing_speed_mps": red.get("crossing_speed_mps"),
        "safety.certified_red_encounter_opportunity_count": red.get(
            "red_opportunity_count"
        ),
        "safety.certified_red_phase_interval_count": red.get(
            "red_phase_interval_count"
        ),
        "safety.drivable_outside_fraction_max": road.get("max_outside_fraction"),
        "safety.drivable_outside_duration_s": road.get("duration_s"),
        "safety.drivable_outside_episode_count": road.get("episode_count"),
        "safety.drivable_signed_clearance_min_m": road.get(
            "signed_boundary_clearance_or_penetration", {}
        ).get("minimum_signed_boundary_clearance_m"),
        "safety.drivable_penetration_max_m": road.get(
            "signed_boundary_clearance_or_penetration", {}
        ).get("maximum_boundary_penetration_m"),
        "safety.wrong_way_duration_s": wrong_way.get("duration_s"),
        "safety.wrong_way_episode_count": wrong_way.get("episode_count"),
        "operations.speed_excess_max_mps": speed.get("max_excess_mps"),
        "operations.speed_excess_mean_positive_mps": speed.get(
            "mean_positive_excess_mps"
        ),
        "operations.ordered_route_arc_final_m": route.get(
            "final_nearest_route_polyline_projection_m"
        ),
        "operations.max_forward_progress_m": route.get("max_forward_m"),
        "operations.net_forward_progress_m": route.get("net_m"),
        "operations.completion_fraction": route.get("completion_fraction"),
        "operations.goal_distance_final_m": goal.get("minimum_goal_distance_m"),
        "operations.goal_reached": goal.get("goal_reached_by_literal_tolerance"),
        "operations.goal_passed": goal.get(
            "goal_passed_by_literal_heading_and_window"
        ),
        "operations.backtracking_duration_s": route.get(
            "backtracking_duration_s"
        ),
        "operations.backtracking_distance_m": route.get(
            "backtracking_distance_m"
        ),
        "operations.distance_traveled_m": route.get("distance_traveled_m"),
    }
    if leaf_id in direct:
        value = direct[leaf_id]
        return (
            ("computed_descriptive", value, None)
            if value is not None
            else ("evidence_missing", None, "required_source_value_missing")
        )
    if leaf_id == "operations.travel_efficiency_ratio":
        distance = route.get("distance_traveled_m")
        forward = route.get("max_forward_m")
        if (
            isinstance(distance, (int, float))
            and not isinstance(distance, bool)
            and distance > 0
            and isinstance(forward, (int, float))
            and not isinstance(forward, bool)
        ):
            return "computed_descriptive", float(forward / distance), None
        return "evidence_missing", None, "zero_or_missing_traveled_distance"
    for family, grid_key in (
        ("clearance_m", "clearance_grid"),
        ("ttc_s", "geometry_ttc_grid"),
        ("closing_mps", "closing_grid"),
        ("drac_mps2", "drac_grid"),
    ):
        if leaf_id.startswith(f"safety.{family}_"):
            output_key = (
                "duration_s"
                if leaf_id.endswith("duration_s")
                else "episode_count"
            )
            for token, row in proximity.get(grid_key, {}).items():
                canonical = str(token).replace(".", "_").replace("-", "neg_")
                if f"_{canonical}" in leaf_id:
                    return "computed_descriptive", row[output_key], None
    if leaf_id.startswith("operations.speed_excess_gt_"):
        for token, row in speed.get("tolerance_grid", {}).items():
            if f"_{str(token).replace('.', '_')}mps_" in leaf_id:
                return "computed_descriptive", row["duration_s"], None
    if leaf_id.startswith("operations.speed_excess_magnitude_above_"):
        for token, row in speed.get("tolerance_grid", {}).items():
            if f"_{str(token).replace('.', '_')}mps_" in leaf_id:
                return "computed_descriptive", row["magnitude_duration_m"], None
    if leaf_id.startswith("comfort.body_") and "_filtered_acceleration_" in leaf_id:
        axis = "longitudinal" if "body_longitudinal" in leaf_id else "lateral"
        source = proxy.get("filtered_acceleration", {}).get(axis, {})
        if "_abs_gt_" in leaf_id:
            for token, row in proxy.get("filtered_acceleration", {}).get(
                "duration_abs_gt_s", {}
            ).items():
                if f"_{str(token).replace('.', '_')}mps2_" in leaf_id:
                    return "computed_descriptive", row[axis], None
        aliases = {
            "mean": "signed_mean",
            "signed_mean": "signed_mean",
            "rms": "rms",
            "min": "min",
            "max": "max",
            "peak_abs": "peak_abs",
            "p50": "abs_p50",
            "p90": "abs_p90",
            "p95": "abs_p95",
            "p99": "abs_p99",
        }
        key = next(
            (
                value
                for token, value in aliases.items()
                if leaf_id.endswith("_" + token)
            ),
            None,
        )
        if key is not None and key in source:
            return "computed_descriptive", source[key], None
    if leaf_id.startswith("comfort.planar_kinematic_vdv_like_"):
        axis = "longitudinal" if leaf_id.endswith("_longitudinal") else "lateral"
        value = proxy.get("planar_kinematic_vdv_like", {}).get(axis)
        if value is not None:
            return "computed_descriptive", value, None
    if leaf_id.startswith("comfort.filtered_") and "_jerk_" in leaf_id:
        axis = "longitudinal" if "filtered_longitudinal" in leaf_id else "lateral"
        source = proxy.get("filtered_jerk", {}).get(axis, {})
        for token in ("rms", "peak_abs", "abs_p95"):
            if leaf_id.endswith("_" + token) and token in source:
                return "computed_descriptive", source[token], None
        if "_abs_gt_" in leaf_id:
            for token, row in proxy.get("filtered_jerk", {}).get(
                "duration_abs_gt_s", {}
            ).items():
                if f"_{str(token).replace('.', '_')}mps3_" in leaf_id:
                    return "computed_descriptive", row[axis], None
    if leaf_id.startswith("realtime.") and "_latency_" in leaf_id:
        for stage in (
            "pool_generation",
            "atoms",
            "context_weights",
            "selector_increment",
            "end_to_end",
        ):
            prefix = f"realtime.{stage}_latency_"
            if leaf_id.startswith(prefix):
                stat = leaf_id.removeprefix(prefix).removesuffix("_ms")
                row = latency.get(stage)
                if row is None:
                    return (
                        "scientifically_inapplicable",
                        None,
                        "stage_not_called_for_arm",
                    )
                return "computed_descriptive", row[stat], None
    if leaf_id.startswith("realtime.end_to_end_exceedance_rate_"):
        for budget, row in latency["budget"].items():
            if f"_{budget.replace('.', '_')}ms" in leaf_id:
                return "computed_descriptive", row["exceedance_rate"], None
    if leaf_id.startswith("realtime.end_to_end_max_overrun_"):
        for budget, row in latency["budget"].items():
            if f"_{budget.replace('.', '_')}ms_" in leaf_id:
                return "computed_descriptive", row["max_overrun_ms"], None
    if leaf_id in {
        "safety.collision_delta_v_mps",
        "safety.collision_contact_severity",
        "safety.time_headway_s",
        "safety.post_encroachment_time_s",
    } or leaf_id.startswith("operations.false_stop_"):
        return (
            "evidence_missing",
            None,
            "industrial_v3_required_context_not_available",
        )
    if (
        "occupant" in leaf_id
        or "iso" in leaf_id.lower()
        or "sae" in leaf_id.lower()
    ):
        return (
            "scientifically_inapplicable",
            None,
            "planar_proxy_is_not_occupant_conformity",
        )
    return "evidence_missing", None, "bounded_receipt_transform_not_supported"


def _literal_oriented_delta(
    direction: str, baseline: float, method: float
) -> float | None:
    if direction == "lower":
        return baseline - method
    if direction == "higher":
        return method - baseline
    return None


def _literal_paired_summary(values: Sequence[float | None]) -> dict[str, Any]:
    if len(values) != 100:
        raise ValueError("reviewer paired cluster denominator drifted")
    finite = [float(value) for value in values if value is not None]
    missing = 100 - len(finite)
    base = {
        "planned_cluster_count": 100,
        "finite_cluster_count": len(finite),
        "missing_or_failure_cluster_count": missing,
        "full_denominator_retained": True,
        "complete_case_inference_used": False,
    }
    if missing:
        return {
            **base,
            "status": "not_evaluable_full_denominator_missing_or_failure",
            "mean_oriented_delta": None,
            "ordinary_two_sided_student_t_ci95": None,
            "better_tie_worse": None,
        }
    array = np.asarray(finite, dtype=np.float64)
    mean = float(np.mean(array))
    from scipy.stats import t

    standard_error = float(np.std(array, ddof=1) / math.sqrt(array.size))
    critical = float(t.ppf(0.975, array.size - 1))
    return {
        **base,
        "status": "computed_exploratory_descriptive",
        "mean_oriented_delta": mean,
        "ordinary_two_sided_student_t_ci95": [
            mean - critical * standard_error,
            mean + critical * standard_error,
        ],
        "ordinary_ci_is_familywise_claim_evidence": False,
        "better_tie_worse": {
            "better": int(np.count_nonzero(array > 0.0)),
            "tie": int(np.count_nonzero(array == 0.0)),
            "worse": int(np.count_nonzero(array < 0.0)),
            "sum": int(array.size),
            "tie_rule": "exact_zero_float64_oriented_delta",
        },
    }


def _assert_semantic_equal(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not type(expected):
        raise ValueError(f"{label} type drifted")
    if type(actual) is dict:
        if set(actual) != set(expected):
            raise ValueError(f"{label} keyset drifted")
        for key in sorted(actual):
            _assert_semantic_equal(actual[key], expected[key], f"{label}/{key}")
        return
    if type(actual) is list:
        if len(actual) != len(expected):
            raise ValueError(f"{label} length drifted")
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            _assert_semantic_equal(left, right, f"{label}/{index}")
        return
    if type(actual) is float:
        if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f"{label} float drifted")
        return
    if actual != expected:
        raise ValueError(f"{label} value drifted")


def review_evaluation(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    execution_dir: Path,
    execution_root: str,
    preflight_dir: Path,
    preflight_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 evaluation")
    execution = _verify(execution_dir, execution_root, "multiroute-v2 execution")
    _verify(preflight_dir, preflight_root, "multiroute-v2 preflight")
    industrial_artifact = _verify(
        industrial_contract_dir,
        industrial_contract_root,
        "accepted industrial v3 contract",
    )
    industrial = review_contract_v3_literal(industrial_artifact["contract"])
    leaves = industrial["scalar_leaf_registry"]
    if (
        len(leaves) != 161
        or source.get("scalar_leaf_count") != 161
        or source.get("independent_cluster_count") != 100
        or source.get("execution_root_sha256") != execution_root
        or source.get("preflight_root_sha256") != preflight_root
        or source.get("industrial_contract_root_sha256")
        != industrial_contract_root
        or source.get("weighted_total_present") is not False
        or source.get("legacy_safetycost_computed") is not False
        or source.get("claim_authorized") is not False
        or execution.get("planned_tick_slots") != 19_200
    ):
        raise ValueError("reviewer evaluation authority or topology drifted")
    source_vectors = source["cluster_vectors"]
    if len(source_vectors) != 100:
        raise ValueError("reviewer evaluation cluster denominator drifted")
    values_by_leaf: dict[str, dict[str, list[dict[str, Any]]]] = {
        leaf["leaf_id"]: {arm: [] for arm in ARMS} for leaf in leaves
    }
    for cluster_summary, source_vector in zip(
        execution["cluster_artifacts"], source_vectors, strict=True
    ):
        cluster = int(cluster_summary["cluster_index"])
        if (
            source_vector["cluster_index"] != cluster
            or source_vector["source_cluster_root_sha256"]
            != cluster_summary["root_sha256"]
        ):
            raise ValueError("reviewer evaluation cluster binding drifted")
        cluster_dir = execution_dir / "clusters" / f"{cluster:03d}"
        verify_complete_seal(
            cluster_dir,
            cluster_summary["root_sha256"],
            label=f"reviewer multiroute-v2 cluster {cluster}",
        )
        cluster_execution = object_from(cluster_dir / "report.json")
        config = object_from(
            preflight_dir / "prepared" / f"{cluster:03d}" / "config.json"
        )
        geometry = _literal_geometry(config)
        expected_by_arm = {}
        for arm in cluster_execution["arms"]:
            expected_by_arm[arm["arm"]] = _literal_arm_metrics(
                arm, config, geometry
            )
        rows = source_vector["scalar_leaf_vector"]
        if len(rows) != 161:
            raise ValueError("reviewer cluster scalar leaf denominator drifted")
        for leaf, actual in zip(leaves, rows, strict=True):
            if actual["leaf_id"] != leaf["leaf_id"]:
                raise ValueError("reviewer scalar leaf order drifted")
            if set(actual["per_arm"]) != set(ARMS):
                raise ValueError("reviewer scalar leaf arm topology drifted")
            for arm in ARMS:
                summary, latency = expected_by_arm[arm]
                status, value, reason = _literal_lookup_leaf(
                    leaf, summary, latency
                )
                expected = {
                    "status": status,
                    "value": value,
                    "reason": reason,
                    "source_cluster_root_sha256": cluster_summary[
                        "root_sha256"
                    ],
                }
                _assert_semantic_equal(
                    actual["per_arm"][arm],
                    expected,
                    f"cluster={cluster}/leaf={leaf['leaf_id']}/arm={arm}",
                )
                values_by_leaf[leaf["leaf_id"]][arm].append(expected)
    expected_aggregates = []
    for leaf in leaves:
        per_arm = values_by_leaf[leaf["leaf_id"]]
        per_arm_summary = {}
        for arm in ARMS:
            finite = [
                float(row["value"])
                for row in per_arm[arm]
                if row["status"] == "computed_descriptive"
                and type(row["value"]) in {int, float}
                and not isinstance(row["value"], bool)
                and math.isfinite(float(row["value"]))
            ]
            per_arm_summary[arm] = {
                "planned_cluster_count": 100,
                "computed_scalar_cluster_count": len(finite),
                "missing_or_non_scalar_cluster_count": 100 - len(finite),
                "mean": float(np.mean(finite)) if len(finite) == 100 else None,
                "minimum": float(np.min(finite)) if len(finite) == 100 else None,
                "maximum": float(np.max(finite)) if len(finite) == 100 else None,
            }
        comparisons = {}
        for method in ("Static14D", "Scene14D"):
            deltas = []
            for baseline_row, method_row in zip(
                per_arm["pool_matched_candidate0"],
                per_arm[method],
                strict=True,
            ):
                if (
                    baseline_row["status"] != "computed_descriptive"
                    or method_row["status"] != "computed_descriptive"
                    or type(baseline_row["value"]) not in {int, float}
                    or isinstance(baseline_row["value"], bool)
                    or type(method_row["value"]) not in {int, float}
                    or isinstance(method_row["value"], bool)
                ):
                    deltas.append(None)
                else:
                    deltas.append(
                        _literal_oriented_delta(
                            leaf["direction"],
                            float(baseline_row["value"]),
                            float(method_row["value"]),
                        )
                    )
            comparisons[method] = {
                "direction": leaf["direction"],
                "oriented_delta_definition": (
                    "baseline_minus_method"
                    if leaf["direction"] == "lower"
                    else (
                        "method_minus_baseline"
                        if leaf["direction"] == "higher"
                        else "descriptive_unclassified"
                    )
                ),
                "cluster_oriented_deltas": deltas,
                "summary": _literal_paired_summary(deltas),
            }
        statuses = {
            row["status"] for arm in ARMS for row in per_arm[arm]
        }
        aggregate_status = (
            "computed_exploratory_multiroute"
            if statuses == {"computed_descriptive"}
            else (
                "scientifically_inapplicable"
                if statuses == {"scientifically_inapplicable"}
                else "evidence_missing_or_mixed_applicability"
            )
        )
        expected_aggregates.append(
            {
                **{
                    key: leaf[key]
                    for key in (
                        "leaf_id",
                        "parent_id",
                        "domain",
                        "units",
                        "direction",
                        "formula",
                        "opportunity_denominator",
                        "evidence_class",
                        "guardrail_role",
                        "multiplicity_family",
                        "test_type",
                    )
                },
                "status": aggregate_status,
                "per_arm_cluster_summary": per_arm_summary,
                "paired_comparisons": comparisons,
                "claim_gate_status": (
                    "not_evaluable_numeric_margin_unauthorized"
                    if leaf["test_type"] in {"noninferiority", "superiority"}
                    else "not_a_claim_test"
                ),
            }
        )
    _assert_semantic_equal(
        source["scalar_leaf_aggregates"],
        expected_aggregates,
        "aggregate scalar leaf vector",
    )
    expected_availability = {
        status: sum(row["status"] == status for row in expected_aggregates)
        for status in (
            "computed_exploratory_multiroute",
            "evidence_missing_or_mixed_applicability",
            "scientifically_inapplicable",
        )
    }
    if source["availability_counts"] != expected_availability:
        raise ValueError("reviewer evaluation availability drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_review_v1"
        ),
        "status": "independent_literal_evaluation_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "execution_root_sha256": execution_root,
        "preflight_root_sha256": preflight_root,
        "industrial_contract_root_sha256": industrial_contract_root,
        "cluster_count": 100,
        "scalar_leaf_count": 161,
        "availability_counts": expected_availability,
        "cluster_leaf_arm_values_rebuilt": 100 * 161 * 3,
        "paired_comparisons_rebuilt": 161 * 2,
        "ordinary_ci_is_familywise_claim_evidence": False,
        "holm_iut_ni_claim_performed": False,
        "weighted_total_present": False,
        "legacy_safetycost_computed": False,
        "producer_evaluator_metric_decision_oracle_imported": False,
        "claim_authorized": False,
    }
    return _write_review(
        output,
        report,
        role="industrial_v3_multiroute_v2_evaluation_review",
        source_root=source_root,
        label="V25 industrial-v3 multiroute-v2 evaluation review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("contract", "matrix", "preflight", "execution", "evaluation"):
        part = sub.add_parser(command)
        part.add_argument("--output", type=Path, required=True)
        part.add_argument("--source-dir", type=Path, required=True)
        part.add_argument("--source-root", required=True)
        if command in {"matrix", "preflight"}:
            part.add_argument("--contract-dir", type=Path, required=True)
            part.add_argument("--contract-root", required=True)
        if command == "matrix":
            part.add_argument("--capability-dir", type=Path, required=True)
            part.add_argument("--capability-root", required=True)
        if command == "preflight":
            part.add_argument("--matrix-dir", type=Path, required=True)
            part.add_argument("--matrix-root", required=True)
            part.add_argument("--focused-dir", type=Path, required=True)
            part.add_argument("--focused-root", required=True)
        if command == "execution":
            part.add_argument("--preflight-dir", type=Path, required=True)
            part.add_argument("--preflight-root", required=True)
            part.add_argument("--training-dir", type=Path, required=True)
            part.add_argument("--training-root", required=True)
        if command == "evaluation":
            part.add_argument("--execution-dir", type=Path, required=True)
            part.add_argument("--execution-root", required=True)
            part.add_argument("--preflight-dir", type=Path, required=True)
            part.add_argument("--preflight-root", required=True)
            part.add_argument("--industrial-contract-dir", type=Path, required=True)
            part.add_argument("--industrial-contract-root", required=True)
    args = parser.parse_args()
    if args.command == "contract":
        root = review_contract(
            args.output, source_dir=args.source_dir, source_root=args.source_root
        )
    elif args.command == "matrix":
        root = review_matrix(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            capability_dir=args.capability_dir,
            capability_root=args.capability_root,
        )
    elif args.command == "preflight":
        root = review_preflight(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            focused_dir=args.focused_dir,
            focused_root=args.focused_root,
        )
    elif args.command == "execution":
        root = review_execution(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            preflight_dir=args.preflight_dir,
            preflight_root=args.preflight_root,
            training_dir=args.training_dir,
            training_root=args.training_root,
        )
    else:
        root = review_evaluation(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            execution_dir=args.execution_dir,
            execution_root=args.execution_root,
            preflight_dir=args.preflight_dir,
            preflight_root=args.preflight_root,
            industrial_contract_dir=args.industrial_contract_dir,
            industrial_contract_root=args.industrial_contract_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
