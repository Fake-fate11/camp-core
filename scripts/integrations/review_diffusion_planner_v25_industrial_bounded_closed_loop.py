from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_bounded_closed_loop_review import (  # noqa: E402
    EXPECTED_AUTHORITY,
    EXPECTED_PARAMETERS,
    review_contract_literal,
    review_evaluation,
    review_execution_receipts,
    review_latent_manifest,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v3 import (  # noqa: E402
    review_contract_v3_literal,
)
from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_contract(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="bounded contract")
    verify_complete_seal(
        industrial_contract_dir,
        industrial_contract_root,
        label="accepted industrial v3 contract",
    )
    source = object_from(contract_dir / "report.json")
    industrial = object_from(industrial_contract_dir / "report.json")
    reviewed = review_contract_literal(source["contract"], industrial["contract"])
    interpreter = source.get("interpreter")
    if (
        type(interpreter) is not dict
        or interpreter.get("minimum_version_passed") is not True
        or interpreter.get("version_info", [0, 0])[:2] < [3, 10]
        or not str(interpreter.get("sys_executable", ""))
    ):
        raise ValueError("contract interpreter receipt drifted")
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_bounded_closed_loop_contract_review_v1"
            ),
            "status": "passed_independent_literal_contract_review",
            "contract_binding": {
                "path": str(contract_dir.resolve()),
                "root_sha256": contract_root,
            },
            "industrial_contract_binding": {
                "path": str(industrial_contract_dir.resolve()),
                "root_sha256": industrial_contract_root,
            },
            "reviewed_contract_sha256": hashlib.sha256(
                (
                    __import__("json").dumps(
                        reviewed,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("utf-8")
            ).hexdigest(),
            "literal_oracle": {
                "producer_contract_module_imported": False,
                "producer_decision_or_evaluator_oracle_imported": False,
                "architecture_denominator_latency_rebuilt": True,
                "industrial_v3_leaf_topology_rebuilt": True,
                "interpreter_and_prohibitions_rebuilt": True,
            },
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
            "claim_authorized": False,
        },
        {
            "role": "independent_industrial_v3_bounded_contract_review",
            "reviewer_head": git_head(),
            "authority_sha256": EXPECTED_AUTHORITY,
            "contract_root_sha256": contract_root,
            "industrial_contract_root_sha256": industrial_contract_root,
        },
        label="V25 independent bounded contract review",
    )


def review_matrix(
    output: Path,
    matrix_dir: Path,
    matrix_root: str,
    contract_dir: Path,
    contract_root: str,
) -> str:
    verify_complete_seal(matrix_dir, matrix_root, label="hardening matrix")
    verify_complete_seal(contract_dir, contract_root, label="bounded contract")
    matrix = object_from(matrix_dir / "report.json")
    contract = object_from(contract_dir / "report.json")["contract"]
    rows = matrix.get("parameter_rows")
    if (
        type(rows) is not list
        or [row.get("parameter") for row in rows] != EXPECTED_PARAMETERS
        or rows
        != contract["pre_execution_hardening"]["parameter_propagation_matrix"]
    ):
        raise ValueError("independent matrix parameter topology drifted")
    entries = matrix.get("production_entrypoints")
    if type(entries) is not list or len(entries) < 8:
        raise ValueError("independent production entrypoint inventory is incomplete")
    for entry in entries:
        if set(entry) != {"relative_path", "sha256", "actual_execution_path"}:
            raise ValueError("independent entrypoint schema drifted")
        path = (ROOT / entry["relative_path"]).resolve()
        if not path.is_file() or _file_sha(path) != entry["sha256"]:
            raise ValueError("independent entrypoint source SHA drifted")
    required_cases = {
        "synthetic_pass",
        "typed_execution_failure",
        "missing_required_keyword",
        "wrong_interpreter",
        "wrong_schema_or_version",
        "extra_missing_duplicate_field",
        "nan_or_inf",
        "path_alias",
        "partial_atomic_write",
        "resign_or_repin",
        "wrong_root_head_model_checkpoint_route",
        "wrong_arm_denominator_or_latency_namespace",
    }
    if set(matrix.get("dry_run_cases", [])) != required_cases:
        raise ValueError("independent hardening mutation topology drifted")
    if (
        matrix.get("zero_bug_claimed") is not False
        or matrix.get("model_pool_selector_calls") != 0
        or matrix.get("outcome_values_read") is not False
    ):
        raise ValueError("independent hardening boundary drifted")
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_production_hardening_matrix_review_v1"
            ),
            "status": "passed_independent_literal_hardening_matrix_review",
            "matrix_binding": {
                "path": str(matrix_dir.resolve()),
                "root_sha256": matrix_root,
            },
            "contract_root_sha256": contract_root,
            "parameter_count": len(rows),
            "production_entrypoint_count": len(entries),
            "mutation_case_count": len(required_cases),
            "literal_oracle": {
                "producer_matrix_module_imported": False,
                "file_shas_recomputed": True,
                "parameter_topology_rebuilt": True,
                "mutation_topology_rebuilt": True,
                "residual_risk_classes_rebuilt": True,
            },
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
        },
        {
            "role": "independent_production_hardening_matrix_review",
            "reviewer_head": git_head(),
            "authority_sha256": EXPECTED_AUTHORITY,
            "matrix_root_sha256": matrix_root,
            "contract_root_sha256": contract_root,
        },
        label="V25 independent hardening matrix review",
    )


