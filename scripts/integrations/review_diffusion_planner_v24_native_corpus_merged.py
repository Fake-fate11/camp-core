#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PILOT_SEED = 24001
REMAINING_SEEDS = [24002, 24003, 24004, 24005]
TRAIN_SEEDS = [PILOT_SEED, *REMAINING_SEEDS]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return "".join(
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
        for row in rows
    ).encode("utf-8")


def _check(checks: list[dict[str, Any]], name: str, passed: Any) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _parse_heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or "=" not in line:
            raise ValueError("malformed HEADS field")
        name, value = line.split("=", 1)
        if not name or not value or name in result:
            raise ValueError("duplicate or empty HEADS field")
        result[name] = value
    return result


def _verify_seal(root: Path, expected_root_sha256: str) -> dict[str, str]:
    root = Path(root).resolve()
    manifest = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    if (
        not _is_hex(expected_root_sha256, 64)
        or not manifest.is_file()
        or _file_sha256(manifest) != expected_root_sha256
        or not receipt.is_file()
        or receipt.read_text(encoding="ascii")
        != f"{expected_root_sha256}  SHA256SUMS\n"
    ):
        raise ValueError(f"sealed root mismatch: {root}")
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not _is_hex(parts[0], 64) or not parts[1]:
            raise ValueError("malformed sealed manifest")
        digest, relative = parts
        if relative in listed or relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("duplicate sealed path")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("sealed path escapes root") from exc
        if not path.is_file() or _file_sha256(path) != digest:
            raise ValueError(f"sealed file mismatch: {relative}")
        listed[relative] = digest
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest, receipt}
    }
    if set(listed) != actual:
        raise ValueError("sealed file inventory mismatch")
    return listed


def _review_closed(payload: Mapping[str, Any]) -> bool:
    checks = payload.get("checks")
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
        and isinstance(checks, list)
        and bool(checks)
        and all(
            isinstance(check, Mapping) and check.get("passed") is True
            for check in checks
        )
        and payload.get("check_count") == len(checks)
        and payload.get("failed_count") == 0
        and payload.get("failed_checks") == []
    )


def _source_review_authority(
    payload: Mapping[str, Any], source_sha256: str, *, pilot: bool
) -> bool:
    decision = payload.get("decision", {})
    source_field = (
        "source_pilot_root_sha256" if pilot else "source_remaining_root_sha256"
    )
    authorized = (
        decision.get("action") == "execute_frozen_remaining_train_seeds"
        and decision.get("authorized") is True
        and decision.get("seeds") == REMAINING_SEEDS
        and isinstance(decision.get("route_order"), list)
        and len(decision["route_order"]) == len(set(decision["route_order"]))
        and decision.get("route_removal_replacement_reordering_authorized") is False
        if pilot
        else decision.get("action")
        == "assemble_frozen_pilot_and_remaining_train_corpus"
        and decision.get("merged_train_corpus_assembly_authorized") is True
        and decision.get("training_authorized") is False
    )
    return (
        payload.get("schema")
        == (
            "camp_dp_v24_native_corpus_pilot_independent_review_v1"
            if pilot
            else "camp_dp_v24_native_corpus_remaining_independent_review_v1"
        )
        and payload.get("status") in {"passed", "passed_with_warning"}
        and payload.get(source_field) == source_sha256
        and _review_closed(payload)
        and authorized
        and decision.get("preserve_all_failures_and_denominator") is True
        and decision.get("tuning_authorized") is False
        and decision.get("outcome_access_authorized") is False
        and decision.get("calibration_access_authorized") is False
        and decision.get("holdout_access_authorized") is False
        and decision.get("claim_authorized") is False
    )


