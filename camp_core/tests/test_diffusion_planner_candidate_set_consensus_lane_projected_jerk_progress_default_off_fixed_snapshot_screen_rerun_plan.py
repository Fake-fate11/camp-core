from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    DEFAULT_STATIC_REVIEW_ROOT,
    GATE_NAME,
    GUARD_ENV_ASSIGNMENT,
    GUARD_ENV_VAR,
    READY_STATUS,
    REJECT_STATUS,
    SHA256SUMS,
    SOURCE_DECISION,
    SOURCE_JSON,
    SOURCE_STATUS,
    build_report,
    main,
    render_markdown,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _source_json(
    *,
    status: str = SOURCE_STATUS,
    passed: bool = True,
    next_gate: str = GATE_NAME,
    rerun_authorized: bool = False,
    blocked_action: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "passed": passed,
        "next_recommended_gate": next_gate,
        "checks": {
            "default_off_consensus_signature": True,
            "default_off_progress_signature": True,
            "diagnostic_payloads_default_none": True,
            "payloads_after_selection": True,
            "selection_effect_false": True,
            "future_outcome_leakage_false": True,
            "no_dp_path_changed": True,
            "no_formal_seed_execution": True,
            "no_replay_execution_artifact": True,
            "no_camp_retraining": True,
        },
    }
    for key in BLOCKED_ACTIONS:
        payload[key] = False
    payload["fixed_snapshot_screen_rerun_authorized"] = rerun_authorized
    if blocked_action:
        payload["atom_promotion_authorized"] = True
    return payload


def _decision_text(
    *,
    status: str = SOURCE_STATUS,
    passed: bool = True,
    next_gate: str = GATE_NAME,
    rerun_authorized: bool = False,
    blocked_action: bool = False,
) -> str:
    lines = [
        f"status={status}",
        f"passed={passed}",
        f"post_implementation_static_review_complete={passed}",
        "default_off_reaudited=True",
        "no_dp_modification=True",
        "no_future_information_leakage=True",
        "no_formal_seed=True",
        "no_replay=True",
        "no_promotion=True",
        "no_safety_benefit_claim=True",
        "no_camp_over_dp_top1_claim=True",
        "no_classic_benders_claim=True",
        f"recommended_next_gate={next_gate}",
    ]
    for key in BLOCKED_ACTIONS:
        lines.append(f"{key}=False")
    lines.append(f"fixed_snapshot_screen_rerun_authorized={rerun_authorized}")
    if blocked_action:
        lines.append("atom_promotion_authorized=True")
    return "\n".join(lines) + "\n"


def _write_static_review_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    decision_text: str | None = None,
    review_exit: int = 0,
    decision_exit: int = 0,
) -> Path:
    root = tmp_path / "post_static_review"
    root.mkdir()
    files = {
        "HEADS.txt": f"CAMP_HEAD=abc\nCAMP_ORIGIN_MAIN=abc\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        SOURCE_JSON: json.dumps(payload or _source_json(), sort_keys=True),
        SOURCE_DECISION: decision_text or _decision_text(),
        "STATIC_REVIEW.err": "",
        "STATIC_REVIEW_EXIT": f"{review_exit}\n",
        "STATIC_REVIEW_DECISION.err": "",
        "STATIC_REVIEW_DECISION_EXIT": f"{decision_exit}\n",
        "SHA256SUMS_CHECK_EXIT": "0\n",
        "EXIT_CODE": "0\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    _write_sha256sums(root, tuple(files))
    return root


def _build(tmp_path: Path, **kwargs) -> dict:
    return build_report(
        static_review_root=_write_static_review_root(tmp_path, **kwargs),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_default_off_fixed_snapshot_screen_rerun_plan_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["fixed_snapshot_rerun_plan"]
    seeds = {row["seed"] for row in plan["route_seed_matrix"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_ready"] is True
    assert decision["fixed_snapshot_screen_rerun_execution_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert not (seeds & FORMAL_SEEDS)
    assert plan["selection_type"] == "guarded_fixed_snapshot_screen_rerun_plan_only"
    assert plan["coverage_summary"]["traffic_light_covered"] is True
    assert plan["coverage_summary"]["turn_covered"] is True
    assert plan["coverage_summary"]["normal_covered"] is True
    assert plan["coverage_summary"]["nishishinjuku_assets_declared"] is True
    assert plan["coverage_summary"]["included_guarded_rerun_count"] == 1
    assert plan["product_code_payload_contract"]["selection_effect_allowed"] is False
    assert plan["product_code_payload_contract"]["future_outcome_leakage_allowed"] is False
    assert report["runbook"]["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT
    assert DEFAULT_STATIC_REVIEW_ROOT.endswith(
        "candidate_set_consensus_lane_projected_jerk_progress_default_off_"
        "post_implementation_static_review_b44e3f5"
    )


def test_default_off_fixed_snapshot_screen_rerun_plan_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_static_review_root(tmp_path)
    (root / SOURCE_DECISION).write_text("mutated=True\n", encoding="utf-8")

    report = build_report(
        static_review_root=root,
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_artifact_sha256sums_ok" in report["final_decision"][
        "failed_checks"
    ]
    assert report["final_decision"]["authorized_next_work"] is None


def test_default_off_fixed_snapshot_screen_rerun_plan_rejects_head_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_review_root=_write_static_review_root(tmp_path),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="def",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "camp_head_equals_origin_main" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_fixed_snapshot_screen_rerun_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_review_root=_write_static_review_root(tmp_path),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_default_off_fixed_snapshot_screen_rerun_plan_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_source_json(status="bad", passed=False, next_gate="other"),
        decision_text=_decision_text(status="bad", passed=False, next_gate="other"),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_decision_status" in failed
    assert "source_passed" in failed
    assert "source_recommends_this_plan_gate" in failed


def test_default_off_fixed_snapshot_screen_rerun_plan_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_source_json(rerun_authorized=True, blocked_action=True),
        decision_text=_decision_text(rerun_authorized=True, blocked_action=True),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_rerun_execution_not_authorized" in failed
    assert "source_no_blocked_actions" in failed


def test_default_off_fixed_snapshot_screen_rerun_plan_markdown_and_runbook(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)
    runbook = report["runbook"]["text"]

    assert "# Default-Off Product-Code Fixed-Snapshot Screen Rerun Plan" in markdown
    assert "plan-only gate; no screen rerun is executed here" in markdown
    assert GUARD_ENV_VAR in runbook
    assert 'PY="/root/miniconda3/bin/python"' in runbook
    assert "Refusing to run" in runbook
    assert "git pull" not in runbook
    assert "seed 11" not in runbook
    assert "seed 12" not in runbook
    assert "seed 13" not in runbook
    assert "camp_retraining" not in runbook.lower()


def test_default_off_fixed_snapshot_screen_rerun_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    review_root = _write_static_review_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    output_bash = tmp_path / "out" / "runbook.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--static_review_root",
            str(review_root),
            "--planned_execution_root",
            str(tmp_path / "execution"),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Default-Off Product-Code Fixed-Snapshot Screen Rerun Plan"
    )
    assert GUARD_ENV_VAR in output_bash.read_text(encoding="utf-8")
