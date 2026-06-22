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

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as AUTHORIZATION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as AUTHORIZATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_AUTHORIZATION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_nonpromotion_closeout_authorization_af8c6d0"
)

AUTHORIZATION_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization.json"
)
AUTHORIZATION_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization.md"
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
            "Record-only closeout for the candidate-set consensus safety-score "
            "shadow atom. It writes the final non-promotion documentation "
            "record and does not run replay, train, promote, or modify DP."
        )
    )
    parser.add_argument(
        "--authorization_root",
        type=Path,
        default=Path(DEFAULT_AUTHORIZATION_ROOT),
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
        authorization_root=args.authorization_root,
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
    authorization_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(authorization_root)
    source = _source_summary(artifact.get("json_payload") or {})
    record = _closeout_record(source, authorization_root)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_record_checks(record),
        *_boundary_checks(record),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_record_v1"
            ),
            "label": label,
            "role": (
                "record-only documentation closeout for a non-promoted "
                "default-off shadow atom"
            ),
            "record_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This record reads only the closeout-authorization artifact "
                "and fixed-head audit. It does not recompute outcomes, define "
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
        "authorization_artifact": _strip_payload(artifact),
        "source_summary": source,
        "closeout_record": record,
        "record_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    record = report["closeout_record"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Non-Promotion Closeout Record",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout recorded: `{decision['nonpromotion_closeout_recorded']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Authorization status: `{source['status']}`",
        f"- Record authorized: `{source['record_authorized']}`",
        f"- Record already written in source: `{source['recorded_in_source']}`",
        "",
        "## Final Record",
        "",
        f"- Record decision: `{record['record_decision']}`",
        f"- Final atom state: `{record['final_atom_state']}`",
        f"- Default-off retained: `{record['default_off_retained']}`",
        f"- Evidence class: `{record['evidence_class']}`",
        "",
        "## Promotion Blockers",
        "",
    ]
    for item in record["promotion_blockers"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Future Boundary", ""])
    for item in record["future_work_boundary"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This record does not authorize safety benefit claims, atom "
            "promotion, CAMP retraining, online selector changes, formal "
            "seeds, Full36, replay, new label attachment, or DP modification.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["record_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        AUTHORIZATION_JSON,
        AUTHORIZATION_MD,
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
    if files[AUTHORIZATION_JSON].is_file():
        loaded = _load_json(files[AUTHORIZATION_JSON])
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
    plan = _dict(payload.get("plan_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "authorization_ready": bool(
            decision.get("nonpromotion_closeout_authorization_ready")
        ),
        "record_authorized": bool(
            decision.get("nonpromotion_closeout_record_authorized")
        ),
        "recorded_in_source": bool(decision.get("nonpromotion_closeout_recorded")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "default_off_retained": bool(plan.get("default_off_retained")),
        "closeout_decision": plan.get("closeout_decision"),
        "promotion_blockers": list(plan.get("promotion_blockers") or []),
        "required_closeout_records": list(plan.get("required_closeout_records") or []),
    }


def _closeout_record(source: dict[str, Any], authorization_root: Path) -> dict[str, Any]:
    return {
        "authorization_root": str(authorization_root),
        "record_decision": (
            "close_candidate_set_consensus_safety_score_shadow_atom_"
            "without_promotion"
        ),
        "final_atom_state": "shadow_only_default_off_not_promoted",
        "default_off_retained": True,
        "evidence_class": "real_mixed_nonpromotion_not_safety_benefit_proof",
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "record_scope": (
            "documentation-only closeout of the safety-score shadow atom "
            "evidence chain"
        ),
        "promotion_blockers": [
            *source["promotion_blockers"],
            "authorization explicitly left nonpromotion_closeout_recorded false before this record",
        ],
        "future_work_boundary": [
            "this chain is closed as non-promotion evidence",
            "candidate-set consensus safety-score atom remains shadow-only/default-off",
            "no CAMP retraining, online selector promotion, Full36, formal seeds, replay, new label attachment, or DP modification is authorized",
            "any future work must start from a fresh plan-only gate with current-state audit",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "authorization_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("authorization_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("authorization_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "authorization_heads_present",
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
        _check_equal("source_status", source["status"], AUTHORIZATION_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_record_only",
            source["authorized_next_work"],
            AUTHORIZATION_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_authorization_ready", source["authorization_ready"], True),
        _check_equal("source_record_authorized", source["record_authorized"], True),
        _check_equal("source_record_not_already_written", source["recorded_in_source"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_default_off_retained", source["default_off_retained"], True),
        _check_equal(
            "source_closeout_decision_nonpromotion",
            source["closeout_decision"],
            "do_not_promote_shadow_atom_keep_default_off",
        ),
        _check_equal("source_has_promotion_blockers", bool(source["promotion_blockers"]), True),
        _check_equal(
            "source_has_required_closeout_records",
            bool(source["required_closeout_records"]),
            True,
        ),
    ]


def _record_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "record_decision_nonpromotion",
            record["record_decision"],
            "close_candidate_set_consensus_safety_score_shadow_atom_without_promotion",
        ),
        _check_equal(
            "record_final_atom_state",
            record["final_atom_state"],
            "shadow_only_default_off_not_promoted",
        ),
        _check_equal("record_default_off_retained", record["default_off_retained"], True),
        _check_equal("record_no_safety_benefit", record["safety_benefit_evidence"], False),
        _check_equal("record_no_atom_promotion", record["atom_promotion_authorized"], False),
        _check_equal("record_has_future_boundary", bool(record["future_work_boundary"]), True),
    ]


def _boundary_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(record["promotion_blockers"] + record["future_work_boundary"]).lower()
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
        "nonpromotion_closeout_record_ready": passed,
        "nonpromotion_closeout_recorded": passed,
        "nonpromotion_closeout_review_authorized": passed,
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
