"""Independent artifact review for the V25 industrial multiroute stage."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "camp_core", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_review import (  # noqa: E402
    AUTHORITY_SHA256,
    FAMILIES,
    FG,
    FR,
    FS,
    RISKS,
    ROUTES,
    SOURCES,
    review_contract_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"
FORMAL_SOURCE = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
FORMAL_SOURCE_ROOT = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
SOURCE_CENSUS = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_a17_route_signal_source_census_c7b1cdba_20260720T124603CST"
)
SOURCE_CENSUS_ROOT = (
    "252862ea50a6f1be906403b136c170ef16dbb2246568821bcbba9283290b0dbb"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    ).hexdigest()


def _interpreter() -> dict[str, Any]:
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "minimum_version_passed": sys.version_info >= (3, 10),
        "autodl_exact_interpreter_passed": sys.executable == AUTODL_INTERPRETER,
    }


def _require_runtime() -> None:
    receipt = _interpreter()
    if (
        receipt["minimum_version_passed"] is not True
        or receipt["autodl_exact_interpreter_passed"] is not True
    ):
        raise RuntimeError("independent review requires exact AutoDL dp312")


def review_contract_artifact(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    _require_runtime()
    verify_complete_seal(contract_dir, contract_root, label="multiroute contract")
    verify_complete_seal(
        industrial_contract_dir,
        industrial_contract_root,
        label="accepted industrial-v3 contract",
    )
    source = object_from(contract_dir / "report.json")
    industrial = object_from(industrial_contract_dir / "report.json")["contract"]
    if output != Path(source["contract"]["exact_dirs"]["contract_review"]):
        raise ValueError("contract review exact path drifted")
    reviewed = review_contract_literal(
        source["contract"], accepted_industrial_contract=industrial
    )
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_contract_review_artifact_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_sha256": _canonical_sha(reviewed),
        "reviewer_imported_multiroute_producer": False,
        "reviewed_topology": {
            "clusters": 100,
            "arms": 300,
            "ticks": 19_200,
            "independent_n": 100,
            "families": list(FAMILIES),
            "risk_tiers": list(RISKS),
            "route_bins": list(ROUTES),
            "source_availability": list(SOURCES),
            "family_risk": [list(row) for row in FR],
            "family_route": [list(row) for row in FG],
            "family_source": [list(row) for row in FS],
            "industrial_leaf_count": 161,
        },
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "implementation_head": git_head(),
        "interpreter": _interpreter(),
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_contract_independent_review",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "contract_root_sha256": contract_root,
        },
        label="V25 industrial-v3 multiroute contract independent review",
    )


def _route_partition(plan: Mapping[str, Any]) -> dict[str, set[str]]:
    output = {}
    for split in ("train", "calibration", "fresh_b"):
        rows = plan.get(split)
        if not isinstance(rows, list):
            raise ValueError("review formal route split inventory missing")
        output[split] = {
            str(row["route_identity_sha256"])
            for row in rows
        }
    if (
        any(output[a] & output[b] for a in output for b in output if a < b)
        or len(set().union(*output.values())) != 401
    ):
        raise ValueError("review sealed 401-route partition drifted")
    return output


def _expected_deficits() -> dict[str, Any]:
    return {
        "family_risk": [
            {
                "family": FAMILIES[family],
                "risk_tier": RISKS[risk],
                "required": FR[family][risk],
                "available_after_route_nonoverlap": 0,
                "deficit": FR[family][risk],
            }
            for family in range(7)
            for risk in range(3)
        ],
        "family_route": [
            {
                "family": FAMILIES[family],
                "route_bin": ROUTES[route],
                "required": FG[family][route],
                "available_after_route_nonoverlap": 0,
                "deficit": FG[family][route],
            }
            for family in range(7)
            for route in range(3)
        ],
        "family_source": [
            {
                "family": FAMILIES[family],
                "source_availability": SOURCES[source],
                "required": FS[family][source],
                "available_after_route_nonoverlap": 0,
                "deficit": FS[family][source],
            }
            for family in range(7)
            for source in range(2)
        ],
    }


def review_manifest_failure(
    output: Path,
    manifest_dir: Path,
    manifest_root: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
) -> str:
    _require_runtime()
    for path, root, label in (
        (manifest_dir, manifest_root, "multiroute manifest failure"),
        (contract_dir, contract_root, "multiroute contract"),
        (contract_review_dir, contract_review_root, "multiroute contract review"),
        (FORMAL_SOURCE, FORMAL_SOURCE_ROOT, "formal source freeze"),
        (SOURCE_CENSUS, SOURCE_CENSUS_ROOT, "source census"),
    ):
        verify_complete_seal(path, root, label=label)
    report = object_from(manifest_dir / "report.json")
    contract_report = object_from(contract_dir / "report.json")
    if output != Path(contract_report["contract"]["exact_dirs"]["manifest_review"]):
        raise ValueError("manifest review exact path drifted")
    plan = _json(FORMAL_SOURCE / "controlled_corpus_final_plan.json")
    census = _json(SOURCE_CENSUS / "route_signal_source_receipts.json")
    partitions = _route_partition(plan)
    source_rows = [
        row for row in census["cases"] if row.get("runner_eligible") is True
    ]
    if len(source_rows) != 1500:
        raise RuntimeError("review source-case denominator drifted")
    training_routes = partitions["train"]
    route_overlap = [
        str(row["route_identity_sha256"])
        for row in source_rows
        if str(row["route_identity_sha256"]) in training_routes
    ]
    eligible_routes = [
        str(row["route_identity_sha256"])
        for row in source_rows
        if str(row["route_identity_sha256"]) not in training_routes
    ]
    if len(route_overlap) != 1500 or eligible_routes:
        raise RuntimeError("review route overlap reconstruction drifted")
    gate = report.get("route_nonoverlap_gate", {})
    if (
        report.get("status")
        != "failed_before_model_insufficient_nonoverlap_route_inventory"
        or report.get("classification")
        != "scientific_source_inventory_capacity_failure"
        or gate.get("candidate_count") != 1500
        or gate.get("excluded_route_overlap_count") != 1500
        or gate.get("eligible_after_route_nonoverlap_count") != 0
        or gate.get("selected_cluster_count") != 0
        or gate.get("required_cluster_count") != 100
        or report.get("missing_quota_taxonomy") != _expected_deficits()
    ):
        raise ValueError("review manifest capacity failure semantics drifted")
    downstream = report.get("downstream", {})
    if (
        downstream.get("manifest_passed") is not False
        or downstream.get("hardening_started") is not False
        or downstream.get("preflight_started") is not False
        or downstream.get("model_calls") != 0
        or downstream.get("execution_started") is not False
        or downstream.get("evaluation_started") is not False
        or downstream.get("fresh_or_outcome_read") is not False
        or downstream.get("old_artifact_or_cas_writes") != 0
    ):
        raise ValueError("review downstream stop boundary drifted")
    result = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_manifest_failure_review_v1"
        ),
        "status": "passed_independent_manifest_capacity_failure_review",
        "authority_sha256": AUTHORITY_SHA256,
        "manifest_root_sha256": manifest_root,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "sealed_route_partition_counts": {
            split: len(routes) for split, routes in partitions.items()
        },
        "sealed_route_partition_union_count": 401,
        "source_case_count": 1500,
        "training_route_overlap_count": 1500,
        "eligible_after_route_nonoverlap_count": 0,
        "required_cluster_count": 100,
        "missing_quota_taxonomy_sha256": _canonical_sha(_expected_deficits()),
        "reviewer_imported_manifest_producer": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "implementation_head": git_head(),
        "interpreter": _interpreter(),
    }
    return write_atomic(
        output,
        result,
        {
            "role": "industrial_v3_multiroute_manifest_failure_independent_review",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "manifest_root_sha256": manifest_root,
            "contract_root_sha256": contract_root,
        },
        label="V25 industrial-v3 multiroute manifest failure independent review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="stage", required=True)
    contract_parser = subparsers.add_parser("contract")
    for name in ("contract-dir", "industrial-contract-dir"):
        contract_parser.add_argument("--" + name, type=Path, required=True)
    for name in ("contract-root", "industrial-contract-root"):
        contract_parser.add_argument("--" + name, required=True)
    contract_parser.add_argument("--output", type=Path, required=True)
    manifest_parser = subparsers.add_parser("manifest")
    for name in (
        "manifest-dir",
        "contract-dir",
        "contract-review-dir",
    ):
        manifest_parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "manifest-root",
        "contract-root",
        "contract-review-root",
    ):
        manifest_parser.add_argument("--" + name, required=True)
    manifest_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = review_contract_artifact(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.industrial_contract_dir,
            args.industrial_contract_root,
        )
    else:
        root = review_manifest_failure(
            args.output,
            args.manifest_dir,
            args.manifest_root,
            args.contract_dir,
            args.contract_root,
            args.contract_review_dir,
            args.contract_review_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
