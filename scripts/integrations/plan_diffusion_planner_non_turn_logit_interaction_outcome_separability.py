#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_payload_smoke import (
    DATASET_AUDIT,
    FORMAL_SEEDS,
    SELECTOR_EQUIVALENCE,
    _check_tokens,
)


ROOT = Path(__file__).resolve().parents[2]
MATCHED_CONTRACT_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_non_turn_logit_interaction_matched_outcomes.py"
)
SEPARABILITY_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_non_turn_logit_interaction_outcome_separability.py"
)

READY_STATUS = "non_turn_logit_interaction_outcome_separability_plan_ready"
REJECT_STATUS = "non_turn_logit_interaction_outcome_separability_plan_rejected"
CONTRACT_READY_STATUS = "non_turn_logit_interaction_matched_outcome_contract_passed"
CONTRACT_NEXT_WORK = "non_turn_logit_interaction_outcome_separability_plan_only"
AUTHORIZED_NEXT_WORK = (
    "non_turn_logit_interaction_outcome_separability_existing_artifact_screen_only"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a no-leak non-turn-logit interaction "
            "outcome-separability screen over existing matched artifacts. It "
            "does not run Diffusion Planner."
        )
    )
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--matched_dataset_audit_json", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument(
        "--matched_selection_log",
        default=(
            "/root/autodl-tmp/"
            "camp_dp_non_turn_logit_interaction_matched_outcome_contract_v1/"
            "matched_interaction_outcomes/camp_selection_log.json"
        ),
    )
    parser.add_argument(
        "--audit_root",
        default=(
            "/root/autodl-tmp/"
            "camp_dp_non_turn_logit_interaction_outcome_separability_plan_v1/audit"
        ),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--matched_contract_source",
        type=Path,
        default=MATCHED_CONTRACT_AUDIT,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument(
        "--separability_audit_source",
        type=Path,
        default=SEPARABILITY_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        matched_contract=_read_json(args.matched_contract_json),
        matched_dataset=_read_json(args.matched_dataset_audit_json),
        selector_equivalence=_read_json(args.selector_equivalence_json),
        matched_selection_log=args.matched_selection_log,
        audit_root=args.audit_root,
        label=args.label,
        matched_contract_source=args.matched_contract_source,
        dataset_audit_source=args.dataset_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        separability_audit_source=args.separability_audit_source,
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
    matched_contract: dict[str, Any],
    matched_dataset: dict[str, Any],
    selector_equivalence: dict[str, Any],
    matched_selection_log: str,
    audit_root: str,
    label: str | None = None,
    matched_contract_source: Path = MATCHED_CONTRACT_AUDIT,
    dataset_audit_source: Path = DATASET_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    separability_audit_source: Path = SEPARABILITY_AUDIT,
) -> dict[str, Any]:
    source_checks = [
        *_source_artifact_checks(
            matched_contract=matched_contract,
            matched_dataset=matched_dataset,
            selector_equivalence=selector_equivalence,
        ),
        *_source_text_checks(
            matched_contract_source=matched_contract_source,
            dataset_audit_source=dataset_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            separability_audit_source=separability_audit_source,
        ),
    ]
    plan_checks = _plan_checks(matched_selection_log, audit_root)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_non_turn_logit_interaction_outcome_separability_plan_v1"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "uses_existing_artifact_only": True,
            "math_boundary": (
                "The planned separability screen reads existing matched replay "
                "records only. Runtime payload fields remain current-tick "
                "finite-candidate descriptors; candidate closed-loop outcomes "
                "are offline labels used only for class labels and thresholds. "
                "Only comfort_progress_interaction_cost is treated as an atom "
                "candidate. If later promoted, it remains a fixed nonnegative "
                "coefficient in score_k(w)=a_k^T w, preserving the "
                "simplex/CVaR/L2 convex master. No DP-side classical Benders "
                "decomposition, dual, or cut is claimed."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "commands": {
            "non_turn_logit_interaction_outcome_separability": _separability_command(
                matched_selection_log,
                audit_root,
            )
        },
        "accept_criteria": _accept_criteria(),
        "reject_criteria": _reject_criteria(),
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "separability_execution_authorized_now": False,
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "schema_promotion_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _source_artifact_checks(
    *,
    matched_contract: dict[str, Any],
    matched_dataset: dict[str, Any],
    selector_equivalence: dict[str, Any],
) -> list[dict[str, Any]]:
    final = matched_contract.get("final_decision", {})
    counts = matched_contract.get("counts", {})
    dataset_checks = matched_dataset.get("checks", {})
    return [
        {
            "name": "matched_contract_passed",
            "passed": final.get("status") == CONTRACT_READY_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == CONTRACT_NEXT_WORK,
            "status": final.get("status"),
            "authorized_next_work": final.get("authorized_next_work"),
        },
        {
            "name": "matched_contract_records_complete",
            "passed": int(counts.get("records", 0)) > 0
            and counts.get("records") == counts.get("payload_records")
            and counts.get("records") == counts.get("outcome_records")
            and int(counts.get("candidate_rows", 0)) > 0
            and int(counts.get("formal_seed_records", -1)) == 0,
            "counts": counts,
        },
        {
            "name": "selector_exact_equivalence",
            "passed": selector_equivalence.get("equivalent") is True
            and _sum_nested_numbers(selector_equivalence.get("exact_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector_equivalence.get("numeric_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector_equivalence.get("numeric_shape_mismatches")) == 0.0
            and _sum_nested_numbers(selector_equivalence.get("numeric_nonexact_entries")) == 0.0,
            "equivalent": selector_equivalence.get("equivalent"),
        },
        {
            "name": "matched_dataset_required_outcomes_passed",
            "passed": matched_dataset.get("passed") is True
            and dataset_checks.get("closed_loop_outcomes_required") is True
            and dataset_checks.get("complete_closed_loop_outcomes") is True
            and dataset_checks.get("finite_candidate_contract_verified") is True
            and dataset_checks.get("forbidden_seed_check") is not False,
            "passed_value": matched_dataset.get("passed"),
            "checks": dataset_checks,
        },
    ]


def _source_text_checks(
    *,
    matched_contract_source: Path,
    dataset_audit_source: Path,
    selector_equivalence_source: Path,
    separability_audit_source: Path,
) -> list[dict[str, Any]]:
    contract_text = _read_text(matched_contract_source)
    dataset_text = _read_text(dataset_audit_source)
    selector_text = _read_text(selector_equivalence_source)
    separability_text = _read_text(separability_audit_source)
    return [
        _check_tokens(
            "matched_contract_audit_available",
            contract_text,
            (
                "dp_camp_non_turn_logit_interaction_matched_outcome_contract_v1",
                "candidate_closed_loop_outcomes",
                "non_turn_logit_interaction_payload_logging",
            ),
        ),
        _check_tokens(
            "dataset_required_outcome_audit_available",
            dataset_text,
            (
                "--closed_loop_outcome_policy",
                "required",
                "--require_finite_candidate_contract",
                "--forbid_seed",
            ),
        ),
        _check_tokens(
            "selector_equivalence_audit_available",
            selector_text,
            ("selected_index", "selection_scores", "require_equivalent"),
        ),
        _check_tokens(
            "separability_audit_available",
            separability_text,
            (
                "dp_camp_non_turn_logit_interaction_outcome_separability_v1",
                "comfort_progress_interaction_cost",
                "future_outcome_labels_used_for_atoms",
                "CONTRACT_READY_STATUS",
            ),
        ),
    ]


def _plan_checks(matched_selection_log: str, audit_root: str) -> list[dict[str, Any]]:
    forbidden_seed_hit = any(
        f"seed_{seed}" in matched_selection_log or f"seed-{seed}" in matched_selection_log
        for seed in FORMAL_SEEDS
    )
    return [
        {
            "name": "formal_seed_path_excluded",
            "passed": not forbidden_seed_hit,
            "details": {"formal_seeds": sorted(FORMAL_SEEDS), "path": matched_selection_log},
        },
        {
            "name": "existing_selection_log_scope",
            "passed": matched_selection_log.endswith("camp_selection_log.json"),
            "details": {"matched_selection_log": matched_selection_log},
        },
        {
            "name": "audit_root_declared",
            "passed": bool(audit_root),
            "details": {"audit_root": audit_root},
        },
    ]


def _separability_command(matched_selection_log: str, audit_root: str) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_non_turn_logit_interaction_outcome_separability.py",
        "--selection_log",
        matched_selection_log,
        "--matched_contract_json",
        (
            "/root/autodl-tmp/"
            "camp_dp_non_turn_logit_interaction_matched_outcome_contract_v1/"
            "audit/matched_interaction_outcome_contract.json"
        ),
        "--matched_dataset_audit_json",
        (
            "/root/autodl-tmp/"
            "camp_dp_non_turn_logit_interaction_matched_outcome_contract_v1/"
            "audit/dataset_required_outcome_audit.json"
        ),
        "--expected_logs",
        "1",
        "--expected_records",
        "3",
        "--expected_candidates",
        "8",
        "--fail_on_formal_seeds",
        "--output_json",
        f"{audit_root}/non_turn_logit_interaction_outcome_separability.json",
        "--output_md",
        f"{audit_root}/non_turn_logit_interaction_outcome_separability.md",
    ]


def _accept_criteria() -> list[str]:
    return [
        "all source and plan checks pass",
        "separability command reads only existing matched selection logs",
        "outcomes are used only for offline class labels and threshold diagnostics",
        "comfort_progress_interaction_cost is the only atom-candidate descriptor promoted by the screen",
        "no formal seed 11/12/13 appears in the source path or records",
    ]


def _reject_criteria() -> list[str]:
    return [
        "matched contract audit is missing or failed",
        "selector equivalence failed",
        "dataset audit does not require complete closed-loop outcomes",
        "separability audit source is missing the no-leak/math-boundary contract",
        "the plan requests new replay, online selector changes, retraining, Full36, or formal seeds",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _sum_nested_numbers(value: Any) -> float:
    if isinstance(value, dict):
        return sum(_sum_nested_numbers(item) for item in value.values())
    if isinstance(value, (int, float)):
        return float(value)
    return float("inf")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    separator = " \\\n  "
    command = report["commands"]["non_turn_logit_interaction_outcome_separability"]
    lines = [
        "# Non-Turn-Logit Interaction Outcome Separability Plan",
        "",
        "This is a design-only plan. It does not run Diffusion Planner, does "
        "not train CAMP, and does not authorize online selector promotion.",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- separability execution authorized now: `{decision['separability_execution_authorized_now']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for item in report["source_checks"]:
        lines.append(f"| `{item['name']}` | `{item['passed']}` |")
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(f"- `{item['name']}`: `{item['passed']}`" for item in report["plan_checks"])
    lines.extend(
        [
            "",
            "## Separability Command",
            "",
            "```bash",
            separator.join(command),
            "```",
            "",
            "## Accept Criteria",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
