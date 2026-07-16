#!/usr/bin/env python3
"""Independently review the v24 holdout main-once static authorization."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.prepare_diffusion_planner_v24_paired_evaluation import (  # noqa: E402
    _seal,
    _verify_artifact_root,
    _write_json,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
HOLDOUT_SEEDS = [24201, 24202, 24203, 24204, 24205]


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_value(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def review_holdout_authorization(
    *,
    config_path: Path,
    authorization_root: Path,
    expected_authorization_root_sha256: str,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    camp_head: str,
    output_dir: Path,
) -> dict[str, Any]:
    roots = {
        "authorization": _verify_artifact_root(
            authorization_root,
            expected_authorization_root_sha256,
            "holdout_authorization",
        ),
        "preflight": _verify_artifact_root(
            preflight_root, expected_preflight_root_sha256, "paired_preflight"
        ),
        "pilot_review": _verify_artifact_root(
            pilot_review_root,
            expected_pilot_review_root_sha256,
            "paired_pilot_review",
        ),
    }
    config = _load_json(config_path)
    source = _load_json(authorization_root / "authorization_result.json")
    source_schedule = _load_json(authorization_root / "schedule_receipt.json")
    preflight = _load_json(preflight_root / "preflight_result.json")
    pilot_review = _load_json(pilot_review_root / "review_result.json")
    run_configs = [
        json.loads(line)
        for line in (preflight_root / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    main = [
        item for item in run_configs if item["protocol"]["evaluation_mode"] == "main"
    ]
    pair_keys: set[str] = set()
    route_seeds: dict[str, set[int]] = defaultdict(set)
    orders: Counter[str] = Counter()
    families: set[str] = set()
    corridors: set[str] = set()
    protocols_valid = True
    for item in main:
        protocol = item["protocol"]
        route = item["routes"][0]
        seed = int(item["seeds"]["scenario"])
        pair_keys.add(f"holdout/{route['name']}/seed_{seed}")
        route_seeds[str(route["name"])].add(seed)
        orders[
            "dp_camp" if protocol["arm_order"] == ["dp", "camp"] else "camp_dp"
        ] += 1
        families.add(str(item["map"]["map_family_id"]))
        corridors.add(str(item["map"]["corridor_group_sha256"]))
        protocols_valid = protocols_valid and (
            protocol["evaluation_split"] == "holdout"
            and protocol["evaluation_steps"] == 64
            and protocol["execution_authorized"] is False
            and protocol["holdout_access_authorized"] is False
            and protocol["independent_reset_per_arm"] is True
            and protocol["same_initial_state_and_exogenous_seed_per_pair"] is True
            and protocol["per_arm_candidate_tensor_immutability_required"] is True
            and protocol["per_arm_candidate0_default_identity_required"] is True
            and protocol[
                "t0_cross_arm_input_and_candidate_hash_identity_required"
            ]
            is True
            and protocol["post_divergence_cross_arm_tensor_identity_required"]
            is False
            and protocol["latency_comparison_authorized"] is False
            and protocol["claim_authorized"] is False
        )
    state_path = Path(str(config["holdout_once_contract"]["state_path"]))
    live_head = _git_value(ROOT, "rev-parse", "HEAD")
    live_status = _git_value(ROOT, "status", "--porcelain", "--untracked-files=no")
    dp_repo = Path(str(main[0]["fixed_dp"]["repo"]))
    dp_head = _git_value(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_value(dp_repo, "status", "--porcelain")
    evaluator = (
        ROOT / "scripts" / "integrations" / "evaluate_diffusion_planner_v24_pairs.py"
    ).read_text(encoding="utf-8")
    execute_source = evaluator.split("def execute_from_preflight(", 1)[1]
    order_verified = (
        execute_source.index("_verify_artifact_root(")
        < execute_source.index("claim_holdout_once_state(")
        < execute_source.index("runner = build_native_arm_runner(")
    )
    recomputed_schedule = {
        "pair_count": len(main),
        "unique_pair_count": len(pair_keys),
        "route_count": len(route_seeds),
        "route_seed_sets_exact": all(
            sorted(seeds) == HOLDOUT_SEEDS for seeds in route_seeds.values()
        ),
        "arm_order_counts": dict(orders),
        "map_family_count": len(families),
        "corridor_group_count": len(corridors),
        "violations": [] if protocols_valid else ["protocol_contract"],
    }
    free_bytes = shutil.disk_usage(output_dir.parent).free
    checks = {
        "source_roots_verified": all(item["root_sha256"] for item in roots.values()),
        "preflight_passed": preflight.get("status") == "passed"
        and preflight.get("holdout_opened") is False,
        "source_passed": source.get("status") == "passed"
        and source.get("failed_count") == 0,
        "source_schedule_exact": source_schedule == recomputed_schedule,
        "source_no_runtime": source.get("runner_built") is False
        and source.get("model_loaded") is False
        and source.get("simulator_executed") is False,
        "source_no_outcomes": source.get("outcome_fields_consumed") == [],
        "preflight_source_bound": source.get("source_roots", {}).get(
            "preflight", {}
        ).get("root_sha256")
        == expected_preflight_root_sha256,
        "pilot_review_source_bound": source.get("source_roots", {}).get(
            "pilot_review", {}
        ).get("root_sha256")
        == expected_pilot_review_root_sha256,
        "pilot_review_passed": pilot_review.get("status") == "passed",
        "pilot_review_holdout_closed": pilot_review.get("holdout_opened") is False
        and pilot_review.get("holdout_open_count") == 0,
        "main_population": len(main) == 120
        and len(pair_keys) == 120
        and len(route_seeds) == 24,
        "five_seeds_per_route": recomputed_schedule["route_seed_sets_exact"],
        "arm_order_balance": dict(orders) == {"dp_camp": 60, "camp_dp": 60},
        "one_family_three_corridors": len(families) == 1 and len(corridors) == 3,
        "protocols_frozen": protocols_valid,
        "config_main_closed": config.get("main_execution_authorized") is False,
        "config_holdout_closed": config.get("holdout_opened") is False
        and config.get("holdout_open_count") == 0,
        "state_marker_absent": not state_path.exists(),
        "exclusive_marker_before_runtime": order_verified,
        "rerun_forbidden": config["holdout_once_contract"]["rerun_authorized"]
        is False,
        "live_camp_head": live_head == camp_head,
        "live_camp_tracked_clean": not live_status,
        "fixed_dp_head": dp_head == FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": not dp_status,
        "disk_floor": free_bytes > 10 * 1024**3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "camp_dp_v24_paired_holdout_main_once_static_authorization_review_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_roots": roots,
        "recomputed_schedule": recomputed_schedule,
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "holdout_state_path": str(state_path),
        "holdout_state_exists": state_path.exists(),
        "holdout_opened": False,
        "holdout_open_count": 0,
        "main_execution_authorized": False,
        "source_authorization_reexecuted": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "outcome_fields_consumed": [],
        "free_bytes_after": free_bytes,
        "next_work_target": "v24_paired_holdout_main_once_execution_authorization_commit_only",
    }
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "review_result.json", result)
    (output_dir / "summary.md").write_text(
        "# v24 holdout main-once authorization review\n\n"
        f"- status/checks/failed: `{result['status']} / {len(checks)} / {len(failed)}`\n"
        "- routes/seeds/pairs: `24 / 5 / 120`\n"
        "- AB/BA: `60/60`\n"
        "- holdout opened/count: `false / 0`\n",
        encoding="utf-8",
    )
    (output_dir / "HEADS.txt").write_text(
        f"CAMP_HEAD={camp_head}\nFIXED_DP_HEAD={dp_head}\n", encoding="ascii"
    )
    (output_dir / "COMMAND.txt").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (output_dir / "run.exit").write_text(
        "0\n" if not failed else "1\n", encoding="ascii"
    )
    result["root_sha256"] = _seal(output_dir)
    if failed:
        raise ValueError(f"v24 holdout authorization review failed: {failed}")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--authorization-root", type=Path, required=True)
    parser.add_argument("--expected-authorization-root-sha256", required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--pilot-review-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-review-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = review_holdout_authorization(
        config_path=args.config,
        authorization_root=args.authorization_root,
        expected_authorization_root_sha256=args.expected_authorization_root_sha256,
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        pilot_review_root=args.pilot_review_root,
        expected_pilot_review_root_sha256=args.expected_pilot_review_root_sha256,
        camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
