#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
PAYLOAD_MODULE = (
    ROOT
    / "camp_core/camp_core/integrations/"
    "diffusion_planner_progress_lane_hard_context.py"
)

SOURCE_READY_STATUS = "progress_lane_hard_context_logging_preflight_ready"
SOURCE_NEXT_WORK = (
    "default_off_progress_lane_hard_context_logging_implementation_unit_tests_only"
)
READY_STATUS = "progress_lane_hard_context_logging_wiring_plan_ready"
REJECT_STATUS = "progress_lane_hard_context_logging_wiring_plan_rejected"
FORMAL_SEED_STATUS = "progress_lane_hard_context_logging_wiring_formal_seed_conflict"
AUTHORIZED_NEXT_WORK = (
    "default_off_progress_lane_hard_context_logging_wiring_unit_tests_only"
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
)


@dataclass(frozen=True)
class WiringSpec:
    planned_flag: str = "--camp_progress_lane_hard_context_logging"
    planned_support_steps_flag: str = "--camp_progress_lane_hard_context_steps"
    planned_dt_flag: str = "--camp_progress_lane_hard_context_dt_s"
    planned_corridor_width_flag: str = (
        "--camp_progress_lane_hard_context_corridor_half_width_m"
    )
    planned_corridor_margin_flag: str = (
        "--camp_progress_lane_hard_context_corridor_safety_margin_m"
    )
    planned_payload_key: str = "progress_lane_hard_context_logging"
    planned_summary_key: str = "camp_progress_lane_hard_context_logging"
    planned_builder: str = "build_progress_lane_hard_context_logging_payload"
    default_support_steps: int = 10
    default_dt_s: float = 0.1
    default_corridor_half_width_m: float = 1.75
    default_corridor_safety_margin_m: float = 0.25
    authorized_stage: str = "unit_tests_only_default_off_payload_wiring"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only implementation plan for default-off progress+lane/hard "
            "context logging replay wiring. This does not modify the replay "
            "runner and does not execute Diffusion Planner."
        )
    )
    parser.add_argument("--context_preflight_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--replay_script", type=Path, default=RUNNER)
    parser.add_argument("--payload_module", type=Path, default=PAYLOAD_MODULE)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        context_preflight_report=_read_json(args.context_preflight_json),
        label=args.label,
        replay_source=args.replay_script,
        payload_module_source=args.payload_module,
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