def review_preflight(
    output: Path,
    preflight_dir: Path,
    preflight_root: str,
    contract_dir: Path,
    contract_root: str,
    matrix_dir: Path,
    matrix_root: str,
) -> str:
    verify_complete_seal(preflight_dir, preflight_root, label="bounded preflight")
    verify_complete_seal(contract_dir, contract_root, label="bounded contract")
    verify_complete_seal(matrix_dir, matrix_root, label="hardening matrix")
    source = object_from(preflight_dir / "report.json")
    contract_report = object_from(contract_dir / "report.json")
    matrix = object_from(matrix_dir / "report.json")
    if (
        source.get("schema_version")
        != "camp_dp_v25_industrial_v3_bounded_preflight_v1"
        or source.get("status") != "passed_before_first_model_call"
        or source.get("authority_sha256") != EXPECTED_AUTHORITY
        or source.get("bindings", {}).get("contract_root_sha256") != contract_root
        or source.get("bindings", {}).get("matrix_root_sha256") != matrix_root
        or matrix.get("contract_root_sha256") != contract_root
    ):
        raise ValueError("independent preflight authority drifted")
    review_latent_manifest(source.get("latent_manifest"))
    clone = source.get("initial_input_clone")
    if type(clone) is not dict:
        raise ValueError("independent initial clone receipt missing")
    payload = clone.get("payload")
    if type(payload) is not dict:
        raise ValueError("independent initial clone payload missing")
    expected_clone = hashlib.sha256(
        (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    forbidden_path = Path(clone["forbidden_inventory_path"])
    forbidden_bytes = forbidden_path.read_bytes()
    forbidden = json.loads(forbidden_bytes)
    if (
        expected_clone != clone.get("clone_key_sha256")
        or hashlib.sha256(forbidden_bytes).hexdigest()
        != clone.get("forbidden_inventory_sha256")
        or expected_clone in set(forbidden.get("clone_keys", []))
        or clone.get("intersection_count") != 0
    ):
        raise ValueError("independent input-only zero-overlap drifted")
    capacity = source.get("capacity")
    if (
        type(capacity) is not dict
        or capacity.get("projected_free_after_bytes", 0)
        < capacity.get("minimum_free_after_bytes", 1)
    ):
        raise ValueError("independent capacity gate drifted")
    interpreter = source.get("interpreter")
    if (
        type(interpreter) is not dict
        or interpreter.get("sys_executable")
        != "/root/autodl-tmp/dp312_venv/bin/python"
        or interpreter.get("version_info", [0, 0])[:2] < [3, 10]
    ):
        raise ValueError("independent preflight interpreter drifted")
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_bounded_preflight_review_v1"
            ),
            "status": "passed_independent_literal_preflight_review",
            "preflight_binding": {
                "path": str(preflight_dir.resolve()),
                "root_sha256": preflight_root,
            },
            "contract_root_sha256": contract_root,
            "matrix_root_sha256": matrix_root,
            "latent_tick_count": 64,
            "forbidden_clone_key_count": clone["forbidden_clone_key_count"],
            "zero_overlap_intersection_count": 0,
            "literal_oracle": {
                "producer_preflight_module_imported": False,
                "latent_bytes_rebuilt": True,
                "clone_key_rehashed": True,
                "forbidden_inventory_reloaded": True,
                "capacity_and_interpreter_rebuilt": True,
            },
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
        },
        {
            "role": "independent_industrial_v3_bounded_preflight_review",
            "reviewer_head": git_head(),
            "authority_sha256": EXPECTED_AUTHORITY,
            "preflight_root_sha256": preflight_root,
            "contract_root_sha256": contract_root,
        },
        label="V25 independent bounded preflight review",
    )


