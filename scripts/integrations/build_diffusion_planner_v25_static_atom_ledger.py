#!/usr/bin/env python3
"""Build the immutable V25 Stage-A 14D atom semantics ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    CANONICAL_ATOM_CONTRACTS,
    CANONICAL_NORMALIZED_ATOM_CLIP,
    canonical_score_atoms,
)
from scripts.integrations.review_diffusion_planner_v25_stage_a0_authority import (  # noqa: E402
    PASSED_PREFLIGHT_ROOT,
    PASSED_REVIEW_ROOT,
    S01_RELEASE_BASELINE_HEAD,
    S01_SOURCE_HEAD,
    SCHEMA_VERSION as A0_SCHEMA_VERSION,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORRECTED_GENERATION_SCALES,
    FORMAL_ROOT_SHA256,
    RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER,
    RED_SCIENTIFIC_MIN_DISTINCT_SOURCE_MAPS,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _file_sha256,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_static_atom_ledger_v4"
FIXTURE_SCHEMA_VERSION = "camp_dp_v25_static_atom_numeric_fixture_v4"
SOURCE_STATE_ENUM = ("available", "not_applicable", "unavailable", "invalid")
ATOM_NAMES = tuple(DP_CAMP_ATOM_NAMES_V10)
PAPER_9D = tuple(CAMP_ATOM_NAMES)
PLAN = ROOT / "configs" / "integrations" / "diffusion_planner_v25_atom_ledger_plan_v4.json"
A0_REQUIRED_FIELDS = {
    "schema_version", "status", "stage", "stage_a0_code_head",
    "released_s01_source_head", "released_s01_final_baseline_head",
    "fixed_dp_head", "strict_inventory", "probe_authority", "rejected_roots",
    "failed_preflight_role", "existing_3x64_model_rerun", "gpu_work_started",
    "stage_a_authorized", "r_authorized", "training_authorized",
    "calibration_authorized", "scene_runtime_authorized", "fresh_b2_opened",
    "outcome_fields_consumed",
}
DECISION_REQUIRED_FIELDS = {
    "schema_version", "status", "decision_date", "source_thread_id",
    "corrected_source_head", "fixed_dp_head", "s01_preflight_root_sha256",
    "s01_review_root_sha256", "a0_root_sha256", "formal_root_sha256",
    "rejected_roots", "superseded_diagnostic_roots", "progress_reference",
    "progress_formula", "selection_eligibility", "empty_source_valid",
    "candidate0_or_all_k_fallback_allowed", "a1_1_authorized",
    "r0_1_source_authority_preflight_authorized",
    "bounded_21red_1nosignal_x64_authorized_after_source_pass",
    "full_r_authorized", "monitor_authorized", "training_authorized",
    "calibration_authorized", "scene_runtime_authorized", "v2i_authorized",
    "fresh_b2_opened", "outcome_fields_consumed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a0-artifact", type=Path, required=True)
    parser.add_argument("--a0-root-sha256", required=True)
    parser.add_argument("--ultra-decision-artifact", type=Path, required=True)
    parser.add_argument("--ultra-decision-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _canonical_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    Path(path).write_bytes(_canonical_bytes(payload))


def validate_a11_authority_payloads(
    a0_report: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    a0_root_sha256: str,
    current_head: str,
) -> None:
    if (
        set(a0_report) != A0_REQUIRED_FIELDS
        or a0_report.get("schema_version") != A0_SCHEMA_VERSION
        or a0_report.get("status") != "passed"
        or a0_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or a0_report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or a0_report.get("stage_a_authorized") is not True
        or any(
            a0_report.get(key) is not False
            for key in (
                "r_authorized", "training_authorized", "calibration_authorized",
                "scene_runtime_authorized", "fresh_b2_opened",
            )
        )
        or a0_report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("A0 authority exact field/value contract drifted")
    if (
        set(decision) != DECISION_REQUIRED_FIELDS
        or decision.get("schema_version")
        != "camp_dp_v25_ultra_stage_a11_r01_decision_v2"
        or decision.get("status") != "A1_1_R0_1_only_released"
        or decision.get("corrected_source_head") != current_head
        or decision.get("fixed_dp_head") != FIXED_DP_HEAD
        or decision.get("a0_root_sha256") != a0_root_sha256
        or decision.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or decision.get("progress_reference")
        != "source_valid_candidate_set_reference"
        or decision.get("a1_1_authorized") is not True
        or decision.get("r0_1_source_authority_preflight_authorized") is not True
        or decision.get(
            "bounded_21red_1nosignal_x64_authorized_after_source_pass"
        ) is not True
        or any(
            decision.get(key) is not False
            for key in (
                "full_r_authorized", "monitor_authorized", "training_authorized",
                "calibration_authorized", "scene_runtime_authorized", "v2i_authorized",
                "fresh_b2_opened",
            )
        )
        or decision.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Ultra A1.1/R0.1 decision exact field/value contract drifted")


def _source_policy(name: str) -> dict[str, str]:
    always = {
        "jerk_early",
        "jerk_late",
        "jerk_full",
        "rms_acceleration",
        "planned_lateral_acceleration_cost",
        "dp_prior_jerk_excess_cost",
    }
    signal = {"planned_red_light_cost", "red_stopping_margin_cost"}
    if name in always:
        return {
            "available": "fixed K=8 same-call candidate tensor and required invariants are valid",
            "not_applicable": "not permitted; the atom is defined for every valid fixed K=8 call",
            "unavailable": "candidate tensor or required same-call operational-default receipt absent; source mask false",
            "invalid": "nonfinite, malformed K8, heading, or candidate0-SHA invariant failure; fail closed",
        }
    if name in signal:
        return {
            "available": "mapped current TrafficLightRegulatoryElement, physical light, controlled lanelet, stop line, route arc, and same-tick phase receipt valid",
            "not_applicable": "route has no controlling signal after valid regulatory census; legal atom zero",
            "unavailable": "a controlling signal is expected but current phase or regulatory mapping source is absent; source mask false, never legal zero",
            "invalid": "wrong/mismatched light, lanelet, stop line, route arc, phase, timestamp, or future/replayed/stale source; fail closed",
        }
    return {
        "available": "required same-call K8 and current static/current-state sources are valid",
        "not_applicable": "only an explicitly validated scene-semantic absence may produce a legal zero",
        "unavailable": "required causal source is absent; source mask false",
        "invalid": "present source violates mapping, finite, schema, or invariant contract; fail closed",
    }


def _dependencies(name: str) -> dict[str, Any]:
    speed = name.startswith("speed_limit_margin_")
    signal = name in {"planned_red_light_cost", "red_stopping_margin_cost"}
    return {
        "k8": "all candidates" if name == "progress_shortfall" else "per candidate in fixed K=8",
        "candidate0": (
            "per-tick operational-default alias SHA reference; not native-ranked Top-1 and not a second forward"
            if name == "dp_prior_jerk_excess_cost"
            else "none"
        ),
        "route": name in {
            "speed_limit_margin_0_0",
            "speed_limit_margin_0_5",
            "speed_limit_margin_1_0",
            "lane_deviation",
            "progress_shortfall",
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        },
        "lane": name in {
            "lane_deviation",
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        },
        "neighbor": (
            "candidate-specific same-call DP neighbor predictions plus current static obstacles"
            if name == "clearance"
            else "none"
        ),
        "signal": (
            "mapped current phase and complete regulatory/stop-line/route receipt"
            if signal
            else "none"
        ),
        "speed_rule": "current route-segment speed rule" if speed else "none",
    }


def _monotonicity(name: str) -> str:
    if name.startswith("speed_limit_margin_"):
        return "nondecreasing in positive candidate-speed excess with route limits fixed"
    if name == "lane_deviation":
        return "nondecreasing in positive boundary exceedance with lane geometry fixed"
    if name == "clearance":
        return "nondecreasing in positive safety-distance shortfall with obstacle predictions fixed"
    if name == "progress_shortfall":
        return "nondecreasing as candidate route progress decreases for a fixed valid reference set"
    if name == "planned_red_light_cost":
        return "nondecreasing in the positive hinge of the same-call planned-red reward cost under a fixed mapped current phase"
    if name == "red_stopping_margin_cost":
        return "nondecreasing in positive stopping-envelope speed excess with current mapped red geometry fixed"
    if name == "dp_prior_jerk_excess_cost":
        return "nondecreasing in positive mean-jerk excess over the verified candidate0 reference"
    return "nondecreasing in the declared nonnegative kinematic norm/energy with all other inputs fixed"


def _atom_rows(
    scales: list[float],
    scale_sha256: str,
    warning_contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    contracts = {contract.name: contract for contract in CANONICAL_ATOM_CONTRACTS}
    if tuple(contracts) != ATOM_NAMES:
        raise ValueError("canonical atom contract order drifted")
    rows = []
    if (
        not isinstance(warning_contract, Mapping)
        or any(name not in ATOM_NAMES for name in warning_contract)
        or any(
            not isinstance(value, str) or not value
            for value in warning_contract.values()
        )
    ):
        raise ValueError("Stage A warning contract is invalid")
    for index, name in enumerate(ATOM_NAMES):
        contract = contracts[name]
        formula = contract.formula
        if name == "jerk_full":
            formula += "; exact production partition requires jerk_full=jerk_early+jerk_late"
        row = {
            "index": index,
            "name": name,
            "paper_9d_member": index < 9,
            "paper_mapping": "canonical_14d_prefix" if index < 9 else "DP_fixed-candidate_extension",
            "formula": formula,
            "unit": contract.unit,
            "dt_contract": "dt=0.1 s; finite and strictly positive; the same dt is used throughout each formula",
            "finite_contract": "every raw coefficient and intermediate must be finite; NaN/Inf fails closed",
            "nonnegative_contract": "raw atom is >=0 on its declared validity domain",
            "raw_bounds": {
                "lower_inclusive": 0.0,
                "upper": None,
                "upper_contract": "unbounded before normalization but finite is mandatory",
            },
            "generation_behavior_scale": {
                "value": scales[index],
                "file": str(CORRECTED_GENERATION_SCALES),
                "file_sha256": scale_sha256,
                "provenance": (
                    "V25 semantic dimensionless floor replacing degenerate legacy 1e-6"
                    if name == "planned_red_light_cost"
                    else "legacy V18 generation behavior scale/floor carried only for corrected-corpus behavior"
                ),
                "not_final_training_scale": True,
            },
            "normalized_clip": {
                "formula": "z=clip(raw_atom/generation_behavior_scale,0,10)",
                "lower": 0.0,
                "upper": CANONICAL_NORMALIZED_ATOM_CLIP,
            },
            "causal_source_class": list(contract.inputs),
            "decision_time_availability": contract.decision_time_availability,
            "source_state_policy": _source_policy(name),
            "invalid_policy": "fail closed; invalid is never converted to zero or uniform fallback",
            "mask_policy": "unavailable is source-masked; not_applicable may be zero only where this row explicitly allows it",
            "monotonicity_domain": _monotonicity(name),
            **{
                f"{key}_dependency": value
                for key, value in _dependencies(name).items()
            },
            "forbidden_sources": [
                "closed-loop outcome",
                "GT/observed future",
                "Fresh or holdout membership/data",
                "map/route/scenario/split/seed ID or proxy as a model feature",
                "private DP latent",
                "future signal schedule",
            ],
            "legal_zero_fixture": f"numeric_fixture.raw_atoms[3][{index}]==0",
            "legal_positive_fixture": f"numeric_fixture.raw_atoms[0][{index}]>0",
            "candidate_distinguishing_fixture": f"numeric_fixture column {index} has at least two distinct K8 values",
            "status": "WARN" if name in warning_contract else "PASS",
            "warning": warning_contract.get(name),
        }
        rows.append(row)
    return rows


def _numeric_fixture(scales: np.ndarray) -> dict[str, Any]:
    normalized_pattern = np.asarray(
        [[value] * 14 for value in (5.0, 4.0, 3.0, 0.0, 1.0, 1.0, 2.0, 12.0)],
        dtype=np.float64,
    )
    atoms = normalized_pattern * scales.reshape(1, -1)
    weights = np.arange(1.0, 15.0, dtype=np.float64)
    weights /= weights.sum()
    normalized, scores = canonical_score_atoms(atoms, scales, weights)
    source_valid = np.array([True, True, True, False, True, True, False, True])
    physical_feasible = np.array([True, False, True, False, False, False, False, False])
    eligible_scores = np.where(source_valid, scores, np.inf)
    selected = int(np.argmin(eligible_scores))
    candidate_sha256 = []
    candidate_tensors = []
    candidate_atom_binding_sha256 = []
    for index in range(8):
        candidate = np.zeros((80, 4), dtype=np.float32)
        candidate[:, 0] = np.linspace(0.0, 20.0 + index, 80, dtype=np.float32)
        candidate[:, 1] = np.float32(index * 0.1)
        candidate[:, 2] = 1.0
        candidate_tensors.append(candidate.tolist())
        candidate_sha256.append(hashlib.sha256(candidate.tobytes()).hexdigest())
        candidate_atom_binding_sha256.append(
            hashlib.sha256(
                candidate.tobytes() + _canonical_bytes(atoms[index].tolist())
            ).hexdigest()
        )
    progress = np.array([5.0, 10.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0])
    atom_source_valid = np.ones((8, 14), dtype=np.bool_)
    atom_applicable = np.ones((8, 14), dtype=np.bool_)
    atom_applicable[:, 10] = False
    atom_applicable[:, 12] = False
    lane_offsets = np.array([[1.5, -1.5, 0.25], [-2.0, 2.0, 0.0]])
    left_widths = np.array([[1.0, 1.0, 1.0], [0.75, 0.75, 0.75]])
    right_widths = np.array([[2.0, 2.0, 2.0], [1.25, 1.25, 1.25]])
    lane_expected = 0.1 * np.sum(
        np.where(
            lane_offsets >= 0.0,
            np.maximum(lane_offsets - left_widths, 0.0),
            np.maximum(-lane_offsets - right_widths, 0.0),
        )
        ** 2,
        axis=1,
    )
    obb_surface_clearance = np.array(
        [[4.0, 2.0, 0.5, 3.0], [1.0, 1.5, 2.5, 5.0]], dtype=np.float64
    )
    clearance_expected = 0.1 * np.sum(
        np.maximum(3.0 - obb_surface_clearance, 0.0) ** 2, axis=1
    )

    def reference_fixture(mask: np.ndarray) -> dict[str, Any]:
        if not mask.any():
            return {"status": "invalid_no_reference", "cost": None}
        reference = float(np.max(progress[mask]))
        return {
            "status": "available",
            "reference_progress_m": reference,
            "cost": np.maximum(reference - progress, 0.0).tolist(),
        }

    return {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "raw_atoms": atoms.tolist(),
        "scales": scales.tolist(),
        "weights": weights.tolist(),
        "source_valid_mask": source_valid.tolist(),
        "physical_feasible_mask": physical_feasible.tolist(),
        "atom_source_valid_mask": atom_source_valid.tolist(),
        "atom_applicable_mask": atom_applicable.tolist(),
        "production_normalized_atoms": normalized.tolist(),
        "production_scores": scores.tolist(),
        "production_selected_index": selected,
        "tie_break": "lowest eligible candidate index",
        "candidate_sha256": candidate_sha256,
        "candidate_tensors": candidate_tensors,
        "candidate_atom_binding_sha256": candidate_atom_binding_sha256,
        "paper_9d_prefix": atoms[:, :9].tolist(),
        "asymmetric_lane_fixture": {
            "dt_s": 0.1,
            "signed_offset_m": lane_offsets.tolist(),
            "left_width_m": left_widths.tolist(),
            "right_width_m": right_widths.tolist(),
            "expected_cost": lane_expected.tolist(),
        },
        "candidate_specific_obb_clearance_fixture": {
            "dt_s": 0.1,
            "threshold_m": 3.0,
            "minimum_obb_surface_clearance_m": obb_surface_clearance.tolist(),
            "expected_cost": clearance_expected.tolist(),
        },
        "progress_reference_adversarial": {
            "candidate_progress_m": progress.tolist(),
            "mixed_source_valid_mask": [True, True, True, False, True, False, False, True],
            "mixed_physical_feasible_mask": [True, False, True, False, False, False, False, False],
            "source_valid_option": reference_fixture(
                np.array([True, True, True, False, True, False, False, True])
            ),
            "physical_feasible_option": reference_fixture(
                np.array([True, False, True, False, False, False, False, False])
            ),
            "all_k_high_risk": {
                "source_valid_mask": [True] * 8,
                "physical_feasible_mask": [False] * 8,
                "source_valid_option": reference_fixture(np.ones(8, dtype=bool)),
                "physical_feasible_option": reference_fixture(np.zeros(8, dtype=bool)),
            },
            "no_reference": {
                "source_valid_mask": [False] * 8,
                "physical_feasible_mask": [False] * 8,
                "source_valid_option": reference_fixture(np.zeros(8, dtype=bool)),
                "physical_feasible_option": reference_fixture(np.zeros(8, dtype=bool)),
            },
            "candidate0_or_all_k_fallback_allowed": False,
        },
    }


def _scale_diagnostic(scales: list[float]) -> dict[str, Any]:
    rows = []
    for index, (name, scale) in enumerate(zip(ATOM_NAMES, scales, strict=True)):
        rows.append(
            {
                "index": index,
                "name": name,
                "generation_behavior_scale": scale,
                "legal_zero_fixture": True,
                "legal_positive_fixture": True,
                "s01_192_tick_raw_zero_count": None,
                "s01_192_tick_raw_positive_count": None,
                "s01_192_tick_clip_saturation_count": None,
                "missing_reason": "sealed S0.1 records only per-tick atom/normalized hashes and aggregate above-clip counts, not per-atom raw values",
            }
        )
    return {
        "role": "S0 diagnostic only; not train empirical evidence",
        "per_atom": rows,
        "available_aggregate": {
            "probe_raw_values_above_clip_counts": [839, 839, 1536],
            "total": 3214,
            "denominator": 3 * 64 * 8 * 14,
            "per_atom_attribution_available": False,
        },
        "three_1e_6_scales": [
            "speed_limit_margin_0_0",
            "speed_limit_margin_0_5",
            "lane_deviation",
        ],
        "three_1e_6_explanation": "legacy zero/near-zero-support generation floors; they are not estimates of empirical training scale and require Stage-B positive-support estimation",
        "planned_red_light_scale_1": "generation-only semantic floor replacing a degenerate 1e-6 scale; continuous/binary train definitions remain an E1 decision after Stage B",
        "red_stopping_scale_4_95e_4": "legacy support-sensitive generation scale retained for corrected-corpus behavior only; sparse positive support prevents treating it as a final training scale",
    }


def _training_scale_freeze() -> dict[str, Any]:
    return {
        "stage": "B sealed corrected train only; calibration/Fresh/outcomes forbidden",
        "continuous_estimator": "weighted q95 of strictly positive finite raw atom values among source-valid applicable candidate rows",
        "quantile": 0.95,
        "minimum_positive_support": {
            "unique_source-independent_semantic_blocks": 20,
            "positive_candidate_rows": 128,
        },
        "zero_support": "no continuous estimate; mark support-limited and block silent substitution/removal",
        "mask": "source-valid and applicable only; unavailable/invalid rows excluded with denominators reported; physical feasibility is not a general scale mask",
        "red_binary_alternative": "pre-registered 1(raw_atom>0) with scale 1.0, reported beside continuous definition; it does not automatically replace the main atom",
        "block_weighting": "equal total mass per source-independent semantic block, then equal route identity, seed, tick, and eligible candidate mass within each parent",
        "generation_floor_is_training_estimate": False,
        "calibration_may_refit_scale": False,
        "semantic_clone_hash": _load_json(PLAN)["semantic_clone_contract"],
    }


def _dag_contract() -> dict[str, Any]:
    return {
        "S0_to_A": "Ultra S0.1 PASS plus A0 strict-inventory supplement PASS",
        "A_exit": "14 rows complete; independent semantics/numeric validation PASS; source-valid progress reference frozen",
        "R0_1_entry": "A1.1 PASS plus sealed Ultra A1.1/R0.1 decision; full R remains closed",
        "R_entry": "Ultra first releases only a sealed 1500-config preflight; independent review and a distinct Ultra execute release are then mandatory",
        "R_exit": "1500x64 sequential corpus sealed and independently reviewed; red scientific coverage passes; then stop",
        "B_entry": "R sealed+reviewed and Ultra-released; train-only empirical audit only",
        "C_entry": "B PASS and Ultra release; outcome-blind seven-family single-axis perturbations",
        "C_exit": "expected atom activation/direction/source completeness reported PASS/WARN/FAIL; no outcome-selected parameters",
        "D_entry": "B PASS and Ultra release; focused algebra/source audit may run read-only in parallel with C only if released",
        "D_exit": "jerk/speed/lane-clearance/red/lateral findings classified by remediation class and combined review sealed",
        "E1_entry": "C and D combined review PASS plus Ultra release",
        "training_calibration_fresh": "E1 -> T/E2 -> Q -> one-shot F -> E3; each Ultra-gated",
        "outcome_red_10m_heuristic_gate": "must be replaced or independently certified before calibration or Fresh B2 pre-open",
        "current_authority": "A1.1/R0.1 bounded only; full R/B/C/D/E/T/Q/F remain closed",
    }


def build_ledger(
    *,
    a0_artifact: Path,
    a0_root_sha256: str,
    ultra_decision_artifact: Path,
    ultra_decision_root_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    a0_seal = verify_complete_seal(
        a0_artifact,
        a0_root_sha256,
        label="V25 Stage A0 supplement",
    )
    a0_report = _load_json(a0_artifact / "report.json")
    decision_seal = verify_complete_seal(
        ultra_decision_artifact,
        ultra_decision_root_sha256,
        label="V25 Ultra Stage-A decision",
    )
    decision = _load_json(ultra_decision_artifact / "decision.json")
    validate_a11_authority_payloads(
        a0_report,
        decision,
        a0_root_sha256=a0_seal["root_sha256"],
        current_head=current_head,
    )
    if (a0_artifact / "run.exit").read_text(encoding="ascii") != "0\n" or (
        ultra_decision_artifact / "run.exit"
    ).read_text(encoding="ascii") != "0\n":
        raise ValueError("A0/Ultra authority run.exit is not zero")
    if (a0_artifact / "HEADS").read_text(encoding="ascii").splitlines() != [
        f"camp_head={a0_report['stage_a0_code_head']}",
        f"fixed_dp_head={FIXED_DP_HEAD}",
    ] or (ultra_decision_artifact / "HEADS").read_text(
        encoding="ascii"
    ).splitlines() != [
        f"camp_head={current_head}", f"fixed_dp_head={FIXED_DP_HEAD}"
    ]:
        raise ValueError("A0/Ultra authority HEADS binding drifted")
    scale_payload = _load_json(CORRECTED_GENERATION_SCALES)
    scales = scale_payload.get("scales")
    if (
        scale_payload.get("schema_version")
        != "camp_dp_v25_generation_behavior_atom_scales_v2"
        or scale_payload.get("atom_names") != list(ATOM_NAMES)
        or not isinstance(scales, list)
        or len(scales) != 14
        or not np.isfinite(np.asarray(scales, dtype=np.float64)).all()
        or np.any(np.asarray(scales, dtype=np.float64) <= 0.0)
    ):
        raise ValueError("generation behavior scale contract drifted")
    scale_sha256 = _file_sha256(CORRECTED_GENERATION_SCALES)
    plan = _load_json(PLAN)
    if (
        plan.get("schema_version") != "camp_dp_v25_atom_ledger_plan_v4"
        or not isinstance(plan.get("warning_contract"), Mapping)
    ):
        raise ValueError("Stage A1 plan schema drifted")
    rows = _atom_rows(scales, scale_sha256, plan["warning_contract"])
    if plan.get("required_row_fields") != list(rows[0]):
        raise ValueError("Stage A1 flat row-field schema drifted")
    ordered_contract = {
        "schema_version": SCHEMA_VERSION,
        "atom_schema": "dp_camp_v10_14d",
        "ordered_atom_names": list(ATOM_NAMES),
        "paper_9d_indices": list(range(9)),
        "required_row_fields": plan["required_row_fields"],
        "rows": rows,
    }
    fixture = _numeric_fixture(np.asarray(scales, dtype=np.float64))
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_with_warnings_progress_source_valid_frozen",
        "stage": "A_static_atom_semantics",
        "authority": {
            "s01_source_head": S01_SOURCE_HEAD,
            "s01_release_baseline_head": S01_RELEASE_BASELINE_HEAD,
            "stage_a_producer_head": current_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "s01_preflight_root_sha256": PASSED_PREFLIGHT_ROOT,
            "s01_review_root_sha256": PASSED_REVIEW_ROOT,
            "formal_source_root_sha256": FORMAL_ROOT_SHA256,
            "a0_artifact": str(a0_artifact),
            "a0_root_sha256": a0_seal["root_sha256"],
            "ultra_decision_artifact": str(ultra_decision_artifact),
            "ultra_decision_root_sha256": decision_seal["root_sha256"],
            "plan_path": str(PLAN),
            "plan_sha256": _file_sha256(PLAN),
            "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        },
        "atom_schema": "dp_camp_v10_14d",
        "paper_9d_contract": "exact canonical 14D[0:9] prefix",
        "source_state_enum": list(SOURCE_STATE_ENUM),
        "ordered_schema_formula_sha256": _canonical_sha256(ordered_contract),
        "ordered_schema_formula_payload": ordered_contract,
        "atoms": rows,
        "progress_shortfall_decision": {
            "status": "frozen_by_Ultra",
            "reference": "source_valid_candidate_set_reference",
            "formula": "r=max(progress[j] where source_valid[j]); progress_shortfall[k]=max(r-progress[k],0)",
            "selection_eligibility": "source_valid",
            "empty_source_valid": "fail_closed",
            "not_frozen": False,
            "candidate0_or_all_k_fallback_allowed": False,
        },
        "generation_scale_diagnostic": _scale_diagnostic(scales),
        "training_scale_estimator_freeze": _training_scale_freeze(),
        "red_signal_contract": {
            "required_receipt": [
                "TrafficLightRegulatoryElement",
                "physical light id",
                "controlled lanelet id",
                "stop-line geometry",
                "route-intersection arc mapping",
                "same-tick current phase",
                "world-to-ego transform bound to stop-line/source-chain/runtime-receipt SHA",
            ],
            "no_signal_legal_zero_distinct_from_missing_source": True,
            "phase_remaining_no_v2i": "unavailable/source-masked and never read from frozen tier/future schedule",
            "v2i": "separate future gate requiring per-tick timestamps/freshness/wrong-id/phase/replay/future/stale tests",
            "outcome_evaluator_10m_nearest_line_heuristic": "calibration/Fresh B2 pre-open hard gate; not accepted as regulatory authority",
        },
        "passive_latency_instrumentation": {
            "semantic_change": False,
            "stages_ms": [
                "dp_default_forward", "extra_k8_generation", "atom_materialization",
                "causal_context", "static_selector", "tracker", "total_tick",
            ],
            "statistics": ["mean", "median", "p95", "p99", "max"],
            "clock": "monotonic perf_counter_ns around existing sequential stages",
            "microbatch_cache_sharding_enabled": False,
        },
        "r_red_scientific_coverage_freeze": {
            "formal_executable_identity_count": 21,
            "formal_by_tier": {"easy": 6, "borderline": 10, "high_risk": 5},
            "formal_distinct_source_map_count": 4,
            "minimum_complete_by_tier": dict(RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER),
            "minimum_distinct_source_maps": RED_SCIENTIFIC_MIN_DISTINCT_SOURCE_MAPS,
            "all_21_retained_capability_failures_scientifically_pass": False,
            "retained_failures_remain_in_denominator": True,
            "failure_disposition": "artifact scientifically_ineligible; B/training blocked even if count is below capability cap 32",
        },
        "dag_contract": plan["dag"],
        "stage_boundaries": {
            "r_authorized": False,
            "full_corpus_started": False,
            "training_executed": False,
            "calibration_executed": False,
            "scene_runtime_connected": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
    }
    return ledger, fixture


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    try:
        ledger, fixture = build_ledger(
            a0_artifact=args.a0_artifact,
            a0_root_sha256=args.a0_root_sha256,
            ultra_decision_artifact=args.ultra_decision_artifact,
            ultra_decision_root_sha256=args.ultra_decision_root_sha256,
        )
        _write_json(args.output_dir / "atom_ledger.json", ledger)
        _write_json(args.output_dir / "numeric_fixture.json", fixture)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={ledger['authority']['stage_a_producer_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root_sha256 = seal_artifact(args.output_dir, label="V25 Stage A ledger")
        print(
            json.dumps(
                {
                    "status": ledger["status"],
                    "atom_count": len(ledger["atoms"]),
                    "root_sha256": root_sha256,
                    "output_dir": str(args.output_dir),
                },
                sort_keys=True,
            )
        )
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 Stage A failed ledger")
        raise


if __name__ == "__main__":
    main()
