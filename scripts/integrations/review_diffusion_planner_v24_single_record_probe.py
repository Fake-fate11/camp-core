from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_CONFIG_SHA256 = (
    "1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc"
)
EXPECTED_ROUTE_SHA256 = (
    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
)
EXPECTED_COMPATIBILITY = (
    "process_local_postponed_annotations_fixed_dp_source_only"
)
EXPECTED_SEED = 24001


def _check(name: str, passed: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def evaluate_contract(
    config: Mapping[str, Any],
    summary: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    arm = summary.get("capability_arm", {})
    ticks = arm.get("ticks", []) if isinstance(arm, Mapping) else []
    tick = ticks[0] if len(ticks) == 1 and isinstance(ticks[0], Mapping) else {}
    rows = tick.get("candidate_row_sha256", [])
    selected = tick.get("selected_index")
    identity = tick.get("default_candidate0_identity", {})
    scores = tick.get("scores", [])
    verification = execution.get("verification", [])
    protocol = config.get("protocol", {})
    selector = config.get("selector", {})
    seeds = config.get("seeds", {})
    fixed_dp = config.get("fixed_dp", {})
    checks = [
        _check(
            "config_schema",
            config.get("schema_version")
            == "camp_dp_v24_single_record_source_probe_v1",
        ),
        _check("config_fixed_dp_head", fixed_dp.get("head") == FIXED_DP_HEAD),
        _check("config_k8", selector.get("candidate_k") == 8),
        _check("config_scenario_seed", seeds.get("scenario") == EXPECTED_SEED),
        _check("config_candidate_seed", seeds.get("candidate") == EXPECTED_SEED),
        _check(
            "config_holdout_closed",
            protocol.get("holdout_access_authorized") is False,
        ),
        _check("config_claim_closed", protocol.get("claim_authorized") is False),
        _check("execution_status", execution.get("status") == "passed"),
        _check("execution_exit", execution.get("execution_exit") == 0),
        _check(
            "execution_config_sha",
            execution.get("config_sha256") == EXPECTED_CONFIG_SHA256,
        ),
        _check("execution_outcome_closed", execution.get("outcome_accessed") is False),
        _check("execution_holdout_closed", execution.get("holdout_opened") is False),
        _check("execution_claim_closed", execution.get("claim_authorized") is False),
        _check(
            "execution_verification_passed",
            bool(verification)
            and all(item.get("exit") == 0 for item in verification),
        ),
        _check("summary_status", summary.get("status") == "passed"),
        _check("summary_mode", summary.get("mode", "capability-smoke") == "capability-smoke"),
        _check("summary_one_route", summary.get("route_count") == 1),
        _check("summary_one_arm", summary.get("arm_count") == 1),
        _check("summary_claim_closed", summary.get("claim_authorized") is False),
        _check("arm_status", arm.get("status") == "ok"),
        _check("arm_is_camp_observation", arm.get("arm", "camp") == "camp"),
        _check("arm_fixed_dp_head", arm.get("fixed_dp_head") == FIXED_DP_HEAD),
        _check("arm_route_sha", arm.get("route_sha256") == EXPECTED_ROUTE_SHA256),
        _check("arm_scenario_seed", arm.get("scenario_seed") == EXPECTED_SEED),
        _check(
            "arm_runtime_compatibility",
            arm.get("runtime_annotation_compatibility") == EXPECTED_COMPATIBILITY,
        ),
        _check("one_tick", len(ticks) == 1),
        _check("eight_candidate_rows", isinstance(rows, list) and len(rows) == 8),
        _check("candidate_rows_unique", len(set(rows)) == 8 if rows else False),
        _check(
            "candidate_tensor_immutable",
            tick.get("candidate_tensor_sha256_before")
            == tick.get("candidate_tensor_sha256_after"),
        ),
        _check(
            "global_rng_immutable",
            tick.get("global_rng_sha256_before")
            == tick.get("global_rng_sha256_after"),
        ),
        _check("candidate0_elementwise_equal", identity.get("elementwise_equal") is True),
        _check("candidate0_zero_difference", identity.get("max_abs_difference") == 0.0),
        _check("native_k_ranking_absent", identity.get("native_ranked_k8") is False),
        _check(
            "candidate0_hash_identity",
            bool(rows)
            and identity.get("candidate0_sha256") == rows[0]
            and identity.get("default_output_sha256") == rows[0],
        ),
        _check(
            "selected_row_identity",
            isinstance(selected, int)
            and 0 <= selected < len(rows)
            and tick.get("selected_trajectory_sha256") == rows[selected],
        ),
        _check("source_complete_k8", tick.get("source_complete_mask") == [True] * 8),
        _check("source_valid_k8", tick.get("source_valid_mask") == [True] * 8),
        _check("physical_feasible_k8", tick.get("physical_feasible_mask") == [True] * 8),
        _check("affine_score_contract", tick.get("score_contract") == "score_k(w)=a_k^T w"),
        _check(
            "eight_finite_scores",
            isinstance(scores, list)
            and len(scores) == 8
            and all(math.isfinite(float(value)) for value in scores),
        ),
        _check(
            "atom_matrix_sha",
            isinstance(tick.get("atom_matrix_sha256"), str)
            and len(tick["atom_matrix_sha256"]) == 64,
        ),
    ]
    return checks


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_manifest(root: Path, expected_root_sha256: str) -> list[dict[str, Any]]:
    manifest = root / "SHA256SUMS"
    checks = [
        _check("manifest_exists", manifest.is_file()),
        _check("root_sha256", manifest.is_file() and _file_sha256(manifest) == expected_root_sha256),
    ]
    if not manifest.is_file():
        return checks
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
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


def review_execution(
    execution_root: Path, expected_root_sha256: str
) -> dict[str, Any]:
    execution_root = execution_root.resolve()
    native_root = execution_root / "native_execution"
    checks = _verify_manifest(execution_root, expected_root_sha256)
    nested_pointer = (native_root / "ROOT_SHA256SUMS").read_text(encoding="ascii").split()[0]
    checks.extend(_verify_manifest(native_root, nested_pointer))
    config = json.loads((native_root / "smoke_config.json").read_text(encoding="utf-8"))
    summary = json.loads((native_root / "summary.json").read_text(encoding="utf-8"))
    execution = json.loads((execution_root / "execution.json").read_text(encoding="utf-8"))
    checks.extend(evaluate_contract(config, summary, execution))

    native_result = summary["capability_arm"]["native_result"]
    resolved_native_paths: dict[str, str] = {}
    staging_prefix = str(execution_root / "native_execution.tmp")
    final_prefix = str(native_root)
    for name in ("clearance_log_path", "trajectory_log_path"):
        recorded = str(native_result[name])
        resolved = Path(recorded.replace(staging_prefix, final_prefix))
        resolved_native_paths[name] = str(resolved)
        checks.append(_check(f"materialized_native_path:{name}", resolved.is_file()))

    failed = [check["name"] for check in checks if not check["passed"]]
    tick = summary["capability_arm"]["ticks"][0]
    return {
        "schema": "camp_dp_v24_single_record_source_probe_independent_review_v1",
        "status": "passed" if not failed else "failed",
        "source_artifact": str(execution_root),
        "source_root_sha256": expected_root_sha256,
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "recomputed": {
            "candidate_k": len(tick["candidate_row_sha256"]),
            "selected_index": int(tick["selected_index"]),
            "candidate_tensor_sha256": tick["candidate_tensor_sha256_before"],
            "candidate0_sha256": tick["candidate_row_sha256"][0],
            "all_source_valid": all(tick["source_valid_mask"]),
            "all_source_complete": all(tick["source_complete_mask"]),
        },
        "staging_path_receipt_count": sum(
            str(native_result[name]).startswith(staging_prefix)
            for name in ("clearance_log_path", "trajectory_log_path")
        ),
        "resolved_native_paths": resolved_native_paths,
        "model_loaded": False,
        "probe_reexecuted": False,
        "outcome_accessed": False,
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
    root_sha = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--expected-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    record = review_execution(args.execution_root, args.expected_root_sha256)
    command = (
        f"review {args.execution_root.resolve()} "
        f"root={args.expected_root_sha256} without model execution\n"
    )
    (args.output_dir / "COMMAND").write_text(command, encoding="utf-8")
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_ARTIFACT_ROOT_SHA256={args.expected_root_sha256}\n",
        encoding="ascii",
    )
    _write_json(args.output_dir / "review.json", record)
    (args.output_dir / "review.md").write_text(
        "# v24 single-record source-probe independent review\n\n"
        f"- status: `{record['status']}`\n"
        f"- checks / failed: `{record['check_count']} / {record['failed_count']}`\n"
        f"- K / selected index: `{record['recomputed']['candidate_k']} / "
        f"{record['recomputed']['selected_index']}`\n"
        "- model/probe/outcome/holdout access: `false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(record, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text(
        "0\n" if record["status"] == "passed" else "1\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "status": record["status"],
                "check_count": record["check_count"],
                "failed_count": record["failed_count"],
                "staging_path_receipt_count": record["staging_path_receipt_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
