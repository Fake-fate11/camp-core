#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as ANALYSIS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as ANALYSIS_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    DEFAULT_DEVELOPMENT_ROOT,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_static_contract_review_only"
)

DEFAULT_ANALYSIS_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "failure_attribution_analysis_432c2cb"
)
ANALYSIS_JSON = "fixed_snapshot_screen_rerun_failure_attribution_analysis.json"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
ANALYSIS_EXIT = "ANALYSIS_EXIT"

BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "fixed_snapshot_screen_rerun_execution_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_evidence",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only remediation design for the default-off fixed-snapshot "
            "rerun after read-only failure attribution."
        )
    )
    parser.add_argument("--analysis_root", type=Path, default=Path(DEFAULT_ANALYSIS_ROOT))
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
        analysis_root=args.analysis_root,
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
    analysis_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(
        analysis_root,
        required_files=(ANALYSIS_JSON, ANALYSIS_EXIT, HEADS, SHA256SUMS),
    )
    analysis_payload = _load_json_if_present(analysis_root / ANALYSIS_JSON)
    source = _source_summary(analysis_payload)
    design = _remediation_design(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_analysis_authorization_checks(source),
        *_source_evidence_checks(source),
        *_design_checks(design),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "remediation_design_plan_v1"
            ),
            "label": label,
            "role": "plan-only remediation design over read-only attribution evidence",
            "plan_only": True,
            "read_only_source": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This plan reads only the existing read-only attribution "
                "artifact and current fixed-head audit. It does not implement "
                "candidate generation, create candidates, rerun the screen, "
                "run DP, run replay, use formal seeds, recompute outcomes, "
                "define runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, claim safety benefit, claim CAMP is better than DP "
                "Top-1, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "analysis_artifact": artifact,
        "source_summary": source,
        "remediation_design": design,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    design = report["remediation_design"]
    lines = [
        "# Default-Off Fixed-Snapshot Rerun Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Attribution Inputs",
        "",
        f"- Primary blocker family: `{source['primary_blocker_family']}`",
        f"- Primary comfort blocker: `{source['primary_comfort_blocker']}`",
        f"- Primary hard blocker: `{source['primary_hard_blocker']}`",
        f"- Primary latency source: `{source['primary_latency_source']}`",
        f"- Recommendation: `{source['recommendation_category']}`",
        f"- Absolute lateral guard retained: `{source['absolute_lateral_guard_retained']}`",
        "",
        "## Design Priorities",
        "",
    ]
    for item in design["design_priorities"]:
        lines.append(
            f"- `{item['priority']}` `{item['focus']}` from `{item['evidence']}`"
        )
    lines.extend(["", "## Plan-Only Remediation Threads", ""])
    for item in design["remediation_threads"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - scope: {item['scope']}")
        lines.append(f"  - static contract: {item['static_contract']}")
        lines.append(f"  - rejection boundary: {item['rejection_boundary']}")
    lines.extend(["", "## Required Next Gate Checks", ""])
    for item in design["next_gate_checks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- implementation is not authorized",
            "- candidate generation execution is not authorized",
            "- fixed-snapshot screen rerun is not authorized",
            "- replay is not authorized",
            "- formal seeds 11/12/13 remain frozen and unused",
            "- Full36 is not authorized",
            "- atom promotion, CAMP retraining, and online selector changes are not authorized",
            "- DP weights and DP code must remain fixed",
            "- no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "- no DP-side classical Benders claim is authorized",
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "remediation_static_contract_review_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path, *, required_files: tuple[str, ...]) -> dict[str, Any]:
    files = {name: (root / name).is_file() for name in required_files}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "analysis_exit": _read_text(root / ANALYSIS_EXIT).strip() or None,
        "heads_text_present": bool(_read_text(root / HEADS).strip()),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    source = _dict(payload.get("source_summary"))
    screen = _dict(source.get("screen"))
    return {
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "candidate_generation_execution_authorized": bool(
            decision.get("candidate_generation_execution_authorized")
        ),
        "fixed_snapshot_screen_rerun_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_authorized")
        ),
        "fixed_snapshot_screen_rerun_execution_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_execution_authorized")
        ),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "full36_authorized": bool(decision.get("full36_authorized")),
        "online_selector_authorized": bool(decision.get("online_selector_authorized")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "camp_over_dp_top1_claim_authorized": bool(
            decision.get("camp_over_dp_top1_claim_authorized")
        ),
        "classic_benders_claim_authorized": bool(
            decision.get("classic_benders_claim_authorized")
        ),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "primary_comfort_blocker": attribution.get("primary_comfort_blocker"),
        "primary_hard_blocker": attribution.get("primary_hard_blocker"),
        "primary_latency_source": attribution.get("primary_latency_source"),
        "recommendation_category": attribution.get("recommendation_category"),
        "absolute_lateral_guard_retained": bool(
            attribution.get("absolute_lateral_guard_retained")
        ),
        "comfort_blocker_ranking": _list(attribution.get("comfort_blocker_ranking")),
        "hard_blocker_ranking": _list(attribution.get("hard_blocker_ranking")),
        "latency_ranking": _list(attribution.get("latency_ranking")),
        "latency_gate_failures": _list(attribution.get("latency_gate_failures")),
        "absolute_guard_failure_ranking": _list(
            attribution.get("absolute_guard_failure_ranking")
        ),
        "generated_candidate_rows": _int(screen.get("generated_candidate_rows")),
        "comfort_rows": _int(screen.get("comfort_rows")),
    }


