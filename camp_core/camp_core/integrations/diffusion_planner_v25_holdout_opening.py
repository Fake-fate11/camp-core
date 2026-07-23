from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    strict_equal,
    transition_holdout_identity,
    validate_experiment_protocol,
    validate_holdout_identity,
    validate_tombstone,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_one_time_opening_release_v1"
CONTROLLER_SCHEMA_VERSION = "camp_dp_v25_holdout_controller_decision_v1"
CONSUMPTION_SCHEMA_VERSION = "camp_dp_v25_holdout_opening_consumption_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

RELEASE_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "critical_implementation_manifest_sha256",
        "controller_decision_root_sha256",
        "preopen_authority",
        "preopen_review",
        "production_composition_preflight",
        "production_composition_preflight_review",
        "b2_tombstone",
        "b2_failure_review",
        "holdout_identity",
        "experiment_protocol",
        "run_nonce",
        "authorized_output_dir",
        "cas_tombstone_path",
        "reservation_commitment_sha256",
        "device",
        "paired_unit_count",
        "arm_run_count",
        "tick_capacity",
        "holdout_open_authorized",
        "full_config_authorized",
        "full_r_authorized",
        "training_authorized",
        "calibration_authorized",
        "fresh_outcome_consumed",
        "claim_authorized",
        "outcome_fields_consumed",
    }
)
CONTROLLER_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "critical_implementation_manifest_sha256",
        "preopen_authority",
        "preopen_review",
        "production_composition_preflight",
        "production_composition_preflight_review",
        "b2_tombstone",
        "b2_failure_review",
        "holdout_identity",
        "experiment_protocol",
        "run_nonce",
        "authorized_output_dir",
        "cas_tombstone_path",
        "device",
        "paired_unit_count",
        "arm_run_count",
        "tick_capacity",
        "holdout_open_authorized",
        "full_config_authorized",
        "full_r_authorized",
        "training_authorized",
        "calibration_authorized",
        "fresh_outcome_consumed",
        "claim_authorized",
        "outcome_fields_consumed",
    }
)


def freeze_holdout_controller_decision(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    critical_implementation_manifest_sha256: str,
    preopen_authority: Mapping[str, Any],
    preopen_review: Mapping[str, Any],
    production_composition_preflight: Mapping[str, Any],
    production_composition_preflight_review: Mapping[str, Any],
    b2_tombstone: Mapping[str, Any],
    b2_failure_review: Mapping[str, Any],
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    run_nonce: str,
    authorized_output_dir: str,
    cas_tombstone_path: str,
) -> dict[str, Any]:
    identity = validate_holdout_identity(holdout_identity)
    protocol = validate_experiment_protocol(experiment_protocol)
    _require_git_head(implementation_source_head, "implementation_source_head")
    _require_git_head(pointer_head_at_release, "pointer_head_at_release")
    _require_sha(
        critical_implementation_manifest_sha256,
        "critical_implementation_manifest_sha256",
    )
    _require_sha(run_nonce, "run_nonce")
    bindings = {
        "preopen_authority": _binding(preopen_authority, "preopen_authority"),
        "preopen_review": _binding(preopen_review, "preopen_review"),
        "production_composition_preflight": _binding(
            production_composition_preflight,
            "production_composition_preflight",
        ),
        "production_composition_preflight_review": _binding(
            production_composition_preflight_review,
            "production_composition_preflight_review",
        ),
        "b2_tombstone": _binding(b2_tombstone, "b2_tombstone"),
        "b2_failure_review": _binding(b2_failure_review, "b2_failure_review"),
    }
    return {
        "schema_version": CONTROLLER_SCHEMA_VERSION,
        "status": "holdout_one_time_opening_authorized",
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest_sha256": (
            critical_implementation_manifest_sha256
        ),
        **bindings,
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "run_nonce": run_nonce,
        "authorized_output_dir": _canonical_output(authorized_output_dir),
        "cas_tombstone_path": _canonical_cas_path(
            cas_tombstone_path, identity["holdout_identity_sha256"]
        ),
        "device": "cuda",
        "paired_unit_count": identity["paired_unit_count"],
        "arm_run_count": identity["arm_run_count"],
        "tick_capacity": identity["tick_capacity"],
        "holdout_open_authorized": True,
        "full_config_authorized": False,
        "full_r_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "fresh_outcome_consumed": False,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
    }


