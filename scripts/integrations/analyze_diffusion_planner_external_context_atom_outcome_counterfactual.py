#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_external_context_atom_schema_dry_run import (  # noqa: E402
    _argmin_with_lowest_index_tie_break,
    _atom_coefficients,
    _combined_scores,
)
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    EPS,
    FORMAL_SEEDS,
    _candidate_branch_components,
    _outcome_float,
    _outcomes,
    _planned_red_values,
)


ATOMIZATION_READY_STATUS = "external_context_atomization_preflight_ready"
ATOMIZATION_NEXT_WORK = "external_context_atom_schema_dry_run_existing_smoke_only"
READY_STATUS = "external_context_atom_outcome_counterfactual_ready"
REJECT_STATUS = "external_context_atom_outcome_counterfactual_rejected"
LOG_NAME = "camp_selection_log.json"
HARD_OUTCOME_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only outcome counterfactual for external-context atom-best "
            "selection. Outcomes are posterior labels only and never enter the "
            "deployable atom payload or online selector."
        )
    )
    parser.add_argument("--atomization_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_records", type=int, default=3)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--progress_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        atomization=_load_json(args.atomization_json),
        candidate_root=args.candidate_root,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        progress_loss_budget_m=args.progress_loss_budget_m,
        label=args.label,
        paths={
            "atomization_json": str(args.atomization_json),
            "candidate_root": str(args.candidate_root),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    *,
    atomization: dict[str, Any],
    candidate_root: Path,
    expected_records: int = 3,
    expected_candidates: int = 8,
    progress_loss_budget_m: float = 0.10,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if progress_loss_budget_m < 0.0:
        raise ValueError("progress_loss_budget_m must be nonnegative.")

    records = _load_records(candidate_root)
    source = _source_gate(atomization)
    selected_specs = [
        row for row in atomization.get("selected_atom_candidates") or []
        if isinstance(row, dict)
    ]
    source_checks = _source_checks(source)
    record_checks = _record_checks(
        records,
        expected_records=expected_records,
        expected_candidates=expected_candidates,
    )
    rows = [
        _counterfactual_row(
            index,
            record,
            selected_specs,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        for index, record in enumerate(records)
    ]
    row_checks = [
        {
            "name": "all_rows_evaluated",
            "passed": all(row["passed"] for row in rows),
            "actual": [row.get("reason") for row in rows if not row["passed"]],
            "expected": [],
        },
        {
            "name": "atom_best_ranking_signal_present",
            "passed": any(row["ranking_signal_present"] for row in rows),
            "actual": sum(int(row["ranking_signal_present"]) for row in rows),
            "expected": ">=1",
        },
    ]
    summary = _summary(rows)
    passed = (
        all(check["passed"] for check in source_checks)
        and all(check["passed"] for check in record_checks)
        and all(check["passed"] for check in row_checks)
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_atom_outcome_counterfactual_v1",
            "label": label,
            "role": (
                "posterior outcome-label evaluation of external-context atom-best "
                "selection over fixed DP candidate pools"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "deployed_atom_schema_change": False,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_evaluation": True,
            "formal_seed_records": 0,
            "progress_loss_budget_m": float(progress_loss_budget_m),
            "paths": paths or {},
            "math_boundary": (
                "Atom-best selection is computed only from fixed current-tick "
                "finite-candidate atom coefficients selected by the atomization "
                "preflight. Candidate closed-loop outcomes are posterior labels "
                "used only to evaluate the counterfactual SafetyCost v1 deltas. "
                "They do not enter the deployable atom coefficients, online "
                "selection, CAMP training, or any Benders cut. The atom score "
                "remains score_k(w)=a_k^T w over fixed coefficients, preserving "
                "the convex simplex/CVaR/L2 master."
            ),
        },
        "source_atomization_gate": source,
        "source_checks": source_checks,
        "record_checks": record_checks,
        "counterfactual_rows": rows,
        "counterfactual_checks": row_checks,
        "summary": summary,
        "final_decision": _final_decision(passed, summary),
    }


def _source_gate(atomization: dict[str, Any]) -> dict[str, Any]:
    decision = atomization.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_atom_candidate_names": list(
            decision.get("selected_atom_candidate_names") or []
        ),
        "blocked_action_conflicts": [
            key
            for key in (
                "camp_retraining_authorized",
                "online_selector_authorized",
                "formal_seeds_authorized",
                "dp_modification_authorized",
                "classic_benders_claim_authorized",
            )
            if bool(decision.get(key))
        ],
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], ATOMIZATION_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorized_atom_dry_run",
            source["authorized_next_work"],
            ATOMIZATION_NEXT_WORK,
        ),
        _check_equal(
            "source_selected_atoms_nonempty",
            bool(source["selected_atom_candidate_names"]),
            True,
        ),
        _check_equal("source_blocked_action_conflicts_empty", source["blocked_action_conflicts"], []),
    ]


