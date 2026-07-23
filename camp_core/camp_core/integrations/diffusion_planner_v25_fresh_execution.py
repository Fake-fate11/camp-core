from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
)
from .diffusion_planner_v25_controlled_scenarios import (
    RetainedScenarioCapabilityFailure,
    ScenarioCapabilityReason,
)
from .diffusion_planner_v25_fresh_b2 import validate_fresh_b2_manifest_row
from .diffusion_planner_v25_fresh_opening import (
    validate_fresh_b2_opening_consumption,
    validate_fresh_b2_opening_release,
)
from .diffusion_planner_v25_fresh_receipt import (
    build_candidate0_pool_evidence,
    build_fresh_b2_complete_row,
    build_fresh_b2_failure_row,
)
from .diffusion_planner_v25_signal_complete_execution import (
    FRESH_PLAN_ARMS,
    build_fresh_b2_arm_config,
)
from .diffusion_planner_v25_holdout_contract import (
    freeze_unit_terminal,
    validate_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_holdout_execution import build_holdout_arm_config
from .diffusion_planner_v25_holdout_opening import (
    validate_holdout_opening_consumption,
    validate_holdout_opening_release,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_three_arm_execution_v1"
RUN_SCHEMA_VERSION = "camp_dp_v25_fresh_b2_arm_terminal_v1"
HOLDOUT_SCHEMA_VERSION = "camp_dp_v25_holdout_three_arm_execution_v1"
HOLDOUT_RUN_SCHEMA_VERSION = "camp_dp_v25_holdout_arm_terminal_v1"
EVALUATION_ARMS = {
    "candidate0_operational_default": "candidate0",
    "camp_static14d": "static14d",
    "camp_scene14d_no_v2i": "scene14d",
}
RunOne = Callable[[Mapping[str, Any], Path], Mapping[str, Any]]
FailureEvidence = Callable[
    [
        Mapping[str, Any],
        Path,
        FixedDpCandidateGenerationCapabilityFailure,
    ],
    Mapping[str, Any],
]
SourceFailureEvidence = Callable[
    [
        Mapping[str, Any],
        Path,
        RetainedScenarioCapabilityFailure,
    ],
    Mapping[str, Any],
]


def materialize_fixed_dp_failure_evidence(
    config: Mapping[str, Any],
    run_dir: Path,
    failure: FixedDpCandidateGenerationCapabilityFailure,
) -> dict[str, Any]:
    """Persist the unchanged same-forward K8 and bound causal reset authority."""

    del config  # Authority is bound by the native runner before propagation.
    metadata = failure.canonical_metadata()
    authority = failure.canonical_fresh_failure_authority()
    raw = failure.candidate_tensor_copy().tobytes(order="C")
    relative = f"fixed_k8_failure_{metadata['raw_k8_sha256']}.float32.bin"
    path = Path(run_dir) / relative
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
    if _file_sha256(path) != metadata["raw_k8_sha256"]:
        raise ValueError("Fresh fixed-DP failure raw K8 write drifted")
    return {
        "schema_version": "camp_dp_v25_fresh_b2_fixed_dp_capability_failure_v1",
        "fixed_dp_failure_metadata": metadata,
        "signal_phase": authority["signal_phase"],
        "pair_authority": authority["pair_authority"],
        "raw_failure_preimage": {
            "relative_path": relative,
            "file_sha256": metadata["raw_k8_sha256"],
            "dtype": "float32",
            "shape": [8, 80, 4],
        },
        "outcome_fields_consumed": [],
        "fresh_protocol_changed": False,
    }


def materialize_source_ineligible_evidence(
    config: Mapping[str, Any],
    run_dir: Path,
    failure: RetainedScenarioCapabilityFailure,
) -> dict[str, Any]:
    """Freeze source unavailability without fabricating a model input."""

    del run_dir
    plan = config["signal_complete_plan_authority"]
    route = config["routes"][0]
    map_asset = config["map"]
    seed = config["seeds"]["scenario"]
    case = config["signal_complete_runtime"]["case"]
    if (
        failure.reason
        is not ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE
        or failure.scenario_id != case["scenario_id"]
        or failure.family != case["family"]
        or failure.source_class != case["signal_source_class"]
        or failure.phase_authority_mode != case["phase_authority_mode"]
    ):
        raise ValueError("holdout source-ineligible exception authority drifted")
    return {
        "schema_version": "camp_dp_v25_holdout_source_ineligible_failure_v1",
        "status": "source_ineligible",
        "failure_class": "preregistered_source_ineligible",
        "typed_failure": failure.as_receipt(),
        "pair_authority": {
            "route_identity_sha256": plan["route_identity_sha256"],
            "semantic_parameter_block_sha256": plan[
                "semantic_parameter_block_sha256"
            ],
            "native_route_sha256": route["sha256"],
            "logical_map_sha256": map_asset["sha256"],
            "scenario_seed": seed,
            "spawn_config_sha256": _canonical_sha(config["spawn_config"]),
            "initial_state_sha256": _canonical_sha(
                {
                    "route_identity_sha256": plan["route_identity_sha256"],
                    "scenario_seed": seed,
                    "reset_contract": (
                        "same_route_scenario_semantic_seed_initial_state_schedule"
                    ),
                }
            ),
            "initial_input_sha256": _canonical_sha(
                {
                    "status": (
                        "not_materialized_preregistered_source_ineligible"
                    ),
                    "scenario_identity_sha256": plan[
                        "scenario_identity_sha256"
                    ],
                    "scenario_seed": seed,
                }
            ),
        },
        "signal_phase": "unavailable",
        "source_evidence_materialized_before_model_input": True,
        "outcome_fields_consumed": [],
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
    }


def execute_fresh_b2_three_arm_units(
    *,
    plan: Mapping[str, Any],
    qualification_rows: Sequence[Mapping[str, Any]],
    probe_template: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    route_asset_by_identity: Mapping[str, Mapping[str, Any]],
    dp_repo: Path,
    runtime_selector_authority: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    opening_consumption: Mapping[str, Any],
    authorized_output_dir: str,
    output_dir: Path,
    run_one: RunOne,
    failure_evidence: FailureEvidence,
) -> dict[str, Any]:
    """Execute the frozen 500-pair denominator after one-time opening.

    This core never creates or consumes the opening nonce.  Its caller must do
    that atomically before invoking this function; the validated consumption
    receipt is required here so no outcome-capable callback can be reached
    without the already-consumed authority.
    """

    validated = validate_signal_complete_execution_plan(plan)
    if (
        validated.get("split") != "fresh_b2"
        or validated.get("identity_count") != 100
        or validated.get("execution_unit_count") != 500
        or validated.get("planned_arm_run_count") != 1500
        or validated.get("ticks_per_arm_run") != 64
    ):
        raise ValueError("Fresh B2 three-arm execution denominator drifted")
    return _execute_validated_fresh_units(
        plan=validated,
        qualification_rows=qualification_rows,
        probe_template=probe_template,
        prepared_runtime_by_scenario=prepared_runtime_by_scenario,
        route_asset_by_identity=route_asset_by_identity,
        dp_repo=dp_repo,
        runtime_selector_authority=runtime_selector_authority,
        opening_release=opening_release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption=opening_consumption,
        authorized_output_dir=authorized_output_dir,
        output_dir=output_dir,
        run_one=run_one,
        failure_evidence=failure_evidence,
        source_failure_evidence=None,
        holdout_mode=False,
    )


def execute_holdout_three_arm_units(
    *,
    plan: Mapping[str, Any],
    qualification_rows: Sequence[Mapping[str, Any]],
    probe_template: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    route_asset_by_identity: Mapping[str, Mapping[str, Any]],
    dp_repo: Path,
    runtime_selector_authority: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    opening_consumption: Mapping[str, Any],
    authorized_output_dir: str,
    output_dir: Path,
    run_one: RunOne,
    failure_evidence: FailureEvidence,
    source_failure_evidence: SourceFailureEvidence = (
        materialize_source_ineligible_evidence
    ),
) -> dict[str, Any]:
    """Execute one sealed generic holdout denominator after CAS consumption."""

    validated = validate_signal_complete_execution_plan(plan)
    release = validate_holdout_opening_release(opening_release)
    identity = validate_holdout_identity(release["holdout_identity"])
    protocol = validate_experiment_protocol(release["experiment_protocol"])
    if (
        validated.get("split") != identity["split"]
        or validated.get("execution_unit_count") != identity["paired_unit_count"]
        or validated.get("planned_arm_run_count") != identity["arm_run_count"]
        or (
            validated.get("planned_arm_run_count")
            * validated.get("ticks_per_arm_run")
            != identity["tick_capacity"]
        )
        or validated.get("ticks_per_arm_run") != 64
        or protocol["experiment_protocol_sha256"]
        != release["experiment_protocol"]["experiment_protocol_sha256"]
    ):
        raise ValueError("holdout three-arm execution denominator drifted")
    return _execute_validated_fresh_units(
        plan=validated,
        qualification_rows=qualification_rows,
        probe_template=probe_template,
        prepared_runtime_by_scenario=prepared_runtime_by_scenario,
        route_asset_by_identity=route_asset_by_identity,
        dp_repo=dp_repo,
        runtime_selector_authority=runtime_selector_authority,
        opening_release=release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption=opening_consumption,
        authorized_output_dir=authorized_output_dir,
        output_dir=output_dir,
        run_one=run_one,
        failure_evidence=failure_evidence,
        source_failure_evidence=source_failure_evidence,
        holdout_mode=True,
    )


def _execute_validated_fresh_units(
    *,
    plan: Mapping[str, Any],
    qualification_rows: Sequence[Mapping[str, Any]],
    probe_template: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    route_asset_by_identity: Mapping[str, Mapping[str, Any]],
    dp_repo: Path,
    runtime_selector_authority: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    opening_consumption: Mapping[str, Any],
    authorized_output_dir: str,
    output_dir: Path,
    run_one: RunOne,
    failure_evidence: FailureEvidence,
    source_failure_evidence: SourceFailureEvidence | None = None,
    holdout_mode: bool = False,
) -> dict[str, Any]:
    if holdout_mode:
        release = validate_holdout_opening_release(opening_release)
        validate_holdout_opening_consumption(
            opening_consumption,
            opening_release=release,
            opening_release_root_sha256=opening_release_root_sha256,
        )
        identity = release["holdout_identity"]
        protocol_authority = release["experiment_protocol"]
        run_schema_version = HOLDOUT_RUN_SCHEMA_VERSION
        execution_schema_version = HOLDOUT_SCHEMA_VERSION
        split_label = identity["split"]
    else:
        release = validate_fresh_b2_opening_release(opening_release)
        validate_fresh_b2_opening_consumption(
            opening_consumption,
            opening_release=release,
            release_root_sha256=opening_release_root_sha256,
        )
        identity = None
        protocol_authority = None
        run_schema_version = RUN_SCHEMA_VERSION
        execution_schema_version = SCHEMA_VERSION
        split_label = "fresh_b2"
    if (
        type(authorized_output_dir) is not str
        or authorized_output_dir != release["authorized_output_dir"]
    ):
        raise ValueError("Fresh B2 authorized output directory drifted")
    _validate_opening_selector_roots(
        release, runtime_selector_authority, holdout_mode=holdout_mode
    )

    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    if len(identities) != len(plan["identities"]):
        raise ValueError("Fresh B2 scenario identities are duplicated")
    qualifications: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(qualification_rows):
        row = validate_fresh_b2_manifest_row(raw, index=index)
        route = row["route_identity_sha256"]
        if route in qualifications:
            raise ValueError("Fresh B2 qualification route is duplicated")
        qualifications[route] = row
    expected_routes = {
        row["route_identity_sha256"] for row in plan["identities"]
    }
    expected_scenarios = set(identities)
    if (
        set(qualifications) != expected_routes
        or set(route_asset_by_identity) != expected_routes
        or set(prepared_runtime_by_scenario) != expected_scenarios
    ):
        raise ValueError("Fresh B2 execution authority inventory drifted")

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    runs_root = output / "runs"
    runs_root.mkdir()
    rows: list[dict[str, Any]] = []
    terminal_rows: list[dict[str, Any]] = []
    for unit in plan["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        manifest = qualifications[identity["route_identity_sha256"]]
        unit_row_start = len(rows)
        unit_configs: dict[str, tuple[dict[str, Any], Path]] = {}
        retained_source_evidence: dict[str, Any] | None = None
        retained_fixed_dp_evidence: dict[str, Any] | None = None
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            if plan_arm not in FRESH_PLAN_ARMS:
                raise ValueError("Fresh B2 execution arm drifted")
            evaluation_arm = EVALUATION_ARMS[plan_arm]
            config_args = {
                "probe_template": probe_template,
                "prepared_runtime": prepared_runtime_by_scenario[
                    unit["scenario_identity_sha256"]
                ],
                "execution_unit": unit,
                "plan_arm": plan_arm,
                "route_asset": route_asset_by_identity[
                    identity["route_identity_sha256"]
                ],
                "dp_repo": dp_repo,
                "runtime_selector_authority": runtime_selector_authority,
            }
            config = (
                build_holdout_arm_config(
                    holdout_identity=release["holdout_identity"],
                    experiment_protocol=release["experiment_protocol"],
                    **config_args,
                )
                if holdout_mode
                else build_fresh_b2_arm_config(**config_args)
            )
            run_dir = runs_root / (
                f"{unit['unit_ordinal']:04d}_{arm_order_index}_"
                f"{unit['unit_sha256'][:16]}_{evaluation_arm}"
            )
            run_dir.mkdir()
            _write_json(run_dir / "run_config.json", config)
            unit_configs[plan_arm] = (config, run_dir)
            try:
                native = dict(run_one(config, run_dir))
                _write_json(run_dir / "native_receipt.json", native)
                pool = (
                    build_candidate0_pool_evidence(native)
                    if evaluation_arm == "candidate0"
                    else None
                )
                row = build_fresh_b2_complete_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    native_receipt=native,
                    candidate0_pool_evidence=pool,
                )
                terminal = {
                    "schema_version": run_schema_version,
                    "status": "complete",
                    **(
                        {
                            "scientific_terminal": freeze_unit_terminal(
                                status="complete",
                                failure_class=None,
                                all_k_bad=bool(
                                    row["all_k_high_risk_tick_count"] == 64
                                ),
                            )
                        }
                        if holdout_mode
                        else {}
                    ),
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": unit["unit_sha256"],
                    "plan_arm": plan_arm,
                    "evaluation_arm": evaluation_arm,
                    "arm_order_index": arm_order_index,
                    "native_receipt_sha256": _canonical_sha(native),
                    "candidate0_pool_evidence_sha256": (
                        _canonical_sha(pool) if pool is not None else None
                    ),
                    "fixed_dp_failure_receipt_sha256": None,
                    "evaluation_row": row,
                }
            except RetainedScenarioCapabilityFailure as failure:
                if not holdout_mode or source_failure_evidence is None:
                    raise
                retained_source_evidence = _validate_source_failure_evidence(
                    source_failure_evidence(config, run_dir, failure),
                    failure=failure,
                )
                break
            except FixedDpCandidateGenerationCapabilityFailure as failure:
                evidence = _fixed_dp_failure_evidence(
                    failure_evidence(config, run_dir, failure),
                    failure,
                    run_dir=run_dir,
                )
                _write_json(run_dir / "fixed_dp_failure_receipt.json", evidence)
                if holdout_mode:
                    retained_fixed_dp_evidence = evidence
                    break
                row = build_fresh_b2_failure_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    status="fixed_dp_candidate_generation_capability_failure",
                    failure_class=evidence["fixed_dp_failure_metadata"][
                        "reason"
                    ],
                    signal_phase=evidence["signal_phase"],
                    pair_authority=evidence["pair_authority"],
                )
                terminal = {
                    "schema_version": run_schema_version,
                    "status": "retained_fixed_dp_capability_failure",
                    **(
                        {
                            "scientific_terminal": freeze_unit_terminal(
                                status=(
                                    "fixed_dp_candidate_generation_capability_failure"
                                ),
                                failure_class=(
                                    "invalid_k8_heading_norm_envelope"
                                ),
                                all_k_bad=False,
                            )
                        }
                        if holdout_mode
                        else {}
                    ),
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": unit["unit_sha256"],
                    "plan_arm": plan_arm,
                    "evaluation_arm": evaluation_arm,
                    "arm_order_index": arm_order_index,
                    "native_receipt_sha256": None,
                    "candidate0_pool_evidence_sha256": None,
                    "fixed_dp_failure_receipt_sha256": _canonical_sha(evidence),
                    "evaluation_row": row,
                }
            _write_json(run_dir / "terminal.json", terminal)
            rows.append(row)
            terminal_rows.append(terminal)
        if retained_fixed_dp_evidence is not None:
            del rows[unit_row_start:]
            del terminal_rows[unit_row_start:]
            raw_info = retained_fixed_dp_evidence["raw_failure_preimage"]
            failure_source_dir = next(
                run_dir
                for _config, run_dir in unit_configs.values()
                if (run_dir / raw_info["relative_path"]).is_file()
            )
            raw_bytes = (
                failure_source_dir / raw_info["relative_path"]
            ).read_bytes()
            for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
                evaluation_arm = EVALUATION_ARMS[plan_arm]
                if plan_arm not in unit_configs:
                    config_args = {
                        "probe_template": probe_template,
                        "prepared_runtime": prepared_runtime_by_scenario[
                            unit["scenario_identity_sha256"]
                        ],
                        "execution_unit": unit,
                        "plan_arm": plan_arm,
                        "route_asset": route_asset_by_identity[
                            identity["route_identity_sha256"]
                        ],
                        "dp_repo": dp_repo,
                        "runtime_selector_authority": (
                            runtime_selector_authority
                        ),
                    }
                    config = build_holdout_arm_config(
                        holdout_identity=release["holdout_identity"],
                        experiment_protocol=release[
                            "experiment_protocol"
                        ],
                        **config_args,
                    )
                    run_dir = runs_root / (
                        f"{unit['unit_ordinal']:04d}_{arm_order_index}_"
                        f"{unit['unit_sha256'][:16]}_{evaluation_arm}"
                    )
                    run_dir.mkdir()
                    _write_json(run_dir / "run_config.json", config)
                    unit_configs[plan_arm] = (config, run_dir)
                _config, run_dir = unit_configs[plan_arm]
                raw_path = run_dir / raw_info["relative_path"]
                if not raw_path.exists():
                    with raw_path.open("xb") as handle:
                        handle.write(raw_bytes)
                        handle.flush()
                if _file_sha256(raw_path) != raw_info["file_sha256"]:
                    raise ValueError(
                        "holdout fixed-DP unit failure preimage drifted"
                    )
                _write_json(
                    run_dir / "fixed_dp_failure_receipt.json",
                    retained_fixed_dp_evidence,
                )
                row = build_fresh_b2_failure_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    status=(
                        "fixed_dp_candidate_generation_capability_failure"
                    ),
                    failure_class="invalid_k8_heading_norm_envelope",
                    signal_phase=retained_fixed_dp_evidence["signal_phase"],
                    pair_authority=retained_fixed_dp_evidence[
                        "pair_authority"
                    ],
                )
                terminal = {
                    "schema_version": run_schema_version,
                    "status": "retained_fixed_dp_capability_failure",
                    "scientific_terminal": freeze_unit_terminal(
                        status=(
                            "fixed_dp_candidate_generation_capability_failure"
                        ),
                        failure_class="invalid_k8_heading_norm_envelope",
                        all_k_bad=False,
                    ),
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": unit["unit_sha256"],
                    "plan_arm": plan_arm,
                    "evaluation_arm": evaluation_arm,
                    "arm_order_index": arm_order_index,
                    "native_receipt_sha256": None,
                    "candidate0_pool_evidence_sha256": None,
                    "fixed_dp_failure_receipt_sha256": _canonical_sha(
                        retained_fixed_dp_evidence
                    ),
                    "evaluation_row": row,
                }
                _write_json(run_dir / "terminal.json", terminal)
                rows.append(row)
                terminal_rows.append(terminal)
        if retained_source_evidence is not None:
            del rows[unit_row_start:]
            del terminal_rows[unit_row_start:]
            for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
                evaluation_arm = EVALUATION_ARMS[plan_arm]
                if plan_arm not in unit_configs:
                    config_args = {
                        "probe_template": probe_template,
                        "prepared_runtime": prepared_runtime_by_scenario[
                            unit["scenario_identity_sha256"]
                        ],
                        "execution_unit": unit,
                        "plan_arm": plan_arm,
                        "route_asset": route_asset_by_identity[
                            identity["route_identity_sha256"]
                        ],
                        "dp_repo": dp_repo,
                        "runtime_selector_authority": (
                            runtime_selector_authority
                        ),
                    }
                    config = build_holdout_arm_config(
                        holdout_identity=release["holdout_identity"],
                        experiment_protocol=release[
                            "experiment_protocol"
                        ],
                        **config_args,
                    )
                    run_dir = runs_root / (
                        f"{unit['unit_ordinal']:04d}_{arm_order_index}_"
                        f"{unit['unit_sha256'][:16]}_{evaluation_arm}"
                    )
                    run_dir.mkdir()
                    _write_json(run_dir / "run_config.json", config)
                    unit_configs[plan_arm] = (config, run_dir)
                _config, run_dir = unit_configs[plan_arm]
                _write_json(
                    run_dir / "source_ineligible_receipt.json",
                    retained_source_evidence,
                )
                row = build_fresh_b2_failure_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    status="source_ineligible",
                    failure_class="preregistered_source_ineligible",
                    signal_phase="unavailable",
                    pair_authority=retained_source_evidence[
                        "pair_authority"
                    ],
                )
                terminal = {
                    "schema_version": run_schema_version,
                    "status": "retained_source_ineligible",
                    "scientific_terminal": freeze_unit_terminal(
                        status="source_ineligible",
                        failure_class="preregistered_source_ineligible",
                        all_k_bad=False,
                    ),
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": unit["unit_sha256"],
                    "plan_arm": plan_arm,
                    "evaluation_arm": evaluation_arm,
                    "arm_order_index": arm_order_index,
                    "native_receipt_sha256": None,
                    "candidate0_pool_evidence_sha256": None,
                    "fixed_dp_failure_receipt_sha256": None,
                    "source_ineligible_receipt_sha256": _canonical_sha(
                        retained_source_evidence
                    ),
                    "evaluation_row": row,
                }
                _write_json(run_dir / "terminal.json", terminal)
                rows.append(row)
                terminal_rows.append(terminal)

    expected_runs = len(plan["execution_units"]) * 3
    if len(rows) != expected_runs or len(terminal_rows) != expected_runs:
        raise ValueError("Fresh B2 terminal denominator drifted")
    coverage = _paired_coverage(plan, rows)
    _write_json(output / "evaluation_rows.json", rows)
    _write_json(output / "run_terminals.json", terminal_rows)
    report = {
        "schema_version": execution_schema_version,
        "status": (
            (
                "passed_holdout_three_arm_execution"
                if holdout_mode
                else "passed_fresh_b2_three_arm_execution"
            )
            if coverage["coverage_gate_passed"]
            else (
                "holdout_three_arm_execution_scientifically_ineligible"
                if holdout_mode
                else "fresh_b2_three_arm_execution_scientifically_ineligible"
            )
        ),
        **(
            {
                "holdout_identity_sha256": release["holdout_identity"][
                    "holdout_identity_sha256"
                ],
                "experiment_protocol_sha256": release[
                    "experiment_protocol"
                ]["experiment_protocol_sha256"],
                "holdout_split": split_label,
                "holdout_opened_once": True,
            }
            if holdout_mode
            else {}
        ),
        "planned_pair_count": len(plan["execution_units"]),
        "planned_arm_run_count": expected_runs,
        "terminal_arm_run_count": len(rows),
        "complete_arm_run_count": sum(row["status"] == "complete" for row in rows),
        "retained_fixed_dp_capability_failure_count": sum(
            row["status"] == "fixed_dp_candidate_generation_capability_failure"
            for row in rows
        ),
        **(
            {
                "retained_source_ineligible_count": sum(
                    row["status"] == "source_ineligible" for row in rows
                )
            }
            if holdout_mode
            else {}
        ),
        "paired_coverage": coverage,
        "evaluation_rows_sha256": _canonical_sha(rows),
        "run_terminals_sha256": _canonical_sha(terminal_rows),
        "candidate_tensor_modified": False,
        "fixed_dp_head": release["fixed_dp_head"],
        "opening_release_root_sha256": opening_release_root_sha256,
        "opening_run_nonce": release["run_nonce"],
        **({"fresh_b2_opened_once": True} if not holdout_mode else {}),
        "fresh_outcome_used_to_change_protocol": False,
        "training_executed": False,
        "calibration_executed": False,
        "claim_authorized_by_execution": False,
    }
    _write_json(output / "report.json", report)
    return report


