from __future__ import annotations

import argparse
import math
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
from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    _collision_and_proximity,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_evaluation_actor_binding import (  # noqa: E402
    AFFECTED_LEAF_SET_SHA256,
    ARMS,
    AUTHORITY_SHA256,
    CLUSTER_COUNT,
    EXECUTION_REVIEW_ROOT_SHA256,
    EXECUTION_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_ROOT_SHA256,
    SUPERSEDED_EVALUATION_ROOT_SHA256,
    affected_leaf_ids,
    canonical_sha256,
    continuation_sha256,
    exact_dirs,
    validate_sealed_actor_binding,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    object_from,
    write_atomic,
)
from scripts.integrations.materialize_diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    _load_root_bound_geometry,
)
from scripts.integrations.run_diffusion_planner_v25_industrial_bounded_closed_loop import (  # noqa: E402
    _arm_metrics,
    _convex_partition_drivable_polygons,
    _lookup_leaf_value,
    _native_from_execution,
)


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _finite_scalar(value: Any) -> float | None:
    if type(value) not in (int, float) or isinstance(value, bool):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _oriented_delta(direction: str, baseline: float, method: float) -> float | None:
    if direction == "lower":
        return baseline - method
    if direction == "higher":
        return method - baseline
    return None


def _paired_summary(values: list[float | None]) -> dict[str, Any]:
    if len(values) != CLUSTER_COUNT:
        raise ValueError("paired cluster denominator drifted")
    finite = [float(value) for value in values if value is not None]
    missing = len(values) - len(finite)
    result: dict[str, Any] = {
        "planned_cluster_count": CLUSTER_COUNT,
        "finite_cluster_count": len(finite),
        "missing_or_failure_cluster_count": missing,
        "full_denominator_retained": True,
        "complete_case_inference_used": False,
    }
    if missing:
        return {
            **result,
            "status": "not_evaluable_full_denominator_missing_or_failure",
            "mean_oriented_delta": None,
            "ordinary_two_sided_student_t_ci95": None,
            "better_tie_worse": None,
        }
    array = np.asarray(finite, dtype=np.float64)
    mean = float(np.mean(array))
    if len(array) < 2:
        ci = None
    else:
        from scipy.stats import t

        standard_error = float(np.std(array, ddof=1) / math.sqrt(len(array)))
        critical = float(t.ppf(0.975, len(array) - 1))
        ci = [mean - critical * standard_error, mean + critical * standard_error]
    return {
        **result,
        "status": "computed_exploratory_descriptive",
        "mean_oriented_delta": mean,
        "ordinary_two_sided_student_t_ci95": ci,
        "ordinary_ci_is_familywise_claim_evidence": False,
        "better_tie_worse": {
            "better": int(np.count_nonzero(array > 0.0)),
            "tie": int(np.count_nonzero(array == 0.0)),
            "worse": int(np.count_nonzero(array < 0.0)),
            "sum": len(array),
            "tie_rule": "exact_zero_float64_oriented_delta",
        },
    }


