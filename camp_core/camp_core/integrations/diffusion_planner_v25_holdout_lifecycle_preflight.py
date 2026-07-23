from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    ARMS,
    _strict_canonical_json,
    canonical_sha256,
    freeze_holdout_identity,
    reserve_holdout_identity,
    strict_equal,
    transition_holdout_identity,
    validate_experiment_protocol,
    validate_holdout_identity,
    validate_tombstone,
)
from .diffusion_planner_v25_holdout_opening import (
    consume_holdout_opening,
    freeze_holdout_controller_decision,
    freeze_holdout_opening_release,
    validate_holdout_controller_decision,
    validate_holdout_opening_consumption,
    validate_holdout_opening_release,
)
from .diffusion_planner_v25_holdout_preflight import (
    validate_production_composition_preflight,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_nonfresh_entrypoint_lifecycle_v1"
CAS_ROOT = Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "implementation_head",
        "production_preflight_payload_sha256",
        "nonfresh_holdout_identity",
        "experiment_protocol_sha256",
        "controller_decision",
        "controller_decision_payload_sha256",
        "opening_release",
        "opening_release_payload_sha256",
        "opening_consumption",
        "execution",
        "execution_review",
        "evaluation_dry_path",
        "evaluation_review",
        "cas_tombstone",
        "release_reserved_before_consumption",
        "consumed_before_execution",
        "execution_independently_reviewed",
        "evaluation_dry_path_independently_reviewed",
        "real_native_callback_tick_count",
        "fresh_identity_cas_created",
        "fresh_outcome_consumed",
        "claim_authorized",
        "outcome_fields_consumed",
    }
)


