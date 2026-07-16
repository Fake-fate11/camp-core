#!/usr/bin/env python3
"""Independent read-only review of a sealed v24 paired static preflight."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.prepare_diffusion_planner_v24_paired_evaluation import (  # noqa: E402
    _file_sha256,
    _load_and_validate_selector,
    _seal,
    _verify_artifact_root,
    _write_json,
    build_evaluation_plan,
    review_learning_curve_stability,
    validate_evaluation_config,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    validate_v24_evaluation_run_config,
)


def review_preflight(
    *,
    config_path: Path,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    camp_head: str,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    validate_evaluation_config(config)
    source_receipt = _verify_artifact_root(
        preflight_root,
        expected_preflight_root_sha256,
        "paired_static_preflight",
    )
    preflight = json.loads(
        (preflight_root / "preflight_result.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (preflight_root / "evaluation_plan.json").read_text(encoding="utf-8")
    )
    routes = json.loads(
        (preflight_root / "route_assets.json").read_text(encoding="utf-8")
    )
    run_receipts = json.loads(
        (preflight_root / "run_config_receipts.json").read_text(encoding="utf-8")
    )
    run_configs = [
        json.loads(line)
        for line in (preflight_root / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    split_source = config["source_split"]
    census_source = config["source_route_census"]
    split = json.loads(
        Path(split_source["manifest_path"]).read_text(encoding="utf-8")
    )
    census = json.loads(
        Path(census_source["census_path"]).read_text(encoding="utf-8")
    )
    recomputed = build_evaluation_plan(config, split, census)
    public = copy.deepcopy(recomputed)
    for rows in public["schedules"].values():
        for row in rows:
            row.pop("route", None)
    model, source_weights, source_scales = _load_and_validate_selector(config)
    runtime_root = preflight_root / "runtime_selector"
    runtime_receipt = _verify_artifact_root(
        runtime_root,
        preflight["selector_runtime_root_sha256"],
        "runtime_selector",
    )
    runtime_weights = np.load(runtime_root / "weights.npy", allow_pickle=False)
    runtime_scales_payload = json.loads(
        (runtime_root / "atom_scales.json").read_text(encoding="utf-8")
    )
    runtime_scales = np.asarray(runtime_scales_payload["scales"], dtype=np.float64)
    recomputed_stability = review_learning_curve_stability(config)
    sealed_stability = json.loads(
        (preflight_root / "learning_curve_stability.json").read_text(
            encoding="utf-8"
        )
    )
    route_hashes_valid = all(
        _file_sha256(Path(item["route_asset"]["path"]))
        == item["route_asset"]["sha256"]
        for item in routes
    )
    for run_config in run_configs:
        validate_v24_evaluation_run_config(run_config)
    arm_orders = {
        mode: {
            "dp_camp": sum(
                row["arm_order"] == ["dp", "camp"]
                for row in plan["schedules"][mode]
            ),
            "camp_dp": sum(
                row["arm_order"] == ["camp", "dp"]
                for row in plan["schedules"][mode]
            ),
        }
        for mode in ("capability", "pilot", "main")
    }
    producer_source = (
        ROOT
        / "scripts"
        / "integrations"
        / "prepare_diffusion_planner_v24_paired_evaluation.py"
    ).read_text(encoding="utf-8")
    checks = {
        "source_preflight_root": source_receipt["root_sha256"]
        == expected_preflight_root_sha256,
        "source_preflight_passed": preflight.get("status") == "passed",
        "source_preflight_no_model_or_simulator": preflight.get("model_loaded")
        is False
        and preflight.get("runner_built") is False
        and preflight.get("simulator_executed") is False
        and preflight.get("candidate_generation_started") is False,
        "source_preflight_no_outcomes": preflight.get("outcome_fields_consumed")
        == [],
        "source_preflight_holdout_closed": preflight.get("holdout_opened")
        is False
        and preflight.get("holdout_open_count") == 0,
        "recomputed_plan_exact": public == plan,
        "route_counts": plan.get("route_counts")
        == {"train": 375, "calibration": 2, "holdout": 24},
        "pair_counts": plan.get("planned_pair_counts")
        == {"capability": 1, "pilot": 2, "main": 120},
        "arm_order_balance": arm_orders["pilot"]
        == {"dp_camp": 1, "camp_dp": 1}
        and arm_orders["main"] == {"dp_camp": 60, "camp_dp": 60},
        "one_family_three_corridors": plan.get("holdout_map_family_count") == 1
        and plan.get("holdout_corridor_group_count") == 3,
        "map_family_ci_forbidden": plan.get("map_family_level_ci_authorized")
        is False,
        "route_asset_count_26": len(routes) == 26,
        "route_asset_hashes": route_hashes_valid,
        "disabled_run_config_count_123": len(run_configs) == 123
        and len(run_receipts) == 123,
        "all_configs_disabled": all(
            item["protocol"]["execution_authorized"] is False
            and item["protocol"]["holdout_access_authorized"] is False
            for item in run_configs
        ),
        "runtime_selector_root": runtime_receipt["root_sha256"]
        == preflight["selector_runtime_root_sha256"],
        "runtime_weights_exact": np.array_equal(runtime_weights, source_weights)
        and np.array_equal(source_weights, np.asarray(model["weights"])),
        "runtime_scales_exact": np.array_equal(runtime_scales, source_scales),
        "learning_curve_stability_exact": sealed_stability
        == recomputed_stability,
        "training_failure_disclosure": preflight.get(
            "train_source_coverage_disclosure"
        )
        == {
            "retained": 1875,
            "complete": 1054,
            "failed": 821,
            "failure_rate": 0.4378666666666667,
        },
        "producer_has_no_runner_build": "build_native_arm_runner(" not in producer_source,
        "producer_has_no_simulator_call": "run_route_replay(" not in producer_source,
        "producer_has_no_holdout_outcome_read": "analyze_retained_pairs(" not in producer_source,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "camp_dp_v24_native_paired_evaluation_static_preflight_review_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_preflight_root_sha256": expected_preflight_root_sha256,
        "source_preflight_file_count": source_receipt["file_count"],
        "runtime_selector_root_sha256": runtime_receipt["root_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "route_counts": plan["route_counts"],
        "planned_pair_counts": plan["planned_pair_counts"],
        "arm_order_counts": arm_orders,
        "holdout_map_family_count": plan["holdout_map_family_count"],
        "holdout_corridor_group_count": plan["holdout_corridor_group_count"],
        "learning_curve_stability": recomputed_stability,
        "camp_head": camp_head,
        "source_preflight_reexecuted": False,
        "model_loaded": False,
        "runner_built": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "pilot_execution_authorized": False,
        "main_execution_authorized": False,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "claim_authorized": False,
        "next_work_target": "v24_paired_calibration_capability_pilot_execution_only",
    }
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "review_result.json", result)
    (output_dir / "summary.md").write_text(
        "# v24 paired static-preflight independent review\n\n"
        f"- status/checks/failed: `{result['status']} / {len(checks)} / {len(failed)}`\n"
        "- routes train/calibration/holdout: `375 / 2 / 24`\n"
        "- capability/pilot/main pairs: `1 / 2 / 120`\n"
        "- pilot/main AB/BA: `1/1` and `60/60`\n"
        "- model/simulator/candidates/outcomes/holdout: not opened\n",
        encoding="utf-8",
    )
    (output_dir / "HEADS.txt").write_text(f"CAMP_HEAD={camp_head}\n", encoding="ascii")
    (output_dir / "COMMAND.txt").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output_dir / "stdout.txt").write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (output_dir / "run.exit").write_text("0\n" if not failed else "1\n", encoding="ascii")
    result["root_sha256"] = _seal(output_dir)
    if failed:
        raise ValueError(f"v24 paired static-preflight review failed: {failed}")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = review_preflight(
        config_path=args.config,
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
