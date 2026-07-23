from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from .diffusion_planner_v25_controlled_scenarios import (
    ScenarioCapabilityReason,
)
from .diffusion_planner_v25_fresh_b2 import validate_fresh_b2_manifest_row
from .diffusion_planner_v25_fresh_execution import (
    EVALUATION_ARMS,
    HOLDOUT_RUN_SCHEMA_VERSION,
    HOLDOUT_SCHEMA_VERSION as HOLDOUT_EXECUTION_SCHEMA_VERSION,
    RUN_SCHEMA_VERSION,
    SCHEMA_VERSION as EXECUTION_SCHEMA_VERSION,
    _paired_coverage,
)
from .diffusion_planner_v25_fresh_opening import (
    validate_fresh_b2_opening_consumption,
    validate_fresh_b2_opening_release,
)
from .diffusion_planner_v25_actual_native_receipt_review import (
    independent_candidate0_pool_evidence,
    independent_historical_candidate0_pool_evidence,
    independent_project_candidate0_supplementary,
    independent_validate_actual_native_receipt,
)
from .diffusion_planner_v25_fresh_receipt import (
    build_fresh_b2_complete_row,
    build_fresh_b2_failure_row,
)
from .diffusion_planner_v25_evaluation import PAIR_AUTHORITY_FIELDS
from .diffusion_planner_v25_signal_complete_execution import (
    FRESH_PLAN_ARMS,
    build_fresh_b2_arm_config,
)
from .diffusion_planner_v25_holdout_contract import (
    freeze_unit_terminal,
    validate_holdout_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_holdout_plan_dispatch import (
    validate_holdout_execution_plan,
)
from .diffusion_planner_v25_holdout_execution import build_holdout_arm_config
from .diffusion_planner_v25_holdout_opening import (
    validate_holdout_opening_consumption,
    validate_holdout_opening_release,
)
from .diffusion_planner_v25_holdout_opening_rc import (
    RELEASE_SCHEMA_VERSION as PRODUCTION_RC_RELEASE_SCHEMA_VERSION,
    validate_production_rc_opening_release,
    validate_scientific_exposure_receipt,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_three_arm_execution_review_v1"
HOLDOUT_SCHEMA_VERSION = "camp_dp_v25_holdout_three_arm_execution_review_v2"


def review_fresh_b2_three_arm_execution(
    *,
    artifact: Path,
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
) -> dict[str, Any]:
    return _review_three_arm_execution(
        artifact=artifact,
        plan=plan,
        qualification_rows=qualification_rows,
        probe_template=probe_template,
        prepared_runtime_by_scenario=prepared_runtime_by_scenario,
        route_asset_by_identity=route_asset_by_identity,
        dp_repo=dp_repo,
        runtime_selector_authority=runtime_selector_authority,
        opening_release=opening_release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption=opening_consumption,
        holdout_mode=False,
    )


def review_holdout_three_arm_execution(
    *,
    artifact: Path,
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
) -> dict[str, Any]:
    return _review_three_arm_execution(
        artifact=artifact,
        plan=plan,
        qualification_rows=qualification_rows,
        probe_template=probe_template,
        prepared_runtime_by_scenario=prepared_runtime_by_scenario,
        route_asset_by_identity=route_asset_by_identity,
        dp_repo=dp_repo,
        runtime_selector_authority=runtime_selector_authority,
        opening_release=opening_release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption=opening_consumption,
        holdout_mode=True,
    )


def _review_three_arm_execution(
    *,
    artifact: Path,
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
    holdout_mode: bool,
) -> dict[str, Any]:
    execution = Path(artifact).resolve()
    validated = (
        validate_holdout_execution_plan(plan)
        if holdout_mode
        else validate_signal_complete_execution_plan(plan)
    )
    if holdout_mode:
        if (
            opening_release.get("schema_version")
            == PRODUCTION_RC_RELEASE_SCHEMA_VERSION
        ):
            release = validate_production_rc_opening_release(opening_release)
        else:
            release = validate_holdout_opening_release(opening_release)
        identity_authority = validate_holdout_identity(
            release["holdout_identity"]
        )
        validate_holdout_experiment_protocol(release["experiment_protocol"])
        if (
            validated.get("split") != identity_authority["split"]
            or validated.get("execution_unit_count")
            != identity_authority["paired_unit_count"]
            or validated.get("planned_arm_run_count")
            != identity_authority["arm_run_count"]
            or validated.get("planned_arm_run_count")
            * validated.get("ticks_per_arm_run")
            != identity_authority["tick_capacity"]
            or validated.get("ticks_per_arm_run") != 64
        ):
            raise ValueError("holdout review denominator drifted")
        if (
            release["schema_version"]
            == PRODUCTION_RC_RELEASE_SCHEMA_VERSION
        ):
            validate_scientific_exposure_receipt(
                opening_consumption,
                opening_release=release,
                opening_release_root_sha256=opening_release_root_sha256,
            )
        else:
            validate_holdout_opening_consumption(
                opening_consumption,
                opening_release=release,
                opening_release_root_sha256=opening_release_root_sha256,
            )
        run_schema_version = HOLDOUT_RUN_SCHEMA_VERSION
        execution_schema_version = HOLDOUT_EXECUTION_SCHEMA_VERSION
    else:
        if (
            validated.get("split") != "fresh_b2"
            or validated.get("identity_count") != 100
            or validated.get("execution_unit_count") != 500
            or validated.get("planned_arm_run_count") != 1500
            or validated.get("ticks_per_arm_run") != 64
        ):
            raise ValueError("Fresh B2 review denominator drifted")
        release = validate_fresh_b2_opening_release(opening_release)
        validate_fresh_b2_opening_consumption(
            opening_consumption,
            opening_release=release,
            release_root_sha256=opening_release_root_sha256,
        )
        run_schema_version = RUN_SCHEMA_VERSION
        execution_schema_version = EXECUTION_SCHEMA_VERSION
    identities = {
        row["scenario_identity_sha256"]: row for row in validated["identities"]
    }
    qualifications: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(qualification_rows):
        row = validate_fresh_b2_manifest_row(raw, index=index)
        route = row["route_identity_sha256"]
        if route in qualifications:
            raise ValueError("Fresh B2 review qualification route is duplicated")
        qualifications[route] = row
    expected_routes = {
        row["route_identity_sha256"] for row in validated["identities"]
    }
    if (
        set(qualifications) != expected_routes
        or set(route_asset_by_identity) != expected_routes
        or set(prepared_runtime_by_scenario) != set(identities)
    ):
        raise ValueError("Fresh B2 review authority inventory drifted")

    recorded_rows = _canonical_json_list(execution / "evaluation_rows.json")
    recorded_terminals = _canonical_json_list(execution / "run_terminals.json")
    report = _canonical_json(execution / "report.json")
    expected_count = len(validated["execution_units"]) * 3
    run_dirs = sorted((execution / "runs").iterdir())
    if (
        len(recorded_rows) != expected_count
        or len(recorded_terminals) != expected_count
        or len(run_dirs) != expected_count
        or any(not path.is_dir() for path in run_dirs)
    ):
        raise ValueError("Fresh B2 review run inventory drifted")

    rebuilt_rows: list[dict[str, Any]] = []
    rebuilt_terminals: list[dict[str, Any]] = []
    offset = 0
    for unit in validated["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        manifest = qualifications[identity["route_identity_sha256"]]
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            evaluation_arm = EVALUATION_ARMS[plan_arm]
            expected_name = (
                f"{unit['unit_ordinal']:04d}_{arm_order_index}_"
                f"{unit['unit_sha256'][:16]}_{evaluation_arm}"
            )
            run_dir = run_dirs[offset]
            offset += 1
            if run_dir.name != expected_name:
                raise ValueError("Fresh B2 review run order drifted")
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
            expected_config = (
                build_holdout_arm_config(
                    holdout_identity=release["holdout_identity"],
                    experiment_protocol=release["experiment_protocol"],
                    **config_args,
                )
                if holdout_mode
                else build_fresh_b2_arm_config(**config_args)
            )
            if not _strict_equal(
                _canonical_json(run_dir / "run_config.json"), expected_config
            ):
                raise ValueError("Fresh B2 review run config drifted")
            terminal = _canonical_json(run_dir / "terminal.json")
            if terminal.get("schema_version") != run_schema_version:
                raise ValueError("Fresh B2 terminal schema drifted")
            if terminal.get("status") == "complete":
                native = _canonical_json(run_dir / "native_receipt.json")
                production_rc = (
                    holdout_mode
                    and release["schema_version"]
                    == PRODUCTION_RC_RELEASE_SCHEMA_VERSION
                )
                raw_native = native
                if production_rc:
                    raw_native = _canonical_json(
                        run_dir / "actual_native_receipt_raw.json"
                    )
                    independent_validate_actual_native_receipt(
                        raw_native,
                        branch=(
                            "candidate0_primary"
                            if evaluation_arm == "candidate0"
                            else (
                                "static14d"
                                if evaluation_arm == "static14d"
                                else "scene14d"
                            )
                        ),
                    )
                    if evaluation_arm == "candidate0":
                        if (
                            run_dir / "candidate_tensor_preimages_primary"
                        ).exists():
                            raise ValueError(
                                "candidate0 primary exposed online K8 preimages"
                            )
                    else:
                        _independent_candidate_tensor_preimages(
                            run_dir / "candidate_tensor_preimages_primary",
                            raw_ticks=raw_native["ticks"],
                        )
                    enriched_native = dict(native)
                    enriched_native.pop(
                        "fresh_decision_evidence_reference", None
                    )
                    enriched_native.pop("fresh_decision_evidence_count", None)
                    if not _strict_equal(raw_native, enriched_native):
                        raise ValueError(
                            "stored native receipt differs from preprojection "
                            "raw receipt"
                        )
                _review_logical_decision_evidence(
                    run_dir, native=native, evaluation_arm=evaluation_arm
                )
                supplementary_native = None
                if holdout_mode and evaluation_arm == "candidate0":
                    supplementary_native = _canonical_json(
                        run_dir
                        / "candidate0_supplementary_native_receipt.json"
                    )
                    if production_rc:
                        raw_supplementary = _canonical_json(
                            run_dir
                            / "candidate0_supplementary_actual_native_raw.json"
                        )
                        independent_validate_actual_native_receipt(
                            raw_supplementary,
                            branch="candidate0_supplementary",
                        )
                        _independent_candidate_tensor_preimages(
                            run_dir
                            / "candidate_tensor_preimages_supplementary",
                            raw_ticks=raw_supplementary["ticks"],
                        )
                        independent_projected = (
                            independent_project_candidate0_supplementary(
                                raw_supplementary
                            )
                        )
                        if not _strict_equal(
                            supplementary_native, independent_projected
                        ):
                            raise ValueError(
                                "candidate0 supplementary projection differs "
                                "from independently rebuilt raw receipt"
                            )
                pool = (
                    (
                        independent_candidate0_pool_evidence(
                            raw_native, supplementary_native
                        )
                        if production_rc
                        else independent_historical_candidate0_pool_evidence(
                            native, supplementary_native
                        )
                    )
                    if evaluation_arm == "candidate0"
                    else None
                )
                if pool is not None and not _strict_equal(
                    _canonical_json(
                        run_dir / "candidate0_pool_evidence.json"
                    ),
                    pool,
                ):
                    raise ValueError(
                        "candidate0 stored pool evidence drifted from native "
                        "receipts"
                    )
                if evaluation_arm != "candidate0" and any(
                    (run_dir / name).exists()
                    for name in (
                        "candidate0_supplementary_native_receipt.json",
                        "candidate0_supplementary_actual_native_raw.json",
                        "candidate0_pool_evidence.json",
                    )
                ):
                    raise ValueError(
                        "method arm exposed candidate0 supplementary evidence"
                    )
                row = build_fresh_b2_complete_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    native_receipt=native,
                    candidate0_pool_evidence=pool,
                )
                expected_terminal = {
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
                    "candidate0_supplementary_native_receipt_sha256": (
                        _canonical_sha(supplementary_native)
                        if supplementary_native is not None
                        else None
                    ),
                    "fixed_dp_failure_receipt_sha256": None,
                    "evaluation_row": row,
                }
            elif terminal.get("status") == "retained_fixed_dp_capability_failure":
                evidence = _canonical_json(
                    run_dir / "fixed_dp_failure_receipt.json"
                )
                metadata = _recompute_fixed_dp_failure(run_dir, evidence)
                _review_failure_pair_authority(
                    evidence,
                    expected_config=expected_config,
                    qualification_row=manifest,
                )
                row = build_fresh_b2_failure_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    status="fixed_dp_candidate_generation_capability_failure",
                    failure_class=metadata["reason"],
                    signal_phase=evidence["signal_phase"],
                    pair_authority=evidence["pair_authority"],
                )
                expected_terminal = {
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
                    "candidate0_supplementary_native_receipt_sha256": None,
                    "fixed_dp_failure_receipt_sha256": _canonical_sha(evidence),
                    "evaluation_row": row,
                }
            elif (
                holdout_mode
                and terminal.get("status") == "retained_source_ineligible"
            ):
                evidence = _canonical_json(
                    run_dir / "source_ineligible_receipt.json"
                )
                _review_source_ineligible(
                    evidence,
                    expected_config=expected_config,
                )
                row = build_fresh_b2_failure_row(
                    qualification_row=manifest,
                    pair_key=unit["unit_sha256"],
                    arm=evaluation_arm,
                    arm_order_index=arm_order_index,
                    status="source_ineligible",
                    failure_class="preregistered_source_ineligible",
                    signal_phase="unavailable",
                    pair_authority=evidence["pair_authority"],
                )
                expected_terminal = {
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
                    "candidate0_supplementary_native_receipt_sha256": None,
                    "fixed_dp_failure_receipt_sha256": None,
                    "source_ineligible_receipt_sha256": _canonical_sha(
                        evidence
                    ),
                    "evaluation_row": row,
                }
            else:
                raise ValueError("Fresh B2 terminal status drifted")
            if not _strict_equal(terminal, expected_terminal):
                raise ValueError("Fresh B2 terminal differs from independent rebuild")
            rebuilt_rows.append(row)
            rebuilt_terminals.append(expected_terminal)

    if (
        not _strict_equal(recorded_rows, rebuilt_rows)
        or not _strict_equal(recorded_terminals, rebuilt_terminals)
    ):
        raise ValueError("Fresh B2 recorded rows differ from independent rebuild")
    if holdout_mode:
        by_pair: dict[str, list[dict[str, Any]]] = {}
        for row in rebuilt_rows:
            by_pair.setdefault(row["pair_key"], []).append(row)
        if any(
            any(row["status"] == "source_ineligible" for row in group)
            and not all(
                row["status"] == "source_ineligible" for row in group
            )
            for group in by_pair.values()
        ):
            raise ValueError(
                "holdout source-ineligible status must terminate the whole unit"
            )
        if any(
            any(
                row["status"]
                == "fixed_dp_candidate_generation_capability_failure"
                for row in group
            )
            and not all(
                row["status"]
                == "fixed_dp_candidate_generation_capability_failure"
                for row in group
            )
            for group in by_pair.values()
        ):
            raise ValueError(
                "holdout fixed-DP capability failure must terminate the whole unit"
            )
    _validate_cross_arm_pair_authority(rebuilt_rows)
    coverage = _paired_coverage(validated, rebuilt_rows)
    expected_report = {
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
                "holdout_split": release["holdout_identity"]["split"],
                "holdout_opened_once": True,
            }
            if holdout_mode
            else {}
        ),
        "planned_pair_count": len(validated["execution_units"]),
        "planned_arm_run_count": expected_count,
        "terminal_arm_run_count": expected_count,
        "complete_arm_run_count": sum(
            row["status"] == "complete" for row in rebuilt_rows
        ),
        "retained_fixed_dp_capability_failure_count": sum(
            row["status"] == "fixed_dp_candidate_generation_capability_failure"
            for row in rebuilt_rows
        ),
        **(
            {
                "retained_source_ineligible_count": sum(
                    row["status"] == "source_ineligible"
                    for row in rebuilt_rows
                )
            }
            if holdout_mode
            else {}
        ),
        "paired_coverage": coverage,
        "evaluation_rows_sha256": _canonical_sha(rebuilt_rows),
        "run_terminals_sha256": _canonical_sha(rebuilt_terminals),
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
    if not _strict_equal(report, expected_report):
        raise ValueError("Fresh B2 execution report differs from independent rebuild")
    return {
        "schema_version": (
            HOLDOUT_SCHEMA_VERSION if holdout_mode else SCHEMA_VERSION
        ),
        "status": (
            "passed_independent_holdout_three_arm_execution_review"
            if holdout_mode
            else "passed_independent_fresh_b2_three_arm_execution_review"
        ),
        **(
            {
                "holdout_identity_sha256": release["holdout_identity"][
                    "holdout_identity_sha256"
                ],
                "experiment_protocol_sha256": release[
                    "experiment_protocol"
                ]["experiment_protocol_sha256"],
                "holdout_opened_once": True,
            }
            if holdout_mode
            else {}
        ),
        "reviewed_artifact": str(execution),
        "planned_pair_count": len(validated["execution_units"]),
        "reviewed_arm_run_count": expected_count,
        "complete_arm_run_count": expected_report["complete_arm_run_count"],
        "retained_fixed_dp_capability_failure_count": expected_report[
            "retained_fixed_dp_capability_failure_count"
        ],
        **(
            {
                "retained_source_ineligible_count": expected_report[
                    "retained_source_ineligible_count"
                ]
            }
            if holdout_mode
            else {}
        ),
        "paired_coverage": coverage,
        "all_configs_independently_rebuilt": True,
        "all_complete_rows_reprojected": True,
        "all_fixed_dp_failure_preimages_recomputed": True,
        "candidate_tensor_modified": False,
        **({"fresh_b2_opened_once": True} if not holdout_mode else {}),
        "fresh_outcome_used_to_change_protocol": False,
        "training_executed": False,
        "calibration_executed": False,
        "claim_authorized_by_review": False,
    }


