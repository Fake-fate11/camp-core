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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as CLOSEOUT_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as CLOSEOUT_REVIEW_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_post_nonpromotion_next_gate_plan_ready"
REJECT_STATUS = "candidate_set_consensus_post_nonpromotion_next_gate_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_candidate_availability_diversity_synthesis_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_CLOSEOUT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_nonpromotion_closeout_review_a1ebac6"
)

CLOSEOUT_REVIEW_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review.json"
)
CLOSEOUT_REVIEW_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review.md"
)
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only selector for the next candidate-set consensus gate after "
            "the safety-score shadow atom was closed as non-promotion evidence."
        )
    )
    parser.add_argument(
        "--closeout_review_root",
        type=Path,
        default=Path(DEFAULT_CLOSEOUT_REVIEW_ROOT),
    )
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
        closeout_review_root=args.closeout_review_root,
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
    closeout_review_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(closeout_review_root)
    source = _source_summary(artifact.get("json_payload") or {})
    plan = _next_gate_plan(source, closeout_review_root)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_post_nonpromotion_next_gate_plan_v1",
            "label": label,
            "role": (
                "plan-only selection of the next smallest candidate-set "
                "consensus work item after safety-score non-promotion closeout"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This gate only reads the safety-score non-promotion closeout "
                "review artifact and fixed-head audit. It does not recompute "
                "outcomes, define atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, run replay, run DP, "
                "modify DP, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "closeout_review_artifact": _strip_payload(artifact),
        "source_summary": source,
        "next_gate_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["next_gate_plan"]
    lines = [
        "# Candidate-Set Consensus Post-Nonpromotion Next-Gate Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next gate: `{plan['selected_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Closeout review status: `{source['status']}`",
        f"- Closeout complete: `{source['closeout_complete']}`",
        f"- Next gate authorized by source: `{source['post_nonpromotion_next_gate_plan_authorized']}`",
        "",
        "## Selected Direction",
        "",
        f"- Selected work: `{plan['selected_next_work']}`",
        f"- Replay consideration status: `{plan['broader_replay_consideration_status']}`",
        f"- Safety-score atom branch status: `{plan['safety_score_atom_branch_status']}`",
        "",
        "## Rationale",
        "",
    ]
    for item in plan["rationale"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        CLOSEOUT_REVIEW_JSON,
        CLOSEOUT_REVIEW_MD,
        COMMAND_LOG,
        COMMAND_ERR,
        EXIT_CODE,
        HEADS,
        SHA256SUMS,
    )
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[CLOSEOUT_REVIEW_JSON].is_file():
        loaded = _load_json(files[CLOSEOUT_REVIEW_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
    heads = (
        (root / HEADS).read_text(encoding="utf-8", errors="replace")
        if (root / HEADS).is_file()
        else ""
    )
    exit_code = (
        (root / EXIT_CODE).read_text(encoding="utf-8").strip()
        if (root / EXIT_CODE).is_file()
        else None
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "exit_code": exit_code,
        "json_payload": payload,
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("closeout_review"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "closeout_review_ready": bool(decision.get("nonpromotion_closeout_review_ready")),
        "closeout_complete": bool(decision.get("nonpromotion_closeout_complete")),
        "post_nonpromotion_next_gate_plan_authorized": bool(
            decision.get("post_nonpromotion_next_gate_plan_authorized")
        ),
        "review_class": review.get("review_class"),
        "chain_closed": bool(review.get("chain_closed")),
        "next_gate_must_be_plan_only": bool(review.get("next_gate_must_be_plan_only")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _next_gate_plan(source: dict[str, Any], closeout_review_root: Path) -> dict[str, Any]:
    return {
        "closeout_review_root": str(closeout_review_root),
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "fresh_plan_only_gate",
        "broader_replay_consideration_status": "already_completed_not_reopened",
        "safety_score_atom_branch_status": "closed_nonpromotion_not_reopened",
        "rationale": [
            "candidate-set consensus broader materiality replay consideration and guarded replay were already completed earlier in the audit chain",
            "candidate-set consensus atom design, zero-weight dry run, weight sensitivity, and safety-score evaluation were already completed",
            "the safety-score branch ended in a confirmed non-promotion closeout, so it cannot justify atom promotion or online selector work",
            "the remaining useful direction is to synthesize candidate availability/diversity evidence under the fixed DP checkpoint before proposing any new source or intervention",
        ],
        "required_next_gate_checks": [
            "read current audit chain and existing candidate availability/diversity artifacts only",
            "separate already-completed replay evidence from any new replay request",
            "the next work item must remain a fresh plan-only gate",
            "keep DP fixed as a black-box candidate generator",
            "predeclare accept/reject criteria before any execution",
            "record artifact paths, HEADS, and SHA256SUMS",
        ],
        "blocked_boundaries": [
            "no replay is authorized by this gate",
            "no CAMP retraining is authorized by this gate",
            "no atom promotion or online selector change is authorized by this gate",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP modification is not authorized",
            "no safety benefit or DP Top-1 superiority claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "review_class": source["review_class"],
        },
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "closeout_review_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("closeout_review_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("closeout_review_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "closeout_review_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], CLOSEOUT_REVIEW_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_post_nonpromotion_plan",
            source["authorized_next_work"],
            CLOSEOUT_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_closeout_review_ready", source["closeout_review_ready"], True),
        _check_equal("source_closeout_complete", source["closeout_complete"], True),
        _check_equal(
            "source_post_nonpromotion_plan_authorized",
            source["post_nonpromotion_next_gate_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_review_class",
            source["review_class"],
            "confirmed_nonpromotion_closeout_complete",
        ),
        _check_equal("source_chain_closed", source["chain_closed"], True),
        _check_equal("source_next_gate_plan_only", source["next_gate_must_be_plan_only"], True),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("plan_selection_type", plan["selection_type"], "fresh_plan_only_gate"),
        _check_equal(
            "plan_does_not_reopen_broader_replay",
            plan["broader_replay_consideration_status"],
            "already_completed_not_reopened",
        ),
        _check_equal(
            "plan_does_not_reopen_safety_score_branch",
            plan["safety_score_atom_branch_status"],
            "closed_nonpromotion_not_reopened",
        ),
        _check_equal("plan_has_rationale", bool(plan["rationale"]), True),
        _check_equal("plan_has_required_next_gate_checks", bool(plan["required_next_gate_checks"]), True),
        _check_equal("plan_has_blocked_boundaries", bool(plan["blocked_boundaries"]), True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        plan["rationale"] + plan["required_next_gate_checks"] + plan["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text or "plan only" in text, True),
        _check_equal("boundary_blocks_replay", "no replay" in text or "not authorized" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp modification" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "post_nonpromotion_next_gate_plan_ready": passed,
        "candidate_availability_diversity_synthesis_plan_authorized": passed,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
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
        item = root / name.strip()
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append({"path": str(item), "expected": expected, "actual": actual, "ok": matched})
    return ok, details


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
