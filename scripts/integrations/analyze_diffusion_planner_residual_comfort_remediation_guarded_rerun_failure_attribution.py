#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

_BASE_MODULE = (
    "scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_"
    "projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution"
)
_POST_REVIEW_MODULE = (
    "scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_"
    "projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_remediation_"
    "post_implementation_static_contract"
)
_base = importlib.import_module(_BASE_MODULE)
_post_review = importlib.import_module(_POST_REVIEW_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_guarded_fixed_snapshot_"
    "screen_rerun_failure_attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_guarded_fixed_snapshot_"
    "screen_rerun_failure_attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SCREEN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_fixed_snapshot_screen_rerun_bff8f8b"
)

SCREEN_JSON = "residual_comfort_remediation_fixed_snapshot_screen.json"
SCREEN_MD = "residual_comfort_remediation_fixed_snapshot_screen.md"
CANDIDATE_LOG = _base.CANDIDATE_LOG
CANDIDATE_ERR = _base.CANDIDATE_ERR
EXIT_CODE = _base.EXIT_CODE
HEADS = _base.HEADS
SHA256SUMS = _base.SHA256SUMS
SCREEN_REJECT_STATUS = _base.SCREEN_REJECT_STATUS
EXPECTED_DP_HEAD = _base.EXPECTED_DP_HEAD
PLANNED_POLICY = _post_review.PLANNED_POLICY
BLOCKED_ACTIONS = _base.BLOCKED_ACTIONS

_PATCHED_BASE_NAMES = (
    "READY_STATUS",
    "REJECT_STATUS",
    "AUTHORIZED_NEXT_WORK",
    "DEFAULT_SCREEN_ROOT",
    "SCREEN_JSON",
    "SCREEN_MD",
    "PLANNED_POLICY",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only attribution over the residual comfort remediation "
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
    label: Optional[str] = None,
) -> dict[str, Any]:
    with _configured_base():
        report = _base.build_report(
            screen_root=screen_root,
            camp_head=camp_head,
            camp_origin_main=camp_origin_main,
            dp_head=dp_head,
            label=label,
        )
        payload = _base._read_json(screen_root / SCREEN_JSON)
        report["checks"].extend(_remediation_specific_checks(payload))
        passed = all(check["passed"] for check in report["checks"])
        report["final_decision"] = _base._final_decision(passed, report["checks"])

    report["analysis"]["name"] = (
        "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_default_"
        "off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
        "residual_comfort_failure_diagnostic_remediation_guarded_fixed_"
        "snapshot_screen_rerun_failure_attribution_v1"
    )
    report["analysis"]["role"] = (
        "read-only attribution over completed residual comfort remediation "
        "guarded fixed-snapshot screen rerun"
    )
    report["analysis"]["math_boundary"] = (
        "This gate reads only completed fixed-snapshot screen artifacts. It "
        "does not create candidates, rerun the screen, run replay, use formal "
        "seeds, define or promote runtime atoms, choose lambda online, alter "
        "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, train "
        "CAMP, change online selection, modify DP weights or code, or claim a "
        "DP-side classical Benders decomposition."
    )
    _augment_decision(report["final_decision"])
    return report


def render_markdown(report: dict[str, Any]) -> str:
    with _configured_base():
        markdown = _base.render_markdown(report)
    lines = markdown.splitlines()
    if lines:
        lines[0] = "# Residual Comfort Remediation Screen Failure Attribution"
    return "\n".join(lines) + "\n"


@contextmanager
def _configured_base() -> Iterator[None]:
    saved = {name: getattr(_base, name) for name in _PATCHED_BASE_NAMES}
    updates = {
        "READY_STATUS": READY_STATUS,
        "REJECT_STATUS": REJECT_STATUS,
        "AUTHORIZED_NEXT_WORK": AUTHORIZED_NEXT_WORK,
        "DEFAULT_SCREEN_ROOT": DEFAULT_SCREEN_ROOT,
        "SCREEN_JSON": SCREEN_JSON,
        "SCREEN_MD": SCREEN_MD,
        "PLANNED_POLICY": PLANNED_POLICY,
    }
    for name, value in updates.items():
        setattr(_base, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(_base, name, value)


def _remediation_specific_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _base._dict(payload.get("analysis"))
    config = _base._dict(payload.get("config"))
    return [
        _base._check(
            "screen_candidate_generation_was_executed",
            analysis.get("candidate_generation_executed") is True,
        ),
        _base._check(
            "screen_no_future_outcome_labels",
            analysis.get("uses_outcome_labels") is False,
        ),
        _base._check(
            "screen_no_selection_effect",
            analysis.get("selection_effect") is False,
        ),
        _base._check(
            "screen_max_remediation_candidates_12",
            config.get("max_remediation_candidates") == 12,
        ),
    ]


def _augment_decision(decision: dict[str, Any]) -> None:
    passed = bool(decision.get("passed"))
    decision["fixed_snapshot_screen_rerun_failure_attribution_complete"] = passed
    decision["followup_design_plan_authorized"] = passed
    decision["candidate_generation_execution_authorized"] = False
    decision["fixed_snapshot_screen_rerun_authorized"] = False
    decision["closed_loop_replay_authorized"] = False
    decision["formal_seeds_authorized"] = False
    decision["full36_authorized"] = False
    decision["atom_promotion_authorized"] = False
    decision["online_selector_promotion_authorized"] = False
    decision["camp_retraining_authorized"] = False
    decision["training_execution_authorized"] = False
    decision["dp_modification_authorized"] = False


if __name__ == "__main__":
    main()
