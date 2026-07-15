#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.materialize_diffusion_planner_v22_native_corpus import (
    CorpusSnapshotWriter,
)
from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
    build_corpus_run_config,
)
from scripts.integrations.review_diffusion_planner_v24_native_corpus import (
    CORPUS_MANIFEST_SHA256,
    CORPUS_PLAN_SHA256,
    FIXED_DP_HEAD,
    TRAIN_SEEDS,
    _source_root_checks,
    file_sha256,
    validate_corpus_boundaries,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    build_native_arm_runner,
    validate_v24_corpus_run_config,
    verify_config_assets,
)


PILOT_SEED = 24001
MINIMUM_FREE_BYTES = 10 * 1024**3


def verified_asset_receipts_complete(receipts: Mapping[str, str]) -> bool:
    return (
        receipts.get("fixed_dp_head") == FIXED_DP_HEAD
        and len(receipts) >= 11
    )


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            _json_safe(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(name): _json_safe(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def pilot_rows(
    manifest: Mapping[str, Any], *, expected_route_count: int = 375
) -> list[tuple[dict[str, Any], int]]:
    if manifest.get("schema") != "camp_dp_v24_native_corpus_manifest_v1":
        raise ValueError("v24 corpus manifest schema mismatch")
    if (
        manifest.get("split") != "train"
        or manifest.get("seeds") != list(TRAIN_SEEDS)
        or manifest.get("outcome_fields_consumed") != []
        or manifest.get("calibration_accessed") is not False
        or manifest.get("holdout_opened") is not False
    ):
        raise ValueError("v24 pilot boundary mismatch")
    routes = [dict(route) for route in manifest.get("routes", [])]
    if len(routes) != expected_route_count:
        raise ValueError("v24 pilot route denominator mismatch")
    identities = [str(route["identity_sha256"]) for route in routes]
    if len(set(identities)) != len(identities):
        raise ValueError("v24 pilot route identities are not unique")
    for route in routes:
        if route.get("seeds") != list(TRAIN_SEEDS):
            raise ValueError("v24 pilot route seed namespace mismatch")
    routes.sort(key=lambda route: str(route["record_key"]))
    return [(route, PILOT_SEED) for route in routes]


class V24CorpusSnapshotWriter(CorpusSnapshotWriter):
    def __init__(self, *, route: Mapping[str, Any], output_dir: Path, seed: int) -> None:
        self.record_key = str(route["record_key"])
        self.map_family_id = str(route["map_family_id"])
        self.corridor_group_sha256 = str(route["corridor_group_sha256"])
        super().__init__(
            output_dir=output_dir,
            split="train",
            logical_map_sha256=str(route["logical_map_sha256"]),
            route_identity_sha256=str(route["identity_sha256"]),
            group_sha256=self.corridor_group_sha256,
            seed=seed,
            source_stratum=route.get("source_stratum", {}),
        )

    def __call__(self, snapshot: Mapping[str, Any]) -> str:
        payload = json.loads(json.dumps(snapshot, allow_nan=False))
        sidecar = payload.setdefault("sidecar", {})
        sidecar.update(
            {
                "record_key": self.record_key,
                "map_family_id": self.map_family_id,
                "corridor_group_sha256": self.corridor_group_sha256,
            }
        )
        return super().__call__(payload)

    def write_v24_run_receipt(
        self,
        *,
        status: str,
        wall_clock_s: float,
        failure_stage: str | None = None,
        failure_reason: str | None = None,
    ) -> Path:
        if status not in {"ok", "failed"}:
            raise ValueError("v24 pilot receipt status mismatch")
        if status == "failed" and (not failure_stage or not failure_reason):
            raise ValueError("v24 failed pilot receipt requires cause")
        receipt = {
            "schema": "camp_dp_v24_native_corpus_pilot_run_receipt_v1",
            "status": status,
            "split": "train",
            "phase": "capability_pilot_all_train_routes_first_seed",
            "record_key": self.record_key,
            "map_family_id": self.map_family_id,
            "logical_map_sha256": self.logical_map_sha256,
            "corridor_group_sha256": self.corridor_group_sha256,
            "route_identity_sha256": self.route_identity_sha256,
            "seed": self.seed,
            "snapshot_sha256": list(self.snapshot_sha256),
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "retained_in_denominator": True,
            "wall_clock_s": wall_clock_s,
        }
        path = (
            self.output_dir
            / "receipts"
            / "train"
            / self.route_identity_sha256
            / f"seed_{self.seed}.json"
        )
        _write_json_atomic(path, receipt)
        return path


def _aggregate_execution(output_dir: Path, planned: int) -> dict[str, Any]:
    receipts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (output_dir / "receipts" / "train").rglob("seed_*.json")
    ] if (output_dir / "receipts" / "train").is_dir() else []
    complete = sum(item.get("status") == "ok" for item in receipts)
    failed = sum(item.get("status") == "failed" for item in receipts)
    snapshots = list((output_dir / "snapshots").glob("*.json"))
    all_k_high_risk = 0
    strata: dict[str, int] = {}
    for path in snapshots:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sidecar = payload["sidecar"]
        all_k_high_risk += int(bool(sidecar.get("all_k_high_risk")))
        active = [
            str(name)
            for name, enabled in sidecar.get("source_stratum", {}).items()
            if enabled
        ] or ["normal"]
        for name in active:
            strata[name] = strata.get(name, 0) + 1
    return {
        "planned_route_seed_runs": planned,
        "complete_route_seed_runs": complete,
        "failed_route_seed_runs": failed,
        "retained_route_seed_runs": len(receipts),
        "pending_route_seed_runs": planned - len(receipts),
        "route_coverage": len(receipts) / planned if planned else 0.0,
        "snapshot_count": len(snapshots),
        "snapshot_count_by_source_stratum": dict(sorted(strata.items())),
        "all_k_high_risk_snapshot_count": all_k_high_risk,
    }


def execute_pilot_manifest(
    manifest: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
    expected_route_count: int = 375,
    free_bytes: Callable[[], int] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    rows = pilot_rows(manifest, expected_route_count=expected_route_count)
    output_dir = Path(output_dir)
    if output_dir.exists() and not resume:
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    free_bytes = free_bytes or (lambda: shutil.disk_usage(output_dir).free)
    execution_started = time.perf_counter()
    stopped_for_disk = False
    for index, (route, seed) in enumerate(rows, start=1):
        receipt_path = (
            output_dir
            / "receipts"
            / "train"
            / str(route["identity_sha256"])
            / f"seed_{seed}.json"
        )
        if receipt_path.is_file():
            prior = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                prior.get("route_identity_sha256") != route["identity_sha256"]
                or prior.get("seed") != seed
                or prior.get("retained_in_denominator") is not True
            ):
                raise ValueError("resume receipt boundary mismatch")
            continue
        if free_bytes() <= MINIMUM_FREE_BYTES:
            stopped_for_disk = True
            break
        writer = V24CorpusSnapshotWriter(
            route=route, output_dir=output_dir, seed=seed
        )
        native_output = (
            output_dir
            / "native_runs"
            / str(route["identity_sha256"])
            / f"seed_{seed}"
        )
        started = time.perf_counter()
        try:
            run_config = build_corpus_run_config(
                template,
                route,
                route["route_asset"],
                seed,
            )
            validate_v24_corpus_run_config(run_config)
            result = run_arm(
                route=run_config["routes"][0],
                arm="camp",
                config=run_config,
                output_dir=native_output,
                max_steps=64,
                decision_sink=writer,
            )
            if result.get("status") != "ok":
                raise RuntimeError(str(result.get("failure_reason") or "native arm failed"))
            native_receipt = (
                output_dir
                / "native_receipts"
                / str(route["identity_sha256"])
                / f"seed_{seed}.json"
            )
            _write_json_atomic(native_receipt, result)
            writer.write_v24_run_receipt(
                status="ok", wall_clock_s=time.perf_counter() - started
            )
        except Exception as exc:
            writer.write_v24_run_receipt(
                status="failed",
                failure_stage="native_arm_execution",
                failure_reason=f"{type(exc).__name__}: {exc}",
                wall_clock_s=time.perf_counter() - started,
            )
        aggregate = _aggregate_execution(output_dir, len(rows))
        aggregate.update(
            {
                "schema": "camp_dp_v24_native_corpus_pilot_progress_v1",
                "status": "running",
                "last_completed_row": index,
                "free_disk_gib": free_bytes() / (1024**3),
            }
        )
        _write_json_atomic(output_dir / "progress.json", aggregate)
        if free_bytes() <= MINIMUM_FREE_BYTES:
            stopped_for_disk = True
            break

    aggregate = _aggregate_execution(output_dir, len(rows))
    if stopped_for_disk:
        status = "stopped_disk_floor"
    elif aggregate["failed_route_seed_runs"]:
        status = "complete_with_retained_failures"
    else:
        status = "complete"
    aggregate.update(
        {
            "schema": "camp_dp_v24_native_corpus_pilot_summary_v1",
            "status": status,
            "phase": "capability_pilot_all_train_routes_first_seed",
            "seed": PILOT_SEED,
            "corpus_steps": 64,
            "sample_every_ticks": 1,
            "theoretical_max_snapshots": len(rows) * 64,
            "wall_clock_s": time.perf_counter() - execution_started,
            "free_disk_gib": free_bytes() / (1024**3),
            "all_routes_retained_in_denominator": (
                aggregate["retained_route_seed_runs"] == len(rows)
            ),
            "tuning_executed": False,
            "calibration_accessed": False,
            "holdout_opened": False,
            "outcome_fields_consumed": [],
            "claim_authorized": False,
        }
    )
    _write_json_atomic(output_dir / "pilot_summary.json", aggregate)
    terminal_progress = dict(aggregate)
    terminal_progress.update(
        {
            "schema": "camp_dp_v24_native_corpus_pilot_progress_v1",
            "status": status,
            "last_completed_row": aggregate["retained_route_seed_runs"],
            "free_disk_gib": aggregate["free_disk_gib"],
        }
    )
    _write_json_atomic(output_dir / "progress.json", terminal_progress)
    return aggregate


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha = file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha


def _execution_preflight(
    *,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    review_root: Path,
    expected_review_root_sha256: str,
    template: Mapping[str, Any],
    dp_repo: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    plan = json.loads((preflight_root / "corpus_plan.json").read_text())
    manifest = json.loads((preflight_root / "corpus_manifest.json").read_text())
    validate_corpus_boundaries(plan, manifest)
    if plan.get("plan_sha256") != CORPUS_PLAN_SHA256:
        raise ValueError("v24 corpus plan SHA mismatch")
    if manifest.get("manifest_sha256") != CORPUS_MANIFEST_SHA256:
        raise ValueError("v24 corpus manifest SHA mismatch")
    rows = pilot_rows(manifest)
    checks = _source_root_checks(
        preflight_root, expected_preflight_root_sha256, "corpus_preflight"
    )
    checks.extend(
        _source_root_checks(review_root, expected_review_root_sha256, "corpus_review")
    )
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
    validated = 0
    first_config = None
    for route, seed in rows:
        config = build_corpus_run_config(template, route, route["route_asset"], seed)
        validate_v24_corpus_run_config(config)
        if first_config is None:
            first_config = config
        validated += 1
    if first_config is None:
        raise ValueError("v24 pilot has no run config")
    verified_assets = verify_config_assets(first_config)
    source_maps = {
        str(route["source_map_path"]): str(route["source_map_sha256"])
        for route, _seed in rows
    }
    source_maps_unchanged = all(
        Path(path).is_file() and file_sha256(Path(path)) == digest
        for path, digest in source_maps.items()
    )
    checks.extend(
        [
            {"name": "fixed_dp_head", "passed": dp_head == FIXED_DP_HEAD},
            {"name": "fixed_dp_tracked_clean", "passed": dp_status == ""},
            {
                "name": "verified_first_run_assets_complete",
                "passed": verified_asset_receipts_complete(verified_assets),
            },
            {"name": "all_live_source_maps_unchanged", "passed": source_maps_unchanged},
            {"name": "pilot_routes_375", "passed": len(rows) == 375},
            {"name": "pilot_configs_375", "passed": validated == 375},
            {"name": "disk_floor", "passed": shutil.disk_usage(preflight_root).free > MINIMUM_FREE_BYTES},
        ]
    )
    return plan, manifest, checks


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("execution-preflight", "execute-pilot"), required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--expected-review-root-sha256", required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.output_dir.exists() and not args.resume:
        raise FileExistsError(args.output_dir)
    if args.mode == "execution-preflight" and args.resume:
        raise ValueError("execution preflight cannot resume")

    template = json.loads(args.template.read_text(encoding="utf-8"))
    plan, manifest, checks = _execution_preflight(
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        review_root=args.review_root,
        expected_review_root_sha256=args.expected_review_root_sha256,
        template=template,
        dp_repo=args.dp_repo,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    if failed:
        raise ValueError(f"v24 corpus execution preflight failed: {failed}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256={args.expected_preflight_root_sha256}\n"
        f"SOURCE_CORPUS_REVIEW_ROOT_SHA256={args.expected_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        f"v24 native corpus {args.mode}\n", encoding="utf-8"
    )
    if args.mode == "execution-preflight":
        result = {
            "schema": "camp_dp_v24_native_corpus_pilot_execution_preflight_v1",
            "status": "passed",
            "check_count": len(checks),
            "failed_count": 0,
            "checks": checks,
            "route_count": 375,
            "seed": PILOT_SEED,
            "theoretical_max_snapshots": 24000,
            "model_loaded": False,
            "simulator_executed": False,
            "candidate_generation_started": False,
            "outcome_fields_consumed": [],
            "calibration_accessed": False,
            "holdout_opened": False,
            "tuning_executed": False,
            "claim_authorized": False,
            "next_work_target": "v24_native_corpus_capability_pilot_execution_only",
        }
        _write_json_atomic(args.output_dir / "preflight.json", result)
        (args.output_dir / "preflight.md").write_text(
            "# v24 native corpus pilot execution preflight\n\n"
            f"- checks / failed: `{len(checks)} / 0`\n"
            "- routes / seed / max snapshots: `375 / 24001 / 24000`\n"
            "- model/simulator/candidates/outcomes/holdout: `false/false/false/false/false`\n",
            encoding="utf-8",
        )
    else:
        import fcntl

        lock_handle = (args.output_dir / ".pilot.lock").open("a+")
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another v24 pilot owns this artifact lock") from exc
        _write_json_atomic(
            args.output_dir / "STATE.json",
            {"status": "running", "pid": os.getpid(), "seed": PILOT_SEED},
        )
        first_route, first_seed = pilot_rows(manifest)[0]
        first_config = build_corpus_run_config(
            template, first_route, first_route["route_asset"], first_seed
        )
        run_arm = build_native_arm_runner(first_config, device=args.device)
        result = execute_pilot_manifest(
            manifest,
            template,
            output_dir=args.output_dir,
            run_arm=run_arm,
            resume=True,
        )
        _write_json_atomic(
            args.output_dir / "STATE.json",
            {"status": result["status"], "pid": os.getpid(), "seed": PILOT_SEED},
        )
        result["source_preflight_root_sha256"] = args.expected_preflight_root_sha256
        result["source_review_root_sha256"] = args.expected_review_root_sha256
        result["fixed_dp_head"] = FIXED_DP_HEAD
        result["next_work_target"] = (
            "v24_native_corpus_capability_pilot_independent_review_only"
            if result["status"].startswith("complete")
            else "global_stop_disk_floor"
        )
        _write_json_atomic(args.output_dir / "execution.json", result)
        (args.output_dir / "execution.md").write_text(
            "# v24 native corpus capability pilot\n\n"
            f"- status: `{result['status']}`\n"
            f"- complete / failed / retained: `{result['complete_route_seed_runs']} / {result['failed_route_seed_runs']} / {result['retained_route_seed_runs']}`\n"
            f"- snapshots: `{result['snapshot_count']}`\n"
            "- tuning/calibration/holdout/claim: `false/false/false/false`\n",
            encoding="utf-8",
        )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    success = result["status"] == "passed" or result["status"].startswith("complete")
    (args.output_dir / "run.exit").write_text(
        "0\n" if success else "2\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "status": result["status"],
                "check_count": len(checks),
                "failed_count": len(failed),
            },
            sort_keys=True,
        )
    )
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