def _fixed_dp_failure_evidence(
    value: Mapping[str, Any],
    failure: FixedDpCandidateGenerationCapabilityFailure,
    *,
    run_dir: Path,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "fixed_dp_failure_metadata",
        "signal_phase",
        "pair_authority",
        "raw_failure_preimage",
        "outcome_fields_consumed",
        "fresh_protocol_changed",
    }:
        raise ValueError("Fresh B2 fixed-DP failure evidence schema drifted")
    metadata = failure.canonical_metadata()
    authority = failure.canonical_fresh_failure_authority()
    raw_info = value.get("raw_failure_preimage")
    if type(raw_info) is not dict or set(raw_info) != {
        "relative_path",
        "file_sha256",
        "dtype",
        "shape",
    }:
        raise ValueError("Fresh B2 fixed-DP raw preimage schema drifted")
    relative = raw_info.get("relative_path")
    if type(relative) is not str or not relative or Path(relative).is_absolute():
        raise ValueError("Fresh B2 fixed-DP raw preimage path is invalid")
    root = run_dir.resolve()
    raw_path = (root / relative).resolve()
    if root not in raw_path.parents or not raw_path.is_file():
        raise ValueError("Fresh B2 fixed-DP raw preimage escaped or is missing")
    if (
        value["schema_version"]
        != "camp_dp_v25_fresh_b2_fixed_dp_capability_failure_v1"
        or not _strict_equal(value["fixed_dp_failure_metadata"], metadata)
        or metadata["failure_class"]
        != "fixed_dp_candidate_generation_capability_failure"
        or metadata["reason"] != "invalid_k8_heading_norm_envelope"
        or value["outcome_fields_consumed"] != []
        or value["fresh_protocol_changed"] is not False
        or not _strict_equal(value["pair_authority"], authority["pair_authority"])
        or value["signal_phase"] != authority["signal_phase"]
        or raw_info["dtype"] != "float32"
        or raw_info["shape"] != [8, 80, 4]
        or raw_info["file_sha256"] != metadata["raw_k8_sha256"]
        or _file_sha256(raw_path) != raw_info["file_sha256"]
    ):
        raise ValueError("Fresh B2 fixed-DP failure evidence drifted")
    return dict(value)