def _recompute_fixed_dp_failure(
    run_dir: Path, evidence: Mapping[str, Any]
) -> dict[str, Any]:
    if type(evidence) is not dict or set(evidence) != {
        "schema_version",
        "fixed_dp_failure_metadata",
        "signal_phase",
        "pair_authority",
        "raw_failure_preimage",
        "outcome_fields_consumed",
        "fresh_protocol_changed",
    }:
        raise ValueError("Fresh B2 reviewed fixed-DP failure schema drifted")
    metadata = evidence.get("fixed_dp_failure_metadata")
    raw_info = evidence.get("raw_failure_preimage")
    if type(metadata) is not dict or type(raw_info) is not dict or set(raw_info) != {
        "relative_path",
        "file_sha256",
        "dtype",
        "shape",
    }:
        raise ValueError("Fresh B2 reviewed fixed-DP failure evidence drifted")
    relative = raw_info.get("relative_path")
    root = Path(run_dir).resolve()
    if type(relative) is not str or not relative or Path(relative).is_absolute():
        raise ValueError("Fresh B2 reviewed raw K8 path is invalid")
    raw_path = (root / relative).resolve()
    if root not in raw_path.parents or not raw_path.is_file():
        raise ValueError("Fresh B2 reviewed raw K8 preimage escaped or is missing")
    raw = raw_path.read_bytes()
    if (
        raw_info.get("dtype") != "float32"
        or raw_info.get("shape") != [8, 80, 4]
        or len(raw) != 8 * 80 * 4 * 4
        or _file_sha256(raw_path) != raw_info.get("file_sha256")
    ):
        raise ValueError("Fresh B2 reviewed raw K8 preimage drifted")
    candidates = np.frombuffer(raw, dtype=np.float32).copy().reshape(8, 80, 4)
    try:
        validate_fixed_k8_candidate_tensor(
            candidates,
            tick_index=metadata["tick_index"],
            default_output_sha256=metadata["default_output_sha256"],
            default_candidate0_identity=metadata["default_candidate0_identity"],
        )
    except FixedDpCandidateGenerationCapabilityFailure as failure:
        rebuilt = failure.canonical_metadata()
    else:
        raise ValueError("Fresh B2 reviewed raw K8 no longer reproduces failure")
    if (
        not _strict_equal(rebuilt, metadata)
        or evidence.get("schema_version")
        != "camp_dp_v25_fresh_b2_fixed_dp_capability_failure_v1"
        or evidence.get("outcome_fields_consumed") != []
        or evidence.get("fresh_protocol_changed") is not False
    ):
        raise ValueError("Fresh B2 reviewed fixed-DP failure metadata drifted")
    return rebuilt