def run_nonfresh_entrypoint_lifecycle(
    *,
    production_preflight: Mapping[str, Any],
    implementation_head: str,
    artifact_path: str,
) -> dict[str, Any]:
    preflight = validate_production_composition_preflight(
        production_preflight
    )
    full_identity = validate_holdout_identity(preflight["holdout_identity"])
    protocol = validate_experiment_protocol(preflight["experiment_protocol"])
    _require_head(implementation_head)
    mini_identity = _mini_identity(
        full_identity=full_identity,
        implementation_head=implementation_head,
        preflight=preflight,
    )
    artifact = _canonical_artifact_path(artifact_path)
    base = (
        f"{artifact}/nonfresh_entrypoint_"
        f"{mini_identity['holdout_identity_sha256'][:16]}"
    )
    bindings = _bindings(base, preflight)
    run_nonce = canonical_sha256(
        {
            "role": "nonfresh_entrypoint_preflight",
            "implementation_head": implementation_head,
            "holdout_identity_sha256": mini_identity[
                "holdout_identity_sha256"
            ],
        }
    )
    authorized_output = f"{base}/execution"
    cas_path = (
        f"{CAS_ROOT.as_posix()}/"
        f"{mini_identity['holdout_identity_sha256']}.json"
    )
    controller = freeze_holdout_controller_decision(
        implementation_source_head=implementation_head,
        pointer_head_at_release=implementation_head,
        critical_implementation_manifest_sha256=canonical_sha256(
            {
                "role": "nonfresh_entrypoint_preflight_manifest",
                "implementation_head": implementation_head,
            }
        ),
        preopen_authority=bindings["preopen_authority"],
        preopen_review=bindings["preopen_review"],
        production_composition_preflight=bindings[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=bindings[
            "production_composition_preflight_review"
        ],
        b2_tombstone=bindings["b2_tombstone"],
        b2_failure_review=bindings["b2_failure_review"],
        holdout_identity=mini_identity,
        experiment_protocol=protocol,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output,
        cas_tombstone_path=cas_path,
    )
    controller_sha = canonical_sha256(controller)
    release = freeze_holdout_opening_release(
        implementation_source_head=implementation_head,
        pointer_head_at_release=implementation_head,
        critical_implementation_manifest_sha256=controller[
            "critical_implementation_manifest_sha256"
        ],
        controller_decision_root_sha256=controller_sha,
        preopen_authority=bindings["preopen_authority"],
        preopen_review=bindings["preopen_review"],
        production_composition_preflight=bindings[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=bindings[
            "production_composition_preflight_review"
        ],
        b2_tombstone=bindings["b2_tombstone"],
        b2_failure_review=bindings["b2_failure_review"],
        holdout_identity=mini_identity,
        experiment_protocol=protocol,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output,
        cas_tombstone_path=cas_path,
    )
    release_sha = canonical_sha256(release)
    reserved = reserve_holdout_identity(
        CAS_ROOT,
        holdout_identity=mini_identity,
        experiment_protocol=protocol,
        reservation_commitment_sha256=release[
            "reservation_commitment_sha256"
        ],
    )
    if reserved.as_posix() != cas_path:
        raise ValueError("non-Fresh entrypoint CAS reservation path drifted")
    consumption = consume_holdout_opening(
        opening_release=release,
        opening_release_root_sha256=release_sha,
    )
    execution = _execution_receipt(
        preflight=preflight,
        identity=mini_identity,
        protocol=protocol,
        release_sha=release_sha,
        consumption=consumption,
    )
    execution_review = _execution_review(
        execution=execution,
        preflight=preflight,
        identity=mini_identity,
        protocol=protocol,
    )
    evaluation = _evaluation_dry_path(
        execution=execution,
        execution_review=execution_review,
        identity=mini_identity,
        protocol=protocol,
    )
    evaluation_review = _evaluation_review(
        evaluation=evaluation,
        execution=execution,
        execution_review=execution_review,
    )
    final_tombstone = transition_holdout_identity(
        reserved,
        expected_state="opened_consumed",
        next_state="terminal_success",
        terminal_artifact_root_sha256=canonical_sha256(evaluation_review),
        terminal_reason="passed_nonfresh_entrypoint_lifecycle_preflight",
        outcome_evaluation_completed=True,
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_nonfresh_holdout_entrypoint_lifecycle",
        "implementation_head": implementation_head,
        "production_preflight_payload_sha256": preflight[
            "preflight_payload_sha256"
        ],
        "nonfresh_holdout_identity": mini_identity,
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "controller_decision": controller,
        "controller_decision_payload_sha256": controller_sha,
        "opening_release": release,
        "opening_release_payload_sha256": release_sha,
        "opening_consumption": consumption,
        "execution": execution,
        "execution_review": execution_review,
        "evaluation_dry_path": evaluation,
        "evaluation_review": evaluation_review,
        "cas_tombstone": final_tombstone,
        "release_reserved_before_consumption": True,
        "consumed_before_execution": True,
        "execution_independently_reviewed": True,
        "evaluation_dry_path_independently_reviewed": True,
        "real_native_callback_tick_count": 192,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
    }
    return validate_nonfresh_entrypoint_lifecycle(
        result,
        production_preflight=preflight,
        artifact_path=artifact,
    )


def validate_nonfresh_entrypoint_lifecycle(
    value: Mapping[str, Any],
    *,
    production_preflight: Mapping[str, Any],
    artifact_path: str,
) -> dict[str, Any]:
    preflight = validate_production_composition_preflight(
        production_preflight
    )
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("non-Fresh entrypoint lifecycle field set drifted")
    result = dict(value)
    _require_head(result["implementation_head"])
    identity = validate_holdout_identity(
        result["nonfresh_holdout_identity"]
    )
    expected_identity = _mini_identity(
        full_identity=preflight["holdout_identity"],
        implementation_head=result["implementation_head"],
        preflight=preflight,
    )
    protocol = validate_experiment_protocol(preflight["experiment_protocol"])
    expected_base = (
        f"{_canonical_artifact_path(artifact_path)}/nonfresh_entrypoint_"
        f"{expected_identity['holdout_identity_sha256'][:16]}"
    )
    expected_bindings = _bindings(expected_base, preflight)
    expected_nonce = canonical_sha256(
        {
            "role": "nonfresh_entrypoint_preflight",
            "implementation_head": result["implementation_head"],
            "holdout_identity_sha256": expected_identity[
                "holdout_identity_sha256"
            ],
        }
    )
    expected_output = f"{expected_base}/execution"
    expected_cas = (
        f"{CAS_ROOT.as_posix()}/"
        f"{expected_identity['holdout_identity_sha256']}.json"
    )
    expected_manifest_sha = canonical_sha256(
        {
            "role": "nonfresh_entrypoint_preflight_manifest",
            "implementation_head": result["implementation_head"],
        }
    )
    controller = validate_holdout_controller_decision(
        result["controller_decision"]
    )
    expected_controller = freeze_holdout_controller_decision(
        implementation_source_head=result["implementation_head"],
        pointer_head_at_release=result["implementation_head"],
        critical_implementation_manifest_sha256=expected_manifest_sha,
        preopen_authority=expected_bindings["preopen_authority"],
        preopen_review=expected_bindings["preopen_review"],
        production_composition_preflight=expected_bindings[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=expected_bindings[
            "production_composition_preflight_review"
        ],
        b2_tombstone=expected_bindings["b2_tombstone"],
        b2_failure_review=expected_bindings["b2_failure_review"],
        holdout_identity=expected_identity,
        experiment_protocol=protocol,
        run_nonce=expected_nonce,
        authorized_output_dir=expected_output,
        cas_tombstone_path=expected_cas,
    )
    release = validate_holdout_opening_release(result["opening_release"])
    controller_sha = canonical_sha256(controller)
    expected_controller_sha = canonical_sha256(expected_controller)
    expected_release = freeze_holdout_opening_release(
        implementation_source_head=result["implementation_head"],
        pointer_head_at_release=result["implementation_head"],
        critical_implementation_manifest_sha256=expected_manifest_sha,
        controller_decision_root_sha256=expected_controller_sha,
        preopen_authority=expected_bindings["preopen_authority"],
        preopen_review=expected_bindings["preopen_review"],
        production_composition_preflight=expected_bindings[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=expected_bindings[
            "production_composition_preflight_review"
        ],
        b2_tombstone=expected_bindings["b2_tombstone"],
        b2_failure_review=expected_bindings["b2_failure_review"],
        holdout_identity=expected_identity,
        experiment_protocol=protocol,
        run_nonce=expected_nonce,
        authorized_output_dir=expected_output,
        cas_tombstone_path=expected_cas,
    )
    release_sha = canonical_sha256(release)
    consumption = validate_holdout_opening_consumption(
        result["opening_consumption"],
        opening_release=release,
        opening_release_root_sha256=release_sha,
    )
    expected_execution = _execution_receipt(
        preflight=preflight,
        identity=identity,
        protocol=protocol,
        release_sha=release_sha,
        consumption=consumption,
    )
    expected_execution_review = _execution_review(
        execution=expected_execution,
        preflight=preflight,
        identity=identity,
        protocol=protocol,
    )
    expected_evaluation = _evaluation_dry_path(
        execution=expected_execution,
        execution_review=expected_execution_review,
        identity=identity,
        protocol=protocol,
    )
    expected_evaluation_review = _evaluation_review(
        evaluation=expected_evaluation,
        execution=expected_execution,
        execution_review=expected_execution_review,
    )
    tombstone = validate_tombstone(result["cas_tombstone"])
    actual_tombstone = validate_tombstone(
        _strict_canonical_json(Path(release["cas_tombstone_path"]))
    )
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_nonfresh_holdout_entrypoint_lifecycle",
        "production_preflight_payload_sha256": preflight[
            "preflight_payload_sha256"
        ],
        "nonfresh_holdout_identity": expected_identity,
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "controller_decision": expected_controller,
        "controller_decision_payload_sha256": controller_sha,
        "opening_release": expected_release,
        "opening_release_payload_sha256": release_sha,
        "execution": expected_execution,
        "execution_review": expected_execution_review,
        "evaluation_dry_path": expected_evaluation,
        "evaluation_review": expected_evaluation_review,
        "cas_tombstone": actual_tombstone,
        "release_reserved_before_consumption": True,
        "consumed_before_execution": True,
        "execution_independently_reviewed": True,
        "evaluation_dry_path_independently_reviewed": True,
        "real_native_callback_tick_count": 192,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
    }
    if (
        not strict_equal(identity, expected_identity)
        or not strict_equal(controller, expected_controller)
        or not strict_equal(release, expected_release)
        or not strict_equal(tombstone, actual_tombstone)
        or controller["holdout_identity"] != identity
        or release["holdout_identity"] != identity
        or controller["experiment_protocol"] != protocol
        or release["experiment_protocol"] != protocol
        or release["controller_decision_root_sha256"] != controller_sha
    ):
        raise ValueError("non-Fresh entrypoint lifecycle authority drifted")
    for name, expected in exact.items():
        if not strict_equal(result[name], expected):
            raise ValueError(f"non-Fresh entrypoint lifecycle {name} drifted")
    if release["authorized_output_dir"] != f"{expected_base}/execution":
        raise ValueError("non-Fresh entrypoint output authority drifted")
    if (
        actual_tombstone["state"] != "terminal_success"
        or actual_tombstone["opening_release_root_sha256"] != release_sha
        or actual_tombstone["marker_sha256"] != consumption["marker_sha256"]
        or actual_tombstone["terminal_artifact_root_sha256"]
        != canonical_sha256(expected_evaluation_review)
        or actual_tombstone["outcome_evaluation_completed"] is not True
    ):
        raise ValueError("non-Fresh entrypoint terminal CAS drifted")
    return result


def _mini_identity(
    *,
    full_identity: Mapping[str, Any],
    implementation_head: str,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    identity = validate_holdout_identity(full_identity)
    return freeze_holdout_identity(
        split="fresh_b3_nonfresh_production_entrypoint_fixture",
        scenario_manifest_sha256=canonical_sha256(
            {
                "role": "nonfresh_production_entrypoint_fixture",
                "full_identity_sha256": identity[
                    "holdout_identity_sha256"
                ],
                "fixture_root_sha256": preflight["fixture_root_sha256"],
                "implementation_head": implementation_head,
            }
        ),
        map_suite_payload_sha256=identity["map_suite_payload_sha256"],
        route_census_sha256=identity["route_census_sha256"],
        corridor_census_sha256=identity["corridor_census_sha256"],
        semantic_census_sha256=identity["semantic_census_sha256"],
        execution_plan_sha256=canonical_sha256(
            {
                "role": "one_pair_three_arm_entrypoint_dry_plan",
                "config_sha256": preflight["config_sha256"],
                "tick_count": 192,
            }
        ),
        seeds=[identity["seeds"][0]],
        arm_order_commit_sha256=canonical_sha256(list(ARMS)),
        paired_unit_count=1,
        arm_run_count=3,
        tick_capacity=192,
    )


def _bindings(
    base: str, preflight: Mapping[str, Any]
) -> dict[str, dict[str, str]]:
    roots = {
        "preopen_authority": canonical_sha256(
            {
                "role": "nonfresh_preopen_fixture",
                "identity": preflight["holdout_identity"][
                    "holdout_identity_sha256"
                ],
            }
        ),
        "preopen_review": canonical_sha256(
            {"role": "nonfresh_preopen_fixture_review"}
        ),
        "production_composition_preflight": preflight[
            "preflight_payload_sha256"
        ],
        "production_composition_preflight_review": canonical_sha256(
            {
                "role": "nonfresh_preflight_independent_review",
                "preflight_payload_sha256": preflight[
                    "preflight_payload_sha256"
                ],
            }
        ),
        "b2_tombstone": canonical_sha256(
            {"role": "nonfresh_b2_tombstone_fixture"}
        ),
        "b2_failure_review": canonical_sha256(
            {"role": "nonfresh_b2_failure_review_fixture"}
        ),
    }
    return {
        name: {"path": f"{base}/{name}", "root_sha256": root}
        for name, root in roots.items()
    }


def _execution_receipt(
    *,
    preflight: Mapping[str, Any],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
    release_sha: str,
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    callbacks = preflight["native_callback_receipts"]
    return {
        "schema_version": "camp_dp_v25_nonfresh_holdout_execution_dry_v1",
        "status": "passed_nonfresh_holdout_execution_dry_path",
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "opening_release_payload_sha256": release_sha,
        "opening_marker_sha256": consumption["marker_sha256"],
        "config_sha256": dict(preflight["config_sha256"]),
        "native_callback_sha256": {
            arm: canonical_sha256(callbacks[arm]) for arm in ARMS
        },
        "arm_terminals": dict(preflight["arm_terminals"]),
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "candidate0_offline_pool_evidence_required": True,
        "action_committed_before_supplementary_evidence": True,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }


def _execution_review(
    *,
    execution: Mapping[str, Any],
    preflight: Mapping[str, Any],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    expected_callbacks = {
        arm: canonical_sha256(preflight["native_callback_receipts"][arm])
        for arm in ARMS
    }
    if (
        execution["config_sha256"] != preflight["config_sha256"]
        or execution["native_callback_sha256"] != expected_callbacks
        or execution["arm_terminals"] != preflight["arm_terminals"]
    ):
        raise ValueError("non-Fresh execution dry path review drifted")
    return {
        "schema_version": (
            "camp_dp_v25_nonfresh_holdout_execution_dry_review_v1"
        ),
        "status": "passed_independent_nonfresh_execution_dry_review",
        "reviewed_execution_sha256": canonical_sha256(execution),
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "full_denominator_formed": True,
        "fresh_outcome_evaluated": False,
        "claim_authorized": False,
    }


def _evaluation_dry_path(
    *,
    execution: Mapping[str, Any],
    execution_review: Mapping[str, Any],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        execution_review["reviewed_execution_sha256"]
        != canonical_sha256(execution)
        or execution_review["full_denominator_formed"] is not True
    ):
        raise ValueError("non-Fresh evaluation dry path input drifted")
    return {
        "schema_version": "camp_dp_v25_nonfresh_holdout_evaluation_dry_v1",
        "status": "passed_nonfresh_evaluation_dry_path_no_claim",
        "execution_sha256": canonical_sha256(execution),
        "execution_review_sha256": canonical_sha256(execution_review),
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "frozen_claim_rule_loaded": True,
        "outcome_values_available": False,
        "claim_authorized": False,
        "fresh_outcome_consumed": False,
        "outcome_fields_consumed": [],
    }


def _evaluation_review(
    *,
    evaluation: Mapping[str, Any],
    execution: Mapping[str, Any],
    execution_review: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        evaluation["execution_sha256"] != canonical_sha256(execution)
        or evaluation["execution_review_sha256"]
        != canonical_sha256(execution_review)
        or evaluation["outcome_values_available"] is not False
        or evaluation["claim_authorized"] is not False
    ):
        raise ValueError("non-Fresh evaluation dry review drifted")
    return {
        "schema_version": (
            "camp_dp_v25_nonfresh_holdout_evaluation_dry_review_v1"
        ),
        "status": "passed_independent_nonfresh_evaluation_dry_review",
        "reviewed_evaluation_sha256": canonical_sha256(evaluation),
        "frozen_claim_rule_reopened": True,
        "outcome_values_available": False,
        "claim_authorized": False,
        "fresh_outcome_consumed": False,
    }


def _canonical_artifact_path(value: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("/root/autodl-tmp/")
        or Path(value).as_posix() != value
        or ".." in Path(value).parts
    ):
        raise ValueError("non-Fresh lifecycle artifact path drifted")
    return value.rstrip("/")


def _require_head(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError("implementation head must be a full Git SHA")
    return value
