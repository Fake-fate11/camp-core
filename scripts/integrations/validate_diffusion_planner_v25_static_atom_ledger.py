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
    FORMAL_ROOT_SHA256,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_static_atom_ledger_validation_v2"
LEDGER_SCHEMA_VERSION = "camp_dp_v25_static_atom_ledger_v2"
FIXTURE_SCHEMA_VERSION = "camp_dp_v25_static_atom_numeric_fixture_v2"
ATOM_NAMES = tuple(DP_CAMP_ATOM_NAMES_V10)
REQUIRED_ROW_KEYS = frozenset(
    {
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
        "dependencies",
        "forbidden_sources",
        "legal_zero_fixture",
        "legal_positive_fixture",
        "candidate_distinguishing_fixture",
        "status",
        "warning",
    }
)


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


def _independent_numeric_recompute(fixture: Mapping[str, Any]) -> dict[str, Any]:
    raw = fixture.get("raw_atoms")
    scales = fixture.get("scales")
    weights = fixture.get("weights")
    source_valid = fixture.get("source_valid_mask")
    physical = fixture.get("physical_feasible_mask")
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
    stored_normalized = np.asarray(
        fixture.get("production_normalized_atoms"), dtype=np.float64
    )
    stored_scores = np.asarray(fixture.get("production_scores"), dtype=np.float64)
    if stored_normalized.shape != (8, 14) or stored_scores.shape != (8,):
        raise ValueError("stored production numeric evidence shape drifted")
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
        "all_atoms_have_zero_positive_and_k8_difference": all(
            raw[0][atom] == 0.0
            and any(float(raw[candidate][atom]) > 0.0 for candidate in range(1, 8))
            and len({float(raw[candidate][atom]) for candidate in range(8)}) > 1
            for atom in range(14)
        ),
        "mixed_masks_are_distinct": source_valid != physical,
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

    def recompute(mask_key: str, option_key: str) -> dict[str, Any]:
        mask = progress.get(mask_key)
        stored = progress.get(option_key)
        if not isinstance(mask, list) or len(mask) != 8 or not isinstance(stored, Mapping):
            raise ValueError("progress mixed-mask fixture is invalid")
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

    source = recompute("mixed_source_valid_mask", "source_valid_option")
    physical = recompute("mixed_physical_feasible_mask", "physical_feasible_option")
    all_bad = progress.get("all_k_high_risk")
    no_ref = progress.get("no_reference")
    if not isinstance(all_bad, Mapping) or not isinstance(no_ref, Mapping):
        raise ValueError("progress all-K/no-reference fixture is missing")
    checks = {
        "source_valid_recomputed": source["equal"],
        "physical_feasible_recomputed": physical["equal"],
        "options_materially_differ": source["expected"] != physical["expected"],
        "all_k_bad_source_valid_available": all_bad.get("source_valid_option", {}).get(
            "status"
        )
        == "available",
        "all_k_bad_physical_has_no_reference": all_bad.get(
            "physical_feasible_option", {}
        ).get("status")
        == "invalid_no_reference",
        "no_reference_both_fail_closed": (
            no_ref.get("source_valid_option", {}).get("status")
            == "invalid_no_reference"
            and no_ref.get("physical_feasible_option", {}).get("status")
            == "invalid_no_reference"
        ),
        "no_candidate0_or_all_k_fallback": progress.get(
            "candidate0_or_all_k_fallback_allowed"
        )
        is False,
    }
    if not all(checks.values()):
        raise ValueError("progress adversarial fixture failed")
    return {"checks": checks, "source_valid": source, "physical_feasible": physical}


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
    if (
        ledger.get("schema_version") != LEDGER_SCHEMA_VERSION
        or not isinstance(authority, Mapping)
        or authority.get("s01_source_head") != S01_SOURCE_HEAD
        or authority.get("s01_release_baseline_head") != S01_RELEASE_BASELINE_HEAD
        or authority.get("fixed_dp_head") != FIXED_DP_HEAD
        or authority.get("s01_preflight_root_sha256") != PASSED_PREFLIGHT_ROOT
        or authority.get("s01_review_root_sha256") != PASSED_REVIEW_ROOT
        or authority.get("formal_source_root_sha256") != FORMAL_ROOT_SHA256
        or authority.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or not isinstance(rows, list)
        or len(rows) != 14
    ):
        raise ValueError("ledger authority or 14-row denominator drifted")
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
        checks = {
            "index_and_name": row.get("index") == index and row.get("name") == name,
            "paper_prefix": row.get("paper_9d_member") is (index < 9),
            "unit_matches_source": row.get("unit") == contracts[name].unit,
            "formula_matches_source": str(row.get("formula", "")).startswith(
                contracts[name].formula
            ),
            "finite_nonnegative_raw": (
                "finite" in str(row.get("finite_contract"))
                and ">=0" in str(row.get("nonnegative_contract"))
                and row.get("raw_bounds", {}).get("lower_inclusive") == 0.0
            ),
            "clip_exact": row.get("normalized_clip")
            == {
                "formula": "z=clip(raw_atom/generation_behavior_scale,0,10)",
                "lower": 0.0,
                "upper": 10.0,
            },
            "source_states_exact": set(row.get("source_state_policy", {}))
            == {"available", "not_applicable", "unavailable", "invalid"},
            "invalid_fails_closed": "fail closed" in str(row.get("invalid_policy")),
            "forbidden_sources_complete": all(
                token in " ".join(row.get("forbidden_sources", [])).lower()
                for token in ("outcome", "future", "fresh", "private dp latent")
            ),
            "fixture_references_present": all(
                isinstance(row.get(key), str) and row.get(key)
                for key in (
                    "legal_zero_fixture",
                    "legal_positive_fixture",
                    "candidate_distinguishing_fixture",
                )
            ),
        }
        if not all(checks.values()):
            raise ValueError(
                f"atom row {index} failed: "
                + ",".join(key for key, value in checks.items() if not value)
            )
        atom_results.append(
            {"index": index, "name": name, "status": row["status"], "checks": checks}
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
            and "source-independent" in str(scale.get("block_weighting"))
            and scale.get("red_binary_alternative")
        ),
        "red_coverage_fail_closed": (
            isinstance(red, Mapping)
            and red.get("formal_executable_identity_count") == 21
            and red.get("all_21_retained_capability_failures_scientifically_pass")
            is False
            and red.get("minimum_complete_by_tier")
            == {"easy": 4, "borderline": 7, "high_risk": 4}
        ),
        "dag_c_d_gated": (
            isinstance(dag, Mapping)
            and "Ultra release" in str(dag.get("C_entry"))
            and "Ultra release" in str(dag.get("D_entry"))
            and "PASS/WARN/FAIL" in str(dag.get("C_exit"))
            and "remediation" in str(dag.get("D_exit"))
        ),
        "progress_not_finally_frozen": ledger.get(
            "progress_shortfall_decision", {}
        ).get("not_frozen")
        is True,
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
    warning_rows = [row["name"] for row in rows if row["status"] == "WARN"]
    fail_rows = [row["name"] for row in rows if row["status"] == "FAIL"]
    if fail_rows:
        raise ValueError("Stage A contains FAIL atom rows")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_with_warnings_ultra_progress_decision_required",
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
        "progress_reference_ultra_decision_required": True,
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
