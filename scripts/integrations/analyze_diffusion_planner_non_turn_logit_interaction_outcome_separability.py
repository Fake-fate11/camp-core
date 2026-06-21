#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (  # noqa: E402
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
)


PAYLOAD_KEY = "non_turn_logit_interaction_payload_logging"
FORMAL_SEEDS = frozenset({11, 12, 13})
CLASS_TOP1 = "top1_reference"
CLASS_BENEFICIAL = "beneficial_alternative"
CLASS_HARMFUL = "harmful_alternative"
CLASS_NEUTRAL = "neutral_alternative"

READY_STATUS = (
    "non_turn_logit_interaction_outcome_separability_promising_for_certificate_design"
)
REJECT_STATUS = "non_turn_logit_interaction_outcome_separability_rejected"
SOURCE_BLOCKED_STATUS = (
    "non_turn_logit_interaction_outcome_separability_source_not_ready"
)
FORMAL_SEED_STATUS = (
    "non_turn_logit_interaction_outcome_separability_formal_seed_conflict"
)
CONTRACT_READY_STATUS = "non_turn_logit_interaction_matched_outcome_contract_passed"
CONTRACT_NEXT_WORK = "non_turn_logit_interaction_outcome_separability_plan_only"

MIN_VALUE_GAIN = 0.05
MIN_VALUE_LOSS = 0.05
PROGRESS_LOSS_BUDGET_M = 0.5
HARMFUL_BLOCK_RATE_TARGET = 0.6
BENEFICIAL_RETAIN_RATE_TARGET = 0.8
ALLOWED_HARMFUL_RATE_TARGET = 0.2
MIN_BENEFICIAL_CANDIDATES = 2
MIN_HARMFUL_CANDIDATES = 2

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "schema_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen for the DP-CAMP "
            "non-turn-logit interaction payload. Outcome labels are used only "
            "for offline class labels and threshold diagnostics."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--matched_dataset_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument(
        "--harmful_block_rate_target",
        type=float,
        default=HARMFUL_BLOCK_RATE_TARGET,
    )
    parser.add_argument(
        "--beneficial_retain_rate_target",
        type=float,
        default=BENEFICIAL_RETAIN_RATE_TARGET,
    )
    parser.add_argument(
        "--allowed_harmful_rate_target",
        type=float,
        default=ALLOWED_HARMFUL_RATE_TARGET,
    )
    parser.add_argument(
        "--min_beneficial_candidates",
        type=int,
        default=MIN_BENEFICIAL_CANDIDATES,
    )
    parser.add_argument(
        "--min_harmful_candidates",
        type=int,
        default=MIN_HARMFUL_CANDIDATES,
    )
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        matched_contract_report=_read_json(args.matched_contract_json),
        matched_dataset_report=_read_json(args.matched_dataset_audit_json),
        label=args.label,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
        min_beneficial_candidates=args.min_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    matched_contract_report: dict[str, Any],
    matched_dataset_report: dict[str, Any],
    label: str | None = None,
    expected_logs: int | None = None,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = _discover_logs(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    if expected_logs is not None and len(log_paths) != int(expected_logs):
        raise ValueError(f"log_count={len(log_paths)} expected={expected_logs}.")

    records: list[dict[str, Any]] = []
    formal_seed_records = 0
    for log_path in log_paths:
        rows = _read_json(log_path)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        if expected_records is not None and len(rows) != int(expected_records):
            raise ValueError(
                f"{log_path} record_count={len(rows)} expected={expected_records}."
            )
        path_seeds = _path_seeds(log_path)
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            record_seed = _record_seed(raw)
            formal = bool(path_seeds & FORMAL_SEEDS) or record_seed in FORMAL_SEEDS
            formal_seed_records += int(formal)
            records.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(path_seeds),
                        "record_seed": record_seed,
                    },
                }
            )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    source = _source_gate(matched_contract_report, matched_dataset_report)
    rows = []
    for index, item in enumerate(records):
        rows.extend(
            _candidate_rows(
                item["raw"],
                item["context"],
                f"record {index}",
                expected_candidates=expected_candidates,
                min_value_gain=min_value_gain,
                min_value_loss=min_value_loss,
                progress_loss_budget_m=progress_loss_budget_m,
            )
        )
    alternatives = [row for row in rows if row["class"] != CLASS_TOP1]
    class_counts = _class_counts(alternatives)
    screens = _threshold_screens(
        alternatives,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )
    ranked = sorted(
        screens,
        key=lambda item: (
            item["promising_screen"],
            item["atom_candidate_eligible"],
            item["harmful_block_rate"],
            item["beneficial_retain_rate"],
            -item["allowed_harmful_rate"],
        ),
        reverse=True,
    )
    decision = _decision(
        source,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_outcome_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_classification": True,
            "future_outcome_labels_used_for_thresholds": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "descriptor_definitions": _descriptor_definitions(),
            "atom_candidate_descriptors": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "label_definition": {
                "beneficial": (
                    "candidate k>0 is feasible, improves outcome value over "
                    "candidate0 by min_value_gain, preserves progress within "
                    "progress_loss_budget_m, and is hard-safety-nonworse"
                ),
                "harmful": (
                    "candidate k>0 is infeasible, hard-safety-worse, loses "
                    "more than min_value_loss in outcome value, or exceeds "
                    "the progress loss budget"
                ),
                "neutral": "all other k>0 candidates",
                "outcome_value_direction": "higher_is_better",
            },
            "math_boundary": (
                "The non-turn-logit interaction payload is a current-tick "
                "fixed finite-candidate descriptor computed before selection "
                "and before candidate closed-loop outcomes. Outcome labels "
                "define only offline beneficial/harmful classes and threshold "
                "diagnostics. comfort_progress_interaction_cost is finite, "
                "nonnegative, and fixed per candidate; if later atomized it "
                "enters CAMP as a coefficient in score_k(w)=a_k^T w, "
                "preserving the simplex/CVaR/L2 convex master. The diagnostic "
                "route-progress and jerk fields are not promoted by this "
                "screen. No DP-side classical Benders master, subproblem, "
                "dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_gate": source,
        "records": {
            "logs": len(log_paths),
            "total_records": len(records),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternatives),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "descriptor_coverage": _descriptor_coverage(alternatives),
        "ranked_screens": ranked[:50],
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    *,
    expected_candidates: int,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> list[dict[str, Any]]:
    payload = raw.get(PAYLOAD_KEY)
    outcomes = raw.get("candidate_closed_loop_outcomes")
    _validate_payload(payload, expected_candidates, label)
    if not isinstance(outcomes, list) or len(outcomes) != int(expected_candidates):
        raise ValueError(f"{label} must contain complete candidate outcomes.")
    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    features = {
        field: np.asarray(payload[field], dtype=np.float64)
        for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES
    }
    rows = []
    for candidate_index, raw_outcome in enumerate(outcomes):
        outcome = _outcome(raw_outcome, f"{label} outcome {candidate_index}")
        value_delta = outcome["value"] - top1["value"]
        progress_delta = outcome["progress_m"] - top1["progress_m"]
        hard_worse = outcome["hard_violation_count"] > top1["hard_violation_count"]
        beneficial = (
            candidate_index != 0
            and outcome["feasible"]
            and value_delta >= float(min_value_gain)
            and progress_delta >= -float(progress_loss_budget_m)
            and not hard_worse
        )
        harmful = (
            candidate_index != 0
            and (
                not outcome["feasible"]
                or hard_worse
                or value_delta <= -float(min_value_loss)
                or progress_delta < -float(progress_loss_budget_m)
            )
        )
        if candidate_index == 0:
            cls = CLASS_TOP1
        elif beneficial:
            cls = CLASS_BENEFICIAL
        elif harmful:
            cls = CLASS_HARMFUL
        else:
            cls = CLASS_NEUTRAL
        rows.append(
            {
                "context": context,
                "candidate_index": candidate_index,
                "class": cls,
                "outcome_value_delta_vs_top1": value_delta,
                "progress_delta_vs_top1_m": progress_delta,
                "hard_violation_delta_vs_top1": (
                    outcome["hard_violation_count"] - top1["hard_violation_count"]
                ),
                "features": {
                    name: float(values[candidate_index])
                    for name, values in features.items()
                    if np.isfinite(values[candidate_index])
                },
            }
        )
    return rows


def _validate_payload(payload: Any, expected_candidates: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing {PAYLOAD_KEY} payload.")
    expected = {
        "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
        "available": True,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"{label} interaction payload {field}={payload.get(field)!r}.")
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} interaction payload embeds outcome labels.")
    if payload.get("candidate_count") != int(expected_candidates):
        raise ValueError(f"{label} interaction payload candidate_count mismatch.")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict) or finite_checks.get("payload_valid") is not True:
        raise ValueError(f"{label} interaction finite checks failed.")
    expected_shape = (int(expected_candidates),)
    arrays = {}
    for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES:
        array = np.asarray(payload.get(field), dtype=np.float64)
        arrays[field] = array
        if array.shape != expected_shape:
            raise ValueError(f"{label} {field} shape={list(array.shape)}.")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{label} {field} contains nonfinite values.")
        if np.any(array < -1e-12):
            raise ValueError(f"{label} {field} contains negative values.")
    interaction = arrays["comfort_progress_interaction_cost"]
    product = (
        arrays["route_progress_deficit_vs_top1_m"]
        * arrays["dp_prior_jerk_excess_cost"]
    )
    if not np.allclose(interaction, product, atol=1e-9, rtol=1e-9):
        raise ValueError(f"{label} interaction is not progress_deficit * jerk_excess.")


def _threshold_screens(
    rows: list[dict[str, Any]],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
) -> list[dict[str, Any]]:
    screens = []
    descriptors = _descriptor_definitions()
    for descriptor, definition in descriptors.items():
        values = sorted(
            {
                float(row["features"][descriptor])
                for row in rows
                if descriptor in row["features"]
            }
        )
        for threshold in values:
            blocked = [
                row for row in rows if row["features"].get(descriptor, -np.inf) >= threshold
            ]
            allowed = [
                row for row in rows if row["features"].get(descriptor, -np.inf) < threshold
            ]
            harmful = [row for row in rows if row["class"] == CLASS_HARMFUL]
            beneficial = [row for row in rows if row["class"] == CLASS_BENEFICIAL]
            harmful_blocked = [row for row in blocked if row["class"] == CLASS_HARMFUL]
            beneficial_allowed = [row for row in allowed if row["class"] == CLASS_BENEFICIAL]
            allowed_harmful = [row for row in allowed if row["class"] == CLASS_HARMFUL]
            harmful_block_rate = _rate(len(harmful_blocked), len(harmful))
            beneficial_retain_rate = _rate(len(beneficial_allowed), len(beneficial))
            allowed_harmful_rate = _rate(len(allowed_harmful), len(allowed))
            atom_eligible = bool(definition["atom_candidate_eligible"])
            promising = (
                atom_eligible
                and harmful_block_rate >= float(harmful_block_rate_target)
                and beneficial_retain_rate >= float(beneficial_retain_rate_target)
                and allowed_harmful_rate <= float(allowed_harmful_rate_target)
            )
            screens.append(
                {
                    "screen_name": f"{descriptor} >= {threshold:.12g}",
                    "descriptor": descriptor,
                    "threshold": threshold,
                    "atom_candidate_eligible": atom_eligible,
                    "promising_screen": promising,
                    "harmful_block_rate": harmful_block_rate,
                    "beneficial_retain_rate": beneficial_retain_rate,
                    "allowed_harmful_rate": allowed_harmful_rate,
                    "blocked_count": len(blocked),
                    "allowed_count": len(allowed),
                    "harmful_count": len(harmful),
                    "beneficial_count": len(beneficial),
                }
            )
    return screens


def _decision(
    source: dict[str, Any],
    ranked: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [screen for screen in ranked if screen["promising_screen"]]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "non_turn_logit_matched_contract_not_ready"
        next_work = "fix_non_turn_logit_matched_contract_before_separability"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_non_turn_logit_matched_label_support_before_training"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_non_turn_logit_matched_label_support_before_training"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_non_turn_logit_interaction_screen_found"
        next_work = "non_turn_logit_interaction_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "comfort_progress_interaction_does_not_separate_candidates"
        next_work = "diagnose_non_turn_logit_interaction_bottleneck_before_retraining"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _source_gate(
    contract: dict[str, Any],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    final = contract.get("final_decision", {})
    dataset_checks = dataset.get("checks", {})
    contract_passed = (
        final.get("status") == CONTRACT_READY_STATUS
        and final.get("passed") is True
        and final.get("authorized_next_work") == CONTRACT_NEXT_WORK
    )
    dataset_passed = (
        dataset.get("passed") is True
        and dataset_checks.get("closed_loop_outcomes_required") is True
        and dataset_checks.get("complete_closed_loop_outcomes") is True
        and dataset_checks.get("finite_candidate_contract_verified") is True
        and dataset_checks.get("forbidden_seed_check") is not False
    )
    return {
        "passed": bool(contract_passed and dataset_passed),
        "contract_status": final.get("status"),
        "contract_passed": bool(contract_passed),
        "matched_dataset_passed": bool(dataset_passed),
        "matched_dataset_checks": dataset_checks,
    }


def _outcome(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    hard_count = sum(
        int(bool(raw.get(field)))
        for field in ("collision", "near_miss", "lane_violation", "red_light_violation")
    )
    value = _float(raw.get("value"))
    progress = _float(raw.get("progress_m"))
    if value is None or progress is None:
        raise ValueError(f"{label} missing finite value/progress_m.")
    return {
        "value": value,
        "progress_m": progress,
        "feasible": bool(raw.get("feasible")),
        "hard_violation_count": hard_count,
    }


def _descriptor_definitions() -> dict[str, dict[str, Any]]:
    return {
        "route_progress_deficit_vs_top1_m": {
            "definition": "max(0, route_progress_candidate0 - route_progress_k)",
            "atom_candidate_eligible": False,
        },
        "dp_prior_jerk_excess_cost": {
            "definition": "max(0, dp_prior_jerk_cost_k - dp_prior_jerk_cost_candidate0)",
            "atom_candidate_eligible": False,
        },
        "comfort_progress_interaction_cost": {
            "definition": "route_progress_deficit_vs_top1_m * dp_prior_jerk_excess_cost",
            "atom_candidate_eligible": True,
        },
    }


def _descriptor_coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    coverage = {}
    for descriptor in _descriptor_definitions():
        finite = sum(
            int(descriptor in row["features"] and np.isfinite(row["features"][descriptor]))
            for row in rows
        )
        nonnegative = sum(
            int(
                descriptor in row["features"]
                and np.isfinite(row["features"][descriptor])
                and row["features"][descriptor] >= -1e-12
            )
            for row in rows
        )
        coverage[descriptor] = {"finite": finite, "nonnegative": nonnegative}
    return coverage


def _class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        CLASS_BENEFICIAL: 0,
        CLASS_HARMFUL: 0,
        CLASS_NEUTRAL: 0,
    }
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return counts


def _discover_logs(paths: list[Path]) -> list[Path]:
    logs = []
    for path in paths:
        if path.is_file():
            logs.append(path)
        elif path.is_dir():
            logs.extend(sorted(path.rglob("camp_selection_log.json")))
    return sorted(dict.fromkeys(logs))


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        value = record.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            value = metadata.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Non-Turn-Logit Interaction Outcome Separability",
        "",
        "This is an offline, read-only screen. Outcome labels are used only for "
        "classification and threshold diagnostics.",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_gate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Screens",
        "",
    ]
    for screen in report["ranked_screens"][:5]:
        lines.append(
            "- `{}`: atom_eligible=`{}`, promising=`{}`, harmful_block_rate=`{:.3f}`, "
            "beneficial_retain_rate=`{:.3f}`, allowed_harmful_rate=`{:.3f}`".format(
                screen["screen_name"],
                screen["atom_candidate_eligible"],
                screen["promising_screen"],
                screen["harmful_block_rate"],
                screen["beneficial_retain_rate"],
                screen["allowed_harmful_rate"],
            )
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
