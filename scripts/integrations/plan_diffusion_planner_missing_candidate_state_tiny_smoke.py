#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from scripts.integrations.audit_diffusion_planner_missing_candidate_state_logging_implementation import (
    AUTHORIZED_NEXT_WORK as IMPLEMENTATION_NEXT_WORK,
    READY_STATUS as IMPLEMENTATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_observable_state_logging_smoke import (
    DATASET_AUDIT,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    SmokeSpec,
    _dataset_audit_command,
    _payload_audit_command,
    _runner_command,
    _selector_equivalence_command,
    _source_checks,
)


READY_STATUS = "missing_candidate_state_logging_tiny_smoke_plan_ready"
REJECT_STATUS = "missing_candidate_state_logging_tiny_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = "default_off_missing_candidate_state_logging_paired_three_step_smoke_only"
FORBIDDEN_FORMAL_SEEDS = frozenset({11, 12, 13})

DEFAULT_SMOKE = replace(
    SmokeSpec(),
    root=(
        "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/"
        "missing_candidate_state_logging_tiny_smoke_current_chain"
    ),
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for the default-off missing candidate-state tiny "
            "paired nonformal smoke. It emits commands but does not run replay."
        )
    )
    parser.add_argument("--implementation_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument("--payload_audit_source", type=Path, default=PAYLOAD_AUDIT)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        implementation_report=_load_json(args.implementation_json),
        label=args.label,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        paths={"implementation_json": str(args.implementation_json)},
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
    implementation_report: dict[str, Any],
    label: str | None = None,
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    smoke: SmokeSpec = DEFAULT_SMOKE,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(implementation_report)
    source_checks = _source_checks(
        replay_source=replay_source,
        payload_audit_source=payload_audit_source,
        selector_equivalence_source=selector_equivalence_source,
        dataset_audit_source=dataset_audit_source,
    )
    plan_checks = _plan_checks(smoke)
    passed = (
        bool(source["passed"])
        and not source["blocked_action_conflicts"]
        and all(check["passed"] for check in source_checks)
        and all(check["passed"] for check in plan_checks)
    )
    baseline_dir = f"{smoke.root}/baseline"
    candidate_dir = f"{smoke.root}/logging_enabled"
    audit_dir = f"{smoke.root}/audit"
    commands = {
        "baseline_replay": _runner_command(smoke, baseline_dir, logging=False),
        "candidate_replay": _runner_command(smoke, candidate_dir, logging=True),
        "selector_equivalence": _selector_equivalence_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
        ),
        "payload_audit": _payload_audit_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
            smoke,
        ),
        "dataset_audit": _dataset_audit_command(candidate_dir, audit_dir, smoke),
    }
    return {
        "analysis": {
            "name": "dp_camp_missing_candidate_state_logging_tiny_smoke_plan_v1",
            "label": label,
            "role": (
                "plan-only gate for paired nonformal default-off missing "
                "candidate-state logging smoke"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": {
                **(paths or {}),
                "replay_source": str(replay_source),
                "payload_audit_source": str(payload_audit_source),
                "selector_equivalence_source": str(selector_equivalence_source),
                "dataset_audit_source": str(dataset_audit_source),
            },
            "math_boundary": (
                "The planned smoke only toggles default-off logging for fixed "
                "current-tick finite-candidate descriptors. It must not change "
                "DP candidates, CAMP atoms, scores, feasibility, selected index, "
                "postprocess_reference, or PerfectTracker execution. If the "
                "logged descriptors are later atomized, they enter CAMP as fixed "
                "candidate coefficients a_k, preserving score_k(w)=a_k^T w and "
                "the simplex/CVaR/L2 convex master. This is not a DP-side "
                "classical Benders decomposition."
            ),
        },
        "source_implementation_gate": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "smoke_spec": asdict(smoke),
        "accept_criteria": _accept_criteria(smoke),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == IMPLEMENTATION_READY_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == IMPLEMENTATION_NEXT_WORK
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "recommended_first_action": final.get("recommended_first_action"),
        "blocked_action_conflicts": conflicts,
    }


