from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract_sha256,
)
from .diffusion_planner_v25_holdout_contract import strict_equal
from .diffusion_planner_v25_holdout_opening import (
    freeze_holdout_controller_decision,
    freeze_holdout_opening_release,
)
from .diffusion_planner_v25_holdout_state import (
    operational_identity_path,
    operational_attempt_path,
    scientific_identity_path,
    validate_operational_attempt,
    validate_operational_identity_reservation,
    validate_scientific_ledger,
)


CONTROLLER_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_controller_decision_production_rc_v2"
)
RELEASE_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_one_time_opening_release_production_rc_v2"
)
EXPOSURE_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_scientific_exposure_receipt_v1"
)


def freeze_production_rc_controller_decision(
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
    cas_root: Path,
) -> dict[str, Any]:
    identity_sha = holdout_identity["holdout_identity_sha256"]
    scientific_path = scientific_identity_path(cas_root, identity_sha)
    operational_path = operational_attempt_path(cas_root, run_nonce)
    identity_reservation_path = operational_identity_path(
        cas_root, identity_sha
    )
    legacy_scientific_path = (
        Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
        / f"{identity_sha}.json"
    )
    legacy = freeze_holdout_controller_decision(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        critical_implementation_manifest_sha256=(
            critical_implementation_manifest_sha256
        ),
        preopen_authority=preopen_authority,
        preopen_review=preopen_review,
        production_composition_preflight=production_composition_preflight,
        production_composition_preflight_review=(
            production_composition_preflight_review
        ),
        b2_tombstone=b2_tombstone,
        b2_failure_review=b2_failure_review,
        holdout_identity=holdout_identity,
        experiment_protocol=experiment_protocol,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        cas_tombstone_path=str(legacy_scientific_path),
    )
    legacy.pop("cas_tombstone_path")
    legacy["schema_version"] = CONTROLLER_SCHEMA_VERSION
    legacy["status"] = "holdout_production_rc_opening_authorized"
    legacy["operational_attempt_path"] = str(operational_path)
    legacy["operational_identity_reservation_path"] = str(
        identity_reservation_path
    )
    legacy["scientific_ledger_path"] = str(scientific_path)
    legacy["actual_native_receipt_contract_sha256"] = (
        actual_native_receipt_contract_sha256()
    )
    legacy["scientific_identity_consumed_at_release"] = False
    return legacy


def validate_production_rc_controller_decision(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "operational_attempt_path",
        "operational_identity_reservation_path",
        "scientific_ledger_path",
        "actual_native_receipt_contract_sha256",
        "scientific_identity_consumed_at_release",
    }
    if type(value) is not dict or not required.issubset(value):
        raise ValueError("production RC controller field set drifted")
    cas_root = Path(value["scientific_ledger_path"]).resolve().parent.parent
    expected = freeze_production_rc_controller_decision(
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
        cas_root=cas_root,
    )
    if not strict_equal(value, expected):
        raise ValueError("production RC controller exact value drifted")
    return expected


def freeze_production_rc_opening_release(
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
    cas_root: Path,
) -> dict[str, Any]:
    identity_sha = holdout_identity["holdout_identity_sha256"]
    scientific_path = scientific_identity_path(cas_root, identity_sha)
    operational_path = operational_attempt_path(cas_root, run_nonce)
    identity_reservation_path = operational_identity_path(
        cas_root, identity_sha
    )
    legacy_scientific_path = (
        Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
        / f"{identity_sha}.json"
    )
    legacy = freeze_holdout_opening_release(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        critical_implementation_manifest_sha256=(
            critical_implementation_manifest_sha256
        ),
        controller_decision_root_sha256=controller_decision_root_sha256,
        preopen_authority=preopen_authority,
        preopen_review=preopen_review,
        production_composition_preflight=production_composition_preflight,
        production_composition_preflight_review=(
            production_composition_preflight_review
        ),
        b2_tombstone=b2_tombstone,
        b2_failure_review=b2_failure_review,
        holdout_identity=holdout_identity,
        experiment_protocol=experiment_protocol,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        cas_tombstone_path=str(legacy_scientific_path),
    )
    legacy.pop("cas_tombstone_path")
    legacy["schema_version"] = RELEASE_SCHEMA_VERSION
    legacy["status"] = "holdout_production_rc_opening_released"
    legacy["operational_attempt_path"] = str(operational_path)
    legacy["operational_identity_reservation_path"] = str(
        identity_reservation_path
    )
    legacy["scientific_ledger_path"] = str(scientific_path)
    legacy["actual_native_receipt_contract_sha256"] = (
        actual_native_receipt_contract_sha256()
    )
    legacy["scientific_identity_consumed_at_release"] = False
    return legacy


