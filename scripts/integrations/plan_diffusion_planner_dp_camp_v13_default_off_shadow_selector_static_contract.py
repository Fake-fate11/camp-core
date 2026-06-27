#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_static_contract_plan_v1"
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_static_contract_plan_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_default_off_shadow_selector_static_contract_plan_ready"
REJECT_STATUS = "dp_camp_v13_default_off_shadow_selector_static_contract_plan_rejected"
SOURCE_PREFLIGHT_STATUS = "dp_camp_v13_promotion_evidence_package_preflight_ready"
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only"
)
AUTHORIZED_NEXT_WORK = "dp_camp_v13_default_off_shadow_selector_implementation_plan_only"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"

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
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only static integration contract for a future default-off "
            "shadow selector using the v13 static CAMP reranker. It reads the "
            "evidence-package preflight and source surfaces; it does not "
            "implement, promote, deploy, train, replay, generate candidates, "
            "or modify DP."
        )
    )
    parser.add_argument("--evidence_package_preflight_json", type=Path, required=True)
    parser.add_argument("--camp_integration_py", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--benders_contract_test_py", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_static_contract_plan",
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
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v13_default_off_shadow_selector_static_contract_plan,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_report(
    *,
    evidence_package_preflight_json: Path,
    camp_integration_py: Path,
    replay_runner_py: Path,
    benders_contract_test_py: Path,
    current_camp_head: str,
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
    report = _empty_report(
        enabled=enabled,
        label=label,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    texts: dict[str, str] = {}
    payload: dict[str, Any] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if name == "evidence_package_preflight" and path.is_file():
            loaded = _load_json(path)
            payload = loaded if isinstance(loaded, dict) else {}
            checks.append(
                _check(
                    "evidence_package_preflight_json_object",
                    isinstance(loaded, dict),
                    type(loaded).__name__,
                    "dict",
                )
            )
        elif path.is_file():
            texts[name] = path.read_text(encoding="utf-8")

    checks.extend(_source_preflight_checks(payload))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(payload)
    report["integration_surface_inventory"] = _integration_surface_inventory(texts)
    report["static_contract_plan"] = _static_contract_plan()
    report["implementation_plan_requirements"] = _implementation_plan_requirements()
    report["forbidden_implementation_paths"] = _forbidden_implementation_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report.get("static_contract_plan", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Static Contract Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized: `{decision['default_off_shadow_selector_implementation_authorized']}`",
        f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        "",
        "## Static Contract",
        "",
        f"- Selector phase: `{contract.get('selector_phase')}`",
        f"- Runtime effect: `{contract.get('runtime_effect')}`",
        f"- Candidate source: `{contract.get('candidate_source')}`",
        f"- Score expression: `{contract.get('score_expression')}`",
        f"- Fallback policy: `{contract.get('fail_closed_policy')}`",
        "",
        "## Required Implementation Plan Items",
        "",
    ]
    for item in report.get("implementation_plan_requirements", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_implementation_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not edit production selector "
            "wiring, train CAMP, run replay, generate candidates, modify DP, "
            "promote atoms or selectors, deploy, or authorize safety/CAMP-over-DP "
            "claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report.get("plan_checks", []):
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "name": "dp_camp_v13_default_off_shadow_selector_static_contract_plan",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "plan_only": True,
            "read_only_existing_artifacts_and_source_surfaces": True,
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "A future shadow selector may only compute finite current-tick "
                "candidate features and affine scores score_k(w)=a_k^T w over "
                "the fixed DP candidate set. The simplex/CVaR/L2 training "
                "master remains convex; no DP-side classical Benders claim is made."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "integration_surface_inventory": {},
        "static_contract_plan": {},
        "implementation_plan_requirements": [],
        "forbidden_implementation_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "static_contract_plan_ready": False,
            "default_off_shadow_selector_implementation_plan_authorized": False,
            "default_off_shadow_selector_implementation_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
            "failed_checks": [],
        },
    }


def _source_preflight_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    return [
        _expect("source_preflight_status_ready", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "source_preflight_authorizes_this_plan",
            decision.get("authorized_next_work"),
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _expect("source_manifest_count", len(payload.get("artifact_manifest") or []), 10),
        _expect(
            "source_static_contract_pinned",
            decision.get("static_integration_contract_pinned"),
            True,
        ),
        _expect(
            "source_shadow_contract_plan_authorized",
            decision.get("default_off_shadow_selector_contract_plan_authorized"),
            True,
        ),
        *[
            _expect(f"source_preflight_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    integration = texts.get("camp_integration_py", "")
    runner = texts.get("replay_runner_py", "")
    benders = texts.get("benders_contract_test_py", "")
    return [
        _contains("integration_has_camp_selector", integration, "class CAMPSelector"),
        _contains("integration_has_selection_result", integration, "class CAMPSelectionResult"),
        _contains("integration_scores_are_affine_matrix_product", integration, "scores = normalized @ weights"),
        _contains("integration_selects_argmin_selection_scores", integration, "selected_index = int(np.argmin(selection_scores))"),
        _contains("integration_returns_candidate_copy_only", integration, "selected_trajectory=candidates[selected_index].copy()"),
        _contains("integration_loads_structured_atom_scales", integration, "load_dp_camp_atom_scales"),
        _contains("runner_has_paper_faithful_boundary_error", runner, "PAPER_FAITHFUL_BOUNDARY_ERROR"),
        _contains("runner_validates_paper_faithful_boundary", runner, "_validate_paper_faithful_boundary"),
        _contains("runner_exposes_selector_mode", runner, "--camp_selector_mode"),
        _contains("runner_has_finite_candidate_contract", runner, "_dp_camp_finite_candidate_contract"),
        _contains("runner_contract_uses_argmin_language", runner, "argmin over finite feasible candidates"),
        _contains("runner_top1_mode_available_for_fail_closed", runner, "\"top1\""),
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


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "manifest_count": len(payload.get("artifact_manifest") or []),
        "static_contract_status": _path(payload, "static_integration_contract.status"),
        "score_expression": _path(payload, "static_integration_contract.score_expression"),
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
        "runtime_effect": "must_log_shadow_decision_without changing DP top1 output",
        "candidate_source": "fixed current-tick DP candidate tensor before CAMP scoring",
        "candidate_count": 8,
        "score_expression": SCORE_EXPRESSION,
        "selection_rule": "argmin_k score_k(w) over finite candidate rows",
        "weights_contract": "simplex nonnegative static weights from immutable v13 artifact",
        "atom_contract": "current-tick finite candidate features only; nonnegative after normalization",
        "fail_closed_policy": "on any missing artifact, K drift, nonfinite value, or source mismatch, emit DP top1 and log no shadow selection",
        "kill_switch_required": True,
        "formal_seed_usage_authorized": False,
        "postselection_authorized": False,
        "trajectory_mutation_authorized": False,
        "default_off_required": True,
    }


def _implementation_plan_requirements() -> list[str]:
    return [
        "declare a default-off shadow selector flag or config with default false",
        "load only immutable v13 weights, atom scales, and artifact hash manifest",
        "verify DP head, K=8, atom schema, score expression, and artifact hashes before scoring",
        "compute scores as normalized_atoms @ weights and shadow_selected_index as argmin",
        "keep runtime output on DP top1 during shadow phase",
        "fail closed to DP top1 on missing candidates, invalid atoms, nonfinite scores, or artifact mismatch",
        "log candidate tensor hash, scores, selected shadow index, feasible mask, artifact hashes, and timing",
        "exclude postselection, reference blend, guidance, underprogress relaxation, and any trajectory rewrite",
        "add static tests before implementation and runtime tests before any online selector change",
    ]


def _forbidden_implementation_paths() -> list[str]:
    return [
        "changing default camp_selector_mode away from top1",
        "routing shadow_selected_index into the executed trajectory",
        "creating, appending, deleting, blending, or postprocessing candidate rows",
        "using closed-loop outcome labels or future simulator state as online inputs",
        "using formal seeds 11, 12, or 13",
        "claiming deployability, safety benefit, or CAMP superiority from this plan",
        "modifying, retraining, or tuning Diffusion Planner",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_contract_plan_ready": passed,
        "default_off_shadow_selector_implementation_plan_authorized": passed,
        "default_off_shadow_selector_implementation_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "failed_checks": failed,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _path(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _stable(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
