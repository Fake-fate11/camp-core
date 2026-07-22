from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FRESH_B2_ARMS = ("candidate0", "static14d", "scene14d")
FRESH_B2_OPENING_RELEASE_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "fixed_dp_head",
        "implementation_source_head",
        "pointer_head_at_release",
        "controller_decision_root_sha256",
        "calibration_contract_root_sha256",
        "preopen_qualification_root_sha256",
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "scenario_manifest_root_sha256",
        "run_nonce",
        "authorized_output_dir",
        "paired_arms",
        "one_shot",
        "fresh_b2_open_authorized",
        "fresh_b2_opened",
        "outcome_fields_consumed",
        "promotion_deployment_activation_authorized",
    }
)
FRESH_B2_OPENING_CONSUMPTION_FIELDS = frozenset(
    {
        "schema_version",
        "release_root_sha256",
        "run_nonce",
        "authorized_output_dir",
        "marker_path",
        "marker_sha256",
        "consumed_before_outcome_capable_operation",
        "outcome_fields_consumed_before_nonce",
        "fresh_b2_opened_once",
        "second_consumption_allowed",
    }
)


def freeze_fresh_b2_opening_release(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    controller_decision_root_sha256: str,
    calibration_contract_root_sha256: str,
    preopen_qualification_root_sha256: str,
    model_registry_sha256: str,
    training_scale_sha256: str,
    context_scaler_sha256: str,
    scenario_manifest_root_sha256: str,
    run_nonce: str,
    authorized_output_dir: str,
) -> dict[str, Any]:
    """Freeze the external, one-time authority required to open Fresh B2.

    This function cannot create authority by itself: the controller decision
    must already exist as a sealed artifact and its root is bound verbatim.
    The production runner must additionally consume ``run_nonce`` atomically
    before any Fresh outcome-capable operation.
    """

    for name, value in {
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
    }.items():
        _require_git_head(value, name)
    for name, value in {
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "calibration_contract_root_sha256": calibration_contract_root_sha256,
        "preopen_qualification_root_sha256": preopen_qualification_root_sha256,
        "model_registry_sha256": model_registry_sha256,
        "training_scale_sha256": training_scale_sha256,
        "context_scaler_sha256": context_scaler_sha256,
        "scenario_manifest_root_sha256": scenario_manifest_root_sha256,
        "run_nonce": run_nonce,
    }.items():
        _require_sha(value, name)
    output = _canonical_output_dir(authorized_output_dir)
    return {
        "schema_version": "camp_dp_v25_fresh_b2_one_time_opening_release_v1",
        "status": "fresh_b2_one_time_opening_released",
        "fixed_dp_head": FIXED_DP_HEAD,
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "calibration_contract_root_sha256": calibration_contract_root_sha256,
        "preopen_qualification_root_sha256": preopen_qualification_root_sha256,
        "model_registry_sha256": model_registry_sha256,
        "training_scale_sha256": training_scale_sha256,
        "context_scaler_sha256": context_scaler_sha256,
        "scenario_manifest_root_sha256": scenario_manifest_root_sha256,
        "run_nonce": run_nonce,
        "authorized_output_dir": output,
        "paired_arms": list(FRESH_B2_ARMS),
        "one_shot": True,
        "fresh_b2_open_authorized": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "promotion_deployment_activation_authorized": False,
    }


def validate_fresh_b2_opening_release(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != FRESH_B2_OPENING_RELEASE_FIELDS:
        raise ValueError("Fresh B2 opening release field set drifted")
    try:
        expected = freeze_fresh_b2_opening_release(
            implementation_source_head=value["implementation_source_head"],
            pointer_head_at_release=value["pointer_head_at_release"],
            controller_decision_root_sha256=value["controller_decision_root_sha256"],
            calibration_contract_root_sha256=value["calibration_contract_root_sha256"],
            preopen_qualification_root_sha256=value["preopen_qualification_root_sha256"],
            model_registry_sha256=value["model_registry_sha256"],
            training_scale_sha256=value["training_scale_sha256"],
            context_scaler_sha256=value["context_scaler_sha256"],
            scenario_manifest_root_sha256=value["scenario_manifest_root_sha256"],
            run_nonce=value["run_nonce"],
            authorized_output_dir=value["authorized_output_dir"],
        )
    except (KeyError, TypeError) as exc:  # pragma: no cover - exact keyset guards this
        raise ValueError("Fresh B2 opening release structure drifted") from exc
    if not _strict_json_equal(value, expected):
        raise ValueError("Fresh B2 opening release exact value drifted")
    return expected


def freeze_fresh_b2_opening_consumption(
    *,
    opening_release: Mapping[str, Any],
    release_root_sha256: str,
    marker_sha256: str,
) -> dict[str, Any]:
    release = validate_fresh_b2_opening_release(opening_release)
    _require_sha(release_root_sha256, "release_root_sha256")
    _require_sha(marker_sha256, "marker_sha256")
    nonce = release["run_nonce"]
    return {
        "schema_version": "camp_dp_v25_fresh_b2_opening_consumption_v1",
        "release_root_sha256": release_root_sha256,
        "run_nonce": nonce,
        "authorized_output_dir": release["authorized_output_dir"],
        "marker_path": (
            "/root/autodl-tmp/.camp_dp_v25_fresh_b2_open_nonces/"
            f"v25_fresh_b2_{nonce}.consumed.json"
        ),
        "marker_sha256": marker_sha256,
        "consumed_before_outcome_capable_operation": True,
        "outcome_fields_consumed_before_nonce": [],
        "fresh_b2_opened_once": True,
        "second_consumption_allowed": False,
    }


def validate_fresh_b2_opening_consumption(
    value: Mapping[str, Any],
    *,
    opening_release: Mapping[str, Any],
    release_root_sha256: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != FRESH_B2_OPENING_CONSUMPTION_FIELDS:
        raise ValueError("Fresh B2 opening consumption field set drifted")
    try:
        expected = freeze_fresh_b2_opening_consumption(
            opening_release=opening_release,
            release_root_sha256=release_root_sha256,
            marker_sha256=value["marker_sha256"],
        )
    except (KeyError, TypeError) as exc:  # pragma: no cover - exact keyset guards this
        raise ValueError("Fresh B2 opening consumption structure drifted") from exc
    if not _strict_json_equal(value, expected):
        raise ValueError("Fresh B2 opening consumption exact value drifted")
    return expected


def _canonical_output_dir(value: Any) -> str:
    if type(value) is not str or not value.startswith("/root/autodl-tmp/"):
        raise ValueError("Fresh B2 authorized output must be an absolute AutoDL path")
    path = PurePosixPath(value)
    if (
        str(path) != value
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("Fresh B2 authorized output path is not canonical")
    return value


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _require_git_head(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a full lowercase 40-hex Git commit")
    return value


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