def validate_holdout_controller_decision(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != CONTROLLER_FIELDS:
        raise ValueError("holdout controller decision field set drifted")
    expected = freeze_holdout_controller_decision(
        implementation_source_head=value["implementation_source_head"],
        pointer_head_at_release=value["pointer_head_at_release"],
        critical_implementation_manifest_sha256=value[
            "critical_implementation_manifest_sha256"
        ],
        preopen_authority=value["preopen_authority"],
        preopen_review=value["preopen_review"],
        production_composition_preflight=value[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=value[
            "production_composition_preflight_review"
        ],
        b2_tombstone=value["b2_tombstone"],
        b2_failure_review=value["b2_failure_review"],
        holdout_identity=value["holdout_identity"],
        experiment_protocol=value["experiment_protocol"],
        run_nonce=value["run_nonce"],
        authorized_output_dir=value["authorized_output_dir"],
        cas_tombstone_path=value["cas_tombstone_path"],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout controller decision exact value drifted")
    return expected


def freeze_opening_commitment(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    controller_decision_root_sha256: str,
    preopen_root_sha256: str,
    preflight_root_sha256: str,
    run_nonce: str,
    authorized_output_dir: str,
) -> str:
    for name, value in {
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "preopen_root_sha256": preopen_root_sha256,
        "preflight_root_sha256": preflight_root_sha256,
        "run_nonce": run_nonce,
    }.items():
        _require_sha(value, name)
    output = _canonical_output(authorized_output_dir)
    return canonical_sha256(
        {
            "schema_version": "camp_dp_v25_holdout_opening_commitment_v1",
            "holdout_identity_sha256": holdout_identity_sha256,
            "experiment_protocol_sha256": experiment_protocol_sha256,
            "controller_decision_root_sha256": controller_decision_root_sha256,
            "preopen_root_sha256": preopen_root_sha256,
            "preflight_root_sha256": preflight_root_sha256,
            "run_nonce": run_nonce,
            "authorized_output_dir": output,
        }
    )


def freeze_holdout_opening_release(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    critical_implementation_manifest_sha256: str,
    controller_decision_root_sha256: str,
    preopen_authority: Mapping[str, Any],
    preopen_review: Mapping[str, Any],
    production_composition_preflight: Mapping[str, Any],
    production_composition_preflight_review: Mapping[str, Any],
    b2_tombstone: Mapping[str, Any],
    b2_failure_review: Mapping[str, Any],
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    run_nonce: str,
    authorized_output_dir: str,
    cas_tombstone_path: str,
) -> dict[str, Any]:
    identity = validate_holdout_identity(holdout_identity)
    protocol = validate_experiment_protocol(experiment_protocol)
    for name, value in {
        "critical_implementation_manifest_sha256": (
            critical_implementation_manifest_sha256
        ),
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "run_nonce": run_nonce,
    }.items():
        _require_sha(value, name)
    _require_git_head(implementation_source_head, "implementation_source_head")
    _require_git_head(pointer_head_at_release, "pointer_head_at_release")
    bindings = {
        "preopen_authority": _binding(preopen_authority, "preopen_authority"),
        "preopen_review": _binding(preopen_review, "preopen_review"),
        "production_composition_preflight": _binding(
            production_composition_preflight,
            "production_composition_preflight",
        ),
        "production_composition_preflight_review": _binding(
            production_composition_preflight_review,
            "production_composition_preflight_review",
        ),
        "b2_tombstone": _binding(b2_tombstone, "b2_tombstone"),
        "b2_failure_review": _binding(b2_failure_review, "b2_failure_review"),
    }
    output = _canonical_output(authorized_output_dir)
    cas_path = _canonical_cas_path(
        cas_tombstone_path, identity["holdout_identity_sha256"]
    )
    commitment = freeze_opening_commitment(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        controller_decision_root_sha256=controller_decision_root_sha256,
        preopen_root_sha256=bindings["preopen_authority"]["root_sha256"],
        preflight_root_sha256=bindings["production_composition_preflight"][
            "root_sha256"
        ],
        run_nonce=run_nonce,
        authorized_output_dir=output,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "holdout_one_time_opening_released",
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest_sha256": (
            critical_implementation_manifest_sha256
        ),
        "controller_decision_root_sha256": controller_decision_root_sha256,
        **bindings,
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "run_nonce": run_nonce,
        "authorized_output_dir": output,
        "cas_tombstone_path": cas_path,
        "reservation_commitment_sha256": commitment,
        "device": "cuda",
        "paired_unit_count": identity["paired_unit_count"],
        "arm_run_count": identity["arm_run_count"],
        "tick_capacity": identity["tick_capacity"],
        "holdout_open_authorized": True,
        "full_config_authorized": False,
        "full_r_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "fresh_outcome_consumed": False,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
    }


def validate_holdout_opening_release(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != RELEASE_FIELDS:
        raise ValueError("holdout opening release field set drifted")
    expected = freeze_holdout_opening_release(
        implementation_source_head=value["implementation_source_head"],
        pointer_head_at_release=value["pointer_head_at_release"],
        critical_implementation_manifest_sha256=value[
            "critical_implementation_manifest_sha256"
        ],
        controller_decision_root_sha256=value[
            "controller_decision_root_sha256"
        ],
        preopen_authority=value["preopen_authority"],
        preopen_review=value["preopen_review"],
        production_composition_preflight=value[
            "production_composition_preflight"
        ],
        production_composition_preflight_review=value[
            "production_composition_preflight_review"
        ],
        b2_tombstone=value["b2_tombstone"],
        b2_failure_review=value["b2_failure_review"],
        holdout_identity=value["holdout_identity"],
        experiment_protocol=value["experiment_protocol"],
        run_nonce=value["run_nonce"],
        authorized_output_dir=value["authorized_output_dir"],
        cas_tombstone_path=value["cas_tombstone_path"],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout opening release exact value drifted")
    return expected


def consume_holdout_opening(
    *,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
) -> dict[str, Any]:
    release = validate_holdout_opening_release(opening_release)
    release_root = _require_sha(
        opening_release_root_sha256, "opening_release_root_sha256"
    )
    tombstone_path = Path(release["cas_tombstone_path"])
    current = validate_tombstone(_canonical_tombstone(tombstone_path))
    if (
        current["state"] != "reserved"
        or current["holdout_identity_sha256"]
        != release["holdout_identity"]["holdout_identity_sha256"]
        or current["experiment_protocol_sha256"]
        != release["experiment_protocol"]["experiment_protocol_sha256"]
        or current["reservation_commitment_sha256"]
        != release["reservation_commitment_sha256"]
    ):
        raise FileExistsError("holdout identity is not reserved for this release")
    marker_sha = canonical_sha256(
        {
            "schema_version": "camp_dp_v25_holdout_consumption_marker_v1",
            "opening_release_root_sha256": release_root,
            "holdout_identity_sha256": current["holdout_identity_sha256"],
            "reservation_commitment_sha256": current[
                "reservation_commitment_sha256"
            ],
            "state": "opened_consumed",
        }
    )
    updated = transition_holdout_identity(
        tombstone_path,
        expected_state="reserved",
        next_state="opened_consumed",
        opening_release_root_sha256=release_root,
        marker_sha256=marker_sha,
    )
    return {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "status": "holdout_opened_consumed",
        "opening_release_root_sha256": release_root,
        "holdout_identity_sha256": updated["holdout_identity_sha256"],
        "experiment_protocol_sha256": updated[
            "experiment_protocol_sha256"
        ],
        "reservation_commitment_sha256": updated[
            "reservation_commitment_sha256"
        ],
        "cas_tombstone_path": str(tombstone_path),
        "marker_sha256": marker_sha,
        "consumed_before_outcome_capable_operation": True,
        "second_opening_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_opening": [],
    }


def validate_holdout_opening_consumption(
    value: Mapping[str, Any],
    *,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
) -> dict[str, Any]:
    release = validate_holdout_opening_release(opening_release)
    release_root = _require_sha(
        opening_release_root_sha256, "opening_release_root_sha256"
    )
    expected_fields = {
        "schema_version",
        "status",
        "opening_release_root_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "reservation_commitment_sha256",
        "cas_tombstone_path",
        "marker_sha256",
        "consumed_before_outcome_capable_operation",
        "second_opening_allowed",
        "new_nonce_allowed",
        "suffix_allowed",
        "outcome_fields_consumed_before_opening",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise ValueError("holdout opening consumption field set drifted")
    expected_values = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "status": "holdout_opened_consumed",
        "opening_release_root_sha256": release_root,
        "holdout_identity_sha256": release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "reservation_commitment_sha256": release[
            "reservation_commitment_sha256"
        ],
        "cas_tombstone_path": release["cas_tombstone_path"],
        "consumed_before_outcome_capable_operation": True,
        "second_opening_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_opening": [],
    }
    for name, expected in expected_values.items():
        if not strict_equal(value.get(name), expected):
            raise ValueError(f"holdout opening consumption {name} drifted")
    _require_sha(value["marker_sha256"], "marker_sha256")
    return dict(value)


def _binding(value: Mapping[str, Any], name: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"{name} binding field set drifted")
    path_text = value["path"]
    path = PurePosixPath(str(path_text))
    if (
        type(path_text) is not str
        or not path.is_absolute()
        or path.as_posix() != path_text
        or ".." in path.parts
        or "." in path.parts
        or "\\" in path_text
    ):
        raise ValueError(f"{name} path is not absolute canonical text")
    return {
        "path": path_text,
        "root_sha256": _require_sha(value["root_sha256"], f"{name}.root_sha256"),
    }


def _canonical_output(value: Any) -> str:
    if type(value) is not str or not value.startswith("/root/autodl-tmp/"):
        raise ValueError("authorized output path drifted")
    path = PurePosixPath(value)
    if (
        not path.is_absolute()
        or path.as_posix() != value
        or ".." in path.parts
        or "." in path.parts
        or "\\" in value
    ):
        raise ValueError("authorized output path is not canonical")
    return value


def _canonical_cas_path(value: Any, identity_sha256: str) -> str:
    expected = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity_sha256}.json"
    )
    if value != expected:
        raise ValueError("holdout CAS tombstone path drifted")
    return expected


def _canonical_tombstone(path: Path) -> dict[str, Any]:
    from .diffusion_planner_v25_holdout_contract import (
        _strict_canonical_json,
    )

    return _strict_canonical_json(path)


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _require_git_head(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase Git SHA")
    return value
