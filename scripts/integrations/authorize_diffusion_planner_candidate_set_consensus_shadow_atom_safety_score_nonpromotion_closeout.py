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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_nonpromotion_closeout_plan_bfb5375"
)

PLAN_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_plan.json"
)
PLAN_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_plan.md"
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
            "Authorization-only gate for the candidate-set consensus "
            "safety-score non-promotion closeout. It verifies the closeout "
            "plan artifact and fixed-head boundaries but does not record the "
            "closeout yet."
        )
    )
    parser.add_argument("--plan_root", type=Path, default=Path(DEFAULT_PLAN_ROOT))
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
        plan_root=args.plan_root,
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
    plan_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(plan_root)
    plan = _plan_summary(artifact.get("json_payload") or {})
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_authorization_v1"
            ),
            "label": label,
            "role": (
                "authorization-only gate for final documentation-only "
                "non-promotion closeout recording"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closeout_recorded": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This authorization gate reads only the closeout-plan "
                "artifact and fixed-head audit. It does not recompute "
                "outcomes, define atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, run replay, "
                "run DP, modify DP, or claim a DP-side classical Benders "
                "decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "plan_artifact": _strip_payload(artifact),
        "plan_summary": plan,
        "authorization_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["plan_summary"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Non-Promotion Closeout Authorization",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout record authorized: `{decision['nonpromotion_closeout_record_authorized']}`",
        f"- Closeout recorded: `{decision['nonpromotion_closeout_recorded']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Heads",
        "",
        f"`{report['head_audit']}`",
        "",
        "## Artifact",
        "",
        f"- Plan root: `{report['plan_artifact']['root']}`",
        f"- SHA OK: `{report['plan_artifact']['sha256sums_ok']}`",
        f"- Exit code: `{report['plan_artifact']['exit_code']}`",
        "",
        "## Source Plan",
        "",
        f"- Source status: `{plan['status']}`",
        f"- Source authorizes this gate: `{plan['authorization_gate_authorized']}`",
        f"- Default-off retained: `{plan['default_off_retained']}`",
        f"- Executes closeout now: `{plan['executes_closeout_now']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This gate does not authorize safety benefit claims, atom promotion, "
        "CAMP retraining, online selector changes, formal seeds, Full36, "
        "replay, label attachment beyond a final documentation-only closeout "
        "record, or DP modification.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["authorization_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (PLAN_JSON, PLAN_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[PLAN_JSON].is_file():
        loaded = _load_json(files[PLAN_JSON])
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


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("closeout_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_ready": bool(decision.get("nonpromotion_closeout_plan_ready")),
        "authorization_gate_authorized": bool(
            decision.get("nonpromotion_closeout_authorization_gate_authorized")
        ),
        "closeout_authorized": bool(decision.get("nonpromotion_closeout_authorized")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "closeout_decision": plan.get("closeout_decision"),
        "default_off_retained": bool(plan.get("default_off_retained")),
        "executes_closeout_now": bool(plan.get("executes_closeout_now")),
        "requires_new_replay": bool(plan.get("requires_new_replay")),
        "requires_label_attachment": bool(plan.get("requires_label_attachment")),
        "requires_camp_training": bool(plan.get("requires_camp_training")),
        "requires_atom_promotion": bool(plan.get("requires_atom_promotion")),
        "requires_online_selector_change": bool(
            plan.get("requires_online_selector_change")
        ),
        "requires_dp_modification": bool(plan.get("requires_dp_modification")),
        "promotion_blockers": list(plan.get("promotion_blockers") or []),
        "required_closeout_records": list(plan.get("required_closeout_records") or []),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "plan_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("plan_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("plan_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "plan_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_plan_status", plan["status"], PLAN_READY_STATUS),
        _check_equal("source_plan_passed", plan["passed"], True),
        _check_equal(
            "source_authorizes_closeout_authorization",
            plan["authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_plan_ready", plan["plan_ready"], True),
        _check_equal(
            "source_authorization_gate_authorized",
            plan["authorization_gate_authorized"],
            True,
        ),
        _check_equal("source_closeout_not_already_authorized", plan["closeout_authorized"], False),
        _check_equal("source_no_blocked_actions", plan["blocked_action_conflicts"], []),
        _check_equal(
            "source_closeout_decision_nonpromotion",
            plan["closeout_decision"],
            "do_not_promote_shadow_atom_keep_default_off",
        ),
        _check_equal("source_default_off_retained", plan["default_off_retained"], True),
        _check_equal("source_executes_nothing_now", plan["executes_closeout_now"], False),
        _check_equal("source_no_new_replay", plan["requires_new_replay"], False),
        _check_equal("source_no_label_attachment", plan["requires_label_attachment"], False),
        _check_equal("source_no_camp_training", plan["requires_camp_training"], False),
        _check_equal("source_no_atom_promotion", plan["requires_atom_promotion"], False),
        _check_equal(
            "source_no_online_selector",
            plan["requires_online_selector_change"],
            False,
        ),
        _check_equal("source_no_dp_modification", plan["requires_dp_modification"], False),
        _check_equal("source_has_promotion_blockers", bool(plan["promotion_blockers"]), True),
        _check_equal(
            "source_has_required_closeout_records",
            bool(plan["required_closeout_records"]),
            True,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["promotion_blockers"] + plan["required_closeout_records"]).lower()
    return [
        _check_equal("boundary_mentions_no_safety_benefit", "safety_benefit_evidence" in text, True),
        _check_equal("boundary_mentions_default_off", "default-off" in text or "default_off" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text or "training" in text, True),
        _check_equal("boundary_blocks_online", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp modification" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "nonpromotion_closeout_authorization_ready": passed,
        "nonpromotion_closeout_record_authorized": passed,
        "nonpromotion_closeout_recorded": False,
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
