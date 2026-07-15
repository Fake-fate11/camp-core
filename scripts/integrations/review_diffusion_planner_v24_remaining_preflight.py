#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.review_diffusion_planner_v24_native_corpus import (
    FIXED_DP_HEAD,
    TRAIN_SEEDS,
    build_expected_run_config,
    file_sha256,
)


REMAINING_SEEDS = tuple(TRAIN_SEEDS[1:])
SOURCE_INVALID_REASON = "ValueError: route slot 0 requires a positive speed limit"
MINIMUM_FREE_GIB = 10.0


def _check(checks: list[dict[str, Any]], name: str, passed: Any) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _sealed_root_checks(
    root: Path, expected_root_sha256: str, prefix: str
) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    manifest = root / "SHA256SUMS"
    root_receipt = root / "ROOT_SHA256SUMS"
    checks: list[dict[str, Any]] = []
    _check(checks, f"{prefix}:manifest_exists", manifest.is_file())
    _check(checks, f"{prefix}:root_receipt_exists", root_receipt.is_file())
    if not manifest.is_file():
        return checks
    _check(
        checks,
        f"{prefix}:root_sha256",
        file_sha256(manifest) == expected_root_sha256,
    )
    _check(
        checks,
        f"{prefix}:root_receipt",
        root_receipt.is_file()
        and root_receipt.read_text(encoding="ascii")
        == f"{expected_root_sha256}  SHA256SUMS\n",
    )
    listed: dict[str, str] = {}
    manifest_valid = True
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            digest, relative = line.split("  ", 1)
        except ValueError:
            manifest_valid = False
            continue
        if relative in listed:
            manifest_valid = False
            continue
        listed[relative] = digest
    _check(checks, f"{prefix}:manifest_syntax_unique", manifest_valid)
    expected_files = {"SHA256SUMS", "ROOT_SHA256SUMS", *listed}
    actual_files = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    _check(checks, f"{prefix}:exact_file_inventory", actual_files == expected_files)
    for relative, digest in sorted(listed.items()):
        path = (root / relative).resolve()
        within_root = root in path.parents
        _check(
            checks,
            f"{prefix}:sha:{relative}",
            within_root and path.is_file() and file_sha256(path) == digest,
        )
    return checks


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


def _parse_heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        name, value = line.split("=", 1)
        if name in result:
            raise ValueError("duplicate HEADS field")
        result[name] = value
    return result


def _closed_review_boundaries(review: Mapping[str, Any]) -> bool:
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
    )


