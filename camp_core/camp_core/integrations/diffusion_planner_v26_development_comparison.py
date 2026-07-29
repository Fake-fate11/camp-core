"""V26-native adapted 14D development-comparison contracts.

This module is deliberately limited to source-authoritative development
identities and CAMP adaptation-layer runtime assets.  It does not import a
V25 runner, validator, evaluation/summarizer, or SafetyCost consumer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_camp_context_math import (
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    CAMPContextScaler,
    context_weights,
    validate_column_simplex_theta,
)
from .diffusion_planner_v26_development_comparison_inventory import (
    comparison_composite_identity,
    validate_development_comparison_inventory,
)
from .diffusion_planner_v26_integration_boundary import (
    FROZEN_SIMPLEX_TOLERANCE,
    V25_ZERO_SHOT_REFERENCE_READ_ONLY,
    V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
    V26_FUTURE_EFFECT_SCHEMA,
    V26_LEGACY_SAFETYCOST_ROLE,
    V26_GENERATOR_ID,
    v26_generator_topology,
)


COMPARISON_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_development_comparison_manifest_v1"
COMPARISON_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_development_comparison_receipt_v1"
COMPARISON_EVIDENCE_ROLE = "development_nonholdout_adapted_14d_comparison"
ADAPTED_RUNTIME_SCHEMA_VERSION = "camp_dp_v26_adapted_selector_runtime_v1"
ADAPTED_SCENE14D_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_adapted_scene14d_weight_receipt_v1"

CANDIDATE0_ARM = "candidate0_row0"
STATIC14D_ARM = "CAMP-Static14D-adapted"
SCENE14D_ARM = "CAMP-Scene14D-adapted"
COMPARISON_ARMS = (CANDIDATE0_ARM, STATIC14D_ARM, SCENE14D_ARM)
RUNTIME_ARM_BY_COMPARISON_ARM = {
    CANDIDATE0_ARM: "pool_matched_candidate0",
    STATIC14D_ARM: "Static14D",
    SCENE14D_ARM: "Scene14D",
}

_SHA_CHARS = frozenset("0123456789abcdef")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _require_commit(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 40 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a full commit")
    return value


def _exact_mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label} field set drifted")
    return dict(value)


def _theta_sha256(value: np.ndarray) -> str:
    """Reproduce the adaptation producer's compact parameter fingerprint."""

    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(item) for item in array.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def _context_scaler_sha256(scaler: CAMPContextScaler) -> str:
    return canonical_json_sha256(
        {
            "q05": scaler.q05.tolist(),
            "q95": scaler.q95.tolist(),
            "raw_feature_names": list(RAW_FEATURE_NAMES),
        }
    )


def _require_scalar_string(archive: Any, key: str, label: str) -> str:
    if key not in archive.files:
        raise ValueError(f"{label} is missing")
    value = np.asarray(archive[key])
    if value.shape != () or not isinstance(value.item(), str):
        raise ValueError(f"{label} must be a scalar string")
    return str(value.item())


