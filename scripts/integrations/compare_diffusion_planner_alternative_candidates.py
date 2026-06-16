#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_SCREENS = (
    "balanced_lateral_jerk_nondegrading",
    "relaxed_lateral_jerk_nondegrading",
)


@dataclass(frozen=True)
class GateThresholds:
    any_success_rate_min: float = 0.40
    any_success_delta_min: float = 0.15
    guarded_success_rate_min: float = 0.20
    guarded_success_delta_min: float = 0.10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare outcome-free alternative-candidate reports against a "
            "fixed baseline. This is an offline candidate-generation "
            "diagnostic gate only; it does not authorize replay, an online "
            "selector, CAMP retraining, DP retraining, or formal seeds."
        )
    )
    parser.add_argument("--baseline_json", type=Path, required=True)
    parser.add_argument(
        "--candidate_json",
        type=_labeled_path,
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Alternative-candidate report. LABEL= is optional.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--any_success_rate_min", type=float, default=0.40)
    parser.add_argument("--any_success_delta_min", type=float, default=0.15)
    parser.add_argument("--guarded_success_rate_min", type=float, default=0.20)
    parser.add_argument("--guarded_success_delta_min", type=float, default=0.10)
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
        any_success_rate_min=args.any_success_rate_min,
        any_success_delta_min=args.any_success_delta_min,
        guarded_success_rate_min=args.guarded_success_rate_min,
        guarded_success_delta_min=args.guarded_success_delta_min,
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
    required_screens: tuple[str, ...] = REQUIRED_SCREENS,
) -> dict[str, Any]:
    baseline_screens = _screens_by_name(baseline, "baseline", required_screens)
    compared = []
    for label, path, candidate in candidates:
        candidate_screens = _screens_by_name(candidate, label, required_screens)
        screen_rows = [
            _compare_screen(
                name=screen_name,
                baseline=baseline_screens[screen_name],
                candidate=candidate_screens[screen_name],
                thresholds=thresholds,
            )
            for screen_name in required_screens
        ]
        gate_pass = all(row["gates"]["screen_gate_pass"] for row in screen_rows)
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
                "screens": screen_rows,
                "gates": {
                    "alternative_candidate_gate_pass": bool(gate_pass),
                    "latency_gate_pass": None,
                    "latency_gate_reason": (
                        "not evaluated; this report only compares stored "
                        "offline alternative-candidate diagnostics"
                    ),
                },
                "next_step": (
                    "advance_to_generator_side_latency_and_pairing_design"
                    if gate_pass
                    else "reject_current_candidate_generation_grid"
                ),
            }
        )
    return {
        "analysis": {
            "name": "dp_camp_alternative_candidate_comparison_v1",
            "role": (
                "offline comparison gate for fixed-DP candidate-generation "
                "diversity diagnostics"
            ),
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "formal_seeds": False,
            "future_outcome_leakage": (
                "posterior outcomes are report labels only; this comparator "
                "does not select online trajectories"
            ),
            "convexity_boundary": (
                "Changing candidate generation changes the finite candidate "
                "set. For any fixed set, CAMP scoring remains affine in w and "
                "compatible with the simplex/CVaR/L2 convex master. This "
                "comparison is not Benders and makes no trajectory-coordinate "
                "convexity claim."
            ),
            "required_screens": list(required_screens),
        },
        "baseline": {"path": None if baseline_path is None else str(baseline_path)},
        "thresholds": thresholds.__dict__,
        "candidates": compared,
    }


