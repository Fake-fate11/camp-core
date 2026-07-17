#!/usr/bin/env python3
"""Independently validate the V25 Stage-A atom ledger and numeric fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
)
from scripts.integrations.review_diffusion_planner_v25_stage_a0_authority import (  # noqa: E402
    PASSED_PREFLIGHT_ROOT,
    PASSED_REVIEW_ROOT,
    S01_RELEASE_BASELINE_HEAD,
    S01_SOURCE_HEAD,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORRECTED_GENERATION_SCALES,
    FORMAL_ROOT_SHA256,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _file_sha256,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_static_atom_ledger_validation_v4"
LEDGER_SCHEMA_VERSION = "camp_dp_v25_static_atom_ledger_v4"
FIXTURE_SCHEMA_VERSION = "camp_dp_v25_static_atom_numeric_fixture_v4"
ATOM_NAMES = tuple(DP_CAMP_ATOM_NAMES_V10)
PLAN = ROOT / "configs" / "integrations" / "diffusion_planner_v25_atom_ledger_plan_v4.json"
REQUIRED_ROW_FIELDS = (
        "index",
        "name",
        "paper_9d_member",
        "paper_mapping",
        "formula",
        "unit",
        "dt_contract",
        "finite_contract",
        "nonnegative_contract",
        "raw_bounds",
        "generation_behavior_scale",
        "normalized_clip",
        "causal_source_class",
        "decision_time_availability",
        "source_state_policy",
        "invalid_policy",
        "mask_policy",
        "monotonicity_domain",
        "k8_dependency",
        "candidate0_dependency",
        "route_dependency",
        "lane_dependency",
        "neighbor_dependency",
        "signal_dependency",
        "speed_rule_dependency",
        "forbidden_sources",
        "legal_zero_fixture",
        "legal_positive_fixture",
        "candidate_distinguishing_fixture",
        "status",
        "warning",
)
REQUIRED_ROW_KEYS = frozenset(REQUIRED_ROW_FIELDS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger-artifact", type=Path, required=True)
    parser.add_argument("--ledger-root-sha256", required=True)
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


def _expected_source_policy(name: str) -> dict[str, str]:
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


def _expected_dependencies(name: str) -> dict[str, Any]:
    speed = name.startswith("speed_limit_margin_")
    signal = name in {"planned_red_light_cost", "red_stopping_margin_cost"}
    return {
        "k8_dependency": "all candidates" if name == "progress_shortfall" else "per candidate in fixed K=8",
        "candidate0_dependency": (
            "per-tick operational-default alias SHA reference; not native-ranked Top-1 and not a second forward"
            if name == "dp_prior_jerk_excess_cost"
            else "none"
        ),
        "route_dependency": name
        in {
            "speed_limit_margin_0_0",
            "speed_limit_margin_0_5",
            "speed_limit_margin_1_0",
            "lane_deviation",
            "progress_shortfall",
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        },
        "lane_dependency": name
        in {"lane_deviation", "planned_red_light_cost", "red_stopping_margin_cost"},
        "neighbor_dependency": (
            "candidate-specific same-call DP neighbor predictions plus current static obstacles"
            if name == "clearance"
            else "none"
        ),
        "signal_dependency": (
            "mapped current phase and complete regulatory/stop-line/route receipt"
            if signal
            else "none"
        ),
        "speed_rule_dependency": "current route-segment speed rule" if speed else "none",
    }


def _expected_monotonicity(name: str) -> str:
    exact = {
        "lane_deviation": "nondecreasing in positive boundary exceedance with lane geometry fixed",
        "clearance": "nondecreasing in positive safety-distance shortfall with obstacle predictions fixed",
        "progress_shortfall": "nondecreasing as candidate route progress decreases for a fixed valid reference set",
        "planned_red_light_cost": "nondecreasing in the positive hinge of the same-call planned-red reward cost under a fixed mapped current phase",
        "red_stopping_margin_cost": "nondecreasing in positive stopping-envelope speed excess with current mapped red geometry fixed",
        "dp_prior_jerk_excess_cost": "nondecreasing in positive mean-jerk excess over the verified candidate0 reference",
    }
    if name.startswith("speed_limit_margin_"):
        return "nondecreasing in positive candidate-speed excess with route limits fixed"
    return exact.get(
        name,
        "nondecreasing in the declared nonnegative kinematic norm/energy with all other inputs fixed",
    )


def _derive_atom_status(name: str, warning_contract: Mapping[str, Any]) -> tuple[str, Any]:
    warning = warning_contract.get(name)
    return ("WARN", warning) if warning is not None else ("PASS", None)


def _independent_numeric_recompute(fixture: Mapping[str, Any]) -> dict[str, Any]:
    raw = fixture.get("raw_atoms")
    scales = fixture.get("scales")
    weights = fixture.get("weights")
    source_valid = fixture.get("source_valid_mask")
    physical = fixture.get("physical_feasible_mask")
    atom_source = np.asarray(fixture.get("atom_source_valid_mask"))
    atom_applicable = np.asarray(fixture.get("atom_applicable_mask"))
    candidate_tensors = fixture.get("candidate_tensors")
    if (
        not isinstance(raw, list)
        or len(raw) != 8
        or any(not isinstance(row, list) or len(row) != 14 for row in raw)
        or not isinstance(scales, list)
        or len(scales) != 14
        or not isinstance(weights, list)
        or len(weights) != 14
        or not isinstance(source_valid, list)
        or len(source_valid) != 8
        or not isinstance(physical, list)
        or len(physical) != 8
        or any(type(value) is not bool for value in source_valid + physical)
        or not isinstance(candidate_tensors, list)
        or len(candidate_tensors) != 8
        or atom_source.dtype != np.bool_
        or atom_applicable.dtype != np.bool_
        or atom_source.shape != (8, 14)
        or atom_applicable.shape != (8, 14)
        or np.any(atom_applicable & ~atom_source)
    ):
        raise ValueError("numeric fixture shape or masks are invalid")
    numbers = [float(value) for row in raw for value in row]
    scale_values = [float(value) for value in scales]
    weight_values = [float(value) for value in weights]
    if (
        not all(math.isfinite(value) and value >= 0.0 for value in numbers)
        or not all(math.isfinite(value) and value > 0.0 for value in scale_values)
        or not all(math.isfinite(value) and value >= 0.0 for value in weight_values)
        or not math.isclose(sum(weight_values), 1.0, rel_tol=0.0, abs_tol=1e-12)
    ):
        raise ValueError("numeric fixture values violate finite/simplex contracts")
    normalized: list[list[float]] = []
    scores: list[float] = []
    for candidate in range(8):
        row = []
        score = 0.0
        for atom in range(14):
            value = float(raw[candidate][atom]) / scale_values[atom]
            clipped = min(max(value, 0.0), 10.0)
            row.append(clipped)
            score += clipped * weight_values[atom]
        normalized.append(row)
        scores.append(score)
    eligible = [index for index, valid in enumerate(source_valid) if valid]
    if not eligible:
        raise ValueError("numeric fixture has no eligible candidate")
    selected = min(eligible, key=lambda index: (scores[index], index))
    recomputed_candidate_sha = []
    recomputed_binding_sha = []
    for index, candidate in enumerate(candidate_tensors):
        values = np.asarray(candidate, dtype=np.float32)
        if values.shape != (80, 4) or not np.isfinite(values).all():
            raise ValueError("numeric fixture candidate tensor is invalid")
        recomputed_candidate_sha.append(hashlib.sha256(values.tobytes()).hexdigest())
        recomputed_binding_sha.append(
            hashlib.sha256(
                values.tobytes() + _canonical_bytes(raw[index])
            ).hexdigest()
        )
    stored_normalized = np.asarray(
        fixture.get("production_normalized_atoms"), dtype=np.float64
    )
    stored_scores = np.asarray(fixture.get("production_scores"), dtype=np.float64)
    if stored_normalized.shape != (8, 14) or stored_scores.shape != (8,):
        raise ValueError("stored production numeric evidence shape drifted")
    lane = fixture.get("asymmetric_lane_fixture", {})
    offsets = np.asarray(lane.get("signed_offset_m"), dtype=np.float64)
    left = np.asarray(lane.get("left_width_m"), dtype=np.float64)
    right = np.asarray(lane.get("right_width_m"), dtype=np.float64)
    lane_expected = float(lane.get("dt_s", float("nan"))) * np.sum(
        np.where(
            offsets >= 0.0,
            np.maximum(offsets - left, 0.0),
            np.maximum(-offsets - right, 0.0),
        )
        ** 2,
        axis=1,
    )
    clearance = fixture.get("candidate_specific_obb_clearance_fixture", {})
    surfaces = np.asarray(
        clearance.get("minimum_obb_surface_clearance_m"), dtype=np.float64
    )
    clearance_expected = float(clearance.get("dt_s", float("nan"))) * np.sum(
        np.maximum(
            float(clearance.get("threshold_m", float("nan"))) - surfaces,
            0.0,
        )
        ** 2,
        axis=1,
    )
    checks = {
        "normalized_exact": bool(
            np.allclose(
                np.asarray(normalized),
                stored_normalized,
                rtol=0.0,
                atol=1e-12,
            )
        ),
        "scores_exact": bool(
            np.allclose(np.asarray(scores), stored_scores, rtol=0.0, atol=1e-12)
        ),
        "selected_index_exact": fixture.get("production_selected_index") == selected,
        "tie_break_exact": fixture.get("tie_break")
        == "lowest eligible candidate index",
        "paper_9d_prefix_exact": np.array_equal(
            np.asarray(fixture.get("paper_9d_prefix"), dtype=np.float64),
            np.asarray(raw, dtype=np.float64)[:, :9],
        ),
        "candidate_sha_count_and_format": (
            isinstance(fixture.get("candidate_sha256"), list)
            and len(fixture["candidate_sha256"]) == 8
            and len(set(fixture["candidate_sha256"])) == 8
            and all(
                isinstance(value, str)
                and len(value) == 64
                and not set(value) - set("0123456789abcdef")
                for value in fixture["candidate_sha256"]
            )
        ),
        "candidate_sha_recomputed": fixture.get("candidate_sha256")
        == recomputed_candidate_sha,
        "candidate_atom_binding_recomputed": fixture.get(
            "candidate_atom_binding_sha256"
        )
        == recomputed_binding_sha,
        "all_atoms_have_zero_positive_and_k8_difference": all(
            any(float(raw[candidate][atom]) == 0.0 for candidate in range(8))
            and any(float(raw[candidate][atom]) > 0.0 for candidate in range(8))
            and len({float(raw[candidate][atom]) for candidate in range(8)}) > 1
            for atom in range(14)
        ),
        "mixed_masks_are_distinct": source_valid != physical,
        "physical_is_subset_of_source_valid": all(
            not physical[index] or source_valid[index] for index in range(8)
        ),
        "masked_lower_score_cannot_win": scores[3] < scores[selected]
        and source_valid[3] is False,
        "lowest_index_tie_is_nontrivial": selected == 4
        and source_valid[4] is True
        and source_valid[5] is True
        and math.isclose(scores[4], scores[5], rel_tol=0.0, abs_tol=1e-12),
        "atom_source_applicability_masks_exact": not np.any(
            atom_applicable & ~atom_source
        ),
        "asymmetric_lane_formula_recomputed": np.allclose(
            lane_expected,
            np.asarray(lane.get("expected_cost"), dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
        ),
        "candidate_specific_obb_clearance_recomputed": np.allclose(
            clearance_expected,
            np.asarray(clearance.get("expected_cost"), dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
        ),
    }
    if not all(checks.values()):
        raise ValueError(
            "independent numeric fixture failed: "
            + ",".join(name for name, passed in checks.items() if not passed)
        )
    return {
        "checks": checks,
        "independent_normalized_sha256": _canonical_sha256(normalized),
        "independent_scores_sha256": _canonical_sha256(scores),
        "independent_selected_index": selected,
        "implementation": "explicit scalar raw/scale clipping, affine sum, eligible argmin, and lowest-index tie; production score helpers not imported",
    }


def _validate_progress_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    progress = fixture.get("progress_reference_adversarial")
    if not isinstance(progress, Mapping):
        raise ValueError("progress adversarial fixture is missing")
    values = progress.get("candidate_progress_m")
    if not isinstance(values, list) or len(values) != 8:
        raise ValueError("progress candidate vector is invalid")

    def recompute(
        container: Mapping[str, Any], mask_key: str, option_key: str
    ) -> dict[str, Any]:
        mask = container.get(mask_key)
        stored = container.get(option_key)
        if not isinstance(mask, list) or len(mask) != 8 or not isinstance(stored, Mapping):
            raise ValueError("progress mixed-mask fixture is invalid")
        if any(type(value) is not bool for value in mask):
            raise ValueError("progress mask contains non-bool values")
        eligible = [index for index, value in enumerate(mask) if value is True]
        if not eligible:
            expected = {"status": "invalid_no_reference", "cost": None}
        else:
            reference = max(float(values[index]) for index in eligible)
            expected = {
                "status": "available",
                "reference_progress_m": reference,
                "cost": [max(reference - float(value), 0.0) for value in values],
            }
        return {"stored": dict(stored), "expected": expected, "equal": dict(stored) == expected}

    source = recompute(progress, "mixed_source_valid_mask", "source_valid_option")
    physical = recompute(
        progress, "mixed_physical_feasible_mask", "physical_feasible_option"
    )
    all_bad = progress.get("all_k_high_risk")
    no_ref = progress.get("no_reference")
    if not isinstance(all_bad, Mapping) or not isinstance(no_ref, Mapping):
        raise ValueError("progress all-K/no-reference fixture is missing")
    all_bad_source = recompute(
        all_bad, "source_valid_mask", "source_valid_option"
    )
    all_bad_physical = recompute(
        all_bad, "physical_feasible_mask", "physical_feasible_option"
    )
    no_ref_source = recompute(no_ref, "source_valid_mask", "source_valid_option")
    no_ref_physical = recompute(
        no_ref, "physical_feasible_mask", "physical_feasible_option"
    )
    mixed_source_mask = progress["mixed_source_valid_mask"]
    mixed_physical_mask = progress["mixed_physical_feasible_mask"]
    checks = {
        "source_valid_recomputed": source["equal"],
        "physical_feasible_recomputed": physical["equal"],
        "options_materially_differ": source["expected"] != physical["expected"],
        "mixed_physical_subset_source": all(
            not mixed_physical_mask[index] or mixed_source_mask[index]
            for index in range(8)
        ),
        "all_k_bad_masks_reachable": all(all_bad["source_valid_mask"])
        and not any(all_bad["physical_feasible_mask"]),
        "all_k_bad_source_valid_recomputed": all_bad_source["equal"]
        and all_bad_source["expected"]["status"] == "available",
        "all_k_bad_physical_recomputed": all_bad_physical["equal"]
        and all_bad_physical["expected"]["status"] == "invalid_no_reference",
        "no_reference_source_recomputed": no_ref_source["equal"]
        and no_ref_source["expected"]["status"] == "invalid_no_reference",
        "no_reference_physical_recomputed": no_ref_physical["equal"]
        and no_ref_physical["expected"]["status"] == "invalid_no_reference",
        "no_candidate0_or_all_k_fallback": progress.get(
            "candidate0_or_all_k_fallback_allowed"
        )
        is False,
    }
    if not all(checks.values()):
        raise ValueError("progress adversarial fixture failed")
    return {
        "checks": checks,
        "source_valid": source,
        "physical_feasible": physical,
        "all_k_high_risk_source_valid": all_bad_source,
        "all_k_high_risk_physical": all_bad_physical,
        "empty_source_valid": no_ref_source,
        "empty_physical": no_ref_physical,
    }


def _independent_kinematic_algebra() -> dict[str, Any]:
    dt = 0.1
    t = np.arange(80, dtype=np.float64) * dt
    xy = np.stack([0.5 * t**3, 0.2 * t**2], axis=1)
    jerk = np.diff(xy, n=3, axis=0) / dt**3
    energy = np.sum(jerk * jerk, axis=1)
    split = max(1, len(energy) // 3)
    early = dt * float(np.sum(energy[:split]))
    late = dt * float(np.sum(energy[split:]))
    full = dt * float(np.sum(energy))
    velocity = np.diff(xy, axis=0) / dt
    speeds = np.linalg.norm(velocity, axis=1)
    limit = 10.0
    speed_costs = [
        dt * float(np.sum(np.maximum(speeds - (limit - margin), 0.0) ** 2))
        for margin in (0.0, 0.5, 1.0)
    ]
    checks = {
        "jerk_full_equals_early_plus_late": math.isclose(
            full, early + late, rel_tol=0.0, abs_tol=1e-12
        ),
        "speed_thresholds_exact_order": speed_costs[0]
        <= speed_costs[1]
        <= speed_costs[2],
        "speed_thresholds_distinct_on_fixture": len(set(speed_costs)) == 3,
    }
    if not all(checks.values()):
        raise ValueError("independent jerk/speed algebra failed")
    return {
        "checks": checks,
        "jerk": {"early": early, "late": late, "full": full},
        "speed_margins_mps": [0.0, 0.5, 1.0],
        "speed_costs": speed_costs,
    }


def _expected_dag_contract() -> dict[str, str]:
    """Independent exact Stage-A DAG contract; do not import producer values."""
    return {
        "S0_to_A": "Ultra S0.1 PASS plus A0 strict-inventory supplement PASS",
        "A_exit": "14 rows complete; independent semantics/numeric validation PASS; source-valid progress reference frozen",
        "R0_3_entry": "A1.3 PASS plus sealed Ultra A1.3/R0.3 decision; full R remains closed",
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
        "current_authority": "A1.3/R0.3 bounded only; full R/B/C/D/E/T/Q/F remain closed",
    }


def validate_ledger(
    *, ledger_artifact: Path, ledger_root_sha256: str
) -> dict[str, Any]:
    current_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(
        ledger_artifact,
        ledger_root_sha256,
        label="V25 Stage A ledger",
    )
    if (ledger_artifact / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("ledger run.exit is not zero")
    ledger = _load_json(ledger_artifact / "atom_ledger.json")
    fixture = _load_json(ledger_artifact / "numeric_fixture.json")
    if fixture.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        raise ValueError("numeric fixture schema drifted")
    authority = ledger.get("authority")
    rows = ledger.get("atoms")
    plan = _load_json(PLAN)
    scale_payload = _load_json(CORRECTED_GENERATION_SCALES)
    warning_contract = plan.get("warning_contract")
    if (
        ledger.get("schema_version") != LEDGER_SCHEMA_VERSION
        or ledger.get("status")
        != "passed_with_warnings_progress_source_valid_frozen"
        or not isinstance(authority, Mapping)
        or authority.get("s01_source_head") != S01_SOURCE_HEAD
        or authority.get("s01_release_baseline_head") != S01_RELEASE_BASELINE_HEAD
        or authority.get("fixed_dp_head") != FIXED_DP_HEAD
        or authority.get("s01_preflight_root_sha256") != PASSED_PREFLIGHT_ROOT
        or authority.get("s01_review_root_sha256") != PASSED_REVIEW_ROOT
        or authority.get("formal_source_root_sha256") != FORMAL_ROOT_SHA256
        or authority.get("plan_path") != str(PLAN)
        or authority.get("plan_sha256") != _file_sha256(PLAN)
        or authority.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or not isinstance(authority.get("ultra_decision_artifact"), str)
        or not isinstance(authority.get("ultra_decision_root_sha256"), str)
        or not isinstance(rows, list)
        or len(rows) != 14
        or plan.get("schema_version") != "camp_dp_v25_atom_ledger_plan_v4"
        or plan.get("required_row_fields") != list(REQUIRED_ROW_FIELDS)
        or not isinstance(warning_contract, Mapping)
    ):
        raise ValueError("ledger authority or 14-row denominator drifted")
    decision_artifact = Path(str(authority["ultra_decision_artifact"]))
    decision_seal = verify_complete_seal(
        decision_artifact,
        str(authority["ultra_decision_root_sha256"]),
        label="V25 Ultra Stage-A decision",
    )
    decision = _load_json(decision_artifact / "decision.json")
    if (
        decision.get("schema_version")
        != "camp_dp_v25_ultra_stage_a13_r03_decision_v4"
        or decision.get("status") != "A1_3_R0_3_only_released"
        or decision.get("progress_reference")
        != "source_valid_candidate_set_reference"
        or decision.get("fixed_dp_head") != FIXED_DP_HEAD
        or decision.get("s01_preflight_root_sha256") != PASSED_PREFLIGHT_ROOT
        or decision.get("s01_review_root_sha256") != PASSED_REVIEW_ROOT
        or decision.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or decision.get("a1_3_authorized") is not True
        or decision.get("r0_3_source_authority_preflight_authorized") is not True
        or decision.get("full_r_authorized") is not False
        or decision_seal["root_sha256"]
        != authority["ultra_decision_root_sha256"]
    ):
        raise ValueError("Ultra Stage-A decision binding drifted")
    if ledger.get("source_state_enum") != [
        "available",
        "not_applicable",
        "unavailable",
        "invalid",
    ]:
        raise ValueError("source-state enum drifted")
    contracts = {contract.name: contract for contract in CANONICAL_ATOM_CONTRACTS}
    atom_results = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != REQUIRED_ROW_KEYS:
            raise ValueError(f"atom row {index} field set drifted")
        name = ATOM_NAMES[index]
        contract = contracts[name]
        expected_formula = contract.formula + (
            "; exact production partition requires jerk_full=jerk_early+jerk_late"
            if name == "jerk_full"
            else ""
        )
        expected_status, expected_warning = _derive_atom_status(
            name, warning_contract
        )
        expected_dependencies = _expected_dependencies(name)
        expected_scale = {
            "value": scale_payload["scales"][index],
            "file": str(CORRECTED_GENERATION_SCALES),
            "file_sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
            "provenance": (
                "V25 semantic dimensionless floor replacing degenerate legacy 1e-6"
                if name == "planned_red_light_cost"
                else "legacy V18 generation behavior scale/floor carried only for corrected-corpus behavior"
            ),
            "not_final_training_scale": True,
        }
        checks = {
            "index_and_name": row.get("index") == index and row.get("name") == name,
            "paper_prefix": row.get("paper_9d_member") is (index < 9)
            and row.get("paper_mapping")
            == ("canonical_14d_prefix" if index < 9 else "DP_fixed-candidate_extension"),
            "unit_exact": row.get("unit") == contract.unit,
            "formula_exact": row.get("formula") == expected_formula,
            "dt_exact": row.get("dt_contract")
            == "dt=0.1 s; finite and strictly positive; the same dt is used throughout each formula",
            "finite_exact": row.get("finite_contract")
            == "every raw coefficient and intermediate must be finite; NaN/Inf fails closed",
            "nonnegative_exact": row.get("nonnegative_contract")
            == "raw atom is >=0 on its declared validity domain",
            "raw_bounds_exact": row.get("raw_bounds")
            == {
                "lower_inclusive": 0.0,
                "upper": None,
                "upper_contract": "unbounded before normalization but finite is mandatory",
            },
            "generation_scale_exact": row.get("generation_behavior_scale")
            == expected_scale,
            "clip_exact": row.get("normalized_clip")
            == {
                "formula": "z=clip(raw_atom/generation_behavior_scale,0,10)",
                "lower": 0.0,
                "upper": 10.0,
            },
            "causal_source_exact": row.get("causal_source_class")
            == list(contract.inputs),
            "decision_time_exact": row.get("decision_time_availability")
            == contract.decision_time_availability,
            "source_states_semantics_exact": row.get("source_state_policy")
            == _expected_source_policy(name),
            "invalid_policy_exact": row.get("invalid_policy")
            == "fail closed; invalid is never converted to zero or uniform fallback",
            "mask_policy_exact": row.get("mask_policy")
            == "unavailable is source-masked; not_applicable may be zero only where this row explicitly allows it",
            "monotonicity_exact": row.get("monotonicity_domain")
            == _expected_monotonicity(name),
            "dependencies_exact": all(
                row.get(key) == value for key, value in expected_dependencies.items()
            ),
            "forbidden_sources_exact": row.get("forbidden_sources")
            == [
                "closed-loop outcome",
                "GT/observed future",
                "Fresh or holdout membership/data",
                "map/route/scenario/split/seed ID or proxy as a model feature",
                "private DP latent",
                "future signal schedule",
            ],
            "fixture_references_exact": row.get("legal_zero_fixture")
            == f"numeric_fixture.raw_atoms[3][{index}]==0"
            and row.get("legal_positive_fixture")
            == f"numeric_fixture.raw_atoms[0][{index}]>0"
            and row.get("candidate_distinguishing_fixture")
            == f"numeric_fixture column {index} has at least two distinct K8 values",
            "status_enum_exact": row.get("status") in {"PASS", "WARN", "FAIL"},
            "status_independently_derived": row.get("status") == expected_status,
            "warning_rationale_exact": row.get("warning") == expected_warning,
        }
        if not all(checks.values()):
            raise ValueError(
                f"atom row {index} failed: "
                + ",".join(key for key, value in checks.items() if not value)
            )
        atom_results.append(
            {
                "index": index,
                "name": name,
                "producer_status": row["status"],
                "derived_status": expected_status,
                "derived_warning": expected_warning,
                "checks": checks,
            }
        )
    if [row["name"] for row in rows[:9]] != list(CAMP_ATOM_NAMES):
        raise ValueError("9D is not the exact canonical 14D prefix")
    ordered_payload = ledger.get("ordered_schema_formula_payload")
    if ledger.get("ordered_schema_formula_sha256") != _canonical_sha256(
        ordered_payload
    ):
        raise ValueError("ordered schema/formula hash mismatch")
    numeric = _independent_numeric_recompute(fixture)
    progress = _validate_progress_fixture(fixture)
    algebra = _independent_kinematic_algebra()
    scale = ledger.get("training_scale_estimator_freeze")
    red = ledger.get("r_red_scientific_coverage_freeze")
    dag = ledger.get("dag_contract")
    contract_checks = {
        "training_estimator_frozen": (
            isinstance(scale, Mapping)
            and scale.get("quantile") == 0.95
            and scale.get("generation_floor_is_training_estimate") is False
            and "semantic block" in str(scale.get("block_weighting"))
            and bool(scale.get("red_binary_alternative"))
            and scale.get("semantic_clone_hash")
            == plan.get("semantic_clone_contract")
        ),
        "red_coverage_fail_closed": (
            isinstance(red, Mapping)
            and red.get("formal_executable_identity_count") == 21
            and red.get("all_21_retained_capability_failures_scientifically_pass")
            is False
            and red.get("minimum_complete_by_tier")
            == {"easy": 4, "borderline": 7, "high_risk": 4}
        ),
        "dag_c_d_gated": dag == _expected_dag_contract(),
        "progress_source_valid_frozen": ledger.get(
            "progress_shortfall_decision", {}
        )
        == {
            "status": "frozen_by_Ultra",
            "reference": "source_valid_candidate_set_reference",
            "formula": "r=max(progress[j] where source_valid[j]); progress_shortfall[k]=max(r-progress[k],0)",
            "selection_eligibility": "source_valid",
            "empty_source_valid": "fail_closed",
            "not_frozen": False,
            "candidate0_or_all_k_fallback_allowed": False,
        },
        "r_and_fresh_closed": (
            ledger.get("stage_boundaries", {}).get("r_authorized") is False
            and ledger.get("stage_boundaries", {}).get("full_corpus_started")
            is False
            and ledger.get("stage_boundaries", {}).get("fresh_b2_opened")
            is False
            and ledger.get("stage_boundaries", {}).get("outcome_fields_consumed")
            == []
        ),
    }
    if not all(contract_checks.values()):
        raise ValueError(
            "ledger cross-contract checks failed: "
            + ",".join(
                name for name, passed in contract_checks.items() if not passed
            )
        )
    warning_rows = [
        row["name"]
        for row in atom_results
        if row["derived_status"] == "WARN"
    ]
    fail_rows = [
        row["name"] for row in atom_results if row["derived_status"] == "FAIL"
    ]
    if fail_rows:
        raise ValueError("Stage A contains FAIL atom rows")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_with_warnings_progress_source_valid_frozen",
        "review_head": current_head,
        "reviewed_artifact": str(ledger_artifact),
        "reviewed_root_sha256": seal["root_sha256"],
        "atom_count": len(rows),
        "paper_9d_indices": list(range(9)),
        "atom_results": atom_results,
        "pass_count": len(rows) - len(warning_rows),
        "warn_count": len(warning_rows),
        "fail_count": len(fail_rows),
        "warning_atoms": warning_rows,
        "numeric_recompute": numeric,
        "progress_adversarial": progress,
        "kinematic_algebra": algebra,
        "contract_checks": contract_checks,
        "progress_reference_ultra_decision_required": False,
        "progress_reference": "source_valid_candidate_set_reference",
        "r_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "independent_validator_imported_production_score_results": False,
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    try:
        report = validate_ledger(
            ledger_artifact=args.ledger_artifact,
            ledger_root_sha256=args.ledger_root_sha256,
        )
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root_sha256 = seal_artifact(
            args.output_dir, label="V25 Stage A independent validation"
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
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
        seal_artifact(args.output_dir, label="V25 Stage A failed validation")
        raise


if __name__ == "__main__":
    main()