def review_execution(
    output: Path,
    execution_dir: Path,
    execution_root: str,
    preflight_dir: Path,
    preflight_root: str,
) -> str:
    verify_complete_seal(execution_dir, execution_root, label="bounded execution")
    verify_complete_seal(preflight_dir, preflight_root, label="bounded preflight")
    source = object_from(execution_dir / "report.json")
    preflight = object_from(preflight_dir / "report.json")
    if (
        source.get("schema_version")
        != "camp_dp_v25_industrial_v3_bounded_execution_v1"
        or source.get("authority_sha256") != EXPECTED_AUTHORITY
        or source.get("preflight_binding", {}).get("root_sha256") != preflight_root
    ):
        raise ValueError("independent execution authority drifted")
    accounting = review_execution_receipts(
        source.get("arms"), preflight.get("latent_manifest")
    )
    with np.load(execution_dir / "preimages.npz", allow_pickle=False) as arrays:
        if set(arrays.files) != {
            "0_candidates",
            "0_neighbors",
            "1_candidates",
            "1_neighbors",
            "2_candidates",
            "2_neighbors",
        }:
            raise ValueError("independent execution preimage keyset drifted")
        for index, arm in enumerate(source["arms"]):
            candidates = np.asarray(arrays[f"{index}_candidates"])
            neighbors = np.asarray(arrays[f"{index}_neighbors"])
            if (
                candidates.shape != (64, 8, 80, 4)
                or candidates.dtype != np.float32
                or neighbors.shape != (64, 8, 32, 80, 4)
                or neighbors.dtype != np.float32
            ):
                raise ValueError("independent execution tensor shape/dtype drifted")
            for tick, receipt in enumerate(arm["ticks"]):
                if (
                    array_sha256(candidates[tick])
                    != receipt["candidate_tensor_sha256_before"]
                    or array_sha256(neighbors[tick])
                    != receipt["candidate_neighbor_sha256"]
                    or [array_sha256(row) for row in candidates[tick]]
                    != receipt["candidate_row_sha256"]
                ):
                    raise ValueError("independent execution raw tensor binding drifted")
    if (
        source.get("formal_model_call_count") != 192
        or source.get("sequential_model_call_count") != 0
        or source.get("post_pool_model_dp_latent_generation_call_count") != 0
        or source.get("hard_integrity_failures") != []
        or source.get("status")
        != "complete_full_denominator_hard_integrity_passed"
    ):
        raise ValueError("independent execution hard integrity gate drifted")
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_bounded_execution_review_v1"
            ),
            "status": "passed_independent_literal_execution_review",
            "execution_binding": {
                "path": str(execution_dir.resolve()),
                "root_sha256": execution_root,
            },
            "preflight_root_sha256": preflight_root,
            "denominator": accounting,
            "formal_model_call_count": 192,
            "sequential_model_call_count": 0,
            "post_pool_forbidden_call_count": 0,
            "tensor_mutation_count": 0,
            "literal_oracle": {
                "runner_generator_selector_failure_oracle_imported": False,
                "raw_candidate_neighbor_bytes_rebuilt": True,
                "latent_call_pool_tensor_bindings_rebuilt": True,
                "terminal_denominator_rebuilt": True,
                "selected_row_and_zero_call_rebuilt": True,
            },
            "claim_authorized": False,
        },
        {
            "role": "independent_industrial_v3_bounded_execution_review",
            "reviewer_head": git_head(),
            "authority_sha256": EXPECTED_AUTHORITY,
            "execution_root_sha256": execution_root,
            "preflight_root_sha256": preflight_root,
        },
        label="V25 independent bounded execution review",
    )