def _compare_screen(
    *,
    name: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    thresholds: GateThresholds,
) -> dict[str, Any]:
    baseline_failure = _failure_records(baseline, f"baseline {name}")
    candidate_failure = _failure_records(candidate, f"candidate {name}")
    baseline_any = _success_count(
        baseline,
        "with_any_admissible_posterior_success",
        baseline_failure,
        f"baseline {name}",
    )
    candidate_any = _success_count(
        candidate,
        "with_any_admissible_posterior_success",
        candidate_failure,
        f"candidate {name}",
    )
    baseline_any_rate = _rate(baseline_any, baseline_failure)
    candidate_any_rate = _rate(candidate_any, candidate_failure)
    guard_rows = _compare_guards(
        baseline=baseline,
        candidate=candidate,
        baseline_failure=baseline_failure,
        candidate_failure=candidate_failure,
        screen_name=name,
    )
    best_guard = max(
        guard_rows,
        key=lambda row: (
            row["guarded_success_rate"]["candidate"],
            row["guarded_success_rate"]["delta"],
            row["name"],
        ),
    )
    any_gate = (
        candidate_any_rate >= thresholds.any_success_rate_min
        and candidate_any_rate - baseline_any_rate >= thresholds.any_success_delta_min
    )
    guarded_gate = (
        best_guard["guarded_success_rate"]["candidate"]
        >= thresholds.guarded_success_rate_min
        and best_guard["guarded_success_rate"]["delta"]
        >= thresholds.guarded_success_delta_min
    )
    return {
        "name": name,
        "failure_records": {
            "baseline": baseline_failure,
            "candidate": candidate_failure,
            "delta": candidate_failure - baseline_failure,
        },
        "any_admissible_posterior_success": {
            "baseline_count": baseline_any,
            "candidate_count": candidate_any,
            "count_delta": candidate_any - baseline_any,
            "baseline_rate": baseline_any_rate,
            "candidate_rate": candidate_any_rate,
            "rate_delta": candidate_any_rate - baseline_any_rate,
        },
        "guard_sets": guard_rows,
        "best_guard_set": best_guard,
        "gates": {
            "any_success_gate_pass": bool(any_gate),
            "guarded_success_gate_pass": bool(guarded_gate),
            "screen_gate_pass": bool(any_gate and guarded_gate),
        },
    }


def _compare_guards(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_failure: int,
    candidate_failure: int,
    screen_name: str,
) -> list[dict[str, Any]]:
    baseline_guards = _guards_by_name(baseline, f"baseline {screen_name}")
    candidate_guards = _guards_by_name(candidate, f"candidate {screen_name}")
    if set(baseline_guards) != set(candidate_guards):
        missing = sorted(set(baseline_guards) - set(candidate_guards))
        extra = sorted(set(candidate_guards) - set(baseline_guards))
        raise ValueError(
            f"{screen_name} guard sets differ; missing={missing}, extra={extra}."
        )
    rows = []
    for name in sorted(baseline_guards):
        base_count = _success_count(
            baseline_guards[name],
            "with_guarded_success",
            baseline_failure,
            f"baseline {screen_name} {name}",
        )
        cand_count = _success_count(
            candidate_guards[name],
            "with_guarded_success",
            candidate_failure,
            f"candidate {screen_name} {name}",
        )
        base_rate = _rate(base_count, baseline_failure)
        cand_rate = _rate(cand_count, candidate_failure)
        reported = float(candidate_guards[name].get("guarded_success_rate", cand_rate))
        if candidate_failure > 0 and abs(reported - cand_rate) > 1e-6:
            raise ValueError(
                f"candidate {screen_name} {name} guarded_success_rate is stale."
            )
        rows.append(
            {
                "name": name,
                "with_guarded_success": {
                    "baseline": base_count,
                    "candidate": cand_count,
                    "delta": cand_count - base_count,
                },
                "guarded_success_rate": {
                    "baseline": base_rate,
                    "candidate": cand_rate,
                    "delta": cand_rate - base_rate,
                },
            }
        )
    return rows


