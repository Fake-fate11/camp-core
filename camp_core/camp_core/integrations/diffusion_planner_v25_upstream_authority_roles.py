from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_artifact_seal import verify_complete_seal
from .diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
)
from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    strict_equal,
)


SCHEMA_VERSION = "camp_dp_v25_upstream_authority_role_contract_v1"
STATUS = "frozen_complete_upstream_authority_role_contract"


_DIRECT = "direct_success"
_RECOVERY = "accepted_via_recovery"
_CLOSEOUT = "accepted_via_closeout"


ROLE_SPECS: dict[str, dict[str, Any]] = {
    "accepted_b3_preopen": {
        "payload_file": "preopen_authority.json",
        "schema_version": "camp_dp_v25_fresh_b3_consolidated_preopen_authority_v1",
        "status": "passed_outcome_blind_fresh_b3_preopen_authority",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "accepted_b3_preopen_review",
    },
    "accepted_b3_preopen_review": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_fresh_b3_preopen_independent_review_v1",
        "status": "passed_independent_fresh_b3_preopen_review",
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "atom_mechanism": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_atom_mechanism_artifact_v1",
        "status": "frozen_atom_mechanism_ready_before_fresh_b2_opening",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "atom_mechanism_review",
    },
    "atom_mechanism_review": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_atom_mechanism_review_v1",
        "status": "passed_independent_atom_mechanism_preopen_review",
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "b2_consumed_failure": {
        "payload_file": "closeout.json",
        "schema_version": "camp_dp_v25_consumed_holdout_failure_closeout_v1",
        "status": "terminal_consumed_one_shot_engineering_failure",
        "run_exit": 0,
        "mode": _CLOSEOUT,
        "review_role": "b2_consumed_failure_review",
        "failure_payload_file": "failure.json",
        "failure_schema_version": "camp_dp_v25_fresh_b2_execution_artifact_v2",
        "failure_status": "failed_closed_fresh_b2_execution",
        "failure_run_exit": 1,
    },
    "b2_consumed_failure_review": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_consumed_holdout_failure_review_v1",
        "status": "passed_independent_consumed_holdout_failure_review",
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "b3_terminal_closeout": {
        "payload_file": "closeout.json",
        "schema_version": "camp_dp_v25_holdout_terminal_failure_closeout_v1",
        "status": "consumed_one_shot_engineering_failure_no_evaluation_no_claim",
        "run_exit": 0,
        "mode": _CLOSEOUT,
        "review_role": "b3_terminal_closeout_review",
        "failure_payload_file": "fatal.json",
        "failure_schema_version": "camp_dp_v25_holdout_artifact_fatal_v1",
        "failure_status": "artifact_fatal",
        "failure_run_exit": 1,
        "embedded_failure_review_payload_file": "report.json",
        "embedded_failure_review_schema_version": (
            "camp_dp_v25_holdout_execution_review_artifact_v1"
        ),
        "embedded_failure_review_status": (
            "passed_independent_holdout_artifact_fatal_review"
        ),
        "embedded_failure_review_run_exit": 0,
    },
    "b3_terminal_closeout_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_holdout_terminal_failure_closeout_review_v1"
        ),
        "status": (
            "passed_independent_holdout_terminal_failure_closeout_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "calibration_freeze": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_calibration_freeze_from_paired_artifact_v1"
        ),
        "status": "calibration_freeze_passed",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "calibration_freeze_review",
    },
    "calibration_freeze_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_calibration_freeze_from_paired_review_v1"
        ),
        "status": (
            "passed_independent_calibration_freeze_from_paired_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "calibration_preregistration": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_paired_calibration_preregistration_artifact_v1"
        ),
        "status": "paired_calibration_preregistration_frozen",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "calibration_preregistration_review",
    },
    "calibration_preregistration_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_paired_calibration_preregistration_review_v1"
        ),
        "status": (
            "passed_independent_paired_calibration_preregistration_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "calibration_raw": {
        "payload_file": "failure.json",
        "schema_version": (
            "camp_dp_v25_paired_calibration_execution_artifact_v1"
        ),
        "status": "failed_closed_paired_calibration_execution",
        "run_exit": 1,
        "mode": _RECOVERY,
        "recovery_role": "calibration_recovery",
        "recovery_review_role": "calibration_recovery_review",
    },
    "calibration_recovery": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_paired_calibration_recovery_analysis_v1"
        ),
        "status": "recovered_calibration_analysis_complete_fresh_closed",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "calibration_recovery_review",
        "reviewed_root_field": "reviewed_recovery_root_sha256",
        "reviewed_path_field": "reviewed_recovery_artifact",
    },
    "calibration_recovery_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_paired_calibration_recovery_review_v1"
        ),
        "status": (
            "passed_independent_paired_calibration_recovery_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "corrected_corpus": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_controlled_training_corpus_execution_v8"
        ),
        "status": "passed",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "corrected_corpus_review",
    },
    "corrected_corpus_review": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_controlled_training_corpus_review_v8",
        "status": "passed_independent_full_corpus_review",
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "production_equivalence_certificate": {
        "payload_file": "preflight.json",
        "schema_version": (
            "camp_dp_v25_nonfresh_production_equivalence_certificate_v3"
        ),
        "status": "passed_nonfresh_production_equivalence_certificate",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "production_equivalence_certificate_review",
    },
    "production_equivalence_certificate_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_nonfresh_production_equivalence_certificate_"
            "independent_review_v2"
        ),
        "status": (
            "passed_independent_nonfresh_production_equivalence_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "storage": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_fresh_storage_qualification_artifact_v1"
        ),
        "status": "passed_fresh_storage_equivalence_and_capacity",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "storage_review",
    },
    "storage_review": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_fresh_storage_qualification_review_v1"
        ),
        "status": (
            "passed_independent_fresh_storage_equivalence_and_capacity_review"
        ),
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "train_route_source": {
        "payload_file": "report.json",
        "schema_version": (
            "camp_dp_v25_a161_route_signal_source_census_v2"
        ),
        "status": "passed_source_only_route_signal_authority_census",
        "run_exit": 0,
        "mode": _DIRECT,
    },
    "training": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_strict_convex_training_artifact_v1",
        "status": "passed_strict_convex_training",
        "run_exit": 0,
        "mode": _DIRECT,
        "review_role": "training_review",
    },
    "training_review": {
        "payload_file": "report.json",
        "schema_version": "camp_dp_v25_strict_convex_training_review_v1",
        "status": "passed_independent_strict_convex_training_review",
        "run_exit": 0,
        "mode": _DIRECT,
    },
}
_STRICT_SEALED_LEGACY_ROLES = frozenset(
    {"corrected_corpus", "corrected_corpus_review"}
)
for _role_name, _role_spec in ROLE_SPECS.items():
    _role_spec["json_byte_policy"] = (
        "strict_sealed_legacy"
        if _role_name in _STRICT_SEALED_LEGACY_ROLES
        else "camp_canonical"
    )


