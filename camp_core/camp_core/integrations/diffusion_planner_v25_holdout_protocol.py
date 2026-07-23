from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_artifact_seal import verify_complete_seal
from .diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
    validate_preopen_authority,
)
from .diffusion_planner_v25_holdout_contract import (
    SCIENTIFIC_TERMINAL_STATUSES,
    canonical_sha256,
)
from .diffusion_planner_v25_scene_runtime import (
    load_v25_runtime_selector_assets,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_protocol_assets_receipt_v1"
PROTOCOL_ASSET_FIELDS = frozenset(
    {
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_contract_sha256",
        "threshold_contract_sha256",
        "noninferiority_contract_sha256",
        "multiplicity_contract_sha256",
        "claim_contract_sha256",
        "failure_contract_sha256",
    }
)


def derive_protocol_assets_from_accepted_preopen(
    *,
    preopen_artifact: Path,
    preopen_root_sha256: str,
    preopen_review_artifact: Path,
    preopen_review_root_sha256: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Derive every holdout protocol hash from the accepted sealed B2 chain."""

    authority, review_report = load_accepted_preopen_authority(
        preopen_artifact=preopen_artifact,
        preopen_root_sha256=preopen_root_sha256,
        preopen_review_artifact=preopen_review_artifact,
        preopen_review_root_sha256=preopen_review_root_sha256,
    )
    preopen = Path(preopen_artifact).resolve()
    review = Path(preopen_review_artifact).resolve()

    bindings = authority["upstream_bindings"]
    training = _binding(bindings, "training")
    training_review = _binding(bindings, "training_review")
    _verify_successful_artifact(
        Path(training["path"]),
        training["root_sha256"],
        label="accepted V25 training authority",
    )
    _verify_successful_artifact(
        Path(training_review["path"]),
        training_review["root_sha256"],
        label="accepted V25 training independent review",
    )
    runtime = load_v25_runtime_selector_assets(
        training_artifact=Path(training["path"]),
        training_root_sha256=training["root_sha256"],
        training_review_artifact=Path(training_review["path"]),
        training_review_root_sha256=training_review["root_sha256"],
    )
    evaluation = authority["evaluation"]
    atom_contract = {
        "schema_version": "camp_dp_v25_holdout_atom_contract_binding_v1",
        "critical_implementation_manifest_sha256": authority[
            "critical_implementation_manifest"
        ]["manifest_sha256"],
        "atom_mechanism": authority["atom_mechanism"],
        "primary_arms": evaluation["primary_arms"],
        "training_scale_sha256": runtime.atom_scales_sha256,
        "normalized_atom_transform": "clip(raw_atom/training_scale,0,10)",
        "candidate_k": 8,
        "candidate_tensor_modified": False,
    }
    threshold_contract = {
        "schema_version": "camp_dp_v25_holdout_threshold_contract_binding_v1",
        "primary": evaluation["primary"],
        "component_guardrails": evaluation["component_guardrails"],
    }
    claim_contract = {
        "schema_version": "camp_dp_v25_holdout_claim_contract_binding_v1",
        "coverage": evaluation["coverage"],
        "claim_requires_primary_component_and_all_ni_gates": evaluation[
            "claim_requires_primary_component_and_all_ni_gates"
        ],
        "claim_scope": evaluation["claim_scope"],
        "real_world_or_broad_map_claim_authorized": evaluation[
            "real_world_or_broad_map_claim_authorized"
        ],
        "promotion_or_deployment_authorized": evaluation[
            "promotion_or_deployment_authorized"
        ],
    }
    failure_contract = {
        "schema_version": "camp_dp_v25_holdout_failure_contract_binding_v1",
        "scientific_unit_statuses": list(SCIENTIFIC_TERMINAL_STATUSES),
        "artifact_integrity_failure_scope": (
            "artifact_fatal_not_scientific_row"
        ),
        "terminal_truth_table": (
            "exclusive_scientific_terminal_or_artifact_fatal_v1"
        ),
        "planned_denominator_retained": True,
        "complete_case_filtering": False,
    }
    assets = {
        "model_registry_sha256": _file_sha256(
            Path(training["path"]) / "model_registry.json"
        ),
        "training_scale_sha256": runtime.atom_scales_sha256,
        "context_scaler_sha256": (
            runtime.scene14d_weight_provider.context_scaler_sha256
        ),
        "atom_contract_sha256": canonical_sha256(atom_contract),
        "threshold_contract_sha256": canonical_sha256(threshold_contract),
        "noninferiority_contract_sha256": canonical_sha256(
            evaluation["noninferiority"]
        ),
        "multiplicity_contract_sha256": canonical_sha256(
            evaluation["paired_statistics"]
        ),
        "claim_contract_sha256": canonical_sha256(claim_contract),
        "failure_contract_sha256": canonical_sha256(failure_contract),
    }
    validate_protocol_assets(assets)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "derived_from_accepted_sealed_preopen_authority",
        "accepted_preopen": {
            "path": str(preopen),
            "root_sha256": preopen_root_sha256,
        },
        "accepted_preopen_review": {
            "path": str(review),
            "root_sha256": preopen_review_root_sha256,
        },
        "accepted_training": training,
        "accepted_training_review": training_review,
        "critical_implementation_manifest_sha256": authority[
            "critical_implementation_manifest"
        ]["manifest_sha256"],
        "atom_contract": atom_contract,
        "threshold_contract": threshold_contract,
        "noninferiority_contract": evaluation["noninferiority"],
        "multiplicity_contract": evaluation["paired_statistics"],
        "claim_contract": claim_contract,
        "failure_contract": failure_contract,
        "protocol_assets": assets,
        "fresh_b2_opened_while_deriving": False,
        "outcome_fields_consumed": [],
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return assets, receipt


def load_accepted_preopen_authority(
    *,
    preopen_artifact: Path,
    preopen_root_sha256: str,
    preopen_review_artifact: Path,
    preopen_review_root_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    preopen = Path(preopen_artifact).resolve()
    review = Path(preopen_review_artifact).resolve()
    _verify_successful_artifact(
        preopen,
        preopen_root_sha256,
        label="accepted Fresh B2 pre-open authority",
    )
    _verify_successful_artifact(
        review,
        preopen_review_root_sha256,
        label="accepted Fresh B2 pre-open independent review",
    )
    authority = validate_preopen_authority(
        _canonical_object(preopen / "preopen_authority.json")
    )
    review_report = _canonical_object(review / "report.json")
    if (
        authority["status"] != "passed_outcome_blind_fresh_b2_preopen_authority"
        or review_report.get("status")
        != "passed_independent_outcome_blind_fresh_b2_preopen_review"
        or review_report.get("reviewed_root_sha256") != preopen_root_sha256
        or authority["fresh_b2_opened"] is not False
        or authority["outcome_fields_consumed"] != []
    ):
        raise ValueError("accepted Fresh B2 pre-open chain drifted")
    return authority, review_report


def validate_protocol_assets(value: Mapping[str, Any]) -> dict[str, str]:
    if type(value) is not dict or set(value) != PROTOCOL_ASSET_FIELDS:
        raise ValueError("holdout protocol asset field set drifted")
    return {
        name: _require_sha(value[name], name)
        for name in sorted(PROTOCOL_ASSET_FIELDS)
    }


def validate_protocol_assets_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "accepted_preopen",
        "accepted_preopen_review",
        "accepted_training",
        "accepted_training_review",
        "critical_implementation_manifest_sha256",
        "atom_contract",
        "threshold_contract",
        "noninferiority_contract",
        "multiplicity_contract",
        "claim_contract",
        "failure_contract",
        "protocol_assets",
        "fresh_b2_opened_while_deriving",
        "outcome_fields_consumed",
        "receipt_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("holdout protocol asset receipt field set drifted")
    result = json.loads(canonical_json_bytes(value))
    if (
        result["schema_version"] != SCHEMA_VERSION
        or result["status"]
        != "derived_from_accepted_sealed_preopen_authority"
        or result["fresh_b2_opened_while_deriving"] is not False
        or result["outcome_fields_consumed"] != []
    ):
        raise ValueError("holdout protocol asset receipt value drifted")
    assets = validate_protocol_assets(result["protocol_assets"])
    expected = {
        "model_registry_sha256": _require_sha(
            assets["model_registry_sha256"], "model_registry_sha256"
        ),
        "training_scale_sha256": _require_sha(
            assets["training_scale_sha256"], "training_scale_sha256"
        ),
        "context_scaler_sha256": _require_sha(
            assets["context_scaler_sha256"], "context_scaler_sha256"
        ),
        "atom_contract_sha256": canonical_sha256(result["atom_contract"]),
        "threshold_contract_sha256": canonical_sha256(
            result["threshold_contract"]
        ),
        "noninferiority_contract_sha256": canonical_sha256(
            result["noninferiority_contract"]
        ),
        "multiplicity_contract_sha256": canonical_sha256(
            result["multiplicity_contract"]
        ),
        "claim_contract_sha256": canonical_sha256(result["claim_contract"]),
        "failure_contract_sha256": canonical_sha256(
            result["failure_contract"]
        ),
    }
    if assets != expected:
        raise ValueError("holdout protocol asset receipt hashes drifted")
    payload = dict(result)
    stored = payload.pop("receipt_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError("holdout protocol asset receipt SHA drifted")
    return result


def _verify_successful_artifact(
    path: Path, root_sha256: str, *, label: str
) -> None:
    root = Path(path).resolve()
    verify_complete_seal(root, root_sha256, label=label)
    if (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError(f"{label} did not exit successfully")


def _binding(
    bindings: Mapping[str, Any], name: str
) -> dict[str, str]:
    value = bindings.get(name)
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"accepted pre-open {name} binding drifted")
    path = value["path"]
    if type(path) is not str or not Path(path).is_absolute():
        raise ValueError(f"accepted pre-open {name} path drifted")
    return {
        "path": str(Path(path).resolve()),
        "root_sha256": _require_sha(value["root_sha256"], f"{name} root"),
    }


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
