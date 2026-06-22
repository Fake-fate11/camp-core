from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    EXIT_CODE,
    HEADS,
    SHA256SUMS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_unit_tests import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    REVIEW_JSON,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_static_contract import (
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as REVIEW_READY_STATUS,
)


def _review_payload(
    *,
    status: str = REVIEW_READY_STATUS,
    authorized_next_work: str | None = REVIEW_AUTHORIZED_NEXT_WORK,
    contract_overrides: dict[str, bool] | None = None,
) -> dict:
    contracts = {
        "relative_comfort_contract": True,
        "hard_feasibility_contract": True,
        "latency_contract": True,
        "policy_default_off_contract": True,
    }
    if contract_overrides:
        contracts.update(contract_overrides)
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "selected_next_work": authorized_next_work,
            "implementation_code_edit_authorized": False,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "atom_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "static_contract_review": {
            "selected_next_work": authorized_next_work,
            "contracts": [
                {
                    "name": name,
                    "status": status_value,
                    "evidence": f"{name} evidence",
                }
                for name, status_value in contracts.items()
            ],
        },
    }


def _write_sha256sums(root: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        data = (root / name).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_root(tmp_path: Path, payload: dict | None = None) -> Path:
    root = tmp_path / "review"
    root.mkdir()
    (root / REVIEW_JSON).write_text(
        json.dumps(payload or _review_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / EXIT_CODE).write_text("0\n", encoding="utf-8")
    (root / HEADS).write_text("HEADS\n", encoding="utf-8")
    _write_sha256sums(root, [REVIEW_JSON, EXIT_CODE, HEADS])
    return root


def _build(tmp_path: Path, payload: dict | None = None) -> dict:
    root = _write_review_root(tmp_path, payload)
    return build_report(
        review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_unit_tests_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    plan = report["unit_test_plan"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert plan["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert len(plan["test_groups"]) == 5


def test_unit_tests_plan_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)
    (root / REVIEW_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_unit_tests_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)

    report = build_report(
        review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_unit_tests_plan_rejects_missing_review_authorization(tmp_path: Path) -> None:
    report = _build(tmp_path, _review_payload(authorized_next_work="not_allowed"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_authorizes_unit_tests_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_unit_tests_plan_rejects_contract_false(tmp_path: Path) -> None:
    payload = _review_payload(
        contract_overrides={"relative_comfort_contract": False}
    )
    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_contract_relative_comfort_contract_true" in report[
        "final_decision"
    ]["failed_checks"]


def test_unit_tests_plan_rejects_missing_contract(tmp_path: Path) -> None:
    payload = _review_payload()
    payload["static_contract_review"]["contracts"] = payload[
        "static_contract_review"
    ]["contracts"][:-1]
    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_contract_names_present" in report["final_decision"][
        "failed_checks"
    ]


def test_unit_tests_plan_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Default-Off Remediation Unit Tests Plan" in markdown
    assert "relative_comfort_threshold_unit_tests" in markdown
    assert "hard_feasibility_label_unit_tests" in markdown
    assert "latency_reporting_unit_tests" in markdown
    assert "policy_default_off_unit_tests" in markdown
    assert "implementation code edits are not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_unit_tests_plan_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    root = _write_review_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--review_root",
            str(root),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Lane-Projected Jerk/Progress Default-Off Remediation Unit Tests Plan"
    )
