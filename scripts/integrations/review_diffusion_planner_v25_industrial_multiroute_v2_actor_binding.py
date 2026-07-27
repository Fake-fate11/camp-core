from __future__ import annotations

import argparse
import hashlib
import json
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
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v3 import (  # noqa: E402
    review_contract_v3_literal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_evaluation_actor_binding_review import (  # noqa: E402
    EXPECTED_AFFECTED_LEAF_SET_SHA,
    EXPECTED_ARMS,
    EXPECTED_AUTHORITY,
    EXPECTED_EXECUTION_REVIEW_ROOT,
    EXPECTED_EXECUTION_ROOT,
    EXPECTED_SUPERSEDED_EVALUATION_ROOT,
    expected_affected_leaf_ids,
    rebuild_actor_binding_literal,
    review_contract_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    object_from,
    write_atomic,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    _assert_semantic_equal,
    _literal_arm_metrics,
    _literal_geometry,
    _literal_lookup_leaf,
    _literal_oriented_delta,
    _literal_paired_summary,
)


EXPECTED_INDUSTRIAL_CONTRACT_ROOT = (
    "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
)
EXPECTED_INDUSTRIAL_CONTRACT_REVIEW_ROOT = (
    "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
)
EXPECTED_INDUSTRIAL_CAPABILITY_ROOT = (
    "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
)
EXPECTED_INDUSTRIAL_CAPABILITY_REVIEW_ROOT = (
    "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
)
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_REVIEWER_STDERR_SHA256 = (
    "b6f6b4b29f50c0020c9ef65116f69ede3aa3c6b5148043272019f3816c48f124"
)
EXPECTED_FIRST_REJECTION = (
    "cluster0/safety.collision_any/pool_matched_candidate0 reason type drifted"
)
EXPECTED_STDERR_REJECTION = (
    "ValueError: cluster=0/leaf=safety.collision_any/"
    "arm=pool_matched_candidate0/reason type drifted"
)
ARMS = EXPECTED_ARMS


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _expected_continuation(implementation_head: str) -> str:
    return _canonical_sha(
        {
            "authority_sha256": EXPECTED_AUTHORITY,
            "implementation_head": implementation_head,
            "fixed_dp_head": EXPECTED_FIXED_DP,
            "execution_root": EXPECTED_EXECUTION_ROOT,
            "execution_review_root": EXPECTED_EXECUTION_REVIEW_ROOT,
            "superseded_evaluation_root": EXPECTED_SUPERSEDED_EVALUATION_ROOT,
            "affected_leaf_set_sha256": EXPECTED_AFFECTED_LEAF_SET_SHA,
            "industrial_contract_root": EXPECTED_INDUSTRIAL_CONTRACT_ROOT,
            "industrial_contract_review_root": (
                EXPECTED_INDUSTRIAL_CONTRACT_REVIEW_ROOT
            ),
            "industrial_capability_root": EXPECTED_INDUSTRIAL_CAPABILITY_ROOT,
            "industrial_capability_review_root": (
                EXPECTED_INDUSTRIAL_CAPABILITY_REVIEW_ROOT
            ),
        }
    )


def _expected_dirs(implementation_head: str, continuation: str) -> dict[str, str]:
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_"
        "evaluation_actor_binding_replacement_"
        f"{implementation_head[:8]}_{continuation[:8]}_"
    )
    return {
        role: prefix + role
        for role in (
            "failure_closeout",
            "failure_closeout_review",
            "correction_contract",
            "correction_contract_review",
            "focused",
            "evaluation",
            "evaluation_review",
            "final_docs",
        )
    }


def _write_review(
    output: Path,
    report: Mapping[str, Any],
    *,
    source_root: str,
    role: str,
) -> str:
    return write_atomic(
        output,
        dict(report),
        {
            "role": role,
            "authority_sha256": EXPECTED_AUTHORITY,
            "source_root_sha256": source_root,
        },
        label="V25 actor-binding corrected evaluation review",
    )