def _review_source_ineligible(
    evidence: Mapping[str, Any],
    *,
    expected_config: Mapping[str, Any],
) -> None:
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
    plan = expected_config["signal_complete_plan_authority"]
    case = expected_config["signal_complete_runtime"]["case"]
    seed = expected_config["seeds"]["scenario"]
    expected_pair = {
        "route_identity_sha256": plan["route_identity_sha256"],
        "semantic_parameter_block_sha256": plan[
            "semantic_parameter_block_sha256"
        ],
        "native_route_sha256": expected_config["routes"][0]["sha256"],
        "logical_map_sha256": expected_config["map"]["sha256"],
        "scenario_seed": seed,
        "spawn_config_sha256": _canonical_sha(
            expected_config["spawn_config"]
        ),
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
                "status": "not_materialized_preregistered_source_ineligible",
                "scenario_identity_sha256": plan[
                    "scenario_identity_sha256"
                ],
                "scenario_seed": seed,
            }
        ),
    }
    expected_typed = {
        "scenario_id": case["scenario_id"],
        "family": case["family"],
        "source_class": case["signal_source_class"],
        "phase_authority_mode": case["phase_authority_mode"],
        "reason": (
            ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value
        ),
    }
    if (
        type(evidence) is not dict
        or set(evidence) != fields
        or evidence["schema_version"]
        != "camp_dp_v25_holdout_source_ineligible_failure_v1"
        or evidence["status"] != "source_ineligible"
        or evidence["failure_class"] != "preregistered_source_ineligible"
        or not _strict_equal(evidence["typed_failure"], expected_typed)
        or not _strict_equal(evidence["pair_authority"], expected_pair)
        or evidence["signal_phase"] != "unavailable"
        or evidence["source_evidence_materialized_before_model_input"]
        is not True
        or evidence["outcome_fields_consumed"] != []
        or evidence["training_eligible"] is not False
        or evidence["calibration_eligible"] is not False
        or evidence["evaluation_eligible"] is not False
    ):
        raise ValueError("holdout source-ineligible evidence drifted")