def _validate_source_failure_evidence(
    value: Mapping[str, Any],
    *,
    failure: RetainedScenarioCapabilityFailure,
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "failure_class",
        "typed_failure",
        "pair_authority",
        "signal_phase",
        "source_evidence_materialized_before_model_input",
        "outcome_fields_consumed",
        "training_eligible",
        "calibration_eligible",
        "evaluation_eligible",
    }
    pair_fields = {
        "route_identity_sha256",
        "semantic_parameter_block_sha256",
        "native_route_sha256",
        "logical_map_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["schema_version"]
        != "camp_dp_v25_holdout_source_ineligible_failure_v1"
        or value["status"] != "source_ineligible"
        or value["failure_class"] != "preregistered_source_ineligible"
        or not _strict_equal(value["typed_failure"], failure.as_receipt())
        or type(value["pair_authority"]) is not dict
        or set(value["pair_authority"]) != pair_fields
        or value["signal_phase"] != "unavailable"
        or value["source_evidence_materialized_before_model_input"] is not True
        or value["outcome_fields_consumed"] != []
        or value["training_eligible"] is not False
        or value["calibration_eligible"] is not False
        or value["evaluation_eligible"] is not False
    ):
        raise ValueError("holdout source-ineligible evidence drifted")
    for name, item in value["pair_authority"].items():
        if name == "scenario_seed":
            if type(item) is not int:
                raise ValueError("holdout source-ineligible seed drifted")
        elif not _sha256(item):
            raise ValueError(f"holdout source-ineligible {name} drifted")
    return dict(value)


