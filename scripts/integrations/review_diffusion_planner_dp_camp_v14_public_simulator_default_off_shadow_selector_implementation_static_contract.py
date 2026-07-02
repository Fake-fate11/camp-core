#!/usr/bin/env python3
"""Review-only v14 default-off shadow selector implementation static contract.

This gate reads the v14 implementation plan artifact and current source
surfaces. It statically reviews the implementation contract for a future
default-off shadow selector without editing selector wiring, training,
replaying, generating candidates, modifying DP, promoting, deploying, or
making safety/CAMP-over-DP claims.
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
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "implementation_static_contract_review_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "static_contract_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_"
    "unit_tests_plan_only"
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
    "executed_trajectory_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
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
        "--enable_v14_default_off_shadow_selector_implementation_static_contract_review",
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
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_default_off_shadow_selector_implementation_static_contract_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    implementation_plan_json: Path,
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
        "implementation_plan": implementation_plan_json,
        "camp_integration_py": camp_integration_py,
        "replay_runner_py": replay_runner_py,
        "benders_contract_test_py": benders_contract_test_py,
    }
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in paths.items()
        if name != "implementation_plan" and path.is_file()
    }
    source_plan = _read_json_dict(implementation_plan_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks = [
        _expect("review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect(
            "current_camp_head_matches_origin",
            current_camp_head,
            current_camp_origin_main,
        ),
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
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_source_surface_checks(texts))
    checks.extend(_audit_eof_checks(v14_text, status_text))
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "review_only": True,
            "default_off": True,
            "read_only_existing_artifacts_and_source_surfaces": True,
            "implementation_plan_json": str(implementation_plan_json.resolve()),
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
                "CAMP remains a fixed-candidate reranker. Any future shadow "
                "selector must compute score_k(w)=a_k^T w from current-tick "
                "finite candidate atoms only, while runtime output remains DP "
                "Top-1 during the default-off shadow phase."
            ),
        },
        "source_hashes": source_hashes,
        "source_summary": _source_summary(source_plan),
        "static_contract_review": _static_contract_review(),
        "unit_tests_plan_requirements": _unit_tests_plan_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "default_off_shadow_selector_implementation_static_contract_review.json",
        report,
    )
    (
        output_dir
        / "default_off_shadow_selector_implementation_static_contract_review.md"
    ).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# V14 Default-Off Shadow Selector Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Unit-tests plan authorized: `{decision['default_off_shadow_selector_implementation_unit_tests_plan_authorized']}`",
        f"- Implementation authorized: `{decision['default_off_shadow_selector_implementation_authorized']}`",
        f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        "",
        "## Review",
        "",
        f"- Status: `{review['status']}`",
        f"- Runtime effect: `{review['runtime_effect']}`",
        f"- Candidate operation: `{review['candidate_operation']}`",
        f"- Score expression: `{review['score_expression']}`",
        "",
        "## Contracts",
        "",
    ]
    for item in review["contracts"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Unit-Test Plan Requirements", ""])
    for item in report["unit_tests_plan_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report["forbidden_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is review-only. It does not edit production selector wiring, "
            "train CAMP, run replay, generate candidates, modify DP, promote "
            "atoms or selectors, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    review_requirements = _list(payload.get("static_review_requirements"))
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
        _expect("source_plan_ready", decision.get("default_off_shadow_selector_implementation_plan_ready"), True),
        _expect(
            "source_static_contract_review_authorized",
            decision.get(
                "default_off_shadow_selector_implementation_static_contract_review_authorized"
            ),
            True,
        ),
        _expect(
            "source_implementation_not_authorized",
            decision.get("default_off_shadow_selector_implementation_authorized"),
            False,
        ),
        _expect("source_plan_status_no_implementation", plan.get("status"), "plan_ready_no_implementation"),
        _expect("source_plan_selector_phase", plan.get("selector_phase"), "future_default_off_shadow_only"),
        _expect(
            "source_plan_runtime_effect",
            plan.get("runtime_effect"),
            "log shadow_selected_index while executed output remains DP Top-1",
        ),
        _expect(
            "source_plan_candidate_source",
            plan.get("candidate_source"),
            "fixed current-tick DP candidate tensor before CAMP scoring",
        ),
        _expect("source_plan_candidate_count", plan.get("candidate_count"), 8),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect(
            "source_plan_selection_rule",
            plan.get("selection_rule"),
            "shadow_selected_index = argmin_k score_k(w)",
        ),
        _contains_item(
            "source_plan_default_off_step",
            required_steps,
            "add a default-off shadow selector flag or config whose default is false",
        ),
        _contains_item(
            "source_plan_immutable_artifacts_step",
            required_steps,
            "load immutable v14 weights, atom scales, and artifact hash manifest only",
        ),
        _contains_item(
            "source_plan_affine_score_step",
            required_steps,
            "compute normalized candidate atoms and scores as normalized_atoms @ weights",
        ),
        _contains_item(
            "source_plan_dp_top1_runtime_step",
            required_steps,
            "keep executed trajectory and online selector output equal to DP Top-1 during shadow phase",
        ),
        _contains_item(
            "source_plan_fail_closed_step",
            required_steps,
            "fail closed to DP Top-1 and explicit no-shadow log on any contract violation",
        ),
        _contains_item(
            "source_review_no_shadow_route_requirement",
            review_requirements,
            "prove no shadow index is routed into executed trajectory output",
        ),
        _contains_item(
            "source_review_no_candidate_mutation_requirement",
            review_requirements,
            "prove no candidate row is created, appended, deleted, blended, or rewritten",
        ),
        _contains_item(
            "source_review_affine_score_requirement",
            review_requirements,
            "prove scoring remains score_k(w)=a_k^T w over fixed current-tick candidate atoms",
        ),
        _contains_item(
            "source_forbids_dp_modification",
            forbidden_paths,
            "modifying, retraining, or tuning Diffusion Planner",
        ),
        _contains_item(
            "source_forbids_claims",
            forbidden_paths,
            "claiming deployability, safety benefit, or CAMP superiority from this plan",
        ),
        *[_expect(f"source_plan_{name}_false", decision.get(name), False) for name in BLOCKED_ACTIONS],
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
            f"current_v14_status={SOURCE_PLAN_STATUS}" in eof,
            _extract_line(eof, "current_v14_status="),
            f"current_v14_status={SOURCE_PLAN_STATUS}",
        ),
        _check(
            "audit_latest_next_work",
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof,
            _extract_line(eof, "next_work_target="),
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}",
        ),
        _check(
            "current_status_latest_status",
            f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text,
            "present" if f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text else "missing",
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
    plan = _dict(payload.get("implementation_plan"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": decision.get(
            "default_off_shadow_selector_implementation_static_contract_review_authorized"
        ),
        "implementation_authorized": decision.get(
            "default_off_shadow_selector_implementation_authorized"
        ),
        "runtime_effect": plan.get("runtime_effect"),
        "candidate_source": plan.get("candidate_source"),
        "candidate_count": plan.get("candidate_count"),
        "score_expression": plan.get("score_expression"),
        "selection_rule": plan.get("selection_rule"),
    }


def _static_contract_review() -> dict[str, Any]:
    return {
        "status": "review_passed_no_implementation",
        "runtime_effect": "executed output remains DP Top-1 during shadow phase",
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
        "unit tests must prove shadow selection does not change executed DP Top-1 trajectory",
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
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "default_off_shadow_selector_implementation_static_contract_review_passed": passed,
        "default_off_shadow_selector_implementation_unit_tests_plan_authorized": passed,
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "review_enabled" in failed_set:
        return "explicit_static_contract_review_authorization_missing"
    if {"audit_latest_status", "audit_latest_next_work"} & failed_set:
        return "v14_eof_contract_mismatch"
    if any(name.startswith("source_plan") or name.startswith("source_review") for name in failed):
        return "source_implementation_plan_contract_failure"
    if any(name.startswith("integration_") or name.startswith("runner_") or name.startswith("benders_") for name in failed):
        return "source_surface_contract_failure"
    return "default_off_shadow_selector_implementation_static_contract_review_failure"


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


def _contains_item(name: str, items: list[Any], expected: str) -> dict[str, Any]:
    return _check(name, expected in items, items, expected)


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


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
