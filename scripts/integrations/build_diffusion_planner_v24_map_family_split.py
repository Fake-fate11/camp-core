from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


PRIMARY_SEEDS = (24001, 24002, 24003, 24004, 24005)
SPLITS = ("train", "calibration", "holdout")
TARGET_RATIOS = {"train": 0.70, "calibration": 0.10, "holdout": 0.20}
EXPECTED_FAMILY_COUNTS = {
    "map_family_d7f16a17d3eb": 375,
    "map_family_f62e06cd1303": 2,
    "map_family_828a913c2f9a": 24,
}
EXPECTED_ASSIGNMENTS = {
    "map_family_d7f16a17d3eb": "train",
    "map_family_f62e06cd1303": "calibration",
    "map_family_828a913c2f9a": "holdout",
}


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_source_only_census(census: Mapping[str, Any]) -> None:
    required = {
        "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
    }
    for name, expected in required.items():
        if census.get(name) != expected:
            raise ValueError(f"route census boundary mismatch: {name}")
    corridor = census.get("corridor_groups")
    if not isinstance(corridor, Mapping):
        raise ValueError("corridor groups are missing")
    if corridor.get("source_only") is not True:
        raise ValueError("corridor groups are not source-only")
    if corridor.get("outcome_fields_consumed") != []:
        raise ValueError("corridor grouping consumed outcome fields")


def _corridor_membership(
    routes: list[Mapping[str, Any]], corridor: Mapping[str, Any]
) -> tuple[dict[str, str], Counter[str]]:
    family_by_key = {str(route["record_key"]): str(route["map_family_id"]) for route in routes}
    if len(family_by_key) != len(routes):
        raise ValueError("route record keys are not unique")
    membership: dict[str, str] = {}
    family_group_counts: Counter[str] = Counter()
    for group in corridor.get("groups", []):
        group_sha = str(group["group_sha256"])
        keys = [str(value) for value in group["route_record_keys"]]
        if int(group["route_record_count"]) != len(keys):
            raise ValueError("corridor group count mismatch")
        families = {family_by_key.get(key) for key in keys}
        if None in families or len(families) != 1:
            raise ValueError("corridor group crosses a map family")
        family = next(iter(families))
        family_group_counts[family] += 1
        for key in keys:
            if key in membership:
                raise ValueError("route appears in multiple corridor groups")
            membership[key] = group_sha
    if set(membership) != set(family_by_key):
        raise ValueError("corridor groups do not cover the route denominator")
    return membership, family_group_counts


def _choose_assignment(family_counts: Mapping[str, int]) -> dict[str, str]:
    families = sorted(family_counts)
    if len(families) < 3:
        raise ValueError("map-family split requires at least three supporting families")
    total = sum(family_counts.values())
    targets = {name: ratio * total for name, ratio in TARGET_RATIOS.items()}
    best: tuple[Any, ...] | None = None
    best_assignment: dict[str, str] | None = None
    for choices in itertools.product(SPLITS, repeat=len(families)):
        if set(choices) != set(SPLITS):
            continue
        assignment = dict(zip(families, choices))
        counts = {
            split: sum(
                family_counts[family]
                for family, assigned in assignment.items()
                if assigned == split
            )
            for split in SPLITS
        }
        objective = (
            sum(abs(counts[name] - targets[name]) for name in SPLITS),
            abs(counts["holdout"] - targets["holdout"]),
            -counts["train"],
            choices,
        )
        if best is None or objective < best:
            best = objective
            best_assignment = assignment
    if best_assignment is None:
        raise ValueError("no nonempty family split exists")
    return best_assignment


