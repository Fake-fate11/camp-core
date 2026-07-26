"""Freeze the zero-outcome multiroute contract and pre-model manifest audit."""

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
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (  # noqa: E402
    validate_evaluation_contract_v3,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute import (  # noqa: E402
    AUTHORITY_SHA256,
    AUTODL_INTERPRETER,
    BASE_HEAD,
    EXACT_DIRS,
    FAMILY_RISK_QUOTAS,
    FAMILY_ROUTE_QUOTAS,
    FAMILY_SOURCE_QUOTAS,
    FAMILIES,
    RISK_TIERS,
    ROUTE_BINS,
    SOURCE_AVAILABILITY,
    UPSTREAM_ROOTS,
    ZERO_OVERLAP_AUTHORITIES,
    ZERO_OVERLAP_LEVELS,
    canonical_bytes,
    canonical_sha256,
    contract,
    route_geometry_bin,
    validate_candidate,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


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
FAIR_PREFLIGHT = Path(
    "/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_preflight_"
    "67308ac0_ed0d298c"
)
FAIR_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
B4_PREOPEN = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST"
)
B4_PREOPEN_ROOT = (
    "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
)
CORRECTED_PREFLIGHT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_batch8_generator_repeatability_corrected_preflight_v1_dc76fbc8"
)
CORRECTED_PREFLIGHT_ROOT = (
    "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac"
)
BOUNDED_PREFLIGHT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_bounded_closed_loop_preflight_a8b665a0_5e55899b"
)
BOUNDED_PREFLIGHT_ROOT = (
    "e6cb543de41042f70ba7ad2ff83eff25ea7beda5afd8387c4885932f2378ba71"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _interpreter_receipt() -> dict[str, Any]:
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "minimum_version_passed": sys.version_info >= (3, 10),
        "autodl_exact_interpreter_passed": sys.executable == AUTODL_INTERPRETER,
        "required_imports": {"numpy": True, "json": True, "hashlib": True},
    }


def _require_autodl_runtime() -> None:
    receipt = _interpreter_receipt()
    if (
        receipt["minimum_version_passed"] is not True
        or receipt["autodl_exact_interpreter_passed"] is not True
    ):
        raise RuntimeError("formal multiroute artifact requires exact AutoDL dp312")


def freeze_contract(
    output: Path,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
    industrial_contract_review_dir: Path,
    industrial_contract_review_root: str,
    industrial_capability_dir: Path,
    industrial_capability_root: str,
    industrial_capability_review_dir: Path,
    industrial_capability_review_root: str,
) -> str:
    _require_autodl_runtime()
    upstream = {
        "industrial_contract": (
            industrial_contract_dir,
            industrial_contract_root,
        ),
        "industrial_contract_review": (
            industrial_contract_review_dir,
            industrial_contract_review_root,
        ),
        "industrial_capability": (
            industrial_capability_dir,
            industrial_capability_root,
        ),
        "industrial_capability_review": (
            industrial_capability_review_dir,
            industrial_capability_review_root,
        ),
    }
    if output != Path(EXACT_DIRS["contract"]) or {
        key: root for key, (_path, root) in upstream.items()
    } != {
        key: UPSTREAM_ROOTS[key] for key in upstream
    }:
        raise ValueError("contract exact path or upstream root drifted")
    for key, (path, root) in upstream.items():
        verify_complete_seal(path, root, label=f"accepted {key}")
    industrial = object_from(industrial_contract_dir / "report.json")["contract"]
    validate_evaluation_contract_v3(industrial)
    payload = contract()
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_multiroute_contract_artifact_v1"
            ),
            "status": "sealed_outcome_independent_multiroute_contract",
            "authority_sha256": AUTHORITY_SHA256,
            "contract": payload,
            "industrial_upstream_bindings": {
                key: {
                    "path": str(path.resolve()),
                    "root_sha256": root,
                }
                for key, (path, root) in upstream.items()
            },
            "implementation_head": git_head(),
            "interpreter": _interpreter_receipt(),
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_writes": 0,
        },
        {
            "role": "industrial_v3_multiroute_contract",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "industrial_contract_root_sha256": industrial_contract_root,
        },
        label="V25 industrial-v3 multiroute contract",
    )


def _route_partition(plan: Mapping[str, Any]) -> dict[str, set[str]]:
    result = {}
    for split in ("train", "calibration", "fresh_b"):
        rows = plan.get(split)
        if not isinstance(rows, list):
            raise ValueError("formal route split inventory missing")
        result[split] = {
            str(row["route_identity_sha256"])
            for row in rows
        }
    if (
        any(result[left] & result[right] for left in result for right in result if left < right)
        or len(set().union(*result.values())) != 401
    ):
        raise ValueError("sealed 401-route split partition drifted")
    return result


def _signal_inventory_sha(source_row: Mapping[str, Any]) -> str:
    chain = source_row["source_chain"]
    semantic = chain["semantic_clone_payload"]
    return canonical_sha256(
        {
            "source_class": source_row["source_class"],
            "signal": semantic.get("signal"),
            "phase_authority_mode": source_row.get("phase_authority_mode"),
            "source_chain_sha256": chain["source_chain_sha256"],
        }
    )


