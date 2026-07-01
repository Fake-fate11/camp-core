from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_member_source_generation import (
    AUTHORIZED_CURRENT_WORK as PLAN_AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_CURRENT_WORK,
    FIXED_DP_HEAD,
    REQUIRED_PLAN_STEPS,
)
from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_member_source_generation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_NEXT_WORK,
    LATEST_AUDIT_STATUS,
    PASS_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "7c54d06c573f2cf3ce8c0ce73946bb3912afffdd"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _plan_artifact(root: Path) -> Path:
    payload = {
        "schema_version": "dp_camp_v13_default_off_member_source_generation_plan_v1",
        "generation_plan": {
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "fixed_dp_candidate_generation_execution_authorized_now": False,
            "next_gate_is_static_contract_review_only": True,
            "required_steps": list(REQUIRED_PLAN_STEPS),
            "score_expression": "score_k(w)=a_k^T w",
            "training_authorized": False,
        },
        "final_decision": {
            "authorized_current_work": PLAN_AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": REVIEW_AUTHORIZED_CURRENT_WORK,
            "failed_checks": [],
            "passed": True,
            "status": "dp_camp_v13_default_off_member_source_generation_plan_ready",
        },
    }
    _write_json(root / "default_off_member_source_generation_plan.json", payload)
    return root


def _audit(path: Path, *, target: str = REVIEW_AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "default_off_member_source_generation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _plan_script(path: Path, *, include_source_contracts: bool = True) -> Path:
    snippets = [
        'fixed_dp_candidate_generation_execution_authorized_now": False',
        'candidate_generation_by_camp_authorized": False',
        'dp_modification_authorized": False',
        'score_expression": SCORE_EXPRESSION',
        'next_gate_is_static_contract_review_only": True',
    ]
    text = "\n".join(snippets if include_source_contracts else snippets[:-1])
    return _write(path, text + "\n")


def _plan_test(path: Path) -> Path:
    return _write(path, "def test_placeholder():\n    assert True\n")


def _build(tmp_path: Path, *, target: str = REVIEW_AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        plan_artifact_dir=_plan_artifact(tmp_path / "plan_artifact"),
        plan_script=_plan_script(tmp_path / "plan.py"),
        plan_test=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_default_off_member_source_generation_static_contract_passes(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["score_expression"] == "score_k(w)=a_k^T w"


def test_default_off_member_source_generation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_default_off_member_source_generation_static_contract_requires_source_boundaries(
    tmp_path: Path,
) -> None:
    report = build_report(
        plan_artifact_dir=_plan_artifact(tmp_path / "plan_artifact"),
        plan_script=_plan_script(
            tmp_path / "plan.py",
            include_source_contracts=False,
        ),
        plan_test=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        name.startswith("source_contains_next_gate_is_static_contract_review_only")
        for name in report["final_decision"]["failed_checks"]
    )


def test_default_off_member_source_generation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--plan_artifact_dir",
            str(_plan_artifact(tmp_path / "plan_artifact")),
            "--plan_script",
            str(_plan_script(tmp_path / "plan.py")),
            "--plan_test",
            str(_plan_test(tmp_path / "test_plan.py")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Static Contract Review" in output_md.read_text(encoding="utf-8")
