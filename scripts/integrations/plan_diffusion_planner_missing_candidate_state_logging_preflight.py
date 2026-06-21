#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrations.design_diffusion_planner_observable_state_logging import (
    FIELD_SPECS,
    SOURCE_HOOKS,
    ROOT,
    _design_checks,
    _family_reports,
    _field_report,
    _hook_report,
    _read_source,
    _required_families,
)


SOURCE_STATUS = "post_inventory_next_design_plan_ready"
SOURCE_NEXT_WORK = "predeclare_default_off_missing_candidate_state_logging_preflight_only"
SOURCE_RECOMMENDED_ACTION = "default_off_missing_candidate_state_logging_preflight"

READY_STATUS = "missing_candidate_state_logging_preflight_ready"
BLOCKED_STATUS = "missing_candidate_state_logging_preflight_blocked"
AUTHORIZED_NEXT_WORK = "default_off_missing_candidate_state_logging_implementation_unit_tests_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
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
            "Design-only preflight for default-off missing candidate-state "
            "logging after the post-inventory next-design gate."
        )
    )
    parser.add_argument("--post_inventory_plan_json", type=Path, required=True)
    parser.add_argument(
        "--replay_source",
        type=Path,
        default=ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py",
    )
    parser.add_argument(
        "--integration_source",
        type=Path,
        default=ROOT / "camp_core/camp_core/integrations/diffusion_planner.py",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        post_inventory_plan=_load_json(args.post_inventory_plan_json),
        replay_source=args.replay_source,
        integration_source=args.integration_source,
        label=args.label,
        paths={"post_inventory_plan_json": str(args.post_inventory_plan_json)},
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
    post_inventory_plan: dict[str, Any],
    replay_source: Path,
    integration_source: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(post_inventory_plan)
    replay_text = _read_source(replay_source)
    integration_text = _read_source(integration_source)
    field_reports = [_field_report(field) for field in FIELD_SPECS]
    family_reports = _family_reports(field_reports)
    hook_reports = [
        _hook_report(hook, replay_text, integration_text) for hook in SOURCE_HOOKS
    ]
    design_checks = _design_checks(field_reports, hook_reports, family_reports)
    checks = [
        *_source_checks(source),
        *_source_contract_checks(source),
        {
            "name": "field_and_source_design_checks_pass",
            "passed": bool(design_checks["passed"]),
            "missing_required_families": design_checks["missing_required_families"],
            "invalid_fields": design_checks["invalid_fields"],
            "missing_source_hooks": design_checks["missing_source_hooks"],
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_missing_candidate_state_logging_preflight_v1",
            "label": label,
            "role": (
                "design-only preflight for default-off current-tick "
                "candidate-state logging on the current post-inventory chain"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "default_off_logging_only": True,
            "paths": {
                **(paths or {}),
                "replay_source": str(replay_source),
                "integration_source": str(integration_source),
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The "
                "preflight only specifies default-off logging of current-tick "
                "finite-candidate state fields and source hooks. It does not "
                "run replay, train CAMP, modify DP, alter scoring, or promote "
                "selection. If any logged field later becomes a CAMP atom, it "
                "must be a fixed coefficient a_k, nonnegative or represented "
                "by nonnegative signed parts, so score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 master remains convex. No "
                "classical Benders master/subproblem, dual, or cut is claimed."
            ),
        },
        "source_post_inventory_plan_gate": source,
        "source_checks": checks,
        "field_specs": field_reports,
        "family_reports": family_reports,
        "source_hook_reports": hook_reports,
        "design_checks": design_checks,
        "implementation_contract": _implementation_contract(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    contract = report.get("default_off_logging_contract") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "recommended_first_action": final.get("recommended_first_action"),
        "candidate_state_families": list(contract.get("candidate_state_families") or []),
        "must_be": list(contract.get("must_be") or []),
        "must_not_include": list(contract.get("must_not_include") or []),
        "blocked_action_conflicts": conflicts,
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_logging_preflight",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "source_recommended_action_matches",
            source["recommended_first_action"],
            SOURCE_RECOMMENDED_ACTION,
        ),
        {
            "name": "source_has_no_blocked_action_conflicts",
            "passed": not source["blocked_action_conflicts"],
            "conflicts": source["blocked_action_conflicts"],
        },
    ]


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    required = sorted(_required_families())
    actual = sorted(str(item) for item in source["candidate_state_families"])
    must_be = set(str(item) for item in source["must_be"])
    must_not = set(str(item) for item in source["must_not_include"])
    return [
        _check_equal("source_candidate_families_match_required", actual, required),
        {
            "name": "source_contract_default_off_and_no_leak",
            "passed": {
                "default-off",
                "selection-effect-free",
                "current-tick only",
                "candidate-level where used for atoms",
            }.issubset(must_be)
            and {
                "candidate_closed_loop_outcomes",
                "future collision/red/near-miss/completion labels",
                "DP weight or source changes",
                "online selector behavior changes",
            }.issubset(must_not),
            "must_be": sorted(must_be),
            "must_not_include": sorted(must_not),
        },
    ]


def _implementation_contract() -> dict[str, Any]:
    return {
        "allowed_next": [
            "implementation unit tests for payload construction",
            "source-token and order checks for default-off gating",
            "finite-shape checks on synthetic candidate arrays",
            "baseline equivalence tests that logging does not change selection",
        ],
        "blocked_until_next_gate": [
            "closed-loop replay",
            "tiny paired nonformal smoke",
            "online selector changes",
            "CAMP retraining",
            "Full36",
            "formal seeds",
            "DP source or weight modification",
        ],
        "payload_must_include": [
            "schema_version",
            "enabled",
            "default_off",
            "selection_effect",
            "future_outcome_leakage",
            "candidate_count",
            "field_shapes",
            "finite_checks",
            "latency_ms",
        ],
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "implement_default_off_logging_unit_gate"
            if passed
            else "repair_missing_candidate_state_logging_preflight"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": (
            "Implement or verify default-off missing candidate-state logging "
            "with unit tests only; replay and smoke remain blocked."
            if passed
            else "Repair the preflight source gate, field contract, or source hooks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_post_inventory_plan_gate"]
    lines = [
        "# Missing Candidate-State Logging Preflight",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommended first action: `{decision['recommended_first_action']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gate",
        "",
        f"- Status: `{source['status']}`",
        f"- Authorized next work: `{source['authorized_next_work']}`",
        f"- Candidate families: `{', '.join(source['candidate_state_families'])}`",
        "",
        "## Families",
        "",
        "| Family | Fields | Candidate-Level Fields | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in report["family_reports"]:
        lines.append(
            f"| `{row['family']}` | `{row['field_count']}` | "
            f"`{row['candidate_level_field_count']}` | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Source Hooks",
            "",
            "| Hook | Source | Found | Missing Tokens |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in report["source_hook_reports"]:
        missing = ", ".join(f"`{token}`" for token in row["missing_tokens"])
        lines.append(
            f"| `{row['name']}` | `{row['file_role']}` | "
            f"`{row['found']}` | {missing or '`none`'} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This is design-only. It does not authorize replay, smoke, training, "
            "online selector promotion, formal seeds, DP modification, or a "
            "classical Benders claim.",
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