def _actor_bound_arm_metrics(
    arm: Mapping[str, Any],
    config: Mapping[str, Any],
    geometry: Mapping[str, Any],
    *,
    execution_root: str,
    cluster_root: str,
    cluster_index: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    arm_name = str(arm["arm"])
    binding = validate_sealed_actor_binding(
        arm,
        execution_root_sha256=execution_root,
        cluster_root_sha256=cluster_root,
        cluster_index=cluster_index,
        expected_arm=arm_name,
    )
    summary, latency = _arm_metrics(arm, config, geometry)
    native = _native_from_execution(arm, config)
    actor_rows = (
        native["ticks"][0]["controlled_scene"]["actors"]
        if native["ticks"]
        else []
    )
    actor_specs = {
        str(row["id"]): {
            "id": row["id"],
            "length_m": row["length_m"],
            "width_m": row["width_m"],
            "wheelbase_m": row["wheelbase_m"],
        }
        for row in actor_rows
    }
    spawn = config["spawn_config"]
    collision, proximity = _collision_and_proximity(
        ticks=native["ticks"],
        actor_source_ticks=native["ticks"],
        actor_specs=actor_specs,
        ego_length=float(spawn["ego_length"]),
        ego_width=float(spawn["ego_width"]),
        ego_wheelbase=float(spawn["ego_wheelbase"]),
    )
    summary["endpoints"]["collision"] = collision
    summary["endpoints"]["dynamic_proximity"] = proximity
    return summary, latency, binding


def _aggregate(
    leaves: list[dict[str, Any]],
    values_by_leaf: dict[str, dict[str, list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    aggregate_leaves = []
    for leaf in leaves:
        per_arm = values_by_leaf[leaf["leaf_id"]]
        arm_summaries = {}
        for arm in ARMS:
            finite = [
                value
                for row in per_arm[arm]
                if (value := _finite_scalar(row["value"])) is not None
                and row["status"] == "computed_descriptive"
            ]
            arm_summaries[arm] = {
                "planned_cluster_count": CLUSTER_COUNT,
                "computed_scalar_cluster_count": len(finite),
                "missing_or_non_scalar_cluster_count": CLUSTER_COUNT - len(finite),
                "mean": float(np.mean(finite)) if len(finite) == CLUSTER_COUNT else None,
                "minimum": float(np.min(finite)) if len(finite) == CLUSTER_COUNT else None,
                "maximum": float(np.max(finite)) if len(finite) == CLUSTER_COUNT else None,
            }
        comparisons = {}
        for method in ("Static14D", "Scene14D"):
            deltas: list[float | None] = []
            for baseline_row, method_row in zip(
                per_arm["pool_matched_candidate0"], per_arm[method], strict=True
            ):
                baseline = _finite_scalar(baseline_row["value"])
                candidate = _finite_scalar(method_row["value"])
                if (
                    baseline_row["status"] != "computed_descriptive"
                    or method_row["status"] != "computed_descriptive"
                    or baseline is None
                    or candidate is None
                ):
                    deltas.append(None)
                else:
                    deltas.append(
                        _oriented_delta(leaf["direction"], baseline, candidate)
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
                "summary": _paired_summary(deltas),
            }
        statuses = {row["status"] for arm in ARMS for row in per_arm[arm]}
        status = (
            "computed_exploratory_multiroute"
            if statuses == {"computed_descriptive"}
            else (
                "scientifically_inapplicable"
                if statuses == {"scientifically_inapplicable"}
                else "evidence_missing_or_mixed_applicability"
            )
        )
        aggregate_leaves.append(
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
                "status": status,
                "per_arm_cluster_summary": arm_summaries,
                "paired_comparisons": comparisons,
                "claim_gate_status": (
                    "not_evaluable_numeric_margin_unauthorized"
                    if leaf["test_type"] in {"noninferiority", "superiority"}
                    else "not_a_claim_test"
                ),
            }
        )
    return aggregate_leaves


def _regression_rows(report: Mapping[str, Any]) -> dict[tuple[int, str], Any]:
    rows: dict[tuple[int, str], Any] = {}
    for cluster in report["cluster_vectors"]:
        cluster_index = int(cluster["cluster_index"])
        for row in cluster["scalar_leaf_vector"]:
            rows[(cluster_index, str(row["leaf_id"]))] = row
    return rows


def evaluate(
    *,
    output: Path,
    implementation_head: str,
    execution_dir: Path,
    execution_review_dir: Path,
    preflight_dir: Path,
    preflight_root: str,
    industrial_contract_dir: Path,
    superseded_evaluation_dir: Path,
) -> str:
    continuation = continuation_sha256(implementation_head)
    expected_dirs = exact_dirs(implementation_head, continuation)
    if output.resolve() != Path(expected_dirs["evaluation"]):
        raise ValueError("corrected evaluation exact dir drifted")
    execution = _verify(
        execution_dir, EXECUTION_ROOT_SHA256, "sealed multiroute execution"
    )
    _verify(
        execution_review_dir,
        EXECUTION_REVIEW_ROOT_SHA256,
        "sealed multiroute execution review",
    )
    _verify(preflight_dir, preflight_root, "sealed multiroute preflight")
    old = _verify(
        superseded_evaluation_dir,
        SUPERSEDED_EVALUATION_ROOT_SHA256,
        "superseded unreviewed evaluation diagnostic",
    )
    industrial = _verify(
        industrial_contract_dir,
        INDUSTRIAL_CONTRACT_ROOT_SHA256,
        "accepted industrial v3 contract",
    )["contract"]
    if (
        execution.get("status")
        != "complete_full_denominator_hard_integrity_passed"
        or execution.get("terminal_accounting", {}).get("unattempted") != 0
        or len(execution.get("cluster_artifacts", [])) != CLUSTER_COUNT
        or len(industrial.get("scalar_leaf_registry", [])) != 161
    ):
        raise ValueError("corrected evaluation sealed input gate drifted")
    leaves = industrial["scalar_leaf_registry"]
    affected = set(affected_leaf_ids())
    all_ids = [str(row["leaf_id"]) for row in leaves]
    if (
        len(all_ids) != len(set(all_ids))
        or not affected.issubset(all_ids)
        or len(set(all_ids) - affected) != 118
        or "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
        in affected
    ):
        raise ValueError("corrected evaluation 43/118 topology drifted")
    values_by_leaf = {
        leaf_id: {arm: [] for arm in ARMS} for leaf_id in all_ids
    }
    cluster_vectors = []
    for cluster_summary in execution["cluster_artifacts"]:
        cluster = int(cluster_summary["cluster_index"])
        cluster_dir = execution_dir / "clusters" / f"{cluster:03d}"
        verify_complete_seal(
            cluster_dir,
            cluster_summary["root_sha256"],
            label=f"sealed cluster {cluster}",
        )
        cluster_execution = object_from(cluster_dir / "report.json")
        config = object_from(
            preflight_dir / "prepared" / f"{cluster:03d}" / "config.json"
        )
        geometry = dict(_load_root_bound_geometry(config))
        geometry["drivable_polygons"] = _convex_partition_drivable_polygons(
            geometry["drivable_polygons"]
        )
        geometry["drivable_polygon_transform"] = (
            "deterministic_simple_polygon_ear_clipping_exact_union_v1"
        )
        arm_summaries = {}
        arm_latencies = {}
        bindings = {}
        for arm in cluster_execution["arms"]:
            summary, latency, binding = _actor_bound_arm_metrics(
                arm,
                config,
                geometry,
                execution_root=EXECUTION_ROOT_SHA256,
                cluster_root=cluster_summary["root_sha256"],
                cluster_index=cluster,
            )
            arm_name = str(arm["arm"])
            arm_summaries[arm_name] = summary
            arm_latencies[arm_name] = latency
            bindings[arm_name] = binding
        vector = []
        for leaf in leaves:
            per_arm = {}
            for arm in ARMS:
                status, value, reason = _lookup_leaf_value(
                    leaf, arm_summaries[arm], arm_latencies[arm]
                )
                row = {
                    "status": status,
                    "value": value,
                    "reason": reason,
                    "source_cluster_root_sha256": cluster_summary["root_sha256"],
                }
                per_arm[arm] = row
                values_by_leaf[leaf["leaf_id"]][arm].append(row)
            vector.append({"leaf_id": leaf["leaf_id"], "per_arm": per_arm})
        cluster_vectors.append(
            {
                "cluster_index": cluster,
                "clone_key_sha256": cluster_summary["clone_key_sha256"],
                "source_cluster_root_sha256": cluster_summary["root_sha256"],
                "sealed_actor_bindings": bindings,
                "scalar_leaf_vector": vector,
            }
        )
    aggregate_leaves = _aggregate(leaves, values_by_leaf)
    old_rows = _regression_rows(old)
    new_rows = _regression_rows({"cluster_vectors": cluster_vectors})
    unaffected = set(all_ids) - affected
    for cluster in range(CLUSTER_COUNT):
        for leaf_id in unaffected:
            if new_rows[(cluster, leaf_id)] != old_rows[(cluster, leaf_id)]:
                raise ValueError(
                    f"unaffected leaf regression drifted: {cluster}/{leaf_id}"
                )
    old_aggregates = {
        str(row["leaf_id"]): row for row in old["scalar_leaf_aggregates"]
    }
    for row in aggregate_leaves:
        if (
            row["leaf_id"] in unaffected
            and row != old_aggregates[row["leaf_id"]]
        ):
            raise ValueError(
                f"unaffected aggregate regression drifted: {row['leaf_id']}"
            )
    availability = {
        status: sum(row["status"] == status for row in aggregate_leaves)
        for status in (
            "computed_exploratory_multiroute",
            "evidence_missing_or_mixed_applicability",
            "scientifically_inapplicable",
        )
    }
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "actor_binding_replacement_evaluation_v1"
        ),
        "status": (
            "sealed_exploratory_multiroute_industrial_v3_"
            "actor_binding_corrected_vector"
        ),
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "continuation_sha256": continuation,
        "exact_dirs": expected_dirs,
        "execution_root_sha256": EXECUTION_ROOT_SHA256,
        "execution_review_root_sha256": EXECUTION_REVIEW_ROOT_SHA256,
        "preflight_root_sha256": preflight_root,
        "industrial_contract_root_sha256": INDUSTRIAL_CONTRACT_ROOT_SHA256,
        "superseded_evaluation_root_sha256": (
            SUPERSEDED_EVALUATION_ROOT_SHA256
        ),
        "superseded_evaluation_accepted_scientific_result": False,
        "superseded_evaluation_used_as_corrected_result_input": False,
        "superseded_evaluation_used_only_for_118_leaf_regression": True,
        "affected_leaf_count": 43,
        "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        "unaffected_leaf_count": 118,
        "collision_onset_proxy_changed": False,
        "parent_endpoint_count": 56,
        "scalar_leaf_count": 161,
        "independent_cluster_count": CLUSTER_COUNT,
        "cluster_vectors": cluster_vectors,
        "scalar_leaf_aggregates": aggregate_leaves,
        "availability_counts": availability,
        "statistics": {
            "independent_unit": "prespecified_route_corridor_semantic_cluster",
            "independent_n": CLUSTER_COUNT,
            "ordinary_two_sided_paired_student_t_ci95_is_descriptive": True,
            "better_tie_worse_exact_zero": True,
            "holm_status": (
                "not_evaluable_numeric_margins_unauthorized_no_familywise_claim"
            ),
            "iut_ni_claim_status": "not_evaluable_no_prespecified_numeric_margin",
            "ticks_arms_k8_rows_used_as_independent_n": False,
        },
        "model_dp_latent_pool_selector_execution_rerun_calls": 0,
        "legacy_safetycost_computed": False,
        "weighted_total_present": False,
        "fresh_or_b4_outcome_values_read": False,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }
    report["cluster_vector_sha256"] = canonical_sha256(cluster_vectors)
    report["aggregate_vector_sha256"] = canonical_sha256(aggregate_leaves)
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_v2_actor_binding_evaluation",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "execution_root_sha256": EXECUTION_ROOT_SHA256,
            "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        },
        label="V25 industrial-v3 multiroute-v2 actor-binding evaluation",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--execution-review-dir", type=Path, required=True)
    parser.add_argument("--preflight-dir", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--industrial-contract-dir", type=Path, required=True)
    parser.add_argument("--superseded-evaluation-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        evaluate(
            output=args.output,
            implementation_head=args.implementation_head,
            execution_dir=args.execution_dir,
            execution_review_dir=args.execution_review_dir,
            preflight_dir=args.preflight_dir,
            preflight_root=args.preflight_root,
            industrial_contract_dir=args.industrial_contract_dir,
            superseded_evaluation_dir=args.superseded_evaluation_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
