from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

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
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
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
) -> str:
    source = _verify(source_dir, source_root, "multiroute-v2 preflight")
    contract = _verify(contract_dir, contract_root, "multiroute-v2 contract")
    matrix = _verify(matrix_dir, matrix_root, "multiroute-v2 matrix")
    review_contract_semantics(contract["contract"])
    if (
        source.get("status") != "passed_before_first_model_call"
        or source.get("source_root_sha256") != EXPECTED_SOURCE_ROOT
        or source.get("selected_manifest_sha256") != EXPECTED_SELECTED_MANIFEST
        or source.get("cluster_count") != 100
        or source.get("planned_tick_slots") != 19_200
        or source.get("model_pool_selector_calls") != 0
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


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("contract", "matrix", "preflight", "execution"):
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
        if command == "execution":
            part.add_argument("--preflight-dir", type=Path, required=True)
            part.add_argument("--preflight-root", required=True)
            part.add_argument("--training-dir", type=Path, required=True)
            part.add_argument("--training-root", required=True)
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
        )
    else:
        root = review_execution(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            preflight_dir=args.preflight_dir,
            preflight_root=args.preflight_root,
            training_dir=args.training_dir,
            training_root=args.training_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
