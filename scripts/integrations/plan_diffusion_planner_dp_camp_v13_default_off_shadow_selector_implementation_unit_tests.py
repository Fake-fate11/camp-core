#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_rejected"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"

REQUIRED_REVIEW_CONTRACTS = (
    "default_off_flag_contract",
    "immutable_artifact_hash_contract",
    "fixed_candidate_tensor_contract",
    "affine_benders_atom_score_contract",
    "dp_top1_runtime_output_contract",
    "fail_closed_observability_contract",
    "no_promotion_no_claims_contract",
)

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
            "Plan-only unit-test gate for a future v13 default-off DP-CAMP "
            "shadow selector implementation. It reads the implementation "
            "static-contract review and source surfaces; it does not write "
            "unit tests, implement selector wiring, train, replay, generate "
            "candidates, modify DP, promote, deploy, or authorize claims."
        )
    )
    parser.add_argument("--static_contract_review_json", type=Path, required=True)
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
        "--enable_v13_default_off_shadow_selector_implementation_unit_tests_plan",
        action="store_true",
        help="Explicit opt-in for this plan-only unit-test planning gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        static_contract_review_json=args.static_contract_review_json,
        camp_integration_py=args.camp_integration_py,
        replay_runner_py=args.replay_runner_py,
        benders_contract_test_py=args.benders_contract_test_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v13_default_off_shadow_selector_implementation_unit_tests_plan,
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
    static_contract_review_json: Path,
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
        "static_contract_review": static_contract_review_json,
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
    source_review: dict[str, Any] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if name == "static_contract_review" and path.is_file():
            loaded = _load_json(path)
            source_review = loaded if isinstance(loaded, dict) else {}
            checks.append(
                _check(
                    "static_contract_review_json_object",
                    isinstance(loaded, dict),
                    type(loaded).__name__,
                    "dict",
                )
            )
        elif path.is_file():
            texts[name] = path.read_text(encoding="utf-8")

    checks.extend(_source_review_checks(source_review))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(source_review)
    report["unit_tests_plan"] = _unit_tests_plan()
    report["acceptance_criteria"] = _acceptance_criteria()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("unit_tests_plan", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Implementation Unit Tests Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Unit tests only authorized next: `{decision['default_off_shadow_selector_implementation_unit_tests_only_authorized']}`",
        f"- Implementation authorized: `{decision['default_off_shadow_selector_implementation_authorized']}`",
        f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
        "",
        "## Planned Test Groups",
        "",
    ]
    for group in plan.get("test_groups", []):
        lines.append(f"- `{group['name']}`")
        lines.append(f"  - purpose: {group['purpose']}")
        lines.append(f"  - required assertions: `{group['required_assertions']}`")
    lines.extend(["", "## Acceptance Criteria", ""])
    for item in report.get("acceptance_criteria", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not write unit tests, edit "
            "production selector wiring, train CAMP, run replay, generate "
            "candidates, modify DP, promote atoms or selectors, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
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
            "name": "dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "plan_only": True,
            "unit_test_code_edit": False,
            "implementation_execution": False,
            "read_only_existing_artifacts_and_source_surfaces": True,
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "The future unit tests may only pin contracts around a "
                "default-off shadow selector that reranks fixed current-tick "
                "DP candidates with score_k(w)=a_k^T w; they do not authorize "
                "runtime selector changes, training, replay, candidate "
                "generation, or DP modification."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "unit_tests_plan": {},
        "acceptance_criteria": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "default_off_shadow_selector_implementation_unit_tests_plan_ready": False,
            "default_off_shadow_selector_implementation_unit_tests_only_authorized": False,
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


def _source_review_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    requirements = _list(payload.get("unit_tests_plan_requirements"))
    forbidden = _list(payload.get("forbidden_paths"))
    contracts = _list(review.get("contracts"))
    return [
        _expect("source_review_status_ready", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_review_passed", decision.get("passed"), True),
        _expect("source_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "source_review_authorizes_this_plan",
            decision.get("authorized_next_work"),
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "source_unit_tests_plan_authorized",
            decision.get("default_off_shadow_selector_implementation_unit_tests_plan_authorized"),
            True,
        ),
        _expect(
            "source_implementation_not_authorized",
            decision.get("default_off_shadow_selector_implementation_authorized"),
            False,
        ),
        _expect("source_review_status_no_implementation", review.get("status"), "review_ready_no_implementation"),
        _expect("source_review_candidate_count", review.get("candidate_count"), 8),
        _expect("source_review_score_expression", review.get("score_expression"), SCORE_EXPRESSION),
        _expect(
            "source_review_candidate_operation",
            review.get("candidate_operation"),
            "fixed DP candidate reranking only",
        ),
        *[
            _contains_item(f"source_contract_{name}", contracts, name)
            for name in REQUIRED_REVIEW_CONTRACTS
        ],
        _contains_item("source_requirement_default_off", requirements, "unit tests must prove default-off behavior before reading missing artifacts"),
        _contains_item("source_requirement_dp_top1_shadow", requirements, "unit tests must prove shadow selection does not change executed DP top1 trajectory"),
        _contains_item("source_requirement_fail_closed", requirements, "unit tests must prove K drift, artifact hash mismatch, and nonfinite scores fail closed"),
        _contains_item("source_requirement_no_mutation", requirements, "unit tests must prove no candidate generation, mutation, blend, guidance, or postselection path is introduced"),
        _contains_item("source_requirement_affine", requirements, "unit tests must prove score_k(w)=a_k^T w remains affine in simplex weights"),
        _contains_item("source_requirement_formal_seed_absent", requirements, "unit tests must prove formal seeds 11, 12, and 13 are rejected or absent"),
        _contains_item("source_forbids_actual_implementation", forbidden, "actual implementation code edits"),
        _contains_item("source_forbids_dp_modification", forbidden, "DP code, weight, config, or invocation modification"),
        *[
            _expect(f"source_review_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    integration = texts.get("camp_integration_py", "")
    runner = texts.get("replay_runner_py", "")
    benders = texts.get("benders_contract_test_py", "")
    audit = texts.get("v13_audit_md", "")
    return [
        _contains("integration_has_camp_selector", integration, "class CAMPSelector"),
        _contains("integration_scores_are_affine_matrix_product", integration, "scores = normalized @ weights"),
        _contains("integration_selects_argmin_selection_scores", integration, "selected_index = int(np.argmin(selection_scores))"),
        _contains("runner_has_selector_mode", runner, "--camp_selector_mode"),
        _contains("runner_has_top1_fail_closed_mode", runner, "\"top1\""),
        _contains("runner_has_finite_candidate_contract", runner, "_dp_camp_finite_candidate_contract"),
        _contains("benders_test_pins_affine_scores", benders, "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights"),
        _contains("benders_test_rejects_negative_atoms", benders, "test_robust_margin_master_rejects_negative_atom_coefficients"),
        _contains(
            "audit_authorizes_current_unit_tests_plan_only",
            audit,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
        ),
        _contains("audit_blocks_online_selector_change", audit, "online_selector_change_authorized=False"),
        _contains(
            "audit_blocks_implementation",
            audit,
            "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
        ),
    ]


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "unit_tests_plan_authorized": bool(
            decision.get("default_off_shadow_selector_implementation_unit_tests_plan_authorized")
        ),
        "implementation_authorized": bool(
            decision.get("default_off_shadow_selector_implementation_authorized")
        ),
        "candidate_operation": review.get("candidate_operation"),
        "score_expression": review.get("score_expression"),
        "contracts": _list(review.get("contracts")),
    }


def _unit_tests_plan() -> dict[str, Any]:
    return {
        "status": "plan_ready_no_unit_test_code",
        "target_test_file": (
            "camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_"
            "shadow_selector_implementation_unit_tests.py"
        ),
        "test_groups": [
            {
                "name": "default_off_disabled_contract",
                "purpose": "prove disabled mode returns before reading missing artifacts",
                "required_assertions": [
                    "missing_weights_no_error_when_disabled",
                    "executed_output_is_dp_top1",
                ],
            },
            {
                "name": "immutable_artifact_hash_contract",
                "purpose": "prove weights, scales, and manifest hashes are checked before scoring",
                "required_assertions": [
                    "hash_mismatch_fails_closed",
                    "missing_artifact_logs_no_shadow_selection",
                ],
            },
            {
                "name": "fixed_candidate_affine_score_contract",
                "purpose": "prove scoring is normalized_atoms @ weights over K=8 fixed rows",
                "required_assertions": [
                    "score_expression_affine",
                    "k_drift_fails_closed",
                    "nonfinite_score_fails_closed",
                ],
            },
            {
                "name": "dp_top1_shadow_runtime_contract",
                "purpose": "prove shadow argmin is logged but not routed to executed trajectory",
                "required_assertions": [
                    "shadow_index_recorded",
                    "executed_trajectory_remains_dp_top1",
                ],
            },
            {
                "name": "no_candidate_mutation_contract",
                "purpose": "prove no candidate row is generated, modified, blended, or postprocessed",
                "required_assertions": [
                    "candidate_tensor_hash_unchanged",
                    "no_reference_blend_or_guidance_flag",
                ],
            },
            {
                "name": "benders_and_seed_boundary_contract",
                "purpose": "prove Benders atom and formal-seed boundaries stay pinned",
                "required_assertions": [
                    "score_k_w_equals_a_k_t_w",
                    "formal_seeds_11_12_13_absent",
                ],
            },
        ],
    }


def _acceptance_criteria() -> list[str]:
    return [
        "unit-tests-only gate may add tests but must not edit production selector implementation",
        "tests must be deterministic and avoid formal seeds 11, 12, and 13",
        "tests must fail on any path that routes shadow selection into executed output",
        "tests must fail on any candidate generation, mutation, blend, guidance, or postselection",
        "tests must pin score_k(w)=a_k^T w and fixed K=8 candidate rows",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "production implementation code edits in this plan gate",
        "selector wiring changes or online selector default changes",
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
        "default_off_shadow_selector_implementation_unit_tests_plan_ready": passed,
        "default_off_shadow_selector_implementation_unit_tests_only_authorized": passed,
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
