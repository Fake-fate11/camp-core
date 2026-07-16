#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import shutil
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.review_diffusion_planner_v24_native_corpus_pilot import (
    FEATURE_FIELDS,
    FIXED_DP_HEAD,
    IDENTITY_FIELDS,
    MINIMUM_FREE_BYTES,
    REMAINING_TRAIN_SEEDS,
    TRAIN_SEEDS,
    _authoritative_boundary_checks,
    _check,
    _eight_booleans,
    _file_sha256,
    _finite_atom_matrix,
    _is_sha256,
    _read_json,
    _seal,
    _verify_seal,
    _write_json,
)


PHASE = "main_completion_remaining_frozen_seeds"
RECEIPT_SCHEMA = "camp_dp_v24_native_corpus_remaining_run_receipt_v1"
SUMMARY_SCHEMA = "camp_dp_v24_native_corpus_remaining_summary_v1"
PROGRESS_SCHEMA = "camp_dp_v24_native_corpus_remaining_progress_v1"
SOURCE_INVALID_REASON = "ValueError: route slot 0 requires a positive speed limit"


def _parse_heads_strict(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or "=" not in line:
            raise ValueError("malformed HEADS field")
        name, value = line.split("=", 1)
        if not name or not value or name in result:
            raise ValueError("duplicate or empty HEADS field")
        result[name] = value
    return result


def _is_git_head(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def _checks_integrity(
    payload: Mapping[str, Any], *, require_failed_checks: bool
) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return False
    names = [check.get("name") for check in checks if isinstance(check, Mapping)]
    return (
        bool(checks)
        and len(names) == len(checks)
        and all(isinstance(name, str) and name for name in names)
        and len(set(names)) == len(names)
        and all(check.get("passed") is True for check in checks)
        and _exact_int(payload.get("check_count"), len(checks))
        and _exact_int(payload.get("failed_count"), 0)
        and (not require_failed_checks or payload.get("failed_checks") == [])
    )


def _review_boundaries_closed(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("review_only") is True
        and payload.get("model_loaded") is False
        and payload.get("candidate_generation_started") is False
        and payload.get("training_executed") is False
        and payload.get("tuning_executed") is False
        and payload.get("outcome_accessed") is False
        and payload.get("calibration_accessed") is False
        and payload.get("holdout_opened") is False
        and payload.get("claim_authorized") is False
    )


def _static_boundaries_closed(
    payload: Mapping[str, Any], *, tuning_field_required: bool = True
) -> bool:
    return (
        payload.get("model_loaded") is False
        and payload.get("simulator_executed") is False
        and payload.get("candidate_generation_started") is False
        and payload.get("training_executed") is False
        and (
            payload.get("tuning_executed") is False
            if tuning_field_required
            else "tuning_executed" not in payload
            or payload.get("tuning_executed") is False
        )
        and payload.get("outcome_fields_consumed") == []
        and payload.get("calibration_accessed") is False
        and payload.get("holdout_opened") is False
        and payload.get("claim_authorized") is False
    )


def _row_order_sha256(routes: Sequence[Mapping[str, Any]], seeds: Sequence[int]) -> str:
    rows = [
        {"record_key": str(route["record_key"]), "seed": int(seed)}
        for route in routes
        for seed in seeds
    ]
    encoded = (
        json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def review_remaining(
    remaining_root: Path,
    expected_root_sha256: str,
    corpus_preflight_root: Path,
    expected_corpus_preflight_root_sha256: str,
    corpus_review_root: Path,
    expected_corpus_review_root_sha256: str,
    pilot_root: Path,
    expected_pilot_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    remaining_preflight_root: Path,
    expected_remaining_preflight_root_sha256: str,
    remaining_preflight_review_root: Path,
    expected_remaining_preflight_review_root_sha256: str,
    expected_source_camp_head: str,
    expected_route_count: int = 375,
) -> dict[str, Any]:
    """Independently review the sealed v24 remaining-seed corpus artifact."""
    roots = {
        "remaining_execution": (remaining_root, expected_root_sha256),
        "corpus_preflight": (
            corpus_preflight_root,
            expected_corpus_preflight_root_sha256,
        ),
        "corpus_review": (corpus_review_root, expected_corpus_review_root_sha256),
        "pilot": (pilot_root, expected_pilot_root_sha256),
        "pilot_review": (pilot_review_root, expected_pilot_review_root_sha256),
        "remaining_preflight": (
            remaining_preflight_root,
            expected_remaining_preflight_root_sha256,
        ),
        "remaining_preflight_review": (
            remaining_preflight_review_root,
            expected_remaining_preflight_review_root_sha256,
        ),
    }
    checks: list[dict[str, Any]] = []
    for prefix, (root, digest) in roots.items():
        checks.extend(_verify_seal(Path(root), digest, prefix))
    recomputed: dict[str, Any] = {}

    try:
        remaining_root = Path(remaining_root).resolve()
        manifest = _read_json(Path(corpus_preflight_root) / "corpus_manifest.json")
        routes = sorted(
            manifest.get("routes", []), key=lambda row: str(row.get("record_key"))
        )
        route_by_identity = {
            str(route["identity_sha256"]): route
            for route in routes
            if isinstance(route, Mapping) and "identity_sha256" in route
        }
        _check(
            checks,
            "manifest_schema",
            manifest.get("schema") == "camp_dp_v24_native_corpus_manifest_v1",
        )
        _check(checks, "manifest_train_only", manifest.get("split") == "train")
        _check(checks, "manifest_seeds", manifest.get("seeds") == TRAIN_SEEDS)
        _check(
            checks,
            "manifest_outcomes_closed",
            manifest.get("outcome_fields_consumed") == [],
        )
        _check(
            checks,
            "manifest_calibration_closed",
            manifest.get("calibration_accessed") is False,
        )
        _check(
            checks, "manifest_holdout_closed", manifest.get("holdout_opened") is False
        )
        _check(
            checks,
            "manifest_denominator",
            manifest.get("route_count") == expected_route_count
            and len(routes) == expected_route_count
            and len(route_by_identity) == expected_route_count,
        )

        route_order = [str(route["record_key"]) for route in routes]
        planned = expected_route_count * len(REMAINING_TRAIN_SEEDS)
        row_order_sha256 = _row_order_sha256(routes, REMAINING_TRAIN_SEEDS)
        corpus_review = _read_json(Path(corpus_review_root) / "review.json")
        pilot_execution = _read_json(Path(pilot_root) / "execution.json")
        pilot_review = _read_json(Path(pilot_review_root) / "review.json")
        remaining_preflight = _read_json(
            Path(remaining_preflight_root) / "preflight.json"
        )
        remaining_preflight_review = _read_json(
            Path(remaining_preflight_review_root) / "review.json"
        )

        _check(
            checks,
            "corpus_review_authoritative",
            corpus_review.get("schema")
            == "camp_dp_v24_native_corpus_static_preflight_review_v1"
            and corpus_review.get("status") == "passed"
            and _exact_int(corpus_review.get("failed_count"), 0)
            and corpus_review.get("source_preflight_root_sha256")
            == expected_corpus_preflight_root_sha256
            and _exact_int(corpus_review.get("route_count"), expected_route_count)
            and _exact_int(
                corpus_review.get("route_seed_run_count"),
                expected_route_count * len(TRAIN_SEEDS),
            )
            and corpus_review.get("fixed_dp_head") == FIXED_DP_HEAD
            and corpus_review.get("preflight_reexecuted") is False
            and corpus_review.get("next_work_target")
            == "v24_native_corpus_capability_pilot_all_train_routes_seed_24001_only"
            and _static_boundaries_closed(corpus_review, tuning_field_required=False),
        )
        _check(
            checks,
            "corpus_review_checks_integrity",
            _checks_integrity(corpus_review, require_failed_checks=True),
        )
        try:
            corpus_review_heads = _parse_heads_strict(
                Path(corpus_review_root) / "HEADS"
            )
        except ValueError:
            corpus_review_heads = {}
        _check(
            checks,
            "corpus_review_heads_source_chain",
            set(corpus_review_heads)
            == {
                "CAMP_HEAD",
                "FIXED_DP_HEAD",
                "SOURCE_PREFLIGHT_ROOT_SHA256",
            }
            and _is_git_head(corpus_review_heads.get("CAMP_HEAD"))
            and corpus_review_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and corpus_review_heads.get("SOURCE_PREFLIGHT_ROOT_SHA256")
            == expected_corpus_preflight_root_sha256,
        )

        pilot_failed = pilot_execution.get("failed_route_seed_runs")
        pilot_complete = pilot_execution.get("complete_route_seed_runs")
        pilot_terminal = (
            "complete_with_retained_failures"
            if type(pilot_failed) is int and pilot_failed > 0
            else "complete"
        )
        _check(
            checks,
            "pilot_execution_authoritative",
            pilot_execution.get("schema")
            == "camp_dp_v24_native_corpus_pilot_summary_v1"
            and pilot_execution.get("status") == pilot_terminal
            and _exact_int(pilot_execution.get("seed"), TRAIN_SEEDS[0])
            and _exact_int(
                pilot_execution.get("planned_route_seed_runs"), expected_route_count
            )
            and _exact_int(
                pilot_execution.get("retained_route_seed_runs"), expected_route_count
            )
            and type(pilot_complete) is int
            and type(pilot_failed) is int
            and pilot_complete + pilot_failed == expected_route_count
            and _exact_int(pilot_execution.get("pending_route_seed_runs"), 0)
            and pilot_execution.get("route_coverage") == 1.0
            and pilot_execution.get("all_routes_retained_in_denominator") is True
            and pilot_execution.get("source_preflight_root_sha256")
            == expected_corpus_preflight_root_sha256
            and pilot_execution.get("source_review_root_sha256")
            == expected_corpus_review_root_sha256
            and pilot_execution.get("fixed_dp_head") == FIXED_DP_HEAD
            and pilot_execution.get("tuning_executed") is False
            and pilot_execution.get("calibration_accessed") is False
            and pilot_execution.get("holdout_opened") is False
            and pilot_execution.get("outcome_fields_consumed") == []
            and pilot_execution.get("claim_authorized") is False
            and pilot_execution.get("next_work_target")
            == "v24_native_corpus_capability_pilot_independent_review_only",
        )
        pilot_heads = _parse_heads_strict(Path(pilot_root) / "HEADS")
        _check(
            checks,
            "pilot_heads_source_chain",
            set(pilot_heads)
            == {
                "CAMP_HEAD",
                "FIXED_DP_HEAD",
                "SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256",
                "SOURCE_CORPUS_REVIEW_ROOT_SHA256",
            }
            and _is_git_head(pilot_heads.get("CAMP_HEAD"))
            and pilot_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and pilot_heads.get("SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256")
            == expected_corpus_preflight_root_sha256
            and pilot_heads.get("SOURCE_CORPUS_REVIEW_ROOT_SHA256")
            == expected_corpus_review_root_sha256,
        )

        pilot_decision = pilot_review.get("decision")
        _check(
            checks,
            "pilot_review_authoritative",
            pilot_review.get("schema")
            == "camp_dp_v24_native_corpus_pilot_independent_review_v1"
            and pilot_review.get("status") in {"passed", "passed_with_warning"}
            and _exact_int(pilot_review.get("failed_count"), 0)
            and pilot_review.get("source_pilot_root_sha256")
            == expected_pilot_root_sha256
            and pilot_review.get("source_corpus_preflight_root_sha256")
            == expected_corpus_preflight_root_sha256
            and _review_boundaries_closed(pilot_review),
        )
        _check(
            checks,
            "pilot_review_checks_integrity",
            _checks_integrity(pilot_review, require_failed_checks=True),
        )
        _check(
            checks,
            "pilot_review_decision",
            isinstance(pilot_decision, Mapping)
            and pilot_decision.get("authorized") is True
            and pilot_decision.get("action") == "execute_frozen_remaining_train_seeds"
            and pilot_decision.get("route_count") == expected_route_count
            and pilot_decision.get("route_order") == route_order
            and pilot_decision.get("seeds") == REMAINING_TRAIN_SEEDS
            and pilot_decision.get("preserve_all_failures_and_denominator") is True
            and pilot_decision.get("route_removal_replacement_reordering_authorized")
            is False
            and pilot_decision.get("tuning_authorized") is False
            and pilot_decision.get("outcome_access_authorized") is False
            and pilot_decision.get("calibration_access_authorized") is False
            and pilot_decision.get("holdout_access_authorized") is False
            and pilot_decision.get("claim_authorized") is False,
        )
        pilot_recomputed = pilot_review.get("recomputed", {})
        _check(
            checks,
            "pilot_review_execution_aggregate",
            isinstance(pilot_recomputed, Mapping)
            and all(
                pilot_recomputed.get(name) == pilot_execution.get(name)
                for name in (
                    "planned_route_seed_runs",
                    "retained_route_seed_runs",
                    "complete_route_seed_runs",
                    "failed_route_seed_runs",
                    "pending_route_seed_runs",
                    "route_coverage",
                )
            ),
        )
        pilot_review_heads = _parse_heads_strict(Path(pilot_review_root) / "HEADS")
        _check(
            checks,
            "pilot_review_heads_source_chain",
            set(pilot_review_heads)
            == {
                "CAMP_HEAD",
                "FIXED_DP_HEAD",
                "SOURCE_PILOT_ROOT_SHA256",
                "SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256",
            }
            and _is_git_head(pilot_review_heads.get("CAMP_HEAD"))
            and pilot_review_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and pilot_review_heads.get("SOURCE_PILOT_ROOT_SHA256")
            == expected_pilot_root_sha256
            and pilot_review_heads.get("SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256")
            == expected_corpus_preflight_root_sha256,
        )

        failure_counts = (
            pilot_recomputed.get("failure_reason_counts", {})
            if isinstance(pilot_recomputed, Mapping)
            else {}
        )
        source_invalid_count = (
            failure_counts.get(SOURCE_INVALID_REASON)
            if isinstance(failure_counts, Mapping)
            else None
        )
        remaining_preflight_heads = _parse_heads_strict(
            Path(remaining_preflight_root) / "HEADS"
        )
        _check(
            checks,
            "remaining_preflight_heads_source_chain",
            set(remaining_preflight_heads)
            == {
                "CAMP_HEAD",
                "FIXED_DP_HEAD",
                "SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256",
                "SOURCE_CORPUS_REVIEW_ROOT_SHA256",
                "SOURCE_PILOT_ROOT_SHA256",
                "SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256",
            }
            and _is_git_head(remaining_preflight_heads.get("CAMP_HEAD"))
            and remaining_preflight_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and remaining_preflight_heads.get("SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256")
            == expected_corpus_preflight_root_sha256
            and remaining_preflight_heads.get("SOURCE_CORPUS_REVIEW_ROOT_SHA256")
            == expected_corpus_review_root_sha256
            and remaining_preflight_heads.get("SOURCE_PILOT_ROOT_SHA256")
            == expected_pilot_root_sha256
            and remaining_preflight_heads.get(
                "SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256"
            )
            == expected_pilot_review_root_sha256,
        )
        _check(
            checks,
            "remaining_preflight_authoritative",
            remaining_preflight.get("schema")
            == "camp_dp_v24_native_corpus_remaining_execution_preflight_v1"
            and remaining_preflight.get("status") == "passed"
            and _exact_int(remaining_preflight.get("failed_count"), 0)
            and _exact_int(remaining_preflight.get("route_count"), expected_route_count)
            and remaining_preflight.get("seeds") == REMAINING_TRAIN_SEEDS
            and _exact_int(remaining_preflight.get("route_seed_run_count"), planned)
            and remaining_preflight.get("row_order_sha256") == row_order_sha256
            and _exact_int(
                remaining_preflight.get("theoretical_max_snapshots"), planned * 64
            )
            and _exact_int(
                remaining_preflight.get("pilot_route_denominator_retained"),
                expected_route_count,
            )
            and remaining_preflight.get("pilot_failures_retained") is True
            and remaining_preflight.get("next_work_target")
            == (
                "v24_native_corpus_remaining_train_seeds_static_preflight_"
                "independent_review_only"
            )
            and _static_boundaries_closed(remaining_preflight),
        )
        _check(
            checks,
            "remaining_preflight_checks_integrity",
            _checks_integrity(remaining_preflight, require_failed_checks=False),
        )
        preflight_checks = {
            check.get("name"): check.get("passed")
            for check in remaining_preflight.get("checks", [])
            if isinstance(check, Mapping)
        }
        _check(
            checks,
            "remaining_preflight_required_checks",
            all(
                preflight_checks.get(name) is True
                for name in (
                    "remaining_task_lock_available",
                    f"remaining_route_seed_runs_{planned}",
                    f"remaining_configs_{planned}",
                    f"all_unique_route_assets_{expected_route_count}_unchanged",
                    "disk_floor",
                )
            ),
        )

        remaining_decision = remaining_preflight_review.get("decision")
        _check(
            checks,
            "remaining_preflight_review_authoritative",
            remaining_preflight_review.get("schema")
            == "camp_dp_v24_native_corpus_remaining_preflight_independent_review_v1"
            and remaining_preflight_review.get("status") == "passed"
            and _exact_int(remaining_preflight_review.get("failed_count"), 0)
            and remaining_preflight_review.get("source_preflight_root_sha256")
            == expected_remaining_preflight_root_sha256
            and remaining_preflight_review.get("source_corpus_root_sha256")
            == expected_corpus_preflight_root_sha256
            and remaining_preflight_review.get("source_corpus_review_root_sha256")
            == expected_corpus_review_root_sha256
            and remaining_preflight_review.get("source_pilot_root_sha256")
            == expected_pilot_root_sha256
            and remaining_preflight_review.get("source_pilot_review_root_sha256")
            == expected_pilot_review_root_sha256
            and remaining_preflight_review.get("source_camp_head")
            == remaining_preflight_heads.get("CAMP_HEAD")
            and remaining_preflight_review.get("fixed_dp_head") == FIXED_DP_HEAD
            and _exact_int(
                remaining_preflight_review.get("route_count"), expected_route_count
            )
            and remaining_preflight_review.get("seeds") == REMAINING_TRAIN_SEEDS
            and _exact_int(
                remaining_preflight_review.get("route_seed_run_count"), planned
            )
            and remaining_preflight_review.get("row_order_sha256") == row_order_sha256
            and type(source_invalid_count) is int
            and _exact_int(
                remaining_preflight_review.get("source_invalid_route_count"),
                source_invalid_count,
            )
            and _exact_int(
                remaining_preflight_review.get("validated_run_config_count"), planned
            )
            and remaining_preflight_review.get("preflight_reexecuted") is False
            and remaining_preflight_review.get(
                "execution_preflight_builder_imported_or_called"
            )
            is False
            and remaining_preflight_review.get("next_work_target")
            == "v24_native_corpus_remaining_train_seeds_unique_execution_only"
            and _static_boundaries_closed(remaining_preflight_review),
        )
        _check(
            checks,
            "remaining_preflight_review_checks_integrity",
            _checks_integrity(remaining_preflight_review, require_failed_checks=True),
        )
        _check(
            checks,
            "remaining_preflight_review_decision",
            isinstance(remaining_decision, Mapping)
            and remaining_decision.get("remaining_execution_authorized") is True
            and remaining_decision.get("action")
            == "launch_one_unique_remaining_train_seed_execution"
            and remaining_decision.get("route_count") == expected_route_count
            and remaining_decision.get("seeds") == REMAINING_TRAIN_SEEDS
            and remaining_decision.get("preserve_all_failures_and_denominator") is True
            and remaining_decision.get(
                "route_removal_replacement_reordering_authorized"
            )
            is False
            and remaining_decision.get("tuning_authorized") is False
            and remaining_decision.get("outcome_access_authorized") is False
            and remaining_decision.get("calibration_access_authorized") is False
            and remaining_decision.get("holdout_access_authorized") is False
            and remaining_decision.get("claim_authorized") is False,
        )
        remaining_review_heads = _parse_heads_strict(
            Path(remaining_preflight_review_root) / "HEADS"
        )
        _check(
            checks,
            "remaining_preflight_review_heads_source_chain",
            set(remaining_review_heads)
            == {
                "CAMP_HEAD",
                "FIXED_DP_HEAD",
                "SOURCE_CAMP_HEAD",
                "SOURCE_PREFLIGHT_ROOT_SHA256",
                "SOURCE_CORPUS_ROOT_SHA256",
                "SOURCE_CORPUS_REVIEW_ROOT_SHA256",
                "SOURCE_PILOT_ROOT_SHA256",
                "SOURCE_PILOT_REVIEW_ROOT_SHA256",
            }
            and _is_git_head(remaining_review_heads.get("CAMP_HEAD"))
            and remaining_review_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and remaining_review_heads.get("SOURCE_CAMP_HEAD")
            == remaining_preflight_heads.get("CAMP_HEAD")
            and remaining_review_heads.get("SOURCE_PREFLIGHT_ROOT_SHA256")
            == expected_remaining_preflight_root_sha256
            and remaining_review_heads.get("SOURCE_CORPUS_ROOT_SHA256")
            == expected_corpus_preflight_root_sha256
            and remaining_review_heads.get("SOURCE_CORPUS_REVIEW_ROOT_SHA256")
            == expected_corpus_review_root_sha256
            and remaining_review_heads.get("SOURCE_PILOT_ROOT_SHA256")
            == expected_pilot_root_sha256
            and remaining_review_heads.get("SOURCE_PILOT_REVIEW_ROOT_SHA256")
            == expected_pilot_review_root_sha256,
        )

        expected_pairs = [
            (str(route["identity_sha256"]), seed)
            for route in routes
            for seed in REMAINING_TRAIN_SEEDS
        ]
        expected_receipts = {
            f"receipts/train/{identity}/seed_{seed}.json"
            for identity, seed in expected_pairs
        }
        actual_receipts = {
            path.relative_to(remaining_root).as_posix()
            for path in (remaining_root / "receipts").rglob("*")
            if path.is_file()
        }
        _check(
            checks,
            "receipt_semantic_inventory_exact",
            actual_receipts == expected_receipts,
        )
        receipts = [
            _read_json(remaining_root / relative)
            for relative in sorted(expected_receipts)
        ]
        receipt_by_pair = {
            (str(receipt.get("route_identity_sha256")), receipt.get("seed")): receipt
            for receipt in receipts
        }
        _check(
            checks, "receipt_denominator_exact", len(receipts) == len(expected_pairs)
        )
        _check(
            checks, "receipt_pairs_unique", len(receipt_by_pair) == len(expected_pairs)
        )
        _check(
            checks, "receipt_pairs_exact", set(receipt_by_pair) == set(expected_pairs)
        )

        complete = 0
        failed = 0
        failure_reasons: Counter[str] = Counter()
        receipt_source_maps: Counter[str] = Counter()
        snapshot_references: Counter[str] = Counter()
        snapshot_owner: dict[str, tuple[str, int]] = {}
        for pair, receipt in receipt_by_pair.items():
            identity, seed = pair
            route = route_by_identity.get(identity, {})
            prefix = f"receipt:{identity}:{seed}"
            status = receipt.get("status")
            valid_cause = (
                status == "ok"
                and receipt.get("failure_stage") is None
                and receipt.get("failure_reason") is None
            ) or (
                status == "failed"
                and isinstance(receipt.get("failure_stage"), str)
                and bool(receipt.get("failure_stage"))
                and isinstance(receipt.get("failure_reason"), str)
                and bool(receipt.get("failure_reason"))
            )
            _check(checks, f"{prefix}:schema", receipt.get("schema") == RECEIPT_SCHEMA)
            _check(checks, f"{prefix}:status_cause", valid_cause)
            _check(
                checks,
                f"{prefix}:retained",
                receipt.get("retained_in_denominator") is True,
            )
            _check(
                checks,
                f"{prefix}:identity",
                receipt.get("split") == "train"
                and receipt.get("seed") == seed
                and receipt.get("phase") == PHASE
                and receipt.get("record_key") == route.get("record_key")
                and receipt.get("map_family_id") == route.get("map_family_id")
                and receipt.get("logical_map_sha256") == route.get("logical_map_sha256")
                and receipt.get("corridor_group_sha256")
                == route.get("corridor_group_sha256")
                and receipt.get("route_identity_sha256") == identity,
            )
            snapshots = receipt.get("snapshot_sha256")
            _check(
                checks,
                f"{prefix}:snapshots",
                isinstance(snapshots, list)
                and len(snapshots) == len(set(snapshots))
                and all(_is_sha256(value) for value in snapshots),
            )
            if isinstance(snapshots, list):
                snapshot_references.update(snapshots)
                snapshot_owner.update({digest: pair for digest in snapshots})
            complete += int(status == "ok")
            failed += int(status == "failed")
            if status == "failed":
                failure_reasons[str(receipt.get("failure_reason"))] += 1
            receipt_source_maps[str(route.get("source_map_sha256"))] += 1

        snapshot_root = remaining_root / "snapshots"
        snapshot_files = sorted(
            path for path in snapshot_root.rglob("*") if path.is_file()
        )
        _check(
            checks,
            "snapshot_semantic_inventory_exact",
            all(
                path.parent == snapshot_root
                and path.suffix == ".json"
                and _is_sha256(path.stem)
                for path in snapshot_files
            ),
        )
        snapshot_by_digest = {path.stem: path for path in snapshot_files}
        _check(
            checks,
            "snapshot_filenames_unique",
            len(snapshot_by_digest) == len(snapshot_files),
        )
        _check(
            checks,
            "snapshot_reference_membership_exact",
            set(snapshot_references) == set(snapshot_by_digest),
        )
        _check(
            checks,
            "snapshot_each_belongs_to_one_receipt",
            all(count == 1 for count in snapshot_references.values()),
        )

        strata: Counter[str] = Counter()
        snapshot_source_maps: Counter[str] = Counter()
        all_k_high_risk = 0
        for digest, path in snapshot_by_digest.items():
            prefix = f"snapshot:{digest}"
            _check(checks, f"{prefix}:digest", _file_sha256(path) == digest)
            payload = _read_json(path)
            features = payload.get("feature_payload", {})
            sidecar = payload.get("sidecar", {})
            rows = (
                features.get("candidate_row_sha256", [])
                if isinstance(features, Mapping)
                else []
            )
            identity = (
                sidecar.get("default_candidate0_identity", {})
                if isinstance(sidecar, Mapping)
                else {}
            )
            owner_pair = snapshot_owner.get(digest)
            owner = receipt_by_pair.get(owner_pair, {})
            route = route_by_identity.get(str(sidecar.get("route_identity_sha256")), {})
            _check(
                checks,
                f"{prefix}:schema",
                payload.get("schema_version") == "v22_native_decision_snapshot_v1",
            )
            _check(
                checks,
                f"{prefix}:feature_fields",
                isinstance(features, Mapping) and set(features) == set(FEATURE_FIELDS),
            )
            _check(
                checks,
                f"{prefix}:feature_identity_absent",
                isinstance(features, Mapping)
                and not IDENTITY_FIELDS.intersection(features),
            )
            _check(
                checks,
                f"{prefix}:atoms",
                isinstance(features, Mapping)
                and _finite_atom_matrix(features.get("atom_matrix")),
            )
            _check(
                checks,
                f"{prefix}:source_mask",
                isinstance(features, Mapping)
                and _eight_booleans(features.get("source_valid_mask")),
            )
            _check(
                checks,
                f"{prefix}:physical_mask",
                isinstance(sidecar, Mapping)
                and _eight_booleans(sidecar.get("physical_feasible_mask")),
            )
            _check(
                checks,
                f"{prefix}:row_hashes",
                isinstance(rows, list)
                and len(rows) == 8
                and all(_is_sha256(value) for value in rows),
            )
            before = sidecar.get("candidate_tensor_sha256_before")
            _check(
                checks,
                f"{prefix}:candidate_tensor_identity",
                _is_sha256(before)
                and before == sidecar.get("candidate_tensor_sha256_after"),
            )
            _check(
                checks,
                f"{prefix}:causal_sha",
                _is_sha256(sidecar.get("causal_input_sha256")),
            )
            candidate0 = rows[0] if isinstance(rows, list) and rows else None
            max_abs_difference = (
                identity.get("max_abs_difference")
                if isinstance(identity, Mapping)
                else None
            )
            _check(
                checks,
                f"{prefix}:candidate0_default_identity",
                _is_sha256(candidate0)
                and sidecar.get("candidate0_sha256") == candidate0
                and sidecar.get("default_output_sha256") == candidate0
                and isinstance(identity, Mapping)
                and identity.get("elementwise_equal") is True
                and type(max_abs_difference) in {int, float}
                and math.isfinite(float(max_abs_difference))
                and float(max_abs_difference) == 0.0
                and identity.get("candidate0_sha256") == candidate0
                and identity.get("default_output_sha256") == candidate0
                and identity.get("native_ranked_k8") is False,
            )
            _check(
                checks,
                f"{prefix}:receipt_sidecar_identity",
                digest in owner.get("snapshot_sha256", [])
                and sidecar.get("split") == owner.get("split") == "train"
                and sidecar.get("seed") == owner.get("seed")
                and sidecar.get("record_key")
                == owner.get("record_key")
                == route.get("record_key")
                and sidecar.get("map_family_id")
                == owner.get("map_family_id")
                == route.get("map_family_id")
                and sidecar.get("logical_map_sha256")
                == owner.get("logical_map_sha256")
                == route.get("logical_map_sha256")
                and sidecar.get("route_identity_sha256")
                == owner.get("route_identity_sha256")
                == route.get("identity_sha256")
                and sidecar.get("corridor_group_sha256")
                == owner.get("corridor_group_sha256")
                == route.get("corridor_group_sha256")
                and sidecar.get("group_sha256") == route.get("corridor_group_sha256")
                and sidecar.get("source_stratum") == route.get("source_stratum"),
            )
            snapshot_source_maps[str(route.get("source_map_sha256"))] += 1
            all_k_high_risk += int(bool(sidecar.get("all_k_high_risk")))
            active = [
                str(name)
                for name, enabled in sidecar.get("source_stratum", {}).items()
                if enabled
            ] or ["normal"]
            strata.update(active)

        aggregate = {
            "planned_route_seed_runs": planned,
            "complete_route_seed_runs": complete,
            "failed_route_seed_runs": failed,
            "retained_route_seed_runs": len(receipts),
            "pending_route_seed_runs": planned - len(receipts),
            "route_coverage": len(receipts) / planned if planned else 0.0,
            "snapshot_count": len(snapshot_files),
            "snapshot_count_by_source_stratum": dict(sorted(strata.items())),
            "all_k_high_risk_snapshot_count": all_k_high_risk,
        }
        summary = _read_json(remaining_root / "remaining_summary.json")
        execution = _read_json(remaining_root / "execution.json")
        progress = _read_json(remaining_root / "progress.json")
        state = _read_json(remaining_root / "STATE.json")
        heads = _parse_heads_strict(remaining_root / "HEADS")
        terminal = "complete_with_retained_failures" if failed else "complete"
        protocol = {
            "phase": PHASE,
            "seeds": REMAINING_TRAIN_SEEDS,
            "corpus_steps": 64,
            "sample_every_ticks": 1,
            "theoretical_max_snapshots": planned * 64,
        }
        for prefix, payload in (("summary", summary), ("execution", execution)):
            _check(checks, f"{prefix}_schema", payload.get("schema") == SUMMARY_SCHEMA)
            _check(checks, f"{prefix}_status", payload.get("status") == terminal)
            _check(
                checks,
                f"{prefix}_aggregate",
                all(payload.get(name) == value for name, value in aggregate.items()),
            )
            _check(
                checks,
                f"{prefix}_protocol",
                all(payload.get(name) == value for name, value in protocol.items()),
            )
            _check(
                checks,
                f"{prefix}_denominator",
                payload.get("all_routes_retained_in_denominator") is True,
            )
            _check(
                checks,
                f"{prefix}_disk",
                float(payload.get("free_disk_gib", 0.0)) > 10.0,
            )
            _check(
                checks,
                f"{prefix}_wall_clock",
                math.isfinite(float(payload.get("wall_clock_s", 0.0)))
                and float(payload.get("wall_clock_s", 0.0)) > 0.0,
            )
            _authoritative_boundary_checks(checks, payload, prefix)
        _check(
            checks,
            "summary_execution_consistency",
            all(execution.get(name) == value for name, value in summary.items()),
        )
        _check(checks, "progress_schema", progress.get("schema") == PROGRESS_SCHEMA)
        _check(
            checks,
            "progress_terminal",
            progress.get("status") == terminal
            and progress.get("last_completed_row") == planned,
        )
        _check(
            checks,
            "progress_aggregate",
            all(progress.get(name) == value for name, value in aggregate.items()),
        )
        _authoritative_boundary_checks(checks, progress, "progress")
        _check(
            checks,
            "state_terminal",
            state.get("status") == terminal
            and state.get("seeds") == REMAINING_TRAIN_SEEDS,
        )
        _check(
            checks,
            "run_exit",
            (remaining_root / "run.exit").read_text(encoding="ascii") == "0\n",
        )
        _check(
            checks,
            "command",
            (remaining_root / "COMMAND").read_text(encoding="utf-8")
            == "v24 native corpus execute-remaining\n",
        )

        expected_heads = {
            "CAMP_HEAD": expected_source_camp_head,
            "FIXED_DP_HEAD": FIXED_DP_HEAD,
            "SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256": expected_corpus_preflight_root_sha256,
            "SOURCE_CORPUS_REVIEW_ROOT_SHA256": expected_corpus_review_root_sha256,
            "SOURCE_PILOT_ROOT_SHA256": expected_pilot_root_sha256,
            "SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256": expected_pilot_review_root_sha256,
            "SOURCE_REMAINING_PREFLIGHT_ROOT_SHA256": expected_remaining_preflight_root_sha256,
            "SOURCE_REMAINING_PREFLIGHT_INDEPENDENT_REVIEW_ROOT_SHA256": expected_remaining_preflight_review_root_sha256,
        }
        _check(checks, "heads_exact", heads == expected_heads)
        execution_sources = {
            "source_preflight_root_sha256": expected_corpus_preflight_root_sha256,
            "source_review_root_sha256": expected_corpus_review_root_sha256,
            "source_pilot_root_sha256": expected_pilot_root_sha256,
            "source_pilot_review_root_sha256": expected_pilot_review_root_sha256,
            "source_remaining_preflight_root_sha256": expected_remaining_preflight_root_sha256,
            "source_remaining_preflight_review_root_sha256": expected_remaining_preflight_review_root_sha256,
            "fixed_dp_head": FIXED_DP_HEAD,
            "next_work_target": "v24_native_corpus_remaining_train_seeds_independent_review_only",
        }
        _check(
            checks,
            "execution_source_chain",
            all(
                execution.get(name) == value
                for name, value in execution_sources.items()
            ),
        )
        free_bytes = shutil.disk_usage(remaining_root).free
        _check(checks, "disk_floor", free_bytes > MINIMUM_FREE_BYTES)
        recomputed = {
            **aggregate,
            "failure_reason_counts": dict(sorted(failure_reasons.items())),
            "receipt_count_by_source_map_sha256": dict(
                sorted(receipt_source_maps.items())
            ),
            "snapshot_count_by_source_map_sha256": dict(
                sorted(snapshot_source_maps.items())
            ),
            "free_disk_gib": free_bytes / 1024**3,
        }
    except Exception as exc:
        _check(checks, f"review_input_valid:{type(exc).__name__}", False)

    failed_checks = [check["name"] for check in checks if not check["passed"]]
    authorized = not failed_checks
    return {
        "schema": "camp_dp_v24_native_corpus_remaining_independent_review_v1",
        "status": "passed" if authorized else "failed",
        "source_remaining_root_sha256": expected_root_sha256,
        "check_count": len(checks),
        "failed_count": len(failed_checks),
        "failed_checks": failed_checks,
        "checks": checks,
        "recomputed": recomputed,
        "decision": {
            "merged_train_corpus_assembly_authorized": authorized,
            "action": (
                "assemble_frozen_pilot_and_remaining_train_corpus"
                if authorized
                else "stop_failed_remaining_review"
            ),
            "preserve_all_failures_and_denominator": authorized,
            "training_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "review_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_native_corpus_merged_train_corpus_assembly_review_only"
            if authorized
            else "v24_native_corpus_remaining_review_failure_analysis"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "remaining-root",
        "corpus-preflight-root",
        "corpus-review-root",
        "pilot-root",
        "pilot-review-root",
        "remaining-preflight-root",
        "remaining-preflight-review-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
        parser.add_argument(f"--expected-{name}-sha256", required=True)
    parser.add_argument("--expected-source-camp-head", required=True)
    parser.add_argument("--expected-route-count", type=int, default=375)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    review = review_remaining(
        args.remaining_root,
        args.expected_remaining_root_sha256,
        args.corpus_preflight_root,
        args.expected_corpus_preflight_root_sha256,
        args.corpus_review_root,
        args.expected_corpus_review_root_sha256,
        args.pilot_root,
        args.expected_pilot_root_sha256,
        args.pilot_review_root,
        args.expected_pilot_review_root_sha256,
        args.remaining_preflight_root,
        args.expected_remaining_preflight_root_sha256,
        args.remaining_preflight_review_root,
        args.expected_remaining_preflight_review_root_sha256,
        args.expected_source_camp_head,
        args.expected_route_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\nSOURCE_REMAINING_ROOT_SHA256={args.expected_remaining_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 native corpus remaining independent review\n", encoding="utf-8"
    )
    _write_json(args.output_dir / "review.json", review)
    (args.output_dir / "review.md").write_text(
        "# v24 remaining native corpus independent review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed: `{review['check_count']} / {review['failed_count']}`\n"
        f"- retained / snapshots: `{review['recomputed'].get('retained_route_seed_runs', 0)} / {review['recomputed'].get('snapshot_count', 0)}`\n"
        "- model/candidates/train/tune/outcomes/calibration/holdout/claim: `false/false/false/false/false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(review, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    success = review["status"] == "passed"
    (args.output_dir / "run.exit").write_text(
        "0\n" if success else "1\n", encoding="ascii"
    )
    root_sha256 = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha256,
                "status": review["status"],
                "check_count": review["check_count"],
                "failed_count": review["failed_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