def _plan_checks(smoke: SmokeSpec) -> list[dict[str, Any]]:
    command_root = str(smoke.root)
    all_paths = [
        command_root,
        str(smoke.route),
        str(smoke.model_path),
        str(smoke.model_args),
        str(smoke.config),
        str(smoke.reward_config),
        str(smoke.atom_scales),
        str(smoke.static_weights),
    ]
    return [
        _check_equal("scope_steps_is_three", int(smoke.steps), 3),
        _check_equal("scope_seed_is_nonformal", int(smoke.seed) not in FORBIDDEN_FORMAL_SEEDS, True),
        _check_equal("scope_single_seed", int(smoke.seed), 1),
        _check_equal("scope_candidate_count", int(smoke.num_candidates), 8),
        _check_equal("scope_traffic_lights_off", str(smoke.traffic_lights), "off"),
        {
            "name": "paths_do_not_contain_formal_seed_ids",
            "passed": not any(_contains_formal_seed(path) for path in all_paths),
            "paths": all_paths,
        },
        {
            "name": "smoke_root_is_current_chain_missing_candidate_state",
            "passed": "missing_candidate_state_logging_tiny_smoke" in command_root,
            "root": command_root,
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closed_loop_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "paired nonformal sample_map_tl_route_59_to_86 seed1 npc4 "
            "traffic_lights_off static, 3 steps only"
            if passed
            else None
        ),
        "tiny_smoke_authorized": passed,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": (
            "Run only the paired three-step nonformal smoke commands and audits "
            "listed in this plan; reject if selector equivalence, payload audit, "
            "dataset audit, or formal-seed exclusion fails."
            if passed
            else "Repair source, implementation gate, or smoke scope before "
            "running any replay."
        ),
    }


def _accept_criteria(smoke: SmokeSpec) -> list[str]:
    return [
        "source implementation gate is missing_candidate_state_logging_implementation_unit_tested",
        "baseline replay exits 0 without --camp_observable_state_logging",
        "candidate replay exits 0 with --camp_observable_state_logging",
        f"both replays use exactly {int(smoke.steps)} steps, seed {int(smoke.seed)}, and {int(smoke.num_candidates)} candidates",
        "no path, command, summary, or audit references formal seeds 11/12/13",
        "baseline summary reports camp_observable_state_logging.enabled=false",
        "candidate summary reports camp_observable_state_logging.enabled=true",
        "candidate records contain non-null observable_state_logging payloads",
        "payload schema, field shapes, finite checks, latency fields, and no future outcome keys pass audit",
        "selector-log equivalence passes for selected_index, feasibility, atoms, scores, and weights",
        "dataset audit passes finite-candidate contract checks with closed-loop outcomes forbidden",
    ]


def _reject_criteria() -> list[str]:
    return [
        "implementation source gate is not ready",
        "any replay command or audit command fails",
        "any formal seed 11/12/13 is detected",
        "baseline logging is not disabled or candidate logging is not enabled",
        "any selected_index, score, atom, feasibility, candidate, or tracker behavior changes",
        "any payload contains future outcome labels or selection_effect=true",
        "the run scope expands beyond the paired three-step nonformal smoke",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Missing Candidate-State Logging Tiny Smoke Plan",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- Scope: `{decision['closed_loop_replay_scope']}`",
        "",
        "## Source Gate",
        "",
        f"- Source status: `{report['source_implementation_gate']['status']}`",
        f"- Source authorized next work: `{report['source_implementation_gate']['authorized_next_work']}`",
        "",
        "## Plan Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Source Checks",
            "",
            "| Check | Passed | Missing |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["source_checks"]:
        missing = ", ".join(f"`{token}`" for token in check.get("missing_tokens", []))
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {missing or '`none`'} |"
        )
    lines.extend(["", "## Commands", ""])
    command_separator = " \\\n  "
    for name, command in report["commands"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(command),
                "```",
                "",
            ]
        )
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
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


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _contains_formal_seed(value: str) -> bool:
    tokens = value.replace("\\", "/").replace("-", "_").split("_")
    return any(token in {"seed11", "seed12", "seed13"} for token in tokens) or any(
        f"seed_{seed}" in value or f"seed/{seed}" in value
        for seed in FORBIDDEN_FORMAL_SEEDS
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