def validate_production_rc_opening_release(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "operational_attempt_path",
        "operational_identity_reservation_path",
        "scientific_ledger_path",
        "actual_native_receipt_contract_sha256",
        "scientific_identity_consumed_at_release",
    }
    if type(value) is not dict or not required.issubset(value):
        raise ValueError("production RC release field set drifted")
    cas_root = Path(value["scientific_ledger_path"]).resolve().parent.parent
    expected = freeze_production_rc_opening_release(
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
        cas_root=cas_root,
    )
    if not strict_equal(value, expected):
        raise ValueError("production RC release exact value drifted")
    return expected


def freeze_scientific_exposure_receipt(
    *,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    operational_attempt: Mapping[str, Any],
    scientific_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    release = validate_production_rc_opening_release(opening_release)
    operational = validate_operational_attempt(operational_attempt)
    scientific = validate_scientific_ledger(scientific_ledger)
    identity_reservation = validate_operational_identity_reservation(
        _strict_canonical_json(
            Path(release["operational_identity_reservation_path"])
        )
    )
    for name, value in {
        "opening_release_root_sha256": opening_release_root_sha256,
        "operational_attempt_sha256": _canonical_sha(operational),
        "scientific_ledger_sha256": _canonical_sha(scientific),
        "operational_identity_reservation_sha256": _canonical_sha(
            identity_reservation
        ),
    }.items():
        _sha(value, name)
    if (
        operational["state"] != "exposure_started"
        or scientific["state"] != "exposure_started"
        or operational["opening_release_root_sha256"]
        != opening_release_root_sha256
        or scientific["opening_release_root_sha256"]
        != opening_release_root_sha256
        or operational["holdout_identity_sha256"]
        != release["holdout_identity"]["holdout_identity_sha256"]
        or scientific["holdout_identity_sha256"]
        != operational["holdout_identity_sha256"]
        or operational["run_nonce"] != release["run_nonce"]
        or scientific["run_nonce"] != release["run_nonce"]
        or identity_reservation["state"] != "exposure_started"
        or identity_reservation["run_nonce"] != release["run_nonce"]
        or identity_reservation["holdout_identity_sha256"]
        != scientific["holdout_identity_sha256"]
    ):
        raise ValueError("production RC scientific exposure binding drifted")
    return {
        "schema_version": EXPOSURE_SCHEMA_VERSION,
        "status": "holdout_scientific_exposure_started",
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": scientific["holdout_identity_sha256"],
        "experiment_protocol_sha256": scientific[
            "experiment_protocol_sha256"
        ],
        "run_nonce": scientific["run_nonce"],
        "operational_attempt_path": release["operational_attempt_path"],
        "operational_attempt_sha256": _canonical_sha(operational),
        "operational_identity_reservation_path": release[
            "operational_identity_reservation_path"
        ],
        "operational_identity_reservation_sha256": _canonical_sha(
            identity_reservation
        ),
        "scientific_ledger_path": release["scientific_ledger_path"],
        "scientific_ledger_sha256": _canonical_sha(scientific),
        "scientific_exposure_started_before_first_forward": True,
        "second_exposure_allowed": False,
        "new_nonce_allowed_after_exposure": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_exposure": [],
    }


def validate_scientific_exposure_receipt(
    value: Mapping[str, Any],
    *,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
) -> dict[str, Any]:
    release = validate_production_rc_opening_release(opening_release)
    operational = validate_operational_attempt(
        _strict_canonical_json(Path(release["operational_attempt_path"]))
    )
    scientific = validate_scientific_ledger(
        _strict_canonical_json(Path(release["scientific_ledger_path"]))
    )
    identity_reservation = validate_operational_identity_reservation(
        _strict_canonical_json(
            Path(release["operational_identity_reservation_path"])
        )
    )
    # Later ledger states retain the immutable exposure prefix.  Rebuild the
    # receipt from the sealed hashes recorded at exposure rather than trusting
    # the current mutable ledger bytes.
    if scientific["history"][0] != "exposure_started":
        raise ValueError("scientific ledger lacks exposure start")
    exposure_operational = dict(operational)
    exposure_operational.update(
        {
            "state": "exposure_started",
            "history": [
                "release_reserved",
                "release_sealed",
                "exposure_started",
            ],
            "terminal_reason": None,
            "scientific_identity_consumed": True,
            "new_attempt_allowed_if_pre_exposure_failure": False,
        }
    )
    exposure_operational = validate_operational_attempt(exposure_operational)
    exposure_scientific = dict(scientific)
    exposure_scientific.update(
        {
            "state": "exposure_started",
            "history": ["exposure_started"],
            "planned_arm_run_count": None,
            "terminal_arm_run_count": 0,
            "terminal_artifact_root_sha256": None,
            "terminal_reason": None,
        }
    )
    exposure_scientific = validate_scientific_ledger(exposure_scientific)
    expected_static = {
        "schema_version": EXPOSURE_SCHEMA_VERSION,
        "status": "holdout_scientific_exposure_started",
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "run_nonce": release["run_nonce"],
        "operational_attempt_path": release["operational_attempt_path"],
        "operational_identity_reservation_path": release[
            "operational_identity_reservation_path"
        ],
        "scientific_ledger_path": release["scientific_ledger_path"],
        "scientific_exposure_started_before_first_forward": True,
        "second_exposure_allowed": False,
        "new_nonce_allowed_after_exposure": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_exposure": [],
    }
    if type(value) is not dict or set(value) != {
        *expected_static,
        "operational_attempt_sha256",
        "operational_identity_reservation_sha256",
        "scientific_ledger_sha256",
    }:
        raise ValueError("scientific exposure receipt field set drifted")
    for name, expected in expected_static.items():
        if not strict_equal(value[name], expected):
            raise ValueError(f"scientific exposure receipt drifted: {name}")
    _sha(value["operational_attempt_sha256"], "operational_attempt_sha256")
    _sha(
        value["operational_identity_reservation_sha256"],
        "operational_identity_reservation_sha256",
    )
    _sha(value["scientific_ledger_sha256"], "scientific_ledger_sha256")
    if (
        value["operational_attempt_sha256"]
        != _canonical_sha(exposure_operational)
        or value["scientific_ledger_sha256"]
        != _canonical_sha(exposure_scientific)
        or identity_reservation["state"] != "exposure_started"
        or value["operational_identity_reservation_sha256"]
        != _canonical_sha(identity_reservation)
    ):
        raise ValueError("scientific exposure receipt ledger hash drifted")
    return dict(value)


def _strict_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate production RC ledger key: {key}")
            result[key] = item
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite production RC ledger token: {token}")
        ),
    )
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if type(value) is not dict or raw != expected:
        raise ValueError("production RC ledger must be a canonical object")
    return value


def _canonical_sha(value: Mapping[str, Any]) -> str:
    from .diffusion_planner_v25_holdout_contract import canonical_sha256

    return canonical_sha256(value)


def _sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
