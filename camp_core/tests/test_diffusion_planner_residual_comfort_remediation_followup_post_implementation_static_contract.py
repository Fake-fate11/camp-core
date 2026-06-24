from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_remediation_"
    "followup_post_implementation_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.IMPLEMENTATION_READY_STATUS}
authorized_next_work={target.CURRENT_GATE}
fixed_snapshot_screen_rerun_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _source_text() -> str:
    return '''
REMEDIATION_PROFILE_OFF = "off"
REMEDIATION_PROFILE_SUPPORT_V1 = "lane_projected_jerk_progress_support_v1"

class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF

def parse_args():
    parser.add_argument("--default_off_remediation_profile")

def build_report_from_rows():
    return {"effective_comfort_budgets": _effective_comfort_budgets(config)}

def _comfort_admissible():
    budgets = _effective_comfort_budgets(config)
    assert budgets["command_jerk_worse_budget_mps3"]
    assert budgets["rollout_lateral_worse_budget_mps2"]

def _comfort_failure_classes():
    budgets = _effective_comfort_budgets(config)
    assert "route_topology_comfort_blocked_rollout_lateral"
    assert budgets["rollout_lateral_worse_budget_mps2"]

def _effective_comfort_budgets(config):
    return {
        "default_off_remediation_profile": REMEDIATION_PROFILE_SUPPORT_V1,
        "command_jerk_worse_budget_mps3": 0.05,
        "rollout_lateral_worse_budget_mps2": 1.0,
    }

def _command_jerk_descriptor_payload():
    return {
        "payload_role": "report_only_current_tick_descriptor",
        "descriptor_family": "command_jerk_hinge",
        "followup_payload_role": "report_only",
        "followup_descriptor_family": "command_jerk_rollout_lateral_zero_comfort_gap",
        "current_tick_features_only": True,
        "candidate_local": True,
        "uses_outcome_labels": False,
        "future_outcome_leakage": False,
        "nonnegative_or_hinge_signed_split_legal": True,
        "command_jerk_hinge_mps3": 0.0,
        "command_jerk_signed_pos_mps3": 0.0,
        "command_jerk_signed_neg_mps3": 0.0,
        "rollout_lateral_hinge_mps2": 0.0,
        "rollout_lateral_signed_pos_mps2": 0.0,
        "rollout_lateral_signed_neg_mps2": 0.0,
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
        "candidate_mutation": False,
        "score_mutation": False,
        "selected_index_mutation": False,
        "fallback_mutation": False,
        "online_selector_feature": False,
        "deployed_atom_schema_change": False,
    }

def _validate_config():
    if config.default_off_remediation_profile not in {
        REMEDIATION_PROFILE_OFF,
        REMEDIATION_PROFILE_SUPPORT_V1,
    }:
        raise ValueError("default_off_remediation_profile")
'''


def _route_test_text() -> str:
    return '''
def test_route_topology_generator_builds_negative_support_followup_policy(): pass
def test_route_topology_generator_builds_comfort_first_remediation_policy(): pass
def test_route_topology_report_rejects_invalid_remediation_candidate_cap(): pass
assert "candidate_budget_cap"
assert "max_remediation_candidates must be positive"
'''


def _contract_test_text() -> str:
    return '''
assert "command_jerk_rollout_lateral_zero_comfort_gap"
assert "_assert_no_surface_mutation"
assert "score_mutation"
assert "current_tick_features_only"
assert "candidate_local"
assert "future_outcome_leakage"
assert "command_jerk_signed_pos_mps3"
assert "rollout_lateral_signed_neg_mps2"
assert "score_k(w)=a_k^T w"
assert "simplex/CVaR/L2 master unchanged"
assert "training_execution_authorized"
assert "dp_modification_authorized"
assert "formal_seeds_authorized"
'''


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    route_test_text: str | None = None,
    contract_test_text: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    source = tmp_path / "screen.py"
    route_test = tmp_path / "test_screen.py"
    contract_test = tmp_path / "test_contract.py"
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    source.write_text(source_text if source_text is not None else _source_text(), encoding="utf-8")
    route_test.write_text(
        route_test_text if route_test_text is not None else _route_test_text(),
        encoding="utf-8",
    )
    contract_test.write_text(
        contract_test_text if contract_test_text is not None else _contract_test_text(),
        encoding="utf-8",
    )
    return audit, source, route_test, contract_test


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    route_test_text: str | None = None,
    contract_test_text: str | None = None,
    dp_head: str = target.EXPECTED_DP_HEAD,
) -> dict:
    audit, source, route_test, contract_test = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        source_text=source_text,
        route_test_text=route_test_text,
        contract_test_text=contract_test_text,
    )
    return target.build_report(
        audit_path=audit,
        source_path=source,
        route_test_path=route_test,
        contract_test_path=contract_test,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_followup_post_implementation_static_review_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_followup_post_implementation_static_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_post_implementation_static_review_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_tail_authorizes_current_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_post_implementation_static_review_rejects_descriptor_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            "command_jerk_rollout_lateral_zero_comfort_gap",
            "missing",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_descriptor_adds_followup_family" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_post_implementation_static_review_rejects_reward_tracker_leak(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            '"deployed_atom_schema_change": False,',
            '"deployed_atom_schema_change": False,\\n        "debug": "_tracker_delta",',
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_descriptor_does_not_call_reward_or_tracker" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_post_implementation_static_review_rejects_missing_profile_validation(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            'raise ValueError("default_off_remediation_profile")',
            "return None",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_invalid_profile_fails_closed" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_post_implementation_static_review_rejects_missing_route_test(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, route_test_text="assert 'candidate_budget_cap'")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "route_test_contract_negative_support_policy_tests_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_post_implementation_static_review_rejects_missing_contract_test(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, contract_test_text="assert 'score_k(w)=a_k^T w'")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "contract_test_contract_followup_family_pinned" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_post_implementation_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, source, route_test, contract_test = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_contract_review.json"
    output_md = tmp_path / "out" / "static_contract_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--audit_path",
            str(audit),
            "--source_path",
            str(source),
            "--route_test_path",
            str(route_test),
            "--contract_test_path",
            str(contract_test),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            target.EXPECTED_DP_HEAD,
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    target.main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["final_decision"]["status"] == target.READY_STATUS
    assert "Post-Implementation Static Contract Review" in markdown
