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
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_replacement import (  # noqa: E402
    ARMS,
    AUTHORITY_SHA256,
    CLUSTER_COUNT,
    INDUSTRIAL_CONTRACT_ROOT_SHA256,
    canonical_sha256,
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
    better = int(np.count_nonzero(array > 0.0))
    tie = int(np.count_nonzero(array == 0.0))
    worse = int(np.count_nonzero(array < 0.0))
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
            "better": better,
            "tie": tie,
            "worse": worse,
            "sum": better + tie + worse,
            "tie_rule": "exact_zero_float64_oriented_delta",
        },
    }


def evaluate(
    *,
    output: Path,
    execution_dir: Path,
    execution_root: str,
    execution_review_dir: Path,
    execution_review_root: str,
    preflight_dir: Path,
    preflight_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    output = output.resolve()
    execution = _verify(execution_dir, execution_root, "multiroute-v2 execution")
    if output != Path(execution["exact_dirs"]["evaluation"]):
        raise ValueError("multiroute-v2 replacement evaluation exact dir drifted")
    _verify(
        execution_review_dir,
        execution_review_root,
        "multiroute-v2 execution review",
    )
    _verify(preflight_dir, preflight_root, "multiroute-v2 preflight")
    industrial = _verify(
        industrial_contract_dir,
        industrial_contract_root,
        "accepted industrial v3 contract",
    )["contract"]
    if (
        industrial_contract_root != INDUSTRIAL_CONTRACT_ROOT_SHA256
        or execution.get("authority_sha256") != AUTHORITY_SHA256
        or execution.get("start_from_zero") is not True
        or execution.get("old_partial_reuse") is not False
        or execution.get("status")
        != "complete_full_denominator_hard_integrity_passed"
        or execution.get("terminal_accounting", {}).get("unattempted") != 0
        or len(execution.get("cluster_artifacts", [])) != CLUSTER_COUNT
    ):
        raise ValueError("multiroute-v2 evaluation input gate drifted")
    leaves = industrial["scalar_leaf_registry"]
    if len(leaves) != 161:
        raise ValueError("industrial v3 scalar leaf topology drifted")
    cluster_vectors = []
    values_by_leaf: dict[str, dict[str, list[dict[str, Any]]]] = {
        leaf["leaf_id"]: {arm: [] for arm in ARMS} for leaf in leaves
    }
    for cluster_summary in execution["cluster_artifacts"]:
        cluster = int(cluster_summary["cluster_index"])
        cluster_dir = execution_dir / "clusters" / f"{cluster:03d}"
        verify_complete_seal(
            cluster_dir,
            cluster_summary["root_sha256"],
            label=f"multiroute-v2 cluster {cluster}",
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
        for arm in cluster_execution["arms"]:
            summary, latency = _arm_metrics(arm, config, geometry)
            arm_summaries[arm["arm"]] = summary
            arm_latencies[arm["arm"]] = latency
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
            vector.append(
                {
                    "leaf_id": leaf["leaf_id"],
                    "per_arm": per_arm,
                }
            )
        cluster_vectors.append(
            {
                "cluster_index": cluster,
                "clone_key_sha256": cluster_summary["clone_key_sha256"],
                "source_cluster_root_sha256": cluster_summary["root_sha256"],
                "scalar_leaf_vector": vector,
            }
        )
    aggregate_leaves = []
    for leaf in leaves:
        leaf_id = leaf["leaf_id"]
        per_arm = values_by_leaf[leaf_id]
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
        statuses = {
            row["status"] for arm in ARMS for row in per_arm[arm]
        }
        if statuses == {"computed_descriptive"}:
            status = "computed_exploratory_multiroute"
        elif statuses == {"scientifically_inapplicable"}:
            status = "scientifically_inapplicable"
        else:
            status = "evidence_missing_or_mixed_applicability"
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
            "replacement_evaluation_v1"
        ),
        "status": "sealed_exploratory_multiroute_industrial_v3_vector",
        "authority_sha256": AUTHORITY_SHA256,
        "execution_root_sha256": execution_root,
        "execution_review_root_sha256": execution_review_root,
        "preflight_root_sha256": preflight_root,
        "industrial_contract_root_sha256": industrial_contract_root,
        "replacement_continuation_sha256": execution[
            "replacement_continuation_sha256"
        ],
        "exact_dirs": dict(execution["exact_dirs"]),
        "start_from_zero": True,
        "old_partial_reuse": False,
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
        "legacy_safetycost_computed": False,
        "weighted_total_present": False,
        "fresh_or_b4_outcome_values_read": False,
        "claim_authorized": False,
    }
    report["cluster_vector_sha256"] = canonical_sha256(cluster_vectors)
    report["aggregate_vector_sha256"] = canonical_sha256(aggregate_leaves)
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_v2_evaluation",
            "authority_sha256": AUTHORITY_SHA256,
            "execution_root_sha256": execution_root,
            "industrial_contract_root_sha256": industrial_contract_root,
        },
        label="V25 industrial-v3 multiroute-v2 evaluation",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--execution-review-dir", type=Path, required=True)
    parser.add_argument("--execution-review-root", required=True)
    parser.add_argument("--preflight-dir", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--industrial-contract-dir", type=Path, required=True)
    parser.add_argument("--industrial-contract-root", required=True)
    args = parser.parse_args()
    root = evaluate(
        output=args.output,
        execution_dir=args.execution_dir,
        execution_root=args.execution_root,
        execution_review_dir=args.execution_review_dir,
        execution_review_root=args.execution_review_root,
        preflight_dir=args.preflight_dir,
        preflight_root=args.preflight_root,
        industrial_contract_dir=args.industrial_contract_dir,
        industrial_contract_root=args.industrial_contract_root,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
