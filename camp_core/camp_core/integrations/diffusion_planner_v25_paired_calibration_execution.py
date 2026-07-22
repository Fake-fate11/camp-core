from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from .diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
)
from .diffusion_planner_v25_paired_calibration import (
    ARM_RUN_COUNT,
    PAIR_COUNT,
    TICKS_PER_ARM_RUN,
    validate_paired_calibration_execution_plan,
)
from .diffusion_planner_v25_signal_complete_execution import (
    build_paired_calibration_arm_config,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_execution_v1"
CORPUS_SCHEMA_VERSION = "camp_dp_v25_paired_calibration_corpus_v1"
RUN_RESULT_SCHEMA_VERSION = "camp_dp_v25_paired_calibration_arm_result_v1"
FAILURE_SCHEMA_VERSION = "camp_dp_v25_paired_calibration_k8_failure_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RunOne = Callable[[Mapping[str, Any], Path, str], Mapping[str, Any]]
ProgressSink = Callable[[Mapping[str, Any]], None]


def execute_paired_calibration_units(
    *,
    calibration_plan: Mapping[str, Any],
    paired_plan: Mapping[str, Any],
    probe_template: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    route_asset_by_identity: Mapping[str, Mapping[str, Any]],
    runtime_selector_authority: Mapping[str, Any],
    dp_repo: Path,
    output_dir: Path,
    run_one: RunOne,
    progress_sink: ProgressSink | None = None,
) -> dict[str, Any]:
    """Run all three frozen calibration arms for all 100 paired units."""

    base = validate_signal_complete_execution_plan(calibration_plan)
    plan = validate_paired_calibration_execution_plan(
        paired_plan, calibration_plan=base
    )
    if (
        plan["pair_count"] != PAIR_COUNT
        or plan["arm_run_count"] != ARM_RUN_COUNT
        or plan["ticks_per_arm_run"] != TICKS_PER_ARM_RUN
    ):
        raise ValueError("paired calibration execution denominator drifted")
    expected_scenarios = {
        row["scenario_identity_sha256"] for row in plan["identities"]
    }
    expected_routes = {row["route_identity_sha256"] for row in plan["identities"]}
    if (
        type(prepared_runtime_by_scenario) is not dict
        or set(prepared_runtime_by_scenario) != expected_scenarios
    ):
        raise ValueError("paired calibration runtime inventory drifted")
    if (
        type(route_asset_by_identity) is not dict
        or set(route_asset_by_identity) != expected_routes
    ):
        raise ValueError("paired calibration route inventory drifted")

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    runs_root = output / "runs"
    runs_root.mkdir()
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    results: list[dict[str, Any]] = []
    run_ordinal = 0
    for unit in plan["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        route_asset = route_asset_by_identity[identity["route_identity_sha256"]]
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            config = build_paired_calibration_arm_config(
                probe_template=probe_template,
                prepared_runtime=prepared_runtime_by_scenario[
                    unit["scenario_identity_sha256"]
                ],
                execution_unit=unit,
                plan_arm=plan_arm,
                route_asset=route_asset,
                dp_repo=dp_repo,
                runtime_selector_authority=runtime_selector_authority,
            )
            run_dir = runs_root / (
                f"{run_ordinal:04d}_{unit['unit_ordinal']:04d}_"
                f"{arm_order_index}_{plan_arm}"
            )
            run_dir.mkdir()
            _write_json(run_dir / "run_config.json", config)
            try:
                native = dict(run_one(config, run_dir, plan_arm))
                result = _complete_result(
                    unit=unit,
                    identity=identity,
                    native=native,
                    plan_arm=plan_arm,
                    arm_order_index=arm_order_index,
                    run_ordinal=run_ordinal,
                    expected_route_sha256=route_asset["sha256"],
                )
            except FixedDpCandidateGenerationCapabilityFailure as failure:
                result = _failure_result(
                    output=output,
                    unit=unit,
                    identity=identity,
                    plan_arm=plan_arm,
                    arm_order_index=arm_order_index,
                    run_ordinal=run_ordinal,
                    failure=failure,
                )
            _write_json(run_dir / "terminal.json", result)
            results.append(result)
            if progress_sink is not None:
                progress_sink(
                    {
                        "schema_version": "camp_dp_v25_paired_calibration_progress_v1",
                        "status": "running",
                        "planned_arm_run_count": ARM_RUN_COUNT,
                        "terminal_arm_run_count": len(results),
                        "complete_arm_run_count": sum(
                            row["status"] == "complete" for row in results
                        ),
                        "retained_fixed_dp_capability_failure_count": sum(
                            row["status"]
                            == "retained_fixed_dp_capability_failure"
                            for row in results
                        ),
                        "last_run_ordinal": run_ordinal,
                        "last_unit_ordinal": unit["unit_ordinal"],
                        "last_plan_arm": plan_arm,
                        "fresh_b2_opened": False,
                        "fresh_outcome_fields_consumed": [],
                    }
                )
            run_ordinal += 1

    corpus = project_paired_calibration_corpus(plan=plan, results=results)
    _write_json(output / "run_results.json", results)
    _write_json(output / "paired_calibration_corpus.json", corpus)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "passed_paired_calibration_execution"
            if corpus["status"] == "passed_paired_calibration_corpus"
            else "paired_calibration_execution_scientifically_ineligible"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "pair_count": PAIR_COUNT,
        "planned_arm_run_count": ARM_RUN_COUNT,
        "terminal_arm_run_count": len(results),
        "complete_arm_run_count": corpus["complete_arm_run_count"],
        "retained_fixed_dp_capability_failure_count": corpus[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_pair_count": corpus["paired_eligible_pair_count"],
        "paired_eligible_rate": corpus["paired_eligible_rate"],
        "coverage_gate_passed": corpus["coverage_gate_passed"],
        "run_results_sha256": _canonical_sha(results),
        "paired_calibration_corpus_sha256": _canonical_sha(corpus),
        "independent_reset_per_arm": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def project_paired_calibration_corpus(
    *, plan: Mapping[str, Any], results: list[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(results) != ARM_RUN_COUNT:
        raise ValueError("paired calibration requires exactly 300 terminal arm rows")
    normalized = [dict(row) for row in results]
    expected = []
    ordinal = 0
    for unit in plan["execution_units"]:
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            expected.append(
                (
                    ordinal,
                    unit["unit_ordinal"],
                    unit["unit_sha256"],
                    arm_order_index,
                    plan_arm,
                )
            )
            ordinal += 1
    actual = [
        (
            row.get("run_ordinal"),
            row.get("unit_ordinal"),
            row.get("unit_sha256"),
            row.get("arm_order_index"),
            row.get("plan_arm"),
        )
        for row in normalized
    ]
    if actual != expected:
        raise ValueError("paired calibration terminal order drifted")
    allowed = {"complete", "retained_fixed_dp_capability_failure"}
    if any(row.get("status") not in allowed for row in normalized):
        raise ValueError("paired calibration terminal status drifted")

    identity_by_sha = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    by_pair: dict[int, list[dict[str, Any]]] = defaultdict(list)
    complete_by_arm: Counter[str] = Counter()
    failure_by_arm: Counter[str] = Counter()
    for row in normalized:
        by_pair[int(row["unit_ordinal"])].append(row)
        if row["status"] == "complete":
            complete_by_arm[str(row["plan_arm"])] += 1
        else:
            failure_by_arm[str(row["plan_arm"])] += 1
    if set(by_pair) != set(range(PAIR_COUNT)) or any(
        len(rows) != 3 for rows in by_pair.values()
    ):
        raise ValueError("paired calibration pair denominator drifted")

    eligible_units = {
        unit_ordinal
        for unit_ordinal, rows in by_pair.items()
        if all(row["status"] == "complete" for row in rows)
    }
    pair_rate = len(eligible_units) / PAIR_COUNT
    family_denominator: Counter[str] = Counter()
    family_eligible: Counter[str] = Counter()
    source_denominator: Counter[str] = Counter()
    source_eligible: Counter[str] = Counter()
    family_tier_denominator: Counter[str] = Counter()
    family_tier_eligible: Counter[str] = Counter()
    for unit in plan["execution_units"]:
        identity = identity_by_sha[unit["scenario_identity_sha256"]]
        family = str(identity["scenario_family"])
        source = str(identity["signal_source_class"])
        family_tier = f"{family}/{identity['risk_tier']}"
        family_denominator[family] += 1
        source_denominator[source] += 1
        family_tier_denominator[family_tier] += 1
        if unit["unit_ordinal"] in eligible_units:
            family_eligible[family] += 1
            source_eligible[source] += 1
            family_tier_eligible[family_tier] += 1
    family_rates = {
        key: family_eligible[key] / value
        for key, value in sorted(family_denominator.items())
    }
    source_rates = {
        key: source_eligible[key] / value
        for key, value in sorted(source_denominator.items())
    }
    family_tier_rates = {
        key: family_tier_eligible[key] / value
        for key, value in sorted(family_tier_denominator.items())
    }
    coverage_gate = bool(
        pair_rate >= 0.95
        and all(value > 0.90 for value in family_rates.values())
        and all(value > 0.90 for value in source_rates.values())
        and all(value > 0.80 for value in family_tier_rates.values())
        and all(value > 0.0 for value in family_tier_rates.values())
    )
    complete_count = sum(row["status"] == "complete" for row in normalized)
    failure_count = ARM_RUN_COUNT - complete_count
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "status": (
            "passed_paired_calibration_corpus"
            if coverage_gate
            else "paired_calibration_corpus_scientifically_ineligible"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "map_count": plan["map_count"],
        "intersection_count": plan["intersection_count"],
        "corridor_count": plan["corridor_count"],
        "route_count": plan["route_count"],
        "pair_count": PAIR_COUNT,
        "planned_arm_run_count": ARM_RUN_COUNT,
        "terminal_arm_run_count": len(normalized),
        "complete_arm_run_count": complete_count,
        "retained_fixed_dp_capability_failure_count": failure_count,
        "complete_count_by_arm": dict(sorted(complete_by_arm.items())),
        "failure_count_by_arm": dict(sorted(failure_by_arm.items())),
        "paired_eligible_pair_count": len(eligible_units),
        "paired_eligible_rate": pair_rate,
        "minimum_overall_paired_eligible_rate": 0.95,
        "minimum_family_and_source_rate_exclusive": 0.90,
        "minimum_family_tier_rate_exclusive": 0.80,
        "family_paired_eligible_rates": family_rates,
        "source_paired_eligible_rates": source_rates,
        "family_tier_paired_eligible_rates": family_tier_rates,
        "coverage_gate_passed": coverage_gate,
        "all_failures_retained_in_denominator": True,
        "complete_case_filtering": False,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modified": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "arm_results": normalized,
    }


def _complete_result(
    *,
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    native: Mapping[str, Any],
    plan_arm: str,
    arm_order_index: int,
    run_ordinal: int,
    expected_route_sha256: str,
) -> dict[str, Any]:
    native_arm = "dp" if plan_arm == "candidate0_operational_default" else "camp"
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_native_arm_receipt,
    )

    validate_native_arm_receipt(
        native,
        native_arm,
        expected_ticks=TICKS_PER_ARM_RUN,
        expected_selection_policy=("v22_source_valid" if native_arm == "camp" else None),
        expected_safety_schema="safety_cost_native_v22",
        expected_candidate0_pool_diagnostics=(
            plan_arm == "candidate0_operational_default"
        ),
    )
    if (
        native.get("fixed_dp_head") != FIXED_DP_HEAD
        or native.get("route_name") != identity["route_identity_sha256"]
        or native.get("route_sha256") != expected_route_sha256
        or native.get("scenario_seed") != unit["seed"]
        or native.get("claim_authorized") is not False
    ):
        raise ValueError("paired calibration native authority drifted")
    ticks = native["ticks"]
    if plan_arm == "candidate0_operational_default":
        if any(tick.get("selected_index") != 0 for tick in ticks):
            raise ValueError("paired calibration candidate0 selection drifted")
    elif plan_arm == "camp_static14d":
        if any(tick.get("v25_scene_selector") is not None for tick in ticks):
            raise ValueError("paired calibration Static14D consumed Scene weights")
    else:
        if any(type(tick.get("v25_scene_selector")) is not dict for tick in ticks):
            raise ValueError("paired calibration Scene14D receipt is missing")
        if any(
            type(tick.get("v25_context")) is not dict
            or type(tick["v25_context"].get("source_receipt")) is not dict
            or tick["v25_context"]["source_receipt"].get(
                "phase_remaining_available"
            )
            is not False
            for tick in ticks
        ):
            raise ValueError("paired calibration Scene14D no-V2I contract drifted")
    return {
        "schema_version": RUN_RESULT_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "unit_ordinal": unit["unit_ordinal"],
        "unit_sha256": unit["unit_sha256"],
        "arm_order_index": arm_order_index,
        "plan_arm": plan_arm,
        "scenario_identity_sha256": unit["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "map_sha256": identity["map_sha256"],
        "intersection_sha256": identity["intersection_sha256"],
        "corridor_sha256": identity["corridor_sha256"],
        "route_family_sha256": identity["route_family_sha256"],
        "scenario_family": identity["scenario_family"],
        "risk_tier": identity["risk_tier"],
        "benchmark_stratum": identity["benchmark_stratum"],
        "signal_source_class": identity["signal_source_class"],
        "phase_authority_mode": identity["phase_authority_mode"],
        "semantic_parameter_block_sha256": identity[
            "semantic_parameter_block_sha256"
        ],
        "seed": unit["seed"],
        "status": "complete",
        "native_receipt": dict(native),
        "failure_receipt": None,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _failure_result(
    *,
    output: Path,
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    plan_arm: str,
    arm_order_index: int,
    run_ordinal: int,
    failure: FixedDpCandidateGenerationCapabilityFailure,
) -> dict[str, Any]:
    metadata = failure.canonical_metadata()
    tensor = failure.candidate_tensor_copy()
    raw = np.ascontiguousarray(tensor).tobytes(order="C")
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != metadata["raw_k8_sha256"]:
        raise ValueError("paired calibration failure raw K8 SHA drifted")
    failure_dir = output / "fixed_dp_capability_failures"
    failure_dir.mkdir(exist_ok=True)
    raw_path = failure_dir / f"{raw_sha}.bin"
    if raw_path.exists() and raw_path.read_bytes() != raw:
        raise ValueError("paired calibration failure content collision")
    raw_path.write_bytes(raw)
    detail = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "unit_ordinal": unit["unit_ordinal"],
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "map_sha256": identity["map_sha256"],
        "intersection_sha256": identity["intersection_sha256"],
        "corridor_sha256": identity["corridor_sha256"],
        "route_family_sha256": identity["route_family_sha256"],
        "plan_arm": plan_arm,
        "seed": unit["seed"],
        "fixed_dp_head": FIXED_DP_HEAD,
        **metadata,
        "raw_preimage": {
            "relative_path": raw_path.relative_to(output).as_posix(),
            "file_sha256": raw_sha,
            "shape": [8, 80, 4],
            "dtype": "float32",
        },
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    detail_path = failure_dir / f"{run_ordinal:04d}_{raw_sha}.json"
    _write_json(detail_path, detail)
    summary = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "failure_class": metadata["failure_class"],
        "reason": metadata["reason"],
        "raw_failure_receipt_sha256": _sha256(detail_path),
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    return {
        "schema_version": RUN_RESULT_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "unit_ordinal": unit["unit_ordinal"],
        "unit_sha256": unit["unit_sha256"],
        "arm_order_index": arm_order_index,
        "plan_arm": plan_arm,
        "scenario_identity_sha256": unit["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "scenario_family": identity["scenario_family"],
        "risk_tier": identity["risk_tier"],
        "benchmark_stratum": identity["benchmark_stratum"],
        "signal_source_class": identity["signal_source_class"],
        "phase_authority_mode": identity["phase_authority_mode"],
        "semantic_parameter_block_sha256": identity[
            "semantic_parameter_block_sha256"
        ],
        "seed": unit["seed"],
        "status": "retained_fixed_dp_capability_failure",
        "native_receipt": None,
        "failure_receipt": summary,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