def _phase_rows(
    root: Path,
    files: Mapping[str, str],
    *,
    pilot: bool,
    expected_route_count: int,
) -> dict[str, Any]:
    seeds = [PILOT_SEED] if pilot else REMAINING_SEEDS
    phase = (
        "capability_pilot_all_train_routes_first_seed"
        if pilot
        else "main_completion_remaining_frozen_seeds"
    )
    schema = (
        "camp_dp_v24_native_corpus_pilot_run_receipt_v1"
        if pilot
        else "camp_dp_v24_native_corpus_remaining_run_receipt_v1"
    )
    snapshot_files = {
        Path(relative).stem: (relative, digest)
        for relative, digest in files.items()
        if relative.startswith("snapshots/") and relative.endswith(".json")
    }
    if any(
        not _is_hex(stem, 64) or stem != digest
        for stem, (_relative, digest) in snapshot_files.items()
    ):
        raise ValueError("snapshot content address mismatch")

    receipt_rows: list[dict[str, Any]] = []
    routes: dict[str, set[int]] = {}
    record_key_by_route: dict[str, str] = {}
    metadata_by_route: dict[str, tuple[str, str, str, str]] = {}
    referenced: list[str] = []
    complete = failed = 0
    failures: Counter[str] = Counter()
    for relative in sorted(
        name
        for name in files
        if name.startswith("receipts/train/")
        and Path(name).name.startswith("seed_")
        and name.endswith(".json")
    ):
        receipt = _read_json(root / relative)
        route = receipt.get("route_identity_sha256")
        seed = receipt.get("seed")
        logical_map = receipt.get("logical_map_sha256")
        corridor = receipt.get("corridor_group_sha256")
        snapshots = receipt.get("snapshot_sha256")
        status = receipt.get("status")
        if not (
            receipt.get("schema") == schema
            and status in {"ok", "failed"}
            and receipt.get("split") == "train"
            and receipt.get("phase") == phase
            and receipt.get("retained_in_denominator") is True
            and _is_hex(route, 64)
            and _is_hex(logical_map, 64)
            and _is_hex(corridor, 64)
            and type(seed) is int
            and seed in seeds
            and relative == f"receipts/train/{route}/seed_{seed}.json"
            and isinstance(snapshots, list)
            and len(snapshots) == len(set(snapshots))
            and all(_is_hex(digest, 64) for digest in snapshots)
        ):
            raise ValueError("invalid source receipt")
        if status == "failed":
            if not receipt.get("failure_stage") or not receipt.get("failure_reason"):
                raise ValueError("failed source receipt lacks cause")
            failed += 1
            failures[str(receipt["failure_reason"])] += 1
        else:
            if (
                receipt.get("failure_stage") is not None
                or receipt.get("failure_reason") is not None
            ):
                raise ValueError("successful source receipt carries failure")
            complete += 1
        routes.setdefault(route, set()).add(seed)
        record_key = str(receipt["record_key"])
        metadata = (
            record_key,
            str(receipt["map_family_id"]),
            logical_map,
            corridor,
        )
        if route in record_key_by_route and record_key_by_route[route] != record_key:
            raise ValueError("route record key changed across seeds")
        if route in metadata_by_route and metadata_by_route[route] != metadata:
            raise ValueError("route metadata changed across seeds")
        record_key_by_route[route] = record_key
        metadata_by_route[route] = metadata
        referenced.extend(snapshots)
        receipt_rows.append(
            {
                "phase": "pilot" if pilot else "remaining",
                "relative_path": relative,
                "sha256": files[relative],
                "record_key": record_key,
                "map_family_id": str(receipt["map_family_id"]),
                "logical_map_sha256": logical_map,
                "corridor_group_sha256": corridor,
                "route_identity_sha256": route,
                "seed": seed,
                "status": status,
                "snapshot_count": len(snapshots),
                "failure_stage": receipt.get("failure_stage"),
                "failure_reason": receipt.get("failure_reason"),
            }
        )
    if (
        len(routes) != expected_route_count
        or any(value != set(seeds) for value in routes.values())
        or len(referenced) != len(set(referenced))
        or set(referenced) != set(snapshot_files)
    ):
        raise ValueError("source denominator or snapshot inventory mismatch")
    snapshots = [
        {
            "phase": "pilot" if pilot else "remaining",
            "relative_path": relative,
            "sha256": digest,
        }
        for _stem, (relative, digest) in sorted(snapshot_files.items())
    ]
    return {
        "routes": set(routes),
        "record_key_by_route": record_key_by_route,
        "metadata_by_route": metadata_by_route,
        "route_seed_pairs": {
            (route, seed)
            for route, route_seeds in routes.items()
            for seed in route_seeds
        },
        "receipts": receipt_rows,
        "snapshots": snapshots,
        "snapshot_digests": set(snapshot_files),
        "planned": expected_route_count * len(seeds),
        "retained": len(receipt_rows),
        "complete": complete,
        "failed": failed,
        "pending": expected_route_count * len(seeds) - len(receipt_rows),
        "snapshot_count": len(snapshot_files),
        "failure_reason_counts": dict(sorted(failures.items())),
    }