def review_remaining_preflight(
    *,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    corpus_root: Path,
    expected_corpus_root_sha256: str,
    corpus_review_root: Path,
    expected_corpus_review_root_sha256: str,
    pilot_root: Path,
    expected_pilot_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    template: Mapping[str, Any],
    camp_repo: Path,
    expected_reviewer_camp_head: str,
    dp_repo: Path,
    expected_source_camp_head: str,
    expected_route_count: int = 375,
    expected_source_invalid_count: int = 153,
    expected_source_map_count: int = 6,
    expected_preflight_check_count: int = 16032,
) -> dict[str, Any]:
    preflight_root = Path(preflight_root).resolve()
    corpus_root = Path(corpus_root).resolve()
    corpus_review_root = Path(corpus_review_root).resolve()
    pilot_root = Path(pilot_root).resolve()
    pilot_review_root = Path(pilot_review_root).resolve()
    checks: list[dict[str, Any]] = []
    for root, digest, prefix in (
        (preflight_root, expected_preflight_root_sha256, "remaining_preflight"),
        (corpus_root, expected_corpus_root_sha256, "corpus_preflight"),
        (
            corpus_review_root,
            expected_corpus_review_root_sha256,
            "corpus_review",
        ),
        (pilot_root, expected_pilot_root_sha256, "pilot"),
        (
            pilot_review_root,
            expected_pilot_review_root_sha256,
            "pilot_review",
        ),
    ):
        checks.extend(_sealed_root_checks(root, digest, prefix))

    preflight = json.loads(
        (preflight_root / "preflight.json").read_text(encoding="utf-8")
    )
    corpus = json.loads(
        (corpus_root / "corpus_manifest.json").read_text(encoding="utf-8")
    )
    corpus_review = json.loads(
        (corpus_review_root / "review.json").read_text(encoding="utf-8")
    )
    pilot_review = json.loads(
        (pilot_review_root / "review.json").read_text(encoding="utf-8")
    )
    heads = _parse_heads(preflight_root / "HEADS")
    expected_heads = {
        "CAMP_HEAD": expected_source_camp_head,
        "FIXED_DP_HEAD": FIXED_DP_HEAD,
        "SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256": expected_corpus_root_sha256,
        "SOURCE_CORPUS_REVIEW_ROOT_SHA256": expected_corpus_review_root_sha256,
        "SOURCE_PILOT_ROOT_SHA256": expected_pilot_root_sha256,
        "SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256": (
            expected_pilot_review_root_sha256
        ),
    }
    _check(checks, "preflight:heads_exact", heads == expected_heads)
    _check(
        checks,
        "preflight:command",
        (preflight_root / "COMMAND").read_text(encoding="utf-8")
        == "v24 native corpus remaining-execution-preflight\n",
    )
    _check(
        checks,
        "preflight:run_exit",
        (preflight_root / "run.exit").read_text(encoding="ascii") == "0\n",
    )
    _check(
        checks,
        "preflight:stderr_empty",
        (preflight_root / "stderr.txt").read_text(encoding="utf-8") == "",
    )
    stdout_payload = json.loads(
        (preflight_root / "stdout.txt").read_text(encoding="utf-8")
    )
    _check(checks, "preflight:stdout_matches_json", stdout_payload == preflight)

    _check(
        checks,
        "corpus_review:source_chain",
        corpus_review.get("source_preflight_root_sha256")
        == expected_corpus_root_sha256,
    )
    _check(
        checks,
        "corpus_review:passed_closed",
        corpus_review.get("schema")
        == "camp_dp_v24_native_corpus_static_preflight_review_v1"
        and corpus_review.get("status") == "passed"
        and corpus_review.get("failed_count") == 0
        and corpus_review.get("preflight_reexecuted") is False
        and corpus_review.get("model_loaded") is False
        and corpus_review.get("simulator_executed") is False
        and corpus_review.get("candidate_generation_started") is False
        and corpus_review.get("outcome_fields_consumed") == []
        and corpus_review.get("calibration_accessed") is False
        and corpus_review.get("holdout_opened") is False
        and corpus_review.get("training_executed") is False
        and corpus_review.get("claim_authorized") is False,
    )

    preflight_checks = preflight.get("checks", [])
    preflight_checks_by_name = {
        str(check.get("name")): check.get("passed") for check in preflight_checks
    }
    expected_run_count = expected_route_count * len(REMAINING_SEEDS)
    _check(
        checks,
        "preflight:status",
        preflight.get("schema")
        == "camp_dp_v24_native_corpus_remaining_execution_preflight_v1"
        and preflight.get("status") == "passed"
        and preflight.get("failed_count") == 0,
    )
    _check(
        checks,
        "preflight:check_inventory",
        preflight.get("check_count") == expected_preflight_check_count
        and len(preflight_checks) == expected_preflight_check_count
        and len(preflight_checks_by_name) == expected_preflight_check_count
        and all(value is True for value in preflight_checks_by_name.values()),
    )
    for name in (
        "remaining_task_lock_available",
        f"remaining_route_seed_runs_{expected_run_count}",
        f"remaining_configs_{expected_run_count}",
        f"all_unique_route_assets_{expected_route_count}_unchanged",
        "disk_floor",
    ):
        _check(
            checks,
            f"preflight:required_check:{name}",
            preflight_checks_by_name.get(name) is True,
        )

    routes = [dict(route) for route in corpus.get("routes", [])]
    routes.sort(key=lambda route: str(route["record_key"]))
    route_keys = [str(route["record_key"]) for route in routes]
    route_identities = [str(route["identity_sha256"]) for route in routes]
    row_order_sha256 = _row_order_sha256(routes, REMAINING_SEEDS)
    _check(
        checks,
        "corpus:boundary",
        corpus.get("schema") == "camp_dp_v24_native_corpus_manifest_v1"
        and corpus.get("split") == "train"
        and corpus.get("route_count") == expected_route_count
        and len(routes) == expected_route_count
        and corpus.get("seeds") == list(TRAIN_SEEDS)
        and corpus.get("outcome_fields_consumed") == []
        and corpus.get("calibration_accessed") is False
        and corpus.get("holdout_opened") is False,
    )
    _check(
        checks,
        "corpus:route_keys_unique",
        len(set(route_keys)) == expected_route_count,
    )
    _check(
        checks,
        "corpus:route_identities_unique",
        len(set(route_identities)) == expected_route_count,
    )

    expected_preflight_fields = {
        "route_count": expected_route_count,
        "seeds": list(REMAINING_SEEDS),
        "route_seed_run_count": expected_run_count,
        "row_order_sha256": row_order_sha256,
        "theoretical_max_snapshots": expected_run_count * 64,
        "pilot_route_denominator_retained": expected_route_count,
        "pilot_failures_retained": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "training_executed": False,
        "tuning_executed": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_native_corpus_remaining_train_seeds_static_preflight_"
            "independent_review_only"
        ),
    }
    for name, value in expected_preflight_fields.items():
        _check(
            checks,
            f"preflight:field:{name}",
            preflight.get(name) == value,
        )

    decision = pilot_review.get("decision", {})
    _check(
        checks,
        "pilot_review:source_chain",
        pilot_review.get("source_pilot_root_sha256") == expected_pilot_root_sha256
        and pilot_review.get("source_corpus_preflight_root_sha256")
        == expected_corpus_root_sha256,
    )
    _check(
        checks,
        "pilot_review:passed_closed",
        pilot_review.get("schema")
        == "camp_dp_v24_native_corpus_pilot_independent_review_v1"
        and pilot_review.get("status") in {"passed", "passed_with_warning"}
        and pilot_review.get("failed_count") == 0
        and _closed_review_boundaries(pilot_review),
    )
    _check(
        checks,
        "pilot_review:decision",
        decision.get("authorized") is True
        and decision.get("action") == "execute_frozen_remaining_train_seeds"
        and decision.get("seeds") == list(REMAINING_SEEDS)
        and decision.get("route_count") == expected_route_count
        and decision.get("route_order") == route_keys
        and decision.get("preserve_all_failures_and_denominator") is True
        and decision.get("route_removal_replacement_reordering_authorized") is False
        and decision.get("tuning_authorized") is False
        and decision.get("outcome_access_authorized") is False
        and decision.get("calibration_access_authorized") is False
        and decision.get("holdout_access_authorized") is False
        and decision.get("claim_authorized") is False,
    )

    pilot_receipts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (pilot_root / "receipts" / "train").rglob("seed_24001.json")
    ]
    pilot_receipt_keys = [str(receipt.get("record_key")) for receipt in pilot_receipts]
    source_invalid_keys = {
        str(receipt.get("record_key"))
        for receipt in pilot_receipts
        if receipt.get("status") == "failed"
        and receipt.get("failure_reason") == SOURCE_INVALID_REASON
    }
    _check(
        checks,
        "pilot:receipt_denominator_exact",
        len(pilot_receipts) == expected_route_count
        and len(set(pilot_receipt_keys)) == expected_route_count
        and set(pilot_receipt_keys) == set(route_keys)
        and all(receipt.get("seed") == 24001 for receipt in pilot_receipts)
        and all(
            receipt.get("retained_in_denominator") is True for receipt in pilot_receipts
        ),
    )
    _check(
        checks,
        "pilot:source_invalid_routes_retained",
        len(source_invalid_keys) == expected_source_invalid_count
        and source_invalid_keys.issubset(set(route_keys))
        and pilot_review.get("recomputed", {})
        .get("failure_reason_counts", {})
        .get(SOURCE_INVALID_REASON)
        == expected_source_invalid_count,
    )

    _check(
        checks,
        "template:fixed_dp_head",
        template.get("fixed_dp", {}).get("head") == FIXED_DP_HEAD,
    )
    for owner, name in (
        ("fixed_dp", "checkpoint"),
        ("fixed_dp", "args_json"),
        ("selector", "atom_scales"),
        ("selector", "weights"),
    ):
        asset = template[owner][name]
        path = Path(str(asset["path"]))
        _check(
            checks,
            f"template:asset:{owner}:{name}",
            path.is_file() and file_sha256(path) == asset["sha256"],
        )

    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    validated_configs = 0
    route_asset_paths: set[str] = set()
    source_map_hashes: dict[str, str | None] = {}
    for route in routes:
        identity = str(route["identity_sha256"])
        _check(
            checks,
            f"route:seed_namespace:{identity}",
            route.get("seeds") == list(TRAIN_SEEDS),
        )
        asset = route["route_asset"]
        asset_path = Path(str(asset["path"])).resolve()
        route_asset_paths.add(str(asset_path))
        _check(
            checks,
            f"route:asset:{identity}",
            corpus_root in asset_path.parents
            and asset_path.is_file()
            and file_sha256(asset_path) == asset["sha256"],
        )
        map_path = str(route["source_map_path"])
        if map_path not in source_map_hashes:
            path = Path(map_path)
            source_map_hashes[map_path] = file_sha256(path) if path.is_file() else None
        _check(
            checks,
            f"route:source_map:{identity}",
            source_map_hashes[map_path] == route["source_map_sha256"],
        )
        for seed in REMAINING_SEEDS:
            try:
                config = build_expected_run_config(template, route, asset, seed)
                validate_v24_corpus_run_config(config)
            except Exception:
                valid = False
            else:
                valid = (
                    config["seeds"]["scenario"] == seed
                    and config["routes"][0]["name"] == identity
                    and config["protocol"]["sample_every_ticks"] == 1
                    and config["protocol"]["candidate_k"] == 8
                    and config["protocol"]["calibration_authorized"] is False
                    and config["protocol"]["holdout_access_authorized"] is False
                    and config["protocol"]["claim_authorized"] is False
                )
            _check(checks, f"run_config:{identity}:{seed}", valid)
            validated_configs += int(valid)
    _check(
        checks,
        "route:unique_assets",
        len(route_asset_paths) == expected_route_count,
    )
    _check(
        checks,
        "route:source_map_count",
        len(source_map_hashes) == expected_source_map_count,
    )
    _check(
        checks,
        "run_config:all_validated",
        validated_configs == expected_run_count,
    )

    camp_head = subprocess.run(
        ["git", "-C", str(camp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    camp_status = subprocess.run(
        [
            "git",
            "-C",
            str(camp_repo),
            "status",
            "--short",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _check(checks, "camp:head", camp_head == expected_reviewer_camp_head)
    _check(checks, "camp:tracked_clean", camp_status == "")
    dp_head = subprocess.run(
        ["git", "-C", str(dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dp_status = subprocess.run(
        ["git", "-C", str(dp_repo), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _check(checks, "fixed_dp:head", dp_head == FIXED_DP_HEAD)
    _check(checks, "fixed_dp:tracked_clean", dp_status == "")
    free_disk_gib = shutil.disk_usage(preflight_root).free / (1024**3)
    _check(checks, "disk:floor", free_disk_gib > MINIMUM_FREE_GIB)

    failed = [check["name"] for check in checks if not check["passed"]]
    authorized = not failed
    return {
        "schema": "camp_dp_v24_native_corpus_remaining_preflight_independent_review_v1",
        "status": "passed" if authorized else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_preflight_root_sha256": expected_preflight_root_sha256,
        "source_corpus_root_sha256": expected_corpus_root_sha256,
        "source_corpus_review_root_sha256": expected_corpus_review_root_sha256,
        "source_pilot_root_sha256": expected_pilot_root_sha256,
        "source_pilot_review_root_sha256": expected_pilot_review_root_sha256,
        "source_camp_head": expected_source_camp_head,
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "route_count": len(routes),
        "seeds": list(REMAINING_SEEDS),
        "route_seed_run_count": expected_run_count,
        "row_order_sha256": row_order_sha256,
        "source_invalid_route_count": len(source_invalid_keys),
        "validated_run_config_count": validated_configs,
        "unique_route_asset_count": len(route_asset_paths),
        "source_map_count": len(source_map_hashes),
        "free_disk_gib": free_disk_gib,
        "preflight_reexecuted": False,
        "execution_preflight_builder_imported_or_called": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "training_executed": False,
        "tuning_executed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "decision": {
            "remaining_execution_authorized": authorized,
            "action": (
                "launch_one_unique_remaining_train_seed_execution"
                if authorized
                else "stop_failed_remaining_preflight_review"
            ),
            "route_count": expected_route_count,
            "seeds": list(REMAINING_SEEDS) if authorized else [],
            "preserve_all_failures_and_denominator": authorized,
            "route_removal_replacement_reordering_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": (
            "v24_native_corpus_remaining_train_seeds_unique_execution_only"
            if authorized
            else "v24_native_corpus_remaining_train_seeds_preflight_review_failure_analysis"
        ),
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
    (root / "SHA256SUMS").write_text(
        "".join(
            f"{file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    root_sha = file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="ascii")
    return root_sha


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--expected-corpus-root-sha256", required=True)
    parser.add_argument("--corpus-review-root", type=Path, required=True)
    parser.add_argument("--expected-corpus-review-root-sha256", required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-root-sha256", required=True)
    parser.add_argument("--pilot-review-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-review-root-sha256", required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--expected-source-camp-head", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    template = json.loads(args.template.read_text(encoding="utf-8"))
    result = review_remaining_preflight(
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        corpus_root=args.corpus_root,
        expected_corpus_root_sha256=args.expected_corpus_root_sha256,
        corpus_review_root=args.corpus_review_root,
        expected_corpus_review_root_sha256=args.expected_corpus_review_root_sha256,
        pilot_root=args.pilot_root,
        expected_pilot_root_sha256=args.expected_pilot_root_sha256,
        pilot_review_root=args.pilot_review_root,
        expected_pilot_review_root_sha256=args.expected_pilot_review_root_sha256,
        template=template,
        camp_repo=ROOT,
        expected_reviewer_camp_head=args.camp_head,
        dp_repo=args.dp_repo,
        expected_source_camp_head=args.expected_source_camp_head,
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={result['fixed_dp_head']}\n"
        f"SOURCE_CAMP_HEAD={args.expected_source_camp_head}\n"
        f"SOURCE_PREFLIGHT_ROOT_SHA256={args.expected_preflight_root_sha256}\n"
        f"SOURCE_CORPUS_ROOT_SHA256={args.expected_corpus_root_sha256}\n"
        f"SOURCE_CORPUS_REVIEW_ROOT_SHA256={args.expected_corpus_review_root_sha256}\n"
        f"SOURCE_PILOT_ROOT_SHA256={args.expected_pilot_root_sha256}\n"
        f"SOURCE_PILOT_REVIEW_ROOT_SHA256={args.expected_pilot_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 remaining native corpus preflight independent review\n",
        encoding="utf-8",
    )
    _write_json(args.output_dir / "review.json", result)
    (args.output_dir / "review.md").write_text(
        "# v24 remaining native corpus preflight independent review\n\n"
        f"- status: `{result['status']}`\n"
        f"- checks / failed: `{result['check_count']} / {result['failed_count']}`\n"
        "- routes / seeds / runs / source-invalid retained: "
        f"`{result['route_count']} / 4 / {result['route_seed_run_count']} / "
        f"{result['source_invalid_route_count']}`\n"
        "- preflight/model/simulator/candidates/training/holdout: "
        "`false/false/false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
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
                "status": result["status"],
                "check_count": result["check_count"],
                "failed_count": result["failed_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
