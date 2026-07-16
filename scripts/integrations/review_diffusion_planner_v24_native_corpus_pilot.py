#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PILOT_SEED = 24001
TRAIN_SEEDS = [24001, 24002, 24003, 24004, 24005]
REMAINING_TRAIN_SEEDS = [24002, 24003, 24004, 24005]
MINIMUM_FREE_BYTES = 10 * 1024**3
FEATURE_FIELDS = ["atom_matrix", "source_valid_mask", "candidate_row_sha256"]
IDENTITY_FIELDS = {
    "record_key",
    "map_family_id",
    "logical_map_sha256",
    "map_id",
    "route_id",
    "route_identity_sha256",
    "corridor_group_sha256",
    "group_sha256",
    "split",
    "seed",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_HEAD_PATTERN = re.compile(r"[0-9a-f]{40}")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _check(checks: list[dict[str, Any]], name: str, passed: Any) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _verify_seal(
    root: Path, expected_root_sha256: str, prefix: str
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    root = root.resolve()
    manifest = root / "SHA256SUMS"
    root_receipt = root / "ROOT_SHA256SUMS"
    _check(checks, f"{prefix}_manifest_exists", manifest.is_file())
    _check(
        checks,
        f"{prefix}_root_sha256",
        manifest.is_file()
        and _is_sha256(expected_root_sha256)
        and _file_sha256(manifest) == expected_root_sha256,
    )
    _check(
        checks,
        f"{prefix}_root_receipt",
        root_receipt.is_file()
        and root_receipt.read_text(encoding="ascii").strip()
        == f"{expected_root_sha256}  SHA256SUMS",
    )
    if not manifest.is_file():
        return checks

    listed: list[str] = []
    for index, line in enumerate(manifest.read_text(encoding="utf-8").splitlines()):
        parts = line.split("  ", 1)
        valid_line = len(parts) == 2 and _is_sha256(parts[0]) and bool(parts[1])
        _check(checks, f"{prefix}_manifest_line:{index}", valid_line)
        if not valid_line:
            continue
        digest, relative = parts
        listed.append(relative)
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
            contained = True
        except ValueError:
            contained = False
        _check(checks, f"{prefix}_contained:{relative}", contained)
        _check(
            checks,
            f"{prefix}_sha:{relative}",
            contained and path.is_file() and _file_sha256(path) == digest,
        )
    _check(checks, f"{prefix}_manifest_paths_unique", len(listed) == len(set(listed)))
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest, root_receipt}
    }
    _check(checks, f"{prefix}_manifest_file_set_exact", set(listed) == actual)
    return checks


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_heads(path: Path) -> dict[str, str]:
    return {
        name: value
        for line in path.read_text(encoding="ascii").splitlines()
        if "=" in line
        for name, value in [line.split("=", 1)]
    }


def _eight_booleans(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 8
        and all(isinstance(item, bool) for item in value)
    )


def _finite_atom_matrix(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 8
        and all(
            isinstance(row, list)
            and len(row) == 14
            and all(
                not isinstance(item, bool)
                and isinstance(item, (int, float))
                and math.isfinite(float(item))
                for item in row
            )
            for row in value
        )
    )


def _authoritative_boundary_checks(
    checks: list[dict[str, Any]], payload: Mapping[str, Any], prefix: str
) -> None:
    _check(checks, f"{prefix}_tuning_closed", payload.get("tuning_executed") is False)
    _check(
        checks,
        f"{prefix}_calibration_closed",
        payload.get("calibration_accessed") is False,
    )
    _check(checks, f"{prefix}_holdout_closed", payload.get("holdout_opened") is False)
    _check(
        checks,
        f"{prefix}_outcomes_closed",
        payload.get("outcome_fields_consumed") == [],
    )
    _check(checks, f"{prefix}_claim_closed", payload.get("claim_authorized") is False)