def _remediation_design(source: dict[str, Any]) -> dict[str, Any]:
    comfort = _top_name(source["comfort_blocker_ranking"])
    hard = _top_name(source["hard_blocker_ranking"])
    latency = source["primary_latency_source"] or _top_name(source["latency_ranking"])
    return {
        "selection_type": "remediation_design_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "design_priorities": [
            {
                "priority": 1,
                "focus": "restore comfort support without relaxing no-leak boundaries",
                "evidence": comfort,
            },
            {
                "priority": 2,
                "focus": "separate immutable DP hard blockers from CAMP-side proposal limits",
                "evidence": hard,
            },
            {
                "priority": 3,
                "focus": "bound candidate-build and total p95 before any rerun",
                "evidence": latency,
            },
            {
                "priority": 4,
                "focus": "keep absolute lateral guard as diagnostic subset only",
                "evidence": "absolute_lateral_guard_retained",
            },
        ],
        "remediation_threads": [
            {
                "name": "relative_comfort_static_contract",
                "scope": (
                    "inspect jerk, lateral, progress-loss, rollout-distance, "
                    "and smoothness thresholds as static contracts before any "
                    "code change or screen rerun"
                ),
                "static_contract": (
                    "predeclare current-tick fields only, no future outcomes, "
                    "and no DP internals; any later atom discussion must prove "
                    "nonnegative or hinge/signed-split legality"
                ),
                "rejection_boundary": (
                    "reject if the proposal needs outcome labels, online "
                    "lambda selection, DP modification, or screen execution"
                ),
            },
            {
                "name": "hard_blocker_separation_contract",
                "scope": (
                    "classify dp_kinematic, road-border, lane, and red-timing "
                    "failures into immutable DP candidate limits versus "
                    "candidate policy constraints"
                ),
                "static_contract": (
                    "preserve DP as a fixed black-box candidate generator and "
                    "avoid claiming valid cuts or classical Benders structure"
                ),
                "rejection_boundary": (
                    "reject if remediation requires DP code, weights, config, "
                    "or invocation changes"
                ),
            },
            {
                "name": "latency_static_contract",
                "scope": (
                    "inspect candidate-build and total p95 contributors for "
                    "default-off deterministic pruning, caching, or vectorized "
                    "bookkeeping plans that can be unit-tested first"
                ),
                "static_contract": (
                    "predeclare deterministic inputs, stable ordering, and "
                    "no reward/tracker semantic change before implementation"
                ),
                "rejection_boundary": (
                    "reject if the proposal makes GPU timing claims, needs "
                    "broader replay, or changes DP reward/tracker code"
                ),
            },
            {
                "name": "absolute_guard_subset_contract",
                "scope": (
                    "treat the absolute lateral guard survivors as a diagnostic "
                    "subset for prioritization only"
                ),
                "static_contract": (
                    "predeclare that subset survival is not safety evidence and "
                    "does not imply CAMP improvement over DP Top-1"
                ),
                "rejection_boundary": (
                    "reject if the proposal promotes atoms, selector behavior, "
                    "or safety claims from subset support"
                ),
            },
        ],
        "next_gate_checks": [
            "read-only source and artifact inspection only",
            "no candidate generation and no fixed-snapshot screen rerun",
            "no replay, Full36, or formal seeds",
            "no atom promotion, CAMP retraining, or online selector change",
            "no DP code, weights, config, or invocation changes",
            "explicit score_k(w)=a_k^T w preservation if atoms are discussed",
            "explicit convex simplex/CVaR/L2 master preservation",
            "explicit default-off boundary for any later implementation plan",
            "artifact HEADS and SHA256SUMS recorded before any later implementation gate",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("analysis_artifact_exists", artifact["exists"], True),
        _check_equal("analysis_required_files_present", artifact["required_files_present"], True),
        _check_equal("analysis_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("analysis_exit_zero", artifact["analysis_exit"], "0"),
        _check_equal("analysis_heads_present", artifact["heads_text_present"], True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _analysis_authorization_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = [key for key in BLOCKED_ACTIONS if source.get(key)]
    return [
        _check_equal("analysis_status_complete", source["status"], ANALYSIS_READY_STATUS),
        _check_equal(
            "analysis_authorizes_remediation_design",
            source["authorized_next_work"],
            ANALYSIS_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("analysis_blocked_actions_clear", blocked, []),
    ]


def _source_evidence_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "primary_blocker_family_comfort_deficit",
            source["primary_blocker_family"],
            "comfort_support_deficit",
        ),
        _check_equal("primary_comfort_blocker_present", source["primary_comfort_blocker"] is not None, True),
        _check_equal("primary_hard_blocker_present", source["primary_hard_blocker"] is not None, True),
        _check_equal("primary_latency_source_present", source["primary_latency_source"] is not None, True),
        _check_equal("recommendation_plan_only", source["recommendation_category"], "design-new-policy-plan-only"),
        _check_equal("absolute_lateral_guard_retained", source["absolute_lateral_guard_retained"], True),
        _check_equal("comfort_rows_zero", source["comfort_rows"], 0),
        _check_equal("generated_rows_positive", source["generated_candidate_rows"] > 0, True),
        _check_equal("comfort_ranking_present", bool(source["comfort_blocker_ranking"]), True),
        _check_equal("hard_ranking_present", bool(source["hard_blocker_ranking"]), True),
        _check_equal("latency_gate_failures_present", bool(source["latency_gate_failures"]), True),
    ]


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(design, sort_keys=True).lower()
    return [
        _check_equal("design_selected_next_work", design["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("design_is_plan_only", design["selection_type"], "remediation_design_plan_only"),
        _check_equal("design_has_four_priorities", len(design["design_priorities"]), 4),
        _check_equal("design_has_four_threads", len(design["remediation_threads"]), 4),
        _check_equal("design_mentions_comfort", "comfort" in text, True),
        _check_equal("design_mentions_hard_blocker", "hard blocker" in text, True),
        _check_equal("design_mentions_latency", "latency" in text, True),
        _check_equal("design_mentions_absolute_guard", "absolute lateral guard" in text, True),
        _check_equal("design_mentions_default_off", "default-off" in text, True),
        _check_equal("design_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("design_mentions_convex_master", "convex simplex/cvar/l2 master" in text, True),
        _check_equal("design_blocks_benders", "classical benders" in text, True),
        _check_equal("design_blocks_safety_claims", "not safety evidence" in text, True),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"], False),
        _check_equal("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"], False),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal("boundary_blocks_camp_over_dp_top1_claim", decision["camp_over_dp_top1_claim_authorized"], False),
        _check_equal("boundary_blocks_benders", decision["classic_benders_claim_authorized"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "remediation_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
        "implementation_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _sha256sum_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    root = path.parent
    details = []
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            ok = False
            details.append({"line": line, "ok": False, "reason": "malformed"})
            continue
        expected, name = parts
        item = Path(name.strip())
        if not item.is_absolute():
            item = root / item
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append({"path": str(item), "expected": expected, "actual": actual, "ok": matched})
    return ok, details


def _load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _top_name(items: list[Any]) -> str | None:
    if not items:
        return None
    first = _dict(items[0])
    return first.get("name")


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    main()