def _counter_sum(*values: Mapping[str, Any]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for value in values:
        result.update({str(name): int(count) for name, count in value.items()})
    return dict(sorted(result.items()))


def _source_map_count_valid(value: Any, expected_total: int) -> bool:
    return (
        isinstance(value, Mapping)
        and sum(value.values()) == expected_total
        and all(
            _is_hex(name, 64) and type(count) is int and count > 0
            for name, count in value.items()
        )
    )


def _source_aggregate_valid(
    summary: Mapping[str, Any],
    review: Mapping[str, Any],
    phase: Mapping[str, Any],
    *,
    pilot: bool,
) -> bool:
    recomputed = review.get("recomputed", {})
    exact = {
        "planned_route_seed_runs": phase["planned"],
        "complete_route_seed_runs": phase["complete"],
        "failed_route_seed_runs": phase["failed"],
        "retained_route_seed_runs": phase["retained"],
        "pending_route_seed_runs": phase["pending"],
        "route_coverage": 1.0,
        "snapshot_count": phase["snapshot_count"],
        "failure_reason_counts": phase["failure_reason_counts"],
    }
    summary_keys = {
        name: value
        for name, value in exact.items()
        if name
        not in {
            "failure_reason_counts",
        }
    }
    return (
        summary.get("schema")
        == (
            "camp_dp_v24_native_corpus_pilot_summary_v1"
            if pilot
            else "camp_dp_v24_native_corpus_remaining_summary_v1"
        )
        and summary.get("status") in {"complete", "complete_with_retained_failures"}
        and summary.get("phase")
        == (
            "capability_pilot_all_train_routes_first_seed"
            if pilot
            else "main_completion_remaining_frozen_seeds"
        )
        and summary.get("all_routes_retained_in_denominator") is True
        and summary.get("tuning_executed") is False
        and summary.get("calibration_accessed") is False
        and summary.get("holdout_opened") is False
        and summary.get("outcome_fields_consumed") == []
        and summary.get("claim_authorized") is False
        and all(summary.get(name) == value for name, value in summary_keys.items())
        and all(recomputed.get(name) == value for name, value in exact.items())
        and _source_map_count_valid(
            recomputed.get("receipt_count_by_source_map_sha256"), phase["retained"]
        )
        and _source_map_count_valid(
            recomputed.get("snapshot_count_by_source_map_sha256"),
            phase["snapshot_count"],
        )
        and summary.get("snapshot_count_by_source_stratum")
        == recomputed.get("snapshot_count_by_source_stratum")
        and summary.get("all_k_high_risk_snapshot_count")
        == recomputed.get("all_k_high_risk_snapshot_count")
    )


def review_merged_corpus(
    *,
    assembly_root: Path,
    expected_assembly_root_sha256: str,
    expected_assembly_camp_head: str,
    pilot_root: Path,
    expected_pilot_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    remaining_root: Path,
    expected_remaining_root_sha256: str,
    remaining_review_root: Path,
    expected_remaining_review_root_sha256: str,
    expected_pilot_camp_head: str,
    expected_remaining_camp_head: str,
    expected_route_count: int = 375,
) -> dict[str, Any]:
    """Independently rebuild the merged indexes and aggregate from sealed sources."""
    checks: list[dict[str, Any]] = []
    roots = {
        "assembly": (Path(assembly_root).resolve(), expected_assembly_root_sha256),
        "pilot": (Path(pilot_root).resolve(), expected_pilot_root_sha256),
        "pilot_review": (
            Path(pilot_review_root).resolve(),
            expected_pilot_review_root_sha256,
        ),
        "remaining": (
            Path(remaining_root).resolve(),
            expected_remaining_root_sha256,
        ),
        "remaining_review": (
            Path(remaining_review_root).resolve(),
            expected_remaining_review_root_sha256,
        ),
    }
    inventories: dict[str, dict[str, str]] = {}
    for name, (root, digest) in roots.items():
        try:
            inventories[name] = _verify_seal(root, digest)
            _check(checks, f"{name}_exact_seal", True)
        except Exception:
            inventories[name] = {}
            _check(checks, f"{name}_exact_seal", False)

    recomputed: dict[str, Any] = {}
    try:
        heads = _parse_heads(roots["assembly"][0] / "HEADS")
        _check(
            checks,
            "assembly_heads",
            heads.get("CAMP_HEAD") == expected_assembly_camp_head
            and _is_hex(expected_assembly_camp_head, 40)
            and heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and heads.get("SOURCE_PILOT_ROOT_SHA256") == expected_pilot_root_sha256
            and heads.get("SOURCE_PILOT_REVIEW_ROOT_SHA256")
            == expected_pilot_review_root_sha256
            and heads.get("SOURCE_REMAINING_ROOT_SHA256")
            == expected_remaining_root_sha256
            and heads.get("SOURCE_REMAINING_REVIEW_ROOT_SHA256")
            == expected_remaining_review_root_sha256,
        )
        assembly_files = inventories["assembly"]
        _check(
            checks,
            "assembly_file_inventory",
            set(assembly_files)
            == {
                "COMMAND",
                "HEADS",
                "assembly.md",
                "merged_summary.json",
                "receipt_index.jsonl",
                "run.exit",
                "snapshot_index.jsonl",
                "stderr.txt",
                "stdout.txt",
            },
        )
        pilot_heads = _parse_heads(roots["pilot"][0] / "HEADS")
        remaining_heads = _parse_heads(roots["remaining"][0] / "HEADS")
        pilot_review_heads = _parse_heads(roots["pilot_review"][0] / "HEADS")
        remaining_review_heads = _parse_heads(roots["remaining_review"][0] / "HEADS")
        _check(
            checks,
            "source_heads",
            pilot_heads.get("CAMP_HEAD") == expected_pilot_camp_head
            and _is_hex(expected_pilot_camp_head, 40)
            and pilot_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and remaining_heads.get("CAMP_HEAD") == expected_remaining_camp_head
            and _is_hex(expected_remaining_camp_head, 40)
            and remaining_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and pilot_review_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and pilot_review_heads.get("SOURCE_PILOT_ROOT_SHA256")
            == expected_pilot_root_sha256
            and remaining_review_heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD
            and remaining_review_heads.get("SOURCE_REMAINING_ROOT_SHA256")
            == expected_remaining_root_sha256,
        )
        _check(
            checks,
            "source_execution_receipts",
            (roots["pilot"][0] / "run.exit").read_text(encoding="ascii") == "0\n"
            and (roots["pilot_review"][0] / "run.exit").read_text(encoding="ascii")
            == "0\n"
            and (roots["remaining"][0] / "run.exit").read_text(encoding="ascii")
            == "0\n"
            and (roots["remaining_review"][0] / "run.exit").read_text(encoding="ascii")
            == "0\n",
        )
        pilot_review = _read_json(roots["pilot_review"][0] / "review.json")
        remaining_review = _read_json(roots["remaining_review"][0] / "review.json")
        _check(
            checks,
            "pilot_review_authority",
            _source_review_authority(
                pilot_review, expected_pilot_root_sha256, pilot=True
            ),
        )
        _check(
            checks,
            "remaining_review_authority",
            _source_review_authority(
                remaining_review, expected_remaining_root_sha256, pilot=False
            ),
        )
        pilot = _phase_rows(
            roots["pilot"][0],
            inventories["pilot"],
            pilot=True,
            expected_route_count=expected_route_count,
        )
        remaining = _phase_rows(
            roots["remaining"][0],
            inventories["remaining"],
            pilot=False,
            expected_route_count=expected_route_count,
        )
        pilot_summary = _read_json(roots["pilot"][0] / "pilot_summary.json")
        remaining_summary = _read_json(roots["remaining"][0] / "remaining_summary.json")
        _check(
            checks,
            "pilot_source_aggregate",
            _source_aggregate_valid(pilot_summary, pilot_review, pilot, pilot=True),
        )
        _check(
            checks,
            "remaining_source_aggregate",
            _source_aggregate_valid(
                remaining_summary, remaining_review, remaining, pilot=False
            ),
        )
        _check(checks, "route_sets_exact", pilot["routes"] == remaining["routes"])
        _check(
            checks,
            "route_record_keys_exact",
            pilot["record_key_by_route"] == remaining["record_key_by_route"],
        )
        _check(
            checks,
            "route_metadata_exact",
            pilot["metadata_by_route"] == remaining["metadata_by_route"],
        )
        _check(
            checks,
            "route_seed_zero_overlap",
            not (pilot["route_seed_pairs"] & remaining["route_seed_pairs"]),
        )
        _check(
            checks,
            "snapshot_zero_overlap",
            not (pilot["snapshot_digests"] & remaining["snapshot_digests"]),
        )
        route_order = pilot_review["decision"].get("route_order", [])
        _check(
            checks,
            "frozen_route_order_exact",
            len(route_order) == expected_route_count
            and set(route_order) == set(pilot["record_key_by_route"].values()),
        )
        route_position = {
            record_key: index for index, record_key in enumerate(route_order)
        }
        receipt_rows = sorted(
            [*pilot["receipts"], *remaining["receipts"]],
            key=lambda row: (route_position[row["record_key"]], row["seed"]),
        )
        snapshot_rows = [*pilot["snapshots"], *remaining["snapshots"]]
        snapshot_rows.sort(key=lambda row: (row["sha256"], row["phase"]))
        expected_receipt_bytes = _jsonl_bytes(receipt_rows)
        expected_snapshot_bytes = _jsonl_bytes(snapshot_rows)
        _check(
            checks,
            "receipt_index_exact",
            (roots["assembly"][0] / "receipt_index.jsonl").read_bytes()
            == expected_receipt_bytes,
        )
        _check(
            checks,
            "snapshot_index_exact",
            (roots["assembly"][0] / "snapshot_index.jsonl").read_bytes()
            == expected_snapshot_bytes,
        )

        pilot_recomputed = pilot_review["recomputed"]
        remaining_recomputed = remaining_review["recomputed"]
        planned = pilot["planned"] + remaining["planned"]
        retained = pilot["retained"] + remaining["retained"]
        recomputed = {
            "route_count": expected_route_count,
            "seeds": TRAIN_SEEDS,
            "planned_route_seed_runs": planned,
            "complete_route_seed_runs": pilot["complete"] + remaining["complete"],
            "failed_route_seed_runs": pilot["failed"] + remaining["failed"],
            "retained_route_seed_runs": retained,
            "pending_route_seed_runs": pilot["pending"] + remaining["pending"],
            "route_coverage": retained / planned if planned else 0.0,
            "all_routes_retained_in_denominator": retained == planned,
            "snapshot_count": pilot["snapshot_count"] + remaining["snapshot_count"],
            "snapshot_overlap_count": 0,
            "snapshot_count_by_source_stratum": _counter_sum(
                pilot_recomputed["snapshot_count_by_source_stratum"],
                remaining_recomputed["snapshot_count_by_source_stratum"],
            ),
            "all_k_high_risk_snapshot_count": int(
                pilot_recomputed["all_k_high_risk_snapshot_count"]
            )
            + int(remaining_recomputed["all_k_high_risk_snapshot_count"]),
            "failure_reason_counts": _counter_sum(
                pilot["failure_reason_counts"], remaining["failure_reason_counts"]
            ),
            "receipt_count_by_source_map_sha256": _counter_sum(
                pilot_recomputed["receipt_count_by_source_map_sha256"],
                remaining_recomputed["receipt_count_by_source_map_sha256"],
            ),
            "snapshot_count_by_source_map_sha256": _counter_sum(
                pilot_recomputed["snapshot_count_by_source_map_sha256"],
                remaining_recomputed["snapshot_count_by_source_map_sha256"],
            ),
            "receipt_index_row_count": len(receipt_rows),
            "receipt_index_sha256": hashlib.sha256(expected_receipt_bytes).hexdigest(),
            "snapshot_index_row_count": len(snapshot_rows),
            "snapshot_index_sha256": hashlib.sha256(
                expected_snapshot_bytes
            ).hexdigest(),
            "corpus_steps": 64,
            "sample_every_ticks": 1,
            "theoretical_max_snapshots": planned * 64,
            "offline_corpus_generation_wall_clock_s": float(
                pilot_summary["wall_clock_s"]
            )
            + float(remaining_summary["wall_clock_s"]),
        }
        summary = _read_json(roots["assembly"][0] / "merged_summary.json")
        _check(
            checks,
            "assembly_execution_receipts",
            (roots["assembly"][0] / "run.exit").read_text(encoding="ascii") == "0\n"
            and (roots["assembly"][0] / "stderr.txt").read_text(encoding="utf-8") == ""
            and _read_json(roots["assembly"][0] / "stdout.txt") == summary
            and (roots["assembly"][0] / "COMMAND").read_text(encoding="utf-8")
            == "v24 native corpus deterministic merged train index assembly\n",
        )
        _check(
            checks,
            "summary_schema",
            summary.get("schema") == "camp_dp_v24_native_corpus_merged_train_index_v1"
            and summary.get("status") == "passed"
            and summary.get("phase") == "merged_train_corpus_assembly_only"
            and summary.get("split") == "train",
        )
        _check(
            checks,
            "summary_recomputed",
            all(summary.get(name) == value for name, value in recomputed.items()),
        )
        _check(
            checks,
            "summary_boundaries_closed",
            summary.get("snapshot_payloads_copied") is False
            and summary.get("snapshot_payloads_modified") is False
            and summary.get("route_or_seed_removed_replaced_or_reordered") is False
            and summary.get("assembly_only") is True
            and summary.get("model_loaded") is False
            and summary.get("simulator_executed") is False
            and summary.get("candidate_generation_started") is False
            and summary.get("training_executed") is False
            and summary.get("tuning_executed") is False
            and summary.get("outcome_fields_consumed") == []
            and summary.get("calibration_accessed") is False
            and summary.get("holdout_opened") is False
            and summary.get("claim_authorized") is False,
        )
        _check(
            checks,
            "source_roots_exact",
            all(
                summary.get("source_artifacts", {}).get(name, {}).get("root_sha256")
                == digest
                for name, (_root, digest) in roots.items()
                if name != "assembly"
            ),
        )
        _check(
            checks,
            "source_verified_file_counts_exact",
            summary.get("source_verified_file_counts")
            == {
                name: len(files)
                for name, files in inventories.items()
                if name != "assembly"
            },
        )
    except Exception:
        _check(checks, "review_input_valid", False)

    failed_checks = [check["name"] for check in checks if not check["passed"]]
    passed = not failed_checks
    return {
        "schema": "camp_dp_v24_native_corpus_merged_independent_review_v1",
        "status": "passed" if passed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed_checks),
        "failed_checks": failed_checks,
        "checks": checks,
        "verified_file_count": sum(len(files) for files in inventories.values()),
        "source_assembly_root_sha256": expected_assembly_root_sha256,
        "source_pilot_root_sha256": expected_pilot_root_sha256,
        "source_pilot_review_root_sha256": expected_pilot_review_root_sha256,
        "source_remaining_root_sha256": expected_remaining_root_sha256,
        "source_remaining_review_root_sha256": expected_remaining_review_root_sha256,
        "fixed_dp_head": FIXED_DP_HEAD,
        "recomputed": recomputed,
        "decision": {
            "action": (
                "review_atom_availability_and_freeze_train_only_mask"
                if passed
                else "merged_corpus_failure_analysis_only"
            ),
            "atom_availability_review_authorized": passed,
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
            "v24_native_corpus_atom_availability_and_freeze_review_only"
            if passed
            else "v24_native_corpus_merged_train_corpus_failure_analysis_only"
        ),
    }


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    (root / "SHA256SUMS").write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly-root", type=Path, required=True)
    parser.add_argument("--expected-assembly-root-sha256", required=True)
    parser.add_argument("--expected-assembly-camp-head", required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-root-sha256", required=True)
    parser.add_argument("--pilot-review-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-review-root-sha256", required=True)
    parser.add_argument("--remaining-root", type=Path, required=True)
    parser.add_argument("--expected-remaining-root-sha256", required=True)
    parser.add_argument("--remaining-review-root", type=Path, required=True)
    parser.add_argument("--expected-remaining-review-root-sha256", required=True)
    parser.add_argument("--expected-pilot-camp-head", required=True)
    parser.add_argument("--expected-remaining-camp-head", required=True)
    parser.add_argument("--expected-route-count", type=int, default=375)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    review = review_merged_corpus(
        assembly_root=args.assembly_root,
        expected_assembly_root_sha256=args.expected_assembly_root_sha256,
        expected_assembly_camp_head=args.expected_assembly_camp_head,
        pilot_root=args.pilot_root,
        expected_pilot_root_sha256=args.expected_pilot_root_sha256,
        pilot_review_root=args.pilot_review_root,
        expected_pilot_review_root_sha256=args.expected_pilot_review_root_sha256,
        remaining_root=args.remaining_root,
        expected_remaining_root_sha256=args.expected_remaining_root_sha256,
        remaining_review_root=args.remaining_review_root,
        expected_remaining_review_root_sha256=args.expected_remaining_review_root_sha256,
        expected_pilot_camp_head=args.expected_pilot_camp_head,
        expected_remaining_camp_head=args.expected_remaining_camp_head,
        expected_route_count=args.expected_route_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_ASSEMBLY_ROOT_SHA256={args.expected_assembly_root_sha256}\n"
        f"SOURCE_PILOT_ROOT_SHA256={args.expected_pilot_root_sha256}\n"
        "SOURCE_PILOT_REVIEW_ROOT_SHA256="
        f"{args.expected_pilot_review_root_sha256}\n"
        f"SOURCE_REMAINING_ROOT_SHA256={args.expected_remaining_root_sha256}\n"
        "SOURCE_REMAINING_REVIEW_ROOT_SHA256="
        f"{args.expected_remaining_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 native corpus merged train index independent review\n",
        encoding="utf-8",
    )
    _write_json(args.output_dir / "review.json", review)
    (args.output_dir / "review.md").write_text(
        "# v24 merged native train corpus independent review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed: `{review['check_count']} / {review['failed_count']}`\n"
        f"- verified files: `{review['verified_file_count']}`\n"
        "- train / outcomes / calibration / holdout / claim authorized: "
        "`false/false/false/false/false`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(review, sort_keys=True, allow_nan=False) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
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
