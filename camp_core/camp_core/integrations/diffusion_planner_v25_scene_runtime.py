from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v21_native import array_sha256
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    V25ContextScaler,
    context_weights,
    validate_column_simplex_theta,
)


SCENE_RECEIPT_SCHEMA_VERSION = "camp_dp_v25_scene_weight_receipt_v3"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TRAINING_ARTIFACT_SCHEMA_VERSION = (
    "camp_dp_v25_strict_convex_training_artifact_v1"
)
TRAINING_REVIEW_SCHEMA_VERSION = "camp_dp_v25_strict_convex_training_review_v1"
MODEL_PARAMETER_SCHEMA_VERSION = "camp_dp_v25_trained_model_parameters_v1"
MODEL_NAME = "CAMP-Scene14D"
MODEL_PARAMETER_PREFIX = "scene14d"
# The convex producer and its accepted independent review both freeze these
# feasibility tolerances.  Runtime validation must preserve the stored solver
# output bit-for-bit; it must not project, clip, or renormalize it.
TRAINED_SIMPLEX_NONNEGATIVE_ATOL = 1e-9
TRAINED_SIMPLEX_SUM_ATOL = 1e-8
_MODEL_ENTRIES = [
    ("CAMP-Static14D", "static14d", "static", 14, True, False),
    ("CAMP-Scene14D", "scene14d", "scene", 14, True, False),
    ("CAMP-Static9D", "static9d", "static", 9, False, True),
    ("CAMP-Scene9D", "scene9d", "scene", 9, False, True),
]
_TRAINING_FILES = {
    "COMMAND",
    "HEADS",
    "model_parameters.npz",
    "model_registry.json",
    "model_reports.json",
    "report.json",
    "runtime_atom_scales.json",
    "static14d_runtime_weights.npy",
    "run.exit",
}
_REVIEW_FILES = {"COMMAND", "HEADS", "report.json", "run.exit"}
_PARAMETER_KEYS = {
    "schema_version",
    "context_feature_names",
    "context_q05",
    "context_q95",
    "training_scales_14d",
}
for _name, _prefix, _mode, _count, _primary, _ablation in _MODEL_ENTRIES:
    _PARAMETER_KEYS.update(
        {
            f"{_prefix}_theta",
            f"{_prefix}_selected_indices",
            f"{_prefix}_selection_margins",
            f"{_prefix}_train_violations",
            f"{_prefix}_cut_mask",
        }
    )
    if _mode == "static":
        _PARAMETER_KEYS.add(f"{_prefix}_runtime_weights")
_SHA256_CHARS = frozenset("0123456789abcdef")
_NO_V2I_RECEIPT_FIELDS = {
    "mode",
    "phase_remaining_available",
    "regulatory_signal_mapped",
}


