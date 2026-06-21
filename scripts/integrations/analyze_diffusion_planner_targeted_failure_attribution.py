#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TARGET_BUCKETS = ("traffic_light", "red_light_turn")
SOURCE_GAP_STATUS = "current_selector_gap_open"
TRAINING_DIAG_STATUS = "offline_convex_selector_training_failure_diagnosed"
SENSITIVITY_DIAG_STATUS = (
    "offline_convex_objective_label_sensitivity_results_diagnosed"
)
BRIDGE_STATUS = "current_observable_separability_bridge_duplicate_rejected"
INVENTORY_STATUS = "current_tick_no_leak_atom_support_inventory_no_unclosed_fields"

READY_STATUS = "targeted_failure_attribution_no_current_route"
BLOCKED_STATUS = "targeted_failure_attribution_source_blocked"
AUTHORIZED_NEXT_WORK = (
    "predeclare_new_no_leak_targeted_support_source_or_reject_current_route_only"
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only targeted failure attribution for DP-CAMP. It explains "
            "why traffic-light/red-light-turn buckets fail despite "
            "hard-guarded oracle opportunity."
        )
    )
    parser.add_argument("--targeted_oracle_json", type=Path, required=True)
    parser.add_argument("--selector_gap_json", type=Path, required=True)
    parser.add_argument("--training_failure_diagnosis_json", type=Path, required=True)
    parser.add_argument("--sensitivity_diagnosis_json", type=Path, required=True)
    parser.add_argument("--observable_bridge_json", type=Path, required=True)
    parser.add_argument("--support_inventory_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        targeted_oracle=_load_json(args.targeted_oracle_json),
        selector_gap=_load_json(args.selector_gap_json),
        training_failure_diagnosis=_load_json(args.training_failure_diagnosis_json),
        sensitivity_diagnosis=_load_json(args.sensitivity_diagnosis_json),
        observable_bridge=_load_json(args.observable_bridge_json),
        support_inventory=_load_json(args.support_inventory_json),
        label=args.label,
        paths={
            "targeted_oracle_json": str(args.targeted_oracle_json),
            "selector_gap_json": str(args.selector_gap_json),
            "training_failure_diagnosis_json": str(
                args.training_failure_diagnosis_json
            ),
            "sensitivity_diagnosis_json": str(args.sensitivity_diagnosis_json),
            "observable_bridge_json": str(args.observable_bridge_json),
            "support_inventory_json": str(args.support_inventory_json),
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


def build_report(
    *,
    targeted_oracle: dict[str, Any],
    selector_gap: dict[str, Any],
    training_failure_diagnosis: dict[str, Any],
    sensitivity_diagnosis: dict[str, Any],
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_checks = _source_checks(
        targeted_oracle=targeted_oracle,
        selector_gap=selector_gap,
        training_failure_diagnosis=training_failure_diagnosis,
        sensitivity_diagnosis=sensitivity_diagnosis,
        observable_bridge=observable_bridge,
        support_inventory=support_inventory,
    )
    target_rows = [
        _target_bucket_row(
            bucket,
            targeted_oracle=targeted_oracle,
            selector_gap=selector_gap,
            training_failure_diagnosis=training_failure_diagnosis,
        )
        for bucket in TARGET_BUCKETS
    ]
    prior_route_closures = _prior_route_closures(
        training_failure_diagnosis=training_failure_diagnosis,
        sensitivity_diagnosis=sensitivity_diagnosis,
        observable_bridge=observable_bridge,
        support_inventory=support_inventory,
    )
    passed = all(check["passed"] for check in source_checks)
    final_decision = _final_decision(
        passed=passed,
        target_rows=target_rows,
        prior_route_closures=prior_route_closures,
    )
    return {
        "analysis": {
            "name": "dp_camp_targeted_failure_attribution_v1",
            "label": label,
            "role": (
                "read-only attribution that separates candidate-pool "
                "opportunity from current CAMP selector failure in targeted "
                "traffic-light buckets"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads only existing offline artifacts. DP remains a "
                "fixed black-box candidate generator. Candidate outcomes are "
                "offline labels/evaluation evidence only and are forbidden as "
                "runtime selector inputs. Runtime CAMP features must remain "
                "fixed current-tick finite-candidate coefficients a_k, so "
                "score_k(w)=a_k^T w stays affine and the simplex/CVaR/L2 "
                "robust master remains convex. This is not a DP-side "
                "classical Benders decomposition."
            ),
        },
        "target_buckets": list(TARGET_BUCKETS),
        "source_checks": source_checks,
        "target_bucket_attribution": target_rows,
        "prior_route_closures": prior_route_closures,
        "failure_summary": _failure_summary(target_rows, prior_route_closures),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final_decision,
    }


def _source_checks(
    *,
    targeted_oracle: dict[str, Any],
    selector_gap: dict[str, Any],
    training_failure_diagnosis: dict[str, Any],
    sensitivity_diagnosis: dict[str, Any],
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    oracle_gate = targeted_oracle.get("opportunity_gate") or {}
    gap_decision = selector_gap.get("final_decision") or {}
    training_decision = training_failure_diagnosis.get("final_decision") or {}
    sensitivity_decision = sensitivity_diagnosis.get("final_decision") or {}
    bridge_decision = observable_bridge.get("final_decision") or {}
    bridge_equivalence = observable_bridge.get("equivalence") or {}
    inventory_decision = support_inventory.get("final_decision") or {}
    checks = [
        _check_equal("targeted_oracle_gate_passed", oracle_gate.get("passed"), True),
        _check_equal(
            "targeted_oracle_has_no_formal_seed_logs",
            _get(targeted_oracle, "logs", "formal_seed_logs"),
            0,
        ),
        _check_empty(
            "targeted_oracle_has_no_missing_required_buckets",
            _get(targeted_oracle, "coverage_gaps", "missing_required_buckets")
            or [],
        ),
        _check_equal(
            "selector_gap_status_current",
            gap_decision.get("status"),
            SOURCE_GAP_STATUS,
        ),
        _check_equal("selector_gap_oracle_passed", gap_decision.get("oracle_passed"), True),
        _check_equal(
            "selector_gap_current_selector_not_proven",
            gap_decision.get("evaluated_passed_proof_protocol_v2"),
            False,
        ),
        _check_equal(
            "selector_gap_current_selector_gap_open",
            gap_decision.get("evaluated_gap_closed"),
            False,
        ),
        _check_equal(
            "selector_gap_evaluated_same_as_logged",
            gap_decision.get("evaluated_same_as_logged"),
            True,
        ),
        _check_equal(
            "training_failure_diagnosis_ready",
            training_decision.get("status"),
            TRAINING_DIAG_STATUS,
        ),
        _check_equal(
            "training_failure_selector_rejected",
            training_decision.get("dry_run_selector_rejected"),
            True,
        ),
        _check_equal(
            "sensitivity_diagnosis_ready",
            sensitivity_decision.get("status"),
            SENSITIVITY_DIAG_STATUS,
        ),
        _check_equal(
            "sensitivity_route_rejected",
            sensitivity_decision.get("sensitivity_route_rejected"),
            True,
        ),
        _check_empty(
            "sensitivity_has_no_credible_direction",
            sensitivity_decision.get("credible_direction_candidates") or [],
        ),
        _check_equal(
            "observable_bridge_duplicate_rejected",
            bridge_decision.get("status"),
            BRIDGE_STATUS,
        ),
        _check_equal(
            "observable_bridge_no_materially_new_route",
            bridge_equivalence.get("materially_new_route"),
            False,
        ),
        _check_equal(
            "support_inventory_no_unclosed_fields",
            inventory_decision.get("status"),
            INVENTORY_STATUS,
        ),
        _check_empty(
            "support_inventory_no_admissible_unclosed_families",
            inventory_decision.get("admissible_unclosed_candidate_families") or [],
        ),
    ]
    for bucket in TARGET_BUCKETS:
        checks.append(_target_oracle_check(bucket, targeted_oracle))
        checks.append(_target_selector_failure_check(bucket, selector_gap))
    checks.extend(_blocked_action_checks(gap_decision, "selector_gap"))
    checks.extend(_blocked_action_checks(training_decision, "training_failure"))
    checks.extend(_blocked_action_checks(sensitivity_decision, "sensitivity"))
    checks.extend(_blocked_action_checks(bridge_decision, "observable_bridge"))
    checks.extend(_blocked_action_checks(inventory_decision, "support_inventory"))
    return checks


def _target_oracle_check(bucket: str, report: dict[str, Any]) -> dict[str, Any]:
    entry = _bucket(report.get("by_bucket") or [], bucket)
    ci_high = _ci(entry, "hard_guarded_oracle_minus_top1", "ci95_high")
    return {
        "name": f"{bucket}_hard_guarded_oracle_opportunity",
        "passed": ci_high is not None and ci_high < 0.0 and int(entry.get("records") or 0) > 0,
        "ci95_high": ci_high,
        "records": entry.get("records"),
    }


def _target_selector_failure_check(bucket: str, report: dict[str, Any]) -> dict[str, Any]:
    failures = _get(report, "evaluated_selector", "top1_bucket_failures") or {}
    value = _number(failures.get(bucket))
    return {
        "name": f"{bucket}_current_selector_top1_failure_present",
        "passed": value is not None and value > 0.0,
        "ci95_high": value,
    }


def _target_bucket_row(
    bucket: str,
    *,
    targeted_oracle: dict[str, Any],
    selector_gap: dict[str, Any],
    training_failure_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    oracle_bucket = _bucket(targeted_oracle.get("by_bucket") or [], bucket)
    gap_eval = _get(selector_gap, "evaluated_selector", "by_bucket") or {}
    gap_bucket = gap_eval.get(bucket) if isinstance(gap_eval, dict) else {}
    training_row = _bucket(
        training_failure_diagnosis.get("bucket_diagnosis") or [],
        bucket,
    )
    return {
        "bucket": bucket,
        "oracle": {
            "records": oracle_bucket.get("records"),
            "logs": oracle_bucket.get("logs"),
            "hard_guarded_oracle_minus_top1_mean": _ci(
                oracle_bucket,
                "hard_guarded_oracle_minus_top1",
                "mean",
            ),
            "hard_guarded_oracle_minus_top1_ci95_high": _ci(
                oracle_bucket,
                "hard_guarded_oracle_minus_top1",
                "ci95_high",
            ),
            "camp_minus_top1_ci95_high": _ci(
                oracle_bucket,
                "camp_minus_top1",
                "ci95_high",
            ),
            "hard_guarded_oracle_beats_top1_rate": _get(
                oracle_bucket,
                "record_rates",
                "hard_guarded_oracle_beats_top1",
            ),
        },
        "current_selector_gap": {
            "camp_minus_top1_ci95_high": _gap_bucket_value(
                gap_bucket,
                "camp_minus_top1_ci_high",
                "camp_minus_top1",
            ),
            "camp_minus_hard_guarded_oracle_ci95_high": _gap_bucket_value(
                gap_bucket,
                "camp_minus_hard_guarded_oracle_ci_high",
                "camp_minus_hard_guarded_oracle",
            ),
            "top1_failure_ci95_high": _get(
                selector_gap,
                "evaluated_selector",
                "top1_bucket_failures",
                bucket,
            ),
            "gap_failure_ci95_high": _get(
                selector_gap,
                "evaluated_selector",
                "gap_bucket_failures",
                bucket,
            ),
        },
        "rejected_training_route": {
            "changed_record_rate": training_row.get("changed_record_rate"),
            "evaluated_minus_logged_cost_mean": training_row.get(
                "evaluated_minus_logged_cost_mean"
            ),
            "evaluated_minus_logged_cost_ci_high": training_row.get(
                "evaluated_minus_logged_cost_ci_high"
            ),
            "regression_components": training_row.get("regression_components")
            or [],
            "top_atom_pressure": (training_row.get("atom_pressure") or [])[:8],
            "failure_modes": training_row.get("failure_modes") or {},
            "candidate_pool_coverage": training_row.get("candidate_pool_coverage")
            or {},
        },
        "attribution": _bucket_attribution(
            oracle_bucket=oracle_bucket,
            gap_bucket=gap_bucket,
            training_row=training_row,
        ),
    }


def _bucket_attribution(
    *,
    oracle_bucket: dict[str, Any],
    gap_bucket: dict[str, Any],
    training_row: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    oracle_ci = _ci(oracle_bucket, "hard_guarded_oracle_minus_top1", "ci95_high")
    if oracle_ci is not None and oracle_ci < 0.0:
        reasons.append("candidate_pool_has_hard_guarded_safetycost_opportunity")
    gap_ci = _gap_bucket_value(
        gap_bucket,
        "camp_minus_hard_guarded_oracle_ci_high",
        "camp_minus_hard_guarded_oracle",
    )
    if _number(gap_ci) is not None and float(gap_ci) > 0.0:
        reasons.append("current_selector_does_not_close_hard_guarded_oracle_gap")
    top1_ci = _gap_bucket_value(
        gap_bucket,
        "camp_minus_top1_ci_high",
        "camp_minus_top1",
    )
    if _number(top1_ci) is not None and float(top1_ci) > 0.0:
        reasons.append("current_selector_fails_bucket_top1_gate")
    regressions = {
        str(row.get("name")): _number(row.get("value"))
        for row in training_row.get("regression_components") or []
        if isinstance(row, dict)
    }
    if any((regressions.get(name) or 0.0) > 0.0 for name in ("collision", "near_miss")):
        reasons.append("rejected_training_route_increased_hard_safety_components")
    failure_modes = training_row.get("failure_modes") or {}
    if _number(failure_modes.get("camp_not_hard_guarded_oracle_when_available")):
        reasons.append("available_oracle_candidates_are_not_selected_often_enough")
    return reasons


def _prior_route_closures(
    *,
    training_failure_diagnosis: dict[str, Any],
    sensitivity_diagnosis: dict[str, Any],
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
) -> dict[str, Any]:
    hypotheses = [
        str(row.get("name"))
        for row in training_failure_diagnosis.get("failure_hypotheses") or []
        if isinstance(row, dict)
    ]
    sensitivity_route = sensitivity_diagnosis.get("route_diagnosis") or {}
    bridge_equivalence = observable_bridge.get("equivalence") or {}
    inventory_decision = support_inventory.get("final_decision") or {}
    return {
        "old_training_route_rejected": bool(
            _get(training_failure_diagnosis, "final_decision", "dry_run_selector_rejected")
        ),
        "training_failure_hypotheses": hypotheses,
        "objective_label_sensitivity_rejected": bool(
            _get(sensitivity_diagnosis, "final_decision", "sensitivity_route_rejected")
        ),
        "sensitivity_persistent_failed_checks": sensitivity_route.get(
            "persistent_failed_checks"
        )
        or [],
        "credible_sensitivity_candidates": _get(
            sensitivity_diagnosis,
            "comparison_summary",
            "credible_direction_candidates",
        )
        or [],
        "observable_route_duplicate_rejected": bool(
            _get(observable_bridge, "final_decision", "status") == BRIDGE_STATUS
            and bridge_equivalence.get("duplicate_route_evidence")
            and not bridge_equivalence.get("materially_new_route")
        ),
        "uncovered_observable_fields": bridge_equivalence.get(
            "uncovered_current_material_fields"
        )
        or [],
        "support_inventory_no_unclosed_fields": bool(
            inventory_decision.get("status") == INVENTORY_STATUS
            and not (inventory_decision.get("admissible_unclosed_candidate_families") or [])
        ),
        "available_existing_or_closed_proxy_families": inventory_decision.get(
            "available_existing_or_closed_proxy_families"
        )
        or [],
    }


def _failure_summary(
    target_rows: list[dict[str, Any]],
    prior_route_closures: dict[str, Any],
) -> dict[str, Any]:
    all_have_oracle = all(
        _number(
            row["oracle"]["hard_guarded_oracle_minus_top1_ci95_high"]
        )
        is not None
        and float(row["oracle"]["hard_guarded_oracle_minus_top1_ci95_high"]) < 0.0
        for row in target_rows
    )
    all_current_fail = all(
        _number(row["current_selector_gap"]["top1_failure_ci95_high"]) is not None
        and float(row["current_selector_gap"]["top1_failure_ci95_high"]) > 0.0
        for row in target_rows
    )
    no_new_support = bool(
        prior_route_closures["observable_route_duplicate_rejected"]
        and prior_route_closures["support_inventory_no_unclosed_fields"]
    )
    return {
        "candidate_pool_opportunity_confirmed": all_have_oracle,
        "current_camp_targeted_failure_confirmed": all_current_fail,
        "old_training_and_sensitivity_routes_closed": bool(
            prior_route_closures["old_training_route_rejected"]
            and prior_route_closures["objective_label_sensitivity_rejected"]
        ),
        "new_no_leak_support_missing_in_current_artifacts": no_new_support,
        "primary_attribution": (
            "candidate_pool_has_opportunity_but_current_and_retrained_selectors_lack_no_leak_support"
            if all_have_oracle and all_current_fail and no_new_support
            else "source_evidence_incomplete"
        ),
    }


def _final_decision(
    *,
    passed: bool,
    target_rows: list[dict[str, Any]],
    prior_route_closures: dict[str, Any],
) -> dict[str, Any]:
    summary = _failure_summary(target_rows, prior_route_closures)
    status = READY_STATUS if passed else BLOCKED_STATUS
    return {
        "status": status,
        "passed": passed,
        "current_camp_dp_selector_route_rejected": bool(
            passed
            and summary["candidate_pool_opportunity_confirmed"]
            and summary["current_camp_targeted_failure_confirmed"]
            and summary["old_training_and_sensitivity_routes_closed"]
            and summary["new_no_leak_support_missing_in_current_artifacts"]
        ),
        "primary_attribution": summary["primary_attribution"],
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "predeclare_new_no_leak_targeted_support_source_or_reject_current_route"
            if passed
            else "repair_targeted_failure_attribution_sources"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["failure_summary"]
    lines = [
        "# Targeted DP-CAMP Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        "- Current CAMP-DP selector route rejected: "
        f"`{decision['current_camp_dp_selector_route_rejected']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary attribution: `{decision['primary_attribution']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(
        [
            "",
            "## Target Buckets",
            "",
            "| Bucket | Oracle CI High | CAMP Top-1 CI High | Gap CI High | Training logged CI High | Attribution |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["target_bucket_attribution"]:
        lines.append(
            f"| `{row['bucket']}` | "
            f"{_fmt(row['oracle']['hard_guarded_oracle_minus_top1_ci95_high'])} | "
            f"{_fmt(row['current_selector_gap']['top1_failure_ci95_high'])} | "
            f"{_fmt(row['current_selector_gap']['gap_failure_ci95_high'])} | "
            f"{_fmt(row['rejected_training_route']['evaluated_minus_logged_cost_ci_high'])} | "
            f"`{', '.join(row['attribution'])}` |"
        )
    lines.extend(
        [
            "",
            "## Prior Route Closures",
            "",
        ]
    )
    for key, value in report["prior_route_closures"].items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(["", "## Source Checks", "", "| Check | Passed | Detail |", "| --- | --- | --- |"])
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
    lines.extend(
        [
            "",
            "## Blocked Actions",
            "",
        ]
    )
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision[action]}`")
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


def _blocked_action_checks(decision: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name, False), False)
        for name in BLOCKED_ACTIONS
    ]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_empty(name: str, value: list[Any]) -> dict[str, Any]:
    return {"name": name, "passed": not value, "actual": value, "expected": []}


def _check_detail(check: dict[str, Any]) -> str:
    if "ci95_high" in check:
        return f"ci95_high={_fmt(check.get('ci95_high'))}, records={check.get('records')}"
    return f"actual=`{check.get('actual')}`, expected=`{check.get('expected')}`"


def _bucket(rows: list[Any], name: str) -> dict[str, Any]:
    for row in rows:
        if isinstance(row, dict) and row.get("bucket") == name:
            return row
    return {}


def _ci(entry: dict[str, Any], metric: str, field: str) -> float | None:
    return _number(_get(entry, "run_level_delta_ci", metric, field))


def _gap_bucket_value(entry: dict[str, Any], field: str, legacy_metric: str) -> float | None:
    for value in (
        _number(entry.get(field)),
        _number(_get(entry, "overall", field)),
        _ci(entry, legacy_metric, "ci95_high"),
    ):
        if value is not None:
            return value
    return None


def _get(value: Any, *path: str) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "n/a"
    return f"{number:.6f}"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
