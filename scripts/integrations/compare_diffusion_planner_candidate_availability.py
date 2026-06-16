#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_BUDGETS_M = (0.0, 0.05)
FLOAT_TOL = 1e-9


@dataclass(frozen=True)
class GateThresholds:
    zero_budget_joint_rate_min: float = 0.02
    zero_budget_joint_delta_min: float = 0.015
    budget_005_joint_rate_min: float = 0.15
    budget_005_joint_delta_min: float = 0.08
    feasible_candidate_delta_min: float = 2.0
    hidden_outcome_rate_max: float = 0.05
    zero_budget_proxy_only_rate_max: float = 0.10
    budget_005_proxy_only_rate_max: float = 0.20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare offline DP+CAMP candidate availability reports against a "
            "fixed K=8 baseline. This is a diagnostic gate only; latency and "
            "closed-loop acceptance remain separate."
        )
    )
    parser.add_argument("--baseline_json", type=Path, required=True)
    parser.add_argument(
        "--candidate_json",
        type=_labeled_path,
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Candidate availability report. LABEL= is optional.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--zero_budget_joint_rate_min", type=float, default=0.02)
    parser.add_argument("--zero_budget_joint_delta_min", type=float, default=0.015)
    parser.add_argument("--budget_005_joint_rate_min", type=float, default=0.15)
    parser.add_argument("--budget_005_joint_delta_min", type=float, default=0.08)
    parser.add_argument("--feasible_candidate_delta_min", type=float, default=2.0)
    parser.add_argument("--hidden_outcome_rate_max", type=float, default=0.05)
    parser.add_argument("--zero_budget_proxy_only_rate_max", type=float, default=0.10)
    parser.add_argument("--budget_005_proxy_only_rate_max", type=float, default=0.20)
    return parser.parse_args()


def _labeled_path(value: str) -> tuple[str, Path]:
    if "=" in value:
        label, raw_path = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("Candidate label must be nonempty.")
        return label, Path(raw_path)
    path = Path(value)
    return path.stem, path


def main() -> None:
    args = parse_args()
    thresholds = GateThresholds(
        zero_budget_joint_rate_min=args.zero_budget_joint_rate_min,
        zero_budget_joint_delta_min=args.zero_budget_joint_delta_min,
        budget_005_joint_rate_min=args.budget_005_joint_rate_min,
        budget_005_joint_delta_min=args.budget_005_joint_delta_min,
        feasible_candidate_delta_min=args.feasible_candidate_delta_min,
        hidden_outcome_rate_max=args.hidden_outcome_rate_max,
        zero_budget_proxy_only_rate_max=args.zero_budget_proxy_only_rate_max,
        budget_005_proxy_only_rate_max=args.budget_005_proxy_only_rate_max,
    )
    baseline = _read_json(args.baseline_json)
    candidates = [
        (label, path, _read_json(path)) for label, path in args.candidate_json
    ]
    report = compare_reports(
        baseline=baseline,
        baseline_path=args.baseline_json,
        candidates=candidates,
        thresholds=thresholds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")


def compare_reports(
    *,
    baseline: dict[str, Any],
    baseline_path: Path | None = None,
    candidates: list[tuple[str, Path | None, dict[str, Any]]],
    thresholds: GateThresholds = GateThresholds(),
) -> dict[str, Any]:
    _validate_report(baseline, "baseline")
    baseline_budgets = _budgets_by_value(baseline, "baseline")
    baseline_feasible = _mean_feasible_candidates(baseline, "baseline")
    compared: list[dict[str, Any]] = []
    for label, path, candidate in candidates:
        _validate_report(candidate, label)
        candidate_budgets = _budgets_by_value(candidate, label)
        missing_budgets = sorted(set(baseline_budgets) - set(candidate_budgets))
        if missing_budgets:
            formatted = ", ".join(f"{budget:.2f}" for budget in missing_budgets)
            raise ValueError(f"{label} is missing baseline budgets: {formatted}.")
        budget_rows = [
            _compare_budget(
                budget=budget,
                baseline=baseline_budgets[budget],
                candidate=candidate_budgets[budget],
            )
            for budget in sorted(baseline_budgets)
        ]
        candidate_feasible = _mean_feasible_candidates(candidate, label)
        feasible_delta = candidate_feasible - baseline_feasible
        gates = _evaluate_gates(
            budget_rows=budget_rows,
            feasible_delta=feasible_delta,
            thresholds=thresholds,
        )
        compared.append(
            {
                "label": label,
                "path": None if path is None else str(path),
                "records": {
                    "baseline_nonfallback": int(baseline["records"]["nonfallback"]),
                    "candidate_nonfallback": int(candidate["records"]["nonfallback"]),
                    "nonfallback_delta": int(candidate["records"]["nonfallback"])
                    - int(baseline["records"]["nonfallback"]),
                },
                "diversity": {
                    "baseline_mean_feasible_candidates": baseline_feasible,
                    "candidate_mean_feasible_candidates": candidate_feasible,
                    "mean_feasible_candidate_delta": feasible_delta,
                },
                "budgets": budget_rows,
                "gates": gates,
                "next_step": (
                    "advance_to_no_outcome_latency_smoke"
                    if gates["availability_gate_pass"]
                    and gates["proxy_reliability_gate_pass"]
                    and gates["candidate_pool_gate_pass"]
                    else "reject_or_redesign_candidate_generation"
                ),
            }
        )
    return {
        "analysis": {
            "name": "dp_camp_candidate_availability_comparison_v1",
            "role": "offline comparison gate for candidate-generation diagnostics",
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "latency_gate": "not_evaluated_by_this_report",
            "closed_loop_acceptance_gate": "not_evaluated_by_this_report",
            "required_progress_budgets_m": list(REQUIRED_BUDGETS_M),
        },
        "baseline": {"path": None if baseline_path is None else str(baseline_path)},
        "thresholds": thresholds.__dict__,
        "candidates": compared,
    }


def _compare_budget(
    *,
    budget: float,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "progress_budget_m": budget,
        "outcome_joint_rate": {
            "baseline": float(baseline["outcome_joint_rate"]),
            "candidate": float(candidate["outcome_joint_rate"]),
            "delta": float(candidate["outcome_joint_rate"])
            - float(baseline["outcome_joint_rate"]),
        },
        "outcome_weak_rate": {
            "baseline": float(baseline["outcome_weak_rate"]),
            "candidate": float(candidate["outcome_weak_rate"]),
            "delta": float(candidate["outcome_weak_rate"])
            - float(baseline["outcome_weak_rate"]),
        },
        "hidden_outcome_weak_rate": {
            "baseline": float(baseline["hidden_outcome_weak_rate"]),
            "candidate": float(candidate["hidden_outcome_weak_rate"]),
            "delta": float(candidate["hidden_outcome_weak_rate"])
            - float(baseline["hidden_outcome_weak_rate"]),
        },
        "proxy_only_weak_rate": {
            "baseline": float(baseline["proxy_only_weak_rate"]),
            "candidate": float(candidate["proxy_only_weak_rate"]),
            "delta": float(candidate["proxy_only_weak_rate"])
            - float(baseline["proxy_only_weak_rate"]),
        },
    }


def _evaluate_gates(
    *,
    budget_rows: list[dict[str, Any]],
    feasible_delta: float,
    thresholds: GateThresholds,
) -> dict[str, Any]:
    by_budget = {row["progress_budget_m"]: row for row in budget_rows}
    zero = by_budget[0.0]
    b005 = by_budget[0.05]
    availability = (
        zero["outcome_joint_rate"]["candidate"]
        >= thresholds.zero_budget_joint_rate_min
        and zero["outcome_joint_rate"]["delta"]
        >= thresholds.zero_budget_joint_delta_min
        and b005["outcome_joint_rate"]["candidate"]
        >= thresholds.budget_005_joint_rate_min
        and b005["outcome_joint_rate"]["delta"]
        >= thresholds.budget_005_joint_delta_min
    )
    proxy_reliability = (
        zero["hidden_outcome_weak_rate"]["candidate"]
        <= thresholds.hidden_outcome_rate_max
        and b005["hidden_outcome_weak_rate"]["candidate"]
        <= thresholds.hidden_outcome_rate_max
        and zero["proxy_only_weak_rate"]["candidate"]
        <= thresholds.zero_budget_proxy_only_rate_max
        and b005["proxy_only_weak_rate"]["candidate"]
        <= thresholds.budget_005_proxy_only_rate_max
    )
    candidate_pool = feasible_delta >= thresholds.feasible_candidate_delta_min
    return {
        "availability_gate_pass": bool(availability),
        "proxy_reliability_gate_pass": bool(proxy_reliability),
        "candidate_pool_gate_pass": bool(candidate_pool),
        "latency_gate_pass": None,
        "latency_gate_reason": "not evaluated; run no-outcome latency smoke separately",
    }


def _validate_report(report: dict[str, Any], label: str) -> None:
    if not isinstance(report.get("records"), dict):
        raise ValueError(f"{label} is missing records.")
    if int(report["records"].get("nonfallback", 0)) <= 0:
        raise ValueError(f"{label} must contain nonfallback records.")
    if not isinstance(report.get("budgets"), list):
        raise ValueError(f"{label} is missing budgets.")
    budgets = _budgets_by_value(report, label)
    for budget in REQUIRED_BUDGETS_M:
        if budget not in budgets:
            raise ValueError(f"{label} is missing progress budget {budget:.2f}.")
    _mean_feasible_candidates(report, label)


def _budgets_by_value(report: dict[str, Any], label: str) -> dict[float, dict[str, Any]]:
    rows: dict[float, dict[str, Any]] = {}
    for row in report.get("budgets", []):
        budget = _canonical_budget(row.get("progress_budget_m"))
        if budget in rows:
            raise ValueError(f"{label} has duplicate budget {budget:.2f}.")
        for key in (
            "outcome_joint_rate",
            "outcome_weak_rate",
            "hidden_outcome_weak_rate",
            "proxy_only_weak_rate",
        ):
            value = float(row.get(key))
            if value < -FLOAT_TOL or value > 1.0 + FLOAT_TOL:
                raise ValueError(f"{label} {key} for {budget:.2f} is not a rate.")
        rows[budget] = row
    return rows


def _canonical_budget(value: Any) -> float:
    budget = round(float(value), 8)
    if budget < -FLOAT_TOL:
        raise ValueError("Progress budgets must be nonnegative.")
    return budget


def _mean_feasible_candidates(report: dict[str, Any], label: str) -> float:
    diversity = report.get("diversity")
    if not isinstance(diversity, dict):
        raise ValueError(f"{label} is missing diversity.")
    value = float(diversity.get("mean_feasible_candidates"))
    if value <= 0.0:
        raise ValueError(f"{label} mean feasible candidates must be positive.")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Candidate Availability Comparison",
        "",
        "This report compares offline outcome-labeled candidate availability "
        "against the fixed K=8 baseline. It is not a latency, closed-loop, or "
        "formal-seed gate.",
        "",
        "| Candidate | Feasible delta | Joint@0.00 | Delta@0.00 | Joint@0.05 | "
        "Delta@0.05 | Hidden@0.05 | Proxy-only@0.05 | Gates | Next step |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for candidate in report["candidates"]:
        by_budget = {
            row["progress_budget_m"]: row for row in candidate["budgets"]
        }
        zero = by_budget[0.0]
        b005 = by_budget[0.05]
        gates = candidate["gates"]
        gate_text = (
            f"availability={_pass_fail(gates['availability_gate_pass'])}, "
            f"proxy={_pass_fail(gates['proxy_reliability_gate_pass'])}, "
            f"pool={_pass_fail(gates['candidate_pool_gate_pass'])}, "
            "latency=not-evaluated"
        )
        lines.append(
            f"| `{candidate['label']}` | "
            f"{candidate['diversity']['mean_feasible_candidate_delta']:+.6f} | "
            f"{zero['outcome_joint_rate']['candidate']:.6f} | "
            f"{zero['outcome_joint_rate']['delta']:+.6f} | "
            f"{b005['outcome_joint_rate']['candidate']:.6f} | "
            f"{b005['outcome_joint_rate']['delta']:+.6f} | "
            f"{b005['hidden_outcome_weak_rate']['candidate']:.6f} | "
            f"{b005['proxy_only_weak_rate']['candidate']:.6f} | "
            f"{gate_text} | `{candidate['next_step']}` |"
        )
    lines.extend(
        [
            "",
            "Passing this diagnostic only advances a configuration to a separate "
            "no-outcome latency smoke. It does not authorize an online selector, "
            "CAMP retraining, formal seeds, or a 12/36-run acceptance matrix.",
            "",
        ]
    )
    return "\n".join(lines)


def _pass_fail(value: bool) -> str:
    return "pass" if value else "fail"


if __name__ == "__main__":
    main()
