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
from scripts.integrations.record_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as RECORD_AUTHORIZED_NEXT_WORK,
    READY_STATUS as RECORD_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review_rejected"
)
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_post_nonpromotion_next_gate_plan_only"

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_RECORD_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_nonpromotion_closeout_record_f64e134"
)

RECORD_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record.json"
)
RECORD_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record.md"
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
            "Review-only gate for the final non-promotion closeout record. "
            "It verifies the record artifact and confirms the safety-score "
            "shadow atom chain is closed without promotion."
        )
    )
    parser.add_argument("--record_root", type=Path, default=Path(DEFAULT_RECORD_ROOT))
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
        record_root=args.record_root,
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
    record_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(record_root)
    source = _source_summary(artifact.get("json_payload") or {})
    review = _review_summary(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_review_checks(review),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_review_v1"
            ),
            "label": label,
            "role": (
                "review-only confirmation that the safety-score shadow atom "
                "chain is closed without promotion"
            ),
            "review_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This review reads only the closeout-record artifact and "
                "fixed-head audit. It does not recompute outcomes, define "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, run replay, run DP, modify DP, or "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "record_artifact": _strip_payload(artifact),
        "source_summary": source,
        "closeout_review": review,
        "review_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    review = report["closeout_review"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Non-Promotion Closeout Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout complete: `{decision['nonpromotion_closeout_complete']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Record Source",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source recorded: `{source['recorded']}`",
        f"- Final atom state: `{source['final_atom_state']}`",
        f"- Evidence class: `{source['evidence_class']}`",
        "",
        "## Review",
        "",
        f"- Review class: `{review['review_class']}`",
        f"- Chain closed: `{review['chain_closed']}`",
        f"- Next gate must be plan-only: `{review['next_gate_must_be_plan_only']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This review does not authorize safety benefit claims, atom promotion, "
        "CAMP retraining, online selector changes, formal seeds, Full36, "
        "replay, new label attachment, or DP modification.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (RECORD_JSON, RECORD_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[RECORD_JSON].is_file():
        loaded = _load_json(files[RECORD_JSON])
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
    record = _dict(payload.get("closeout_record"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "record_ready": bool(decision.get("nonpromotion_closeout_record_ready")),
        "recorded": bool(decision.get("nonpromotion_closeout_recorded")),
        "review_authorized": bool(decision.get("nonpromotion_closeout_review_authorized")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "record_decision": record.get("record_decision"),
        "final_atom_state": record.get("final_atom_state"),
        "default_off_retained": bool(record.get("default_off_retained")),
        "evidence_class": record.get("evidence_class"),
        "safety_benefit_evidence": bool(record.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(record.get("atom_promotion_authorized")),
        "future_work_boundary": list(record.get("future_work_boundary") or []),
    }


def _review_summary(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_class": "confirmed_nonpromotion_closeout_complete",
        "chain_closed": True,
        "closed_atom_state": source["final_atom_state"],
        "next_gate_must_be_plan_only": True,
        "replay_authorized": False,
        "training_authorized": False,
        "promotion_authorized": False,
        "dp_modification_authorized": False,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "record_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("record_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("record_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "record_heads_present",
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
        _check_equal("source_status", source["status"], RECORD_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_review_only",
            source["authorized_next_work"],
            RECORD_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_record_ready", source["record_ready"], True),
        _check_equal("source_recorded", source["recorded"], True),
        _check_equal("source_review_authorized", source["review_authorized"], True),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal(
            "source_record_decision_nonpromotion",
            source["record_decision"],
            "close_candidate_set_consensus_safety_score_shadow_atom_without_promotion",
        ),
        _check_equal(
            "source_final_atom_state_default_off",
            source["final_atom_state"],
            "shadow_only_default_off_not_promoted",
        ),
        _check_equal("source_default_off_retained", source["default_off_retained"], True),
        _check_equal(
            "source_evidence_class_nonpromotion",
            source["evidence_class"],
            "real_mixed_nonpromotion_not_safety_benefit_proof",
        ),
        _check_equal("source_no_safety_benefit", source["safety_benefit_evidence"], False),
        _check_equal("source_no_atom_promotion", source["atom_promotion_authorized"], False),
        _check_equal("source_future_boundary_present", bool(source["future_work_boundary"]), True),
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "review_class_confirmed",
            review["review_class"],
            "confirmed_nonpromotion_closeout_complete",
        ),
        _check_equal("review_chain_closed", review["chain_closed"], True),
        _check_equal("review_next_gate_plan_only", review["next_gate_must_be_plan_only"], True),
        _check_equal("review_no_replay", review["replay_authorized"], False),
        _check_equal("review_no_training", review["training_authorized"], False),
        _check_equal("review_no_promotion", review["promotion_authorized"], False),
        _check_equal("review_no_dp_modification", review["dp_modification_authorized"], False),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(source["future_work_boundary"]).lower()
    return [
        _check_equal("boundary_mentions_default_off", "default-off" in text or "default_off" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text or "training" in text, True),
        _check_equal("boundary_blocks_online", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_replay", "replay" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp modification" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "nonpromotion_closeout_review_ready": passed,
        "nonpromotion_closeout_complete": passed,
        "post_nonpromotion_next_gate_plan_authorized": passed,
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