def _review_failure_pair_authority(
    evidence: Mapping[str, Any],
    *,
    expected_config: Mapping[str, Any],
    qualification_row: Mapping[str, Any],
) -> None:
    authority = evidence.get("pair_authority")
    plan = expected_config.get("signal_complete_plan_authority")
    routes = expected_config.get("routes")
    spawn = expected_config.get("spawn_config")
    if (
        type(authority) is not dict
        or set(authority) != PAIR_AUTHORITY_FIELDS
        or type(plan) is not dict
        or type(routes) is not list
        or len(routes) != 1
        or type(routes[0]) is not dict
        or type(spawn) is not dict
    ):
        raise ValueError("Fresh B2 reviewed failure pair authority schema drifted")
    spawn_sha = hashlib.sha256(
        json.dumps(
            {**spawn, "max_steps": 64},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    initial_input = authority.get("initial_input_sha256")
    expected_state = (
        hashlib.sha256(
            ("v21_native_scene_context_v1\0" + initial_input).encode("ascii")
        ).hexdigest()
        if _sha256(initial_input)
        else None
    )
    expected = {
        "route_identity_sha256": qualification_row["route_identity_sha256"],
        "semantic_parameter_block_sha256": qualification_row[
            "semantic_parameter_block_sha256"
        ],
        "native_route_sha256": routes[0]["sha256"],
        "logical_map_sha256": expected_config["map"]["sha256"],
        "scenario_seed": expected_config["seeds"]["scenario"],
        "spawn_config_sha256": spawn_sha,
        "initial_state_sha256": expected_state,
        "initial_input_sha256": initial_input,
    }
    if not _strict_equal(authority, expected):
        raise ValueError("Fresh B2 reviewed failure pair authority drifted")


def _validate_cross_arm_pair_authority(rows: Sequence[Mapping[str, Any]]) -> None:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["pair_key"]), []).append(row)
    for group in grouped.values():
        if len(group) != 3:
            raise ValueError("Fresh B2 cross-arm pair denominator drifted")
        baseline = group[0]
        if any(
            any(row[field] != baseline[field] for field in PAIR_AUTHORITY_FIELDS)
            for row in group[1:]
        ):
            raise ValueError("Fresh B2 cross-arm pair authority drifted")


