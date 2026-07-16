#!/usr/bin/env python3
"""Execute one frozen v24 paired mode from the sealed static preflight."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.evaluation.diffusion_planner_v24_statistics import (  # noqa: E402
    analyze_retained_pairs,
)
from camp_core.integrations.diffusion_planner_v22_native import (  # noqa: E402
    retained_pair_row,
)
from scripts.integrations.prepare_diffusion_planner_v24_paired_evaluation import (  # noqa: E402
    _seal,
    _verify_artifact_root,
    _write_json,
    validate_evaluation_config,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    build_native_arm_runner,
    validate_native_arm_receipt,
    validate_v24_evaluation_run_config,
    verify_config_assets,
)


MODES = frozenset({"capability", "pilot", "main"})


def load_mode_from_preflight(
    config: Mapping[str, Any],
    preflight_root: Path,
    *,
    expected_root_sha256: str,
    mode: str,
    execution_authorized: bool,
    holdout_once_authorized: bool = False,
) -> list[dict[str, Any]]:
    validate_evaluation_config(config, require_all_execution_closed=False)
    if mode not in MODES:
        raise ValueError("unknown v24 paired-evaluation mode")
    if execution_authorized is not True:
        raise ValueError("v24 paired execution requires an explicit gate authorization")
    if mode in {"capability", "pilot"} and config.get(
        "pilot_execution_authorized"
    ) is not True:
        raise ValueError("v24 calibration capability/pilot is not config-authorized")
    if mode == "main" and config.get("main_execution_authorized") is not True:
        raise ValueError("v24 main holdout is not config-authorized")
    if mode == "main" and holdout_once_authorized is not True:
        raise ValueError("v24 main requires explicit holdout-once authorization")
    if mode != "main" and holdout_once_authorized:
        raise ValueError("holdout authorization is invalid outside main")
    if config.get("holdout_opened") is not False or config.get("holdout_open_count") != 0:
        raise ValueError("v24 holdout is already marked opened")
    _verify_artifact_root(preflight_root, expected_root_sha256, "paired_preflight")
    preflight = json.loads(
        (Path(preflight_root) / "preflight_result.json").read_text(encoding="utf-8")
    )
    if (
        preflight.get("status") != "passed"
        or preflight.get("model_loaded") is not False
        or preflight.get("simulator_executed") is not False
        or preflight.get("candidate_generation_started") is not False
        or preflight.get("outcome_fields_consumed") != []
        or preflight.get("holdout_opened") is not False
        or preflight.get("holdout_open_count") != 0
        or preflight.get("planned_pair_counts")
        != {"capability": 1, "pilot": 2, "main": 120}
        or preflight.get("arm_order_counts", {}).get("pilot")
        != {"dp_camp": 1, "camp_dp": 1}
        or preflight.get("arm_order_counts", {}).get("main")
        != {"dp_camp": 60, "camp_dp": 60}
    ):
        raise ValueError("v24 paired static-preflight receipt mismatch")
    configs = [
        json.loads(line)
        for line in (Path(preflight_root) / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    selected = [
        copy.deepcopy(item)
        for item in configs
        if item.get("protocol", {}).get("evaluation_mode") == mode
    ]
    expected = {"capability": 1, "pilot": 2, "main": 120}[mode]
    if len(selected) != expected:
        raise ValueError("v24 preflight mode schedule count mismatch")
    for run_config in selected:
        protocol = run_config["protocol"]
        if protocol.get("execution_authorized") is not False:
            raise ValueError("v24 preflight run config was not disabled")
        protocol["execution_authorized"] = True
        protocol["holdout_access_authorized"] = mode == "main"
        validate_v24_evaluation_run_config(run_config)
    counts = {
        "dp_camp": sum(
            item["protocol"]["arm_order"] == ["dp", "camp"] for item in selected
        ),
        "camp_dp": sum(
            item["protocol"]["arm_order"] == ["camp", "dp"] for item in selected
        ),
    }
    if mode == "pilot" and counts != {"dp_camp": 1, "camp_dp": 1}:
        raise ValueError("pilot arm order is not balanced")
    if mode == "main" and counts != {"dp_camp": 60, "camp_dp": 60}:
        raise ValueError("main arm order is not balanced")
    return selected


def validate_successful_pair(
    dp_arm: Mapping[str, Any],
    camp_arm: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> dict[str, Any]:
    protocol = run_config["protocol"]
    steps = int(protocol["evaluation_steps"])
    validate_native_arm_receipt(
        dp_arm,
        "dp",
        expected_ticks=steps,
        require_summary=steps > 1,
        expected_safety_schema="safety_cost_native_v22",
    )
    validate_native_arm_receipt(
        camp_arm,
        "camp",
        expected_ticks=steps,
        require_summary=steps > 1,
        expected_selection_policy="v22_source_valid",
        expected_safety_schema="safety_cost_native_v22",
    )
    route = run_config["routes"][0]
    expected = {
        "route_name": route["name"],
        "route_sha256": route["sha256"],
        "logical_map_sha256": run_config["map"]["sha256"],
        "fixed_dp_head": run_config["fixed_dp"]["head"],
        "checkpoint_sha256": run_config["fixed_dp"]["checkpoint"]["sha256"],
        "args_sha256": run_config["fixed_dp"]["args_json"]["sha256"],
        "scenario_seed": run_config["seeds"]["scenario"],
    }
    for name, value in expected.items():
        if dp_arm.get(name) != value or camp_arm.get(name) != value:
            raise ValueError(f"v24 paired {name} mismatch")
    for name in ("initial_state_sha256", "initial_input_sha256"):
        if dp_arm.get(name) != camp_arm.get(name):
            raise ValueError(f"v24 paired {name} mismatch")

    for arm, receipt in (("dp", dp_arm), ("camp", camp_arm)):
        ticks = list(receipt["ticks"])
        for tick in ticks:
            before = tick.get("candidate_tensor_sha256_before")
            after = tick.get("candidate_tensor_sha256_after")
            rows = tick.get("candidate_row_sha256")
            identity = tick.get("default_candidate0_identity")
            selected_index = tick.get("selected_index")
            if (
                not isinstance(before, str)
                or len(before) != 64
                or before != after
                or not isinstance(rows, list)
                or len(rows) != 8
                or not isinstance(identity, Mapping)
                or identity.get("elementwise_equal") is not True
                or identity.get("max_abs_difference") != 0.0
                or identity.get("default_output_sha256") != rows[0]
                or identity.get("candidate0_sha256") != rows[0]
                or tick.get("default_output_sha256") != rows[0]
                or isinstance(selected_index, bool)
                or not isinstance(selected_index, int)
                or selected_index < 0
                or selected_index >= 8
                or tick.get("selected_trajectory_sha256") != rows[selected_index]
            ):
                raise ValueError(f"v24 {arm} candidate identity contract mismatch")
            if tick.get("global_rng_sha256_before") != tick.get(
                "global_rng_sha256_after"
            ):
                raise ValueError(f"v24 {arm} candidate work changed global RNG")
            if arm == "dp" and (
                selected_index != 0
                or tick.get("candidate0_operational_default") is not True
                or tick.get("selection_policy") != "candidate0_operational_default"
                or tick.get("score_contract") != "candidate0_operational_default"
            ):
                raise ValueError("v24 DP arm is not candidate-0 operational default")
            if arm == "camp" and (
                tick.get("selection_policy") != "v22_source_valid"
                or tick.get("score_contract") != "score_k(w)=a_k^T w"
            ):
                raise ValueError("v24 CAMP arm selector contract mismatch")
    dp_first = dp_arm["ticks"][0]
    camp_first = camp_arm["ticks"][0]
    for name in (
        "input_sha256",
        "candidate_tensor_sha256_before",
        "candidate_row_sha256",
        "default_output_sha256",
    ):
        if dp_first.get(name) != camp_first.get(name):
            raise ValueError(f"v24 t0 cross-arm {name} mismatch")
    return {
        "per_arm_candidate_immutability_verified": True,
        "per_arm_candidate0_default_identity_verified": True,
        "t0_cross_arm_input_and_candidate_identity_verified": True,
        "post_divergence_cross_arm_tensor_compared": False,
        "native_ranked_k8_provenance_claimed": False,
    }


def execute_mode(
    config: Mapping[str, Any],
    run_configs: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
    camp_head: str,
    preflight_root_sha256: str,
) -> dict[str, Any]:
    if Path(output_dir).exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    free_before = shutil.disk_usage(output_dir).free
    if free_before <= 10 * 1024**3:
        raise ValueError("v24 paired execution violates the 10 GiB disk floor")
    rows = []
    started = time.perf_counter()
    for run_config in run_configs:
        verify_config_assets(run_config)
        protocol = run_config["protocol"]
        route = run_config["routes"][0]
        seed = int(run_config["seeds"]["scenario"])
        pair_key = f"{protocol['evaluation_split']}/{route['name']}/seed_{seed}"
        pair_root = output_dir / protocol["evaluation_split"] / route["name"] / f"seed_{seed}"
        pair_root.mkdir(parents=True)
        arms: dict[str, dict[str, Any]] = {}
        for arm in protocol["arm_order"]:
            arm_started = time.perf_counter()
            try:
                receipt = dict(
                    run_arm(
                        route=route,
                        arm=arm,
                        config=run_config,
                        output_dir=pair_root / "native_runs" / arm,
                        max_steps=int(protocol["evaluation_steps"]),
                    )
                )
            except Exception as exc:
                receipt = _failure_arm(arm, exc)
            receipt["evaluation_wall_clock_s"] = time.perf_counter() - arm_started
            arms[arm] = receipt
            _write_json(pair_root / f"{arm}.json", receipt)
        pair_guards = {
            "per_arm_candidate_immutability_verified": False,
            "per_arm_candidate0_default_identity_verified": False,
            "t0_cross_arm_input_and_candidate_identity_verified": False,
            "post_divergence_cross_arm_tensor_compared": False,
            "native_ranked_k8_provenance_claimed": False,
        }
        if arms["dp"].get("status") == arms["camp"].get("status") == "ok":
            pair_guards = validate_successful_pair(
                arms["dp"], arms["camp"], run_config
            )
        camp_all_high = any(
            bool(tick.get("all_k_high_risk"))
            for tick in arms["camp"].get("ticks", [])
        )
        arms["camp"]["all_k_high_risk"] = camp_all_high
        row = retained_pair_row(
            pair_key=pair_key,
            split=str(protocol["evaluation_split"]),
            dp_arm=arms["dp"],
            camp_arm=arms["camp"],
        )
        row.update(
            {
                "route_retained": True,
                "included_in_denominator": True,
                "replacement_used": False,
                "source_invalid": bool(row["hard_invalid"]),
                "route_identity_sha256": str(route["name"]),
                "map_family_id": str(run_config["map"].get("map_family_id", "pending_from_route_asset_manifest")),
                "corridor_group_sha256": str(run_config["map"].get("corridor_group_sha256", "pending_from_route_asset_manifest")),
                "logical_map_sha256": str(run_config["map"]["logical_map_sha256"]),
                "seed": seed,
                "arm_order": list(protocol["arm_order"]),
                "arm_order_rank_sha256": str(protocol["arm_order_rank_sha256"]),
                "all_k_high_risk": camp_all_high,
                **pair_guards,
            }
        )
        if row["paired_complete"] and int(protocol["evaluation_steps"]) > 1:
            row.update(
                {
                    "dp_safety": arms["dp"]["safety"],
                    "camp_safety": arms["camp"]["safety"],
                    "dp_secondary": arms["dp"]["secondary"],
                    "camp_secondary": arms["camp"]["secondary"],
                    "dp_tick_latency_ms": [tick["latency_ms"] for tick in arms["dp"]["ticks"]],
                    "camp_tick_latency_ms": [tick["latency_ms"] for tick in arms["camp"]["ticks"]],
                    "camp_selected_indices": [int(tick["selected_index"]) for tick in arms["camp"]["ticks"]],
                }
            )
        _write_json(pair_root / "pair.json", row)
        rows.append(row)

    complete = [row for row in rows if row["paired_complete"]]
    free_after = shutil.disk_usage(output_dir).free
    if free_after <= 10 * 1024**3:
        raise ValueError("v24 paired execution crossed the 10 GiB disk floor")
    summary: dict[str, Any] = {
        "schema": "camp_dp_v24_native_paired_execution_summary_v1",
        "status": "complete" if len(complete) == len(rows) else "complete_with_retained_failures",
        "mode": mode,
        "planned_pair_count": len(run_configs),
        "retained_pair_count": len(rows),
        "paired_complete_count": len(complete),
        "source_invalid_pair_count": sum(bool(row["source_invalid"]) for row in rows),
        "execution_failure_pair_count": sum(bool(row["execution_failure"]) for row in rows),
        "arm_order_counts": {
            "dp_camp": sum(row["arm_order"] == ["dp", "camp"] for row in rows),
            "camp_dp": sum(row["arm_order"] == ["camp", "dp"] for row in rows),
        },
        "wall_clock_s": time.perf_counter() - started,
        "free_bytes_before": free_before,
        "free_bytes_after": free_after,
        "camp_head": camp_head,
        "preflight_root_sha256": preflight_root_sha256,
        "holdout_opened": mode == "main",
        "holdout_open_count": 1 if mode == "main" else 0,
        "post_divergence_cross_arm_tensor_compared": False,
        "latency_comparison_authorized": False,
        "final_claim_authorized": False,
    }
    if mode != "capability":
        summary["descriptive_statistics"] = analyze_retained_pairs(
            [row["pair_key"] for row in rows],
            rows,
            claim_evaluation=False,
        )
    _write_json(output_dir / "pair_rows.json", rows)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(
        "# v24 native paired execution\n\n"
        f"- mode: `{mode}`\n"
        f"- planned / retained / complete: `{len(run_configs)} / {len(rows)} / {len(complete)}`\n"
        f"- holdout opened/count: `{mode == 'main'} / {1 if mode == 'main' else 0}`\n"
        "- latency: descriptive instrumented only\n"
        "- final claim authorized: `false`\n",
        encoding="utf-8",
    )
    (output_dir / "HEADS.txt").write_text(
        f"CAMP_HEAD={camp_head}\n", encoding="ascii"
    )
    (output_dir / "COMMAND.txt").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output_dir / "stdout.txt").write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (output_dir / "run.exit").write_text("0\n", encoding="ascii")
    summary["root_sha256"] = _seal(output_dir)
    return summary


def execute_from_preflight(
    *,
    config_path: Path,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    mode: str,
    output_dir: Path,
    device: str,
    camp_head: str,
    execution_authorized: bool,
    holdout_once_authorized: bool,
) -> dict[str, Any]:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    run_configs = load_mode_from_preflight(
        config,
        preflight_root,
        expected_root_sha256=expected_preflight_root_sha256,
        mode=mode,
        execution_authorized=execution_authorized,
        holdout_once_authorized=holdout_once_authorized,
    )
    runner = build_native_arm_runner(run_configs[0], device=device)
    return execute_mode(
        config,
        run_configs,
        mode=mode,
        output_dir=output_dir,
        run_arm=runner,
        camp_head=camp_head,
        preflight_root_sha256=expected_preflight_root_sha256,
    )


def _failure_arm(arm: str, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "failed",
        "arm": arm,
        "failure_stage": "arm_execution",
        "reason": f"{type(exc).__name__}: {exc}",
        "claim_authorized": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--execute-authorized", action="store_true")
    parser.add_argument("--holdout-once-authorized", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = execute_from_preflight(
        config_path=args.config,
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        mode=args.mode,
        output_dir=args.output_dir,
        device=args.device,
        camp_head=args.camp_head,
        execution_authorized=args.execute_authorized,
        holdout_once_authorized=args.holdout_once_authorized,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
