"""Development-only V26 CAMP selector-adaptation contracts.

The module deliberately operates on reviewed, training-only saved B8 pools.
It never constructs or updates Diffusion Planner, its checkpoint, the
generator, or latent inputs.  The frozen zero-shot 9D/14D selectors are
read-only references; any fitted parameters are a CAMP adaptation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import statistics
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v25_context import (
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    V25ContextScaler,
    context_weights,
    validate_column_simplex_theta,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (
    FIXED_DP_HEAD,
    training_parameter_array_sha256,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (
    FROZEN_SIMPLEX_TOLERANCE,
    V25_ZERO_SHOT_REFERENCE_READ_ONLY,
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    v26_generator_topology,
)
if TYPE_CHECKING:
    from camp_core.integrations.diffusion_planner_v25_training import (
        V25TrainedSelector,
    )
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
    )


SAVED_POOL_DIAGNOSTIC_SCHEMA_VERSION = (
    "camp_dp_v26_saved_pool_selection_diagnostic_v1"
)
SAVED_POOL_DIAGNOSTIC_ROLE = (
    "development_train_only_saved_pool_selection_diagnostic"
)
ADAPTATION_CONFIG_SCHEMA_VERSION = "camp_dp_v26_selector_adaptation_config_v1"
ADAPTATION_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_selector_adaptation_receipt_v1"
ADAPTATION_ROLE = "development_train_only_selector_adaptation"
COMPARISON_PLAN_SCHEMA_VERSION = "camp_dp_v26_development_comparison_plan_v1"
COMPARISON_PLAN_ROLE = "development_nonholdout_zero_shot_vs_adapted_plan"
TRAINING_ROWS_SCHEMA_VERSION = V26_TRAINING_ROWS_SCHEMA_VERSION
TRAINING_SOURCE_SCHEMA_VERSION = V26_TRAINING_SOURCE_SCHEMA_VERSION
REFERENCE_TRAINING_SCHEMA_VERSION = "camp_dp_v25_strict_convex_training_artifact_v1"
SAME_EGO_BATCH_SIZE = 8

ADAPTATION_MODEL_IDS = (
    "CAMP-Static9D",
    "CAMP-Scene9D",
    "CAMP-Static14D",
    "CAMP-Scene14D",
)
ACTIVE_INDICES_BY_MODEL = {
    "CAMP-Static9D": tuple(range(9)),
    "CAMP-Scene9D": tuple(range(9)),
    "CAMP-Static14D": tuple(range(14)),
    "CAMP-Scene14D": tuple(range(14)),
}
MODEL_PREFIXES = {
    "CAMP-Static9D": "static9d",
    "CAMP-Scene9D": "scene9d",
    "CAMP-Static14D": "static14d",
    "CAMP-Scene14D": "scene14d",
}
FROZEN_COMPONENTS = (
    "fixed_dp",
    "checkpoint",
    "generator",
    "same_ego_b8_pool_topology",
)


@dataclass(frozen=True)
class TrainOnlySavedPools:
    """Validated, reviewed train-only B8 rows used by the adaptation layer."""

    source_dir: Path
    rows_path: Path
    rows_sha256: str
    source_report_sha256: str
    label_sidecar_sha256: str
    fixed_dp_head: str
    normalized_atoms_14d: np.ndarray
    raw_context: np.ndarray
    context_source_complete: np.ndarray
    oracle_indices: np.ndarray
    margins: np.ndarray
    source_valid_mask: np.ndarray
    physical_feasible_mask: np.ndarray
    record_weights: np.ndarray
    route_ids: np.ndarray
    corridor_ids: np.ndarray
    map_family_ids: np.ndarray
    seeds: np.ndarray
    scenario_ids: np.ndarray
    source_manifest_sha256: str
    event_manifest_sha256: np.ndarray
    training_scales: np.ndarray
    source_snapshot_count: int

    @property
    def record_count(self) -> int:
        return int(self.normalized_atoms_14d.shape[0])

    def identity_summary(self) -> dict[str, Any]:
        return {
            "split": "training_only",
            "holdout_accessed": False,
            "saved_pool_record_count": self.record_count,
            "candidate_count_per_saved_pool": SAME_EGO_BATCH_SIZE,
            "unique_route_count": int(np.unique(self.route_ids).size),
            "unique_corridor_count": int(np.unique(self.corridor_ids).size),
            "unique_map_family_count": int(np.unique(self.map_family_ids).size),
            "unique_scenario_count": int(np.unique(self.scenario_ids).size),
            "route_ids_sha256": _array_fingerprint(self.route_ids),
            "map_family_ids_sha256": _array_fingerprint(self.map_family_ids),
            "scenario_ids_sha256": _array_fingerprint(self.scenario_ids),
            "seeds_sha256": _array_fingerprint(self.seeds),
            "source_manifest_sha256": self.source_manifest_sha256,
            "event_manifest_sha256": _array_fingerprint(self.event_manifest_sha256),
            "training_source_schema": TRAINING_SOURCE_SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class ZeroShotReferenceAssets:
    """Read-only frozen zero-shot selector parameters and scaler."""

    source_dir: Path
    reference_role: str
    fixed_dp_head: str
    model_parameters_sha256: str
    model_reports_sha256: str
    runtime_scales_sha256: str
    static9d_theta: np.ndarray
    scene9d_theta: np.ndarray
    static14d_theta: np.ndarray
    scene14d_theta: np.ndarray
    context_scaler: V25ContextScaler
    atom_scales: np.ndarray

    def parameter_hashes(self) -> dict[str, str]:
        return {
            "static9d_theta_sha256": training_parameter_array_sha256(
                self.static9d_theta
            ),
            "scene9d_theta_sha256": training_parameter_array_sha256(
                self.scene9d_theta
            ),
            "static14d_theta_sha256": training_parameter_array_sha256(
                self.static14d_theta
            ),
            "scene14d_theta_sha256": training_parameter_array_sha256(
                self.scene14d_theta
            ),
            "context_scaler_sha256": _context_scaler_sha256(self.context_scaler),
            "atom_scales_sha256": _array_fingerprint(self.atom_scales),
        }


@dataclass(frozen=True)
class AdaptationConfig:
    """Explicit optimizer/config identity for CAMP-only fitting."""

    path: Path
    sha256: str
    payload: dict[str, Any]
    master: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _array_fingerprint(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype.hasobject:
        raise ValueError("object arrays are forbidden in V26 adaptation provenance")
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(
        json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
    )
    digest.update(array.tobytes())
    return digest.hexdigest()


def _json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be a SHA256 string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    return value


def _require_commit(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError(f"{label} must be a full commit")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    return value


def _require_finite_numeric(
    value: Any, shape: tuple[int, ...], label: str, *, nonnegative: bool = False
) -> np.ndarray:
    array = np.asarray(value)
    if (
        array.shape != shape
        or array.dtype.kind not in "fiu"
        or array.dtype.kind == "b"
    ):
        raise ValueError(f"{label} must be numeric with shape {list(shape)}")
    result = array.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)) or (nonnegative and np.any(result < 0.0)):
        raise ValueError(f"{label} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result.copy()


def _require_bool(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or array.dtype != np.bool_:
        raise ValueError(f"{label} must be bool with shape {list(shape)}")
    return array.copy()


def _require_integer(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or array.dtype.kind not in "iu" or array.dtype.kind == "b":
        raise ValueError(f"{label} must be an integer array with shape {list(shape)}")
    return array.astype(np.int64, copy=True)


def _require_string_vector(value: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (size,) or array.dtype.kind not in "SU":
        raise ValueError(f"{label} must be a native string vector")
    if any(not str(item) for item in array.tolist()):
        raise ValueError(f"{label} must not contain empty values")
    return array.copy()


def _archive_scalar_string(archive: Any, key: str, label: str) -> str:
    if key not in archive.files:
        raise ValueError(f"{label} is missing")
    value = np.asarray(archive[key])
    if value.shape != ():
        raise ValueError(f"{label} must be a scalar")
    result = value.item()
    if not isinstance(result, str):
        raise ValueError(f"{label} must be a string")
    return result


def _require_hash_vector(value: Any, size: int, label: str) -> np.ndarray:
    result = _require_string_vector(value, size, label)
    for item in result.tolist():
        _require_sha256(str(item), label)
    return result


def _require_hash_matrix(value: Any, shape: tuple[int, int], label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or array.dtype.kind not in "SU":
        raise ValueError(f"{label} must be a native SHA256 matrix")
    result = array.copy()
    for row in result.tolist():
        if len(set(str(item) for item in row)) != shape[1]:
            raise ValueError(f"{label} rows must remain unique B8 identities")
        for item in row:
            _require_sha256(str(item), label)
    return result


def _require_constant_integer(value: Any, shape: tuple[int, ...], expected: int, label: str) -> np.ndarray:
    result = _require_integer(value, shape, label)
    if not np.all(result == expected):
        raise ValueError(f"{label} must be exactly {expected}")
    return result


def load_train_only_saved_pools(source_dir: Path) -> TrainOnlySavedPools:
    """Load only V26-proven same-ego single-invocation B8 training pools."""

    source = Path(source_dir).resolve()
    report_path = source / "report.json"
    label_path = source / "label_sidecar.json"
    rows_path = source / "training_rows.npz"
    report = _json_object(report_path, "training source report")
    label = _json_object(label_path, "training label sidecar")
    if report.get("schema_version") != TRAINING_SOURCE_SCHEMA_VERSION:
        if type(report.get("schema_version")) is str and report["schema_version"].startswith("camp_dp_v25_"):
            raise ValueError("V25 rows are zero-shot reference-only and cannot be V26 fit input")
        raise ValueError("V26 adaptation requires the V26 same-ego B8 training-source schema")
    if (
        report.get("evidence_role") != "development_training_same_ego_b8_acquisition"
        or report.get("status") != "terminal_training_evidence"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("generator_id") != V26_GENERATOR_ID
        or report.get("generator_topology") != v26_generator_topology()
        or report.get("outcome_fields_consumed") != []
        or report.get("holdout_accessed") is not False
        or report.get("training_rows_schema_version") != TRAINING_ROWS_SCHEMA_VERSION
    ):
        raise ValueError("V26 adaptation requires outcome-blind same-ego B8 training evidence")
    source_manifest_sha = _require_sha256(
        report.get("source_manifest_sha256"), "V26 training source manifest"
    )
    denominator = report.get("denominator")
    if (
        type(denominator) is not dict
        or set(denominator) != {"planned", "complete", "failed", "unattempted"}
        or any(type(value) is not int or value < 0 for value in denominator.values())
        or denominator["planned"]
        != denominator["complete"] + denominator["failed"] + denominator["unattempted"]
    ):
        raise ValueError("V26 training source denominator is invalid")
    rows_sha256 = _sha256_file(rows_path)
    if report.get("training_rows_sha256") != rows_sha256:
        raise ValueError("V26 adaptation training rows SHA256 drifted")
    if (
        label.get("training_source_schema") != TRAINING_SOURCE_SCHEMA_VERSION
        or label.get("label_contract") != "causal_policy_distillation_no_outcome"
        or label.get("fresh_or_outcome_consumed") is not False
        or label.get("identity_fields_used_as_label_or_feature") is not False
    ):
        raise ValueError("V26 adaptation training labels are not outcome blind")

    with np.load(rows_path, allow_pickle=False) as archive:
        if (
            _archive_scalar_string(archive, "schema_version", "training row schema")
            != TRAINING_ROWS_SCHEMA_VERSION
        ):
            raise ValueError("V26 adaptation training row schema drifted")
        if "normalized_atoms_14d" not in archive.files:
            raise ValueError("V26 adaptation normalized atoms are missing")
        atoms = np.asarray(archive["normalized_atoms_14d"])
        if atoms.ndim != 3 or atoms.shape[1:] != (SAME_EGO_BATCH_SIZE, 14):
            raise ValueError("V26 adaptation requires saved B8 14D atom pools")
        count = int(atoms.shape[0])
        if count < 1:
            raise ValueError("V26 adaptation requires at least one saved training pool")
        normalized_atoms = _require_finite_numeric(
            atoms, (count, SAME_EGO_BATCH_SIZE, 14), "normalized_atoms_14d", nonnegative=True
        )
        if np.any(normalized_atoms > 10.0 + 1e-12):
            raise ValueError("V26 adaptation atoms exceed the canonical normalized clip")
        raw_context = _require_finite_numeric(
            archive["raw_context"], (count, RAW_FEATURE_COUNT), "raw_context"
        )
        context_source = _require_bool(
            archive["context_source_complete"],
            (count, RAW_FEATURE_COUNT),
            "context_source_complete",
        )
        oracle = _require_integer(archive["oracle_indices"], (count,), "oracle_indices")
        margins = _require_finite_numeric(
            archive["margins"], (count, SAME_EGO_BATCH_SIZE), "margins", nonnegative=True
        )
        source_valid = _require_bool(
            archive["source_valid_mask"],
            (count, SAME_EGO_BATCH_SIZE),
            "source_valid_mask",
        )
        atom_source = _require_bool(
            archive["atom_source_valid_mask"],
            (count, SAME_EGO_BATCH_SIZE, 14),
            "atom_source_valid_mask",
        )
        applicable = _require_bool(
            archive["atom_applicable_mask"],
            (count, SAME_EGO_BATCH_SIZE, 14),
            "atom_applicable_mask",
        )
        physical = _require_bool(
            archive["physical_feasible_mask"],
            (count, SAME_EGO_BATCH_SIZE),
            "physical_feasible_mask",
        )
        record_weights = _require_finite_numeric(
            archive["record_weights"], (count,), "record_weights"
        )
        route_ids = _require_string_vector(archive["route_ids"], count, "route_ids")
        corridor_ids = _require_string_vector(
            archive["corridor_ids"], count, "corridor_ids"
        )
        map_family_ids = _require_string_vector(
            archive["map_family_ids"], count, "map_family_ids"
        )
        seeds = _require_integer(archive["seeds"], (count,), "seeds")
        scenario_ids = _require_string_vector(
            archive["scenario_ids"], count, "scenario_ids"
        )
        archived_source_manifest_sha = _archive_scalar_string(
            archive, "source_manifest_sha256", "V26 training source manifest"
        )
        _require_sha256(archived_source_manifest_sha, "V26 archived training source manifest")
        event_manifest_sha = _require_hash_vector(
            archive["event_manifest_sha256"], count, "event_manifest_sha256"
        )
        _require_constant_integer(
            archive["model_call_count"], (count,), 1, "model_call_count"
        )
        _require_constant_integer(
            archive["sequential_forward_count"], (count,), 0, "sequential_forward_count"
        )
        _require_constant_integer(
            archive["candidate0_row"], (count,), 0, "candidate0_row"
        )
        _require_constant_integer(
            archive["post_pool_model_dp_latent_generation_calls"],
            (count,),
            0,
            "post_pool_model_dp_latent_generation_calls",
        )
        _require_constant_integer(
            archive["candidate_pool_mutation_count"],
            (count,),
            0,
            "candidate_pool_mutation_count",
        )
        _require_constant_integer(
            archive["trajectory_regeneration_count"],
            (count,),
            0,
            "trajectory_regeneration_count",
        )
        _require_hash_matrix(
            archive["latent_row_sha256"], (count, SAME_EGO_BATCH_SIZE), "latent_row_sha256"
        )
        _require_hash_matrix(
            archive["candidate_row_sha256"], (count, SAME_EGO_BATCH_SIZE), "candidate_row_sha256"
        )
        scales = _require_finite_numeric(
            archive["training_scales"], (14,), "training_scales"
        )
    if archived_source_manifest_sha != source_manifest_sha:
        raise ValueError("V26 training source manifest binding drifted")
    if (
        np.any(record_weights <= 0.0)
        or np.any(scales <= 0.0)
        or np.any(~np.any(source_valid, axis=1))
        or np.any(oracle < 0)
        or np.any(oracle >= SAME_EGO_BATCH_SIZE)
        or np.any(~source_valid[np.arange(count), oracle])
    ):
        raise ValueError("V26 adaptation training-pool eligibility drifted")
    if (
        np.any(applicable & ~atom_source)
        or not np.array_equal(source_valid, np.all(atom_source, axis=2))
        or np.any(physical & ~source_valid)
    ):
        raise ValueError("V26 adaptation source/applicability/physical masks drifted")
    if (
        report.get("snapshot_count") != count
        or report.get("candidate_count") != count * SAME_EGO_BATCH_SIZE
        or denominator["complete"] != count
        or denominator["planned"] < count
    ):
        raise ValueError("V26 adaptation training-source denominator drifted")
    return TrainOnlySavedPools(
        source_dir=source,
        rows_path=rows_path,
        rows_sha256=rows_sha256,
        source_report_sha256=_sha256_file(report_path),
        label_sidecar_sha256=_sha256_file(label_path),
        fixed_dp_head=FIXED_DP_HEAD,
        normalized_atoms_14d=normalized_atoms,
        raw_context=raw_context,
        context_source_complete=context_source,
        oracle_indices=oracle,
        margins=margins,
        source_valid_mask=source_valid,
        physical_feasible_mask=physical,
        record_weights=record_weights,
        route_ids=route_ids,
        corridor_ids=corridor_ids,
        map_family_ids=map_family_ids,
        seeds=seeds,
        scenario_ids=scenario_ids,
        source_manifest_sha256=source_manifest_sha,
        event_manifest_sha256=event_manifest_sha,
        training_scales=scales,
        source_snapshot_count=count,
    )


def _theta_from_archive(archive: Any, key: str, atom_count: int) -> np.ndarray:
    if key not in archive.files:
        raise ValueError(f"zero-shot reference {key} is missing")
    theta = _require_finite_numeric(
        archive[key], (atom_count, PHI_DIMENSION), key
    )
    # Preserve the frozen solver bytes.  The existing runtime admits only its
    # established simplex tolerance; it must not clip or reproject theta.
    return validate_column_simplex_theta(
        theta, num_atoms=atom_count, atol=FROZEN_SIMPLEX_TOLERANCE
    ).copy()


def load_zero_shot_reference_assets(reference_dir: Path) -> ZeroShotReferenceAssets:
    """Load frozen zero-shot weights as references, never as mutable parameters."""

    source = Path(reference_dir).resolve()
    report_path = source / "report.json"
    parameter_path = source / "model_parameters.npz"
    model_reports_path = source / "model_reports.json"
    runtime_scales_path = source / "runtime_atom_scales.json"
    report = _json_object(report_path, "zero-shot reference report")
    if (
        report.get("schema_version") != REFERENCE_TRAINING_SCHEMA_VERSION
        or report.get("status") != "passed_strict_convex_training"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("outcome_fields_consumed") != []
        or report.get("fresh_b2_opened") is not False
        or report.get("calibration_executed") is not False
        or report.get("model_parameters_sha256") != _sha256_file(parameter_path)
    ):
        raise ValueError("V26 adaptation zero-shot reference identity drifted")
    model_reports = _json_object(model_reports_path, "zero-shot model reports")
    if set(model_reports) != set(ADAPTATION_MODEL_IDS):
        raise ValueError("V26 adaptation zero-shot model registry drifted")
    scales_payload = _json_object(runtime_scales_path, "zero-shot runtime atom scales")
    with np.load(parameter_path, allow_pickle=False) as archive:
        q05 = _require_finite_numeric(
            archive["context_q05"], (RAW_FEATURE_COUNT,), "context_q05"
        )
        q95 = _require_finite_numeric(
            archive["context_q95"], (RAW_FEATURE_COUNT,), "context_q95"
        )
        static9 = _theta_from_archive(archive, "static9d_theta", 9)
        scene9 = _theta_from_archive(archive, "scene9d_theta", 9)
        static14 = _theta_from_archive(archive, "static14d_theta", 14)
        scene14 = _theta_from_archive(archive, "scene14d_theta", 14)
    scaler = V25ContextScaler(q05=q05, q95=q95)
    scales = _require_finite_numeric(
        scales_payload.get("scales"), (14,), "zero-shot runtime scales"
    )
    if np.any(scales <= 0.0):
        raise ValueError("zero-shot runtime scales must be positive")
    expected_thetas = {
        "CAMP-Static9D": static9,
        "CAMP-Scene9D": scene9,
        "CAMP-Static14D": static14,
        "CAMP-Scene14D": scene14,
    }
    for name, theta in expected_thetas.items():
        model_report = model_reports[name]
        if (
            type(model_report) is not dict
            or model_report.get("theta_sha256") != training_parameter_array_sha256(theta)
            or model_report.get("outcome_or_fresh_consumed") is not False
        ):
            raise ValueError(f"V26 adaptation zero-shot model report drifted: {name}")
    return ZeroShotReferenceAssets(
        source_dir=source,
        reference_role=V25_ZERO_SHOT_REFERENCE_READ_ONLY,
        fixed_dp_head=FIXED_DP_HEAD,
        model_parameters_sha256=_sha256_file(parameter_path),
        model_reports_sha256=_sha256_file(model_reports_path),
        runtime_scales_sha256=_sha256_file(runtime_scales_path),
        static9d_theta=static9,
        scene9d_theta=scene9,
        static14d_theta=static14,
        scene14d_theta=scene14,
        context_scaler=scaler,
        atom_scales=scales,
    )


def _context_scaler_sha256(scaler: V25ContextScaler) -> str:
    return _canonical_json_sha256(
        {
            "q05": scaler.q05.tolist(),
            "q95": scaler.q95.tolist(),
            "raw_feature_names": list(RAW_FEATURE_NAMES),
        }
    )


def _distribution(values: np.ndarray) -> dict[str, Any]:
    data = np.asarray(values, dtype=np.float64).reshape(-1)
    if data.size == 0:
        return {"observed_count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "observed_count": int(data.size),
        "minimum": float(np.min(data)),
        "median": float(np.median(data)),
        "maximum": float(np.max(data)),
    }


def _selected_index_counts(indices: np.ndarray) -> dict[str, int]:
    result = {str(index): 0 for index in range(SAME_EGO_BATCH_SIZE)}
    for index in np.asarray(indices, dtype=np.int64).tolist():
        result[str(index)] += 1
    return result


def _select_scores(
    atoms: np.ndarray, source_valid: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    if weights.ndim == 1:
        scores = np.einsum("nka,a->nk", atoms, weights)
    elif weights.ndim == 2:
        scores = np.einsum("nka,na->nk", atoms, weights)
    else:
        raise ValueError("selector weights must be [A] or [N,A]")
    if not np.all(np.isfinite(scores)):
        raise ValueError("selector scores must be finite")
    eligible = np.where(source_valid, scores, np.inf)
    selected = np.argmin(eligible, axis=1).astype(np.int64)
    sorted_scores = np.sort(eligible, axis=1)
    margin = sorted_scores[:, 1] - sorted_scores[:, 0]
    margin[np.sum(source_valid, axis=1) < 2] = 0.0
    if not np.all(np.isfinite(margin)):
        raise ValueError("selector margin must be finite")
    return selected, margin


def _label_rank(
    margins: np.ndarray, source_valid: np.ndarray, selected: np.ndarray
) -> np.ndarray:
    candidate_indices = np.arange(SAME_EGO_BATCH_SIZE, dtype=np.int64)[None, :]
    selected_values = margins[np.arange(margins.shape[0]), selected][:, None]
    lower = (margins < selected_values) | (
        (margins == selected_values) & (candidate_indices < selected[:, None])
    )
    return (1 + np.sum(source_valid & lower, axis=1)).astype(np.int64)


def _reference_model_weights(
    data: TrainOnlySavedPools, reference: ZeroShotReferenceAssets
) -> dict[str, np.ndarray]:
    phi = reference.context_scaler.lift(
        data.raw_context, source_complete=data.context_source_complete
    )
    return {
        "CAMP-Static9D": reference.static9d_theta[:, 0].copy(),
        "CAMP-Scene9D": context_weights(reference.scene9d_theta, phi),
        "CAMP-Static14D": reference.static14d_theta[:, 0].copy(),
        "CAMP-Scene14D": context_weights(reference.scene14d_theta, phi),
    }


def build_saved_pool_selection_diagnostic(
    data: TrainOnlySavedPools, reference: ZeroShotReferenceAssets
) -> dict[str, Any]:
    """Describe frozen-reference selection inputs without outcome evaluation."""

    if data.fixed_dp_head != reference.fixed_dp_head:
        raise ValueError("saved-pool and reference fixed-DP identities differ")
    weights = _reference_model_weights(data, reference)
    arm_results: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    per_arm: dict[str, Any] = {}
    candidate0 = np.zeros(data.record_count, dtype=np.int64)
    candidate0_observed = data.source_valid_mask[:, 0]
    candidate0_rank = _label_rank(
        data.margins[candidate0_observed],
        data.source_valid_mask[candidate0_observed],
        candidate0[candidate0_observed],
    )
    per_arm["candidate0"] = {
        "selected_index_counts": _selected_index_counts(candidate0),
        "source_valid_selected_count": int(np.sum(candidate0_observed)),
        "selected_train_only_label_rank": _distribution(candidate0_rank),
        "model_score_margin": {"observed_count": 0, "minimum": None, "median": None, "maximum": None},
        "selection_disagrees_with_candidate0": {
            "observed_count": int(np.sum(candidate0_observed)),
            "count": 0,
        },
    }
    for name in ADAPTATION_MODEL_IDS:
        active = ACTIVE_INDICES_BY_MODEL[name]
        selected, score_margin = _select_scores(
            data.normalized_atoms_14d[:, :, active],
            data.source_valid_mask,
            weights[name],
        )
        arm_results[name] = (selected, score_margin)
        observed = candidate0_observed
        per_arm[name] = {
            "selected_index_counts": _selected_index_counts(selected),
            "source_valid_selected_count": data.record_count,
            "selected_train_only_label_rank": _distribution(
                _label_rank(data.margins, data.source_valid_mask, selected)
            ),
            "model_score_margin": _distribution(score_margin),
            "selection_disagrees_with_candidate0": {
                "observed_count": int(np.sum(observed)),
                "count": int(np.sum(selected[observed] != 0)),
            },
        }
    static9, _ = arm_results["CAMP-Static9D"]
    scene9, _ = arm_results["CAMP-Scene9D"]
    static14, _ = arm_results["CAMP-Static14D"]
    scene14, _ = arm_results["CAMP-Scene14D"]
    context_coverage = {
        name: {
            "available": int(np.sum(data.context_source_complete[:, index])),
            "unavailable": int(
                data.record_count - np.sum(data.context_source_complete[:, index])
            ),
        }
        for index, name in enumerate(RAW_FEATURE_NAMES)
    }
    return {
        "schema_version": SAVED_POOL_DIAGNOSTIC_SCHEMA_VERSION,
        "evidence_role": SAVED_POOL_DIAGNOSTIC_ROLE,
        "scope": (
            "outcome-blind saved-pool rank/flip/margin/scale/context input "
            "diagnostic only; not an effect, safety, support/OOD, stability, "
            "or route-selection result"
        ),
        "source_pool_provenance": {
            "source_dir": str(data.source_dir),
            "training_rows_sha256": data.rows_sha256,
            "source_report_sha256": data.source_report_sha256,
            "label_sidecar_sha256": data.label_sidecar_sha256,
            "fixed_dp_head": data.fixed_dp_head,
            "same_ego_batch_size": SAME_EGO_BATCH_SIZE,
            "stage7_model_dp_latent_generation_calls": 0,
            "training_identity": data.identity_summary(),
        },
        "zero_shot_reference": {
            "source_dir": str(reference.source_dir),
            "compatibility_role": reference.reference_role,
            "fixed_dp_head": reference.fixed_dp_head,
            "model_parameters_sha256": reference.model_parameters_sha256,
            "model_reports_sha256": reference.model_reports_sha256,
            "runtime_scales_sha256": reference.runtime_scales_sha256,
            **reference.parameter_hashes(),
        },
        "denominator": {
            "planned": data.record_count,
            "complete": data.record_count,
            "failed": 0,
            "unattempted": 0,
        },
        "selection_description": {
            "arms": per_arm,
            "flip_counts": {
                "static9d_vs_static14d": int(np.sum(static9 != static14)),
                "scene9d_vs_scene14d": int(np.sum(scene9 != scene14)),
                "static9d_vs_scene9d": int(np.sum(static9 != scene9)),
                "static14d_vs_scene14d": int(np.sum(static14 != scene14)),
            },
        },
        "input_coverage": {
            "source_valid_candidate_count": _distribution(
                np.sum(data.source_valid_mask, axis=1)
            ),
            "physical_feasible_candidate_count": _distribution(
                np.sum(data.physical_feasible_mask, axis=1)
            ),
            "training_scales": {
                "sha256": _array_fingerprint(data.training_scales),
                **_distribution(data.training_scales),
            },
            "reference_runtime_scales": {
                "sha256": _array_fingerprint(reference.atom_scales),
                **_distribution(reference.atom_scales),
            },
            "context_source_complete": context_coverage,
        },
    }


def load_adaptation_config(path: Path) -> AdaptationConfig:
    """Load the explicit selector-only training configuration."""

    config_path = Path(path).resolve()
    payload = _json_object(config_path, "V26 adaptation config")
    expected = {
        "schema_version",
        "evidence_role",
        "adaptation_scope",
        "frozen_components",
        "reference_role",
        "training_label_contract",
        "models",
        "master",
        "comparison_protocol",
    }
    if set(payload) != expected:
        raise ValueError("V26 adaptation config field set drifted")
    if (
        payload["schema_version"] != ADAPTATION_CONFIG_SCHEMA_VERSION
        or payload["evidence_role"] != ADAPTATION_ROLE
        or payload["adaptation_scope"] != "camp_selector_adaptation_layer_only"
        or payload["frozen_components"] != list(FROZEN_COMPONENTS)
        or payload["reference_role"] != "frozen_zero_shot_reference_arm"
        or payload["training_label_contract"] != "causal_policy_distillation_no_outcome"
        or payload["models"] != list(ADAPTATION_MODEL_IDS)
    ):
        raise ValueError("V26 adaptation config identity drifted")
    comparison = payload["comparison_protocol"]
    if (
        type(comparison) is not dict
        or comparison
        != {
            "profiling_pools_are_training_and_route_selection_excluded": True,
            "comparison_identities_must_be_new_and_prefixed_before_execution": True,
            "closed_loop_if_executed": "each_arm_own_state_compute_matched",
            "same_pool_profiling_is_not_effect_evaluation": True,
        }
    ):
        raise ValueError("V26 adaptation comparison protocol drifted")
    master_payload = payload["master"]
    expected_master = {
        "alpha",
        "l2_reg",
        "bt_anchor_reg",
        "max_iter",
        "tolerance",
        "solver",
        "solver_options",
        "bt_iterations",
        "bt_learning_rate",
        "bt_l2_reg",
        "bt_max_pairs",
    }
    if type(master_payload) is not dict or set(master_payload) != expected_master:
        raise ValueError("V26 adaptation master config field set drifted")
    options = master_payload["solver_options"]
    if type(options) is not dict:
        raise ValueError("V26 adaptation solver_options must be an object")
    master = {
        "alpha": float(master_payload["alpha"]),
        "l2_reg": float(master_payload["l2_reg"]),
        "bt_anchor_reg": float(master_payload["bt_anchor_reg"]),
        "max_iter": int(master_payload["max_iter"]),
        "tolerance": float(master_payload["tolerance"]),
        "solver": str(master_payload["solver"]),
        "solver_options": tuple(options.items()),
        "bt_iterations": int(master_payload["bt_iterations"]),
        "bt_learning_rate": float(master_payload["bt_learning_rate"]),
        "bt_l2_reg": float(master_payload["bt_l2_reg"]),
        "bt_max_pairs": int(master_payload["bt_max_pairs"]),
    }
    if (
        not 0.0 <= master["alpha"] < 1.0
        or master["l2_reg"] < 0.0
        or master["bt_anchor_reg"] < 0.0
        or master["max_iter"] < 1
        or master["tolerance"] < 0.0
        or master["solver"] != "CLARABEL"
        or master["bt_iterations"] < 1
        or master["bt_learning_rate"] <= 0.0
        or master["bt_l2_reg"] < 0.0
        or master["bt_max_pairs"] < 1
    ):
        raise ValueError("V26 adaptation master config values are invalid")
    return AdaptationConfig(
        path=config_path,
        sha256=_sha256_file(config_path),
        payload=payload,
        master=master,
    )


def train_selector_adaptation(
    data: TrainOnlySavedPools, config: AdaptationConfig
) -> dict[str, V25TrainedSelector]:
    """Fit only CAMP Static/Scene 9D/14D selector parameters."""

    from camp_core.integrations.diffusion_planner_v25_training import (
        train_v25_selector_suite,
    )
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
    )

    return train_v25_selector_suite(
        data.normalized_atoms_14d,
        data.raw_context,
        data.context_source_complete,
        data.oracle_indices,
        data.margins,
        data.source_valid_mask,
        data.record_weights,
        stability_cluster_ids=tuple(str(item) for item in data.corridor_ids.tolist()),
        config=V25ParametricMasterConfig(**config.master),
    )


def adapted_parameter_arrays(
    data: TrainOnlySavedPools, suite: Mapping[str, V25TrainedSelector]
) -> dict[str, np.ndarray]:
    """Serialize fitted selector parameters without modifying frozen references."""

    if set(suite) != set(ADAPTATION_MODEL_IDS):
        raise ValueError("V26 adaptation suite model set drifted")
    scene14 = suite["CAMP-Scene14D"]
    arrays: dict[str, np.ndarray] = {
        "schema_version": np.asarray(V26_ADAPTED_WEIGHTS_SCHEMA_VERSION),
        "training_rows_sha256": np.asarray(data.rows_sha256),
        "context_feature_names": np.asarray(RAW_FEATURE_NAMES),
        "context_q05": np.asarray(scene14.context_scaler.q05, dtype=np.float64),
        "context_q95": np.asarray(scene14.context_scaler.q95, dtype=np.float64),
        "training_scales_14d": np.asarray(data.training_scales, dtype=np.float64),
    }
    for name in ADAPTATION_MODEL_IDS:
        model = suite[name]
        prefix = MODEL_PREFIXES[name]
        expected_active = ACTIVE_INDICES_BY_MODEL[name]
        if model.active_atom_indices != expected_active:
            raise ValueError(f"V26 adaptation active atom identity drifted: {name}")
        arrays[f"{prefix}_theta"] = np.asarray(model.theta, dtype=np.float64)
        arrays[f"{prefix}_selected_indices"] = np.asarray(
            model.selected_indices, dtype=np.int64
        )
        arrays[f"{prefix}_selection_margins"] = np.asarray(
            model.selection_margins, dtype=np.float64
        )
        arrays[f"{prefix}_train_violations"] = np.asarray(
            model.result.train_violations, dtype=np.float64
        )
        if name.startswith("CAMP-Static"):
            arrays[f"{prefix}_runtime_weights"] = np.asarray(
                model.theta[:, 0], dtype=np.float64
            )
    return arrays


def adapted_model_summary(
    suite: Mapping[str, V25TrainedSelector]
) -> dict[str, dict[str, Any]]:
    """Return compact fitted-parameter provenance without outcome metrics."""

    result: dict[str, dict[str, Any]] = {}
    for name in ADAPTATION_MODEL_IDS:
        model = suite[name]
        result[name] = {
            "mode": model.mode,
            "active_atom_indices": list(model.active_atom_indices),
            "theta_sha256": training_parameter_array_sha256(model.theta),
            "context_scaler_sha256": _context_scaler_sha256(model.context_scaler),
            "solver_name": model.result.solver_name,
            "solver_status": model.result.solver_status,
            "converged": bool(model.result.converged),
            "iterations": int(model.result.iterations),
            "training_rows": int(model.selected_indices.size),
            "outcome_or_fresh_consumed": False,
        }
    return result


def build_adaptation_manifest(
    *,
    camp_head: str,
    config: AdaptationConfig,
    data: TrainOnlySavedPools,
    reference: ZeroShotReferenceAssets,
    fixed_dp_checkpoint: Mapping[str, str],
    fixed_dp_args: Mapping[str, str],
) -> dict[str, Any]:
    """Build the pre-fit identity record for a selector-only run."""

    if data.fixed_dp_head != reference.fixed_dp_head:
        raise ValueError("training and zero-shot references have different fixed-DP heads")
    if reference.reference_role != V25_ZERO_SHOT_REFERENCE_READ_ONLY:
        raise ValueError("zero-shot compatibility weights must be reference-only")
    checkpoint_path = fixed_dp_checkpoint.get("path")
    args_path = fixed_dp_args.get("path")
    if type(checkpoint_path) is not str or type(args_path) is not str:
        raise ValueError("fixed DP checkpoint and args paths are required")
    checkpoint = {"path": checkpoint_path, "sha256": fixed_dp_checkpoint.get("sha256")}
    args = {"path": args_path, "sha256": fixed_dp_args.get("sha256")}
    checkpoint["sha256"] = _require_sha256(checkpoint["sha256"], "fixed DP checkpoint")
    args["sha256"] = _require_sha256(args["sha256"], "fixed DP args")
    if not checkpoint["path"] or not args["path"]:
        raise ValueError("fixed DP checkpoint and args paths are required")
    return {
        "schema_version": "camp_dp_v26_selector_adaptation_manifest_v1",
        "evidence_role": ADAPTATION_ROLE,
        "camp_head": _require_commit(camp_head, "camp_head"),
        "adaptation_scope": "camp_selector_adaptation_layer_only",
        "frozen_components": list(FROZEN_COMPONENTS),
        "frozen_dp": {
            "head": data.fixed_dp_head,
            "checkpoint": checkpoint,
            "args": args,
            "stage7_model_dp_latent_generation_calls": 0,
        },
        "saved_pool_provenance": {
            "training_rows_sha256": data.rows_sha256,
            "source_report_sha256": data.source_report_sha256,
            "label_sidecar_sha256": data.label_sidecar_sha256,
            "source_dir": str(data.source_dir),
            "pool_count": data.record_count,
            "same_ego_batch_size": SAME_EGO_BATCH_SIZE,
            "training_source_schema": TRAINING_SOURCE_SCHEMA_VERSION,
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "source_manifest_sha256": data.source_manifest_sha256,
            "event_manifest_sha256": _array_fingerprint(data.event_manifest_sha256),
            "generator_invoked_by_stage7": False,
        },
        "training_identity": data.identity_summary(),
        "training_label_contract": "causal_policy_distillation_no_outcome",
        "reference": {
            "role": "frozen_zero_shot_reference_arm",
            "compatibility_role": reference.reference_role,
            "source_dir": str(reference.source_dir),
            "model_parameters_sha256": reference.model_parameters_sha256,
            "model_reports_sha256": reference.model_reports_sha256,
            "runtime_scales_sha256": reference.runtime_scales_sha256,
            **reference.parameter_hashes(),
        },
        "adaptation_config": {
            "path": str(config.path),
            "sha256": config.sha256,
            "models": list(ADAPTATION_MODEL_IDS),
        },
        "denominator": {
            "input_planned": data.record_count,
            "input_complete": data.record_count,
            "input_failed": 0,
            "input_unattempted": 0,
            "fit_planned": 1,
        },
    }


def build_adaptation_receipt(
    *,
    manifest: Mapping[str, Any],
    fitted_models: Mapping[str, Mapping[str, Any]],
    adapted_assets: Mapping[str, Mapping[str, str]],
    terminal_status: str,
    failure: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Create the ordinary development receipt for the adaptation run."""

    if terminal_status not in {"complete", "typed_failure"}:
        raise ValueError("V26 adaptation terminal status is invalid")
    if set(fitted_models) != set(ADAPTATION_MODEL_IDS) and terminal_status == "complete":
        raise ValueError("V26 adaptation complete receipt needs every fitted model")
    if terminal_status == "complete" and failure is not None:
        raise ValueError("V26 adaptation complete receipt cannot carry failure")
    if terminal_status == "typed_failure" and failure is None:
        raise ValueError("V26 adaptation typed failure needs a reason")
    return {
        "schema_version": ADAPTATION_RECEIPT_SCHEMA_VERSION,
        "evidence_role": ADAPTATION_ROLE,
        "scope": (
            "CAMP selector/adaptation-layer fitting only; fixed DP, checkpoint, "
            "generator, and same-ego B8 topology are not tuned"
        ),
        "manifest": dict(manifest),
        "terminal": {
            "status": terminal_status,
            "failure": None if failure is None else dict(failure),
        },
        "denominator": {
            **dict(manifest["denominator"]),
            "fit_complete": int(terminal_status == "complete"),
            "fit_failed": int(terminal_status == "typed_failure"),
            "fit_unattempted": 0,
        },
        "fitted_models": dict(fitted_models),
        "adapted_assets": dict(adapted_assets),
        "weight_roles": {
            "reference": V25_ZERO_SHOT_REFERENCE_READ_ONLY,
            "adapted": (
                V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
                if terminal_status == "complete"
                else "not_written_typed_failure"
            ),
        },
        "claim_scope": (
            "development training capability/provenance only; no support/OOD, "
            "stability, safety, benefit, or comparison conclusion"
        ),
    }