def _regression_rows(report: Mapping[str, Any]) -> dict[tuple[int, str], Any]:
    rows = {}
    for cluster in report["cluster_vectors"]:
        cluster_index = int(cluster["cluster_index"])
        for row in cluster["scalar_leaf_vector"]:
            rows[(cluster_index, str(row["leaf_id"]))] = row
    return rows


def review_failure_closeout(
    *,
    output: Path,
    source_dir: Path,
    source_root: str,
    superseded_evaluation_dir: Path,
    reviewer_stderr: Path,
) -> str:
    source = _verify(source_dir, source_root, "failure closeout")
    old = _verify(
        superseded_evaluation_dir,
        EXPECTED_SUPERSEDED_EVALUATION_ROOT,
        "superseded evaluation",
    )
    stderr_sha = _sha_file(reviewer_stderr)
    stderr_text = reviewer_stderr.read_text(encoding="utf-8", errors="replace")
    implementation_head = str(source.get("implementation_head"))
    continuation = _expected_continuation(implementation_head)
    dirs = _expected_dirs(implementation_head, continuation)
    if (
        output.resolve() != Path(dirs["failure_closeout_review"])
        or source.get("status") != "attempt_stopped_engineering_recoverable"
        or source.get("classification")
        != (
            "full_denominator_evaluation_sealed_actor_binding_"
            "consumer_wiring_failure"
        )
        or source.get("continuation_sha256") != continuation
        or source.get("exact_dirs") != dirs
        or source.get("superseded_evaluation_root_sha256")
        != EXPECTED_SUPERSEDED_EVALUATION_ROOT
        or source.get("superseded_evaluation_schema_version")
        != old.get("schema_version")
        or source.get("accepted_scientific_result") is not False
        or source.get("review_artifact_formed") is not False
        or source.get("first_rejection") != EXPECTED_FIRST_REJECTION
        or source.get("reviewer_stderr_sha256")
        != EXPECTED_REVIEWER_STDERR_SHA256
        or stderr_sha != EXPECTED_REVIEWER_STDERR_SHA256
        or EXPECTED_STDERR_REJECTION not in stderr_text
        or source.get("execution_root_sha256") != EXPECTED_EXECUTION_ROOT
        or source.get("execution_review_root_sha256")
        != EXPECTED_EXECUTION_REVIEW_ROOT
        or source.get("frozen_denominator")
        != {"clusters": 100, "arms": 300, "ticks": 19_200}
        or source.get("execution_or_model_rerun") is not False
        or source.get("old_evaluation_overwritten_or_countersigned") is not False
        or source.get("effect_or_outcome_used_to_choose_fix") is not False
        or source.get("scientific_block") is not False
        or source.get("project_terminal") is not False
        or source.get("five_class_flow_policy") is not True
        or source.get("claim_authorized") is not False
    ):
        raise ValueError("independent failure closeout semantics drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_failure_closeout_review_v1"
        ),
        "status": "independent_failure_closeout_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "implementation_head": implementation_head,
        "continuation_sha256": continuation,
        "superseded_evaluation_root_sha256": (
            EXPECTED_SUPERSEDED_EVALUATION_ROOT
        ),
        "reviewer_stderr_sha256": stderr_sha,
        "first_rejection_rebuilt": EXPECTED_FIRST_REJECTION,
        "accepted_scientific_result": False,
        "execution_or_model_rerun": False,
        "producer_closeout_oracle_imported": False,
        "scientific_block": False,
        "five_class_flow_policy": True,
        "claim_authorized": False,
    }
    return _write_review(
        output,
        report,
        source_root=source_root,
        role="evaluation_actor_binding_failure_closeout_review",
    )