def review_pilot(
    pilot_root: Path,
    expected_root_sha256: str,
    corpus_preflight_root: Path,
    expected_corpus_preflight_root_sha256: str,
    expected_route_count: int = 375,
) -> dict[str, Any]:
    """Independently review a sealed v24 seed-24001 pilot without modifying it."""
    pilot_root = Path(pilot_root).resolve()
    corpus_preflight_root = Path(corpus_preflight_root).resolve()
    checks = _verify_seal(pilot_root, expected_root_sha256, "pilot")
    checks.extend(
        _verify_seal(
            corpus_preflight_root,
            expected_corpus_preflight_root_sha256,
            "corpus_preflight",
        )
    )
    warnings: list[str] = []
    stale_progress = False
    recomputed: dict[str, Any] = {
        "failure_reason_counts": {},
        "receipt_count_by_source_map_sha256": {},
        "snapshot_count_by_source_map_sha256": {},
    }
    route_order: list[str] = []

    try:
        manifest = _read_json(corpus_preflight_root / "corpus_manifest.json")
        state = _read_json(pilot_root / "STATE.json")
        summary = _read_json(pilot_root / "pilot_summary.json")
        execution = _read_json(pilot_root / "execution.json")
        progress = _read_json(pilot_root / "progress.json")
        heads = _parse_heads(pilot_root / "HEADS")

        routes = manifest.get("routes", [])
        _check(checks, "manifest_schema", manifest.get("schema") == "camp_dp_v24_native_corpus_manifest_v1")
        _check(checks, "manifest_train_only", manifest.get("split") == "train")
        _check(checks, "manifest_train_seeds", manifest.get("seeds") == TRAIN_SEEDS)
        _check(checks, "manifest_outcomes_closed", manifest.get("outcome_fields_consumed") == [])
        _check(checks, "manifest_calibration_closed", manifest.get("calibration_accessed") is False)
        _check(checks, "manifest_holdout_closed", manifest.get("holdout_opened") is False)
        _check(
            checks,
            "manifest_route_denominator",
            manifest.get("route_count") == expected_route_count
            and isinstance(routes, list)
            and len(routes) == expected_route_count,
        )
        route_by_identity = {
            str(route["identity_sha256"]): route
            for route in routes
            if isinstance(route, Mapping) and "identity_sha256" in route
        }
        record_keys = [str(route.get("record_key")) for route in routes]
        route_order = record_keys
        _check(checks, "manifest_route_identities_unique", len(route_by_identity) == expected_route_count)
        _check(checks, "manifest_record_keys_unique", len(set(record_keys)) == expected_route_count)
        _check(
            checks,
            "manifest_route_seed_namespace",
            all(route.get("seeds") == TRAIN_SEEDS for route in routes),
        )

        expected_receipt_paths = {
            f"receipts/train/{identity}/seed_{PILOT_SEED}.json"
            for identity in route_by_identity
        }
        actual_receipt_paths = {
            path.relative_to(pilot_root).as_posix()
            for path in (pilot_root / "receipts").rglob("*")
            if path.is_file()
        }
        _check(
            checks,
            "receipt_semantic_inventory_exact",
            actual_receipt_paths == expected_receipt_paths,
        )
        receipt_paths = sorted(pilot_root / relative for relative in expected_receipt_paths)
        receipts = [_read_json(path) for path in receipt_paths]
        receipt_by_identity = {
            str(receipt.get("route_identity_sha256")): receipt for receipt in receipts
        }
        _check(checks, "receipt_denominator_exact", len(receipts) == expected_route_count)
        _check(checks, "receipt_route_identities_unique", len(receipt_by_identity) == expected_route_count)
        _check(checks, "receipt_manifest_membership_exact", set(receipt_by_identity) == set(route_by_identity))

        failure_reasons: Counter[str] = Counter()
        receipt_source_maps: Counter[str] = Counter()
        snapshot_source_maps: Counter[str] = Counter()
        snapshot_references: Counter[str] = Counter()
        complete = 0
        failed = 0
        for identity, receipt in receipt_by_identity.items():
            route = route_by_identity.get(identity, {})
            prefix = f"receipt:{identity}"
            status = receipt.get("status")
            cause_valid = (
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
            _check(checks, f"{prefix}:schema", receipt.get("schema") == "camp_dp_v24_native_corpus_pilot_run_receipt_v1")
            _check(checks, f"{prefix}:status_cause", status in {"ok", "failed"} and cause_valid)
            _check(checks, f"{prefix}:retained", receipt.get("retained_in_denominator") is True)
            _check(
                checks,
                f"{prefix}:identity",
                receipt.get("split") == "train"
                and receipt.get("seed") == PILOT_SEED
                and receipt.get("phase") == "capability_pilot_all_train_routes_first_seed"
                and receipt.get("record_key") == route.get("record_key")
                and receipt.get("map_family_id") == route.get("map_family_id")
                and receipt.get("logical_map_sha256") == route.get("logical_map_sha256")
                and receipt.get("corridor_group_sha256") == route.get("corridor_group_sha256")
                and receipt.get("route_identity_sha256") == route.get("identity_sha256"),
            )
            snapshots = receipt.get("snapshot_sha256", [])
            _check(
                checks,
                f"{prefix}:snapshot_receipts",
                isinstance(snapshots, list)
                and len(snapshots) == len(set(snapshots))
                and all(_is_sha256(value) for value in snapshots),
            )
            snapshot_references.update(snapshots if isinstance(snapshots, list) else [])
            source_map_sha = str(route.get("source_map_sha256"))
            receipt_source_maps[source_map_sha] += 1
            complete += int(status == "ok")
            failed += int(status == "failed")
            if status == "failed":
                failure_reasons[str(receipt.get("failure_reason"))] += 1

        snapshot_root = pilot_root / "snapshots"
        snapshot_tree_files = sorted(
            path for path in snapshot_root.rglob("*") if path.is_file()
        )
        _check(
            checks,
            "snapshot_semantic_inventory_exact",
            all(
                path.parent == snapshot_root
                and path.suffix == ".json"
                and _is_sha256(path.stem)
                for path in snapshot_tree_files
            ),
        )
        snapshot_paths = [
            path
            for path in snapshot_tree_files
            if path.parent == snapshot_root
            and path.suffix == ".json"
            and _is_sha256(path.stem)
        ]
        snapshot_by_digest = {path.stem: path for path in snapshot_paths}
        _check(checks, "snapshot_filenames_unique", len(snapshot_by_digest) == len(snapshot_paths))
        _check(checks, "snapshot_reference_membership_exact", set(snapshot_references) == set(snapshot_by_digest))
        _check(
            checks,
            "snapshot_each_belongs_to_one_receipt",
            all(count == 1 for count in snapshot_references.values()),
        )
        all_k_high_risk = 0
        strata: Counter[str] = Counter()
        for digest, path in snapshot_by_digest.items():
            prefix = f"snapshot:{digest}"
            _check(checks, f"{prefix}:digest", _is_sha256(digest) and _file_sha256(path) == digest)
            payload = _read_json(path)
            features = payload.get("feature_payload", {})
            sidecar = payload.get("sidecar", {})
            rows = features.get("candidate_row_sha256", []) if isinstance(features, Mapping) else []
            identity = sidecar.get("default_candidate0_identity", {}) if isinstance(sidecar, Mapping) else {}
            route_identity = str(sidecar.get("route_identity_sha256"))
            route = route_by_identity.get(route_identity, {})
            owner = receipt_by_identity.get(route_identity, {})
            _check(checks, f"{prefix}:schema", payload.get("schema_version") == "v22_native_decision_snapshot_v1")
            _check(
                checks,
                f"{prefix}:feature_fields",
                isinstance(features, Mapping)
                and len(features) == len(FEATURE_FIELDS)
                and set(features) == set(FEATURE_FIELDS),
            )
            _check(checks, f"{prefix}:feature_identity_absent", isinstance(features, Mapping) and not IDENTITY_FIELDS.intersection(features))
            _check(checks, f"{prefix}:atoms", isinstance(features, Mapping) and _finite_atom_matrix(features.get("atom_matrix")))
            _check(checks, f"{prefix}:source_mask", isinstance(features, Mapping) and _eight_booleans(features.get("source_valid_mask")))
            _check(checks, f"{prefix}:physical_mask", isinstance(sidecar, Mapping) and _eight_booleans(sidecar.get("physical_feasible_mask")))
            _check(checks, f"{prefix}:row_hashes", isinstance(rows, list) and len(rows) == 8 and all(_is_sha256(value) for value in rows))
            before = sidecar.get("candidate_tensor_sha256_before")
            _check(checks, f"{prefix}:candidate_tensor_identity", _is_sha256(before) and before == sidecar.get("candidate_tensor_sha256_after"))
            _check(checks, f"{prefix}:causal_sha", _is_sha256(sidecar.get("causal_input_sha256")))
            candidate0 = rows[0] if isinstance(rows, list) and rows else None
            _check(
                checks,
                f"{prefix}:candidate0_default_identity",
                _is_sha256(candidate0)
                and sidecar.get("candidate0_sha256") == candidate0
                and sidecar.get("default_output_sha256") == candidate0
                and isinstance(identity, Mapping)
                and identity.get("elementwise_equal") is True
                and identity.get("max_abs_difference") == 0.0
                and identity.get("candidate0_sha256") == candidate0
                and identity.get("default_output_sha256") == candidate0
                and identity.get("native_ranked_k8") is False,
            )
            _check(
                checks,
                f"{prefix}:receipt_sidecar_identity",
                digest in owner.get("snapshot_sha256", [])
                and sidecar.get("split") == owner.get("split") == "train"
                and sidecar.get("seed") == owner.get("seed") == PILOT_SEED
                and sidecar.get("record_key") == owner.get("record_key") == route.get("record_key")
                and sidecar.get("map_family_id") == owner.get("map_family_id") == route.get("map_family_id")
                and sidecar.get("logical_map_sha256") == owner.get("logical_map_sha256") == route.get("logical_map_sha256")
                and sidecar.get("route_identity_sha256") == owner.get("route_identity_sha256") == route.get("identity_sha256")
                and sidecar.get("corridor_group_sha256") == owner.get("corridor_group_sha256") == route.get("corridor_group_sha256")
                and sidecar.get("group_sha256") == route.get("corridor_group_sha256")
                and sidecar.get("source_stratum") == route.get("source_stratum"),
            )
            source_map_sha = str(route.get("source_map_sha256"))
            snapshot_source_maps[source_map_sha] += 1
            all_k_high_risk += int(bool(sidecar.get("all_k_high_risk")))
            active = [
                str(name)
                for name, enabled in sidecar.get("source_stratum", {}).items()
                if enabled
            ] or ["normal"]
            strata.update(active)

        aggregate = {
            "planned_route_seed_runs": expected_route_count,
            "complete_route_seed_runs": complete,
            "failed_route_seed_runs": failed,
            "retained_route_seed_runs": len(receipts),
            "pending_route_seed_runs": expected_route_count - len(receipts),
            "route_coverage": len(receipts) / expected_route_count if expected_route_count else 0.0,
            "snapshot_count": len(snapshot_paths),
            "snapshot_count_by_source_stratum": dict(sorted(strata.items())),
            "all_k_high_risk_snapshot_count": all_k_high_risk,
        }
        terminal_status = "complete_with_retained_failures" if failed else "complete"
        expected_protocol = {
            "phase": "capability_pilot_all_train_routes_first_seed",
            "corpus_steps": 64,
            "sample_every_ticks": 1,
            "theoretical_max_snapshots": expected_route_count * 64,
        }
        for prefix, payload in (("summary", summary), ("execution", execution)):
            _check(
                checks,
                f"{prefix}_aggregate",
                all(payload.get(name) == value for name, value in aggregate.items()),
            )
            _check(checks, f"{prefix}_status", payload.get("status") == terminal_status)
            _check(checks, f"{prefix}_schema", payload.get("schema") == "camp_dp_v24_native_corpus_pilot_summary_v1")
            _check(checks, f"{prefix}_seed", payload.get("seed") == PILOT_SEED)
            _check(
                checks,
                f"{prefix}_protocol",
                all(payload.get(name) == value for name, value in expected_protocol.items()),
            )
            _check(checks, f"{prefix}_denominator_retained", payload.get("all_routes_retained_in_denominator") is True)
            _check(checks, f"{prefix}_disk_recorded", float(payload.get("free_disk_gib", 0.0)) > 10.0)
            _authoritative_boundary_checks(checks, payload, prefix)
        _check(checks, "summary_execution_consistency", all(execution.get(name) == summary.get(name) for name in summary))
        _check(checks, "state_terminal", state.get("status") == terminal_status and state.get("seed") == PILOT_SEED)
        _check(checks, "execution_source_preflight", execution.get("source_preflight_root_sha256") == expected_corpus_preflight_root_sha256)
        _check(checks, "execution_fixed_dp", execution.get("fixed_dp_head") == FIXED_DP_HEAD)
        _check(checks, "heads_camp", GIT_HEAD_PATTERN.fullmatch(heads.get("CAMP_HEAD", "")) is not None)
        _check(checks, "heads_fixed_dp", heads.get("FIXED_DP_HEAD") == FIXED_DP_HEAD)
        _check(checks, "heads_source_preflight", heads.get("SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256") == expected_corpus_preflight_root_sha256)
        _check(checks, "progress_schema", progress.get("schema") == "camp_dp_v24_native_corpus_pilot_progress_v1")
        _check(checks, "progress_aggregate", all(progress.get(name) == value for name, value in aggregate.items()))
        _check(checks, "progress_completed_rows", progress.get("last_completed_row") == expected_route_count)
        _check(checks, "progress_disk_recorded", float(progress.get("free_disk_gib", 0.0)) > 10.0)
        if progress.get("status") == "running" and terminal_status.startswith("complete"):
            stale_progress = True
        else:
            _check(checks, "progress_terminal_status", progress.get("status") == terminal_status)
        free_bytes = shutil.disk_usage(pilot_root).free
        _check(checks, "disk_floor", free_bytes > MINIMUM_FREE_BYTES)
        recomputed.update(
            {
                **aggregate,
                "failure_reason_counts": dict(sorted(failure_reasons.items())),
                "receipt_count_by_source_map_sha256": dict(sorted(receipt_source_maps.items())),
                "snapshot_count_by_source_map_sha256": dict(sorted(snapshot_source_maps.items())),
                "free_disk_gib": free_bytes / (1024**3),
            }
        )
    except Exception as exc:
        _check(checks, f"review_input_valid:{type(exc).__name__}", False)

    failed_checks = [check["name"] for check in checks if not check["passed"]]
    authoritative_passed = not failed_checks
    if authoritative_passed and stale_progress:
        warnings.append("progress_terminal_status_stale_running")
    decision = {
        "authorized": authoritative_passed,
        "action": "execute_frozen_remaining_train_seeds" if authoritative_passed else "stop_failed_review",
        "seeds": REMAINING_TRAIN_SEEDS if authoritative_passed else [],
        "route_count": expected_route_count,
        "route_order": route_order if authoritative_passed else [],
        "preserve_all_failures_and_denominator": authoritative_passed,
        "route_removal_replacement_reordering_authorized": False,
        "tuning_authorized": False,
        "outcome_access_authorized": False,
        "calibration_access_authorized": False,
        "holdout_access_authorized": False,
        "claim_authorized": False,
    }
    status = "failed" if failed_checks else ("passed_with_warning" if warnings else "passed")
    return {
        "schema": "camp_dp_v24_native_corpus_pilot_independent_review_v1",
        "status": status,
        "source_pilot_root_sha256": expected_root_sha256,
        "source_corpus_preflight_root_sha256": expected_corpus_preflight_root_sha256,
        "check_count": len(checks),
        "failed_count": len(failed_checks),
        "failed_checks": failed_checks,
        "checks": checks,
        "warning_count": len(warnings),
        "warnings": warnings,
        "recomputed": recomputed,
        "decision": decision,
        "review_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha256 = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha256}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha256


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--expected-root-sha256", required=True)
    parser.add_argument("--corpus-preflight-root", type=Path, required=True)
    parser.add_argument("--expected-corpus-preflight-root-sha256", required=True)
    parser.add_argument("--expected-route-count", type=int, default=375)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    review = review_pilot(
        args.pilot_root,
        args.expected_root_sha256,
        args.corpus_preflight_root,
        args.expected_corpus_preflight_root_sha256,
        args.expected_route_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_PILOT_ROOT_SHA256={args.expected_root_sha256}\n"
        f"SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256={args.expected_corpus_preflight_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 native corpus pilot independent review\n", encoding="utf-8"
    )
    _write_json(args.output_dir / "review.json", review)
    (args.output_dir / "review.md").write_text(
        "# v24 native corpus pilot independent review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed / warnings: `{review['check_count']} / "
        f"{review['failed_count']} / {review['warning_count']}`\n"
        f"- next seeds authorized: `{review['decision']['seeds']}`\n"
        "- model/candidates/train/tune/outcomes/calibration/holdout/claim: "
        "`false/false/false/false/false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(review, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    success = review["status"] in {"passed", "passed_with_warning"}
    (args.output_dir / "run.exit").write_text("0\n" if success else "1\n", encoding="ascii")
    root_sha256 = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha256,
                "status": review["status"],
                "check_count": review["check_count"],
                "failed_count": review["failed_count"],
                "warning_count": review["warning_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