def _review_logical_decision_evidence(
    run_dir: Path, *, native: Mapping[str, Any], evaluation_arm: str
) -> None:
    reference_path = run_dir / "decision_evidence.ref.json"
    storage_path = run_dir / "decision_evidence.json.gz"
    if (run_dir / "decision_evidence.json").exists():
        raise ValueError("Fresh decision evidence was not stored as a logical shard")
    reference = _canonical_json(reference_path)
    fields = {
        "schema_version",
        "relative_path",
        "codec",
        "logical_sha256",
        "logical_nbytes",
        "storage_sha256",
        "storage_nbytes",
        "retained_regression_shard",
    }
    if (
        set(reference) != fields
        or reference.get("schema_version")
        != "camp_dp_v25_fresh_logical_file_reference_v1"
        or reference.get("relative_path") != "decision_evidence.json"
        or reference.get("codec") != "gzip_rfc1952_level6_mtime0"
        or reference.get("retained_regression_shard")
        != "decision_evidence.json.gz"
        or native.get("fresh_decision_evidence_reference") != reference
    ):
        raise ValueError("Fresh decision-evidence logical reference drifted")
    storage_raw = storage_path.read_bytes()
    logical_raw = gzip.decompress(storage_raw)
    if (
        hashlib.sha256(storage_raw).hexdigest() != reference["storage_sha256"]
        or len(storage_raw) != reference["storage_nbytes"]
        or hashlib.sha256(logical_raw).hexdigest() != reference["logical_sha256"]
        or len(logical_raw) != reference["logical_nbytes"]
    ):
        raise ValueError("Fresh decision-evidence logical bytes drifted")
    evidence = _strict_json(logical_raw)
    if logical_raw != _canonical_bytes(evidence) or type(evidence) is not list:
        raise ValueError("Fresh decision-evidence logical JSON drifted")
    expected_count = 0 if evaluation_arm == "candidate0" else 64
    if (
        native.get("fresh_decision_evidence_count") != expected_count
        or len(evidence) != expected_count
        or (
            evidence
            and [row.get("sidecar", {}).get("tick_index") for row in evidence]
            != list(range(64))
        )
    ):
        raise ValueError("Fresh decision-evidence logical denominator drifted")


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B2 authority JSON must be a mapping: {path}")
    return value


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    value = _canonical_value(path)
    if type(value) is not list or any(type(row) is not dict for row in value):
        raise ValueError(f"Fresh B2 authority JSON must be a list: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = Path(path).read_bytes()
    value = _strict_json(raw)
    if raw != _canonical_bytes(value):
        raise ValueError(f"Fresh B2 authority JSON is not canonical: {path}")
    return value


def _sha256(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _strict_json(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("Fresh B2 authority JSON contains a duplicate key")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
    )


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


def _independent_candidate_tensor_preimages(
    root: Path, *, raw_ticks: Sequence[Mapping[str, Any]]
) -> None:
    if not root.is_dir() or root.is_symlink() or len(raw_ticks) != 64:
        raise ValueError("candidate tensor preimage root drifted")
    manifest = _canonical_json(root / "manifest.json")
    if (
        set(manifest)
        != {
            "schema_version",
            "status",
            "tick_count",
            "dtype",
            "shape",
            "rows",
        }
        or manifest["schema_version"]
        != "camp_dp_v25_candidate_tensor_preimage_manifest_v1"
        or manifest["status"] != "persisted_before_projection"
        or manifest["tick_count"] != 64
        or manifest["dtype"] != "<f4"
        or manifest["shape"] != [8, 80, 4]
        or type(manifest["rows"]) is not list
        or len(manifest["rows"]) != 64
    ):
        raise ValueError("candidate tensor preimage manifest drifted")
    expected_files = {"manifest.json"}
    for tick_index, (row, raw_tick) in enumerate(
        zip(manifest["rows"], raw_ticks, strict=True)
    ):
        binary_name = f"tick_{tick_index:02d}.float32.bin"
        receipt_name = f"tick_{tick_index:02d}.json"
        expected_files.update({binary_name, receipt_name})
        if row != {
            "tick_index": tick_index,
            "candidate_tensor_sha256": raw_tick[
                "candidate_tensor_sha256_before"
            ],
            "binary_relative_path": binary_name,
            "receipt_relative_path": receipt_name,
        }:
            raise ValueError("candidate tensor preimage manifest row drifted")
        receipt = _canonical_json(root / receipt_name)
        raw = (root / binary_name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if (
            set(receipt)
            != {
                "schema_version",
                "tick_index",
                "dtype",
                "shape",
                "nbytes",
                "candidate_tensor_sha256",
                "native_metadata",
                "persisted_before_projection",
            }
            or receipt["schema_version"]
            != "camp_dp_v25_candidate_tensor_preimage_v1"
            or receipt["tick_index"] != tick_index
            or receipt["dtype"] != "<f4"
            or receipt["shape"] != [8, 80, 4]
            or receipt["nbytes"] != 8 * 80 * 4 * 4
            or receipt["candidate_tensor_sha256"] != digest
            or digest != raw_tick["candidate_tensor_sha256_before"]
            or receipt["native_metadata"].get("candidate_tensor_sha256")
            != digest
            or receipt["persisted_before_projection"] is not True
            or len(raw) != receipt["nbytes"]
        ):
            raise ValueError("candidate tensor preimage receipt drifted")
        candidates = np.frombuffer(raw, dtype="<f4").reshape(8, 80, 4)
        validate_fixed_k8_candidate_tensor(candidates)
    actual_files = {
        path.name
        for path in root.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if actual_files != expected_files:
        raise ValueError("candidate tensor preimage inventory drifted")


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