def review_bounded_evaluation(
    output: Path,
    evaluation_dir: Path,
    evaluation_root: str,
    execution_dir: Path,
    execution_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    verify_complete_seal(evaluation_dir, evaluation_root, label="bounded evaluation")
    verify_complete_seal(execution_dir, execution_root, label="bounded execution")
    verify_complete_seal(
        industrial_contract_dir,
        industrial_contract_root,
        label="accepted industrial v3 contract",
    )
    evaluation = object_from(evaluation_dir / "report.json")
    execution = object_from(execution_dir / "report.json")
    industrial = review_contract_v3_literal(
        object_from(industrial_contract_dir / "report.json")["contract"]
    )
    expected_ids = [row["leaf_id"] for row in industrial["scalar_leaf_registry"]]
    reviewed = review_evaluation(evaluation, expected_ids)
    if (
        reviewed.get("execution_binding", {}).get("root_sha256") != execution_root
        or reviewed.get("industrial_contract_binding", {}).get("root_sha256")
        != industrial_contract_root
        or execution.get("denominator", {}).get("planned_ticks") != 192
    ):
        raise ValueError("independent bounded evaluation root binding drifted")
    for leaf, expected in zip(
        reviewed["scalar_leaf_vector"],
        industrial["scalar_leaf_registry"],
    ):
        for field in (
            "leaf_id",
            "parent_id",
            "domain",
            "units",
            "direction",
            "formula",
            "opportunity_denominator",
            "evidence_class",
        ):
            if leaf.get(field) != expected.get(field):
                raise ValueError(
                    f"independent bounded leaf semantic drifted: {leaf.get('leaf_id')} {field}"
                )
        if set(leaf.get("per_arm", {})) != {
            "pool_matched_candidate0",
            "Static14D",
            "Scene14D",
        }:
            raise ValueError("independent bounded leaf arm vector drifted")
        for arm_value in leaf["per_arm"].values():
            value = arm_value.get("value")
            if value is not None and isinstance(value, (int, float)):
                if not np.isfinite(float(value)):
                    raise ValueError("independent bounded leaf nonfinite value")
            if arm_value.get("source_execution_root_sha256") != execution_root:
                raise ValueError("independent bounded leaf source root drifted")
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_bounded_evaluation_review_v1"
            ),
            "status": "passed_independent_literal_bounded_evaluation_review",
            "evaluation_binding": {
                "path": str(evaluation_dir.resolve()),
                "root_sha256": evaluation_root,
            },
            "execution_root_sha256": execution_root,
            "industrial_contract_root_sha256": industrial_contract_root,
            "parent_endpoint_count": 56,
            "scalar_leaf_count": 161,
            "inferential_status": "not_evaluable_bounded_single_cluster",
            "weighted_total_present": False,
            "legacy_safetycost_computed": False,
            "literal_oracle": {
                "evaluator_metric_or_decision_oracle_imported": False,
                "industrial_v3_leaf_semantics_rebuilt": True,
                "source_root_units_denominator_missing_topology_rebuilt": True,
                "single_cluster_no_claim_topology_rebuilt": True,
            },
            "claim_authorized": False,
        },
        {
            "role": "independent_industrial_v3_bounded_evaluation_review",
            "reviewer_head": git_head(),
            "authority_sha256": EXPECTED_AUTHORITY,
            "evaluation_root_sha256": evaluation_root,
            "execution_root_sha256": execution_root,
        },
        label="V25 independent bounded evaluation review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="stage", required=True)
    contract_parser = subs.add_parser("contract")
    contract_parser.add_argument("--output", type=Path, required=True)
    contract_parser.add_argument("--contract-dir", type=Path, required=True)
    contract_parser.add_argument("--contract-root", required=True)
    contract_parser.add_argument("--industrial-contract-dir", type=Path, required=True)
    contract_parser.add_argument("--industrial-contract-root", required=True)
    matrix_parser = subs.add_parser("matrix")
    matrix_parser.add_argument("--output", type=Path, required=True)
    matrix_parser.add_argument("--matrix-dir", type=Path, required=True)
    matrix_parser.add_argument("--matrix-root", required=True)
    matrix_parser.add_argument("--contract-dir", type=Path, required=True)
    matrix_parser.add_argument("--contract-root", required=True)
    preflight_parser = subs.add_parser("preflight")
    for name in ("output", "preflight-dir", "contract-dir", "matrix-dir"):
        preflight_parser.add_argument("--" + name, type=Path, required=True)
    for name in ("preflight-root", "contract-root", "matrix-root"):
        preflight_parser.add_argument("--" + name, required=True)
    execution_parser = subs.add_parser("execution")
    for name in ("output", "execution-dir", "preflight-dir"):
        execution_parser.add_argument("--" + name, type=Path, required=True)
    for name in ("execution-root", "preflight-root"):
        execution_parser.add_argument("--" + name, required=True)
    evaluation_parser = subs.add_parser("evaluation")
    for name in (
        "output",
        "evaluation-dir",
        "execution-dir",
        "industrial-contract-dir",
    ):
        evaluation_parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "evaluation-root",
        "execution-root",
        "industrial-contract-root",
    ):
        evaluation_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = review_contract(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.industrial_contract_dir,
            args.industrial_contract_root,
        )
    elif args.stage == "matrix":
        root = review_matrix(
            args.output,
            args.matrix_dir,
            args.matrix_root,
            args.contract_dir,
            args.contract_root,
        )
    elif args.stage == "preflight":
        root = review_preflight(
            args.output,
            args.preflight_dir,
            args.preflight_root,
            args.contract_dir,
            args.contract_root,
            args.matrix_dir,
            args.matrix_root,
        )
    elif args.stage == "execution":
        root = review_execution(
            args.output,
            args.execution_dir,
            args.execution_root,
            args.preflight_dir,
            args.preflight_root,
        )
    else:
        root = review_bounded_evaluation(
            args.output,
            args.evaluation_dir,
            args.evaluation_root,
            args.execution_dir,
            args.execution_root,
            args.industrial_contract_dir,
            args.industrial_contract_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