def _validate_opening_selector_roots(
    release: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    holdout_mode: bool = False,
) -> None:
    if type(authority) is not dict:
        raise ValueError("Fresh B2 runtime selector authority is malformed")
    if holdout_mode:
        protocol = release["experiment_protocol"]
        expected = {
            "preopen_qualification_root_sha256": release[
                "preopen_authority"
            ]["root_sha256"],
            "model_registry_sha256": protocol["model_registry_sha256"],
            "training_scale_sha256": protocol["training_scale_sha256"],
            "context_scaler_sha256": protocol["context_scaler_sha256"],
        }
    else:
        expected = {
            "calibration_contract_root_sha256": release[
                "calibration_contract_root_sha256"
            ],
            "preopen_qualification_root_sha256": release[
                "preopen_qualification_root_sha256"
            ],
            "scenario_manifest_root_sha256": release[
                "scenario_manifest_root_sha256"
            ],
            "model_registry_sha256": release["model_registry_sha256"],
            "training_scale_sha256": release["training_scale_sha256"],
            "context_scaler_sha256": release["context_scaler_sha256"],
        }
    if any(authority.get(name) != value for name, value in expected.items()):
        raise ValueError("Fresh B2 opening/runtime selector roots drifted")


def _paired_coverage(
    plan: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    by_pair: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(str(row["pair_key"]), []).append(row)
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    units = {row["unit_sha256"]: row for row in plan["execution_units"]}
    if set(by_pair) != set(units) or any(len(group) != 3 for group in by_pair.values()):
        raise ValueError("Fresh B2 paired row denominator drifted")
    entries = []
    for key, unit in units.items():
        identity = identities[unit["scenario_identity_sha256"]]
        group = by_pair[key]
        entries.append(
            {
                "eligible": all(row["status"] == "complete" for row in group),
                "scenario_family": identity["scenario_family"],
                "tier": identity["risk_tier"],
                "source_mode": identity["phase_authority_mode"],
            }
        )
    overall = _rate(entries)
    by_family = _rates(entries, ("scenario_family",))
    by_source_mode = _rates(entries, ("source_mode",))
    by_family_tier = _rates(entries, ("scenario_family", "tier"))
    gate = bool(
        overall >= 0.95
        and all(value > 0.90 for value in by_family.values())
        and all(value > 0.90 for value in by_source_mode.values())
        and all(value > 0.80 for value in by_family_tier.values())
        and all(value > 0.0 for value in by_family_tier.values())
    )
    return {
        "planned_pair_count": len(entries),
        "paired_eligible_count": sum(row["eligible"] for row in entries),
        "overall_paired_eligible_rate": overall,
        "by_family": by_family,
        "by_source_mode": by_source_mode,
        "by_family_tier": by_family_tier,
        "overall_minimum": 0.95,
        "family_and_source_strict_minimum": 0.90,
        "family_tier_strict_minimum": 0.80,
        "zero_complete_strata_forbidden": True,
        "coverage_gate_passed": gate,
    }


def _rates(
    rows: Sequence[Mapping[str, Any]], fields: tuple[str, ...]
) -> dict[str, float]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        label = "|".join(str(row[field]) for field in fields)
        groups.setdefault(label, []).append(row)
    return {label: _rate(group) for label, group in sorted(groups.items())}


def _rate(rows: Sequence[Mapping[str, Any]]) -> float:
    if not rows:
        raise ValueError("Fresh B2 coverage group is empty")
    return float(sum(bool(row["eligible"]) for row in rows) / len(rows))


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


def _sha256(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
