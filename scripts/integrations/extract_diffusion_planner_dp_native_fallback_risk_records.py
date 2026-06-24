#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_ranking import (  # noqa: E402
    EXPECTED_DP_HEAD,
    build_report as build_audit_report,
)


DISABLED_STATUS = "dp_native_fallback_risk_extractor_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_extractor_complete"
REJECT_STATUS = "dp_native_fallback_risk_extractor_rejected"

FORBIDDEN_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "Full36_authorized",
    "formal_seeds_11_12_13_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only extractor for DP-native CAMP fallback-risk "
            "diagnostic records."
        )
    )
    parser.add_argument("--evaluation_root", type=Path, required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_extractor",
        action="store_true",
        help="Explicit opt-in required before reading selection logs.",
    )
    parser.add_argument("--expected_dp_head", default=EXPECTED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=None)
    parser.add_argument("--camp_head", default=None)
    parser.add_argument("--camp_origin_main", default=None)
    parser.add_argument("--expected_summary_sha256", default=None)
    parser.add_argument("--expected_no_feasible_records", type=int, default=15)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_extraction_report(
        evaluation_root=args.evaluation_root,
        enabled=args.enable_default_off_fallback_risk_extractor,
        expected_dp_head=args.expected_dp_head,
        dp_head=_git_head(args.dp_repo) if args.dp_repo else args.expected_dp_head,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        expected_summary_sha256=args.expected_summary_sha256,
        expected_no_feasible_records=args.expected_no_feasible_records,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if report["final_decision"]["status"] == REJECT_STATUS:
        raise SystemExit(1)


def build_extraction_report(
    *,
    evaluation_root: Path,
    enabled: bool = False,
    expected_dp_head: str = EXPECTED_DP_HEAD,
    dp_head: str = EXPECTED_DP_HEAD,
    camp_head: str | None = None,
    camp_origin_main: str | None = None,
    expected_summary_sha256: str | None = None,
    expected_no_feasible_records: int = 15,
    label: str | None = None,
) -> dict[str, Any]:
    base = {
        "analysis": {
            "name": "dp_native_fallback_risk_extractor_v1",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "fixed_source_artifact_only": True,
            "records_scope": "records_without_feasible_candidate_only",
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {"evaluation_root": str(evaluation_root)},
        "heads": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": expected_dp_head,
        },
        "fallback_risk_records": [],
        "record_counts": {
            "records_total": 0,
            "records_without_feasible_candidate": 0,
            "records_with_feasible_candidate": 0,
        },
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=bool(enabled),
            failed_checks=[],
        ),
    }
    if not enabled:
        return base

    audit = build_audit_report(
        evaluation_root=evaluation_root,
        expected_dp_head=expected_dp_head,
        dp_head=dp_head,
        camp_head=camp_head,
        camp_origin_main=camp_origin_main,
        expected_summary_sha256=expected_summary_sha256,
        expected_no_feasible_records=expected_no_feasible_records,
        label=label,
    )
    passed = bool(audit["final_decision"]["passed"])
    base.update(
        {
            "source_paths": audit["source_paths"],
            "source_hashes": audit["source_hashes"],
            "summary_evidence": audit["summary_evidence"],
            "record_counts": audit["record_counts"],
            "ranking_summary": audit["ranking_summary"],
            "fallback_risk_records": [
                _slim_record(record) for record in audit["record_audits"]
            ],
            "audit_failed_checks": audit["final_decision"]["failed_checks"],
            "final_decision": _decision(
                status=COMPLETE_STATUS if passed else REJECT_STATUS,
                passed=passed,
                enabled=True,
                failed_checks=audit["final_decision"]["failed_checks"],
            ),
        }
    )
    return base


def _slim_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record["run_id"],
        "record_index": record["record_index"],
        "candidate_count": record["candidate_count"],
        "selected_index": record["selected_index"],
        "selected_index_in_range": record["selected_index_in_range"],
        "union_reasons": record["union_reasons"],
        "all_candidate_reason_signature": record["all_candidate_reason_signature"],
        "ranking": {
            metric: {
                "min_cost": payload["min_cost"],
                "min_indices": payload["min_indices"],
                "selected_cost": payload["selected_cost"],
                "selected_is_min": payload["selected_is_min"],
                "lower_cost_candidate_indices": payload[
                    "lower_cost_candidate_indices"
                ],
            }
            for metric, payload in record["ranking"].items()
        },
        "candidate_tensor_provenance_checks": record[
            "candidate_tensor_provenance"
        ].get("checks", {}),
        "no_mutation_evidence_checks": record["no_mutation_evidence"].get(
            "checks",
            {},
        ),
        "errors": record["errors"],
    }


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    failed_checks: list[str],
) -> dict[str, Any]:
    decision = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "failed_checks": failed_checks,
        "fallback_risk_extractor_output_written": bool(enabled and passed),
        "implementation_scope": "default_off_read_only_extractor",
        "training_authorized": False,
        "production_selector_change_authorized": False,
        "online_selector_change_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _git_head(path: Path | None) -> str:
    if path is None:
        return EXPECTED_DP_HEAD
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["record_counts"]
    lines = [
        "# DP Native Fallback Risk Extractor",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"records_without_feasible_candidate={counts['records_without_feasible_candidate']}",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "```",
        "",
    ]
    if not decision["enabled"]:
        lines.extend(
            [
                "The extractor is default-off. No selection logs were read and "
                "no fallback-risk records were emitted.",
                "",
            ]
        )
        return "\n".join(lines)
    lines.extend(
        [
            "## Ranking Summary",
            "",
            "| Metric | Records | Selected at min | Lower-cost fixed candidate available |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for metric in ("red", "lane", "quality"):
        item = report["ranking_summary"][metric]
        lines.append(
            "| `{}` | {} | {} | {} |".format(
                metric,
                item["records"],
                item["selected_min_count"],
                item["lower_cost_candidate_available_count"],
            )
        )
    lines.extend(
        [
            "",
            "This extractor only reads existing fixed candidate logs. It does not "
            "run replay, generate candidates, train CAMP, modify DP, promote a "
            "selector or atom, or claim safety benefit.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
