#!/usr/bin/env python3
"""Plan-only v14 default-off shadow selector static integration contract.

This gate reads the v14 promotion evidence-package preflight and current source
surfaces. It plans the static contract for a future default-off shadow selector.
It does not implement selector wiring, promote, deploy, train, replay, generate
candidates, modify DP, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_static_"
    "integration_contract_plan_v1"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_evidence_package_preflight_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_static_"
    "integration_contract_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_static_"
    "integration_contract_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_static_"
    "integration_contract_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "plan_only"
)

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence_package_preflight_json", type=Path, required=True)
    parser.add_argument("--camp_integration_py", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--benders_contract_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_default_off_shadow_selector_static_contract_plan",
        action="store_true",
        help="Explicit opt-in for this plan-only static contract gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evidence_package_preflight_json=args.evidence_package_preflight_json,
        camp_integration_py=args.camp_integration_py,
        replay_runner_py=args.replay_runner_py,
        benders_contract_test_py=args.benders_contract_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_default_off_shadow_selector_static_contract_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evidence_package_preflight_json: Path,
    camp_integration_py: Path,
    replay_runner_py: Path,
    benders_contract_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    paths = {
        "evidence_package_preflight": evidence_package_preflight_json,
        "camp_integration_py": camp_integration_py,
        "replay_runner_py": replay_runner_py,
        "benders_contract_test_py": benders_contract_test_py,
    }
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in paths.items()
        if name != "evidence_package_preflight" and path.is_file()
    }
    preflight = _read_json_dict(evidence_package_preflight_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks = [
        _expect("plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _check("v14_audit_md_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check(
            "current_status_md_exists",
            current_status_md.is_file(),
            str(current_status_md),
            "file",
        ),
    ]
    source_hashes = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file"))
        if path.is_file():
            source_hashes[f"{name}_sha256"] = _sha256(path)
    checks.extend(_source_preflight_checks(preflight))
    checks.extend(_source_surface_checks(texts))
    checks.extend(_audit_eof_checks(v14_text, status_text))
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "default_off": True,
            "read_only_existing_artifacts_and_source_surfaces": True,
            "evidence_package_preflight_json": str(evidence_package_preflight_json.resolve()),
            "camp_integration_py": str(camp_integration_py.resolve()),
            "replay_runner_py": str(replay_runner_py.resolve()),
            "benders_contract_test_py": str(benders_contract_test_py.resolve()),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "implementation_executed": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "math_boundary": (
                "A future default-off shadow selector may only compute finite "
                "current-tick candidate features and affine scores "
                "score_k(w)=a_k^T w over a fixed DP candidate tensor. The "
                "simplex/CVaR/L2 master remains convex; no DP-side classical "
                "Benders claim is made."
            ),
        },
        "source_hashes": source_hashes,
        "source_summary": _source_summary(preflight),
        "integration_surface_inventory": _integration_surface_inventory(texts),
        "static_contract_plan": _static_contract_plan(),
        "implementation_plan_requirements": _implementation_plan_requirements(),
        "forbidden_implementation_paths": _forbidden_implementation_paths(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "default_off_shadow_selector_static_integration_contract_plan.json",
        report,
    )
    (output_dir / "default_off_shadow_selector_static_integration_contract_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["static_contract_plan"]
    lines = [
        "# V14 Default-Off Shadow Selector Static Integration Contract Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation plan authorized: `{decision['default_off_shadow_selector_implementation_plan_authorized']}`",
        f"- Implementation authorized: `{decision['default_off_shadow_selector_implementation_authorized']}`",
        f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        "",
        "## Static Contract",
        "",
        f"- Selector phase: `{contract['selector_phase']}`",
        f"- Runtime effect: `{contract['runtime_effect']}`",
        f"- Candidate source: `{contract['candidate_source']}`",
        f"- Score expression: `{contract['score_expression']}`",
        f"- Selection rule: `{contract['selection_rule']}`",
        f"- Fail-closed policy: `{contract['fail_closed_policy']}`",
        "",
        "## Required Implementation Plan Items",
        "",
    ]
    for item in report["implementation_plan_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report["forbidden_implementation_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not edit production selector wiring, "
            "train CAMP, run replay, generate candidates, modify DP, promote "
            "atoms or selectors, deploy, or authorize safety/CAMP-over-DP claims.",
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
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_preflight_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    contract = _dict(payload.get("static_integration_contract"))
    return [
        _expect("source_preflight_status_ready", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "source_preflight_authorizes_this_plan",
            decision.get("authorized_next_work"),
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _expect("source_manifest_count", len(payload.get("artifact_manifest") or []), 7),
        _expect("source_static_contract_status", contract.get("status"), "preflight_ready_contract_pinned"),
        _expect("source_static_contract_score", contract.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_contract_simplex_convex", contract.get("simplex_master_convex"), True),
        _expect("source_static_contract_cvar_convex", contract.get("cvar_master_convex"), True),
        _expect("source_static_contract_l2_convex", contract.get("l2_master_convex"), True),
        _expect(
            "source_shadow_contract_plan_authorized",
            decision.get("default_off_shadow_selector_contract_plan_authorized"),
            True,
        ),
        *[_expect(f"source_preflight_{name}_false", decision.get(name), False) for name in BLOCKED_ACTIONS],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    integration = texts.get("camp_integration_py", "")
    runner = texts.get("replay_runner_py", "")
    benders = texts.get("benders_contract_test_py", "")
    return [
        _contains("integration_has_camp_selector", integration, "class CAMPSelector"),
        _contains("integration_has_selection_result", integration, "class CAMPSelectionResult"),
        _contains("integration_scores_are_affine_matrix_product", integration, "scores = normalized @ weights"),
        _contains(
            "integration_selects_argmin_selection_scores",
            integration,
            "selected_index = int(np.argmin(selection_scores))",
        ),
        _contains(
            "integration_returns_candidate_copy_only",
            integration,
            "selected_trajectory=candidates[selected_index].copy()",
        ),
        _contains("integration_loads_structured_atom_scales", integration, "load_dp_camp_atom_scales"),
        _contains("runner_has_paper_faithful_boundary_error", runner, "PAPER_FAITHFUL_BOUNDARY_ERROR"),
        _contains("runner_validates_paper_faithful_boundary", runner, "_validate_paper_faithful_boundary"),
        _contains("runner_exposes_selector_mode", runner, "--camp_selector_mode"),
        _contains("runner_has_finite_candidate_contract", runner, "_dp_camp_finite_candidate_contract"),
        _contains("runner_contract_uses_argmin_language", runner, "argmin over finite feasible candidates"),
        _contains("runner_top1_mode_available_for_fail_closed", runner, "\"top1\""),
        _contains("runner_can_log_shadow_without_effect", runner, "\"executed_output_policy\": \"dp_top1\""),
        _contains(
            "benders_test_pins_affine_scores",
            benders,
            "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights",
        ),
        _contains(
            "benders_test_rejects_negative_atoms",
            benders,
            "test_robust_margin_master_rejects_negative_atom_coefficients",
        ),
    ]


def _audit_eof_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    return [
        _check(
            "audit_latest_status",
            f"current_v14_status={SOURCE_PREFLIGHT_STATUS}" in eof,
            _extract_line(eof, "current_v14_status="),
            f"current_v14_status={SOURCE_PREFLIGHT_STATUS}",
        ),
        _check(
            "audit_latest_next_work",
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof,
            _extract_line(eof, "next_work_target="),
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}",
        ),
        _check(
            "current_status_latest_status",
            f"current_v14_status={SOURCE_PREFLIGHT_STATUS}" in status_text,
            "present" if f"current_v14_status={SOURCE_PREFLIGHT_STATUS}" in status_text else "missing",
            "present",
        ),
        _check(
            "current_status_latest_next_work",
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text,
            "present" if f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text else "missing",
            "present",
        ),
    ]


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    source = _dict(payload.get("source_summary"))
    contract = _dict(payload.get("static_integration_contract"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "manifest_count": len(payload.get("artifact_manifest") or []),
        "static_contract_status": contract.get("status"),
        "score_expression": contract.get("score_expression"),
        "records_total": source.get("records_total"),
        "training_records": source.get("training_records"),
        "num_candidates": source.get("num_candidates"),
        "num_atoms": source.get("num_atoms"),
    }


def _integration_surface_inventory(texts: dict[str, str]) -> dict[str, Any]:
    return {
        "camp_selector_surface": {
            "source": "camp_core/camp_core/integrations/diffusion_planner.py",
            "class": "CAMPSelector",
            "result_dataclass": "CAMPSelectionResult",
            "score_expression_in_code": "scores = normalized @ weights",
            "selection_rule_in_code": "selected_index = int(np.argmin(selection_scores))",
        },
        "runner_surface": {
            "source": "scripts/integrations/run_diffusion_planner_camp_replay.py",
            "selector_mode_argument_present": "--camp_selector_mode" in texts.get("replay_runner_py", ""),
            "paper_faithful_boundary_present": "PAPER_FAITHFUL_BOUNDARY_ERROR" in texts.get("replay_runner_py", ""),
            "finite_candidate_contract_present": "_dp_camp_finite_candidate_contract" in texts.get("replay_runner_py", ""),
            "dp_top1_shadow_policy_present": "\"executed_output_policy\": \"dp_top1\"" in texts.get("replay_runner_py", ""),
        },
        "contract_tests": {
            "source": "camp_core/tests/test_diffusion_planner_benders_atom_contract.py",
            "affine_score_test_present": "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights" in texts.get("benders_contract_test_py", ""),
            "negative_atom_rejection_test_present": "test_robust_margin_master_rejects_negative_atom_coefficients" in texts.get("benders_contract_test_py", ""),
        },
    }


def _static_contract_plan() -> dict[str, Any]:
    return {
        "status": "plan_ready_no_implementation",
        "selector_phase": "default_off_shadow_only",
        "runtime_effect": "must_log_shadow_selected_index_without_changing_dp_top1_output",
        "candidate_source": "fixed current-tick DP candidate tensor before CAMP scoring",
        "candidate_count": 8,
        "score_expression": SCORE_EXPRESSION,
        "selection_rule": "argmin_k score_k(w) over finite feasible candidate rows",
        "weights_contract": "nonnegative simplex static weights from immutable v14 artifact",
        "atom_contract": "current-tick finite candidate features only; no closed-loop outcomes",
        "fail_closed_policy": "on missing artifact, K drift, nonfinite value, source mismatch, or unavailable candidates, execute DP top1 and log no shadow selection",
        "kill_switch_required": True,
        "default_off_required": True,
        "formal_seed_usage_authorized": False,
        "postselection_authorized": False,
        "trajectory_mutation_authorized": False,
    }


def _implementation_plan_requirements() -> list[str]:
    return [
        "declare a default-off shadow selector flag or config with default false",
        "load only immutable v14 weights, atom scales, and artifact hash manifest",
        "verify DP head, K=8, atom schema, score expression, and artifact hashes before scoring",
        "compute scores as normalized_atoms @ weights and shadow_selected_index as argmin",
        "keep executed trajectory output on DP Top-1 during shadow phase",
        "fail closed to DP Top-1 on missing candidates, invalid atoms, nonfinite scores, or artifact mismatch",
        "log candidate tensor hash, scores, shadow selected index, feasible mask, artifact hashes, and timing",
        "exclude postselection, reference blend, guidance, underprogress relaxation, and any trajectory rewrite",
        "add static tests before implementation and runtime tests before any online selector change",
    ]


def _forbidden_implementation_paths() -> list[str]:
    return [
        "changing default camp_selector_mode or production selection away from DP Top-1",
        "routing shadow_selected_index into the executed trajectory",
        "creating, appending, deleting, blending, or postprocessing candidate rows",
        "using closed-loop outcome labels or future simulator state as online inputs",
        "using Full36 or formal seeds 11, 12, or 13",
        "claiming deployability, safety benefit, or CAMP superiority from this plan",
        "modifying, retraining, or tuning Diffusion Planner",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_contract_plan_ready": passed,
        "default_off_shadow_selector_implementation_plan_authorized": passed,
        "default_off_shadow_selector_implementation_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "plan_enabled" in failed_set:
        return "explicit_static_contract_plan_authorization_missing"
    if {"audit_latest_status", "audit_latest_next_work"} & failed_set:
        return "v14_eof_contract_mismatch"
    if any(name.startswith("source_preflight") or name.startswith("source_static") for name in failed):
        return "source_preflight_contract_failure"
    if any(name.startswith("integration_") or name.startswith("runner_") or name.startswith("benders_") for name in failed):
        return "source_surface_contract_failure"
    return "default_off_shadow_selector_static_contract_plan_failure"


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _latest_text_block(text: str) -> str:
    marker = "## "
    index = text.rfind(marker)
    return text[index:] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line
    return None


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 96 else text[:93] + "..."


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256sums(output_dir: Path) -> None:
    rows: list[str] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
