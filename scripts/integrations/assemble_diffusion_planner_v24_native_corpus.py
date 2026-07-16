#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PILOT_PHASE = "capability_pilot_all_train_routes_first_seed"
REMAINING_PHASE = "main_completion_remaining_frozen_seeds"
PILOT_SEED = 24001
REMAINING_SEEDS = [24002, 24003, 24004, 24005]
TRAIN_SEEDS = [PILOT_SEED, *REMAINING_SEEDS]
MINIMUM_FREE_BYTES = 10 * 1024**3


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
    if not _is_hex(expected_root_sha256, 64):
        raise ValueError("invalid expected root SHA256")
    if not manifest.is_file() or _file_sha256(manifest) != expected_root_sha256:
        raise ValueError(f"sealed manifest mismatch: {root}")
    if (
        not receipt.is_file()
        or receipt.read_text(encoding="ascii")
        != f"{expected_root_sha256}  SHA256SUMS\n"
    ):
        raise ValueError(f"root receipt mismatch: {root}")

    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not _is_hex(parts[0], 64) or not parts[1]:
            raise ValueError(f"malformed sealed manifest: {root}")
        digest, relative = parts
        if relative in listed or relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError(f"duplicate sealed path: {relative}")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"sealed path escapes root: {relative}") from exc
        if not path.is_file() or _file_sha256(path) != digest:
            raise ValueError(f"sealed file mismatch: {relative}")
        listed[relative] = digest

    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest, receipt}
    }
    if set(listed) != actual:
        raise ValueError(f"sealed file inventory mismatch: {root}")
    return listed


def _review_is_closed(review: Mapping[str, Any]) -> bool:
    checks = review.get("checks")
    return (
        review.get("review_only") is True
        and review.get("model_loaded") is False
        and review.get("candidate_generation_started") is False
        and review.get("training_executed") is False
        and review.get("tuning_executed") is False
        and review.get("outcome_accessed") is False
        and review.get("calibration_accessed") is False
        and review.get("holdout_opened") is False
        and review.get("claim_authorized") is False
        and isinstance(checks, list)
        and bool(checks)
        and all(
            isinstance(check, Mapping) and check.get("passed") is True
            for check in checks
        )
        and type(review.get("check_count")) is int
        and review.get("check_count") == len(checks)
        and review.get("failed_count") == 0
        and review.get("failed_checks") == []
    )


def _summary_is_closed(summary: Mapping[str, Any]) -> bool:
    return (
        summary.get("tuning_executed") is False
        and summary.get("calibration_accessed") is False
        and summary.get("holdout_opened") is False
        and summary.get("outcome_fields_consumed") == []
        and summary.get("claim_authorized") is False
    )


