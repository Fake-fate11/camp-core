#!/usr/bin/env python3
"""Independently review the sealed V25 train-only atom audit projection."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
)


SCHEMA_VERSION = "camp_dp_v25_train_only_atom_audit_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FROZEN_TRAINING_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v25_training_v1.json"
)
FROZEN_TRAINING_CONFIG_SHA256 = (
    "939a4cf4275daa205cad0aaf5aef25cfb65e5f9cc412e389191cae14d5044422"
)
EXPECTED_FILES = {
    "COMMAND",
    "HEADS",
    "atom_audit.json",
    "label_sidecar.json",
    "report.json",
    "run.exit",
    "training_rows.npz",
    "training_scales.json",
}
TRAINING_KEYS = {
    "schema_version",
    "normalized_atoms_14d",
    "raw_atoms",
    "oracle_indices",
    "margins",
    "source_valid_mask",
    "atom_source_valid_mask",
    "atom_applicable_mask",
    "physical_feasible_mask",
    "raw_context",
    "context_source_complete",
    "record_weights",
    "route_ids",
    "semantic_block_ids",
    "corridor_ids",
    "map_family_ids",
    "family_tier",
    "seeds",
    "ticks",
    "scenario_ids",
    "training_scales",
    "severity",
}
RED_INDICES = {10, 12}
ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
CORRECTNESS_ATOL = 1e-9
CORRECTNESS_RTOL = 1e-9


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_numeric(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} native numeric shape drifted")
    result = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _strict_bool(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != shape or result.dtype != np.bool_:
        raise ValueError(f"{name} native bool shape drifted")
    return result


def _strings(value: np.ndarray, size: int, name: str) -> tuple[str, ...]:
    raw = np.asarray(value)
    if raw.shape != (size,) or raw.dtype.kind != "U":
        raise ValueError(f"{name} must be a native Unicode vector")
    result = tuple(str(item) for item in raw.tolist())
    if any(not item for item in result):
        raise ValueError(f"{name} contains an empty value")
    return result


def _independent_weights(
    routes: Sequence[str], blocks: Sequence[str], seeds: np.ndarray, ticks: np.ndarray
) -> np.ndarray:
    count = len(routes)
    result = np.zeros(count, dtype=np.float64)
    columns: tuple[Sequence[Any], ...] = (routes, blocks, seeds.tolist(), ticks.tolist())

    def distribute(indices: list[int], level: int, mass: float) -> None:
        if level == len(columns):
            result[indices] = mass / len(indices)
            return
        groups: dict[Any, list[int]] = defaultdict(list)
        for index in indices:
            groups[columns[level][index]].append(index)
        child_mass = mass / len(groups)
        for key in sorted(groups, key=lambda item: (str(type(item)), str(item))):
            distribute(groups[key], level + 1, child_mass)

    distribute(list(range(count)), 0, 1.0)
    return result


def _weighted_q95(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values, kind="mergesort")
    ordered = values[order]
    mass = weights[order]
    threshold = 0.95 * float(np.sum(mass))
    index = int(np.searchsorted(np.cumsum(mass), threshold, side="left"))
    return float(ordered[min(index, ordered.size - 1)])


def _independent_correctness(
    raw: np.ndarray,
    source: np.ndarray,
    atom_source: np.ndarray,
    applicable: np.ndarray,
) -> tuple[dict[str, Any], tuple[tuple[str, ...], ...]]:
    failures: list[list[str]] = [[] for _ in range(14)]
    jerk_mask = source & np.all(atom_source[:, :, :3], axis=2) & np.all(
        applicable[:, :, :3], axis=2
    )
    jerk_error = np.abs(raw[:, :, 2] - (raw[:, :, 0] + raw[:, :, 1]))
    jerk_limit = CORRECTNESS_ATOL + CORRECTNESS_RTOL * np.abs(raw[:, :, 2])
    jerk_bad = jerk_mask & (jerk_error > jerk_limit)
    if np.any(jerk_bad):
        for index in (0, 1, 2):
            failures[index].append("jerk_full_not_equal_early_plus_late")

    speed_mask = source & np.all(atom_source[:, :, 4:7], axis=2) & np.all(
        applicable[:, :, 4:7], axis=2
    )
    speed_bad = speed_mask & (
        (raw[:, :, 4] > raw[:, :, 5] + CORRECTNESS_ATOL)
        | (raw[:, :, 5] > raw[:, :, 6] + CORRECTNESS_ATOL)
    )
    if np.any(speed_bad):
        for index in (4, 5, 6):
            failures[index].append("speed_margin_costs_not_monotone_0_0_le_0_5_le_1_0")

    nonapplicable_counts: list[int] = []
    for index in range(14):
        bad = (
            atom_source[:, :, index]
            & ~applicable[:, :, index]
            & (np.abs(raw[:, :, index]) > CORRECTNESS_ATOL)
        )
        count = int(np.sum(bad))
        nonapplicable_counts.append(count)
        if count:
            failures[index].append("nonapplicable_atom_must_be_exact_zero")

    progress_bad = 0
    for record_index in range(raw.shape[0]):
        mask = (
            source[record_index]
            & atom_source[record_index, :, 9]
            & applicable[record_index, :, 9]
        )
        if not np.any(mask) or float(np.min(raw[record_index, mask, 9])) > CORRECTNESS_ATOL:
            progress_bad += 1
    if progress_bad:
        failures[9].append("progress_shortfall_source_valid_reference_has_no_zero_cost_candidate")

    prior_mask = source[:, 0] & atom_source[:, 0, 13] & applicable[:, 0, 13]
    prior_bad = prior_mask & (np.abs(raw[:, 0, 13]) > CORRECTNESS_ATOL)
    if np.any(prior_bad):
        failures[13].append("candidate0_dp_prior_jerk_excess_must_be_zero")
    checks = {
        "jerk_full_equals_early_plus_late": {
            "checked_candidate_count": int(np.sum(jerk_mask)),
            "violation_count": int(np.sum(jerk_bad)),
            "maximum_absolute_error": float(np.max(jerk_error[jerk_mask])) if np.any(jerk_mask) else None,
            "status": "FAIL" if np.any(jerk_bad) else "PASS",
        },
        "speed_margin_cost_monotonicity": {
            "formula_order": "margin_0_0_le_margin_0_5_le_margin_1_0",
            "checked_candidate_count": int(np.sum(speed_mask)),
            "violation_count": int(np.sum(speed_bad)),
            "status": "FAIL" if np.any(speed_bad) else "PASS",
        },
        "nonapplicable_atoms_are_zero": {
            "per_atom_violation_count": nonapplicable_counts,
            "violation_count": int(sum(nonapplicable_counts)),
            "status": "FAIL" if any(nonapplicable_counts) else "PASS",
        },
        "progress_source_valid_reference": {
            "checked_snapshot_count": int(raw.shape[0]),
            "violation_count": progress_bad,
            "status": "FAIL" if progress_bad else "PASS",
        },
        "candidate0_dp_prior_anchor": {
            "checked_snapshot_count": int(np.sum(prior_mask)),
            "violation_count": int(np.sum(prior_bad)),
            "status": "FAIL" if np.any(prior_bad) else "PASS",
        },
    }
    return checks, tuple(tuple(row) for row in failures)


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    root = Path(artifact).resolve()
    seal = verify_complete_seal(root, expected_root, label="V25 train atom audit")
    if set(seal["manifest_paths"]) != EXPECTED_FILES:
        raise ValueError("train atom audit manifest inventory drifted")
    if (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("train atom audit did not exit successfully")
    report = _json(root / "report.json")
    scales_report = _json(root / "training_scales.json")
    audit = _json(root / "atom_audit.json")
    labels = _json(root / "label_sidecar.json")
    corpus = report.get("corpus")
    if _sha256(FROZEN_TRAINING_CONFIG) != FROZEN_TRAINING_CONFIG_SHA256:
        raise ValueError("V25 training/audit config SHA drifted")
    training_config = _json(FROZEN_TRAINING_CONFIG)
    audit_contract = training_config.get("train_only_atom_audit_contract")
    label_contract = (
        audit_contract.get("causal_policy_distillation")
        if type(audit_contract) is dict
        else None
    )
    if (
        report.get("schema_version")
        != "camp_dp_v25_train_only_atom_audit_artifact_v1"
        or report.get("status") != "passed_train_only_atom_audit_projection"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or type(corpus) is not dict
        or corpus.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or Path(str(report.get("training_config"))).resolve()
        != FROZEN_TRAINING_CONFIG.resolve()
        or report.get("training_config_sha256")
        != FROZEN_TRAINING_CONFIG_SHA256
        or report.get("training_config_payload") != training_config
        or report.get("train_only_atom_audit_contract") != audit_contract
        or type(audit_contract) is not dict
        or type(label_contract) is not dict
    ):
        raise ValueError("train atom audit report contract drifted")
    minimum_positive_rows = audit_contract.get("minimum_positive_candidate_rows")
    minimum_positive_blocks = audit_contract.get(
        "minimum_positive_semantic_blocks"
    )
    if (
        set(audit_contract)
        != {
            "scale_estimator",
            "scale_quantile",
            "minimum_positive_candidate_rows",
            "minimum_positive_semantic_blocks",
            "zero_support_policy",
            "support_limited_red_policy",
            "causal_policy_distillation",
        }
        or audit_contract.get("scale_estimator")
        != "positive_support_block_weighted_inverse_empirical_q95"
        or audit_contract.get("scale_quantile") != 0.95
        or type(minimum_positive_rows) is not int
        or minimum_positive_rows != 128
        or type(minimum_positive_blocks) is not int
        or minimum_positive_blocks != 20
        or audit_contract.get("zero_support_policy")
        != "keep_14d_dimension_masked_and_use_neutral_unit_scale_not_generation_floor"
        or audit_contract.get("support_limited_red_policy")
        != "binary_scale_1_not_degenerate_continuous_floor"
        or set(label_contract)
        != {
            "severity_14d",
            "physical_penalty",
            "margin_multiplier",
            "margin_clip",
            "eligibility",
            "tie_break",
            "closed_loop_outcome_consumed",
            "fresh_b2_consumed",
            "identity_fields_used_as_label_or_feature",
        }
        or label_contract.get("physical_penalty") != 100.0
        or label_contract.get("margin_multiplier") != 0.1
        or label_contract.get("margin_clip") != 2.0
        or label_contract.get("eligibility") != "source_valid_candidate_set"
        or label_contract.get("tie_break") != "lowest_candidate_index"
        or label_contract.get("closed_loop_outcome_consumed") is not False
        or label_contract.get("fresh_b2_consumed") is not False
        or label_contract.get("identity_fields_used_as_label_or_feature") is not False
    ):
        raise ValueError("train-only audit numeric config contract drifted")
    verify_complete_seal(
        Path(str(corpus["corpus_artifact"])),
        str(corpus["corpus_root_sha256"]),
        label="reviewed source corpus",
    )
    verify_complete_seal(
        Path(str(corpus["review_artifact"])),
        str(corpus["review_root_sha256"]),
        label="source corpus independent review",
    )
    if report.get("training_rows_sha256") != _sha256(root / "training_rows.npz"):
        raise ValueError("training row archive SHA drifted")
    with np.load(root / "training_rows.npz", allow_pickle=False) as archive:
        if set(archive.files) != TRAINING_KEYS:
            raise ValueError("training row archive keyset drifted")
        data = {key: archive[key] for key in archive.files}
    if data["schema_version"].shape != () or str(data["schema_version"].item()) != (
        "camp_dp_v25_fair_2x2_training_rows_v1"
    ):
        raise ValueError("training row archive schema drifted")
    n = int(data["raw_atoms"].shape[0])
    raw = _strict_numeric(data["raw_atoms"], (n, 8, 14), "raw_atoms")
    normalized = _strict_numeric(
        data["normalized_atoms_14d"], (n, 8, 14), "normalized_atoms_14d"
    )
    source = _strict_bool(data["source_valid_mask"], (n, 8), "source_valid")
    atom_source = _strict_bool(
        data["atom_source_valid_mask"], (n, 8, 14), "atom_source_valid"
    )
    applicable = _strict_bool(
        data["atom_applicable_mask"], (n, 8, 14), "atom_applicable"
    )
    physical = _strict_bool(
        data["physical_feasible_mask"], (n, 8), "physical_feasible"
    )
    context = _strict_numeric(data["raw_context"], (n, RAW_FEATURE_COUNT), "raw_context")
    context_source = _strict_bool(
        data["context_source_complete"],
        (n, RAW_FEATURE_COUNT),
        "context_source_complete",
    )
    if np.any(raw < 0.0) or np.any(applicable & ~atom_source):
        raise ValueError("raw atom/applicability contract drifted")
    if not np.array_equal(source, np.all(atom_source, axis=2)):
        raise ValueError("candidate source-valid conjunction drifted")
    if np.any(physical & ~source) or np.any(~np.any(source, axis=1)):
        raise ValueError("physical/source eligibility contract drifted")
    phase_remaining = RAW_FEATURE_NAMES.index("traffic_signal_phase_remaining_s")
    if np.any(context_source[:, phase_remaining]):
        raise ValueError("no-V2I training projection exposed phase_remaining")
    routes = _strings(data["route_ids"], n, "route_ids")
    blocks = _strings(data["semantic_block_ids"], n, "semantic_block_ids")
    _strings(data["corridor_ids"], n, "corridor_ids")
    _strings(data["map_family_ids"], n, "map_family_ids")
    _strings(data["family_tier"], n, "family_tier")
    _strings(data["scenario_ids"], n, "scenario_ids")
    seeds = np.asarray(data["seeds"])
    ticks = np.asarray(data["ticks"])
    if (
        seeds.shape != (n,)
        or seeds.dtype.kind not in "iu"
        or ticks.shape != (n,)
        or ticks.dtype.kind not in "iu"
        or np.any(seeds != 25001)
        or np.any(ticks < 0)
        or np.any(ticks >= 64)
    ):
        raise ValueError("seed/tick authority drifted")
    weights = _strict_numeric(data["record_weights"], (n,), "record_weights")
    expected_weights = _independent_weights(routes, blocks, seeds, ticks)
    if not np.allclose(weights, expected_weights, rtol=0.0, atol=1e-15):
        raise ValueError("hierarchical block weights were not independently reproduced")
    training_scales = _strict_numeric(
        data["training_scales"], (14,), "training_scales"
    )
    if np.any(training_scales <= 0.0):
        raise ValueError("training scales must be positive")
    scale_rows = scales_report.get("atom_rows")
    if (
        scales_report.get("schema_version") != "camp_dp_v25_train_only_atom_scales_v2"
        or type(scale_rows) is not list
        or len(scale_rows) != 14
        or not np.array_equal(
            np.asarray(scales_report.get("scales"), dtype=np.float64),
            training_scales,
        )
    ):
        raise ValueError("training scale report schema drifted")
    for atom_index, row in enumerate(scale_rows):
        eligible = source & atom_source[:, :, atom_index] & applicable[:, :, atom_index]
        positive = eligible & (raw[:, :, atom_index] > 0.0)
        positive_count = int(np.sum(positive))
        positive_blocks = len({blocks[i] for i in range(n) if np.any(positive[i])})
        candidate_weights = np.zeros((n, 8), dtype=np.float64)
        counts = np.sum(eligible, axis=1)
        valid = counts > 0
        candidate_weights[valid] = (
            weights[valid, None] / counts[valid, None]
        ) * eligible[valid]
        q95 = (
            _weighted_q95(raw[:, :, atom_index][positive], candidate_weights[positive])
            if positive_count
            else None
        )
        support_ok = (
            positive_count >= minimum_positive_rows
            and positive_blocks >= minimum_positive_blocks
        )
        expected_scale = (
            1.0
            if q95 is None or (atom_index in RED_INDICES and not support_ok)
            else q95
        )
        if (
            row.get("atom_index") != atom_index
            or row.get("positive_candidate_row_count") != positive_count
            or row.get("positive_semantic_block_count") != positive_blocks
            or row.get("status") != ("PASS" if support_ok else "WARN")
            or not np.isclose(training_scales[atom_index], expected_scale, rtol=0.0, atol=1e-12)
        ):
            raise ValueError(f"training scale atom {atom_index} failed independent oracle")
    expected_normalized = np.clip(raw / training_scales[None, None, :], 0.0, 10.0)
    if not np.array_equal(normalized, expected_normalized):
        raise ValueError("canonical training normalization drifted")
    severity = _strict_numeric(data["severity"], (14,), "severity")
    if severity.tolist() != label_contract.get("severity_14d"):
        raise ValueError("causal-label severity differs from frozen config")
    contributions = np.where(
        atom_source & applicable,
        normalized * severity[None, None, :],
        0.0,
    )
    costs = np.sum(contributions, axis=2) + float(
        label_contract["physical_penalty"]
    ) * (~physical)
    costs = np.where(source, costs, np.inf)
    oracle = np.argmin(costs, axis=1).astype(np.int64)
    oracle_cost = costs[np.arange(n), oracle]
    margins = np.clip(
        float(label_contract["margin_multiplier"])
        * (costs - oracle_cost[:, None]),
        0.0,
        float(label_contract["margin_clip"]),
    )
    margins[~source] = 0.0
    stored_oracle = np.asarray(data["oracle_indices"])
    stored_margins = _strict_numeric(data["margins"], (n, 8), "margins")
    if (
        stored_oracle.shape != (n,)
        or stored_oracle.dtype.kind not in "iu"
        or not np.array_equal(stored_oracle, oracle)
        or not np.array_equal(stored_margins, margins)
    ):
        raise ValueError("causal-policy-distillation labels failed independent oracle")
    if (
        labels.get("schema_version")
        != "camp_dp_v25_train_only_causal_label_sidecar_v1"
        or labels.get("label_contract") != "causal_policy_distillation_no_outcome"
        or labels.get("physical_penalty") != label_contract["physical_penalty"]
        or labels.get("margin_multiplier") != label_contract["margin_multiplier"]
        or labels.get("margin_clip") != label_contract["margin_clip"]
        or labels.get("severity") != severity.tolist()
        or labels.get("oracle_index_sha256")
        != hashlib.sha256(np.ascontiguousarray(stored_oracle).tobytes()).hexdigest()
        or labels.get("margin_sha256")
        != hashlib.sha256(np.ascontiguousarray(stored_margins).tobytes()).hexdigest()
    ):
        raise ValueError("causal label sidecar hash/value contract drifted")
    audit_rows = audit.get("atom_rows")
    expected_correctness, correctness_failures = _independent_correctness(
        raw, source, atom_source, applicable
    )
    if audit.get("correctness_checks") != expected_correctness:
        raise ValueError("atom audit correctness checks failed independent oracle")
    expected_atom_statuses: list[str] = []
    for atom_index in range(14):
        row = audit_rows[atom_index] if type(audit_rows) is list and len(audit_rows) == 14 else {}
        eligible = source & atom_source[:, :, atom_index] & applicable[:, :, atom_index]
        positive = eligible & (raw[:, :, atom_index] > 0.0)
        positive_count = int(np.sum(positive))
        positive_blocks = len({blocks[i] for i in range(n) if np.any(positive[i])})
        support_ok = (
            positive_count >= minimum_positive_rows
            and positive_blocks >= minimum_positive_blocks
        )
        distinction_ranges: list[float] = []
        distinction_weights: list[float] = []
        for record_index in range(n):
            values = raw[record_index, eligible[record_index], atom_index]
            if values.size < 2:
                continue
            distinction_ranges.append(float(np.max(values) - np.min(values)))
            distinction_weights.append(float(weights[record_index]))
        positive_range_weight = 0.0
        if distinction_ranges:
            normalized_distinction_weights = np.asarray(
                distinction_weights, dtype=np.float64
            )
            normalized_distinction_weights /= np.sum(normalized_distinction_weights)
            positive_range_weight = float(
                np.sum(
                    normalized_distinction_weights[
                        np.asarray(distinction_ranges, dtype=np.float64) > 0.0
                    ]
                )
            )
        warning_reasons: list[str] = []
        remediation_classes: list[str] = []
        failure_reasons = list(correctness_failures[atom_index])
        if failure_reasons:
            remediation_classes.append("implementation_correctness")
        if not support_ok:
            warning_reasons.append("support_limited")
            remediation_classes.append("evidence_support")
        if distinction_ranges and positive_range_weight == 0.0:
            warning_reasons.append("candidate_indistinguishable")
            remediation_classes.append("expected_redundancy")
        expected_status = "FAIL" if failure_reasons else "WARN" if warning_reasons else "PASS"
        expected_atom_statuses.append(expected_status)
        distinction = row.get("candidate_distinction") if type(row) is dict else None
        if (
            type(row) is not dict
            or row.get("atom_index") != atom_index
            or row.get("atom_name") != ATOM_NAMES[atom_index]
            or row.get("positive_candidate_count") != positive_count
            or row.get("positive_semantic_block_count") != positive_blocks
            or row.get("status") != expected_status
            or row.get("status_scope")
            != "sealed_train_only_empirical_support_and_candidate_distinction_not_static_formula_or_source_correctness"
            or row.get("warning") != (warning_reasons[0] if warning_reasons else None)
            or row.get("warning_reasons") != warning_reasons
            or row.get("failure_reasons") != failure_reasons
            or row.get("remediation_class")
            != (remediation_classes[0] if remediation_classes else None)
            or row.get("remediation_classes") != remediation_classes
            or type(distinction) is not dict
            or distinction.get("eligible_snapshot_count") != len(distinction_ranges)
            or not np.isclose(
                float(distinction.get("positive_range_weight", -1.0)),
                positive_range_weight,
                rtol=0.0,
                atol=1e-15,
            )
        ):
            raise ValueError(f"atom {atom_index} empirical status failed independent oracle")
    expected_status_counts = {
        status: expected_atom_statuses.count(status) for status in ("PASS", "WARN", "FAIL")
    }
    if (
        labels.get("fresh_or_outcome_consumed") is not False
        or labels.get("identity_fields_used_as_label_or_feature") is not False
        or audit.get("fresh_or_outcome_consumed") is not False
        or audit.get("status_scope")
        != "sealed_train_only_empirical_support_and_candidate_distinction_not_static_formula_or_source_correctness"
        or audit.get("static_correctness_prerequisite")
        != "formula_source_schema_clip_and_mask_failures_must_be_rejected_upstream"
        or audit.get("status_counts") != expected_status_counts
        or report.get("atom_audit_status_counts") != expected_status_counts
        or type(audit_rows) is not list
        or len(audit_rows) != 14
        or context.shape != (n, RAW_FEATURE_COUNT)
    ):
        raise ValueError("audit/label evidence contract drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_train_only_atom_audit_review",
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "snapshot_count": n,
        "candidate_count": n * 8,
        "atom_count": 14,
        "training_config_sha256": FROZEN_TRAINING_CONFIG_SHA256,
        "training_scale_status_counts": report["training_scale_status_counts"],
        "atom_audit_status_counts": report["atom_audit_status_counts"],
        "atom_audit_status_scope": audit["status_scope"],
        "static_correctness_prerequisite": audit[
            "static_correctness_prerequisite"
        ],
        "phase_remaining_available_count": 0,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(
        (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.artifact, args.root_sha256)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={_json(args.artifact / 'report.json')['camp_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 train atom audit review")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(args.output_dir / "failure.json", {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)})
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="failed V25 train atom audit review")
        raise


if __name__ == "__main__":
    main()
