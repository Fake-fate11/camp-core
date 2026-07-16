#!/usr/bin/env python3
"""Independently review sealed v24 calibration capability/pilot receipts."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.prepare_diffusion_planner_v24_paired_evaluation import (  # noqa: E402
    _seal,
    _verify_artifact_root,
    _write_json,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_COUNTS = {"capability": 1, "pilot": 2}
EXPECTED_STEPS = {"capability": 1, "pilot": 64}


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pair_key(run_config: Mapping[str, Any]) -> str:
    protocol = run_config["protocol"]
    route = run_config["routes"][0]
    seed = int(run_config["seeds"]["scenario"])
    return f"{protocol['evaluation_split']}/{route['name']}/seed_{seed}"


def _git_value(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tick_violations(
    tick: Mapping[str, Any], arm: str, tick_index: int
) -> list[str]:
    prefix = f"{arm}.tick_{tick_index}"
    violations: list[str] = []
    rows = tick.get("candidate_row_sha256")
    selected = tick.get("selected_index")
    identity = tick.get("default_candidate0_identity")
    if tick.get("tick_index") != tick_index:
        violations.append(f"{prefix}.index")
    if not isinstance(rows, list) or len(rows) != 8:
        violations.append(f"{prefix}.candidate_rows")
        rows = [None] * 8
    if not isinstance(selected, int) or not 0 <= selected < 8:
        violations.append(f"{prefix}.selected_index")
        selected = 0
    if tick.get("candidate_tensor_sha256_before") != tick.get(
        "candidate_tensor_sha256_after"
    ):
        violations.append(f"{prefix}.candidate_immutability")
    if tick.get("global_rng_sha256_before") != tick.get("global_rng_sha256_after"):
        violations.append(f"{prefix}.global_rng")
    if tick.get("npc_operational_outputs_unchanged") is not True:
        violations.append(f"{prefix}.npc_outputs")
    if not isinstance(identity, Mapping):
        violations.append(f"{prefix}.candidate0_identity")
        identity = {}
    if (
        identity.get("elementwise_equal") is not True
        or float(identity.get("max_abs_difference", math.inf)) != 0.0
        or identity.get("default_output_sha256") != rows[0]
        or identity.get("candidate0_sha256") != rows[0]
        or tick.get("default_output_sha256") != rows[0]
        or identity.get("native_ranked_k8") is not False
    ):
        violations.append(f"{prefix}.candidate0_identity")
    if tick.get("selected_trajectory_sha256") != rows[selected]:
        violations.append(f"{prefix}.selected_row_identity")
    if arm == "dp":
        if (
            selected != 0
            or tick.get("candidate0_operational_default") is not True
            or tick.get("selection_policy") != "candidate0_operational_default"
            or tick.get("score_contract") != "candidate0_operational_default"
        ):
            violations.append(f"{prefix}.dp_operational_default")
    elif (
        tick.get("selection_policy") != "v22_source_valid"
        or tick.get("score_contract") != "score_k(w)=a_k^T w"
        or not isinstance(tick.get("scores"), list)
        or len(tick.get("scores", [])) != 8
        or not isinstance(tick.get("source_valid_mask"), list)
        or len(tick.get("source_valid_mask", [])) != 8
    ):
        violations.append(f"{prefix}.camp_selector")
    return violations


def _inspect_mode(
    execution_root: Path,
    mode: str,
    expected_configs: Sequence[Mapping[str, Any]],
    expected_execution_source_head: str,
) -> dict[str, Any]:
    summary = _load_json(execution_root / "summary.json")
    rows = _load_json(execution_root / "pair_rows.json")
    expected = {_pair_key(item): item for item in expected_configs}
    violations: list[str] = []
    selected_indices: list[int] = []
    safety_deltas: list[float] = []
    arm_orders: Counter[str] = Counter()
    t0_hashes: list[dict[str, str]] = []

    if len(expected) != len(expected_configs):
        violations.append("expected_pair_keys_not_unique")
    if len(rows) != len(expected) or {row.get("pair_key") for row in rows} != set(
        expected
    ):
        violations.append("pair_population")

    for row in rows:
        pair_key = str(row.get("pair_key"))
        run_config = expected.get(pair_key)
        if run_config is None:
            continue
        protocol = run_config["protocol"]
        route = run_config["routes"][0]
        seed = int(run_config["seeds"]["scenario"])
        arm_order = list(protocol["arm_order"])
        arm_orders["dp_camp" if arm_order == ["dp", "camp"] else "camp_dp"] += 1
        required_row = {
            "split": "calibration",
            "seed": seed,
            "arm_order": arm_order,
            "route_retained": True,
            "included_in_denominator": True,
            "replacement_used": False,
            "paired_complete": True,
            "source_invalid": False,
            "execution_failure": False,
            "per_arm_candidate_immutability_verified": True,
            "per_arm_candidate0_default_identity_verified": True,
            "t0_cross_arm_input_and_candidate_identity_verified": True,
            "post_divergence_cross_arm_tensor_compared": False,
            "native_ranked_k8_provenance_claimed": False,
        }
        for name, value in required_row.items():
            if row.get(name) != value:
                violations.append(f"{pair_key}.row.{name}")
        if row.get("route_identity_sha256") != route["name"]:
            violations.append(f"{pair_key}.route_identity")

        pair_root = execution_root / Path(pair_key)
        arms = {
            arm: _load_json(pair_root / f"{arm}.json") for arm in ("dp", "camp")
        }
        for arm, receipt in arms.items():
            if (
                receipt.get("status") != "ok"
                or receipt.get("arm") != arm
                or receipt.get("route_name") != route["name"]
                or receipt.get("route_sha256") != route["sha256"]
                or receipt.get("logical_map_sha256")
                != run_config["map"]["sha256"]
                or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
                or receipt.get("checkpoint_sha256")
                != run_config["fixed_dp"]["checkpoint"]["sha256"]
                or receipt.get("args_sha256")
                != run_config["fixed_dp"]["args_json"]["sha256"]
                or receipt.get("scenario_seed") != seed
                or receipt.get("claim_authorized") is not False
            ):
                violations.append(f"{pair_key}.{arm}.base_contract")
            ticks = receipt.get("ticks")
            if not isinstance(ticks, list) or len(ticks) != EXPECTED_STEPS[mode]:
                violations.append(f"{pair_key}.{arm}.tick_count")
                continue
            for index, tick in enumerate(ticks):
                violations.extend(_tick_violations(tick, arm, index))
            if receipt.get("initial_input_sha256") != ticks[0].get("input_sha256"):
                violations.append(f"{pair_key}.{arm}.initial_input")

        base_fields = (
            "initial_state_sha256",
            "initial_input_sha256",
            "spawn_config_sha256",
            "scenario_seed",
            "fixed_dp_head",
            "checkpoint_sha256",
            "args_sha256",
        )
        if any(arms["dp"].get(name) != arms["camp"].get(name) for name in base_fields):
            violations.append(f"{pair_key}.paired_reset_contract")
        dp_t0 = arms["dp"]["ticks"][0]
        camp_t0 = arms["camp"]["ticks"][0]
        t0_fields = (
            "input_sha256",
            "candidate_tensor_sha256_before",
            "candidate_row_sha256",
            "candidate_neighbor_sha256",
            "default_output_sha256",
        )
        if any(dp_t0.get(name) != camp_t0.get(name) for name in t0_fields):
            violations.append(f"{pair_key}.t0_cross_arm_identity")
        t0_hashes.append(
            {
                "pair_key": pair_key,
                "input_sha256": str(dp_t0["input_sha256"]),
                "candidate_tensor_sha256": str(
                    dp_t0["candidate_tensor_sha256_before"]
                ),
            }
        )
        selected_indices.extend(
            int(tick["selected_index"]) for tick in arms["camp"]["ticks"]
        )
        if mode == "pilot":
            safety_deltas.append(
                float(arms["camp"]["safety"]["safety_cost"])
                - float(arms["dp"]["safety"]["safety_cost"])
            )

    if summary.get("mode") != mode:
        violations.append("summary.mode")
    if summary.get("camp_head") != expected_execution_source_head:
        violations.append("summary.camp_head")
    expected_count = EXPECTED_COUNTS[mode]
    for name, value in {
        "planned_pair_count": expected_count,
        "retained_pair_count": expected_count,
        "paired_complete_count": expected_count,
        "source_invalid_pair_count": 0,
        "execution_failure_pair_count": 0,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "post_divergence_cross_arm_tensor_compared": False,
        "latency_comparison_authorized": False,
        "final_claim_authorized": False,
    }.items():
        if summary.get(name) != value:
            violations.append(f"summary.{name}")

    stats_checks: dict[str, Any] = {}
    if mode == "pilot":
        stats = summary.get("descriptive_statistics", {})
        overall = stats.get("strata", {}).get("overall", {})
        expected_btw = {
            "better": sum(value < -1e-12 for value in safety_deltas),
            "tie": sum(abs(value) <= 1e-12 for value in safety_deltas),
            "worse": sum(value > 1e-12 for value in safety_deltas),
        }
        selection = stats.get("candidate_selection", {})
        stats_checks = {
            "safety_mean": math.isclose(
                float(overall.get("mean", math.nan)), mean(safety_deltas), abs_tol=1e-12
            ),
            "safety_median": math.isclose(
                float(overall.get("median", math.nan)),
                median(safety_deltas),
                abs_tol=1e-12,
            ),
            "better_tie_worse": overall.get("better_tie_worse") == expected_btw,
            "candidate_tick_count": selection.get("tick_count")
            == len(selected_indices),
            "candidate0_count": selection.get("candidate0_selection_count")
            == sum(index == 0 for index in selected_indices),
            "non_candidate0_count": selection.get("non_candidate0_selection_count")
            == sum(index != 0 for index in selected_indices),
            "latency_descriptive_only": stats.get("latency_comparison_authorized")
            is False
            and stats.get("latency_reporting_role")
            == "descriptive_instrumented_only",
            "claim_preclosed": stats.get("claim_decision", {}).get("decision")
            == "honest_no_claim",
        }
        violations.extend(
            f"pilot_stats.{name}" for name, passed in stats_checks.items() if not passed
        )

    return {
        "mode": mode,
        "pair_count": len(rows),
        "tick_count_per_arm": sum(EXPECTED_STEPS[mode] for _ in rows),
        "arm_order_counts": dict(arm_orders),
        "camp_candidate0_count": sum(index == 0 for index in selected_indices),
        "camp_non_candidate0_count": sum(index != 0 for index in selected_indices),
        "safety_cost_deltas": safety_deltas,
        "t0_hashes": t0_hashes,
        "post_divergence_cross_arm_tensor_compared": False,
        "stats_checks": stats_checks,
        "violations": violations,
    }


def review_calibration_pilot(
    *,
    config_path: Path,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    capability_root: Path,
    expected_capability_root_sha256: str,
    pilot_root: Path,
    expected_pilot_root_sha256: str,
    expected_execution_source_head: str,
    camp_head: str,
    output_dir: Path,
) -> dict[str, Any]:
    roots = {
        "preflight": _verify_artifact_root(
            preflight_root, expected_preflight_root_sha256, "paired_preflight"
        ),
        "capability": _verify_artifact_root(
            capability_root, expected_capability_root_sha256, "paired_capability"
        ),
        "pilot": _verify_artifact_root(
            pilot_root, expected_pilot_root_sha256, "paired_pilot"
        ),
    }
    config = _load_json(config_path)
    run_configs = [
        json.loads(line)
        for line in (preflight_root / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    by_mode = {
        mode: [
            item
            for item in run_configs
            if item["protocol"]["evaluation_mode"] == mode
        ]
        for mode in EXPECTED_COUNTS
    }
    capability = _inspect_mode(
        capability_root,
        "capability",
        by_mode["capability"],
        expected_execution_source_head,
    )
    pilot = _inspect_mode(
        pilot_root,
        "pilot",
        by_mode["pilot"],
        expected_execution_source_head,
    )
    live_head = _git_value(ROOT, "rev-parse", "HEAD")
    live_status = _git_value(ROOT, "status", "--porcelain", "--untracked-files=no")
    dp_repo = Path(str(by_mode["pilot"][0]["fixed_dp"]["repo"]))
    dp_head = _git_value(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_value(dp_repo, "status", "--porcelain")
    free_bytes = shutil.disk_usage(output_dir.parent).free

    checks = {
        "source_roots_verified": all(item["root_sha256"] for item in roots.values()),
        "live_camp_head": live_head == camp_head,
        "live_camp_tracked_clean": not live_status,
        "fixed_dp_head": dp_head == FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": not dp_status,
        "pilot_only_authorized": config.get("pilot_execution_authorized") is True,
        "main_closed": config.get("main_execution_authorized") is False,
        "holdout_closed": config.get("holdout_opened") is False
        and config.get("holdout_open_count") == 0,
        "claim_closed": config.get("claim_authorized") is False,
        "capability_schedule_count": len(by_mode["capability"]) == 1,
        "pilot_schedule_count": len(by_mode["pilot"]) == 2,
        "capability_receipts": not capability["violations"],
        "pilot_receipts": not pilot["violations"],
        "pilot_arm_order_balance": pilot["arm_order_counts"]
        == {"dp_camp": 1, "camp_dp": 1},
        "capability_pair_complete": capability["pair_count"] == 1,
        "pilot_pairs_complete": pilot["pair_count"] == 2,
        "capability_ticks": capability["tick_count_per_arm"] == 1,
        "pilot_ticks": pilot["tick_count_per_arm"] == 128,
        "t0_cross_arm_identity": len(capability["t0_hashes"]) == 1
        and len(pilot["t0_hashes"]) == 2,
        "post_divergence_not_compared": capability[
            "post_divergence_cross_arm_tensor_compared"
        ]
        is False
        and pilot["post_divergence_cross_arm_tensor_compared"] is False,
        "pilot_statistics_recomputed": all(pilot["stats_checks"].values()),
        "latency_comparison_closed": config["arm_order_policy"][
            "latency_comparison_authorized"
        ]
        is False,
        "no_holdout_pairs_reviewed": all(
            item["protocol"]["evaluation_split"] == "calibration"
            for mode in ("capability", "pilot")
            for item in by_mode[mode]
        ),
        "disk_floor": free_bytes > 10 * 1024**3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "camp_dp_v24_paired_calibration_pilot_independent_review_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_roots": roots,
        "capability": capability,
        "pilot": pilot,
        "camp_head": camp_head,
        "execution_source_head": expected_execution_source_head,
        "fixed_dp_head": dp_head,
        "free_bytes_after_review": free_bytes,
        "source_execution_reexecuted": False,
        "model_loaded": False,
        "runner_built": False,
        "simulator_executed": False,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "latency_comparison_authorized": False,
        "pilot_effect_claim_authorized": False,
        "main_execution_authorized": False,
        "next_work_target": "v24_paired_holdout_main_once_plan_static_preflight_only",
    }
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "review_result.json", result)
    (output_dir / "summary.md").write_text(
        "# v24 paired calibration pilot independent review\n\n"
        f"- status/checks/failed: `{result['status']} / {len(checks)} / {len(failed)}`\n"
        "- capability/pilot pairs: `1 / 2`\n"
        "- pilot AB/BA: `1/1`\n"
        "- holdout opened/count: `false / 0`\n"
        "- latency/effect claim: descriptive only / unauthorized\n",
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
        raise ValueError(f"v24 calibration pilot review failed: {failed}")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--capability-root", type=Path, required=True)
    parser.add_argument("--expected-capability-root-sha256", required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-root-sha256", required=True)
    parser.add_argument("--expected-execution-source-head", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = review_calibration_pilot(
        config_path=args.config,
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        capability_root=args.capability_root,
        expected_capability_root_sha256=args.expected_capability_root_sha256,
        pilot_root=args.pilot_root,
        expected_pilot_root_sha256=args.expected_pilot_root_sha256,
        expected_execution_source_head=args.expected_execution_source_head,
        camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
