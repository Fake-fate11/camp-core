#!/usr/bin/env python3
"""Prepare a sealed, outcome-free authorization for v24 holdout main once."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.prepare_diffusion_planner_v24_paired_evaluation import (  # noqa: E402
    _seal,
    _verify_artifact_root,
    _write_json,
    validate_evaluation_config,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
HOLDOUT_SEEDS = [24201, 24202, 24203, 24204, 24205]
GLOBAL_LOCK = "/root/autodl-tmp/camp_dp_v24_paired_evaluation.global.lock"


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_value(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _active_evaluators() -> list[str]:
    output = subprocess.run(
        ["ps", "-eo", "args="],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pattern = re.compile(
        r"^\S*python\S*\s+.*evaluate_diffusion_planner_v24_pairs\.py(?:\s|$)"
    )
    return [line for line in output.splitlines() if pattern.search(line)]


def _lock_is_held(path: str) -> bool:
    completed = subprocess.run(
        ["lslocks", "--noheadings", "--output", "PATH"],
        check=False,
        capture_output=True,
        text=True,
    )
    return any(line.strip() == path for line in completed.stdout.splitlines())


def _schedule_receipt(main_configs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pair_keys: list[str] = []
    route_seeds: dict[str, set[int]] = defaultdict(set)
    orders: Counter[str] = Counter()
    map_families: set[str] = set()
    corridors: set[str] = set()
    violations: list[str] = []
    for item in main_configs:
        protocol = item.get("protocol", {})
        route = item.get("routes", [{}])[0]
        seed = int(item.get("seeds", {}).get("scenario", -1))
        route_name = str(route.get("name"))
        pair_key = f"{protocol.get('evaluation_split')}/{route_name}/seed_{seed}"
        pair_keys.append(pair_key)
        route_seeds[route_name].add(seed)
        order = protocol.get("arm_order")
        orders["dp_camp" if order == ["dp", "camp"] else "camp_dp"] += 1
        map_families.add(str(item.get("map", {}).get("map_family_id")))
        corridors.add(str(item.get("map", {}).get("corridor_group_sha256")))
        if (
            protocol.get("evaluation_mode") != "main"
            or protocol.get("evaluation_split") != "holdout"
            or protocol.get("evaluation_steps") != 64
            or protocol.get("execution_authorized") is not False
            or protocol.get("holdout_access_authorized") is not False
            or protocol.get("independent_reset_per_arm") is not True
            or protocol.get("same_initial_state_and_exogenous_seed_per_pair")
            is not True
            or protocol.get("route_retention")
            != "all_preregistered_routes_and_failures_no_replacement"
            or protocol.get("per_arm_candidate_tensor_immutability_required")
            is not True
            or protocol.get("per_arm_candidate0_default_identity_required") is not True
            or protocol.get("t0_cross_arm_input_and_candidate_hash_identity_required")
            is not True
            or protocol.get("post_divergence_cross_arm_tensor_identity_required")
            is not False
            or protocol.get("latency_comparison_authorized") is not False
            or protocol.get("claim_authorized") is not False
            or seed not in HOLDOUT_SEEDS
        ):
            violations.append(pair_key)
    return {
        "pair_count": len(main_configs),
        "unique_pair_count": len(set(pair_keys)),
        "route_count": len(route_seeds),
        "route_seed_sets_exact": all(
            sorted(seeds) == HOLDOUT_SEEDS for seeds in route_seeds.values()
        ),
        "arm_order_counts": dict(orders),
        "map_family_count": len(map_families),
        "corridor_group_count": len(corridors),
        "violations": violations,
    }


def prepare_holdout_authorization(
    *,
    config_path: Path,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    camp_head: str,
    output_dir: Path,
) -> dict[str, Any]:
    roots = {
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
    validate_evaluation_config(config, require_all_execution_closed=False)
    preflight = _load_json(preflight_root / "preflight_result.json")
    plan = _load_json(preflight_root / "evaluation_plan.json")
    pilot_review = _load_json(pilot_review_root / "review_result.json")
    run_configs = [
        json.loads(line)
        for line in (preflight_root / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    main_configs = [
        item for item in run_configs if item["protocol"]["evaluation_mode"] == "main"
    ]
    schedule = _schedule_receipt(main_configs)
    holdout_contract = config["holdout_once_contract"]
    state_path = Path(str(holdout_contract["state_path"]))
    live_head = _git_value(ROOT, "rev-parse", "HEAD")
    live_status = _git_value(ROOT, "status", "--porcelain", "--untracked-files=no")
    dp_repo = Path(str(main_configs[0]["fixed_dp"]["repo"]))
    dp_head = _git_value(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_value(dp_repo, "status", "--porcelain")
    evaluator_source = (
        ROOT / "scripts" / "integrations" / "evaluate_diffusion_planner_v24_pairs.py"
    ).read_text(encoding="utf-8")
    execute_source = evaluator_source.split("def execute_from_preflight(", 1)[1]
    authorization_index = execute_source.index("_verify_artifact_root(")
    marker_index = execute_source.index("claim_holdout_once_state(")
    runner_index = execute_source.index("runner = build_native_arm_runner(")
    free_bytes = shutil.disk_usage(output_dir.parent).free
    active = _active_evaluators()
    lock_held = _lock_is_held(GLOBAL_LOCK)

    checks = {
        "source_roots_verified": all(item["root_sha256"] for item in roots.values()),
        "preflight_passed": preflight.get("status") == "passed",
        "preflight_main_120": preflight.get("planned_pair_counts", {}).get("main")
        == 120,
        "preflight_holdout_closed": preflight.get("holdout_opened") is False
        and preflight.get("holdout_open_count") == 0,
        "preflight_no_outcomes": preflight.get("outcome_fields_consumed") == [],
        "pilot_review_passed": pilot_review.get("status") == "passed"
        and pilot_review.get("failed_count") == 0,
        "pilot_review_holdout_closed": pilot_review.get("holdout_opened") is False
        and pilot_review.get("holdout_open_count") == 0,
        "pilot_review_no_reexecution": pilot_review.get("source_execution_reexecuted")
        is False,
        "config_pilot_authorized": config.get("pilot_execution_authorized") is True,
        "config_main_closed": config.get("main_execution_authorized") is False,
        "config_holdout_closed": config.get("holdout_opened") is False
        and config.get("holdout_open_count") == 0,
        "config_claim_closed": config.get("claim_authorized") is False,
        "state_marker_absent": not state_path.exists(),
        "state_contract_exclusive": holdout_contract.get(
            "exclusive_create_before_runner_build"
        )
        is True
        and holdout_contract.get("rerun_authorized") is False,
        "authorization_before_marker_before_runner": authorization_index
        < marker_index
        < runner_index,
        "main_pair_count": schedule["pair_count"] == 120,
        "main_pair_keys_unique": schedule["unique_pair_count"] == 120,
        "main_route_count": schedule["route_count"] == 24,
        "main_route_seed_sets": schedule["route_seed_sets_exact"] is True,
        "main_arm_order_balance": schedule["arm_order_counts"]
        == {"dp_camp": 60, "camp_dp": 60},
        "main_one_map_family": schedule["map_family_count"] == 1,
        "main_three_corridors": schedule["corridor_group_count"] == 3,
        "main_protocols_frozen": not schedule["violations"],
        "plan_primary_ci": plan.get("primary_ci_cluster_hierarchy")
        == ["corridor_group_sha256", "route_identity_sha256", "seed"],
        "plan_map_family_ci_forbidden": plan.get("map_family_level_ci_authorized")
        is False,
        "plan_post_divergence_noncomparability": plan.get(
            "post_divergence_cross_arm_tensor_identity_required"
        )
        is False,
        "latency_comparison_closed": config["arm_order_policy"][
            "latency_comparison_authorized"
        ]
        is False,
        "coverage_gates_frozen": config["coverage_execution_contract"][
            "planned_pair_retention_rate_min"
        ]
        == 1.0
        and config["coverage_execution_contract"][
            "paired_complete_rate_min_for_claim"
        ]
        == 1.0
        and config["coverage_execution_contract"][
            "source_invalid_pair_rate_max_for_claim"
        ]
        == 0.0
        and config["coverage_execution_contract"][
            "execution_invalid_pair_rate_max_for_claim"
        ]
        == 0.0,
        "live_camp_head": live_head == camp_head,
        "live_camp_tracked_clean": not live_status,
        "fixed_dp_head": dp_head == FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": not dp_status,
        "no_active_evaluator": not active,
        "global_lock_free": not lock_held,
        "disk_floor": free_bytes > 10 * 1024**3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "camp_dp_v24_paired_holdout_main_once_static_authorization_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_roots": roots,
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "main_pair_count": schedule["pair_count"],
        "main_route_count": schedule["route_count"],
        "main_seed_count_per_route": len(HOLDOUT_SEEDS),
        "arm_order_counts": schedule["arm_order_counts"],
        "holdout_map_family_count": schedule["map_family_count"],
        "holdout_corridor_group_count": schedule["corridor_group_count"],
        "holdout_state_path": str(state_path),
        "holdout_state_exists": state_path.exists(),
        "holdout_opened": False,
        "holdout_open_count": 0,
        "main_execution_authorized": False,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "active_evaluators": active,
        "global_lock_held": lock_held,
        "free_bytes_after": free_bytes,
        "next_work_target": "v24_paired_holdout_main_once_execution_authorization_commit_only",
    }
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "authorization_result.json", result)
    _write_json(output_dir / "schedule_receipt.json", schedule)
    (output_dir / "summary.md").write_text(
        "# v24 holdout main-once static authorization\n\n"
        f"- status/checks/failed: `{result['status']} / {len(checks)} / {len(failed)}`\n"
        "- holdout routes/seeds/pairs: `24 / 5 / 120`\n"
        "- AB/BA: `60/60`\n"
        "- holdout opened/count: `false / 0`\n"
        "- runner/model/simulator/outcomes: not opened\n",
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
        raise ValueError(f"v24 holdout main-once authorization failed: {failed}")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--pilot-review-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-review-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = prepare_holdout_authorization(
        config_path=args.config,
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