def build_split_plan(census: Mapping[str, Any]) -> dict[str, Any]:
    _require_source_only_census(census)
    routes = list(census.get("retained_routes", []))
    if not routes:
        raise ValueError("route census is empty")
    identities = [
        (str(route["map_family_id"]), str(route["identity_sha256"])) for route in routes
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("route identities are not unique within map family")
    corridor = census["corridor_groups"]
    membership, family_group_counts = _corridor_membership(routes, corridor)
    family_counts = Counter(str(route["map_family_id"]) for route in routes)
    assignments = _choose_assignment(family_counts)
    route_counts = {
        split: sum(
            count
            for family, count in family_counts.items()
            if assignments[family] == split
        )
        for split in SPLITS
    }
    logical_names: dict[str, list[str]] = defaultdict(list)
    for route in routes:
        name = str(route.get("logical_map_name", ""))
        family = str(route["map_family_id"])
        if name and name not in logical_names[family]:
            logical_names[family].append(name)
    plan: dict[str, Any] = {
        "schema": "camp_dp_v24_map_family_split_plan_v1",
        "assignment_rule": (
            "minimum_route_count_l1_70_10_20_then_holdout_distance_"
            "then_larger_train_then_lexicographic"
        ),
        "target_ratios": dict(TARGET_RATIOS),
        "family_assignments": dict(sorted(assignments.items())),
        "family_route_counts": dict(sorted(family_counts.items())),
        "family_corridor_group_counts": dict(sorted(family_group_counts.items())),
        "family_logical_map_names": {
            family: sorted(names) for family, names in sorted(logical_names.items())
        },
        "route_counts": route_counts,
        "route_seed_counts": {
            split: count * len(PRIMARY_SEEDS) for split, count in route_counts.items()
        },
        "route_count": len(routes),
        "corridor_group_count": len(corridor["groups"]),
        "supporting_family_count": len(family_counts),
        "primary_seeds": list(PRIMARY_SEEDS),
        "pilot_seed": PRIMARY_SEEDS[0],
        "seed_count": len(PRIMARY_SEEDS),
        "corridor_membership_count": len(membership),
        "outcome_fields_consumed": [],
        "model_loaded": False,
        "candidate_generation_started": False,
        "holdout_opened": False,
        "formal_split_manifest_materialized": False,
        "claim_authorized": False,
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def build_split_manifest(
    census: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    routes = list(census["retained_routes"])
    membership, _ = _corridor_membership(routes, census["corridor_groups"])
    assignments = plan["family_assignments"]
    records = [
        {
            "record_key": str(route["record_key"]),
            "identity_sha256": str(route["identity_sha256"]),
            "map_family_id": str(route["map_family_id"]),
            "corridor_group_sha256": membership[str(route["record_key"])],
            "split": str(assignments[str(route["map_family_id"])]),
            "seeds": list(PRIMARY_SEEDS),
        }
        for route in routes
    ]
    records.sort(key=lambda item: item["record_key"])
    manifest = {
        "schema": "camp_dp_v24_map_family_split_manifest_v1",
        "plan_sha256": str(plan["plan_sha256"]),
        "family_assignments": dict(plan["family_assignments"]),
        "primary_seeds": list(PRIMARY_SEEDS),
        "pilot_seed": PRIMARY_SEEDS[0],
        "records": records,
        "route_count": len(records),
        "route_seed_count": len(records) * len(PRIMARY_SEEDS),
        "outcome_fields_consumed": [],
        "holdout_opened": False,
        "claim_authorized": False,
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return manifest


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_root_checks(root: Path, expected_root_sha256: str) -> list[dict[str, Any]]:
    manifest = root / "SHA256SUMS"
    checks = [
        {"name": "source_manifest_exists", "passed": manifest.is_file()},
        {
            "name": "source_root_sha256",
            "passed": manifest.is_file()
            and _file_sha256(manifest) == expected_root_sha256,
        },
    ]
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = root / relative
            checks.append(
                {
                    "name": f"source_sha:{relative}",
                    "passed": path.is_file() and _file_sha256(path) == digest,
                }
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
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--route-census", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-source-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    census = json.loads(args.route_census.read_text(encoding="utf-8"))
    plan = build_split_plan(census)
    checks = _source_root_checks(args.source_root, args.expected_source_root_sha256)
    checks.extend(
        [
            {"name": "route_count_401", "passed": plan["route_count"] == 401},
            {
                "name": "corridor_group_count_5",
                "passed": plan["corridor_group_count"] == 5,
            },
            {
                "name": "supporting_family_count_3",
                "passed": plan["supporting_family_count"] == 3,
            },
            {
                "name": "family_counts",
                "passed": plan["family_route_counts"] == EXPECTED_FAMILY_COUNTS,
            },
            {
                "name": "family_assignments",
                "passed": plan["family_assignments"] == EXPECTED_ASSIGNMENTS,
            },
            {
                "name": "route_counts",
                "passed": plan["route_counts"]
                == {"train": 375, "calibration": 2, "holdout": 24},
            },
            {
                "name": "route_seed_counts",
                "passed": plan["route_seed_counts"]
                == {"train": 1875, "calibration": 10, "holdout": 120},
            },
            {"name": "outcomes_closed", "passed": plan["outcome_fields_consumed"] == []},
            {"name": "holdout_closed", "passed": plan["holdout_opened"] is False},
        ]
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    mode = "preflight" if args.preflight else "execute"
    if args.execute:
        manifest = build_split_manifest(census, plan)
        _write_json(args.output_dir / "split_manifest.json", manifest)
    result = {
        "schema": "camp_dp_v24_map_family_split_gate_v1",
        "mode": mode,
        "status": "passed" if not failed else "failed",
        "source_root_sha256": args.expected_source_root_sha256,
        "route_census_sha256": _file_sha256(args.route_census),
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "plan": plan,
        "formal_split_manifest_materialized": bool(args.execute),
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"SOURCE_ROUTE_CENSUS_ROOT_SHA256={args.expected_source_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        f"v24 map-family split {mode} from sealed route census\n", encoding="utf-8"
    )
    _write_json(args.output_dir / f"{mode}.json", result)
    (args.output_dir / f"{mode}.md").write_text(
        f"# v24 map-family split {mode}\n\n"
        f"- status: `{result['status']}`\n"
        f"- checks / failed: `{result['check_count']} / {result['failed_count']}`\n"
        "- routes train/calibration/holdout: `375 / 2 / 24`\n"
        "- primary seeds: `5`\n"
        "- model/candidates/outcomes/holdout: `false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text(
        "0\n" if result["status"] == "passed" else "1\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "mode": mode,
                "status": result["status"],
                "check_count": result["check_count"],
                "failed_count": result["failed_count"],
                "plan_sha256": plan["plan_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