def review_correction_contract(
    *,
    output: Path,
    source_dir: Path,
    source_root: str,
    failure_closeout_dir: Path,
    failure_closeout_root: str,
    failure_closeout_review_dir: Path,
    failure_closeout_review_root: str,
) -> str:
    source = _verify(source_dir, source_root, "correction contract")
    _verify(failure_closeout_dir, failure_closeout_root, "failure closeout")
    _verify(
        failure_closeout_review_dir,
        failure_closeout_review_root,
        "failure closeout review",
    )
    contract = review_contract_literal(source["contract"])
    implementation_head = str(source.get("implementation_head"))
    continuation = _expected_continuation(implementation_head)
    dirs = _expected_dirs(implementation_head, continuation)
    if (
        output.resolve() != Path(dirs["correction_contract_review"])
        or source.get("status")
        != "outcome_independent_correction_contract_frozen"
        or source.get("authority_sha256") != EXPECTED_AUTHORITY
        or source.get("continuation_sha256") != continuation
        or source.get("exact_dirs") != dirs
        or source.get("failure_closeout_root_sha256") != failure_closeout_root
        or source.get("failure_closeout_review_root_sha256")
        != failure_closeout_review_root
        or source.get("industrial_roots")
        != {
            "contract": EXPECTED_INDUSTRIAL_CONTRACT_ROOT,
            "contract_review": EXPECTED_INDUSTRIAL_CONTRACT_REVIEW_ROOT,
            "capability": EXPECTED_INDUSTRIAL_CAPABILITY_ROOT,
            "capability_review": EXPECTED_INDUSTRIAL_CAPABILITY_REVIEW_ROOT,
        }
        or source.get("affected_leaf_set_sha256")
        != EXPECTED_AFFECTED_LEAF_SET_SHA
        or source.get("model_dp_latent_pool_selector_execution_calls") != 0
        or source.get("claim_authorized") is not False
        or source.get("five_class_flow_policy") is not True
        or contract.get("continuation_sha256") != continuation
        or contract.get("exact_dirs") != dirs
    ):
        raise ValueError("independent correction contract semantics drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_review_v1"
        ),
        "status": "independent_literal_correction_contract_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "implementation_head": implementation_head,
        "continuation_sha256": continuation,
        "affected_leaf_set_sha256": EXPECTED_AFFECTED_LEAF_SET_SHA,
        "affected_leaf_count": 43,
        "unaffected_leaf_count": 118,
        "failure_closeout_root_sha256": failure_closeout_root,
        "failure_closeout_review_root_sha256": failure_closeout_review_root,
        "producer_contract_actor_binding_oracle_imported": False,
        "model_dp_latent_pool_selector_execution_calls": 0,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }
    return _write_review(
        output,
        report,
        source_root=source_root,
        role="evaluation_actor_binding_correction_contract_review",
    )


