#!/usr/bin/env python3
"""Independent sealed-artifact review for v22 native paired results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.evaluation.diffusion_planner_v22_statistics import (  # noqa: E402
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    analyze_retained_pairs,
)
from camp_core.integrations.diffusion_planner_v22_split import (  # noqa: E402
    validate_split_manifest,
)
from scripts.integrations.evaluate_diffusion_planner_v22_pairs import (  # noqa: E402
    build_pair_schedule,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    V22_SOURCE_VALID_SELECTION,
    validate_native_arm_receipt,
)


FORBIDDEN_SELECTOR_IDENTITY_FIELDS = {
    "map_id",
    "route_id",
    "route_identity",
    "route_identity_sha256",
    "split",
    "split_identity",
    "seed",
}


def review_execution(
    source_artifact: Path,
    source_root_sha256: str,
    config_path: Path,
    *,
    mode: str,
    expected_camp_head: str,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    source = Path(source_artifact).resolve()
    config = _load_json(config_path)
    manifest = _load_json(Path(str(config["source_split"]["manifest_path"])))
    validate_split_manifest(manifest)
    schedule = build_pair_schedule(config, manifest, mode=mode)
    expected_keys = {str(item["pair_key"]) for item in schedule}

    checks = 0
    failures: list[str] = []

    def check(value: Any, message: str) -> None:
        nonlocal checks
        checks += 1
        if not bool(value):
            failures.append(message)

    check(_sha256(source / "SHA256SUMS") == source_root_sha256, "source root SHA")
    check(
        (source / "ROOT_SHA256SUMS").read_text(encoding="utf-8").split()[0]
        == source_root_sha256,
        "source root receipt",
    )
    verified_files = 0
    for line in (source / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, name = line.split(maxsplit=1)
        path = (source / name.removeprefix("./")).resolve()
        check(source in path.parents and _sha256(path) == expected, f"source SHA {name}")
        verified_files += 1

    heads = dict(
        line.split("=", 1)
        for line in (source / "HEADS").read_text(encoding="utf-8").splitlines()
    )
    check(heads.get("camp_head") == expected_camp_head, "CAMP HEAD")
    check(heads.get("fixed_dp_head") == FIXED_DP_HEAD, "fixed DP HEAD")
    check((source / "run.exit").read_text().strip() == "0", "source exit")

    source_summary = _load_json(source / "summary.json")
    expected_split = str(config["modes"][mode]["split"])
    check(source_summary.get("mode") == mode, "source mode")
    check(source_summary.get("execution_split") == expected_split, "source split")
    check(source_summary.get("planned_pair_count") == len(schedule), "planned count")
    check(source_summary.get("retained_pair_count") == len(schedule), "retained count")
    check(source_summary.get("final_claim_authorized") is False, "source claim guard")
    check(
        source_summary.get("holdout_opened") is (mode == "main"),
        "holdout-open state",
    )

    rows = _load_json(source / "pair_rows.json")
    check(isinstance(rows, list) and len(rows) == len(schedule), "pair row count")
    observed_keys = {str(row.get("pair_key")) for row in rows}
    check(observed_keys == expected_keys, "planned/observed pair keys")
    check(len(observed_keys) == len(rows), "unique pair keys")
    check({row.get("split") for row in rows} == {expected_split}, "row split")

    candidate0_count = 0
    non_candidate0_count = 0
    all_k_high_risk_ticks = 0
    immutable_ticks = 0
    candidate0_identity_ticks = 0
    symmetric_failures = 0
    arm_symmetry = True
    feature_denylist = True
    candidate_immutability = True
    candidate0_identity = True
    complete_count = 0
    for row in rows:
        check(row.get("route_retained") is True, "route retained")
        check(row.get("included_in_denominator") is True, "denominator retained")
        pair_path = source / str(row["receipt_key"])
        check(pair_path.exists(), "pair receipt exists")
        check(_load_json(pair_path) == row, "pair row equals receipt")
        arms = {
            arm: _load_json(pair_path.with_name(f"{arm}.json"))
            for arm in ("dp", "camp")
        }
        if row.get("paired_complete") is True:
            complete_count += 1
            for arm in ("dp", "camp"):
                try:
                    validate_native_arm_receipt(
                        arms[arm],
                        arm,
                        expected_ticks=int(config["modes"][mode]["max_steps"]),
                        require_summary=True,
                        expected_selection_policy=(
                            V22_SOURCE_VALID_SELECTION if arm == "camp" else None
                        ),
                        expected_safety_schema="safety_cost_native_v22",
                    )
                    check(True, f"{arm} receipt validator")
                except Exception as exc:
                    check(False, f"{arm} receipt validator: {exc}")
            for name in (
                "route_name",
                "route_sha256",
                "logical_map_sha256",
                "fixed_dp_head",
                "checkpoint_sha256",
                "args_sha256",
                "scenario_seed",
                "spawn_config_sha256",
                "initial_state_sha256",
                "initial_input_sha256",
            ):
                equal = arms["dp"].get(name) == arms["camp"].get(name)
                arm_symmetry &= equal
                check(equal, f"paired symmetry {name}")
            for tick in arms["camp"]["ticks"]:
                index = int(tick["selected_index"])
                candidate0_count += int(index == 0)
                non_candidate0_count += int(index != 0)
                all_k_high_risk_ticks += int(tick["all_k_high_risk"])
                unchanged = (
                    tick["candidate_tensor_sha256_before"]
                    == tick["candidate_tensor_sha256_after"]
                    and tick["selected_trajectory_sha256"]
                    == tick["candidate_row_sha256"][index]
                )
                candidate_immutability &= unchanged
                immutable_ticks += 1
                check(unchanged, "fixed candidate immutability")
                identity = (
                    tick["candidate_row_sha256"][0]
                    == tick["default_output_sha256"]
                    == tick["default_candidate0_identity"]["candidate0_sha256"]
                )
                candidate0_identity &= identity
                candidate0_identity_ticks += 1
                check(identity, "candidate0/default identity")
                denied = FORBIDDEN_SELECTOR_IDENTITY_FIELDS.isdisjoint(tick)
                feature_denylist &= denied
                check(denied, "selector identity denylist")
        else:
            symmetric = (
                row.get("dp_status") == row.get("camp_status")
                and row.get("dp_failure_stage") == row.get("camp_failure_stage")
                and row.get("dp_failure_reason") == row.get("camp_failure_reason")
            )
            arm_symmetry &= symmetric
            symmetric_failures += int(symmetric)
            check(symmetric, "failure arm symmetry")

    guards = {
        "artifact_sha_verified": not any(
            message.startswith("source SHA") or message.startswith("source root")
            for message in failures
        ),
        "candidate_immutability_verified": candidate_immutability,
        "candidate0_default_identity_verified": candidate0_identity,
        "independent_review_passed": False,
        "split_zero_overlap_verified": True,
        "arm_symmetry_verified": arm_symmetry,
        "feature_identity_denylist_verified": feature_denylist,
    }
    preliminary = analyze_retained_pairs(
        list(expected_keys),
        rows,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        evidence_guards=guards,
        claim_evaluation=False,
    )
    status = "passed" if not failures else "failed"
    guards["independent_review_passed"] = status == "passed"
    statistics = analyze_retained_pairs(
        list(expected_keys),
        rows,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        evidence_guards=guards,
        claim_evaluation=mode == "main" and status == "passed",
    )
    return {
        "schema_version": "camp_dp_v22_native_result_independent_review_v1",
        "status": status,
        "run_exit": 0 if status == "passed" else 1,
        "checks": checks,
        "failed_checks": len(failures),
        "failures": failures,
        "mode": mode,
        "source_execution_artifact": str(source),
        "source_execution_root_sha256": source_root_sha256,
        "verified_source_files": verified_files,
        "planned_pair_count": len(schedule),
        "retained_pair_count": len(rows),
        "paired_complete_count": complete_count,
        "symmetric_failure_pair_count": symmetric_failures,
        "candidate0_selection_count": candidate0_count,
        "non_candidate0_selection_count": non_candidate0_count,
        "all_k_high_risk_tick_count": all_k_high_risk_ticks,
        "immutable_candidate_ticks": immutable_ticks,
        "candidate0_default_identity_ticks": candidate0_identity_ticks,
        "evidence_guards": guards,
        "statistics": statistics,
        "preliminary_nonclaim_decision": preliminary["claim_decision"],
        "claim_decision": statistics["claim_decision"],
        "holdout_opened": mode == "main",
    }


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mode", choices=("pilot", "main"), required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    result = review_execution(
        args.source_artifact,
        args.source_root_sha256,
        args.config,
        mode=args.mode,
        expected_camp_head=args.expected_camp_head,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
    )
    args.output.mkdir(parents=True)
    (args.output / "review.json").write_text(
        json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    overall = result["statistics"]["strata"]["overall"]
    coverage = result["statistics"]["coverage"]
    (args.output / "review.md").write_text(
        "# v22 native paired result independent review\n\n"
        f"- Status: `{result['status']}`\n"
        f"- Mode: `{result['mode']}`\n"
        f"- Checks / failures: `{result['checks']} / {result['failed_checks']}`\n"
        f"- Planned / retained / complete: `{coverage['planned_pair_count']} / "
        f"{coverage['retained_pair_count']} / {coverage['paired_complete_count']}`\n"
        f"- Mean / median delta: `{overall['mean']} / {overall['median']}`\n"
        f"- Cluster CI95: `[{overall['ci95_low']}, {overall['ci95_high']}]`\n"
        f"- Decision: `{result['claim_decision']['decision']}`\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["run_exit"])


if __name__ == "__main__":
    raise SystemExit(main())
