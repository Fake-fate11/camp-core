#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations import (
    analyze_diffusion_planner_residual_comfort_remediation_followup_materially_different_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution as base,
)


EXPECTED_DP_HEAD = base.EXPECTED_DP_HEAD
PLANNED_POLICY = "lane_red_hard_feasible_jerk_lateral_material_support"
REMEDIATION_PROFILE = "lane_red_hard_feasible_jerk_lateral_support_v2"
SCREEN_REJECT_STATUS = base.SCREEN_REJECT_STATUS

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)

DEFAULT_SCREEN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "fixed_snapshot_screen_rerun_bff8f8b"
)
SCREEN_JSON = "material_generator_remediation_fixed_snapshot_screen.json"
SCREEN_MD = "material_generator_remediation_fixed_snapshot_screen.md"
CANDIDATE_LOG = base.CANDIDATE_LOG
CANDIDATE_ERR = base.CANDIDATE_ERR
EXIT_CODE = base.EXIT_CODE
HEADS = base.HEADS
SHA256SUMS = base.SHA256SUMS
PY39_IMPORT_FAILURE_ERR = "CANDIDATE_SCREEN.python39_import_failure.err"
BLOCKED_ACTIONS = base.BLOCKED_ACTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only attribution over the v2 material generator remediation "
            "guarded fixed-snapshot screen rerun result."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        screen_root=args.screen_root,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
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


def build_report(
    *,
    screen_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    _configure_base()
    report = base.build_report(
        screen_root=screen_root,
        camp_head=camp_head,
        camp_origin_main=camp_origin_main,
        dp_head=dp_head,
        label=label,
    )
    report["analysis"]["name"] = (
        "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_default_"
        "off_fixed_snapshot_screen_rerun_remediation_negative_support_"
        "followup_residual_comfort_failure_diagnostic_remediation_followup_"
        "materially_different_generator_guarded_fixed_snapshot_screen_rerun_"
        "failure_attribution_remediation_guarded_fixed_snapshot_screen_rerun_"
        "failure_attribution_v1"
    )
    report["analysis"]["role"] = (
        "read-only attribution over completed v2 material remediation screen"
    )
    report["analysis"]["generator_policy"] = PLANNED_POLICY
    report["analysis"]["default_off_remediation_profile"] = REMEDIATION_PROFILE
    _annotate_v2_shape(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    _configure_base()
    markdown = base.render_markdown(report)
    return markdown.replace(
        "# Material Generator Screen Failure Attribution",
        "# Material Generator Remediation Screen Failure Attribution",
        1,
    )


def _configure_base() -> None:
    base.PLANNED_POLICY = PLANNED_POLICY
    base.REMEDIATION_PROFILE = REMEDIATION_PROFILE
    base.READY_STATUS = READY_STATUS
    base.REJECT_STATUS = REJECT_STATUS
    base.AUTHORIZED_NEXT_WORK = AUTHORIZED_NEXT_WORK
    base.DEFAULT_SCREEN_ROOT = DEFAULT_SCREEN_ROOT
    base.SCREEN_JSON = SCREEN_JSON
    base.SCREEN_MD = SCREEN_MD
    base.CANDIDATE_LOG = CANDIDATE_LOG
    base.CANDIDATE_ERR = CANDIDATE_ERR
    base.EXIT_CODE = EXIT_CODE
    base.HEADS = HEADS
    base.SHA256SUMS = SHA256SUMS
    base.PY39_IMPORT_FAILURE_ERR = PY39_IMPORT_FAILURE_ERR


def _annotate_v2_shape(report: dict[str, Any]) -> None:
    source = report["source_summary"]
    attribution = report["read_only_attribution"]
    hard_gap = float(attribution.get("hard_support_gap") or 0.0)
    attribution["v2_hard_support_near_threshold"] = (
        source["hard_support_rate"] > 0.0 and hard_gap <= (1.0 / 21.0)
    )
    attribution["v2_zero_comfort_support"] = source["comfort_admissible_rows"] == 0
    attribution["remediation_followup_training_ready"] = False


if __name__ == "__main__":
    main()