def _record_checks(
    records: list[dict[str, Any]],
    *,
    expected_records: int,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    checks = [_check_equal("record_count", len(records), expected_records)]
    for index, record in enumerate(records):
        label = f"record_{index}"
        payload = record.get("external_context_payload_logging")
        outcomes = record.get("candidate_closed_loop_outcomes")
        checks.extend(
            [
                _check_equal(f"{label}_payload_present", isinstance(payload, dict), True),
                _check_equal(f"{label}_outcomes_present", isinstance(outcomes, list), True),
                _check_equal(f"{label}_candidate_count", int(record.get("num_candidates", 0)), expected_candidates),
                _check_equal(f"{label}_formal_seed", int(record.get("seed", -1)) in FORMAL_SEEDS, False),
            ]
        )
        if isinstance(outcomes, list):
            checks.append(_check_equal(f"{label}_outcome_count", len(outcomes), expected_candidates))
    return checks


def _counterfactual_row(
    index: int,
    record: dict[str, Any],
    selected_specs: list[dict[str, Any]],
    *,
    progress_loss_budget_m: float,
) -> dict[str, Any]:
    payload = record.get("external_context_payload_logging")
    if not isinstance(payload, dict):
        return {"record_index": index, "passed": False, "reason": "payload_missing"}
    candidate_count = int(payload.get("candidate_count", record.get("num_candidates", 0)))
    atom_scores: dict[str, list[float]] = {}
    for spec in selected_specs:
        atom_scores[str(spec.get("name"))] = _atom_coefficients(spec, payload, candidate_count)
    combined = _combined_scores(atom_scores, candidate_count)
    atom_best = _argmin_with_lowest_index_tie_break(combined)
    selected = int(record.get("selected_index"))
    top1 = 0
    outcomes = _outcomes(
        record.get("candidate_closed_loop_outcomes"),
        candidate_count,
        f"record {index} outcomes",
    )
    planned_red, planned_red_source = _planned_red_values(record, candidate_count)
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        feasible = np.ones(candidate_count, dtype=bool)
    components = _candidate_branch_components(outcomes, planned_red, feasible)
    if atom_best is None:
        return {"record_index": index, "passed": False, "reason": "atom_best_missing"}
    selected_cost = float(components[selected]["cost"])
    atom_cost = float(components[atom_best]["cost"])
    top1_cost = float(components[top1]["cost"])
    selected_progress = _outcome_float(outcomes[selected], "progress_m")
    atom_progress = _outcome_float(outcomes[atom_best], "progress_m")
    route_progress = _candidate_route_progress(record, candidate_count)
    guarded_atom_best = _guarded_atom_best_index(
        combined,
        route_progress,
        selected,
        progress_loss_budget_m=progress_loss_budget_m,
    )
    selected_preserving_guarded = _selected_preserving_guarded_atom_best_index(
        combined,
        route_progress,
        selected,
        progress_loss_budget_m=progress_loss_budget_m,
    )
    guarded_cost = float(components[guarded_atom_best]["cost"])
    selected_preserving_cost = float(components[selected_preserving_guarded]["cost"])
    guarded_progress = _outcome_float(outcomes[guarded_atom_best], "progress_m")
    selected_preserving_progress = _outcome_float(
        outcomes[selected_preserving_guarded],
        "progress_m",
    )
    return {
        "record_index": index,
        "passed": True,
        "selected_index": selected,
        "atom_best_index": int(atom_best),
        "guarded_atom_best_index": int(guarded_atom_best),
        "selected_preserving_guarded_atom_best_index": int(selected_preserving_guarded),
        "top1_index": top1,
        "would_change_selected_index": bool(atom_best != selected),
        "guarded_would_change_selected_index": bool(guarded_atom_best != selected),
        "selected_preserving_guarded_would_change_selected_index": bool(
            selected_preserving_guarded != selected
        ),
        "ranking_signal_present": bool(combined and max(combined) > min(combined)),
        "combined_atom_score": combined,
        "candidate_route_progress": route_progress,
        "planned_red_source": planned_red_source,
        "costs": {
            "selected": selected_cost,
            "atom_best": atom_cost,
            "guarded_atom_best": guarded_cost,
            "selected_preserving_guarded_atom_best": selected_preserving_cost,
            "top1": top1_cost,
        },
        "deltas": {
            "atom_best_minus_selected_cost": atom_cost - selected_cost,
            "guarded_atom_best_minus_selected_cost": guarded_cost - selected_cost,
            "selected_preserving_guarded_atom_best_minus_selected_cost": (
                selected_preserving_cost - selected_cost
            ),
            "atom_best_minus_top1_cost": atom_cost - top1_cost,
            "guarded_atom_best_minus_top1_cost": guarded_cost - top1_cost,
            "selected_preserving_guarded_atom_best_minus_top1_cost": (
                selected_preserving_cost - top1_cost
            ),
            "selected_minus_top1_cost": selected_cost - top1_cost,
            "atom_best_progress_minus_selected_m": atom_progress - selected_progress,
            "guarded_atom_best_progress_minus_selected_m": (
                guarded_progress - selected_progress
            ),
            "selected_preserving_guarded_atom_best_progress_minus_selected_m": (
                selected_preserving_progress - selected_progress
            ),
            "guarded_route_progress_minus_selected_m": (
                route_progress[guarded_atom_best] - route_progress[selected]
            ),
            "selected_preserving_guarded_route_progress_minus_selected_m": (
                route_progress[selected_preserving_guarded] - route_progress[selected]
            ),
        },
        "relations": {
            "atom_best_better_than_selected": atom_cost < selected_cost - EPS,
            "atom_best_noninferior_to_selected": atom_cost <= selected_cost + EPS,
            "atom_best_progress_within_budget": (
                atom_progress + progress_loss_budget_m >= selected_progress
            ),
            "atom_best_hard_nonworse_than_selected": _hard_nonworse(
                outcomes[atom_best],
                outcomes[selected],
            ),
            "guarded_atom_best_better_than_selected": (
                guarded_cost < selected_cost - EPS
            ),
            "guarded_atom_best_noninferior_to_selected": (
                guarded_cost <= selected_cost + EPS
            ),
            "guarded_atom_best_progress_within_budget": (
                guarded_progress + progress_loss_budget_m >= selected_progress
            ),
            "guarded_atom_best_hard_nonworse_than_selected": _hard_nonworse(
                outcomes[guarded_atom_best],
                outcomes[selected],
            ),
            "selected_preserving_guarded_atom_best_better_than_selected": (
                selected_preserving_cost < selected_cost - EPS
            ),
            "selected_preserving_guarded_atom_best_noninferior_to_selected": (
                selected_preserving_cost <= selected_cost + EPS
            ),
            "selected_preserving_guarded_atom_best_progress_within_budget": (
                selected_preserving_progress + progress_loss_budget_m >= selected_progress
            ),
            "selected_preserving_guarded_atom_best_hard_nonworse_than_selected": (
                _hard_nonworse(outcomes[selected_preserving_guarded], outcomes[selected])
            ),
        },
        "component_costs": {
            "selected": components[selected],
            "atom_best": components[atom_best],
            "guarded_atom_best": components[guarded_atom_best],
            "selected_preserving_guarded_atom_best": components[
                selected_preserving_guarded
            ],
            "top1": components[top1],
        },
        "future_outcome_labels_used_for_atoms": False,
        "future_outcome_labels_used_for_evaluation": True,
    }


def _hard_nonworse(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return all(
        float(bool(candidate[field])) <= float(bool(baseline[field]))
        for field in HARD_OUTCOME_FIELDS
    )


def _candidate_route_progress(record: dict[str, Any], candidate_count: int) -> list[float]:
    values = record.get("candidate_route_progress")
    if not isinstance(values, list) or len(values) != candidate_count:
        raise ValueError("candidate_route_progress must match candidate count.")
    parsed = [float(value) for value in values]
    if not all(np.isfinite(value) for value in parsed):
        raise ValueError("candidate_route_progress must be finite.")
    return parsed


def _guarded_atom_best_index(
    scores: list[float],
    route_progress: list[float],
    selected_index: int,
    *,
    progress_loss_budget_m: float,
) -> int:
    selected_progress = route_progress[selected_index]
    eligible = [
        index
        for index, progress in enumerate(route_progress)
        if progress + progress_loss_budget_m >= selected_progress
    ]
    if not eligible:
        return selected_index
    best = eligible[0]
    best_score = float(scores[best])
    for index in eligible[1:]:
        score = float(scores[index])
        if score < best_score:
            best = index
            best_score = score
    return int(best)


def _selected_preserving_guarded_atom_best_index(
    scores: list[float],
    route_progress: list[float],
    selected_index: int,
    *,
    progress_loss_budget_m: float,
) -> int:
    selected_progress = route_progress[selected_index]
    eligible = [
        index
        for index, progress in enumerate(route_progress)
        if progress + progress_loss_budget_m >= selected_progress
    ]
    if not eligible:
        return selected_index
    best_score = min(float(scores[index]) for index in eligible)
    selected_score = float(scores[selected_index])
    if selected_index in eligible and selected_score <= best_score + EPS:
        return selected_index
    best = eligible[0]
    best_value = float(scores[best])
    for index in eligible[1:]:
        value = float(scores[index])
        if value < best_value:
            best = index
            best_value = value
    return int(best)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row.get("passed")]
    deltas = [float(row["deltas"]["atom_best_minus_selected_cost"]) for row in valid]
    guarded_deltas = [
        float(row["deltas"]["guarded_atom_best_minus_selected_cost"]) for row in valid
    ]
    selected_preserving_deltas = [
        float(row["deltas"]["selected_preserving_guarded_atom_best_minus_selected_cost"])
        for row in valid
    ]
    changed = [row for row in valid if row["would_change_selected_index"]]
    guarded_changed = [
        row for row in valid if row["guarded_would_change_selected_index"]
    ]
    selected_preserving_changed = [
        row for row in valid
        if row["selected_preserving_guarded_would_change_selected_index"]
    ]
    better = [row for row in valid if row["relations"]["atom_best_better_than_selected"]]
    noninferior = [row for row in valid if row["relations"]["atom_best_noninferior_to_selected"]]
    hard = [row for row in valid if row["relations"]["atom_best_hard_nonworse_than_selected"]]
    progress = [row for row in valid if row["relations"]["atom_best_progress_within_budget"]]
    guarded_better = [
        row for row in valid if row["relations"]["guarded_atom_best_better_than_selected"]
    ]
    guarded_noninferior = [
        row for row in valid if row["relations"]["guarded_atom_best_noninferior_to_selected"]
    ]
    guarded_hard = [
        row for row in valid
        if row["relations"]["guarded_atom_best_hard_nonworse_than_selected"]
    ]
    guarded_progress = [
        row for row in valid
        if row["relations"]["guarded_atom_best_progress_within_budget"]
    ]
    selected_preserving_better = [
        row for row in valid
        if row["relations"][
            "selected_preserving_guarded_atom_best_better_than_selected"
        ]
    ]
    selected_preserving_noninferior = [
        row for row in valid
        if row["relations"][
            "selected_preserving_guarded_atom_best_noninferior_to_selected"
        ]
    ]
    selected_preserving_hard = [
        row for row in valid
        if row["relations"][
            "selected_preserving_guarded_atom_best_hard_nonworse_than_selected"
        ]
    ]
    selected_preserving_progress = [
        row for row in valid
        if row["relations"][
            "selected_preserving_guarded_atom_best_progress_within_budget"
        ]
    ]
    return {
        "records": len(rows),
        "valid_records": len(valid),
        "changed_records": len(changed),
        "guarded_changed_records": len(guarded_changed),
        "selected_preserving_guarded_changed_records": len(selected_preserving_changed),
        "ranking_signal_records": sum(int(row["ranking_signal_present"]) for row in valid),
        "atom_best_better_records": len(better),
        "atom_best_noninferior_records": len(noninferior),
        "atom_best_hard_nonworse_records": len(hard),
        "atom_best_progress_within_budget_records": len(progress),
        "guarded_atom_best_better_records": len(guarded_better),
        "guarded_atom_best_noninferior_records": len(guarded_noninferior),
        "guarded_atom_best_hard_nonworse_records": len(guarded_hard),
        "guarded_atom_best_progress_within_budget_records": len(guarded_progress),
        "selected_preserving_guarded_atom_best_better_records": len(
            selected_preserving_better
        ),
        "selected_preserving_guarded_atom_best_noninferior_records": len(
            selected_preserving_noninferior
        ),
        "selected_preserving_guarded_atom_best_hard_nonworse_records": len(
            selected_preserving_hard
        ),
        "selected_preserving_guarded_atom_best_progress_within_budget_records": len(
            selected_preserving_progress
        ),
        "atom_best_minus_selected_cost_mean": _mean(deltas),
        "guarded_atom_best_minus_selected_cost_mean": _mean(guarded_deltas),
        "selected_preserving_guarded_atom_best_minus_selected_cost_mean": _mean(
            selected_preserving_deltas
        ),
        "atom_best_minus_selected_cost_values": deltas,
        "guarded_atom_best_minus_selected_cost_values": guarded_deltas,
        "selected_preserving_guarded_atom_best_minus_selected_cost_values": (
            selected_preserving_deltas
        ),
    }


def _final_decision(passed: bool, summary: dict[str, Any]) -> dict[str, Any]:
    valid = int(summary["valid_records"])
    noninferior_all = valid > 0 and summary["atom_best_noninferior_records"] == valid
    hard_all = valid > 0 and summary["atom_best_hard_nonworse_records"] == valid
    progress_all = valid > 0 and summary["atom_best_progress_within_budget_records"] == valid
    guarded_noninferior_all = (
        valid > 0 and summary["guarded_atom_best_noninferior_records"] == valid
    )
    guarded_hard_all = (
        valid > 0 and summary["guarded_atom_best_hard_nonworse_records"] == valid
    )
    guarded_progress_all = (
        valid > 0 and summary["guarded_atom_best_progress_within_budget_records"] == valid
    )
    selected_preserving_noninferior_all = (
        valid > 0
        and summary["selected_preserving_guarded_atom_best_noninferior_records"] == valid
    )
    selected_preserving_hard_all = (
        valid > 0
        and summary["selected_preserving_guarded_atom_best_hard_nonworse_records"] == valid
    )
    selected_preserving_progress_all = (
        valid > 0
        and summary[
            "selected_preserving_guarded_atom_best_progress_within_budget_records"
        ]
        == valid
    )
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": None,
        "closed_loop_replay_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "promotion_authorized": False,
        "tiny_counterfactual_noninferior": bool(noninferior_all and hard_all and progress_all),
        "guarded_tiny_counterfactual_noninferior": bool(
            guarded_noninferior_all and guarded_hard_all and guarded_progress_all
        ),
        "selected_preserving_guarded_tiny_counterfactual_noninferior": bool(
            selected_preserving_noninferior_all
            and selected_preserving_hard_all
            and selected_preserving_progress_all
        ),
        "next_step": (
            "Use this tiny posterior-label result only to decide whether a "
            "predeclared broader nonformal outcome gate is justified; do not "
            "deploy, train, or enter Full36 from this artifact."
            if passed
            else "Reject the counterfactual and inspect failed source, record, or row checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["summary"]
    lines = [
        "# External Context Atom Outcome Counterfactual",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Promotion authorized: `{decision['promotion_authorized']}`",
        f"- Tiny counterfactual noninferior: `{decision['tiny_counterfactual_noninferior']}`",
        f"- Valid records: `{summary['valid_records']}`",
        f"- Changed records: `{summary['changed_records']}`",
        f"- Guarded changed records: `{summary['guarded_changed_records']}`",
        f"- Selected-preserving guarded changed records: `{summary['selected_preserving_guarded_changed_records']}`",
        f"- Atom-best better records: `{summary['atom_best_better_records']}`",
        f"- Guarded atom-best better records: `{summary['guarded_atom_best_better_records']}`",
        f"- Selected-preserving guarded atom-best better records: `{summary['selected_preserving_guarded_atom_best_better_records']}`",
        f"- Atom-best noninferior records: `{summary['atom_best_noninferior_records']}`",
        f"- Guarded atom-best noninferior records: `{summary['guarded_atom_best_noninferior_records']}`",
        f"- Selected-preserving guarded atom-best noninferior records: `{summary['selected_preserving_guarded_atom_best_noninferior_records']}`",
        f"- Mean atom-best minus selected SafetyCost: `{summary['atom_best_minus_selected_cost_mean']}`",
        f"- Mean guarded atom-best minus selected SafetyCost: `{summary['guarded_atom_best_minus_selected_cost_mean']}`",
        f"- Mean selected-preserving guarded atom-best minus selected SafetyCost: `{summary['selected_preserving_guarded_atom_best_minus_selected_cost_mean']}`",
        "",
        "## Record Effects",
        "",
    ]
    for row in report["counterfactual_rows"]:
        if not row.get("passed"):
            lines.append(f"- record `{row['record_index']}` failed: `{row.get('reason')}`")
            continue
        lines.append(
            f"- record `{row['record_index']}`: selected=`{row['selected_index']}`, "
            f"atom_best=`{row['atom_best_index']}`, "
            f"guarded_atom_best=`{row['guarded_atom_best_index']}`, "
            f"selected_preserving_guarded_atom_best=`{row['selected_preserving_guarded_atom_best_index']}`, "
            f"delta_cost=`{row['deltas']['atom_best_minus_selected_cost']}`, "
            f"guarded_delta_cost=`{row['deltas']['guarded_atom_best_minus_selected_cost']}`, "
            f"selected_preserving_guarded_delta_cost=`{row['deltas']['selected_preserving_guarded_atom_best_minus_selected_cost']}`, "
            f"hard_nonworse=`{row['relations']['atom_best_hard_nonworse_than_selected']}`"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_records(root: Path) -> list[dict[str, Any]]:
    paths = iter_selection_log_paths([root])
    if not paths:
        raise FileNotFoundError(f"No {LOG_NAME} found under {root}")
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        records.extend(row for row in payload if isinstance(row, dict))
    return records


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
