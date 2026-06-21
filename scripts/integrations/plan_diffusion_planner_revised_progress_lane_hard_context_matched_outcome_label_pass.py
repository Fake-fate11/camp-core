#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (
    MISSING_OUTCOMES_NEXT_WORK,
    MISSING_OUTCOMES_STATUS,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_broader_nonformal_smoke import (
    BroaderSmokeSpec,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_logging_smoke import (
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _check_order,
    _check_tokens,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_matched_outcome_label_pass import (
    DATASET_AUDIT,
    MATCHED_CONTEXT_CONTRACT_AUDIT,
    _dataset_audit_command,
    _matched_context_contract_command,
    _replay_command,
    _selector_equivalence_command,
)


REVISED_ATOM_SEPARABILITY_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability.py"
)
DEFAULT_SOURCE_SMOKE_AUDIT = (
    "/root/autodl-tmp/camp_dp_revised_context_logging_smoke_77d396e/"
    "audit/progress_lane_hard_context_logging_smoke.json"
)

READY_STATUS = (
    "revised_progress_lane_hard_context_matched_outcome_label_pass_plan_ready"
)
REJECT_STATUS = (
    "revised_progress_lane_hard_context_matched_outcome_label_pass_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "revised_progress_lane_hard_context_matched_outcome_label_nonformal_smoke_only"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for revised progress+lane/hard context atom "
            "matched outcome-label replay. It emits commands and checks only; "
            "it does not run Diffusion Planner."
        )
    )
    parser.add_argument("--tiny_separability_contract_json", type=Path, required=True)
    parser.add_argument("--source_smoke_audit_json", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--dataset_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    parser.add_argument(
        "--matched_context_contract_audit_source",
        type=Path,
        default=MATCHED_CONTEXT_CONTRACT_AUDIT,
    )
    parser.add_argument(
        "--revised_atom_separability_audit_source",
        type=Path,
        default=REVISED_ATOM_SEPARABILITY_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = replace(
        BroaderSmokeSpec(),
        root=(
            "/root/autodl-tmp/"
            "camp_dp_revised_context_matched_outcome_labels_nonformal_v1"
        ),
    )
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        tiny_contract=_read_json(args.tiny_separability_contract_json),
        source_smoke_audit=_read_json(args.source_smoke_audit_json),
        selector_equivalence=_read_json(args.selector_equivalence_json),
        dataset_audit=_read_json(args.dataset_audit_json),
        source_smoke_audit_path=str(args.source_smoke_audit_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        matched_context_contract_audit_source=(
            args.matched_context_contract_audit_source
        ),
        revised_atom_separability_audit_source=(
            args.revised_atom_separability_audit_source
        ),
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
    tiny_contract: dict[str, Any],
    source_smoke_audit: dict[str, Any],
    selector_equivalence: dict[str, Any],
    dataset_audit: dict[str, Any],
    source_smoke_audit_path: str = DEFAULT_SOURCE_SMOKE_AUDIT,
    label: str | None = None,
    spec: BroaderSmokeSpec | None = None,
    replay_source: Path = RUNNER,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    matched_context_contract_audit_source: Path = MATCHED_CONTEXT_CONTRACT_AUDIT,
    revised_atom_separability_audit_source: Path = REVISED_ATOM_SEPARABILITY_AUDIT,
) -> dict[str, Any]:
    if spec is None:
        spec = replace(
            BroaderSmokeSpec(),
            root=(
                "/root/autodl-tmp/"
                "camp_dp_revised_context_matched_outcome_labels_nonformal_v1"
            ),
        )
    source_checks = [
        *_source_artifact_checks(
            tiny_contract=tiny_contract,
            source_smoke_audit=source_smoke_audit,
            selector_equivalence=selector_equivalence,
            dataset_audit=dataset_audit,
        ),
        *_source_text_checks(
            replay_source=replay_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
            matched_context_contract_audit_source=matched_context_contract_audit_source,
            revised_atom_separability_audit_source=(
                revised_atom_separability_audit_source
            ),
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_revised_progress_lane_hard_context_matched_"
                "outcome_label_pass_plan_v1"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "formal_seed_records": 0,
            "future_outcome_leakage": False,
            "math_boundary": (
                "The planned matched branch records revised current-tick "
                "progress+lane/hard context atom coefficients and posterior "
                "candidate closed-loop outcomes in the same replay record. "
                "Outcomes are offline labels only and are forbidden as runtime "
                "selector features. Revised atoms are fixed nonnegative "
                "candidate coefficients, so CAMP score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 robust master remains convex. "
                "No DP-side classical Benders decomposition, dual, or cut is "
                "claimed."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "coverage_targets": _coverage_targets(spec),
        "commands": _commands(spec, source_smoke_audit_path=source_smoke_audit_path),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: 4 paired nonformal runs x 12 steps; matched "
                "branch collects revised progress_lane_hard_context atoms and "
                "candidate_closed_loop_outcomes"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "online_optimization_promotion_authorized": False,
        },
    }


def _source_artifact_checks(
    *,
    tiny_contract: dict[str, Any],
    source_smoke_audit: dict[str, Any],
    selector_equivalence: dict[str, Any],
    dataset_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    contract_final = tiny_contract.get("final_decision", {})
    contract_records = tiny_contract.get("records", {})
    coverage = tiny_contract.get("payload_descriptor_coverage", {})
    smoke_final = source_smoke_audit.get("final_decision", {})
    return [
        {
            "name": "tiny_revised_atom_contract_missing_outcomes",
            "passed": contract_final.get("status") == MISSING_OUTCOMES_STATUS
            and contract_final.get("authorized_next_work")
            == MISSING_OUTCOMES_NEXT_WORK
            and contract_final.get("passed") is False,
            "final_decision": contract_final,
        },
        {
            "name": "tiny_revised_atom_payload_coverage_finite",
            "passed": int(contract_records.get("candidate_rows", 0)) > 0
            and int(contract_records.get("missing_outcome_records", 0)) > 0
            and all(
                int(row.get("finite", -1)) == int(row.get("total", -2))
                and int(row.get("total", 0)) > 0
                for row in coverage.values()
            ),
            "records": contract_records,
            "payload_descriptor_coverage": coverage,
        },
        {
            "name": "source_logging_smoke_passed",
            "passed": smoke_final.get("status")
            == "progress_lane_hard_context_logging_smoke_passed"
            and smoke_final.get("passed") is True,
            "final_decision": smoke_final,
        },
        {
            "name": "source_selector_equivalence_exact",
            "passed": selector_equivalence.get("equivalent") is True,
            "equivalent": selector_equivalence.get("equivalent"),
        },
        {
            "name": "source_dataset_audit_passed",
            "passed": dataset_audit.get("passed") is True,
            "passed_value": dataset_audit.get("passed"),
        },
    ]


def _source_text_checks(
    *,
    replay_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
    matched_context_contract_audit_source: Path,
    revised_atom_separability_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    context_contract_text = _read_text(matched_context_contract_audit_source)
    revised_text = _read_text(revised_atom_separability_audit_source)
    return [
        _check_tokens(
            "replay_supports_context_logging_and_outcome_labels",
            replay_text,
            (
                "--camp_progress_lane_hard_context_logging",
                "--camp_collect_closed_loop_outcomes",
                "build_progress_lane_hard_context_logging_payload(",
                "compute_candidate_closed_loop_outcomes(",
            ),
        ),
        _check_order(
            "replay_computes_context_payload_before_outcomes",
            replay_text,
            "build_progress_lane_hard_context_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "selector_equivalence_audit_available",
            selector_text,
            ("selected_index", "selection_scores", "require_equivalent"),
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
            "matched_context_contract_audit_available",
            context_contract_text,
            (
                "dp_camp_matched_progress_lane_hard_context_outcome_contract_v1",
                "progress_lane_hard_context_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
        _check_tokens(
            "revised_atom_separability_audit_available",
            revised_text,
            (
                "dp_camp_revised_progress_lane_hard_context_atom_separability_v1",
                "revised_progress_lane_hard_context_atoms",
                "candidate_closed_loop_outcomes_missing_for_revised_atom_separability",
                "score_k(w)=a_k^T w",
            ),
        ),
    ]


def _plan_checks(spec: BroaderSmokeSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    npc_counts = {run.max_npcs for run in spec.runs}
    route_names = {run.route_name for run in spec.runs}
    bucket_counts = _bucket_counts(spec)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": not (seeds & FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "small_nonformal_matched_scope",
            "passed": len(spec.runs) == 4 and int(spec.steps) == 12,
            "details": {"runs": len(spec.runs), "steps": int(spec.steps)},
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": int(spec.num_candidates) == 8,
            "details": {"num_candidates": int(spec.num_candidates)},
        },
        {
            "name": "traffic_light_on_and_off_covered",
            "passed": {"on", "off"}.issubset(traffic_modes),
            "details": {"traffic_light_modes": sorted(traffic_modes)},
        },
        {
            "name": "npc_and_no_npc_covered",
            "passed": 0 in npc_counts and any(count > 0 for count in npc_counts),
            "details": {"max_npcs": sorted(npc_counts)},
        },
        {
            "name": "red_turn_and_normal_routes_covered",
            "passed": {
                "sample_map_tl_route_59_to_86",
                "sample_map_route_2_to_104",
            }.issubset(route_names),
            "details": {"route_names": sorted(route_names)},
        },
        {
            "name": "scenario_buckets_cover_required_contexts",
            "passed": all(
                bucket_counts.get(bucket, 0) > 0
                for bucket in (
                    "traffic_light",
                    "red_light_turn",
                    "sharp_turn",
                    "npc_interaction",
                    "normal",
                )
            ),
            "details": {"bucket_counts": bucket_counts},
        },
    ]


def _coverage_targets(spec: BroaderSmokeSpec) -> dict[str, Any]:
    matched_records = len(spec.runs) * int(spec.steps)
    return {
        "paired_runs": len(spec.runs),
        "baseline_logs": len(spec.runs),
        "matched_logs": len(spec.runs),
        "matched_records": matched_records,
        "matched_candidate_rows": matched_records * int(spec.num_candidates),
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _commands(
    spec: BroaderSmokeSpec,
    *,
    source_smoke_audit_path: str,
) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    matched_root = f"{spec.root}/matched_revised_context_outcomes"
    audit_root = f"{spec.root}/audit"
    replays: list[dict[str, Any]] = []
    for run in spec.runs:
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "baseline",
                "command": _replay_command(
                    spec,
                    run,
                    f"{baseline_root}/{run.run_id}",
                    matched=False,
                ),
            }
        )
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "matched_revised_context_outcomes",
                "command": _replay_command(
                    spec,
                    run,
                    f"{matched_root}/{run.run_id}",
                    matched=True,
                ),
            }
        )
    return {
        "paired_replays": replays,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            matched_root,
            audit_root,
        ),
        "dataset_required_outcome_audit": _dataset_audit_command(
            matched_root,
            audit_root,
            spec,
        ),
        "matched_context_contract_audit": _matched_context_contract_command(
            matched_root,
            audit_root,
            spec,
        ),
        "revised_atom_separability_audit": _revised_atom_separability_command(
            matched_root,
            audit_root,
            source_smoke_audit_path,
        ),
    }


def _revised_atom_separability_command(
    matched_root: str,
    audit_root: str,
    source_smoke_audit_path: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability.py",
        "--root",
        matched_root,
        "--source_smoke_audit_json",
        source_smoke_audit_path,
        "--fail_on_formal_seeds",
        "--output_json",
        f"{audit_root}/revised_context_atom_separability.json",
        "--output_md",
        f"{audit_root}/revised_context_atom_separability.md",
    ]


def _accept_criteria(spec: BroaderSmokeSpec) -> list[str]:
    return [
        f"exactly {len(spec.runs)} baseline logs and {len(spec.runs)} matched logs",
        f"exactly {len(spec.runs) * int(spec.steps)} matched records",
        "all matched records contain progress_lane_hard_context_logging",
        "all matched records contain complete candidate_closed_loop_outcomes",
        "selector equivalence remains exact between baseline and matched branches",
        "dataset audit passes with closed_loop_outcome_policy=required",
        "revised atom separability audit reaches a supported accept/reject decision",
        "formal seeds 11/12/13 remain absent",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any formal seed appears",
        "any replay command fails",
        "selector equivalence fails",
        "dataset required-outcome audit fails",
        "matched context contract audit fails",
        "revised atom separability audit cannot classify candidates",
        "any evidence suggests online selector behavior changed",
    ]


def _bucket_counts(spec: BroaderSmokeSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Revised Context Matched Outcome Label Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Coverage Targets",
        "",
        "```json",
        json.dumps(report["coverage_targets"], indent=2, sort_keys=True),
        "```",
        "",
        "## Commands",
        "",
    ]
    for item in report["commands"]["paired_replays"]:
        lines.extend(
            [
                f"### {item['variant']} {item['run_id']}",
                "",
                "```bash",
                " ".join(item["command"]),
                "```",
                "",
            ]
        )
    for key in (
        "selector_equivalence",
        "dataset_required_outcome_audit",
        "matched_context_contract_audit",
        "revised_atom_separability_audit",
    ):
        lines.extend(["### " + key, "", "```bash", " ".join(report["commands"][key]), "```", ""])
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