def freeze_upstream_authority_role_contract(
    bindings: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    normalized = _bindings(bindings)
    roles: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    for role in sorted(ROLE_SPECS):
        spec = ROLE_SPECS[role]
        binding = normalized[role]
        path = Path(binding["path"])
        verify_complete_seal(
            path, binding["root_sha256"], label=f"upstream role {role}"
        )
        _require_run_exit(path, spec["run_exit"], role)
        payload = _authority_object(
            path / spec["payload_file"],
            byte_policy=spec["json_byte_policy"],
        )
        _require_payload(payload, spec, role)
        payloads[role] = payload
        roles.append(
            {
                "role": role,
                "binding": binding,
                "execution_terminal": {
                    "run_exit": spec["run_exit"],
                    "payload_file": spec["payload_file"],
                    "schema_version": spec["schema_version"],
                    "status": spec["status"],
                    "json_byte_policy": spec["json_byte_policy"],
                },
                "authority_disposition": _disposition(
                    role, spec, normalized, payload
                ),
            }
        )
    _verify_crosslinks(normalized, payloads, roles)
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "role_count": len(roles),
        "roles": roles,
    }
    result["contract_sha256"] = canonical_sha256(result)
    return result


def validate_upstream_authority_role_contract(
    value: Mapping[str, Any],
    *,
    bindings: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    normalized = _bindings(bindings)
    if type(value) is not dict or set(value) != {
        "schema_version",
        "status",
        "role_count",
        "roles",
        "contract_sha256",
    }:
        raise ValueError("upstream authority role contract field set drifted")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["status"] != STATUS
        or type(value["role_count"]) is not int
        or value["role_count"] != len(ROLE_SPECS)
        or type(value["roles"]) is not list
        or len(value["roles"]) != len(ROLE_SPECS)
    ):
        raise ValueError("upstream authority role contract header drifted")
    seen: set[str] = set()
    for row in value["roles"]:
        if type(row) is not dict or set(row) != {
            "role",
            "binding",
            "execution_terminal",
            "authority_disposition",
        }:
            raise ValueError("upstream authority role row field set drifted")
        role = row["role"]
        if type(role) is not str or role not in ROLE_SPECS or role in seen:
            raise ValueError("unknown or duplicate upstream authority role")
        seen.add(role)
        spec = ROLE_SPECS[role]
        if not strict_equal(row["binding"], normalized[role]):
            raise ValueError(f"upstream authority binding drifted: {role}")
        expected_terminal = {
            "run_exit": spec["run_exit"],
            "payload_file": spec["payload_file"],
            "schema_version": spec["schema_version"],
            "status": spec["status"],
            "json_byte_policy": spec["json_byte_policy"],
        }
        if not strict_equal(row["execution_terminal"], expected_terminal):
            raise ValueError(f"upstream execution terminal drifted: {role}")
        _validate_disposition_shape(
            role, row["authority_disposition"], spec, normalized
        )
    if seen != set(ROLE_SPECS):
        raise ValueError("upstream authority role set drifted")
    unsigned = dict(value)
    contract_sha256 = unsigned.pop("contract_sha256")
    if (
        type(contract_sha256) is not str
        or contract_sha256 != canonical_sha256(unsigned)
    ):
        raise ValueError("upstream authority role contract SHA drifted")
    return json.loads(json.dumps(value))