@dataclass(frozen=True)
class V25Scene14DWeightProvider:
    """Auditable no-V2I runtime for the sealed Scene14D affine head.

    The provider only evaluates ``w(x)=Theta phi(x)``.  It does not project,
    clip, normalize, or otherwise repair Theta, phi, or the resulting weights.
    """

    theta: np.ndarray
    context_scaler: V25ContextScaler
    training_artifact: str
    training_root_sha256: str
    training_review_artifact: str
    training_review_root_sha256: str
    theta_sha256: str
    context_scaler_sha256: str

    def __call__(self, context_payload: Mapping[str, Any]) -> dict[str, Any]:
        if type(context_payload) is not dict or set(context_payload) != {
            "schema_version",
            "raw_context",
            "source_complete",
            "source_receipt",
        }:
            raise ValueError("V25 Scene14D context payload exact schema drifted")
        if context_payload["schema_version"] != CONTEXT_SCHEMA_VERSION:
            raise ValueError("V25 Scene14D context schema version drifted")

        raw_mapping = context_payload["raw_context"]
        source_mapping = context_payload["source_complete"]
        if type(raw_mapping) is not dict or set(raw_mapping) != set(RAW_FEATURE_NAMES):
            raise ValueError("V25 Scene14D raw context fields drifted")
        if type(source_mapping) is not dict or set(source_mapping) != set(
            RAW_FEATURE_NAMES
        ):
            raise ValueError("V25 Scene14D source-complete fields drifted")
        raw_values: list[float] = []
        source_values: list[bool] = []
        for name in RAW_FEATURE_NAMES:
            value = raw_mapping[name]
            source = source_mapping[name]
            if type(value) not in {int, float} or not np.isfinite(value):
                raise ValueError(f"V25 Scene14D context {name} must be finite numeric")
            if type(source) is not bool:
                raise ValueError(
                    f"V25 Scene14D source-complete {name} must be native boolean"
                )
            raw_values.append(float(value))
            source_values.append(source)

        timing_index = RAW_FEATURE_NAMES.index("traffic_signal_phase_remaining_s")
        timing_receipt = context_payload["source_receipt"]
        if (
            type(timing_receipt) is not dict
            or set(timing_receipt) != _NO_V2I_RECEIPT_FIELDS
            or timing_receipt.get("mode") != "no_v2i"
            or timing_receipt.get("phase_remaining_available") is not False
            or type(timing_receipt.get("regulatory_signal_mapped")) is not bool
            or source_values[timing_index] is not False
            or raw_values[timing_index] != 0.0
        ):
            raise ValueError("primary Scene14D requires the frozen no-V2I context")

        raw = np.asarray(raw_values, dtype=np.float64)
        source = np.asarray(source_values, dtype=np.bool_)
        phi = self.context_scaler.lift(raw, source_complete=source)
        weights = context_weights(self.theta, phi)
        if (
            weights.shape != (14,)
            or not np.all(np.isfinite(weights))
            or np.any(weights < 0.0)
            or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-10)
        ):
            raise ValueError("Scene14D affine head violated the runtime simplex")
        return {
            "schema_version": SCENE_RECEIPT_SCHEMA_VERSION,
            "model_name": MODEL_NAME,
            "fixed_dp_head": FIXED_DP_HEAD,
            "training_root_sha256": self.training_root_sha256,
            "training_review_root_sha256": self.training_review_root_sha256,
            "theta_sha256": self.theta_sha256,
            "context_scaler_sha256": self.context_scaler_sha256,
            "phi_sha256": array_sha256(phi),
            "weights_sha256": array_sha256(weights),
            "weights": weights.tolist(),
            "runtime_projection": False,
            "softmax": False,
        }


@dataclass(frozen=True)
class V25RuntimeSelectorAssets:
    """Sealed Static14D and Scene14D assets for one paired evaluation."""

    atom_scales: np.ndarray
    static14d_weights: np.ndarray
    scene14d_weight_provider: V25Scene14DWeightProvider
    training_root_sha256: str
    training_review_root_sha256: str
    atom_scales_sha256: str
    static14d_weights_sha256: str


def load_v25_runtime_selector_assets(
    *,
    training_artifact: Path,
    training_root_sha256: str,
    training_review_artifact: Path,
    training_review_root_sha256: str,
) -> V25RuntimeSelectorAssets:
    """Load both primary CAMP arms from the same sealed training authority."""

    scene_provider = load_v25_scene14d_weight_provider(
        training_artifact=training_artifact,
        training_root_sha256=training_root_sha256,
        training_review_artifact=training_review_artifact,
        training_review_root_sha256=training_review_root_sha256,
    )
    training = Path(training_artifact).resolve()
    scales_path = training / "runtime_atom_scales.json"
    scales_payload = _canonical_json(scales_path)
    from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
    from camp_core.integrations.diffusion_planner_causal_atoms import (
        validate_v25_atom_scales,
    )

    atom_schema, atom_names = atom_schema_for_dimension(14)
    if set(scales_payload) != {
        "schema_version",
        "atom_schema_version",
        "atom_names",
        "scales",
        "scale_source",
        "calibration_or_fresh_consumed",
    } or scales_payload != {
        "schema_version": "camp_dp_v25_runtime_atom_scales_v1",
        "atom_schema_version": atom_schema,
        "atom_names": list(atom_names),
        "scales": scales_payload.get("scales"),
        "scale_source": "sealed_train_only_block_weighted_positive_support",
        "calibration_or_fresh_consumed": False,
    }:
        raise ValueError("V25 runtime atom-scale authority drifted")
    scales = validate_v25_atom_scales(
        _native_numeric(scales_payload["scales"], (14,), "runtime atom scales")
    )

    weights_path = training / "static14d_runtime_weights.npy"
    weights = _native_numeric(
        np.load(weights_path, allow_pickle=False),
        (14,),
        "Static14D runtime weights",
    )
    if (
        np.any(weights < -TRAINED_SIMPLEX_NONNEGATIVE_ATOL)
        or not np.isclose(
            weights.sum(), 1.0, rtol=0.0, atol=TRAINED_SIMPLEX_SUM_ATOL
        )
    ):
        raise ValueError("Static14D runtime weights violated the simplex")
    with np.load(training / "model_parameters.npz", allow_pickle=False) as archive:
        static_theta = _native_numeric(
            archive["static14d_theta"],
            (14, PHI_DIMENSION),
            "Static14D theta",
        )
        stored_runtime = _native_numeric(
            archive["static14d_runtime_weights"],
            (14,),
            "Static14D archived runtime weights",
        )
    if not np.array_equal(weights, static_theta[:, 0]) or not np.array_equal(
        weights, stored_runtime
    ):
        raise ValueError("Static14D runtime weights drifted from sealed Theta")
    model_report = _canonical_json(training / "model_reports.json").get(
        "CAMP-Static14D"
    )
    if (
        type(model_report) is not dict
        or model_report.get("mode") != "static"
        or model_report.get("active_atom_indices") != list(range(14))
        or model_report.get("theta_column_simplex") is not True
        or model_report.get("runtime_projection") is not False
        or model_report.get("softmax") is not False
        or model_report.get("outcome_or_fresh_consumed") is not False
        or model_report.get("theta_sha256")
        != training_parameter_array_sha256(static_theta)
    ):
        raise ValueError("Static14D reviewed model contract drifted")
    return V25RuntimeSelectorAssets(
        atom_scales=scales.copy(),
        static14d_weights=weights.copy(),
        scene14d_weight_provider=scene_provider,
        training_root_sha256=training_root_sha256,
        training_review_root_sha256=training_review_root_sha256,
        atom_scales_sha256=_file_sha256(scales_path),
        static14d_weights_sha256=_file_sha256(weights_path),
    )