def review_evaluation(
    *,
    output: Path,
    source_dir: Path,
    source_root: str,
    execution_dir: Path,
    preflight_dir: Path,
    preflight_root: str,
    industrial_contract_dir: Path,
    superseded_evaluation_dir: Path,
) -> str:
    source = _verify(source_dir, source_root, "actor-binding evaluation")
    execution = _verify(
        execution_dir, EXPECTED_EXECUTION_ROOT, "sealed execution"
    )
    _verify(preflight_dir, preflight_root, "sealed preflight")
    old = _verify(
        superseded_evaluation_dir,
        EXPECTED_SUPERSEDED_EVALUATION_ROOT,
        "superseded unreviewed evaluation",
    )
    industrial_artifact = _verify(
        industrial_contract_dir,
        EXPECTED_INDUSTRIAL_CONTRACT_ROOT,
        "accepted industrial v3 contract",
    )
    industrial = review_contract_v3_literal(industrial_artifact["contract"])
    leaves = industrial["scalar_leaf_registry"]
    affected = set(expected_affected_leaf_ids())
    all_ids = [str(row["leaf_id"]) for row in leaves]
    unaffected = set(all_ids) - affected
    if (
        len(leaves) != 161
        or len(unaffected) != 118
        or source.get("authority_sha256") != EXPECTED_AUTHORITY
        or source.get("execution_root_sha256") != EXPECTED_EXECUTION_ROOT
        or source.get("execution_review_root_sha256")
        != EXPECTED_EXECUTION_REVIEW_ROOT
        or source.get("superseded_evaluation_root_sha256")
        != EXPECTED_SUPERSEDED_EVALUATION_ROOT
        or source.get("superseded_evaluation_accepted_scientific_result")
        is not False
        or source.get("superseded_evaluation_used_as_corrected_result_input")
        is not False
        or source.get("affected_leaf_count") != 43
        or source.get("affected_leaf_set_sha256")
        != EXPECTED_AFFECTED_LEAF_SET_SHA
        or source.get("unaffected_leaf_count") != 118
        or source.get("collision_onset_proxy_changed") is not False
        or source.get("scalar_leaf_count") != 161
        or source.get("independent_cluster_count") != 100
        or source.get("model_dp_latent_pool_selector_execution_rerun_calls")
        != 0
        or source.get("weighted_total_present") is not False
        or source.get("legacy_safetycost_computed") is not False
        or source.get("claim_authorized") is not False
        or source.get("five_class_flow_policy") is not True
        or output.resolve() != Path(source["exact_dirs"]["evaluation_review"])
    ):
        raise ValueError("reviewer actor-binding evaluation authority drifted")
    source_vectors = source["cluster_vectors"]
    if len(source_vectors) != 100:
        raise ValueError("reviewer cluster denominator drifted")
    values_by_leaf = {
        leaf_id: {arm: [] for arm in ARMS} for leaf_id in all_ids
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
            raise ValueError("reviewer cluster binding drifted")
        cluster_dir = execution_dir / "clusters" / f"{cluster:03d}"
        verify_complete_seal(
            cluster_dir,
            cluster_summary["root_sha256"],
            label=f"reviewer sealed cluster {cluster}",
        )
        cluster_execution = object_from(cluster_dir / "report.json")
        config = object_from(
            preflight_dir / "prepared" / f"{cluster:03d}" / "config.json"
        )
        geometry = _literal_geometry(config)
        expected_by_arm = {}
        expected_bindings = {}
        for arm in cluster_execution["arms"]:
            arm_name = str(arm["arm"])
            expected_bindings[arm_name] = rebuild_actor_binding_literal(
                arm,
                execution_root_sha256=EXPECTED_EXECUTION_ROOT,
                cluster_root_sha256=cluster_summary["root_sha256"],
                cluster_index=cluster,
                expected_arm=arm_name,
            )
            expected_by_arm[arm_name] = _literal_arm_metrics(
                arm, config, geometry
            )
        _assert_semantic_equal(
            source_vector["sealed_actor_bindings"],
            expected_bindings,
            f"cluster={cluster}/sealed_actor_bindings",
        )
        rows = source_vector["scalar_leaf_vector"]
        if len(rows) != 161:
            raise ValueError("reviewer scalar leaf denominator drifted")
        for leaf, actual in zip(leaves, rows, strict=True):
            if (
                actual["leaf_id"] != leaf["leaf_id"]
                or set(actual["per_arm"]) != set(ARMS)
            ):
                raise ValueError("reviewer scalar leaf topology drifted")
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
        statuses = {row["status"] for arm in ARMS for row in per_arm[arm]}
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
    old_rows = _regression_rows(old)
    new_rows = _regression_rows(source)
    for cluster in range(100):
        for leaf_id in unaffected:
            _assert_semantic_equal(
                new_rows[(cluster, leaf_id)],
                old_rows[(cluster, leaf_id)],
                f"unaffected regression cluster={cluster}/leaf={leaf_id}",
            )
    old_aggregates = {
        str(row["leaf_id"]): row for row in old["scalar_leaf_aggregates"]
    }
    for row in expected_aggregates:
        if row["leaf_id"] in unaffected:
            _assert_semantic_equal(
                row,
                old_aggregates[row["leaf_id"]],
                f"unaffected aggregate={row['leaf_id']}",
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
        raise ValueError("reviewer availability counts drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "actor_binding_replacement_evaluation_review_v1"
        ),
        "status": "independent_literal_actor_binding_evaluation_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "execution_root_sha256": EXPECTED_EXECUTION_ROOT,
        "preflight_root_sha256": preflight_root,
        "industrial_contract_root_sha256": (
            EXPECTED_INDUSTRIAL_CONTRACT_ROOT
        ),
        "superseded_evaluation_root_sha256": (
            EXPECTED_SUPERSEDED_EVALUATION_ROOT
        ),
        "cluster_count": 100,
        "scalar_leaf_count": 161,
        "affected_leaf_count": 43,
        "unaffected_leaf_regression_count": 118,
        "availability_counts": expected_availability,
        "actor_tick_bindings_rebuilt": 100 * 3 * 64,
        "cluster_leaf_arm_values_rebuilt": 100 * 161 * 3,
        "paired_comparisons_rebuilt": 161 * 2,
        "producer_actor_binding_metric_decision_oracle_imported": False,
        "old_diagnostic_used_as_corrected_result_input": False,
        "ordinary_ci_is_familywise_claim_evidence": False,
        "holm_iut_ni_claim_performed": False,
        "weighted_total_present": False,
        "legacy_safetycost_computed": False,
        "model_dp_latent_pool_selector_execution_rerun_calls": 0,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }
    return _write_review(
        output,
        report,
        source_root=source_root,
        role="industrial_v3_multiroute_v2_actor_binding_evaluation_review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    closeout = sub.add_parser("failure-closeout")
    closeout.add_argument("--output", type=Path, required=True)
    closeout.add_argument("--source-dir", type=Path, required=True)
    closeout.add_argument("--source-root", required=True)
    closeout.add_argument(
        "--superseded-evaluation-dir", type=Path, required=True
    )
    closeout.add_argument("--reviewer-stderr", type=Path, required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    contract.add_argument("--source-dir", type=Path, required=True)
    contract.add_argument("--source-root", required=True)
    contract.add_argument("--failure-closeout-dir", type=Path, required=True)
    contract.add_argument("--failure-closeout-root", required=True)
    contract.add_argument(
        "--failure-closeout-review-dir", type=Path, required=True
    )
    contract.add_argument("--failure-closeout-review-root", required=True)
    evaluation = sub.add_parser("evaluation")
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--source-dir", type=Path, required=True)
    evaluation.add_argument("--source-root", required=True)
    evaluation.add_argument("--execution-dir", type=Path, required=True)
    evaluation.add_argument("--preflight-dir", type=Path, required=True)
    evaluation.add_argument("--preflight-root", required=True)
    evaluation.add_argument(
        "--industrial-contract-dir", type=Path, required=True
    )
    evaluation.add_argument(
        "--superseded-evaluation-dir", type=Path, required=True
    )
    args = parser.parse_args()
    if args.command == "failure-closeout":
        root = review_failure_closeout(
            output=args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            superseded_evaluation_dir=args.superseded_evaluation_dir,
            reviewer_stderr=args.reviewer_stderr,
        )
    elif args.command == "contract":
        root = review_correction_contract(
            output=args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            failure_closeout_dir=args.failure_closeout_dir,
            failure_closeout_root=args.failure_closeout_root,
            failure_closeout_review_dir=args.failure_closeout_review_dir,
            failure_closeout_review_root=args.failure_closeout_review_root,
        )
    else:
        root = review_evaluation(
            output=args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            execution_dir=args.execution_dir,
            preflight_dir=args.preflight_dir,
            preflight_root=args.preflight_root,
            industrial_contract_dir=args.industrial_contract_dir,
            superseded_evaluation_dir=args.superseded_evaluation_dir,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