def verify_upstream_authority_role_contract(
    value: Mapping[str, Any],
    *,
    bindings: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    stored = validate_upstream_authority_role_contract(
        value, bindings=bindings
    )
    rebuilt = freeze_upstream_authority_role_contract(bindings)
    if not strict_equal(stored, rebuilt):
        raise ValueError("sealed upstream authority role contract drifted")
    return stored


def _bindings(
    value: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or set(value) != set(ROLE_SPECS):
        raise ValueError("complete upstream authority role set is required")
    result: dict[str, dict[str, str]] = {}
    for role in sorted(value):
        item = value[role]
        if type(item) is not dict or set(item) != {"path", "root_sha256"}:
            raise ValueError(f"upstream authority binding drifted: {role}")
        path = Path(item["path"])
        if (
            type(item["path"]) is not str
            or not path.is_absolute()
            or str(path.resolve()) != item["path"]
            or type(item["root_sha256"]) is not str
            or len(item["root_sha256"]) != 64
        ):
            raise ValueError(f"upstream authority binding invalid: {role}")
        result[role] = dict(item)
    return result


def _disposition(
    role: str,
    spec: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, str]],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    mode = spec["mode"]
    if mode == _DIRECT:
        return {
            "mode": mode,
            "independent_review_role": spec.get("review_role"),
        }
    if mode == _RECOVERY:
        recovery_role = spec["recovery_role"]
        review_role = spec["recovery_review_role"]
        chain = {
            "raw": bindings[role],
            "recovery": bindings[recovery_role],
            "recovery_review": bindings[review_role],
        }
        return {
            "mode": mode,
            "recovery_role": recovery_role,
            "recovery_review_role": review_role,
            "chain_id_sha256": canonical_sha256(chain),
        }
    if mode == _CLOSEOUT:
        failure = payload.get("failure_artifact")
        if type(failure) is not dict:
            raise ValueError(f"closeout failure binding missing: {role}")
        disposition: dict[str, Any] = {
            "mode": mode,
            "independent_review_role": spec["review_role"],
            "embedded_failure": _binding(failure, f"{role} failure"),
            "holdout_identity_sha256": _holdout_identity(payload, role),
        }
        if "embedded_failure_review_payload_file" in spec:
            failure_review = payload.get("failure_review")
            if type(failure_review) is not dict:
                raise ValueError(
                    f"closeout failure review binding missing: {role}"
                )
            disposition["embedded_failure_review"] = _binding(
                failure_review, f"{role} failure review"
            )
        chain = {
            "closeout": bindings[role],
            "closeout_review": bindings[spec["review_role"]],
            "embedded_failure": disposition["embedded_failure"],
            "holdout_identity_sha256": disposition[
                "holdout_identity_sha256"
            ],
        }
        if "embedded_failure_review" in disposition:
            chain["embedded_failure_review"] = disposition[
                "embedded_failure_review"
            ]
        disposition["chain_id_sha256"] = canonical_sha256(chain)
        return disposition
    raise ValueError(f"unknown authority disposition: {role}")


def _validate_disposition_shape(
    role: str,
    value: Any,
    spec: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, str]],
) -> None:
    if type(value) is not dict or value.get("mode") != spec["mode"]:
        raise ValueError(f"upstream authority disposition drifted: {role}")
    if spec["mode"] == _DIRECT:
        if value != {
            "mode": _DIRECT,
            "independent_review_role": spec.get("review_role"),
        }:
            raise ValueError(
                f"direct-success authority disposition drifted: {role}"
            )
        return
    if spec["mode"] == _RECOVERY:
        if set(value) != {
            "mode",
            "recovery_role",
            "recovery_review_role",
            "chain_id_sha256",
        }:
            raise ValueError(f"recovery authority disposition drifted: {role}")
        expected_chain = {
            "raw": bindings[role],
            "recovery": bindings[spec["recovery_role"]],
            "recovery_review": bindings[spec["recovery_review_role"]],
        }
        if (
            value["recovery_role"] != spec["recovery_role"]
            or value["recovery_review_role"]
            != spec["recovery_review_role"]
            or value["chain_id_sha256"] != canonical_sha256(expected_chain)
        ):
            raise ValueError(f"recovery authority chain drifted: {role}")
        return
    expected_fields = {
        "mode",
        "independent_review_role",
        "embedded_failure",
        "holdout_identity_sha256",
        "chain_id_sha256",
    }
    if "embedded_failure_review_payload_file" in spec:
        expected_fields.add("embedded_failure_review")
    if (
        set(value) != expected_fields
        or value["independent_review_role"] != spec["review_role"]
        or type(value["holdout_identity_sha256"]) is not str
        or len(value["holdout_identity_sha256"]) != 64
    ):
        raise ValueError(f"closeout authority disposition drifted: {role}")
    failure = _binding(value["embedded_failure"], f"{role} failure")
    chain: dict[str, Any] = {
        "closeout": bindings[role],
        "closeout_review": bindings[spec["review_role"]],
        "embedded_failure": failure,
        "holdout_identity_sha256": value["holdout_identity_sha256"],
    }
    if "embedded_failure_review_payload_file" in spec:
        chain["embedded_failure_review"] = _binding(
            value["embedded_failure_review"], f"{role} failure review"
        )
    if value["chain_id_sha256"] != canonical_sha256(chain):
        raise ValueError(f"closeout authority chain SHA drifted: {role}")