def build_report(
    *,
    context_preflight_report: dict[str, Any],
    label: str | None = None,
    replay_source: Path = RUNNER,
    payload_module_source: Path = PAYLOAD_MODULE,
    spec: WiringSpec = WiringSpec(),
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    formal_seed_records = _formal_seed_records(context_preflight_report)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this wiring plan.")

    source_checks = [
        *_source_artifact_checks(context_preflight_report),
        *_source_text_checks(
            replay_source=replay_source,
            payload_module_source=payload_module_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    blocked_flags = {name: False for name in BLOCKED_ACTIONS}
    return {
        "analysis": {
            "name": "dp_camp_progress_lane_hard_context_logging_wiring_plan_v1",
            "label": label,
            "source_status": SOURCE_READY_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "wiring_plan_only": True,
            "future_outcome_labels_used_for_plan": False,
            "formal_seed_records": int(formal_seed_records),
            "selection_neutrality_required": True,
            "math_boundary": (
                "The planned wiring only records default-off current-tick "
                "finite-candidate fields and nonnegative context atom "
                "coefficients before closed-loop outcome labels. If later "
                "atomized, each candidate coefficient a_k is fixed for the "
                "tick, preserving affine score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master. This plan constructs no "
                "DP-side classical Benders master/subproblem, dual, or cut."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "planned_wiring": _planned_wiring(spec),
        "unit_test_requirements": _unit_test_requirements(spec),
        "reject_criteria": _reject_criteria(),
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "next_scope": (
                "modify replay wiring and unit tests only; no replay execution"
                if passed
                else None
            ),
            **blocked_flags,
        },
    }


def _source_artifact_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    final = report.get("final_decision", {}) if isinstance(report, dict) else {}
    analysis = report.get("analysis", {}) if isinstance(report, dict) else {}
    return [
        {
            "name": "context_preflight_ready",
            "passed": final.get("status") == SOURCE_READY_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK,
            "status": final.get("status"),
            "authorized_next_work": final.get("authorized_next_work"),
        },
        {
            "name": "context_preflight_blocks_forbidden_actions",
            "passed": _source_blocks_forbidden_actions(final),
        },
        {
            "name": "context_preflight_math_boundary_present",
            "passed": "score_k(w)=a_k^T w"
            in str(analysis.get("math_boundary", ""))
            and "classical Benders" in str(analysis.get("math_boundary", "")),
        },
        {
            "name": "context_preflight_does_not_authorize_replay",
            "passed": _false_flag(final, "new_replay_authorized")
            and _false_flag(final, "closed_loop_smoke_authorized")
            and _false_flag(final, "full36_authorized", "Full36_authorized"),
        },
    ]


def _source_text_checks(
    *,
    replay_source: Path,
    payload_module_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    payload_text = _read_text(payload_module_source)
    return [
        _check_tokens(
            "replay_has_adjacent_default_off_logging_hooks",
            replay_text,
            (
                "--camp_progress_support_logging",
                "--camp_lane_hard_violation_support_logging",
                "progress_support_logging_payload = None",
                "lane_hard_violation_support_logging_payload = None",
                "build_progress_support_logging_payload(",
                "build_lane_hard_violation_support_logging_payload(",
                "\"progress_support_logging\": progress_support_logging_payload",
                "\"lane_hard_violation_support_logging\":",
                "\"camp_progress_support_logging\"",
                "\"camp_lane_hard_violation_support_logging\"",
            ),
        ),
        _check_order(
            "replay_default_off_payloads_before_outcome_collection",
            replay_text,
            "build_progress_support_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "replay_has_latency_and_validation_insertion_points",
            replay_text,
            (
                "**progress_support_latency_ms",
                "**lane_hard_violation_support_latency_ms",
                "validation[\"camp_progress_support_logging\"]",
                "validation[\"camp_lane_hard_violation_support_logging\"]",
                "selection_effect",
                "future_outcome_leakage",
                "closed_loop_outcome_fields_read",
                "classical_benders_claim",
            ),
        ),
        _check_tokens(
            "payload_module_exports_default_off_context_builder",
            payload_text,
            (
                "PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION",
                "PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES",
                "PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES",
                "PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS",
                "build_progress_lane_hard_context_logging_payload",
                "\"default_off\": True",
                "\"selection_effect\": False",
                "\"future_outcome_leakage\": False",
                "\"closed_loop_outcome_fields_read\": False",
                "\"classical_benders_claim\": False",
                "score_k(w)=a_k^T w",
            ),
        ),
        _check_tokens(
            "payload_module_signature_uses_current_tick_inputs_only",
            payload_text,
            (
                "candidates: np.ndarray",
                "route_centerline_ego: np.ndarray",
                "support_steps: int",
                "corridor_half_width_m",
                "corridor_safety_margin_m",
            ),
        ),
    ]


def _plan_checks(spec: WiringSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "planned_flag_default_off",
            "passed": spec.planned_flag.startswith("--camp_")
            and spec.planned_flag.endswith("_logging"),
            "value": spec.planned_flag,
        },
        {
            "name": "planned_payload_key_is_record_field",
            "passed": spec.planned_payload_key.endswith("_logging")
            and not spec.planned_payload_key.startswith("camp_"),
            "value": spec.planned_payload_key,
        },
        {
            "name": "planned_summary_key_is_summary_field",
            "passed": spec.planned_summary_key.startswith("camp_")
            and spec.planned_summary_key.endswith("_logging"),
            "value": spec.planned_summary_key,
        },
        {
            "name": "planned_builder_is_context_payload_builder",
            "passed": spec.planned_builder
            == "build_progress_lane_hard_context_logging_payload",
            "value": spec.planned_builder,
        },
        {
            "name": "planned_defaults_valid",
            "passed": spec.default_support_steps >= 2
            and spec.default_dt_s > 0.0
            and spec.default_corridor_half_width_m > 0.0
            and spec.default_corridor_safety_margin_m >= 0.0,
            "values": {
                "support_steps": spec.default_support_steps,
                "dt_s": spec.default_dt_s,
                "corridor_half_width_m": spec.default_corridor_half_width_m,
                "corridor_safety_margin_m": spec.default_corridor_safety_margin_m,
            },
        },
    ]


def _planned_wiring(spec: WiringSpec) -> dict[str, Any]:
    return {
        **asdict(spec),
        "planned_imports": (
            "PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES",
            "PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES",
            "PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS",
            "PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION",
            "build_progress_lane_hard_context_logging_payload",
        ),
        "planned_payload_builder_call": {
            "function": spec.planned_builder,
            "arguments": {
                "candidates": "candidates",
                "route_centerline_ego": "route_centerline_ego",
                "support_steps": "progress_lane_hard_context_steps",
                "dt_s": "progress_lane_hard_context_dt_s",
                "corridor_half_width_m": (
                    "progress_lane_hard_context_corridor_half_width_m"
                ),
                "corridor_safety_margin_m": (
                    "progress_lane_hard_context_corridor_safety_margin_m"
                ),
            },
        },
        "planned_insertion_points": (
            "argparse default-off logging options beside progress/lane-hard support",
            "route_centerline_ego reuse condition",
            "payload build before collect_closed_loop_outcomes",
            "phase_latencies_ms merge through payload latency keys",
            "selection_log record field progress_lane_hard_context_logging",
            "camp_replay_summary and camp_validation_summary metadata",
        ),
        "required_metadata": {
            "schema_version": "dp_camp_progress_lane_hard_context_logging_v1",
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "classical_benders_claim": False,
        },
    }


def _unit_test_requirements(spec: WiringSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "default_disabled_summary",
            "expected": (
                f"{spec.planned_summary_key}.enabled is false and "
                f"{spec.planned_payload_key} is None when the flag is absent"
            ),
        },
        {
            "name": "enabled_payload_logged_without_selection_effect",
            "expected": (
                f"enabling {spec.planned_flag} logs non-null payloads while "
                "selected_index, feasible_mask, scores, and candidates are unchanged"
            ),
        },
        {
            "name": "summary_validation_metadata",
            "expected": (
                "summary and validation expose default_off, no-leak, "
                "closed_loop_outcome_fields_read=false, and no Benders claim"
            ),
        },
        {
            "name": "latency_fields_merged",
            "expected": (
                "all PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS appear as finite "
                "nonnegative per-record latency fields when enabled"
            ),
        },
    ]


def _reject_criteria() -> list[str]:
    return [
        "source context preflight is not ready or authorized next work differs",
        "replay source lacks adjacent default-off logging insertion points",
        "payload module lacks no-leak metadata, schema, field, atom, or latency exports",
        "the planned wiring would affect selection, feasibility, scores, candidates, or tracker execution",
        "any formal seed records appear in the source evidence when fail_on_formal_seeds is set",
    ]


def _source_blocks_forbidden_actions(final: dict[str, Any]) -> bool:
    return (
        _false_flag(final, "new_replay_authorized")
        and _false_flag(final, "closed_loop_smoke_authorized")
        and _false_flag(final, "full36_authorized", "Full36_authorized")
        and _false_flag(final, "formal_seeds_authorized")
        and _false_flag(final, "online_selector_authorized")
        and _false_flag(final, "camp_retraining_authorized", "CAMP_retraining_authorized")
        and _false_flag(final, "dp_modification_authorized", "DP_modification_authorized")
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Progress+Lane/Hard Context Logging Wiring Plan",
        "",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"authorized_next_work={decision['authorized_next_work']}",
        "",
        "## Analysis",
        "",
        f"training={report['analysis']['training']}",
        f"online_selector_change={report['analysis']['online_selector_change']}",
        f"diffusion_planner_execution={report['analysis']['diffusion_planner_execution']}",
        f"wiring_plan_only={report['analysis']['wiring_plan_only']}",
        f"future_outcome_labels_used_for_plan={report['analysis']['future_outcome_labels_used_for_plan']}",
        "",
        "## Planned Wiring",
        "",
    ]
    planned = report["planned_wiring"]
    for key in (
        "planned_flag",
        "planned_payload_key",
        "planned_summary_key",
        "planned_builder",
        "authorized_stage",
    ):
        lines.append(f"- {key}: `{planned[key]}`")
    lines.extend(
        [
            "",
            "## Source Checks",
            "",
        ]
    )
    for check in report["source_checks"]:
        lines.append(f"- {check['name']}: {check['passed']}")
    lines.extend(["", "## Plan Checks", ""])
    for check in report["plan_checks"]:
        lines.append(f"- {check['name']}: {check['passed']}")
    lines.extend(
        [
            "",
            "## Blocked Actions",
            "",
        ]
    )
    for name in BLOCKED_ACTIONS:
        lines.append(f"- {name}: {decision[name]}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _formal_seed_records(report: dict[str, Any]) -> int:
    for key in ("formal_seed_records",):
        value = report.get(key)
        if isinstance(value, int):
            return int(value)
    analysis = report.get("analysis", {}) if isinstance(report, dict) else {}
    value = analysis.get("formal_seed_records") if isinstance(analysis, dict) else None
    return int(value) if isinstance(value, int) else 0


def _false_flag(mapping: dict[str, Any], *names: str) -> bool:
    present = False
    for name in names:
        if name in mapping:
            present = True
            if mapping.get(name) is not False:
                return False
    return present


def _check_tokens(name: str, text: str, tokens: tuple[str, ...]) -> dict[str, Any]:
    missing = [token for token in tokens if token not in text]
    return {
        "name": name,
        "passed": not missing,
        "missing_tokens": missing,
    }


def _check_order(name: str, text: str, first: str, second: str) -> dict[str, Any]:
    first_index = text.find(first)
    second_index = text.find(second)
    return {
        "name": name,
        "passed": first_index >= 0 and second_index >= 0 and first_index < second_index,
        "first_token": first,
        "second_token": second,
        "first_index": first_index,
        "second_index": second_index,
    }


if __name__ == "__main__":
    main()