def canonical_comparison_state_identity(
    *, route_sha256: str, scenario_seed: int, spawn_config: Mapping[str, Any], unit_index: int
) -> str:
    """Create a comparison identity from route metadata, never outcomes."""

    _require_sha256(route_sha256, "comparison route_sha256")
    if type(scenario_seed) is not int or scenario_seed < 0:
        raise ValueError("comparison scenario seed must be nonnegative")
    if type(spawn_config) is not dict or type(unit_index) is not int or unit_index < 0:
        raise ValueError("comparison state identity inputs are invalid")
    payload = {
        "route_sha256": route_sha256,
        "scenario_seed": scenario_seed,
        "spawn_config": dict(spawn_config),
        "unit_index": unit_index,
        "role": COMPARISON_PLAN_ROLE,
    }
    return _canonical_json_sha256(payload)


def build_development_comparison_plan(
    profiling_manifest: Mapping[str, Any], *, profiling_manifest_sha256: str
) -> dict[str, Any]:
    """Pre-fix new development identities without reading profiling trajectories."""

    from camp_core.integrations.diffusion_planner_v26_development_profiling import (
        PROFILE_STATE_COUNT,
        validate_development_profiling_manifest,
    )

    source = validate_development_profiling_manifest(profiling_manifest)
    _require_sha256(profiling_manifest_sha256, "profiling_manifest_sha256")
    route = dict(source["route"])
    seed_material = {
        "role": COMPARISON_PLAN_ROLE,
        "route_sha256": route["route_sha256"],
        "profiling_scenario_seed": route["scenario_seed"],
        "spawn_config": route["spawn_config"],
        "derivation": "metadata_only_no_trajectory_or_selector_result",
    }
    comparison_seed = int(_canonical_json_sha256(seed_material)[:15], 16) % (2**31)
    if comparison_seed == route["scenario_seed"]:
        comparison_seed = (comparison_seed + 1) % (2**31)
    state_plan = [
        {
            "unit_index": index,
            "planned_state_id_sha256": canonical_comparison_state_identity(
                route_sha256=route["route_sha256"],
                scenario_seed=comparison_seed,
                spawn_config=route["spawn_config"],
                unit_index=index,
            ),
        }
        for index in range(PROFILE_STATE_COUNT)
    ]
    return {
        "schema_version": COMPARISON_PLAN_SCHEMA_VERSION,
        "evidence_role": COMPARISON_PLAN_ROLE,
        "status": "prepared_no_execution_no_claim",
        "source_profiling_manifest_sha256": profiling_manifest_sha256,
        "identity_derivation": (
            "SHA256 over profiling route metadata only; the 20-state trajectory, "
            "selector outputs, and descriptive summary are excluded"
        ),
        "route": {
            "split": "development_nonholdout",
            "holdout": False,
            "route_sha256": route["route_sha256"],
            "scenario_seed": comparison_seed,
            "spawn_config": route["spawn_config"],
        },
        "state_count": PROFILE_STATE_COUNT,
        "state_plan": state_plan,
        "disjoint_from_profiling": {
            "profiling_scenario_seed": route["scenario_seed"],
            "comparison_scenario_seed": comparison_seed,
            "scenario_seed_differs": comparison_seed != route["scenario_seed"],
            "same_pool_profiling_reuse_forbidden": True,
        },
        "arms": [
            "candidate0",
            "Static9D_zero_shot",
            "Scene9D_zero_shot",
            "Static14D_zero_shot",
            "Scene14D_zero_shot",
            "Static9D_adapted",
            "Scene9D_adapted",
            "Static14D_adapted",
            "Scene14D_adapted",
        ],
        "closed_loop_if_executed": (
            "each arm starts from its own reset state and uses one compute-matched "
            "same-ego B8 invocation; no cross-arm pool sharing"
        ),
        "forbidden_interpretation": (
            "same-pool profiling is not effect evaluation and this plan carries "
            "no support/OOD, stability, safety, benefit, or route-selection result"
        ),
    }