def _verify_crosslinks(
    bindings: Mapping[str, Mapping[str, str]],
    payloads: Mapping[str, Mapping[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    rows_by_role = {row["role"]: row for row in rows}
    for role, spec in ROLE_SPECS.items():
        review_role = spec.get("review_role")
        if review_role is not None:
            review = payloads[review_role]
            root_field = spec.get(
                "reviewed_root_field", "reviewed_root_sha256"
            )
            path_field = spec.get("reviewed_path_field", "reviewed_artifact")
            if review.get(root_field) != bindings[role]["root_sha256"]:
                raise ValueError(f"independent review root drifted: {role}")
            reviewed_artifact = review.get(path_field)
            if (
                reviewed_artifact is not None
                and reviewed_artifact != bindings[role]["path"]
            ):
                raise ValueError(f"independent review path drifted: {role}")
    raw_role = "calibration_raw"
    raw = bindings[raw_role]
    recovery = payloads["calibration_recovery"]
    recovery_review = payloads["calibration_recovery_review"]
    if (
        recovery.get("original_execution_artifact") != raw["path"]
        or recovery.get("original_execution_root_sha256")
        != raw["root_sha256"]
        or type(recovery.get("original_execution_run_exit")) is not int
        or recovery.get("original_execution_run_exit") != 1
        or recovery_review.get("original_execution_artifact") != raw["path"]
        or recovery_review.get("original_execution_root_sha256")
        != raw["root_sha256"]
        or type(recovery_review.get("original_execution_run_exit")) is not int
        or recovery_review.get("original_execution_run_exit") != 1
        or recovery_review.get("reviewed_recovery_artifact")
        != bindings["calibration_recovery"]["path"]
        or recovery_review.get("reviewed_recovery_root_sha256")
        != bindings["calibration_recovery"]["root_sha256"]
    ):
        raise ValueError("calibration recovery authority chain drifted")
    for role in ("b2_consumed_failure", "b3_terminal_closeout"):
        _verify_closeout(
            role,
            ROLE_SPECS[role],
            bindings,
            payloads,
            rows_by_role[role]["authority_disposition"],
        )


def _verify_closeout(
    role: str,
    spec: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, str]],
    payloads: Mapping[str, Mapping[str, Any]],
    disposition: Mapping[str, Any],
) -> None:
    failure = disposition["embedded_failure"]
    failure_path = Path(failure["path"])
    verify_complete_seal(
        failure_path,
        failure["root_sha256"],
        label=f"{role} embedded failure",
    )
    _require_run_exit(
        failure_path, spec["failure_run_exit"], f"{role} embedded failure"
    )
    failure_payload = _authority_object(
        failure_path / spec["failure_payload_file"],
        byte_policy="camp_canonical",
    )
    if (
        failure_payload.get("schema_version")
        != spec["failure_schema_version"]
        or failure_payload.get("status") != spec["failure_status"]
    ):
        raise ValueError(f"{role} embedded failure terminal drifted")
    closeout_review = payloads[spec["review_role"]]
    if (
        closeout_review.get("reviewed_root_sha256")
        != bindings[role]["root_sha256"]
        or closeout_review.get("holdout_identity_sha256")
        != disposition["holdout_identity_sha256"]
    ):
        raise ValueError(f"{role} closeout review crosslink drifted")
    if "embedded_failure_review_payload_file" in spec:
        failure_review = disposition["embedded_failure_review"]
        review_path = Path(failure_review["path"])
        verify_complete_seal(
            review_path,
            failure_review["root_sha256"],
            label=f"{role} embedded failure review",
        )
        _require_run_exit(
            review_path,
            spec["embedded_failure_review_run_exit"],
            f"{role} embedded failure review",
        )
        review_payload = _authority_object(
            review_path / spec["embedded_failure_review_payload_file"],
            byte_policy="camp_canonical",
        )
        if (
            review_payload.get("schema_version")
            != spec["embedded_failure_review_schema_version"]
            or review_payload.get("status")
            != spec["embedded_failure_review_status"]
            or review_payload.get("reviewed_root_sha256")
            != failure["root_sha256"]
            or review_payload.get("holdout_identity_sha256")
            != disposition["holdout_identity_sha256"]
        ):
            raise ValueError(f"{role} embedded failure review drifted")


def _require_payload(
    payload: Mapping[str, Any], spec: Mapping[str, Any], role: str
) -> None:
    if (
        payload.get("schema_version") != spec["schema_version"]
        or payload.get("status") != spec["status"]
    ):
        raise ValueError(f"upstream authority payload drifted: {role}")


def _require_run_exit(path: Path, expected: int, label: str) -> None:
    if type(expected) is not int or (path / "run.exit").read_bytes() != (
        f"{expected}\n".encode("ascii")
    ):
        raise ValueError(f"upstream native-int run.exit drifted: {label}")


def _authority_object(path: Path, *, byte_policy: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=_no_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(token)
        ),
    )
    if type(value) is not dict:
        raise ValueError(f"authority JSON object expected: {path}")
    _require_finite(value, path=path)
    if byte_policy == "camp_canonical":
        if raw != canonical_json_bytes(value):
            raise ValueError(f"authority JSON is not canonical: {path}")
    elif byte_policy != "strict_sealed_legacy":
        raise ValueError(f"unknown authority JSON byte policy: {path}")
    return value


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_finite(value: Any, *, path: Path) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"nonfinite authority JSON value: {path}")
    if type(value) is list:
        for item in value:
            _require_finite(item, path=path)
    elif type(value) is dict:
        for item in value.values():
            _require_finite(item, path=path)


def _binding(value: Any, label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"{label} binding drifted")
    path = Path(value["path"])
    if (
        type(value["path"]) is not str
        or not path.is_absolute()
        or str(path.resolve()) != value["path"]
        or type(value["root_sha256"]) is not str
        or len(value["root_sha256"]) != 64
    ):
        raise ValueError(f"{label} binding invalid")
    return dict(value)


def _holdout_identity(payload: Mapping[str, Any], role: str) -> str:
    value = payload.get("holdout_identity_sha256")
    if value is None and type(payload.get("holdout_identity")) is dict:
        value = payload["holdout_identity"].get("holdout_identity_sha256")
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{role} holdout identity drifted")
    return value
