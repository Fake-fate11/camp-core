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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_post_nonpromotion_next_gate import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_candidate_availability_diversity_synthesis_plan_ready"
REJECT_STATUS = "candidate_set_consensus_candidate_availability_diversity_synthesis_plan_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_candidate_generation_support_redesign_plan_only"

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_POST_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_post_nonpromotion_"
    "next_gate_plan_b6f46bd"
)
DEFAULT_EVIDENCE_PATHS = {
    "support_bottleneck": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/support_bottleneck_synthesis_0fe5a24/"
        "support_bottleneck_synthesis.json"
    ),
    "next_design_preflight": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/next_design_gate_preflight_1020942/"
        "next_design_gate_preflight.json"
    ),
    "mode_seeking_gate": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/mode_seeking_candidate_gate_a2ec874/"
        "mode_seeking_candidate_gate.json"
    ),
    "old_guidance_availability": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/mode_seeking_candidate_availability_smoke_c3c1b97/"
        "mode_seeking_candidate_availability.json"
    ),
    "dense_guidance_availability": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/mode_seeking_candidate0_dense_lanechange_seed3_steps1_91de92a/"
        "availability_diagnostic/mode_seeking_candidate_availability.json"
    ),
    "dense_guidance_failure_source": (
        f"{DEFAULT_DEVELOPMENT_ROOT}/mode_seeking_candidate0_dense_lanechange_seed3_steps1_91de92a/"
        "failure_source_diagnostic_bd15e9a/mode_seeking_failure_source.json"
    ),
}

