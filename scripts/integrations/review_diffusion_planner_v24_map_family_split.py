from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SPLITS = ("train", "calibration", "holdout")
SEED_NAMESPACES = {
    "train": (24001, 24002, 24003, 24004, 24005),
    "calibration": (24101, 24102, 24103, 24104, 24105),
    "holdout": (24201, 24202, 24203, 24204, 24205),
}
EXPECTED_PLAN_SHA256 = (
    "52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539"
)


def _check(name: str, passed: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _canonical_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_split(
    census: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    source_routes = list(census.get("retained_routes", []))
    records = list(manifest.get("records", []))
    source_by_key = {str(route["record_key"]): route for route in source_routes}
    manifest_by_key = {str(record["record_key"]): record for record in records}

    corridor_by_key: dict[str, str] = {}
    for group in census.get("corridor_groups", {}).get("groups", []):
        for key in group["route_record_keys"]:
            if str(key) in corridor_by_key:
                raise ValueError("source route appears in multiple corridor groups")
            corridor_by_key[str(key)] = str(group["group_sha256"])

    split_keys: dict[str, set[str]] = {name: set() for name in SPLITS}
    split_identities: dict[str, set[str]] = {name: set() for name in SPLITS}
    split_families: dict[str, set[str]] = {name: set() for name in SPLITS}
    split_corridors: dict[str, set[str]] = {name: set() for name in SPLITS}
    split_route_seeds: dict[str, set[tuple[str, int]]] = {
        name: set() for name in SPLITS
    }
    for record in records:
        split = str(record.get("split"))
        if split not in split_keys:
            continue
        key = str(record["record_key"])
        family = str(record["map_family_id"])
        identity = f"{family}:{record['identity_sha256']}"
        corridor = str(record["corridor_group_sha256"])
        split_keys[split].add(key)
        split_identities[split].add(identity)
        split_families[split].add(family)
        split_corridors[split].add(corridor)
        for seed in record.get("seeds", []):
            split_route_seeds[split].add((key, int(seed)))

    def pairwise_disjoint(values: Mapping[str, set[Any]]) -> bool:
        return all(
            not values[left] & values[right]
            for index, left in enumerate(SPLITS)
            for right in SPLITS[index + 1 :]
        )

    exact_source_fields = all(
        key in source_by_key
        and str(record["map_family_id"])
        == str(source_by_key[key]["map_family_id"])
        and str(record["identity_sha256"])
        == str(source_by_key[key]["identity_sha256"])
        and str(record["corridor_group_sha256"]) == corridor_by_key.get(key)
        for key, record in manifest_by_key.items()
    )
    family_splits: dict[str, set[str]] = defaultdict(set)
    corridor_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        family_splits[str(record["map_family_id"])].add(str(record["split"]))
        corridor_splits[str(record["corridor_group_sha256"])].add(
            str(record["split"])
        )
    assignments = manifest.get("family_assignments", {})
    assignments_match = all(
        len(splits) == 1 and assignments.get(family) == next(iter(splits))
        for family, splits in family_splits.items()
    )

    route_counts = {name: len(split_keys[name]) for name in SPLITS}
    route_seed_counts = {name: len(split_route_seeds[name]) for name in SPLITS}
    observed_seed_namespaces = {
        split: {
            int(seed)
            for record in records
            if record.get("split") == split
            for seed in record.get("seeds", [])
        }
        for split in SPLITS
    }
    seed_namespace_zero_overlap = pairwise_disjoint(observed_seed_namespaces)
    checks = [
        _check(
            "source_schema",
            census.get("schema")
            == "diffusion_planner_v24_outcome_blind_route_census_v1",
        ),
        _check("source_complete", census.get("route_census_completed") is True),
        _check("source_outcomes_closed", census.get("outcome_accessed") is False),
        _check("source_holdout_closed", census.get("holdout_opened") is False),
        _check(
            "manifest_schema",
            manifest.get("schema") == "camp_dp_v24_map_family_split_manifest_v1",
        ),
        _check(
            "manifest_sha256",
            manifest.get("manifest_sha256") == _canonical_manifest_sha256(manifest),
        ),
        _check(
            "plan_sha256",
            isinstance(manifest.get("plan_sha256"), str)
            and len(str(manifest["plan_sha256"])) == 64,
        ),
        _check("source_route_keys_unique", len(source_by_key) == len(source_routes)),
        _check("manifest_route_keys_unique", len(manifest_by_key) == len(records)),
        _check("full_route_denominator", set(manifest_by_key) == set(source_by_key)),
        _check("full_corridor_denominator", set(corridor_by_key) == set(source_by_key)),
        _check("exact_source_fields", exact_source_fields),
        _check("all_splits_nonempty", all(split_keys[name] for name in SPLITS)),
        _check("family_assignments_match", assignments_match),
        _check("families_indivisible", all(len(values) == 1 for values in family_splits.values())),
        _check("corridors_indivisible", all(len(values) == 1 for values in corridor_splits.values())),
        _check("route_keys_zero_overlap", pairwise_disjoint(split_keys)),
        _check("route_identities_zero_overlap", pairwise_disjoint(split_identities)),
        _check("families_zero_overlap", pairwise_disjoint(split_families)),
        _check("corridors_zero_overlap", pairwise_disjoint(split_corridors)),
        _check("route_seed_zero_overlap", pairwise_disjoint(split_route_seeds)),
        _check("seed_namespace_zero_overlap", seed_namespace_zero_overlap),
        _check(
            "every_route_has_five_frozen_seeds",
            all(
                record.get("seeds") == list(SEED_NAMESPACES.get(record.get("split"), ()))
                for record in records
            ),
        ),
        _check("route_count_field", manifest.get("route_count") == len(records)),
        _check(
            "route_seed_count_field",
            manifest.get("route_seed_count")
            == len(records) * len(SEED_NAMESPACES["train"]),
        ),
        _check("manifest_outcomes_closed", manifest.get("outcome_fields_consumed") == []),
        _check("manifest_holdout_closed", manifest.get("holdout_opened") is False),
        _check("manifest_claim_closed", manifest.get("claim_authorized") is False),
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "route_counts": route_counts,
        "route_seed_counts": route_seed_counts,
        "family_counts": {name: len(split_families[name]) for name in SPLITS},
        "corridor_group_counts": {
            name: len(split_corridors[name]) for name in SPLITS
        },
        "route_count": len(records),
        "route_seed_count": sum(route_seed_counts.values()),
        "zero_overlap": all(
            pairwise_disjoint(values)
            for values in (
                split_keys,
                split_identities,
                split_families,
                split_corridors,
                split_route_seeds,
            )
        ),
        "seed_namespace_zero_overlap": seed_namespace_zero_overlap,
        "manifest_sha256": manifest.get("manifest_sha256"),
        "plan_sha256": manifest.get("plan_sha256"),
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_manifest(root: Path, expected_root_sha256: str) -> list[dict[str, Any]]:
    root = root.resolve()
    manifest = root / "SHA256SUMS"
    checks = [
        _check("manifest_exists", manifest.is_file()),
        _check(
            "root_sha256",
            manifest.is_file() and _file_sha256(manifest) == expected_root_sha256,
        ),
    ]
    if not manifest.is_file():
        return checks
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
            contained = True
        except ValueError:
            contained = False
        checks.append(_check(f"manifest_contained:{relative}", contained))
        checks.append(
            _check(
                f"manifest_sha:{relative}",
                contained and path.is_file() and _file_sha256(path) == digest,
            )
        )
    return checks


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
    root_sha = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--expected-execution-root-sha256", required=True)
    parser.add_argument("--source-census", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-source-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    execution_checks = _verify_manifest(
        args.execution_root, args.expected_execution_root_sha256
    )
    source_checks = _verify_manifest(args.source_root, args.expected_source_root_sha256)
    census = json.loads(args.source_census.read_text(encoding="utf-8"))
    manifest = json.loads(
        (args.execution_root / "split_manifest.json").read_text(encoding="utf-8")
    )
    review = evaluate_split(census, manifest)
    all_checks = execution_checks + source_checks + review.pop("checks")
    all_checks.append(
        _check("expected_plan_sha256", manifest.get("plan_sha256") == EXPECTED_PLAN_SHA256)
    )
    failed = [check["name"] for check in all_checks if not check["passed"]]
    review.update(
        {
            "schema": "camp_dp_v24_map_family_split_independent_review_v1",
            "status": "passed" if not failed else "failed",
            "check_count": len(all_checks),
            "failed_count": len(failed),
            "failed_checks": failed,
            "checks": all_checks,
            "source_execution_artifact": str(args.execution_root.resolve()),
            "source_execution_root_sha256": args.expected_execution_root_sha256,
            "source_census_root_sha256": args.expected_source_root_sha256,
            "split_reexecuted": False,
        }
    )
    (args.output_dir / "COMMAND").write_text(
        "independent read-only v24 map-family split review\n", encoding="utf-8"
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_EXECUTION_ROOT_SHA256={args.expected_execution_root_sha256}\n"
        f"SOURCE_CENSUS_ROOT_SHA256={args.expected_source_root_sha256}\n",
        encoding="ascii",
    )
    _write_json(args.output_dir / "review.json", review)
    (args.output_dir / "review.md").write_text(
        "# v24 map-family split independent review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed: `{review['check_count']} / {review['failed_count']}`\n"
        "- routes train/calibration/holdout: "
        f"`{review['route_counts']['train']} / "
        f"{review['route_counts']['calibration']} / "
        f"{review['route_counts']['holdout']}`\n"
        f"- zero overlap: `{str(review['zero_overlap']).lower()}`\n"
        "- split/model/candidates/outcomes/holdout: `false/false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(review, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text(
        "0\n" if review["status"] == "passed" else "1\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "status": review["status"],
                "check_count": review["check_count"],
                "failed_count": review["failed_count"],
                "zero_overlap": review["zero_overlap"],
            },
            sort_keys=True,
        )
    )
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
