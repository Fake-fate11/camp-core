#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_rejected"
)
SOURCE_PLAN_STATUS = "dp_camp_v13_default_off_shadow_selector_implementation_plan_ready"
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"

BLOCKED_ACTIONS = (
    "default_off_shadow_selector_implementation_authorized",
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
            "Review-only static contract gate for the v13 default-off "
            "shadow selector implementation plan. It checks that the plan "
            "preserves DP top-1 runtime output, fixed-candidate affine CAMP "
            "reranking, and no-action boundaries. It does not implement "
            "selector wiring, train, replay, generate candidates, modify DP, "
            "promote, deploy, or authorize safety/CAMP-over-DP claims."
        )
    )
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--camp_integration_py", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--benders_contract_test_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_implementation_static_contract_review",
        action="store_true",
        help="Explicit opt-in for this review-only static contract gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        implementation_plan_json=args.implementation_plan_json,
        camp_integration_py=args.camp_integration_py,
        replay_runner_py=args.replay_runner_py,
        benders_contract_test_py=args.benders_contract_test_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_implementation_static_contract_review
        ),
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
    implementation_plan_json: Path,
    camp_integration_py: Path,
    replay_runner_py: Path,
    benders_contract_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    paths = {
        "implementation_plan": implementation_plan_json,
        "camp_integration_py": camp_integration_py,
        "replay_runner_py": replay_runner_py,
        "benders_contract_test_py": benders_contract_test_py,
        "v13_audit_md": v13_audit_md,
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
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    texts: dict[str, str] = {}
    source_plan: dict[str, Any] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if name == "implementation_plan" and path.is_file():
            loaded = _load_json(path)
            source_plan = loaded if isinstance(loaded, dict) else {}
            checks.append(
                _check(
                    "implementation_plan_json_object",
                    isinstance(loaded, dict),
                    type(loaded).__name__,
                    "dict",
                )
            )
        elif path.is_file():
            texts[name] = path.read_text(encoding="utf-8")

    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(source_plan)
    report["static_contract_review"] = _static_contract_review()
    report["unit_tests_plan_requirements"] = _unit_tests_plan_requirements()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report.get("static_contract_review", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized: `{decision['default_off_shadow_selector_implementation_authorized']}`",
        f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        "",
        "## Review",
        "",
        f"- Status: `{review.get('status')}`",
        f"- Runtime effect: `{review.get('runtime_effect')}`",
        f"- Candidate operation: `{review.get('candidate_operation')}`",
        f"- Score expression: `{review.get('score_expression')}`",
        "",
        "## Contracts",
        "",
    ]
    for item in review.get("contracts", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Unit-Test Plan Requirements", ""])
    for item in report.get("unit_tests_plan_requirements", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is review-only. It does not edit production selector "
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
            "name": (
                "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review"
            ),
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "review_only": True,
            "implementation_execution": False,
            "read_only_existing_artifacts_and_source_surfaces": True,
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "CAMP remains a fixed-candidate reranker. Any future shadow "
                "selector must compute score_k(w)=a_k^T w from current-tick "
                "finite candidate atoms only, while the runtime output remains "
                "DP top1 during the default-off shadow phase."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "static_contract_review": {},
        "unit_tests_plan_requirements": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "default_off_shadow_selector_implementation_static_contract_review_ready": False,
            "default_off_shadow_selector_implementation_unit_tests_plan_authorized": False,
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


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    static_review_requirements = _list(payload.get("static_review_requirements"))
    forbidden_paths = _list(payload.get("forbidden_implementation_paths"))
    required_steps = _list(plan.get("required_steps"))
    return [
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "source_plan_authorizes_this_review",
            decision.get("authorized_next_work"),
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "source_static_contract_review_authorized",
            decision.get(
                "default_off_shadow_selector_implementation_static_contract_review_authorized"
            ),
            True,
        ),
        _expect("source_implementation_not_authorized", decision.get("default_off_shadow_selector_implementation_authorized"), False),
        _expect("source_plan_status_no_implementation", plan.get("status"), "plan_ready_no_implementation"),
        _expect("source_plan_candidate_count", plan.get("candidate_count"), 8),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect(
            "source_plan_selection_rule",
            plan.get("selection_rule"),
            "shadow_selected_index = argmin_k score_k(w)",
        ),
        _contains_item("source_plan_default_off_step", required_steps, "add a default-off shadow selector flag or config whose default is false"),
        _contains_item("source_plan_immutable_artifacts_step", required_steps, "load immutable v13 weights, atom scales, and artifact hash manifest only"),
        _contains_item("source_plan_affine_score_step", required_steps, "compute normalized candidate atoms and scores as normalized_atoms @ weights"),
        _contains_item("source_plan_dp_top1_runtime_step", required_steps, "keep executed trajectory and online selector output equal to DP top1 during shadow phase"),
        _contains_item("source_plan_fail_closed_step", required_steps, "fail closed to DP top1 and explicit no-shadow log on any contract violation"),
        _contains_item("source_review_no_shadow_route_requirement", static_review_requirements, "prove no shadow index is routed into executed trajectory output"),
        _contains_item("source_review_no_candidate_mutation_requirement", static_review_requirements, "prove no candidate row is created, appended, deleted, blended, or rewritten"),
        _contains_item("source_review_affine_score_requirement", static_review_requirements, "prove scoring remains score_k(w)=a_k^T w over fixed current-tick candidate atoms"),
        _contains_item("source_forbids_dp_modification", forbidden_paths, "modifying, retraining, or tuning TiERIV Diffusion Planner"),
        _contains_item("source_forbids_claims", forbidden_paths, "claiming selector promotion, deployment readiness, safety benefit, or CAMP superiority"),
        *[
            _expect(f"source_plan_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    integration = texts.get("camp_integration_py", "")
    runner = texts.get("replay_runner_py", "")
    benders = texts.get("benders_contract_test_py", "")
    audit = texts.get("v13_audit_md", "")
    current_boundary = _current_v13_boundary(audit)
    return [
        _contains("integration_has_camp_selector", integration, "class CAMPSelector"),
        _contains("integration_scores_are_affine_matrix_product", integration, "scores = normalized @ weights"),
        _contains("integration_selects_argmin_selection_scores", integration, "selected_index = int(np.argmin(selection_scores))"),
        _contains("integration_returns_candidate_copy_only", integration, "selected_trajectory=candidates[selected_index].copy()"),
        _contains("runner_has_selector_mode", runner, "--camp_selector_mode"),
        _contains("runner_has_top1_fail_closed_mode", runner, "\"top1\""),
        _contains("runner_has_paper_boundary_error", runner, "PAPER_FAITHFUL_BOUNDARY_ERROR"),
        _contains("runner_has_finite_candidate_contract", runner, "_dp_camp_finite_candidate_contract"),
        _contains("benders_test_pins_affine_scores", benders, "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights"),
        _contains("benders_test_rejects_negative_atoms", benders, "test_robust_margin_master_rejects_negative_atom_coefficients"),
        _contains(
            "audit_authorizes_current_review_only",
            current_boundary,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
        ),
        _contains("audit_blocks_online_selector_change", current_boundary, "online_selector_change_authorized=False"),
        _contains_any(
            "audit_blocks_implementation",
            current_boundary,
            (
                "default_off_shadow_selector_implementation_authorized=False",
                "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
            ),
        ),
    ]


def _current_v13_boundary(audit: str) -> str:
    marker = "\n## Current V13 "
    index = audit.rfind(marker)
    return audit[index + 1 :] if index >= 0 else audit


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": bool(
            decision.get(
                "default_off_shadow_selector_implementation_static_contract_review_authorized"
            )
        ),
        "implementation_authorized": bool(
            decision.get("default_off_shadow_selector_implementation_authorized")
        ),
        "runtime_effect": plan.get("runtime_effect"),
        "candidate_count": plan.get("candidate_count"),
        "score_expression": plan.get("score_expression"),
        "selection_rule": plan.get("selection_rule"),
    }


def _static_contract_review() -> dict[str, Any]:
    return {
        "status": "review_ready_no_implementation",
        "runtime_effect": "executed output remains DP top1 during shadow phase",
        "candidate_operation": "fixed DP candidate reranking only",
        "candidate_count": 8,
        "score_expression": SCORE_EXPRESSION,
        "selection_rule": "shadow_selected_index = argmin_k score_k(w)",
        "contracts": [
            "default_off_flag_contract",
            "immutable_artifact_hash_contract",
            "fixed_candidate_tensor_contract",
            "affine_benders_atom_score_contract",
            "dp_top1_runtime_output_contract",
            "fail_closed_observability_contract",
            "no_promotion_no_claims_contract",
        ],
    }


def _unit_tests_plan_requirements() -> list[str]:
    return [
        "unit tests must prove default-off behavior before reading missing artifacts",
        "unit tests must prove shadow selection does not change executed DP top1 trajectory",
        "unit tests must prove K drift, artifact hash mismatch, and nonfinite scores fail closed",
        "unit tests must prove no candidate generation, mutation, blend, guidance, or postselection path is introduced",
        "unit tests must prove score_k(w)=a_k^T w remains affine in simplex weights",
        "unit tests must prove formal seeds 11, 12, and 13 are rejected or absent",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "actual implementation code edits",
        "routing shadow_selected_index into executed trajectory",
        "training, replay execution, or candidate generation",
        "DP code, weight, config, or invocation modification",
        "selector or atom promotion",
        "deployable checkpoint, safety benefit, or CAMP-over-DP Top-1 claim",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "default_off_shadow_selector_implementation_static_contract_review_ready": passed,
        "default_off_shadow_selector_implementation_unit_tests_plan_authorized": passed,
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


def _contains_any(name: str, text: str, needles: tuple[str, ...]) -> dict[str, Any]:
    matched = next((needle for needle in needles if needle in text), None)
    return _check(name, matched is not None, matched if matched else "missing", needles)


def _contains_item(name: str, items: list[Any], expected: str) -> dict[str, Any]:
    return _check(name, expected in items, items, expected)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