POST_PLAN_JSON = "candidate_set_consensus_post_nonpromotion_next_gate_plan.json"
POST_PLAN_MD = "candidate_set_consensus_post_nonpromotion_next_gate_plan.md"
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
            "Plan-only synthesis of existing candidate availability/diversity "
            "evidence after candidate-set consensus safety-score non-promotion "
            "closeout. It selects the next support-redesign planning gate."
        )
    )
    parser.add_argument("--post_plan_root", type=Path, default=Path(DEFAULT_POST_PLAN_ROOT))
    parser.add_argument(
        "--evidence_json",
        action="append",
        default=[],
        help="Evidence mapping as name=/path/to/artifact.json",
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
        post_plan_root=args.post_plan_root,
        evidence_paths=_evidence_paths(args.evidence_json),
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
    post_plan_root: Path,
    evidence_paths: dict[str, Path],
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(post_plan_root)
    source = _source_summary(artifact.get("json_payload") or {})
    evidence = _evidence_summary(evidence_paths)
    synthesis = _synthesis_plan(source, evidence)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_evidence_checks(evidence),
        *_synthesis_checks(synthesis),
        *_boundary_checks(synthesis),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_availability_diversity_synthesis_plan_v1",
            "label": label,
            "role": (
                "plan-only synthesis of existing candidate availability and "
                "diversity evidence before any new support redesign work"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This synthesis plan reads only existing fixed-artifact "
                "candidate availability/diversity diagnostics and the "
                "post-nonpromotion next-gate artifact. It does not generate "
                "new DP candidates, recompute outcomes, define an online atom, "
                "alter score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, run replay, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "post_plan_artifact": _strip_payload(artifact),
        "source_summary": source,
        "evidence_summary": evidence,
        "synthesis_plan": synthesis,
        "synthesis_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    synthesis = report["synthesis_plan"]
    lines = [
        "# Candidate-Set Consensus Availability/Diversity Synthesis Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{synthesis['selected_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Evidence Inputs",
        "",
    ]
    for name, item in sorted(report["evidence_summary"].items()):
        lines.append(f"- `{name}`: status `{item['status']}`, present `{item['present']}`")
    lines.extend(["", "## Synthesis", ""])
    for item in synthesis["conclusions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Gate Requirements", ""])
    for item in synthesis["required_next_gate_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in synthesis["blocked_boundaries"]:
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
    for check in report["synthesis_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _evidence_paths(items: list[str]) -> dict[str, Path]:
    paths = {name: Path(value) for name, value in DEFAULT_EVIDENCE_PATHS.items()}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"bad --evidence_json mapping: {item}")
        name, value = item.split("=", 1)
        paths[name] = Path(value)
    return paths


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (POST_PLAN_JSON, POST_PLAN_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[POST_PLAN_JSON].is_file():
        loaded = _load_json(files[POST_PLAN_JSON])
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
    plan = _dict(payload.get("next_gate_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "post_plan_ready": bool(decision.get("post_nonpromotion_next_gate_plan_ready")),
        "synthesis_plan_authorized": bool(
            decision.get("candidate_availability_diversity_synthesis_plan_authorized")
        ),
        "selected_next_work": decision.get("selected_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "broader_replay_consideration_status": plan.get("broader_replay_consideration_status"),
        "safety_score_atom_branch_status": plan.get("safety_score_atom_branch_status"),
    }


def _evidence_summary(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    summary = {}
    for name, path in paths.items():
        payload = {}
        if path.is_file():
            loaded = _load_json(path)
            payload = loaded if isinstance(loaded, dict) else {}
        decision = _dict(payload.get("final_decision"))
        summary[name] = {
            "path": str(path),
            "present": path.is_file(),
            "status": decision.get("status"),
            "final_decision": decision,
        }
    return summary


def _synthesis_plan(
    source: dict[str, Any], evidence: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "fresh_plan_only_gate",
        "conclusions": [
            "candidate-set consensus safety-score atom branch is closed as non-promotion evidence",
            "current descriptor thresholding/reweighting and simple K/noise candidate-generation variants were previously rejected",
            "mode-seeking candidate generation remains only a conditional design direction",
            "old route/lane guidance and candidate0-preserving dense lane-change guidance are rejected as support or latency failures",
            "failure-source evidence points to candidate-generation support and latency, not CAMP selector retraining",
        ],
        "required_next_gate_checks": [
            "predeclare a materially different support-redesign hypothesis before any execution",
            "preserve candidate0 and fixed DP weights by contract",
            "predeclare endpoint/mode diversity, tracker support, and latency gates",
            "reject if the design repeats the route/lane guidance support or latency failure",
            "record artifact paths, HEADS, SHA256SUMS, and no-formal-seed boundary",
        ],
        "blocked_boundaries": [
            "the next gate remains plan-only until a separate reviewed artifact authorizes execution",
            "no replay is authorized by this synthesis plan",
            "no candidate generation execution is authorized by this synthesis plan",
            "no CAMP retraining is authorized",
            "no atom promotion or online selector change is authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or DP Top-1 superiority claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "selected_next_work": source["selected_next_work"],
        },
        "evidence_contract": {name: item["status"] for name, item in evidence.items()},
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "post_plan_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("post_plan_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("post_plan_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal("post_plan_heads_present", bool(str(artifact.get("heads_text") or "").strip()), True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal("source_authorizes_synthesis", source["authorized_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_post_plan_ready", source["post_plan_ready"], True),
        _check_equal("source_synthesis_plan_authorized", source["synthesis_plan_authorized"], True),
        _check_equal("source_selected_next_work", source["selected_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal(
            "source_does_not_reopen_broader_replay",
            source["broader_replay_consideration_status"],
            "already_completed_not_reopened",
        ),
        _check_equal(
            "source_does_not_reopen_safety_score_branch",
            source["safety_score_atom_branch_status"],
            "closed_nonpromotion_not_reopened",
        ),
    ]


def _evidence_checks(evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    expected_status = {
        "support_bottleneck": "current_fixed_dp_selector_calibration_exhausted",
        "next_design_preflight": "next_design_preflight_has_conditional_paths",
        "mode_seeking_gate": "mode_seeking_candidate_design_gate_ready",
        "old_guidance_availability": "mode_seeking_candidate_availability_rejected",
        "dense_guidance_availability": "mode_seeking_candidate_availability_rejected",
        "dense_guidance_failure_source": "mode_seeking_failure_source_candidate_support_insufficient",
    }
    checks = []
    for name, status in expected_status.items():
        item = evidence.get(name, {"present": False, "status": None})
        checks.append(_check_equal(f"evidence_{name}_present", item["present"], True))
        checks.append(_check_equal(f"evidence_{name}_status", item["status"], status))
    preflight = _decision(evidence, "next_design_preflight")
    checks.append(
        _check_equal(
            "evidence_preflight_has_mode_seeking_path",
            "new_mode_seeking_candidate_generation"
            in list(preflight.get("conditional_paths") or []),
            True,
        )
    )
    old_avail = _decision(evidence, "old_guidance_availability")
    dense_avail = _decision(evidence, "dense_guidance_availability")
    failure = _decision(evidence, "dense_guidance_failure_source")
    checks.extend(
        [
            _check_equal("old_guidance_candidate0_not_preserved", _gate(old_avail, "candidate0_preserved"), False),
            _check_equal("dense_guidance_candidate0_preserved", _gate(dense_avail, "candidate0_preserved"), True),
            _check_equal("dense_guidance_latency_failed", _gate(dense_avail, "latency_p95_pass"), False),
            _check_equal("failure_source_not_reward_gate_only", bool(failure.get("reward_gate_suspect")), False),
            _check_equal("failure_source_support_insufficient", bool(failure.get("geometry_or_tracker_support_insufficient")), True),
            _check_equal("failure_source_latency_blocked", bool(failure.get("latency_blocked")), True),
        ]
    )
    return checks


def _synthesis_checks(synthesis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("synthesis_selected_next_work", synthesis["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("synthesis_selection_type", synthesis["selection_type"], "fresh_plan_only_gate"),
        _check_equal("synthesis_has_conclusions", bool(synthesis["conclusions"]), True),
        _check_equal("synthesis_has_next_gate_checks", bool(synthesis["required_next_gate_checks"]), True),
        _check_equal("synthesis_has_blocked_boundaries", bool(synthesis["blocked_boundaries"]), True),
    ]


def _boundary_checks(synthesis: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        synthesis["conclusions"]
        + synthesis["required_next_gate_checks"]
        + synthesis["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text or "plan only" in text, True),
        _check_equal("boundary_blocks_replay", "no replay" in text, True),
        _check_equal("boundary_blocks_candidate_generation_execution", "no candidate generation execution" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp weights" in text and "fixed" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "candidate_availability_diversity_synthesis_plan_ready": passed,
        "candidate_generation_support_redesign_plan_authorized": passed,
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


def _decision(evidence: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    return _dict(evidence.get(name, {}).get("final_decision"))


def _gate(decision: dict[str, Any], name: str) -> Any:
    return _dict(decision.get("gates")).get(name)


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
