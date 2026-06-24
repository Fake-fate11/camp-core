from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    CURRENT_GATE,
    DEFAULT_POLICY,
    IMPLEMENTATION_READY_STATUS,
    PLANNED_POLICY,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_CONTRACT_TESTS,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={IMPLEMENTATION_READY_STATUS}
authorized_next_work={CURRENT_GATE}
candidate_generation_execution_authorized=False
fixed_snapshot_screen_rerun_authorized=False
formal_seeds_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _source_text() -> str:
    return f'''
class RouteTopologyCandidateConfig:
    generator_policy: str = "{DEFAULT_POLICY}"
    max_remediation_candidates: int = 12

def parse_args():
    parser.add_argument("--max_remediation_candidates")
    choices = ("{DEFAULT_POLICY}", "{PLANNED_POLICY}")

def build_route_topology_candidates():
    if int(config.max_remediation_candidates) <= 0:
        raise ValueError("max_remediation_candidates must be positive.")
    if config.generator_policy == "{PLANNED_POLICY}":
        metadata.append({{
            "candidate_budget_cap": int(config.max_remediation_candidates),
            "remediation_descriptor_payload": _command_jerk_descriptor_payload(candidate),
        }})

def analyze():
    _score_trajectories()
    _tracker_delta()

def _command_jerk_descriptor_payload():
    return {{
        "payload_role": "report_only_current_tick_descriptor",
        "descriptor_family": "command_jerk_hinge",
        "top_comfort_blocker": "route_topology_comfort_blocked_command_jerk",
        "current_tick_features_only": True,
        "candidate_local": True,
        "nonnegative_or_hinge_signed_split_legal": True,
        "command_jerk_abs_max_mps3": 0.0,
        "command_jerk_hinge_mps3": 0.0,
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
        "candidate_mutation": False,
        "selected_index_mutation": False,
        "fallback_mutation": False,
        "online_selector_feature": False,
        "deployed_atom_schema_change": False,
        "dp_import": False,
        "reward_recompute": False,
        "tracker_recompute": False,
    }}
'''


def _route_test_text() -> str:
    return f'''
def test_route_topology_report_rejects_invalid_remediation_candidate_cap():
    assert "max_remediation_candidates must be positive"
    assert "max_remediation_candidates=0"

def test_route_topology_policy_contracts():
    assert "{DEFAULT_POLICY}"
    assert "{PLANNED_POLICY}"
    assert "candidate_budget_cap"
'''


def _contract_test_text() -> str:
    tests = "\n".join(f"def {name}(): pass" for name in REQUIRED_CONTRACT_TESTS)
    return (
        tests
        + '\nassert "remediation_descriptor_payload"\n'
        + 'assert "score_k(w)=a_k^T w"\n'
        + 'assert "simplex/CVaR/L2"\n'
        + 'assert "formal_seeds"\n'
        + 'assert "formal seeds"\n'
        + 'assert "use formal seeds"\n'
        + 'assert "seed=11" not in source\n'
        + 'assert "seed=12" not in source\n'
        + 'assert "seed=13" not in source\n'
        + 'assert "training"\n'
        + 'assert "dp_import"\n'
        + 'assert "reward_recompute"\n'
        + 'assert "tracker_recompute"\n'
    )


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
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, source, route_test, contract_test = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        source_text=source_text,
        route_test_text=route_test_text,
        contract_test_text=contract_test_text,
    )
    return build_report(
        audit_path=audit,
        source_path=source,
        route_test_path=route_test,
        contract_test_path=contract_test,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_post_implementation_static_review_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_residual_comfort_remediation_post_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_residual_comfort_remediation_post_review_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_tail_authorizes_current_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_post_review_rejects_descriptor_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace("command_jerk_hinge", "missing"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_descriptor_family_command_jerk_hinge" in report[
        "final_decision"
    ]["failed_checks"]


def test_residual_comfort_remediation_post_review_rejects_dp_reward_tracker_in_descriptor(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            '"tracker_recompute": False,',
            '"tracker_recompute": False,\\n        "debug": "_score_trajectories",',
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_descriptor_does_not_call_reward_or_tracker" in report[
        "final_decision"
    ]["failed_checks"]


def test_residual_comfort_remediation_post_review_rejects_route_test_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        route_test_text=_route_test_text().replace("candidate_budget_cap", "missing"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "route_test_contract_route_required_tokens_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_residual_comfort_remediation_post_review_rejects_contract_test_drift(
    tmp_path: Path,
) -> None:
    missing = "test_residual_comfort_remediation_report_only_descriptor_payload"
    report = _build(
        tmp_path,
        contract_test_text=_contract_test_text().replace(missing, "missing_test"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_contract_required_contract_tests_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_residual_comfort_remediation_post_review_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Review" in markdown
    assert "fixed-snapshot screen rerun planning only may follow" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "classical Benders" in markdown


def test_residual_comfort_remediation_post_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, source, route_test, contract_test = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"
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

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Residual Comfort Remediation Post-Implementation Static Review"
    )
