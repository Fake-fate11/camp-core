from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from .diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
)
from .diffusion_planner_v25_calibration_corpus import (
    FAILURE_SCHEMA_VERSION,
    RUN_RESULT_SCHEMA_VERSION,
    project_candidate0_calibration_corpus,
    validate_candidate0_calibration_corpus,
)
from .diffusion_planner_v25_signal_complete_execution import (
    build_candidate0_calibration_config,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_execution_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RunOne = Callable[[Mapping[str, Any], Path], Mapping[str, Any]]


def execute_candidate0_calibration_units(
    *,
    plan: Mapping[str, Any],
    probe_template: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    route_asset_by_identity: Mapping[str, Mapping[str, Any]],
    dp_repo: Path,
    output_dir: Path,
    run_one: RunOne,
) -> dict[str, Any]:
    """Execute the frozen 100-run candidate0 calibration denominator."""

    validated = validate_signal_complete_execution_plan(plan)
    if (
        validated["split"] != "calibration"
        or validated["execution_unit_count"] != 100
        or validated["planned_arm_run_count"] != 100
        or validated["ticks_per_arm_run"] != 64
    ):
        raise ValueError("candidate0 calibration execution plan drifted")
    if type(prepared_runtime_by_scenario) is not dict:
        raise ValueError("candidate0 calibration runtime inventory is malformed")
    if type(route_asset_by_identity) is not dict:
        raise ValueError("candidate0 calibration route inventory is malformed")
    expected_scenarios = {
        row["scenario_identity_sha256"] for row in validated["identities"]
    }
    expected_routes = {
        row["route_identity_sha256"] for row in validated["identities"]
    }
    if set(prepared_runtime_by_scenario) != expected_scenarios:
        raise ValueError("candidate0 calibration runtime inventory drifted")
    if set(route_asset_by_identity) != expected_routes:
        raise ValueError("candidate0 calibration route inventory drifted")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    runs_root = output / "runs"
    runs_root.mkdir()
    identities = {
        row["scenario_identity_sha256"]: row for row in validated["identities"]
    }
    results: list[dict[str, Any]] = []
    for unit in validated["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        route_asset = route_asset_by_identity[identity["route_identity_sha256"]]
        config = build_candidate0_calibration_config(
            probe_template=probe_template,
            prepared_runtime=prepared_runtime_by_scenario[
                unit["scenario_identity_sha256"]
            ],
            execution_unit=unit,
            route_asset=route_asset,
            dp_repo=dp_repo,
        )
        run_dir = runs_root / f"{unit['unit_ordinal']:04d}_{unit['unit_sha256'][:16]}"
        run_dir.mkdir()
        _write_json(run_dir / "run_config.json", config)
        try:
            native = dict(run_one(config, run_dir))
            result = _complete_result(
                unit,
                identity,
                native,
                expected_route_sha256=route_asset["sha256"],
            )
        except FixedDpCandidateGenerationCapabilityFailure as failure:
            result = _failure_result(
                output=output,
                unit=unit,
                identity=identity,
                failure=failure,
            )
        _write_json(run_dir / "terminal.json", result)
        results.append(result)
    projection = validate_candidate0_calibration_corpus(
        project_candidate0_calibration_corpus(validated, results)
    )
    _write_json(output / "run_results.json", results)
    _write_json(output / "calibration_corpus.json", projection)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "passed_candidate0_calibration_execution"
            if projection["status"]
            == "passed_candidate0_calibration_corpus_projection"
            else "candidate0_calibration_execution_scientifically_ineligible"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "planned_run_count": 100,
        "terminal_run_count": len(results),
        "complete_run_count": projection["complete_run_count"],
        "retained_fixed_dp_capability_failure_count": projection[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_rate": projection["paired_eligible_rate"],
        "run_results_sha256": _canonical_sha(results),
        "calibration_corpus_sha256": _canonical_sha(projection),
        "independent_reset_per_run": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _complete_result(
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    native: Mapping[str, Any],
    *,
    expected_route_sha256: str,
) -> dict[str, Any]:
    if (
        native.get("schema_version") != "v21_native_arm_receipt_v1"
        or native.get("status") != "ok"
        or native.get("arm") != "dp"
        or native.get("fixed_dp_head") != FIXED_DP_HEAD
        or native.get("route_name") != identity["route_identity_sha256"]
        or native.get("route_sha256") != expected_route_sha256
        or native.get("scenario_seed") != unit["seed"]
        or native.get("claim_authorized") is not False
        or type(native.get("ticks")) is not list
        or len(native["ticks"]) != 64
        or [tick.get("tick_index") for tick in native["ticks"]] != list(range(64))
        or any(tick.get("selected_index") != 0 for tick in native["ticks"])
    ):
        raise ValueError("candidate0 calibration native receipt drifted")
    return {
        "schema_version": RUN_RESULT_SCHEMA_VERSION,
        "unit_ordinal": unit["unit_ordinal"],
        "unit_sha256": unit["unit_sha256"],
        "scenario_identity_sha256": unit["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
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
    failure: FixedDpCandidateGenerationCapabilityFailure,
) -> dict[str, Any]:
    metadata = failure.canonical_metadata()
    tensor = failure.candidate_tensor_copy()
    raw = np.ascontiguousarray(tensor).tobytes(order="C")
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != metadata["raw_k8_sha256"]:
        raise ValueError("candidate0 calibration failure raw K8 SHA drifted")
    failure_dir = output / "fixed_dp_capability_failures"
    failure_dir.mkdir(exist_ok=True)
    raw_path = failure_dir / f"{raw_sha}.bin"
    if raw_path.exists() and raw_path.read_bytes() != raw:
        raise ValueError("candidate0 calibration failure content collision")
    raw_path.write_bytes(raw)
    detail = {
        "schema_version": "camp_dp_v25_candidate0_calibration_k8_failure_detail_v1",
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
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
    detail_path = failure_dir / f"{raw_sha}.json"
    _write_json(detail_path, detail)
    summary = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "seed": unit["seed"],
        "fixed_dp_head": FIXED_DP_HEAD,
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
        "unit_ordinal": unit["unit_ordinal"],
        "unit_sha256": unit["unit_sha256"],
        "scenario_identity_sha256": unit["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
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