def _counter_sum(*values: Mapping[str, Any]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for value in values:
        total.update({str(name): int(count) for name, count in value.items()})
    return dict(sorted(total.items()))


def _source_map_count_valid(value: Any, expected_total: int) -> bool:
    return (
        isinstance(value, Mapping)
        and all(
            _is_hex(name, 64) and type(count) is int and count > 0
            for name, count in value.items()
        )
        and sum(value.values()) == expected_total
    )


def _collect_phase(
    root: Path,
    files: Mapping[str, str],
    *,
    phase_name: str,
    receipt_schema: str,
    seeds: Sequence[int],
    expected_route_count: int,
) -> dict[str, Any]:
    snapshot_files = {
        Path(relative).stem: (relative, digest)
        for relative, digest in files.items()
        if relative.startswith("snapshots/") and relative.endswith(".json")
    }
    for stem, (_relative, digest) in snapshot_files.items():
        if not _is_hex(stem, 64) or stem != digest:
            raise ValueError("snapshot content address mismatch")

    receipt_paths = sorted(
        relative
        for relative in files
        if relative.startswith("receipts/train/")
        and Path(relative).name.startswith("seed_")
        and relative.endswith(".json")
    )
    receipt_rows: list[dict[str, Any]] = []
    referenced_snapshots: list[str] = []
    route_seeds: dict[str, set[int]] = {}
    record_key_by_route: dict[str, str] = {}
    metadata_by_route: dict[str, tuple[str, str, str, str]] = {}
    failures: Counter[str] = Counter()
    complete = failed = 0

    for relative in receipt_paths:
        receipt = _read_json(root / relative)
        status = receipt.get("status")
        seed = receipt.get("seed")
        route = receipt.get("route_identity_sha256")
        logical_map = receipt.get("logical_map_sha256")
        corridor = receipt.get("corridor_group_sha256")
        snapshots = receipt.get("snapshot_sha256")
        expected_path = (
            f"receipts/train/{route}/seed_{seed}.json"
            if isinstance(route, str) and type(seed) is int
            else ""
        )
        valid = (
            isinstance(receipt, Mapping)
            and receipt.get("schema") == receipt_schema
            and status in {"ok", "failed"}
            and receipt.get("split") == "train"
            and receipt.get("phase") == phase_name
            and receipt.get("retained_in_denominator") is True
            and _is_hex(route, 64)
            and _is_hex(logical_map, 64)
            and _is_hex(corridor, 64)
            and type(seed) is int
            and seed in seeds
            and relative == expected_path
            and isinstance(snapshots, list)
            and len(snapshots) == len(set(snapshots))
            and all(_is_hex(digest, 64) for digest in snapshots)
        )
        if not valid:
            raise ValueError(f"invalid merged source receipt: {relative}")
        if status == "failed":
            if not receipt.get("failure_stage") or not receipt.get("failure_reason"):
                raise ValueError(f"failed receipt lacks cause: {relative}")
            failed += 1
            failures[str(receipt["failure_reason"])] += 1
        else:
            if (
                receipt.get("failure_stage") is not None
                or receipt.get("failure_reason") is not None
            ):
                raise ValueError(f"successful receipt carries failure: {relative}")
            complete += 1
        route_seeds.setdefault(route, set()).add(seed)
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
        referenced_snapshots.extend(snapshots)
        receipt_rows.append(
            {
                "phase": "pilot" if seed == PILOT_SEED else "remaining",
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

    expected_seed_set = set(seeds)
    if len(route_seeds) != expected_route_count or any(
        route_seed_set != expected_seed_set for route_seed_set in route_seeds.values()
    ):
        raise ValueError("route-seed denominator mismatch")
    if len(referenced_snapshots) != len(set(referenced_snapshots)):
        raise ValueError("duplicate snapshot reference within phase")
    if set(referenced_snapshots) != set(snapshot_files):
        raise ValueError("receipt and snapshot inventory mismatch")

    snapshot_rows = [
        {
            "phase": "pilot" if seeds == [PILOT_SEED] else "remaining",
            "relative_path": relative,
            "sha256": digest,
        }
        for _stem, (relative, digest) in sorted(snapshot_files.items())
    ]
    return {
        "routes": set(route_seeds),
        "record_key_by_route": record_key_by_route,
        "metadata_by_route": metadata_by_route,
        "route_seed_pairs": {
            (route, seed)
            for route, route_seed_set in route_seeds.items()
            for seed in route_seed_set
        },
        "receipt_rows": receipt_rows,
        "snapshot_rows": snapshot_rows,
        "snapshot_digests": set(snapshot_files),
        "planned": expected_route_count * len(seeds),
        "retained": len(receipt_rows),
        "complete": complete,
        "failed": failed,
        "pending": expected_route_count * len(seeds) - len(receipt_rows),
        "snapshot_count": len(snapshot_files),
        "failure_reason_counts": dict(sorted(failures.items())),
    }


def _validate_phase_authority(
    *,
    root: Path,
    files: Mapping[str, str],
    root_sha256: str,
    review_root: Path,
    review_files: Mapping[str, str],
    expected_camp_head: str,
    summary_name: str,
    summary_schema: str,
    phase_name: str,
    receipt_schema: str,
    seeds: Sequence[int],
    expected_route_count: int,
    pilot: bool,
) -> tuple[dict[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    heads = _parse_heads(root / "HEADS")
    review_heads = _parse_heads(review_root / "HEADS")
    if (root / "run.exit").read_text(encoding="ascii") != "0\n" or (
        review_root / "run.exit"
    ).read_text(encoding="ascii") != "0\n":
        raise ValueError("source run.exit receipt mismatch")
    if heads.get("CAMP_HEAD") != expected_camp_head or not _is_hex(
        expected_camp_head, 40
    ):
        raise ValueError("source CAMP HEAD mismatch")
    if heads.get("FIXED_DP_HEAD") != FIXED_DP_HEAD:
        raise ValueError("source fixed DP HEAD mismatch")
    if review_heads.get("FIXED_DP_HEAD") != FIXED_DP_HEAD:
        raise ValueError("source review fixed DP HEAD mismatch")
    source_head_field = (
        "SOURCE_PILOT_ROOT_SHA256" if pilot else "SOURCE_REMAINING_ROOT_SHA256"
    )
    if review_heads.get(source_head_field) != root_sha256:
        raise ValueError("source review HEADS chain mismatch")
    if not files or not review_files:
        raise ValueError("empty sealed source artifact")

    summary = _read_json(root / summary_name)
    execution = _read_json(root / "execution.json")
    review = _read_json(review_root / "review.json")
    expected_review_schema = (
        "camp_dp_v24_native_corpus_pilot_independent_review_v1"
        if pilot
        else "camp_dp_v24_native_corpus_remaining_independent_review_v1"
    )
    if (
        summary.get("schema") != summary_schema
        or execution.get("schema") != summary_schema
        or summary.get("phase") != phase_name
        or execution.get("phase") != phase_name
        or summary.get("status") not in {"complete", "complete_with_retained_failures"}
        or execution.get("status") != summary.get("status")
        or not _summary_is_closed(summary)
        or not _summary_is_closed(execution)
        or review.get("schema") != expected_review_schema
        or review.get("status") not in {"passed", "passed_with_warning"}
        or not _review_is_closed(review)
        or review.get(
            "source_pilot_root_sha256" if pilot else "source_remaining_root_sha256"
        )
        != root_sha256
    ):
        raise ValueError("source summary or review authority mismatch")

    decision = review.get("decision", {})
    if pilot:
        authorized = (
            decision.get("action") == "execute_frozen_remaining_train_seeds"
            and decision.get("authorized") is True
            and decision.get("seeds") == REMAINING_SEEDS
            and isinstance(decision.get("route_order"), list)
            and len(decision["route_order"]) == expected_route_count
            and len(set(decision["route_order"])) == expected_route_count
            and decision.get("route_removal_replacement_reordering_authorized") is False
        )
    else:
        authorized = (
            decision.get("action") == "assemble_frozen_pilot_and_remaining_train_corpus"
            and decision.get("merged_train_corpus_assembly_authorized") is True
            and decision.get("training_authorized") is False
        )
    if not (
        authorized
        and decision.get("preserve_all_failures_and_denominator") is True
        and decision.get("tuning_authorized") is False
        and decision.get("outcome_access_authorized") is False
        and decision.get("calibration_access_authorized") is False
        and decision.get("holdout_access_authorized") is False
        and decision.get("claim_authorized") is False
    ):
        raise ValueError("source review decision mismatch")

    collected = _collect_phase(
        root,
        files,
        phase_name=phase_name,
        receipt_schema=receipt_schema,
        seeds=seeds,
        expected_route_count=expected_route_count,
    )
    recomputed = review.get("recomputed", {})
    aggregate = {
        "planned_route_seed_runs": collected["planned"],
        "complete_route_seed_runs": collected["complete"],
        "failed_route_seed_runs": collected["failed"],
        "retained_route_seed_runs": collected["retained"],
        "pending_route_seed_runs": collected["pending"],
        "route_coverage": 1.0,
        "snapshot_count": collected["snapshot_count"],
        "failure_reason_counts": collected["failure_reason_counts"],
    }
    if any(
        summary.get(name) != value
        for name, value in aggregate.items()
        if name
        not in {
            "failure_reason_counts",
        }
    ):
        raise ValueError("source summary aggregate mismatch")
    if any(recomputed.get(name) != value for name, value in aggregate.items()):
        raise ValueError("source review recomputation mismatch")
    if not (
        _source_map_count_valid(
            recomputed.get("receipt_count_by_source_map_sha256"),
            collected["retained"],
        )
        and _source_map_count_valid(
            recomputed.get("snapshot_count_by_source_map_sha256"),
            collected["snapshot_count"],
        )
    ):
        raise ValueError("source review map census mismatch")
    if summary.get("snapshot_count_by_source_stratum") != recomputed.get(
        "snapshot_count_by_source_stratum"
    ) or summary.get("all_k_high_risk_snapshot_count") != recomputed.get(
        "all_k_high_risk_snapshot_count"
    ):
        raise ValueError("source reviewed snapshot aggregate mismatch")
    return collected, summary, review


def assemble_merged_corpus(
    *,
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
    output_dir: Path,
    expected_route_count: int = 375,
) -> dict[str, Any]:
    """Assemble a sealed train-only index over immutable pilot and remaining roots."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_dir.parent).free <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")

    roots = {
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
    inventories = {
        name: _verify_seal(root, digest) for name, (root, digest) in roots.items()
    }
    pilot, pilot_summary, pilot_review = _validate_phase_authority(
        root=roots["pilot"][0],
        files=inventories["pilot"],
        root_sha256=roots["pilot"][1],
        review_root=roots["pilot_review"][0],
        review_files=inventories["pilot_review"],
        expected_camp_head=expected_pilot_camp_head,
        summary_name="pilot_summary.json",
        summary_schema="camp_dp_v24_native_corpus_pilot_summary_v1",
        phase_name=PILOT_PHASE,
        receipt_schema="camp_dp_v24_native_corpus_pilot_run_receipt_v1",
        seeds=[PILOT_SEED],
        expected_route_count=expected_route_count,
        pilot=True,
    )
    remaining, remaining_summary, remaining_review = _validate_phase_authority(
        root=roots["remaining"][0],
        files=inventories["remaining"],
        root_sha256=roots["remaining"][1],
        review_root=roots["remaining_review"][0],
        review_files=inventories["remaining_review"],
        expected_camp_head=expected_remaining_camp_head,
        summary_name="remaining_summary.json",
        summary_schema="camp_dp_v24_native_corpus_remaining_summary_v1",
        phase_name=REMAINING_PHASE,
        receipt_schema="camp_dp_v24_native_corpus_remaining_run_receipt_v1",
        seeds=REMAINING_SEEDS,
        expected_route_count=expected_route_count,
        pilot=False,
    )
    if pilot["routes"] != remaining["routes"]:
        raise ValueError("pilot and remaining route sets differ")
    if pilot["record_key_by_route"] != remaining["record_key_by_route"]:
        raise ValueError("pilot and remaining route record keys differ")
    if pilot["metadata_by_route"] != remaining["metadata_by_route"]:
        raise ValueError("pilot and remaining route metadata changed")
    if pilot["route_seed_pairs"] & remaining["route_seed_pairs"]:
        raise ValueError("pilot and remaining route-seed overlap")
    snapshot_overlap = pilot["snapshot_digests"] & remaining["snapshot_digests"]
    if snapshot_overlap:
        raise ValueError("pilot and remaining snapshot overlap")

    route_order = pilot_review["decision"]["route_order"]
    if set(route_order) != set(pilot["record_key_by_route"].values()):
        raise ValueError("frozen route order does not match merged routes")
    route_position = {record_key: index for index, record_key in enumerate(route_order)}
    receipt_rows = sorted(
        [*pilot["receipt_rows"], *remaining["receipt_rows"]],
        key=lambda row: (route_position[row["record_key"]], row["seed"]),
    )
    snapshot_rows = [*pilot["snapshot_rows"], *remaining["snapshot_rows"]]
    snapshot_rows.sort(key=lambda row: (row["sha256"], row["phase"]))
    output_dir.mkdir()
    receipt_bytes = _jsonl_bytes(receipt_rows)
    snapshot_bytes = _jsonl_bytes(snapshot_rows)
    (output_dir / "receipt_index.jsonl").write_bytes(receipt_bytes)
    (output_dir / "snapshot_index.jsonl").write_bytes(snapshot_bytes)

    planned = pilot["planned"] + remaining["planned"]
    retained = pilot["retained"] + remaining["retained"]
    pilot_recomputed = pilot_review["recomputed"]
    remaining_recomputed = remaining_review["recomputed"]
    summary = {
        "schema": "camp_dp_v24_native_corpus_merged_train_index_v1",
        "status": "passed",
        "phase": "merged_train_corpus_assembly_only",
        "split": "train",
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
        "corpus_steps": 64,
        "sample_every_ticks": 1,
        "theoretical_max_snapshots": planned * 64,
        "offline_corpus_generation_wall_clock_s": float(pilot_summary["wall_clock_s"])
        + float(remaining_summary["wall_clock_s"]),
        "free_disk_gib": shutil.disk_usage(output_dir).free / (1024**3),
        "minimum_free_disk_gib": 10,
        "receipt_index_row_count": len(receipt_rows),
        "receipt_index_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "snapshot_index_row_count": len(snapshot_rows),
        "snapshot_index_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "source_artifacts": {
            name: {"path": str(root), "root_sha256": digest}
            for name, (root, digest) in roots.items()
        },
        "source_verified_file_counts": {
            name: len(inventory) for name, inventory in inventories.items()
        },
        "snapshot_payloads_copied": False,
        "snapshot_payloads_modified": False,
        "route_or_seed_removed_replaced_or_reordered": False,
        "assembly_only": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_native_corpus_merged_train_corpus_independent_review_only"
        ),
    }
    _write_json(output_dir / "merged_summary.json", summary)
    return summary


def seal_artifact(root: Path) -> str:
    root = Path(root)
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
    root_sha256 = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha256}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha256


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
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

    summary = assemble_merged_corpus(
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
        output_dir=args.output_dir,
        expected_route_count=args.expected_route_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_PILOT_ROOT_SHA256={args.expected_pilot_root_sha256}\n"
        "SOURCE_PILOT_REVIEW_ROOT_SHA256="
        f"{args.expected_pilot_review_root_sha256}\n"
        f"SOURCE_REMAINING_ROOT_SHA256={args.expected_remaining_root_sha256}\n"
        "SOURCE_REMAINING_REVIEW_ROOT_SHA256="
        f"{args.expected_remaining_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 native corpus deterministic merged train index assembly\n",
        encoding="utf-8",
    )
    (args.output_dir / "assembly.md").write_text(
        "# v24 merged native train corpus assembly\n\n"
        f"- status: `{summary['status']}`\n"
        f"- routes / seeds / route-seed rows: `{summary['route_count']} / "
        f"{len(summary['seeds'])} / {summary['retained_route_seed_runs']}`\n"
        f"- complete / failed / snapshots: `{summary['complete_route_seed_runs']} / "
        f"{summary['failed_route_seed_runs']} / {summary['snapshot_count']}`\n"
        "- payload copy / train / outcomes / calibration / holdout / claim: "
        "`false/false/false/false/false/false`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(summary, sort_keys=True, allow_nan=False) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = seal_artifact(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha256,
                "status": summary["status"],
                "route_seed_rows": summary["retained_route_seed_runs"],
                "snapshot_count": summary["snapshot_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
