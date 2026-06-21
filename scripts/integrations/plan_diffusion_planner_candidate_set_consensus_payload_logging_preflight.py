#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

MATERIALITY_STATUS = "candidate_set_consensus_existing_log_materiality_insufficient"
MATERIALITY_NEXT_WORK = "candidate_set_consensus_default_off_payload_logging_preflight_only"

READY_STATUS = "candidate_set_consensus_payload_logging_preflight_ready"
BLOCKED_STATUS = "candidate_set_consensus_payload_logging_preflight_blocked"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_payload_implementation_unit_tests_only"

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


@dataclass(frozen=True)
class SourceHook:
    name: str
    required_tokens: tuple[str, ...]
    rationale: str


SOURCE_HOOKS: tuple[SourceHook, ...] = (
    SourceHook(
        name="fixed_candidate_tensor_available_before_selection",
        required_tokens=(
            "candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories",
            "candidate_generation_done = time.perf_counter()",
        ),
        rationale="payload must compute from the fixed current-tick DP candidate tensor before selection",
    ),
    SourceHook(
        name="selection_log_append_site_available",
        required_tokens=(
            "records.append(",
            "\"selected_index\": selected_index",
            "\"candidate_trajectory_horizon_steps\": int(candidates.shape[1])",
        ),
        rationale="payload must be written at the existing selection-log site",
    ),
    SourceHook(
        name="default_off_payload_pattern_available",
        required_tokens=(
            "external_context_payload_logging_payload = None",
            "temporal_consistency_payload_logging_payload = None",
            "if temporal_consistency_payload_logging:",
        ),
        rationale="existing default-off payload pattern can be followed without changing selection",
    ),
    SourceHook(
        name="latency_accounting_site_available",
        required_tokens=(
            "phase_latencies_ms = {",
            "**external_context_payload_latency_ms",
            "**temporal_consistency_payload_latency_ms",
        ),
        rationale="payload latency can be reported as an explicit component before any smoke",
    ),
    SourceHook(
        name="summary_metadata_pattern_available",
        required_tokens=(
            "\"camp_external_context_payload_logging\": (",
            "\"camp_temporal_consistency_payload_logging\": (",
            "\"selection_effect\": False",
        ),
        rationale="replay summary can record schema, enabled state, records, and latency",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only source-code preflight for default-off candidate-set "
            "consensus payload logging. It consumes the insufficient existing-log "
            "materiality artifact and checks whether replay has safe hook points. "
            "It does not implement logging or run replay."
        )
    )
    parser.add_argument("--materiality_json", type=Path, required=True)
    parser.add_argument(
        "--replay_source",
        type=Path,
        default=ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        materiality=_load_json(args.materiality_json),
        replay_source=args.replay_source,
        label=args.label,
        paths={
            "materiality_json": str(args.materiality_json),
            "replay_source": str(args.replay_source),
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
    materiality: dict[str, Any],
    replay_source: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
    source_hooks: tuple[SourceHook, ...] = SOURCE_HOOKS,
) -> dict[str, Any]:
    materiality_summary = _materiality_summary(materiality)
    replay_text = _read_source(replay_source)
    hook_reports = [_hook_report(hook, replay_text) for hook in source_hooks]
    checks = [*_materiality_checks(materiality_summary), *_hook_checks(hook_reports)]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_payload_logging_preflight_v1",
            "label": label,
            "role": (
                "read-only preflight for adding default-off candidate-set "
                "consensus payload logging after existing logs proved insufficient"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "The preflight does not create a runtime atom. A future payload "
                "implementation may only compute fixed current-tick finite "
                "candidate coefficients from the already generated DP candidate "
                "tensor before selection. If later atomized, those coefficients "
                "enter score_k(w)=a_k^T w and preserve convex simplex/CVaR/L2 "
                "optimization over w. No DP-side classical Benders "
                "master/subproblem, dual, or valid cut is constructed."
            ),
        },
        "materiality_summary": materiality_summary,
        "source_hook_reports": hook_reports,
        "preflight_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Payload Logging Preflight",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Hooks",
        "",
        "| Hook | Found | Missing Tokens |",
        "| --- | ---: | --- |",
    ]
    for hook in report["source_hook_reports"]:
        missing = ", ".join(f"`{token}`" for token in hook["missing_tokens"])
        lines.append(f"| `{hook['name']}` | `{hook['found']}` | {missing or '`none`'} |")
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["preflight_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This preflight does not authorize replay, CAMP training, online "
            "selector promotion, Full36, formal seeds, DP modification, or a "
            "DP-side classical Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _materiality_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    record_summary = _dict(report.get("record_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "screen_completed": bool(decision.get("screen_completed")),
        "materiality_gate_passed": bool(decision.get("materiality_gate_passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_gap": decision.get("primary_gap"),
        "valid_records": record_summary.get("valid_records"),
        "missing_prefix_records": record_summary.get("missing_prefix_records"),
        "blocked_action_conflicts": conflicts,
    }


def _hook_report(hook: SourceHook, source_text: str) -> dict[str, Any]:
    missing = [token for token in hook.required_tokens if token not in source_text]
    payload = asdict(hook)
    payload["found"] = not missing
    payload["missing_tokens"] = missing
    return payload


def _materiality_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("materiality_status", summary["status"], MATERIALITY_STATUS),
        _check_equal("materiality_screen_completed", summary["screen_completed"], True),
        _check_equal("materiality_not_passed", summary["materiality_gate_passed"], False),
        _check_equal(
            "materiality_authorizes_logging_preflight",
            summary["authorized_next_work"],
            MATERIALITY_NEXT_WORK,
        ),
        _check_equal(
            "materiality_primary_gap",
            summary["primary_gap"],
            "too_few_existing_candidate_prefix_records",
        ),
        _check_empty("materiality_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _hook_checks(hook_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            f"source_hook_{hook['name']}",
            bool(hook["found"]),
            True,
        )
        for hook in hook_reports
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "payload_implementation_authorized": passed,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": (
            "Implement only default-off candidate-set consensus payload unit "
            "tests and wiring. Do not run replay, train CAMP, or change online "
            "selection yet."
            if passed
            else "Repair materiality artifact or source hook assumptions before payload implementation."
        ),
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": [],
        "passed": len(value) == 0,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