def _candidate(source_row: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    chain = source_row["source_chain"]
    semantic = chain["semantic_clone_payload"]
    route_sha = str(source_row["route_identity_sha256"])
    geometry_sha = str(chain["route_geometry_sha256"])
    actor_sha = canonical_sha256(
        {
            "actors": semantic.get("actors", []),
            "spawn": semantic.get("spawn"),
            "goal": semantic.get("goal"),
        }
    )
    seed_sha = canonical_sha256(
        {
            "scenario_seed": source_row["seed"],
            "formal_case_sha256": source_row["formal_case_sha256"],
        }
    )
    latent_sha = canonical_sha256(
        {
            "authority_sha256": AUTHORITY_SHA256,
            "route_sha256": route_sha,
            "formal_case_sha256": source_row["formal_case_sha256"],
            "tick_schedule": list(range(64)),
            "policy": "row0_zero_rows1_7_unique_pcg64_float32",
        }
    )
    payload = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
        ),
        "canonical_route_lanelet_arc_sha256": route_sha,
        "route_geometry_sha256": geometry_sha,
        "semantic_family": source_row["family"],
        "risk_tier": source_row["tier"],
        "source_availability": source_row["source_class"],
        "certified_signal_stopline_inventory_sha256": _signal_inventory_sha(
            source_row
        ),
        "canonical_state_actor_geometry_sha256": actor_sha,
        "scenario_source_bytes_sha256": source_row["formal_case_sha256"],
        "scenario_seed_sha256": seed_sha,
        "latent_instance_sha256": latent_sha,
    }
    clone = canonical_sha256(payload)
    row = {
        "clone_payload": payload,
        "clone_key_sha256": clone,
        "route_bin": route_geometry_bin(semantic["route_polyline_local_m"]),
        "overlap_keys": {
            "route": route_sha,
            "state": canonical_sha256(
                {
                    "route": route_sha,
                    "actors": actor_sha,
                    "source": source_row["formal_case_sha256"],
                }
            ),
            "geometry": geometry_sha,
            "semantic": canonical_sha256(
                {
                    "family": source_row["family"],
                    "tier": source_row["tier"],
                    "signal_stopline": payload[
                        "certified_signal_stopline_inventory_sha256"
                    ],
                    "actor_geometry": actor_sha,
                }
            ),
            "source": source_row["formal_case_sha256"],
            "seed": seed_sha,
            "latent_instance": latent_sha,
            "composite": clone,
        },
        "source_binding": {
            "artifact_path": str(SOURCE_CENSUS),
            "artifact_root_sha256": SOURCE_CENSUS_ROOT,
            "inventory_entry_path": (
                "route_signal_source_receipts.json#/cases/" + str(ordinal)
            ),
            "inventory_entry_sha256": canonical_sha256(source_row),
        },
    }
    return validate_candidate(row)


def _quota_deficits() -> dict[str, Any]:
    return {
        "family_risk": [
            {
                "family": FAMILIES[family],
                "risk_tier": RISK_TIERS[risk],
                "required": FAMILY_RISK_QUOTAS[family][risk],
                "available_after_route_nonoverlap": 0,
                "deficit": FAMILY_RISK_QUOTAS[family][risk],
            }
            for family in range(7)
            for risk in range(3)
        ],
        "family_route": [
            {
                "family": FAMILIES[family],
                "route_bin": ROUTE_BINS[route],
                "required": FAMILY_ROUTE_QUOTAS[family][route],
                "available_after_route_nonoverlap": 0,
                "deficit": FAMILY_ROUTE_QUOTAS[family][route],
            }
            for family in range(7)
            for route in range(3)
        ],
        "family_source": [
            {
                "family": FAMILIES[family],
                "source_availability": SOURCE_AVAILABILITY[source],
                "required": FAMILY_SOURCE_QUOTAS[family][source],
                "available_after_route_nonoverlap": 0,
                "deficit": FAMILY_SOURCE_QUOTAS[family][source],
            }
            for family in range(7)
            for source in range(2)
        ],
    }