def _screens_by_name(
    report: dict[str, Any],
    label: str,
    required_screens: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    if not isinstance(report.get("records"), dict):
        raise ValueError(f"{label} is missing records.")
    if int(report["records"].get("nonfallback", 0)) <= 0:
        raise ValueError(f"{label} must contain nonfallback records.")
    screens = report.get("screens")
    if not isinstance(screens, list):
        raise ValueError(f"{label} is missing screens.")
    rows: dict[str, dict[str, Any]] = {}
    for screen in screens:
        if not isinstance(screen, dict):
            raise ValueError(f"{label} has a non-object screen row.")
        name = str(screen.get("name", ""))
        if not name:
            raise ValueError(f"{label} has an unnamed screen.")
        if name in rows:
            raise ValueError(f"{label} has duplicate screen {name}.")
        rows[name] = screen
    missing = [name for name in required_screens if name not in rows]
    if missing:
        raise ValueError(f"{label} is missing required screens: {', '.join(missing)}.")
    return rows


def _guards_by_name(screen: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    guards = screen.get("guard_sets")
    if not isinstance(guards, list) or not guards:
        raise ValueError(f"{label} is missing guard_sets.")
    rows: dict[str, dict[str, Any]] = {}
    for guard in guards:
        if not isinstance(guard, dict):
            raise ValueError(f"{label} has a non-object guard row.")
        name = str(guard.get("name", ""))
        if not name:
            raise ValueError(f"{label} has an unnamed guard.")
        if name in rows:
            raise ValueError(f"{label} has duplicate guard {name}.")
        rows[name] = guard
    return rows


def _failure_records(screen: dict[str, Any], label: str) -> int:
    value = int(screen.get("failure_records", -1))
    if value < 0:
        raise ValueError(f"{label} failure_records must be nonnegative.")
    return value


def _success_count(row: dict[str, Any], key: str, total: int, label: str) -> int:
    value = int(row.get(key, -1))
    if value < 0:
        raise ValueError(f"{label} {key} must be nonnegative.")
    if value > total:
        raise ValueError(f"{label} {key} exceeds failure_records.")
    return value


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 1.0
    return count / total


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Alternative Candidate Comparison",
        "",
        "This report compares stored offline alternative-candidate diagnostics "
        "across candidate-generation settings. It does not evaluate latency or "
        "closed-loop performance, and it does not authorize an online selector, "
        "CAMP retraining, DP retraining, or formal seeds.",
        "",
        "| Candidate | Screen | Failures | Any success | Delta | Best guard | "
        "Guard success | Delta | Gate |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for candidate in report["candidates"]:
        for screen in candidate["screens"]:
            any_success = screen["any_admissible_posterior_success"]
            best_guard = screen["best_guard_set"]
            guard_rate = best_guard["guarded_success_rate"]
            gate = screen["gates"]
            lines.append(
                f"| `{candidate['label']}` | `{screen['name']}` | "
                f"{screen['failure_records']['baseline']} -> "
                f"{screen['failure_records']['candidate']} | "
                f"{any_success['baseline_rate']:.6f} -> "
                f"{any_success['candidate_rate']:.6f} | "
                f"{any_success['rate_delta']:+.6f} | "
                f"`{best_guard['name']}` | "
                f"{guard_rate['baseline']:.6f} -> "
                f"{guard_rate['candidate']:.6f} | "
                f"{guard_rate['delta']:+.6f} | "
                f"{_pass_fail(gate['screen_gate_pass'])} |"
            )
    lines.extend(
        [
            "",
            "Gate policy: every required screen must pass both the any-success "
            "coverage threshold and the best predeclared guarded-success "
            "coverage threshold. Passing this report only advances to a "
            "separate generator-side latency and paired-replay design step.",
            "",
            "Mathematical boundary: candidate-generation changes alter the "
            "finite candidate set. For a fixed set, CAMP scoring remains "
            "affine in `w` and compatible with the simplex/CVaR/L2 convex "
            "master. This comparison is not Benders and makes no "
            "trajectory-coordinate convexity claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _pass_fail(value: bool) -> str:
    return "pass" if value else "fail"


if __name__ == "__main__":
    main()