def _require_numeric(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or array.dtype.kind not in "fiu" or array.dtype.kind == "b":
        raise ValueError(f"{label} shape or dtype drifted")
    result = np.asarray(array, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite")
    return result.copy()


def _safe_asset_path(root: Path, item: Mapping[str, Any], label: str) -> Path:
    row = dict(item)
    if set(row) != {"relative_path", "sha256"}:
        raise ValueError(f"V26 adapted {label} asset schema drifted")
    relative = Path(str(row["relative_path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"V26 adapted {label} asset path is unsafe")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"V26 adapted {label} asset escaped its receipt root") from exc
    expected = _require_sha256(row["sha256"], f"V26 adapted {label} SHA")
    if not path.is_file() or _sha256_file(path) != expected:
        raise ValueError(f"V26 adapted {label} asset SHA drifted")
    return path


@dataclass(frozen=True)
class V26AdaptedSelectorAssets:
    """Read-only b32 CAMP adaptation assets for the V26 native callback."""

    receipt_path: Path
    adaptation_receipt_sha256: str
    asset_manifest_sha256: str
    fixed_dp_head: str
    atom_scales: np.ndarray
    static14d_weights: np.ndarray
    scene14d_theta: np.ndarray
    context_scaler: CAMPContextScaler
    atom_scales_sha256: str
    static14d_weights_sha256: str
    scene14d_theta_sha256: str
    context_scaler_sha256: str
    reference_manifest_sha256: str

    def scene14d_weights(self, context_payload: Mapping[str, Any]) -> dict[str, Any]:
        context = dict(context_payload)
        if set(context) != {
            "schema_version",
            "raw_context",
            "source_complete",
            "source_receipt",
        }:
            raise ValueError("V26 adapted Scene14D context schema drifted")
        if type(context["raw_context"]) is not dict or type(context["source_complete"]) is not dict:
            raise ValueError("V26 adapted Scene14D context payload is invalid")
        if set(context["raw_context"]) != set(RAW_FEATURE_NAMES) or set(
            context["source_complete"]
        ) != set(RAW_FEATURE_NAMES):
            raise ValueError("V26 adapted Scene14D context fields drifted")
        raw = np.asarray(
            [context["raw_context"][name] for name in RAW_FEATURE_NAMES], dtype=np.float64
        )
        source = np.asarray(
            [context["source_complete"][name] for name in RAW_FEATURE_NAMES], dtype=np.bool_
        )
        if not np.all(np.isfinite(raw)):
            raise ValueError("V26 adapted Scene14D context is nonfinite")
        phi = self.context_scaler.lift(raw, source_complete=source)
        weights = np.asarray(context_weights(self.scene14d_theta, phi), dtype=np.float64)
        if (
            weights.shape != (14,)
            or not np.all(np.isfinite(weights))
            or np.any(weights < -FROZEN_SIMPLEX_TOLERANCE)
            or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=FROZEN_SIMPLEX_TOLERANCE)
        ):
            raise ValueError("V26 adapted Scene14D runtime simplex drifted")
        return {
            "schema_version": ADAPTED_SCENE14D_RECEIPT_SCHEMA_VERSION,
            "weights": weights.tolist(),
            "weights_sha256": canonical_json_sha256({"weights": weights.tolist()}),
            "theta_sha256": self.scene14d_theta_sha256,
            "context_scaler_sha256": self.context_scaler_sha256,
            "adaptation_receipt_sha256": self.adaptation_receipt_sha256,
            "runtime_projection": False,
            "softmax": False,
        }


def load_v26_adapted_selector_assets(receipt_path: Path) -> V26AdaptedSelectorAssets:
    """Load V26 fit assets directly; V25 compatibility directories are not inputs."""

    receipt_path = Path(receipt_path).resolve()
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)
    root = receipt_path.parent
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if type(receipt) is not dict:
        raise ValueError("V26 adaptation receipt must be an object")
    if (
        receipt.get("schema_version") != "camp_dp_v26_selector_adaptation_receipt_v1"
        or receipt.get("evidence_role") != "development_train_only_selector_adaptation"
        or receipt.get("terminal", {}).get("status") != "complete"
        or receipt.get("weight_roles")
        != {
            "reference": V25_ZERO_SHOT_REFERENCE_READ_ONLY,
            "adapted": V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
        }
    ):
        raise ValueError("V26 adapted selector receipt identity drifted")
    manifest = dict(receipt.get("manifest", {}))
    frozen_dp = dict(manifest.get("frozen_dp", {}))
    if (
        manifest.get("adaptation_scope") != "camp_selector_adaptation_layer_only"
        or type(frozen_dp.get("head")) is not str
        or manifest.get("training_label_contract") != "causal_policy_distillation_no_outcome"
    ):
        raise ValueError("V26 adapted selector scope drifted")
    reference = dict(manifest.get("reference", {}))
    if reference.get("compatibility_role") != V25_ZERO_SHOT_REFERENCE_READ_ONLY:
        raise ValueError("V26 adapted selector reference role drifted")
    assets = receipt.get("adapted_assets")
    if type(assets) is not dict or set(assets) != {
        "parameters",
        "model_reports",
        "runtime_atom_scales",
        "static14d_runtime_weights",
    }:
        raise ValueError("V26 adapted selector asset manifest is incomplete")
    parameter_path = _safe_asset_path(root, assets["parameters"], "parameters")
    report_path = _safe_asset_path(root, assets["model_reports"], "model reports")
    scales_path = _safe_asset_path(root, assets["runtime_atom_scales"], "atom scales")
    static_path = _safe_asset_path(root, assets["static14d_runtime_weights"], "Static14D")
    with np.load(parameter_path, allow_pickle=False) as archive:
        if _require_scalar_string(archive, "schema_version", "V26 adapted parameter schema") != (
            V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
        ):
            raise ValueError("V26 adapted parameter schema drifted")
        names = np.asarray(archive["context_feature_names"])
        if names.tolist() != list(RAW_FEATURE_NAMES):
            raise ValueError("V26 adapted context feature ordering drifted")
        q05 = _require_numeric(archive["context_q05"], (RAW_FEATURE_COUNT,), "V26 adapted q05")
        q95 = _require_numeric(archive["context_q95"], (RAW_FEATURE_COUNT,), "V26 adapted q95")
        if np.any(q95 <= q05):
            raise ValueError("V26 adapted context scaler span drifted")
        atom_scales = _require_numeric(
            archive["training_scales_14d"], (14,), "V26 adapted training scales"
        )
        if np.any(atom_scales <= 0.0):
            raise ValueError("V26 adapted training scales must be positive")
        static_theta = validate_column_simplex_theta(
            _require_numeric(archive["static14d_theta"], (14, PHI_DIMENSION), "V26 adapted Static14D theta"),
            num_atoms=14,
            atol=FROZEN_SIMPLEX_TOLERANCE,
        )
        scene_theta = validate_column_simplex_theta(
            _require_numeric(archive["scene14d_theta"], (14, PHI_DIMENSION), "V26 adapted Scene14D theta"),
            num_atoms=14,
            atol=FROZEN_SIMPLEX_TOLERANCE,
        )
        archived_static = _require_numeric(
            archive["static14d_runtime_weights"], (14,), "V26 adapted archived Static14D weights"
        )
    static_weights = _require_numeric(
        np.load(static_path, allow_pickle=False), (14,), "V26 adapted Static14D weights"
    )
    if (
        not np.array_equal(static_weights, static_theta[:, 0])
        or not np.array_equal(static_weights, archived_static)
    ):
        raise ValueError("V26 adapted Static14D runtime weights drifted from theta")
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    if type(reports) is not dict:
        raise ValueError("V26 adapted model reports must be an object")
    for name, theta, mode in (
        ("CAMP-Static14D", static_theta, "static"),
        ("CAMP-Scene14D", scene_theta, "scene"),
    ):
        report = reports.get(name)
        if (
            type(report) is not dict
            or report.get("mode") != mode
            or report.get("active_atom_indices") != list(range(14))
            or report.get("theta_sha256") != _theta_sha256(theta)
            or report.get("outcome_or_fresh_consumed") is not False
        ):
            raise ValueError(f"V26 adapted {name} report drifted")
    scales = json.loads(scales_path.read_text(encoding="utf-8"))
    if (
        type(scales) is not dict
        or scales.get("schema_version") != "camp_dp_v26_adapted_runtime_atom_scales_v1"
        or scales.get("atom_count") != 14
        or scales.get("scale_source") != "reviewed_training_only_saved_pools"
        or scales.get("outcome_or_fresh_consumed") is not False
        or not np.array_equal(
            _require_numeric(scales.get("scales"), (14,), "V26 adapted scale receipt"), atom_scales
        )
    ):
        raise ValueError("V26 adapted runtime atom scale receipt drifted")
    scaler = CAMPContextScaler(q05=q05, q95=q95)
    asset_manifest = {
        key: {"relative_path": str(value["relative_path"]), "sha256": str(value["sha256"])}
        for key, value in sorted(assets.items())
    }
    return V26AdaptedSelectorAssets(
        receipt_path=receipt_path,
        adaptation_receipt_sha256=_sha256_file(receipt_path),
        asset_manifest_sha256=canonical_json_sha256(asset_manifest),
        fixed_dp_head=str(frozen_dp["head"]),
        atom_scales=atom_scales.copy(),
        static14d_weights=static_weights.copy(),
        scene14d_theta=scene_theta.copy(),
        context_scaler=scaler,
        atom_scales_sha256=_sha256_file(scales_path),
        static14d_weights_sha256=_sha256_file(static_path),
        scene14d_theta_sha256=_theta_sha256(scene_theta),
        context_scaler_sha256=_context_scaler_sha256(scaler),
        reference_manifest_sha256=canonical_json_sha256(reference),
    )


def _scenario_seed(*, inventory_sha256: str, cluster: Mapping[str, Any], arm_id: str) -> int:
    value = canonical_json_sha256(
        {
            "inventory_sha256": inventory_sha256,
            "composite_identity": list(comparison_composite_identity(cluster)),
            "arm_id": arm_id,
            "derivation": "identity_only_v26_development_comparison_state_v1",
        }
    )
    return int(value[:15], 16) % (2**31)


def build_development_comparison_manifest(
    *,
    inventory: Mapping[str, Any],
    inventory_file_sha256: str,
    camp_head: str,
    base_probe: Mapping[str, Any],
    adapted_assets: V26AdaptedSelectorAssets,
) -> dict[str, Any]:
    """Freeze all route-cluster and per-arm states before model initialization."""

    source = validate_development_comparison_inventory(inventory)
    inventory_file_sha256 = _require_sha256(
        inventory_file_sha256, "V26 comparison inventory file"
    )
    camp_head = _require_commit(camp_head, "V26 comparison CAMP head")
    if source["camp_head"] != camp_head:
        raise ValueError("V26 comparison inventory CAMP head drifted")
    if adapted_assets.fixed_dp_head != source["fixed_dp"]["head"]:
        raise ValueError("V26 adapted selector fixed-DP head drifted")
    source_adapted = dict(source["selectors"].get("adapted", {}))
    if (
        source_adapted.get("artifact_role") != V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
        or source_adapted.get("adaptation_receipt_sha256")
        != adapted_assets.adaptation_receipt_sha256
    ):
        raise ValueError("V26 comparison inventory adapted asset binding drifted")
    source_assets = source_adapted.get("assets")
    if type(source_assets) is not dict or canonical_json_sha256(
        {
            key: {
                "relative_path": str(item["relative_path"]),
                "sha256": str(item["sha256"]),
            }
            for key, item in sorted(source_assets.items())
        }
    ) != adapted_assets.asset_manifest_sha256:
        raise ValueError("V26 comparison inventory adapted asset manifest drifted")
    base = dict(base_probe)
    if set(base) != {"source_path", "source_sha256", "fixed_dp", "spawn_config", "seed_template"}:
        raise ValueError("V26 comparison base probe schema drifted")
    _require_sha256(base["source_sha256"], "V26 comparison base probe")
    fixed_dp = dict(base["fixed_dp"])
    if set(fixed_dp) != {"head", "checkpoint", "args_json", "native_source_sha256"}:
        raise ValueError("V26 comparison fixed-DP base probe drifted")
    if fixed_dp["head"] != source["fixed_dp"]["head"]:
        raise ValueError("V26 comparison fixed-DP head drifted")
    if fixed_dp["checkpoint"] != source["fixed_dp"]["checkpoint"]:
        raise ValueError("V26 comparison fixed-DP checkpoint drifted")
    if type(base["spawn_config"]) is not dict or type(base["seed_template"]) is not dict:
        raise ValueError("V26 comparison spawn/seed base drifted")
    clusters = []
    units = []
    for cluster_index, source_cluster in enumerate(source["selected_clusters"]):
        cluster = dict(source_cluster)
        composite = comparison_composite_identity(cluster)
        cluster_id = canonical_json_sha256(
            {
                "inventory_sha256": source["inventory_sha256"],
                "cluster_index": cluster_index,
                "composite_identity": list(composite),
            }
        )
        clusters.append(
            {
                "cluster_index": cluster_index,
                "cluster_id_sha256": cluster_id,
                "route": cluster,
            }
        )
        for arm_id in COMPARISON_ARMS:
            seed = _scenario_seed(
                inventory_sha256=source["inventory_sha256"], cluster=cluster, arm_id=arm_id
            )
            state_id = canonical_json_sha256(
                {
                    "cluster_id_sha256": cluster_id,
                    "arm_id": arm_id,
                    "scenario_seed": seed,
                    "spawn_config": base["spawn_config"],
                    "state_topology": "own_reset_state_one_same_ego_b8_forward",
                }
            )
            units.append(
                {
                    "unit_index": len(units),
                    "cluster_index": cluster_index,
                    "cluster_id_sha256": cluster_id,
                    "arm_id": arm_id,
                    "runtime_operational_arm": RUNTIME_ARM_BY_COMPARISON_ARM[arm_id],
                    "scenario_seed": seed,
                    "planned_state_id_sha256": state_id,
                }
            )
    value = {
        "schema_version": COMPARISON_MANIFEST_SCHEMA_VERSION,
        "evidence_role": COMPARISON_EVIDENCE_ROLE,
        "status": "frozen_pre_model_no_outcome_execution_plan",
        "camp_head": camp_head,
        "inventory": {
            "path_role": "source_authoritative_development_inventory",
            "file_sha256": inventory_file_sha256,
            "inventory_sha256": source["inventory_sha256"],
            "input_bindings": dict(source["input_bindings"]),
        },
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed_before_freeze": [],
        "fixed_dp": fixed_dp,
        "base_probe": {
            "source_path": base["source_path"],
            "source_sha256": base["source_sha256"],
            "spawn_config": dict(base["spawn_config"]),
            "seed_template": dict(base["seed_template"]),
        },
        "generator_id": V26_GENERATOR_ID,
        "generator_topology": v26_generator_topology(),
        "arms": list(COMPARISON_ARMS),
        "execution_topology": {
            "cluster_independent_n": True,
            "arm_state": "each_arm_own_reset_state_compute_matched",
            "pool": "one_same_ego_b8_forward_per_arm_state",
            "candidate0": "frozen_row0_default_output",
            "selector_scope": "only_current_arm_same_pool",
            "cross_arm_pool_equality_claim": False,
            "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
        },
        "adapted_selector": {
            "artifact_role": V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
            "runtime_schema_version": ADAPTED_RUNTIME_SCHEMA_VERSION,
            "adaptation_receipt_sha256": adapted_assets.adaptation_receipt_sha256,
            "asset_manifest_sha256": adapted_assets.asset_manifest_sha256,
            "fixed_dp_head": adapted_assets.fixed_dp_head,
            "atom_scales_sha256": adapted_assets.atom_scales_sha256,
            "static14d_weights_sha256": adapted_assets.static14d_weights_sha256,
            "scene14d_theta_sha256": adapted_assets.scene14d_theta_sha256,
            "context_scaler_sha256": adapted_assets.context_scaler_sha256,
            "reference_manifest_sha256": adapted_assets.reference_manifest_sha256,
        },
        "endpoint_contract": {
            "schema_version": V26_FUTURE_EFFECT_SCHEMA,
            "domains": [
                "safety",
                "operation_progress",
                "planar_dynamics_filtered_body_frame_smoothness_proxy",
                "realtime",
            ],
            "weighted_total_score": False,
            "legacy_safetycost_role": V26_LEGACY_SAFETYCOST_ROLE,
        },
        "clusters": clusters,
        "unit_plan": units,
        "denominator": {
            "planned_clusters": len(clusters),
            "planned_arm_units": len(units),
            "complete_arm_units": 0,
            "typed_failure_arm_units": 0,
            "unattempted_arm_units": len(units),
        },
        "claim_scope": (
            "development comparison capability only; no effect, safety benefit, OOD, "
            "stability, holdout, six-family, or unseen-family generalization conclusion"
        ),
        "manifest_sha256": "",
    }
    value["manifest_sha256"] = canonical_json_sha256(
        {key: item for key, item in value.items() if key != "manifest_sha256"}
    )
    return validate_development_comparison_manifest(value)


def validate_development_comparison_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    expected = {
        "schema_version", "evidence_role", "status", "camp_head", "inventory", "split",
        "holdout_accessed", "outcome_fields_consumed_before_freeze", "fixed_dp", "base_probe",
        "generator_id", "generator_topology", "arms", "execution_topology", "adapted_selector",
        "endpoint_contract", "clusters", "unit_plan", "denominator", "claim_scope", "manifest_sha256",
    }
    if set(result) != expected:
        raise ValueError("V26 comparison manifest field set drifted")
    if (
        result["schema_version"] != COMPARISON_MANIFEST_SCHEMA_VERSION
        or result["evidence_role"] != COMPARISON_EVIDENCE_ROLE
        or result["status"] != "frozen_pre_model_no_outcome_execution_plan"
        or result["split"] != "development_nonholdout"
        or result["holdout_accessed"] is not False
        or result["outcome_fields_consumed_before_freeze"] != []
        or result["generator_id"] != V26_GENERATOR_ID
        or result["generator_topology"] != v26_generator_topology()
        or result["arms"] != list(COMPARISON_ARMS)
    ):
        raise ValueError("V26 comparison manifest identity drifted")
    _require_commit(result["camp_head"], "V26 comparison CAMP head")
    inventory = _exact_mapping(
        result["inventory"],
        {"path_role", "file_sha256", "inventory_sha256", "input_bindings"},
        "V26 comparison inventory binding",
    )
    if inventory["path_role"] != "source_authoritative_development_inventory":
        raise ValueError("V26 comparison inventory role drifted")
    _require_sha256(inventory["file_sha256"], "V26 comparison inventory file")
    _require_sha256(inventory["inventory_sha256"], "V26 comparison inventory identity")
    bindings = _exact_mapping(
        inventory["input_bindings"],
        {"final_training_population_sha256", "revision_plan_sha256"},
        "V26 comparison input bindings",
    )
    for key, item in bindings.items():
        bindings[key] = _require_sha256(item, f"V26 comparison {key}")
    inventory["input_bindings"] = bindings
    result["inventory"] = inventory
    fixed_dp = dict(result["fixed_dp"])
    if set(fixed_dp) != {"head", "checkpoint", "args_json", "native_source_sha256"}:
        raise ValueError("V26 comparison fixed-DP binding drifted")
    _require_commit(fixed_dp["head"], "V26 comparison fixed-DP head")
    for key in ("checkpoint", "args_json"):
        item = _exact_mapping(fixed_dp[key], {"path", "sha256"}, f"V26 comparison {key}")
        if type(item["path"]) is not str or not item["path"]:
            raise ValueError(f"V26 comparison {key} path is required")
        item["sha256"] = _require_sha256(item["sha256"], f"V26 comparison {key} SHA")
        fixed_dp[key] = item
    if type(fixed_dp["native_source_sha256"]) is not dict or not fixed_dp["native_source_sha256"]:
        raise ValueError("V26 comparison fixed-DP source hash binding is required")
    result["fixed_dp"] = fixed_dp
    topology = _exact_mapping(
        result["execution_topology"],
        {
            "cluster_independent_n", "arm_state", "pool", "candidate0", "selector_scope",
            "cross_arm_pool_equality_claim", "post_pool_model_dp_latent_generation_mutation_regeneration",
        },
        "V26 comparison topology",
    )
    if topology != {
        "cluster_independent_n": True,
        "arm_state": "each_arm_own_reset_state_compute_matched",
        "pool": "one_same_ego_b8_forward_per_arm_state",
        "candidate0": "frozen_row0_default_output",
        "selector_scope": "only_current_arm_same_pool",
        "cross_arm_pool_equality_claim": False,
        "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
    }:
        raise ValueError("V26 comparison topology drifted")
    adapted = _exact_mapping(
        result["adapted_selector"],
        {
            "artifact_role", "runtime_schema_version", "adaptation_receipt_sha256",
            "asset_manifest_sha256", "atom_scales_sha256", "static14d_weights_sha256",
            "scene14d_theta_sha256", "context_scaler_sha256", "reference_manifest_sha256",
            "fixed_dp_head",
        },
        "V26 comparison adapted selector",
    )
    if (
        adapted["artifact_role"] != V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
        or adapted["runtime_schema_version"] != ADAPTED_RUNTIME_SCHEMA_VERSION
    ):
        raise ValueError("V26 comparison adapted selector role drifted")
    for key, item in adapted.items():
        if key not in {"artifact_role", "runtime_schema_version", "fixed_dp_head"}:
            adapted[key] = _require_sha256(item, f"V26 comparison {key}")
    adapted["fixed_dp_head"] = _require_commit(
        adapted["fixed_dp_head"], "V26 comparison adapted fixed-DP head"
    )
    if adapted["fixed_dp_head"] != fixed_dp["head"]:
        raise ValueError("V26 comparison adapted/fixed-DP identity drifted")
    result["adapted_selector"] = adapted
    endpoint = dict(result["endpoint_contract"])
    if (
        endpoint.get("schema_version") != V26_FUTURE_EFFECT_SCHEMA
        or endpoint.get("domains")
        != [
            "safety", "operation_progress", "planar_dynamics_filtered_body_frame_smoothness_proxy", "realtime",
        ]
        or endpoint.get("weighted_total_score") is not False
        or endpoint.get("legacy_safetycost_role") != V26_LEGACY_SAFETYCOST_ROLE
    ):
        raise ValueError("V26 comparison endpoint contract drifted")
    clusters = result["clusters"]
    units = result["unit_plan"]
    if type(clusters) is not list or not clusters or type(units) is not list:
        raise ValueError("V26 comparison frozen plan is empty")
    seen_cluster_ids: set[str] = set()
    for index, row_value in enumerate(clusters):
        row = _exact_mapping(row_value, {"cluster_index", "cluster_id_sha256", "route"}, "V26 comparison cluster")
        if row["cluster_index"] != index:
            raise ValueError("V26 comparison cluster order drifted")
        row["cluster_id_sha256"] = _require_sha256(row["cluster_id_sha256"], "V26 cluster identity")
        if row["cluster_id_sha256"] in seen_cluster_ids:
            raise ValueError("V26 comparison cluster identity duplicated")
        seen_cluster_ids.add(row["cluster_id_sha256"])
        comparison_composite_identity(row["route"])
    if len(units) != len(clusters) * len(COMPARISON_ARMS):
        raise ValueError("V26 comparison arm-unit denominator drifted")
    seen_units: set[str] = set()
    for index, row_value in enumerate(units):
        row = _exact_mapping(
            row_value,
            {
                "unit_index", "cluster_index", "cluster_id_sha256", "arm_id",
                "runtime_operational_arm", "scenario_seed", "planned_state_id_sha256",
            },
            "V26 comparison arm unit",
        )
        if (
            row["unit_index"] != index
            or row["cluster_index"] not in range(len(clusters))
            or row["cluster_id_sha256"] != clusters[row["cluster_index"]]["cluster_id_sha256"]
            or row["arm_id"] not in COMPARISON_ARMS
            or row["runtime_operational_arm"] != RUNTIME_ARM_BY_COMPARISON_ARM[row["arm_id"]]
            or type(row["scenario_seed"]) is not int
            or row["scenario_seed"] < 0
        ):
            raise ValueError("V26 comparison arm-unit identity drifted")
        state_id = _require_sha256(row["planned_state_id_sha256"], "V26 comparison state identity")
        if state_id in seen_units:
            raise ValueError("V26 comparison planned state duplicated")
        seen_units.add(state_id)
    expected_denominator = {
        "planned_clusters": len(clusters),
        "planned_arm_units": len(units),
        "complete_arm_units": 0,
        "typed_failure_arm_units": 0,
        "unattempted_arm_units": len(units),
    }
    if result["denominator"] != expected_denominator:
        raise ValueError("V26 comparison pre-model denominator drifted")
    expected_hash = canonical_json_sha256(
        {key: item for key, item in result.items() if key != "manifest_sha256"}
    )
    if result["manifest_sha256"] != expected_hash:
        raise ValueError("V26 comparison manifest hash drifted")
    return result


def industrial_v3_endpoint_vector(*, planning_latency_ms: float | None) -> dict[str, Any]:
    """Represent unavailable future effects honestly while retaining latency."""

    latency = None if planning_latency_ms is None else float(planning_latency_ms)
    if latency is not None and (not math.isfinite(latency) or latency < 0.0):
        raise ValueError("V26 comparison planning latency is invalid")
    missing = {
        "status": "typed_missing",
        "reason": "one_state_development_comparison_has_no_formal_future_effect_adapter",
    }
    return {
        "schema_version": V26_FUTURE_EFFECT_SCHEMA,
        "domains": {
            "safety": dict(missing),
            "operation_progress": dict(missing),
            "planar_dynamics_filtered_body_frame_smoothness_proxy": dict(missing),
            "realtime": (
                dict(missing)
                if latency is None
                else {"status": "observed_planning_latency", "planning_latency_ms": latency}
            ),
        },
        "weighted_total_score": None,
        "legacy_safetycost": {
            "role": V26_LEGACY_SAFETYCOST_ROLE,
            "consumed": False,
            "value": None,
        },
    }


def validate_industrial_v3_endpoint_vector(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _exact_mapping(
        value,
        {"schema_version", "domains", "weighted_total_score", "legacy_safetycost"},
        "V26 comparison industrial-v3 endpoint",
    )
    if result["schema_version"] != V26_FUTURE_EFFECT_SCHEMA or result["weighted_total_score"] is not None:
        raise ValueError("V26 comparison endpoint schema drifted")
    expected_domains = {
        "safety", "operation_progress", "planar_dynamics_filtered_body_frame_smoothness_proxy", "realtime",
    }
    domains = _exact_mapping(result["domains"], expected_domains, "V26 comparison endpoint domains")
    for name, row_value in domains.items():
        row = dict(row_value)
        if row.get("status") == "typed_missing":
            if set(row) != {"status", "reason"} or type(row["reason"]) is not str or not row["reason"]:
                raise ValueError(f"V26 comparison {name} typed-missing endpoint drifted")
        elif name == "realtime" and row.get("status") == "observed_planning_latency":
            if set(row) != {"status", "planning_latency_ms"}:
                raise ValueError("V26 comparison realtime endpoint fields drifted")
            latency = row["planning_latency_ms"]
            if type(latency) not in {int, float} or not math.isfinite(float(latency)) or latency < 0.0:
                raise ValueError("V26 comparison realtime latency drifted")
        else:
            raise ValueError(f"V26 comparison {name} endpoint status drifted")
    legacy = _exact_mapping(
        result["legacy_safetycost"], {"role", "consumed", "value"}, "V26 comparison legacy endpoint"
    )
    if legacy != {"role": V26_LEGACY_SAFETYCOST_ROLE, "consumed": False, "value": None}:
        raise ValueError("V26 comparison legacy endpoint role drifted")
    return result