def freeze_manifest_failure(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
) -> str:
    _require_autodl_runtime()
    if output != Path(EXACT_DIRS["manifest"]):
        raise ValueError("manifest exact path drifted")
    for path, root, label in (
        (contract_dir, contract_root, "multiroute contract"),
        (contract_review_dir, contract_review_root, "multiroute contract review"),
        (FORMAL_SOURCE, FORMAL_SOURCE_ROOT, "formal source freeze"),
        (SOURCE_CENSUS, SOURCE_CENSUS_ROOT, "route signal source census"),
        (FAIR_PREFLIGHT, FAIR_PREFLIGHT_ROOT, "fair-pool preflight"),
        (B4_PREOPEN, B4_PREOPEN_ROOT, "Fresh B4 input inventory"),
        (CORRECTED_PREFLIGHT, CORRECTED_PREFLIGHT_ROOT, "corrected development preflight"),
        (BOUNDED_PREFLIGHT, BOUNDED_PREFLIGHT_ROOT, "bounded single-route preflight"),
    ):
        verify_complete_seal(path, root, label=label)
    plan = _json(FORMAL_SOURCE / "controlled_corpus_final_plan.json")
    census = _json(SOURCE_CENSUS / "route_signal_source_receipts.json")
    partitions = _route_partition(plan)
    source_rows = [
        row for row in census["cases"] if row.get("runner_eligible") is True
    ]
    if len(source_rows) != 1500:
        raise RuntimeError("sealed executable source-case denominator drifted")
    candidates = [_candidate(row, ordinal) for ordinal, row in enumerate(source_rows)]
    if len({row["clone_key_sha256"] for row in candidates}) != 1500:
        raise RuntimeError("source candidate clone keys are not unique")
    training_routes = partitions["train"]
    excluded = [
        row
        for row in candidates
        if row["overlap_keys"]["route"] in training_routes
    ]
    eligible = [
        row
        for row in candidates
        if row["overlap_keys"]["route"] not in training_routes
    ]
    if len(excluded) != 1500 or eligible:
        raise RuntimeError("expected sealed training-route overlap audit drifted")
    pre_counts = Counter(
        (
            row["clone_payload"]["semantic_family"],
            row["clone_payload"]["risk_tier"],
            row["route_bin"],
            row["clone_payload"]["source_availability"],
        )
        for row in candidates
    )
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_manifest_capacity_failure_v1"
        ),
        "status": "failed_before_model_insufficient_nonoverlap_route_inventory",
        "classification": "scientific_source_inventory_capacity_failure",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "sealed_source_inventory": {
            "formal_source_root_sha256": FORMAL_SOURCE_ROOT,
            "source_census_root_sha256": SOURCE_CENSUS_ROOT,
            "route_partition_counts": {
                split: len(routes) for split, routes in partitions.items()
            },
            "route_partition_union_count": len(set().union(*partitions.values())),
            "candidate_case_count": len(candidates),
            "candidate_clone_key_count": len(
                {row["clone_key_sha256"] for row in candidates}
            ),
            "candidate_cell_counts": [
                {"cell": list(cell), "count": count}
                for cell, count in sorted(pre_counts.items())
            ],
        },
        "route_nonoverlap_gate": {
            "forbidden_authority": "training",
            "candidate_count": 1500,
            "excluded_route_overlap_count": len(excluded),
            "eligible_after_route_nonoverlap_count": len(eligible),
            "excluded_route_overlap_key_sha256": canonical_sha256(
                sorted(row["overlap_keys"]["route"] for row in excluded)
            ),
            "selected_cluster_count": 0,
            "required_cluster_count": 100,
        },
        "missing_quota_taxonomy": _quota_deficits(),
        "downstream": {
            "manifest_passed": False,
            "hardening_started": False,
            "preflight_started": False,
            "model_calls": 0,
            "execution_started": False,
            "evaluation_started": False,
            "fresh_or_outcome_read": False,
            "old_artifact_or_cas_writes": 0,
        },
        "scientific_interpretation": (
            "The only sealed executable seven-family source-case inventory is "
            "route-bound to the accepted training partition. The authority "
            "requires route-level zero overlap, so no candidate remains. No "
            "new route or route arc is fabricated and no model call is allowed."
        ),
        "exact_dirs_remaining_absent": [
            EXACT_DIRS[key]
            for key in (
                "hardening_matrix",
                "hardening_review",
                "hardening_focused",
                "preflight",
                "preflight_review",
                "execution",
                "execution_review",
                "evaluation",
                "evaluation_review",
                "final_docs",
            )
        ],
        "interpreter": _interpreter_receipt(),
        "implementation_head": git_head(),
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_manifest_capacity_failure",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "contract_root_sha256": contract_root,
            "source_census_root_sha256": SOURCE_CENSUS_ROOT,
        },
        label="V25 industrial-v3 multiroute manifest capacity failure",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="stage", required=True)
    contract_parser = subparsers.add_parser("contract")
    contract_parser.add_argument("--output", type=Path, required=True)
    for name in (
        "industrial-contract-dir",
        "industrial-contract-review-dir",
        "industrial-capability-dir",
        "industrial-capability-review-dir",
    ):
        contract_parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "industrial-contract-root",
        "industrial-contract-review-root",
        "industrial-capability-root",
        "industrial-capability-review-root",
    ):
        contract_parser.add_argument("--" + name, required=True)
    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("--output", type=Path, required=True)
    for name in ("contract-dir", "contract-review-dir"):
        manifest_parser.add_argument("--" + name, type=Path, required=True)
    for name in ("contract-root", "contract-review-root"):
        manifest_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = freeze_contract(
            args.output,
            args.industrial_contract_dir,
            args.industrial_contract_root,
            args.industrial_contract_review_dir,
            args.industrial_contract_review_root,
            args.industrial_capability_dir,
            args.industrial_capability_root,
            args.industrial_capability_review_dir,
            args.industrial_capability_review_root,
        )
    else:
        root = freeze_manifest_failure(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.contract_review_dir,
            args.contract_review_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