def load_v25_scene14d_weight_provider(
    *,
    training_artifact: Path,
    training_root_sha256: str,
    training_review_artifact: Path,
    training_review_root_sha256: str,
) -> V25Scene14DWeightProvider:
    training = Path(training_artifact).resolve()
    review = Path(training_review_artifact).resolve()
    training_seal = verify_complete_seal(
        training,
        _sha256(training_root_sha256, "training_root_sha256"),
        label="V25 CAMP training",
    )
    review_seal = verify_complete_seal(
        review,
        _sha256(training_review_root_sha256, "training_review_root_sha256"),
        label="V25 CAMP training review",
    )
    if (
        set(training_seal["manifest_paths"]) != _TRAINING_FILES
        or set(review_seal["manifest_paths"]) != _REVIEW_FILES
        or (training / "run.exit").read_bytes() != b"0\n"
        or (review / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("V25 Scene14D training/review inventory drifted")

    report = _canonical_json(training / "report.json")
    registry = _canonical_json(training / "model_registry.json")
    model_reports = _canonical_json(training / "model_reports.json")
    review_report = _canonical_json(review / "report.json")
    camp_head = report.get("camp_head")
    if (
        report.get("schema_version") != TRAINING_ARTIFACT_SCHEMA_VERSION
        or report.get("status") != "passed_strict_convex_training"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("all_models_converged") is not True
        or report.get("all_solver_status_optimal") is not True
        or report.get("same_rows_labels_scales_and_block_weights") is not True
        or report.get("selection_eligibility") != "source_valid_candidate_set"
        or report.get("physical_feasible_mask_consumed_by_training") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or report.get("model_reports") != model_reports
        or registry.get("fresh_or_outcome_consumed") is not False
        or review_report.get("schema_version") != TRAINING_REVIEW_SCHEMA_VERSION
        or review_report.get("status")
        != "passed_independent_strict_convex_training_review"
        or review_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(review_report.get("reviewed_artifact"))).resolve() != training
        or review_report.get("reviewed_root_sha256") != training_root_sha256
        or review_report.get("selection_eligibility")
        != "source_valid_candidate_set"
        or review_report.get("physical_feasible_mask_consumed_by_training")
        is not False
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("outcome_fields_consumed") != []
        or review_report.get("phase_remaining_available_count") != 0
        or type(camp_head) is not str
        or len(camp_head) != 40
        or set(camp_head) - _SHA256_CHARS
        or (training / "HEADS").read_bytes()
        != (
            f"camp_head={camp_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
        or (review / "HEADS").read_bytes()
        != (
            f"camp_head={camp_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
        or report.get("runtime_assets")
        != {
            "atom_scales": {
                "relative_path": "runtime_atom_scales.json",
                "sha256": _file_sha256(training / "runtime_atom_scales.json"),
                "model_scope": ["CAMP-Static14D", "CAMP-Scene14D"],
            },
            "static14d_weights": {
                "relative_path": "static14d_runtime_weights.npy",
                "sha256": _file_sha256(
                    training / "static14d_runtime_weights.npy"
                ),
                "model_scope": ["CAMP-Static14D"],
            },
        }
    ):
        raise ValueError("V25 Scene14D training/review authority drifted")
    expected_models = [
        {
            "name": name,
            "parameter_prefix": prefix,
            "mode": mode,
            "active_atom_indices": list(range(atom_count)),
            "primary_method": primary,
            "paper_subset_ablation": ablation,
        }
        for name, prefix, mode, atom_count, primary, ablation in _MODEL_ENTRIES
    ]
    if registry != {
        "schema_version": "camp_dp_v25_model_registry_v1",
        "models": expected_models,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "fresh_or_outcome_consumed": False,
    }:
        raise ValueError("V25 model registry exact contract drifted")
    if set(model_reports) != {entry[0] for entry in _MODEL_ENTRIES} or set(
        review_report.get("models", {})
    ) != {entry[0] for entry in _MODEL_ENTRIES}:
        raise ValueError("V25 reviewed model set drifted")
    model_report = model_reports.get(MODEL_NAME)
    if (
        type(model_report) is not dict
        or model_report.get("mode") != "scene"
        or model_report.get("active_atom_indices") != list(range(14))
        or model_report.get("theta_column_simplex") is not True
        or model_report.get("runtime_projection") is not False
        or model_report.get("softmax") is not False
        or model_report.get("outcome_or_fresh_consumed") is not False
    ):
        raise ValueError("V25 Scene14D model report drifted")

    parameter_path = training / "model_parameters.npz"
    if report.get("model_parameters_sha256") != _file_sha256(parameter_path):
        raise ValueError("V25 Scene14D parameter archive SHA drifted")
    with np.load(parameter_path, allow_pickle=False) as archive:
        if len(archive.files) != len(set(archive.files)) or set(archive.files) != _PARAMETER_KEYS:
            raise ValueError("V25 model parameter archive keyset drifted")
        schema = np.asarray(archive["schema_version"])
        feature_names = np.asarray(archive["context_feature_names"])
        q05 = _native_numeric(archive["context_q05"], (RAW_FEATURE_COUNT,), "q05")
        q95 = _native_numeric(archive["context_q95"], (RAW_FEATURE_COUNT,), "q95")
        theta = _native_numeric(
            archive[f"{MODEL_PARAMETER_PREFIX}_theta"],
            (14, PHI_DIMENSION),
            "Scene14D theta",
        )
    if (
        schema.shape != ()
        or str(schema.item()) != MODEL_PARAMETER_SCHEMA_VERSION
        or feature_names.tolist() != list(RAW_FEATURE_NAMES)
    ):
        raise ValueError("V25 Scene14D parameter metadata drifted")
    theta = validate_column_simplex_theta(theta, num_atoms=14, atol=1e-10)
    if np.any(theta < 0.0):
        raise ValueError("V25 Scene14D runtime Theta must be exactly nonnegative")
    if model_report.get("theta_sha256") != training_parameter_array_sha256(theta):
        raise ValueError("V25 Scene14D Theta SHA drifted")
    scaler = V25ContextScaler(q05=q05, q95=q95)
    return V25Scene14DWeightProvider(
        theta=theta.copy(),
        context_scaler=scaler,
        training_artifact=str(training),
        training_root_sha256=training_root_sha256,
        training_review_artifact=str(review),
        training_review_root_sha256=training_review_root_sha256,
        theta_sha256=array_sha256(theta),
        context_scaler_sha256=_context_scaler_sha256(q05, q95),
    )


def _context_scaler_sha256(q05: np.ndarray, q95: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(b"camp_dp_v25_context_scaler_v1\0")
    for name in RAW_FEATURE_NAMES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
    for value in (q05, q95):
        array = np.ascontiguousarray(value, dtype=np.float64)
        digest.update(array.tobytes())
    return digest.hexdigest()


def training_parameter_array_sha256(value: np.ndarray) -> str:
    """Reproduce the frozen producer SHA for stored training parameters."""

    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(item) for item in array.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON constant {token}")
            ),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid canonical JSON: {path}") from exc
    if type(value) is not dict:
        raise ValueError(f"expected JSON object: {path}")
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
    if raw != expected:
        raise ValueError(f"noncanonical CAMP-authored JSON: {path}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _native_numeric(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{label} must be native numeric with shape {shape}")
    result = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite")
    return result


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - _SHA256_CHARS
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
